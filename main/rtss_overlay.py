"""
RivaTuner Statistics Server (RTSS) Resmi SDK Birebir Entegrasyonu
Guru3D RTSS C++ SDK kaynak kodlarından (RTSSSharedMemorySampleDlg.cpp) doğrudan uyarlanmıştır.
"""
import ctypes
from ctypes import wintypes
import atexit
import os
import sys
import subprocess

FILE_MAP_ALL_ACCESS = 0x000F001F
RTSS_SHARED_MEMORY_NAME = "RTSSSharedMemoryV2"
RTSS_SIGNATURE = 0x52545353  # 'RTSS'

class RTSSOverlay:
    def __init__(self, app_name="WattCost", _watchdog=True):
        self.app_name = app_name
        self._use_watchdog = _watchdog
        self.kernel32 = ctypes.windll.kernel32
        
        self.kernel32.OpenFileMappingW.restype = wintypes.HANDLE
        self.kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        
        self.kernel32.MapViewOfFile.restype = wintypes.LPVOID
        self.kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
        
        self.kernel32.UnmapViewOfFile.argtypes = [wintypes.LPCVOID]
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        
        # Uygulama beklenmedik kapansa bile OSD'yi temizle
        atexit.register(self.release_osd)
        
        # Windows konsol / oturum kapatma kancası
        try:
            def _console_ctrl_handler(ctrl_type):
                try:
                    self.release_osd()
                except Exception:
                    pass
                return False

            self._handler_ref = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)(_console_ctrl_handler)
            self.kernel32.SetConsoleCtrlHandler(self._handler_ref, True)
        except Exception:
            pass

        # Açılışta varsa önceki kalıntıları hemen süpür
        try:
            self.release_osd()
        except Exception:
            pass

        # Sert kapatmaya (Görev Yöneticisi / çökme) karşı gözcü süreç başlat
        if self._use_watchdog:
            self._start_watchdog()

    def _start_watchdog(self):
        """Ana süreç nasıl ölürse ölsün, OSD slotunu temizleyen ayrı bir süreç başlatır."""
        try:
            if getattr(sys, 'frozen', False):
                # Exe modunda çalışırken: kendisini --watch argümanı ile çağır
                args = [sys.executable, "--watch", str(os.getpid()), self.app_name]
            else:
                exe = sys.executable
                pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
                if os.path.exists(pyw):
                    exe = pyw
                script = os.path.abspath(__file__)
                args = [exe, script, "--watch", str(os.getpid()), self.app_name]
            CREATE_NO_WINDOW = 0x08000000
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_BREAKAWAY_FROM_JOB = 0x01000000
            base = CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            for flags in (base | CREATE_BREAKAWAY_FROM_JOB, base):
                try:
                    subprocess.Popen(args, creationflags=flags, close_fds=True,
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                    return
                except OSError:
                    continue
        except Exception:
            pass

    def update_osd(self, text):
        """
        RTSS OSD metnini gunceller.
        RTSS_SHARED_MEMORY_OSD_ENTRY yapisi:
          Offset 0   (256 bayt) : szOSD (Goruntulenen metin)
          Offset 256 (256 bayt) : szOSDOwner (Uygulama kimligi, ornegin 'WattCost')
          Offset 512 (4096 bayt): szOSDEx (Genisletilmis metin, v2.7+)
        """
        h_map = self.kernel32.OpenFileMappingW(FILE_MAP_ALL_ACCESS, False, RTSS_SHARED_MEMORY_NAME)
        if not h_map:
            return False
            
        p_buf = self.kernel32.MapViewOfFile(h_map, FILE_MAP_ALL_ACCESS, 0, 0, 0)
        if not p_buf:
            self.kernel32.CloseHandle(h_map)
            return False
            
        b_result = False
        try:
            dw_signature = ctypes.c_uint32.from_address(p_buf).value
            dw_version = ctypes.c_uint32.from_address(p_buf + 4).value
            
            if dw_signature == RTSS_SIGNATURE and dw_version >= 0x00020000:
                dw_osd_entry_size = ctypes.c_uint32.from_address(p_buf + 20).value
                dw_osd_arr_offset = ctypes.c_uint32.from_address(p_buf + 24).value
                dw_osd_arr_size = ctypes.c_uint32.from_address(p_buf + 28).value
                
                # Resmi SDK Mantigi: 
                # 1. Gecis (Pass 0): Once onceden yakaladigimiz slotu ara
                # 2. Gecis (Pass 1): Bulunamazsa ilk bos slotu yakala
                # Not: dw_entry = 1'den baslar (Slot 0 birincil istemciler icindir)
                for dw_pass in range(2):
                    for dw_entry in range(1, dw_osd_arr_size):
                        entry_ptr = p_buf + dw_osd_arr_offset + (dw_entry * dw_osd_entry_size)
                        
                        # szOSDOwner offset 256'dadir!
                        owner_bytes = ctypes.string_at(entry_ptr + 256, 256)
                        owner = owner_bytes.split(b'\x00')[0].decode('latin-1', errors='ignore')
                        
                        if dw_pass == 1:
                            if not owner:
                                owner_raw = self.app_name.encode('latin-1')[:255] + b'\x00'
                                ctypes.memmove(entry_ptr + 256, owner_raw, len(owner_raw))
                                owner = self.app_name
                                
                        if owner == self.app_name:
                            # Metin yoksa veya bossa ekrandan kaldir
                            if not text or not text.strip():
                                ctypes.memset(entry_ptr, 0, dw_osd_entry_size)
                                cur_frame = ctypes.c_uint32.from_address(p_buf + 32).value
                                ctypes.c_uint32.from_address(p_buf + 32).value = cur_frame + 1
                                b_result = True
                                break

                            # Metni Latin-1 ve temiz ASCII olarak hazırla
                            text_clean = text.encode('latin-1', errors='ignore')
                            
                            # KESIN COZUM: Yazmadan once OSD tamponlarini tamamen SIFIRLA!
                            # Boylece 2 satirdan 1 satira dusuldugunde eski satir artiklari ekranda kalmaz.
                            ctypes.memset(entry_ptr, 0, 256)
                            if dw_version >= 0x00020007:
                                ctypes.memset(entry_ptr + 512, 0, 4096)

                            # Resmi SDK Kuralı: v2.7+ ise YALNIZCA szOSDEx alanına yazılır.
                            # Hem szOSD hem szOSDEx'e yazılırsa RTSS ekranda çift (duplicate) metin çizer!
                            if dw_version >= 0x00020007:
                                osd_long = text_clean[:4095] + b'\x00'
                                ctypes.memmove(entry_ptr + 512, osd_long, len(osd_long))
                            else:
                                osd_short = text_clean[:255] + b'\x00'
                                ctypes.memmove(entry_ptr, osd_short, len(osd_short))
                                
                            # RESMI SDK: pMem->dwOSDFrame++ (offset 32)
                            cur_frame = ctypes.c_uint32.from_address(p_buf + 32).value
                            ctypes.c_uint32.from_address(p_buf + 32).value = cur_frame + 1
                            
                            b_result = True
                            break
                            
                    if b_result:
                        break
        finally:
            self.kernel32.UnmapViewOfFile(p_buf)
            self.kernel32.CloseHandle(h_map)
            
        return b_result

    def release_osd(self):
        """Uygulama kapanirken OSD slotunu tamamen temizler ve ekrandan kaldirir."""
        h_map = self.kernel32.OpenFileMappingW(FILE_MAP_ALL_ACCESS, False, RTSS_SHARED_MEMORY_NAME)
        if not h_map:
            return
        p_buf = self.kernel32.MapViewOfFile(h_map, FILE_MAP_ALL_ACCESS, 0, 0, 0)
        if not p_buf:
            self.kernel32.CloseHandle(h_map)
            return
        try:
            dw_signature = ctypes.c_uint32.from_address(p_buf).value
            if dw_signature == RTSS_SIGNATURE:
                dw_osd_entry_size = ctypes.c_uint32.from_address(p_buf + 20).value
                dw_osd_arr_offset = ctypes.c_uint32.from_address(p_buf + 24).value
                dw_osd_arr_size = ctypes.c_uint32.from_address(p_buf + 28).value
                
                cleared = False
                for dw_entry in range(dw_osd_arr_size):
                    entry_ptr = p_buf + dw_osd_arr_offset + (dw_entry * dw_osd_entry_size)
                    owner = ctypes.string_at(entry_ptr + 256, 256).split(b'\x00')[0].decode('latin-1', errors='ignore')
                    osd = ctypes.string_at(entry_ptr, 256).split(b'\x00')[0].decode('latin-1', errors='ignore')
                    osd_ex = ctypes.string_at(entry_ptr + 512, 512).split(b'\x00')[0].decode('latin-1', errors='ignore')
                    
                    if (owner == self.app_name or self.app_name in osd or self.app_name in osd_ex or
                        ("TL/sa" in osd) or ("TL" in osd and "W" in osd) or
                        ("TL/sa" in osd_ex) or ("TL" in osd_ex and "W" in osd_ex)):
                        ctypes.memset(entry_ptr, 0, dw_osd_entry_size)
                        cleared = True
                        
                if cleared:
                    cur_frame = ctypes.c_uint32.from_address(p_buf + 32).value
                    ctypes.c_uint32.from_address(p_buf + 32).value = cur_frame + 1
        finally:
            self.kernel32.UnmapViewOfFile(p_buf)
            self.kernel32.CloseHandle(h_map)

    def get_active_fps(self):
        """RTSS arrApp dizisinden aktif 3D oyunun anlık FPS değerini okur."""
        h_map = self.kernel32.OpenFileMappingW(FILE_MAP_ALL_ACCESS, False, RTSS_SHARED_MEMORY_NAME)
        if not h_map:
            return 0.0
        p_buf = self.kernel32.MapViewOfFile(h_map, FILE_MAP_ALL_ACCESS, 0, 0, 0)
        if not p_buf:
            self.kernel32.CloseHandle(h_map)
            return 0.0
        active_fps = 0.0
        try:
            dw_signature = ctypes.c_uint32.from_address(p_buf).value
            dw_version = ctypes.c_uint32.from_address(p_buf + 4).value
            if dw_signature == RTSS_SIGNATURE and dw_version >= 0x00020000:
                app_size = ctypes.c_uint32.from_address(p_buf + 8).value
                app_offset = ctypes.c_uint32.from_address(p_buf + 12).value
                app_count = ctypes.c_uint32.from_address(p_buf + 16).value
                for i in range(app_count):
                    ptr = p_buf + app_offset + i * app_size
                    pid = ctypes.c_uint32.from_address(ptr).value
                    if pid:
                        name = ctypes.string_at(ptr + 4, 260).split(b'\x00')[0].decode('latin-1', errors='ignore').lower()
                        if "rtss.exe" in name:
                            continue
                        t0 = ctypes.c_uint32.from_address(ptr + 268).value
                        t1 = ctypes.c_uint32.from_address(ptr + 272).value
                        frames = ctypes.c_uint32.from_address(ptr + 276).value
                        if t1 > t0:
                            fps = 1000.0 * frames / (t1 - t0)
                            if fps > active_fps:
                                active_fps = fps
        finally:
            self.kernel32.UnmapViewOfFile(p_buf)
            self.kernel32.CloseHandle(h_map)
        return active_fps



def _watch_and_clear(pid, app_name):
    """Verilen PID kapanana kadar bekler, sonra OSD slotunu temizler."""
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    SYNCHRONIZE = 0x00100000
    h = k32.OpenProcess(SYNCHRONIZE, False, int(pid))
    if h:
        k32.WaitForSingleObject(h, 0xFFFFFFFF)  # INFINITE
        k32.CloseHandle(h)
    # Süreç yok / kapandı: temizle
    RTSSOverlay(app_name, _watchdog=False).release_osd()


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--watch":
        _watch_and_clear(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "WattCost")
    else:
        overlay = RTSSOverlay()
        print("Resmi SDK protokolü ile OSD test ediliyor...")
        text = "WattCost: 161 W | 0.42 TL/sa\nOturum: 1.25 TL"
        success = overlay.update_osd(text)
        print("Guncelleme Sonucu:", success)
