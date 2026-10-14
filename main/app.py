"""
PC Canlı Elektrik & TL Harcama Takipçisi (AIDA64 Destekli)
UI/UX Pro Max Standartlarında Modern Cyber-Tech Masaüstü Widget'ı
"""
import ctypes
from ctypes import wintypes
import struct
import xml.etree.ElementTree as ET
import re
import time
import json
import os
import sys
import threading
import winreg
import tkinter as tk
from tkinter import ttk, messagebox
import pystray
from PIL import Image, ImageDraw, ImageTk
# Scriptin / Exe'nin bulunduğu klasörü çalışma dizini yap (yolların daima doğru çalışması için)
if getattr(sys, 'frozen', False):
    _app_dir = os.path.dirname(sys.executable)
else:
    _app_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(_app_dir)
from rtss_overlay import RTSSOverlay

# --- Günlük & Aylık Geçmiş Veritabanı Yöneticisi ---
class HistoryManager:
    HISTORY_FILE = "tuketim_gecmisi.json"

    @classmethod
    def load_history(cls):
        if os.path.exists(cls.HISTORY_FILE):
            try:
                with open(cls.HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @classmethod
    def add_energy(cls, wh, price_per_kwh):
        today = time.strftime("%Y-%m-%d")
        history = cls.load_history()
        
        if today not in history:
            history[today] = {
                "wh": 0.0,
                "kwh": 0.0,
                "cost_tl": 0.0,
                "active_seconds": 0
            }
            
        history[today]["wh"] += wh
        history[today]["kwh"] = history[today]["wh"] / 1000.0
        history[today]["cost_tl"] = history[today]["kwh"] * price_per_kwh
        history[today]["active_seconds"] += 1

        try:
            with open(cls.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    @classmethod
    def get_summary(cls):
        history = cls.load_history()
        today = time.strftime("%Y-%m-%d")
        current_month = time.strftime("%Y-%m")
        
        today_tl = history.get(today, {}).get("cost_tl", 0.0)
        today_kwh = history.get(today, {}).get("kwh", 0.0)
        
        month_tl = 0.0
        month_kwh = 0.0
        for date_str, data in history.items():
            if date_str.startswith(current_month):
                month_tl += data.get("cost_tl", 0.0)
                month_kwh += data.get("kwh", 0.0)
                
        return {
            "today_tl": today_tl,
            "today_kwh": today_kwh,
            "month_tl": month_tl,
            "month_kwh": month_kwh,
            "history": history
        }

# --- Windows Başlangıç Yöneticisi ---
class WindowsAutoStart:
    REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "WattCostHaYTooL"

    @classmethod
    def is_enabled(cls):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, cls.APP_NAME)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    @classmethod
    def set_enabled(cls, enable=True):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY, 0, winreg.KEY_SET_VALUE)
            if enable:
                script_path = os.path.abspath("Baslat.bat")
                cmd = f'"{script_path}"'
                winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, cls.APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

# --- Donanım Sensör Okuyucuları (MSI Afterburner & AIDA64) ---
FILE_MAP_READ = 0x0004

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]

class MSIAfterburnerReader:
    """MSI Afterburner (MAHMSharedMemory) Donanım Okuyucusu (RivaTuner ile tam entegre)."""
    SHARED_MEMORY_NAME = "MAHMSharedMemory"

    def __init__(self):
        self.k32 = ctypes.windll.kernel32
        self.k32.OpenFileMappingW.restype = wintypes.HANDLE
        self.k32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        self.k32.MapViewOfFile.restype = wintypes.LPVOID
        self.k32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
        self.k32.UnmapViewOfFile.argtypes = [wintypes.LPCVOID]
        self.k32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.k32.GetTickCount64.restype = ctypes.c_uint64

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        self.k32.GlobalMemoryStatusEx(ctypes.byref(stat))
        self.total_ram_mb = max(1024.0, stat.ullTotalPhys / (1024.0 * 1024.0))

    def read_sensors(self):
        names = [self.SHARED_MEMORY_NAME, f"Global\\{self.SHARED_MEMORY_NAME}"]
        h_map = None
        for name in names:
            h_map = self.k32.OpenFileMappingW(FILE_MAP_READ, False, name)
            if h_map:
                break
        if not h_map:
            return None

        p_buf = self.k32.MapViewOfFile(h_map, FILE_MAP_READ, 0, 0, 0)
        if not p_buf:
            self.k32.CloseHandle(h_map)
            return None

        try:
            sig = ctypes.c_uint32.from_address(p_buf).value
            if sig != 0x4d41484d:  # 'MAHM' imzası
                return None
            header_size = ctypes.c_uint32.from_address(p_buf + 8).value
            entry_count = ctypes.c_uint32.from_address(p_buf + 12).value
            entry_size = ctypes.c_uint32.from_address(p_buf + 16).value

            mahm_raw = {}
            for i in range(entry_count):
                e_ptr = p_buf + header_size + i * entry_size
                raw_e = ctypes.string_at(e_ptr, entry_size)
                name = raw_e[0:260].split(b'\x00')[0].decode('latin-1', 'ignore').strip()
                val = struct.unpack('f', raw_e[1300:1304])[0]
                mahm_raw[name] = val
        except Exception:
            return None
        finally:
            self.k32.UnmapViewOfFile(p_buf)
            self.k32.CloseHandle(h_map)

        cpu_w = mahm_raw.get('CPU power', 0.0)
        gpu_w = mahm_raw.get('Power', 0.0)
        cpu_t = mahm_raw.get('CPU temperature', 0.0)
        gpu_t = mahm_raw.get('GPU temperature', 0.0)
        cpu_u = mahm_raw.get('CPU usage', 0.0)
        gpu_u = mahm_raw.get('GPU usage', 0.0)
        ram_mb = mahm_raw.get('RAM usage', 0.0)
        ram_pct = min(100, int((ram_mb / self.total_ram_mb) * 100))
        cpu_clk = mahm_raw.get('CPU clock', 0.0)
        gpu_clk = mahm_raw.get('GPU clock', 0.0)
        vram_mb = mahm_raw.get('Memory usage', 0.0)
        fan_rpm = mahm_raw.get('Fan tachometer', 0.0)
        if fan_rpm <= 0:
            fan_rpm = mahm_raw.get('Fan speed', 0.0)

        up_sec = int(self.k32.GetTickCount64() / 1000)
        hrs = up_sec // 3600
        mins = (up_sec % 3600) // 60
        secs = up_sec % 60
        uptime_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

        return {
            'PCPUPKG': f"{cpu_w:.2f}",
            'PGPU1': f"{gpu_w:.2f}",
            'TCPU': f"{int(cpu_t)}",
            'TCPUPKG': f"{int(cpu_t)}",
            'TGPU1': f"{int(gpu_t)}",
            'SCPUUTI': f"{int(cpu_u)}",
            'SGPU1UTI': f"{int(gpu_u)}",
            'SUSEDMEM': f"{int(ram_mb)}",
            'SMEMUTI': f"{ram_pct}",
            'CPUCLK': f"{int(cpu_clk)}",
            'GPUCLK': f"{int(gpu_clk)}",
            'VRAMMEM': f"{int(vram_mb)}",
            'FANRPM': f"{int(fan_rpm)}",
            'SUPTIME': uptime_str,
            '_source': 'MSI Afterburner'
        }

class AIDA64Reader:
    """AIDA64 Paylaşımlı Bellek Okuyucusu (XML)."""
    SHARED_MEMORY_NAME = "AIDA64_SensorValues"

    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.kernel32.OpenFileMappingW.restype = wintypes.HANDLE
        self.kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel32.MapViewOfFile.restype = wintypes.LPVOID
        self.kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
        self.kernel32.UnmapViewOfFile.argtypes = [wintypes.LPCVOID]
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    def read_sensors(self):
        names = [self.SHARED_MEMORY_NAME, f"Global\\{self.SHARED_MEMORY_NAME}"]
        h_map = None
        for name in names:
            h_map = self.kernel32.OpenFileMappingW(FILE_MAP_READ, False, name)
            if h_map:
                break
        if not h_map:
            return None
            
        p_buf = self.kernel32.MapViewOfFile(h_map, FILE_MAP_READ, 0, 0, 0)
        if not p_buf:
            self.kernel32.CloseHandle(h_map)
            return None
            
        try:
            raw_bytes = ctypes.string_at(p_buf)
            xml_text = raw_bytes.decode('utf-8', errors='ignore').strip()
        finally:
            self.kernel32.UnmapViewOfFile(p_buf)
            self.kernel32.CloseHandle(h_map)
            
        if not xml_text:
            return None
            
        try:
            root = ET.fromstring(f"<root>{xml_text}</root>")
            sensor_dict = {'_source': 'AIDA64'}
            for child in root:
                sid = child.findtext('id', default='').strip()
                val = child.findtext('value', default='0').strip()
                sensor_dict[sid] = val
            return sensor_dict
        except Exception:
            return None

class UnifiedSensorReader:
    """MSI Afterburner (öncelikli) ve AIDA64 (yedekli) hibrit sensör yöneticisi."""
    def __init__(self):
        self.msi_reader = MSIAfterburnerReader()
        self.aida_reader = AIDA64Reader()

    def read_sensors(self):
        # 1. Önce MSI Afterburner kontrol et (Hızlı, sıfır ek yük, RTSS ile entegre)
        data = self.msi_reader.read_sensors()
        if data:
            return data

        # 2. MSI Afterburner yoksa AIDA64'e başvur
        data = self.aida_reader.read_sensors()
        if data:
            return data

        return None


# --- UI / UX Pro Max Tasarım Sistemi Tokenları ---
THEME = {
    "bg": "#090B11",             # Derin Obsidian
    "card_bg": "#121624",        # Panel Arkaplanı
    "card_border": "#1E263D",    # Zarif Çerçeve
    "card_inner": "#181D30",     # İç Kutu
    "text_primary": "#F1F5F9",   # Yüksek Kontrast Başlık
    "text_secondary": "#94A3B8", # Yardımcı Açıklama
    "text_muted": "#64748B",     # Sönük Metin
    "accent_cyan": "#00E5FF",    # Canlı Güç Rengi
    "accent_green": "#10B981",   # Tasarruf & Saatlik TL
    "accent_amber": "#F59E0B",   # Oturum Maliyeti
    "accent_rose": "#F43F5E",    # Oyun Maliyeti / Yüksek Yük
    "accent_purple": "#8B5CF6",  # Aylık Projeksiyon
    "btn_bg": "#1E263D",
    "btn_hover": "#2B3554",
    "btn_active": "#3B476F",
    "font_family": "Segoe UI",
}


# --- Ana Masaüstü Widget Uygulaması ---
class PowerTrackerApp:
    CONFIG_FILE = "config.json"

    DEFAULT_CONFIG = {
        "kwh_price_tl": 2.60,         # Kocaeli Sepaş ortalama birim fiyat
        "asus_monitor_w": 16.5,       # Asus VP249 144Hz
        "samsung_monitor_w": 19.0,    # Samsung SyncMaster
        "modem_w": 10.0,              # Keenetic Hopper KN-3610
        "asus_mon_active": True,
        "samsung_mon_active": False,
        "modem_active": True,
        "always_on_top": True,
        "close_to_tray": False,       # X ile kapatınca: False ise tamamen çıkar ve RTSS ekranını temizler
        "rtss_enabled": True,
        "tray_mode": "dual_temp",     # dual_temp, cpu_uti, gpu_uti, cpu_temp, gpu_temp, power_w, hourly_tl, logo
        # RTSS OSD Değer Açma/Kapama & Etiket Değiştirme
        "rtss_show_fps": True,
        "rtss_label_fps": "FPS",
        "rtss_color_fps": "#F43F5E",
        "rtss_size_fps": "100",
        "rtss_show_power": True,
        "rtss_label_power": "GUC",
        "rtss_color_power": "#00E5FF",
        "rtss_size_power": "100",
        "rtss_show_hourly": True,
        "rtss_label_hourly": "TUKETIM",
        "rtss_color_hourly": "#10B981",
        "rtss_size_hourly": "100",
        "rtss_show_session": True,
        "rtss_label_session": "OTURUM",
        "rtss_color_session": "#F59E0B",
        "rtss_size_session": "100",
        "rtss_show_today": False,
        "rtss_label_today": "BUGUN",
        "rtss_color_today": "#A855F7",
        "rtss_size_today": "100",
        "rtss_show_month": False,
        "rtss_label_month": "AY",
        "rtss_color_month": "#EC4899",
        "rtss_size_month": "100",
        "rtss_show_cpu": False,
        "rtss_label_cpu": "CPU",
        "rtss_color_cpu": "#F59E0B",
        "rtss_size_cpu": "100",
        "rtss_show_cpu_w": False,
        "rtss_label_cpu_w": "CPU-W",
        "rtss_color_cpu_w": "#F59E0B",
        "rtss_size_cpu_w": "100",
        "rtss_show_cpu_clk": False,
        "rtss_label_cpu_clk": "CPU-CLK",
        "rtss_color_cpu_clk": "#FCD34D",
        "rtss_size_cpu_clk": "100",
        "rtss_show_gpu": False,
        "rtss_label_gpu": "GPU",
        "rtss_color_gpu": "#00E5FF",
        "rtss_size_gpu": "100",
        "rtss_show_gpu_w": False,
        "rtss_label_gpu_w": "GPU-W",
        "rtss_color_gpu_w": "#00E5FF",
        "rtss_size_gpu_w": "100",
        "rtss_show_gpu_clk": False,
        "rtss_label_gpu_clk": "GPU-CLK",
        "rtss_color_gpu_clk": "#38BDF8",
        "rtss_size_gpu_clk": "100",
        "rtss_show_vram": False,
        "rtss_label_vram": "VRAM",
        "rtss_color_vram": "#818CF8",
        "rtss_size_vram": "100",
        "rtss_show_ram": False,
        "rtss_label_ram": "RAM",
        "rtss_color_ram": "#A855F7",
        "rtss_size_ram": "100",
        "rtss_show_fan": False,
        "rtss_label_fan": "FAN",
        "rtss_color_fan": "#34D399",
        "rtss_size_fan": "100",
        "rtss_show_kwh": True,
        "rtss_multiline": True,
        "ui_tab": "genel"
    }

    def __init__(self, root):
        self.root = root
        self.root.title("WattCost HaYTooL • PC Güç & TL Monitörü")
        self.root.geometry("400x720")
        self.root.minsize(390, 690)
        self.root.resizable(True, True)
        self.root.configure(bg=THEME["bg"])

        # Pencere İkonunu Ayarla (Yeni Logo: bewicon.png & app_icon.ico)
        try:
            if os.path.exists("app_icon.ico"):
                self.root.iconbitmap("app_icon.ico")
            icon_file = "bewicon.png" if os.path.exists("bewicon.png") else "app_icon.png"
            if os.path.exists(icon_file):
                img_ico = ImageTk.PhotoImage(file=icon_file)
                self.root.iconphoto(False, img_ico)
                self._app_icon_ref = img_ico
        except Exception:
            pass

        # X butonuna basınca (Varsayılan: Temiz Çıkış ve Ekranı Temizleme)
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close_clicked)

        self.reader = UnifiedSensorReader()
        self.rtss = RTSSOverlay()
        self.load_config()

        # Oturum istatistikleri
        self.session_start = time.time()
        self.last_update = time.time()
        self.total_energy_wh = 0.0

        # UI Değişkenleri
        self.asus_var = tk.BooleanVar(value=self.config.get("asus_mon_active", True))
        self.samsung_var = tk.BooleanVar(value=self.config.get("samsung_mon_active", False))
        self.modem_var = tk.BooleanVar(value=self.config.get("modem_active", True))
        self.on_top_var = tk.BooleanVar(value=self.config.get("always_on_top", True))

        self.apply_always_on_top()
        self.build_ui()
        self.init_tray_icon()
        self.update_loop()

    def get_tray_fonts(self):
        if not hasattr(self, '_tray_fonts'):
            font_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'segoeuib.ttf')
            if not os.path.exists(font_path):
                font_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arialbd.ttf')
            try:
                self._tray_fonts = (
                    ImageFont.truetype(font_path, 26),  # Büyük tekil değer (%75, 45°)
                    ImageFont.truetype(font_path, 20),  # Orta değer (240W, 1.8₺, C45°)
                    ImageFont.truetype(font_path, 13)   # Küçük etiket (CPU, GPU, WATT)
                )
            except Exception:
                f_def = ImageFont.load_default()
                self._tray_fonts = (f_def, f_def, f_def)
        return self._tray_fonts

    def set_tray_mode(self, mode):
        self.config["tray_mode"] = mode
        self.save_config()
        if hasattr(self, 'tray_icon') and self.tray_icon:
            hw = getattr(self, "_last_hw", {})
            self.tray_icon.icon = self.create_tray_image(
                watt=getattr(self, "_last_watt", 0),
                cpu_temp=hw.get("cpu_temp", 0),
                gpu_temp=hw.get("gpu_temp", 0),
                cpu_uti=hw.get("cpu_uti", 0),
                gpu_uti=hw.get("gpu_uti", 0),
                hourly_tl=getattr(self, "_last_hourly", 0.0)
            )

    def create_tray_image(self, watt=0, cpu_temp=0, gpu_temp=0, cpu_uti=0, gpu_uti=0, hourly_tl=0.0):
        mode = self.config.get("tray_mode", "dual_temp")

        # Sabit Logo Modu
        if mode == "logo":
            logo_p = "bewicon.png" if os.path.exists("bewicon.png") else "app_icon.png"
            if os.path.exists(logo_p):
                try:
                    return Image.open(logo_p).convert('RGBA').resize((64, 64), Image.Resampling.LANCZOS)
                except Exception:
                    pass

        img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        f_lg, f_md, f_sm = self.get_tray_fonts()

        # Alarm ve arka plan çerçeve rengini belirle
        outline_color = (16, 185, 129, 255)  # Canlı Yeşil (varsayılan)

        if mode in ("cpu_uti", "gpu_uti"):
            val = cpu_uti if mode == "cpu_uti" else gpu_uti
            lbl = "CPU" if mode == "cpu_uti" else "GPU"
            lbl_color = (245, 158, 11, 255) if mode == "cpu_uti" else (0, 229, 255, 255)

            if val >= 80:
                outline_color = (244, 63, 94, 255)   # Kırmızı
            elif val >= 50:
                outline_color = (245, 158, 11, 255)  # Sarı
            else:
                outline_color = (16, 185, 129, 255)  # Yeşil

            draw.rounded_rectangle([1, 1, 62, 62], radius=10, fill=(11, 15, 25, 250), outline=outline_color, width=2)
            draw.text((10, 4), lbl, fill=lbl_color, font=f_sm)
            draw.text((6, 23), f"%{int(val)}", fill=(241, 245, 249, 255), font=f_lg)

        elif mode in ("cpu_temp", "gpu_temp"):
            temp = cpu_temp if mode == "cpu_temp" else gpu_temp
            lbl = "CPU" if mode == "cpu_temp" else "GPU"
            lbl_color = (192, 132, 252, 255) if mode == "cpu_temp" else (0, 229, 255, 255)

            if temp >= 80:
                outline_color = (244, 63, 94, 255)
            elif temp >= 70:
                outline_color = (245, 158, 11, 255)
            else:
                outline_color = (16, 185, 129, 255)

            draw.rounded_rectangle([1, 1, 62, 62], radius=10, fill=(11, 15, 25, 250), outline=outline_color, width=2)
            draw.text((10, 4), lbl, fill=lbl_color, font=f_sm)
            draw.text((8, 23), f"{int(temp)}°", fill=(241, 245, 249, 255), font=f_lg)

        elif mode == "power_w":
            if watt >= 350:
                outline_color = (244, 63, 94, 255)
            elif watt >= 200:
                outline_color = (0, 229, 255, 255)
            else:
                outline_color = (16, 185, 129, 255)

            draw.rounded_rectangle([1, 1, 62, 62], radius=10, fill=(11, 15, 25, 250), outline=outline_color, width=2)
            draw.text((10, 4), "WATT", fill=(0, 229, 255, 255), font=f_sm)
            draw.text((4, 25), f"{int(watt)}W", fill=(241, 245, 249, 255), font=f_md)

        elif mode == "hourly_tl":
            outline_color = (16, 185, 129, 255)
            draw.rounded_rectangle([1, 1, 62, 62], radius=10, fill=(11, 15, 25, 250), outline=outline_color, width=2)
            draw.text((12, 4), "TL/SA", fill=(16, 185, 129, 255), font=f_sm)
            draw.text((4, 25), f"{hourly_tl:.1f}₺", fill=(241, 245, 249, 255), font=f_md)

        else: # "dual_temp" (Klasik CPU & GPU iki satır)
            if cpu_temp >= 80 or gpu_temp >= 80 or watt > 480:
                outline_color = (244, 63, 94, 255)
            elif watt > 260:
                outline_color = (0, 229, 255, 255)
            else:
                outline_color = (16, 185, 129, 255)

            draw.rounded_rectangle([1, 1, 62, 62], radius=10, fill=(11, 15, 25, 250), outline=outline_color, width=2)
            c_val_str = f"{int(cpu_temp)}°"
            draw.text((4, 5), "C", fill=(192, 132, 252, 255), font=f_sm)
            draw.text((20, 4), c_val_str, fill=(241, 245, 249, 255), font=f_md)

            g_val_str = f"{int(gpu_temp)}°"
            draw.text((4, 33), "G", fill=(0, 229, 255, 255), font=f_sm)
            draw.text((20, 32), g_val_str, fill=(241, 245, 249, 255), font=f_md)

        return img

    def init_tray_icon(self):
        self.tray_watt_str = "⚡ Anlık Güç: --- W"
        self.tray_temp_str = "🌡️ Sıcaklık: CPU --°C | GPU --°C"
        self.tray_hourly_str = "₺ Saatlik: 0.00 TL/sa"

        icon_img = self.create_tray_image(0, 0, 0)
        
        # Dinamik Tray Menüsü (Sağ tıkta canlı değerler ve gösterge seçimi)
        menu = pystray.Menu(
            pystray.MenuItem(lambda item: self.tray_watt_str, lambda: None, enabled=False),
            pystray.MenuItem(lambda item: self.tray_temp_str, lambda: None, enabled=False),
            pystray.MenuItem(lambda item: self.tray_hourly_str, lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📌 Saatteki Gösterge (Tray)", pystray.Menu(
                pystray.MenuItem("CPU Kullanımı (%)", lambda: self.set_tray_mode("cpu_uti"), checked=lambda item: self.config.get("tray_mode") == "cpu_uti"),
                pystray.MenuItem("GPU Kullanımı (%)", lambda: self.set_tray_mode("gpu_uti"), checked=lambda item: self.config.get("tray_mode") == "gpu_uti"),
                pystray.MenuItem("CPU & GPU Sıcaklığı (°C)", lambda: self.set_tray_mode("dual_temp"), checked=lambda item: self.config.get("tray_mode", "dual_temp") == "dual_temp"),
                pystray.MenuItem("CPU Sıcaklığı (°C)", lambda: self.set_tray_mode("cpu_temp"), checked=lambda item: self.config.get("tray_mode") == "cpu_temp"),
                pystray.MenuItem("GPU Sıcaklığı (°C)", lambda: self.set_tray_mode("gpu_temp"), checked=lambda item: self.config.get("tray_mode") == "gpu_temp"),
                pystray.MenuItem("Prizden Toplam Güç (Watt)", lambda: self.set_tray_mode("power_w"), checked=lambda item: self.config.get("tray_mode") == "power_w"),
                pystray.MenuItem("Saatlik Harcama (TL/sa)", lambda: self.set_tray_mode("hourly_tl"), checked=lambda item: self.config.get("tray_mode") == "hourly_tl"),
                pystray.MenuItem("Sabit Logo (WattCost)", lambda: self.set_tray_mode("logo"), checked=lambda item: self.config.get("tray_mode") == "logo"),
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Pencereyi Göster / Gizle", self.toggle_window, default=True),
            pystray.MenuItem("Oturumu Sıfırla", lambda: self.root.after(0, self.reset_session)),
            pystray.MenuItem("🧹 Ekrandaki Metni Temizle", lambda: self.rtss.release_osd() if hasattr(self, 'rtss') and self.rtss else None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Tamamen Çıkış", self.quit_app)
        )
        self.tray_icon = pystray.Icon("wattcost_haytool", icon_img, "WattCost HaYTooL • PC Güç & Derece Monitörü", menu)
        
        # Ayrı iş parçacığında çalıştır
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def on_window_close_clicked(self):
        # X butonuna basılınca
        if self.config.get("close_to_tray", False):
            self.hide_to_tray()
        else:
            self.quit_app()

    def hide_to_tray(self):
        self.root.withdraw()

    def show_from_tray(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def toggle_window(self):
        if self.root.winfo_viewable():
            self.root.after(0, self.hide_to_tray)
        else:
            self.root.after(0, self.show_from_tray)

    def quit_app(self):
        try:
            if hasattr(self, 'rtss') and self.rtss:
                self.rtss.release_osd()
        except Exception:
            pass
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass
        import os
        os._exit(0)

    def load_config(self):
        self.config = self.DEFAULT_CONFIG.copy()
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.config.update(saved)
            except Exception:
                pass

    def save_config(self):
        self.config["asus_mon_active"] = self.asus_var.get()
        self.config["samsung_mon_active"] = self.samsung_var.get()
        self.config["modem_active"] = self.modem_var.get()
        self.config["always_on_top"] = self.on_top_var.get()
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def apply_always_on_top(self):
        self.root.attributes("-topmost", self.on_top_var.get())

    def toggle_always_on_top(self):
        self.apply_always_on_top()
        self.save_config()

    def create_card(self, parent, pady=(0, 6)):
        frame = tk.Frame(parent, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
        frame.pack(fill="x", padx=12, pady=pady)
        return frame

    # ------------------------------------------------------------------ UI yardımcıları
    # 5 Kafa Renk Paleti (Mor, Cyan, Yeşil, Kırmızı, Sarı + Beyaz)
    RTSS_PALETTE = [
        ("Mor",     "#A855F7"),  # Kesin olması istenen ana MOR
        ("Cyan",    "#00E5FF"),  # Neon Buz Mavisi
        ("Yeşil",   "#10B981"),  # Tüketim & Enerji Yeşili
        ("Kırmızı", "#F43F5E"),  # Rose / FPS Kırmızısı
        ("Sarı",    "#F59E0B"),  # Amber / Altın Sarısı
        ("Beyaz",   "#FFFFFF"),  # Standart Beyaz
    ]

    RTSS_ROWS = [
        # (show_key, label_key, color_key, size_key, title, def_color, def_size, def_label, def_active)
        ("rtss_show_fps",       "rtss_label_fps",       "rtss_color_fps",       "rtss_size_fps",       "Anlık FPS",                 "#F43F5E", "100", "FPS",     True),
        ("rtss_show_power",     "rtss_label_power",     "rtss_color_power",     "rtss_size_power",     "Prizden Güç (Toplam W)",    "#00E5FF", "100", "GUC",     True),
        ("rtss_show_hourly",    "rtss_label_hourly",    "rtss_color_hourly",    "rtss_size_hourly",    "Saatlik Harcama (TL/sa)",   "#10B981", "100", "TUKETIM", True),
        ("rtss_show_session",   "rtss_label_session",   "rtss_color_session",   "rtss_size_session",   "Oturum Tutarı (TL)",        "#F59E0B", "100", "OTURUM",  True),
        ("rtss_show_today",     "rtss_label_today",     "rtss_color_today",     "rtss_size_today",     "Bugünkü Toplam (TL)",       "#A855F7", "100", "BUGUN",   False),
        ("rtss_show_month",     "rtss_label_month",     "rtss_color_month",     "rtss_size_month",     "Bu Ayki Fatura (TL)",       "#EC4899", "100", "AY",      False),
        ("rtss_show_cpu",       "rtss_label_cpu",       "rtss_color_cpu",       "rtss_size_cpu",       "İşlemci (CPU % ve °C)",     "#F59E0B", "100", "CPU",     False),
        ("rtss_show_cpu_w",     "rtss_label_cpu_w",     "rtss_color_cpu_w",     "rtss_size_cpu_w",     "İşlemci Gücü (CPU Watt)",   "#F59E0B", "100", "CPU-W",   False),
        ("rtss_show_cpu_clk",   "rtss_label_cpu_clk",   "rtss_color_cpu_clk",   "rtss_size_cpu_clk",   "İşlemci Hızı (CPU MHz)",    "#FCD34D", "100", "CPU-CLK", False),
        ("rtss_show_gpu",       "rtss_label_gpu",       "rtss_color_gpu",       "rtss_size_gpu",       "Ekran Kartı (GPU % ve °C)", "#00E5FF", "100", "GPU",     False),
        ("rtss_show_gpu_w",     "rtss_label_gpu_w",     "rtss_color_gpu_w",     "rtss_size_gpu_w",     "Ekran Kartı Gücü (GPU Watt)","#00E5FF", "100", "GPU-W",   False),
        ("rtss_show_gpu_clk",   "rtss_label_gpu_clk",   "rtss_color_gpu_clk",   "rtss_size_gpu_clk",   "Ekran Kartı Hızı (GPU MHz)","#38BDF8", "100", "GPU-CLK", False),
        ("rtss_show_vram",      "rtss_label_vram",      "rtss_color_vram",      "rtss_size_vram",      "Ekran Kartı VRAM (GB)",     "#818CF8", "100", "VRAM",    False),
        ("rtss_show_ram",       "rtss_label_ram",       "rtss_color_ram",       "rtss_size_ram",       "Sistem Belleği (RAM %)",    "#A855F7", "100", "RAM",     False),
        ("rtss_show_fan",       "rtss_label_fan",       "rtss_color_fan",       "rtss_size_fan",       "Fan Devri (RPM)",           "#34D399", "100", "FAN",     False),
    ]

    def make_btn(self, parent, text, command, fg=None, bg=None, padx=8, pady=3):
        bg = bg or THEME["btn_bg"]
        btn = tk.Button(parent, text=text, command=command, font=(THEME["font_family"], 8, "bold"),
                        bg=bg, fg=fg or THEME["text_secondary"], activebackground=THEME["btn_hover"],
                        activeforeground=THEME["text_primary"], relief="flat", bd=0,
                        padx=padx, pady=pady, cursor="hand2")
        btn.bind("<Enter>", lambda e: btn.config(bg=THEME["btn_hover"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def make_check(self, parent, text, var, command, fg=None, bold=False, bg=None):
        bg = bg or THEME["card_bg"]
        return tk.Checkbutton(parent, text=text, variable=var, command=command,
                              font=(THEME["font_family"], 8, "bold" if bold else "normal"),
                              fg=fg or THEME["text_secondary"], bg=bg, selectcolor=THEME["card_inner"],
                              activebackground=bg, activeforeground=THEME["text_primary"],
                              bd=0, highlightthickness=0, cursor="hand2")

    def make_card_title(self, card, text, color, right_widget_factory=None):
        row = tk.Frame(card, bg=THEME["card_bg"])
        row.pack(fill="x", padx=12, pady=(8, 2))
        lbl = tk.Label(row, text=text, font=(THEME["font_family"], 7, "bold"),
                       fg=color, bg=THEME["card_bg"])
        lbl.pack(side="left")
        if right_widget_factory:
            right_widget_factory(row)
        return lbl

    # ------------------------------------------------------------------ Ana ekran
    def build_ui(self):
        f_font = THEME["font_family"]

        # --- 1. ÜST HEADER BAR ---
        header = tk.Frame(self.root, bg=THEME["bg"])
        header.pack(fill="x", padx=14, pady=(10, 6))

        f_brand = tk.Frame(header, bg=THEME["bg"])
        f_brand.pack(side="left")

        # Yeni Logo Gösterimi (bewicon.png)
        logo_loaded = False
        icon_file = "bewicon.png" if os.path.exists("bewicon.png") else "app_icon.png"
        if os.path.exists(icon_file):
            try:
                raw_logo = Image.open(icon_file).resize((26, 26), Image.Resampling.LANCZOS)
                self.img_brand_logo = ImageTk.PhotoImage(raw_logo)
                lbl_logo = tk.Label(f_brand, image=self.img_brand_logo, bg=THEME["bg"])
                lbl_logo.pack(side="left", padx=(0, 7))
                logo_loaded = True
            except Exception:
                pass
        if not logo_loaded:
            tk.Label(f_brand, text="₺", font=(f_font, 15, "bold"), fg=THEME["accent_amber"],
                     bg=THEME["bg"]).pack(side="left", padx=(0, 5))

        f_title = tk.Frame(f_brand, bg=THEME["bg"])
        f_title.pack(side="left")
        tk.Label(f_title, text="WATTCOST", font=(f_font, 10, "bold"),
                 fg=THEME["text_primary"], bg=THEME["bg"]).pack(anchor="w")
        tk.Label(f_title, text="HaYTooL • PC Güç & TL Monitörü", font=(f_font, 7),
                 fg=THEME["text_muted"], bg=THEME["bg"]).pack(anchor="w")

        f_actions = tk.Frame(header, bg=THEME["bg"])
        f_actions.pack(side="right")
        self.make_btn(f_actions, "⚙", self.open_settings, padx=8).pack(side="right", padx=(4, 0))
        self.make_btn(f_actions, "📥", self.hide_to_tray, fg=THEME["text_muted"], padx=8).pack(side="right", padx=(4, 0))
        self.make_btn(f_actions, "📊", self.open_history_report, fg="#38BDF8", padx=8).pack(side="right", padx=(4, 0))
        self.make_check(f_actions, "Sabitle", self.on_top_var, self.toggle_always_on_top,
                        bg=THEME["bg"]).pack(side="right", padx=(0, 4))

        # --- 6. ALT DURUM ÇUBUĞU (bottom: önce paketlenmeli) ---
        self.lbl_status = tk.Label(self.root, text="● AIDA64 Bağlı (1 Hz Canlı Veri)", font=(f_font, 7, "bold"),
                                   fg=THEME["accent_green"], bg=THEME["bg"])
        self.lbl_status.pack(side="bottom", fill="x", pady=(2, 4))

        # --- 2. ANA GÜÇ & PROJEKSİYON KARTI (her zaman görünür) ---
        card_power = self.create_card(self.root, pady=(0, 8))
        tk.Frame(card_power, bg=THEME["accent_cyan"], height=2).pack(fill="x")

        tk.Label(card_power, text="PRIZDEN ÇEKİLEN ANLIK GÜÇ", font=(f_font, 7, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w", padx=14, pady=(8, 0))

        f_val_row = tk.Frame(card_power, bg=THEME["card_bg"])
        f_val_row.pack(fill="x", padx=14, pady=(0, 6))
        self.lbl_power = tk.Label(f_val_row, text="--- W", font=(f_font, 28, "bold"),
                                  fg=THEME["accent_cyan"], bg=THEME["card_bg"])
        self.lbl_power.pack(side="left")
        self.lbl_power_status = tk.Label(f_val_row, text="• KARARLI", font=(f_font, 8, "bold"),
                                         fg=THEME["text_muted"], bg=THEME["card_bg"])
        self.lbl_power_status.pack(side="right", pady=(12, 0))

        f_rates = tk.Frame(card_power, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_rates.pack(fill="x", padx=12, pady=(2, 10))

        def rate_col(title, color, attr, last=False):
            col = tk.Frame(f_rates, bg=THEME["card_inner"])
            col.pack(side="left", expand=True, fill="both", pady=6)
            tk.Label(col, text=title, font=(f_font, 7, "bold"), fg=THEME["text_muted"], bg=THEME["card_inner"]).pack()
            lbl = tk.Label(col, text="0.00 TL", font=(f_font, 11, "bold"), fg=color, bg=THEME["card_inner"])
            lbl.pack()
            setattr(self, attr, lbl)
            if not last:
                tk.Frame(f_rates, bg=THEME["card_border"], width=1).pack(side="left", fill="y", pady=3)

        rate_col("SAATLİK TL", THEME["accent_green"], "lbl_rate_hour")
        rate_col("GÜNLÜK", "#38BDF8", "lbl_rate_day")
        rate_col("AYLIK (30G)", THEME["accent_purple"], "lbl_rate_month", last=True)

        # --- SEKME ÇUBUĞU ---
        f_tabbar = tk.Frame(self.root, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_tabbar.pack(fill="x", padx=12, pady=(0, 8))
        self.tab_buttons = {}
        for key, label in (("genel", "📈 Genel"), ("oyun", "🎮 Oyun Göstergesi"), ("cihaz", "🔌 Cihazlar")):
            b = tk.Button(f_tabbar, text=label, font=(f_font, 8, "bold"), relief="flat", bd=0, cursor="hand2",
                          pady=5, command=lambda k=key: self.show_tab(k))
            b.pack(side="left", expand=True, fill="x", padx=2, pady=2)
            self.tab_buttons[key] = b

        self.tab_body = tk.Frame(self.root, bg=THEME["bg"])
        self.tab_body.pack(fill="both", expand=True)
        self.tab_frames = {k: tk.Frame(self.tab_body, bg=THEME["bg"]) for k in self.tab_buttons}

        self.build_tab_genel(self.tab_frames["genel"])
        self.build_rtss_panel(self.tab_frames["oyun"])
        self.build_tab_cihaz(self.tab_frames["cihaz"])

        self.show_tab(self.config.get("ui_tab", "genel"))

    def show_tab(self, key):
        if key not in self.tab_frames:
            key = "genel"
        for fr in self.tab_frames.values():
            fr.pack_forget()
        self.tab_frames[key].pack(fill="both", expand=True)
        for k, b in self.tab_buttons.items():
            if k == key:
                b.config(bg="#2563EB", fg="#FFFFFF", activebackground="#1D4ED8", activeforeground="#FFFFFF")
            else:
                b.config(bg=THEME["card_inner"], fg=THEME["text_secondary"],
                         activebackground=THEME["btn_hover"], activeforeground=THEME["text_primary"])
        if self.config.get("ui_tab") != key:
            self.config["ui_tab"] = key
            self.save_config()

    # --- Sekme: Genel ---
    def build_tab_genel(self, parent):
        f_font = THEME["font_family"]

        card_session = self.create_card(parent, pady=(0, 8))
        self.make_card_title(card_session, "BU OTURUMDA HARCANAN", THEME["accent_amber"])

        f_cost_row = tk.Frame(card_session, bg=THEME["card_bg"])
        f_cost_row.pack(fill="x", padx=14, pady=(0, 4))
        self.lbl_cost = tk.Label(f_cost_row, text="0.00 TL", font=(f_font, 20, "bold"),
                                 fg=THEME["accent_amber"], bg=THEME["card_bg"])
        self.lbl_cost.pack(side="left")
        self.make_btn(f_cost_row, "↺ Sıfırla", self.reset_session, fg=THEME["text_primary"],
                      bg=THEME["card_inner"]).pack(side="right")

        f_details = tk.Frame(card_session, bg=THEME["card_bg"])
        f_details.pack(fill="x", padx=14, pady=(0, 6))
        self.lbl_kwh = tk.Label(f_details, text="Tüketim: 0.000 kWh", font=(f_font, 8),
                                fg=THEME["text_secondary"], bg=THEME["card_bg"])
        self.lbl_kwh.pack(side="left")
        self.lbl_time = tk.Label(f_details, text="Oturum: 00:00:00", font=(f_font, 8),
                                 fg=THEME["text_muted"], bg=THEME["card_bg"])
        self.lbl_time.pack(side="right")

        f_up_box = tk.Frame(card_session, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_up_box.pack(fill="x", padx=12, pady=(2, 10))
        self.lbl_pc_uptime = tk.Label(f_up_box, text="🖥 PC Açık Kalma: --:--:--", font=(f_font, 8, "bold"),
                                      fg=THEME["text_secondary"], bg=THEME["card_inner"])
        self.lbl_pc_uptime.pack(anchor="w", padx=10, pady=(5, 2))
        f_up_compare = tk.Frame(f_up_box, bg=THEME["card_inner"])
        f_up_compare.pack(fill="x", padx=10, pady=(0, 5))
        self.lbl_saver_est = tk.Label(f_up_compare, text="🌱 Tasarruf: 0.00 TL", font=(f_font, 8, "bold"),
                                      fg=THEME["accent_green"], bg=THEME["card_inner"])
        self.lbl_saver_est.pack(side="left")
        tk.Label(f_up_compare, text="•", font=(f_font, 8), fg=THEME["text_muted"],
                 bg=THEME["card_inner"]).pack(side="left", padx=5)
        self.lbl_game_est = tk.Label(f_up_compare, text="🎮 Oyunda: 0.00 TL", font=(f_font, 8, "bold"),
                                     fg=THEME["accent_rose"], bg=THEME["card_inner"])
        self.lbl_game_est.pack(side="left")

        card_hw = self.create_card(parent, pady=(0, 4))
        self.lbl_hw_title = self.make_card_title(card_hw, "CANLI DONANIM & SENSÖRLER (MSI Afterburner)", THEME["accent_purple"])
        hw_rows = (
            ("CPU (Ryzen 5800X):", "lbl_cpu", (1, 1)),
            ("GPU (RTX 4060 Ti):", "lbl_gpu", (1, 1)),
            ("RAM Kullanımı:",     "lbl_ram", (1, 6)),
        )
        for text, attr, pad in hw_rows:
            r = tk.Frame(card_hw, bg=THEME["card_bg"])
            r.pack(fill="x", padx=12, pady=pad)
            tk.Label(r, text=text, font=(f_font, 8), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")
            lbl = tk.Label(r, text="--", font=(f_font, 8, "bold"), fg=THEME["text_primary"], bg=THEME["card_bg"])
            lbl.pack(side="right")
            setattr(self, attr, lbl)

    # --- Sekme: Cihazlar ---
    def build_tab_cihaz(self, parent):
        f_font = THEME["font_family"]
        card = self.create_card(parent, pady=(0, 6))
        self.make_card_title(card, "PRİZE BAĞLI CİHAZ PROFİLİ", THEME["accent_cyan"])
        self.dev_w_labels = []
        devices = (
            (self.asus_var, "Asus VP249 (144Hz IPS)", "asus_monitor_w", 16.5),
            (self.samsung_var, "Samsung 2. Monitör (22\")", "samsung_monitor_w", 19.0),
            (self.modem_var, "Keenetic Hopper Modem", "modem_w", 10.0),
        )
        for var, name, key, default in devices:
            row = tk.Frame(card, bg=THEME["card_bg"])
            row.pack(fill="x", padx=12, pady=3)
            self.make_check(row, name, var, self.save_config, fg=THEME["text_primary"]).pack(side="left")
            lbl = tk.Label(row, text="", font=(f_font, 8, "bold"), fg=THEME["accent_amber"], bg=THEME["card_bg"])
            lbl.pack(side="right")
            self.dev_w_labels.append((lbl, key, default))
        tk.Label(card, text="İşaretli cihazların gücü, kasa tüketimine eklenerek prizden çekilen toplam hesaplanır.\n"
                            "Watt değerlerini ⚙ Ayarlar'dan değiştirebilirsiniz.",
                 font=(f_font, 7), fg=THEME["text_muted"], bg=THEME["card_bg"], justify="left",
                 wraplength=340).pack(anchor="w", padx=12, pady=(4, 10))
        self.refresh_device_labels()

    def refresh_device_labels(self):
        for lbl, key, default in getattr(self, "dev_w_labels", []):
            try:
                lbl.config(text=f"{float(self.config.get(key, default)):.1f} W")
            except Exception:
                pass

    # --- Sekme: Oyun İçi Gösterge (RTSS) ---
    def build_rtss_panel(self, parent):
        f_font = THEME["font_family"]
        cfg = self.config

        card = self.create_card(parent, pady=(0, 6))

        # Ana anahtarlar
        f_top = tk.Frame(card, bg=THEME["card_bg"])
        f_top.pack(fill="x", padx=12, pady=(8, 2))
        self.rtss_enabled_var = tk.BooleanVar(value=cfg.get("rtss_enabled", True))
        self.make_check(f_top, "Oyun içi göstergeyi aç (RTSS)", self.rtss_enabled_var,
                        self.on_rtss_change, fg=THEME["accent_cyan"], bold=True).pack(side="left")
        self.rtss_multiline_var = tk.BooleanVar(value=cfg.get("rtss_multiline", True))
        self.make_check(f_top, "2 satır", self.rtss_multiline_var, self.on_rtss_change).pack(side="right")

        tk.Frame(card, bg=THEME["card_border"], height=1).pack(fill="x", padx=12, pady=(4, 4))

        head = tk.Frame(card, bg=THEME["card_bg"])
        head.pack(fill="x", padx=12, pady=(2, 4))
        tk.Label(head, text="GÖSTERİLECEK DEĞER", font=(f_font, 7, "bold"), fg=THEME["text_muted"],
                 bg=THEME["card_bg"]).pack(side="left")

        f_hdr_r = tk.Frame(head, bg=THEME["card_bg"])
        f_hdr_r.pack(side="right")
        tk.Label(f_hdr_r, text="BAŞLIK", font=(f_font, 7, "bold"), fg=THEME["text_muted"],
                 bg=THEME["card_bg"], width=8).pack(side="left", padx=2)
        tk.Label(f_hdr_r, text="BOYUT", font=(f_font, 7, "bold"), fg=THEME["text_muted"],
                 bg=THEME["card_bg"], width=4).pack(side="left", padx=2)
        tk.Label(f_hdr_r, text="RENK", font=(f_font, 7, "bold"), fg=THEME["text_muted"],
                 bg=THEME["card_bg"], width=3).pack(side="left", padx=2)

        # Kaydırılabilir Sensör Listesi
        f_scroll_box = tk.Frame(card, bg=THEME["card_bg"])
        f_scroll_box.pack(fill="x", padx=6, pady=(0, 4))

        canvas = tk.Canvas(f_scroll_box, bg=THEME["card_bg"], highlightthickness=0, height=200)
        v_bar = tk.Scrollbar(f_scroll_box, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=v_bar.set)

        rows_container = tk.Frame(canvas, bg=THEME["card_bg"])
        rows_win = canvas.create_window((0, 0), window=rows_container, anchor="nw")

        def _on_cfg(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        rows_container.bind("<Configure>", _on_cfg)

        def _on_c_cfg(e):
            canvas.itemconfig(rows_win, width=e.width)
        canvas.bind("<Configure>", _on_c_cfg)

        def _on_wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        
        rows_container.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_wheel))
        rows_container.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        canvas.pack(side="left", fill="both", expand=True)
        v_bar.pack(side="right", fill="y")

        self.rtss_vars = {}
        self.rtss_entries = {}
        self.rtss_size_entries = {}
        self.rtss_color_btns = {}
        self.rtss_colors = {}

        for show_key, label_key, color_key, size_key, title, def_color, def_size, def_label, def_active in self.RTSS_ROWS:
            row = tk.Frame(rows_container, bg=THEME["card_bg"])
            row.pack(fill="x", padx=6, pady=1)

            var = tk.BooleanVar(value=cfg.get(show_key, def_active))
            self.rtss_vars[show_key] = var
            self.make_check(row, title, var, self.on_rtss_change, fg=THEME["text_primary"]).pack(side="left")

            f_ctrl = tk.Frame(row, bg=THEME["card_bg"])
            f_ctrl.pack(side="right")

            cur_color = str(cfg.get(color_key, def_color))
            self.rtss_colors[color_key] = cur_color

            # 1. Başlık Kutusu
            ent_lbl = tk.Entry(f_ctrl, width=8, font=(f_font, 8, "bold"), bg=THEME["card_inner"], fg=cur_color,
                               insertbackground=THEME["text_primary"], relief="flat", justify="center",
                               highlightbackground=THEME["card_border"], highlightcolor=cur_color,
                               highlightthickness=1)
            ent_lbl.insert(0, str(cfg.get(label_key, def_label)))
            ent_lbl.pack(side="left", padx=2, ipady=1)
            ent_lbl.bind("<KeyRelease>", self.on_rtss_change)
            self.rtss_entries[label_key] = ent_lbl

            # 2. Metin Boyutu Kutusu (yazarak değiştirilebilir, örn: 100, 120, 80)
            ent_sz = tk.Entry(f_ctrl, width=4, font=(f_font, 8, "bold"), bg=THEME["card_inner"], fg=THEME["text_primary"],
                              insertbackground=THEME["text_primary"], relief="flat", justify="center",
                              highlightbackground=THEME["card_border"], highlightcolor=THEME["accent_cyan"],
                              highlightthickness=1)
            ent_sz.insert(0, str(cfg.get(size_key, def_size)))
            ent_sz.pack(side="left", padx=2, ipady=1)
            ent_sz.bind("<KeyRelease>", self.on_rtss_change)
            self.rtss_size_entries[size_key] = ent_sz

            # 3. Renk Butonu (Tıklayınca 5 kafa renk menüsü açılır)
            btn_col = tk.Button(f_ctrl, text="■", font=(f_font, 9, "bold"), bg=THEME["card_inner"], fg=cur_color,
                                activebackground=THEME["btn_hover"], activeforeground=cur_color,
                                relief="flat", bd=0, width=3, cursor="hand2")
            btn_col.pack(side="left", padx=2, ipady=1)

            def make_color_cmd(c_key=color_key, b=btn_col, e=ent_lbl):
                return lambda: self.open_color_picker_menu(b, c_key, e)

            btn_col.config(command=make_color_cmd())
            self.rtss_color_btns[color_key] = btn_col

            if show_key == "rtss_show_session":
                self.rtss_kwh_var = tk.BooleanVar(value=cfg.get("rtss_show_kwh", True))
                self.make_check(rows_container, "Oturum yanında kWh de göster", self.rtss_kwh_var,
                                self.on_rtss_change).pack(anchor="w", padx=(30, 0))

        tk.Label(card, text="• Başlık kutusunu boş bırakırsanız sadece değer görünür.\n"
                            "• Boyuta istediğiniz sayıyı yazabilirsiniz (Örn: 100 normal, 120 büyük, 80 küçük).\n"
                            "• Renk düğmesine (■) basarak Mor, Cyan, Yeşil, Kırmızı veya Sarı seçebilirsiniz.",
                 font=(f_font, 7), fg=THEME["text_muted"], bg=THEME["card_bg"], justify="left").pack(anchor="w", padx=12, pady=(2, 6))

        # Canlı önizleme
        card_prev = self.create_card(parent, pady=(0, 6))
        self.make_card_title(card_prev, "ŞU AN OYUNDA GÖRÜNEN", THEME["accent_cyan"])
        f_prev = tk.Frame(card_prev, bg="#0B0E18", highlightbackground=THEME["card_border"], highlightthickness=1)
        f_prev.pack(fill="x", padx=12, pady=(2, 8))
        self.lbl_rtss_preview = tk.Label(f_prev, text="", font=("Consolas", 9, "bold"), fg="#38BDF8",
                                         bg="#0B0E18", justify="left", anchor="w")
        self.lbl_rtss_preview.pack(fill="x", padx=10, pady=8)

        f_btns = tk.Frame(card_prev, bg=THEME["card_bg"])
        f_btns.pack(fill="x", padx=12, pady=(0, 10))
        self.make_btn(f_btns, "🧹 Ekrandaki metni temizle", self.clear_rtss_now).pack(side="left")
        self.lbl_rtss_note = tk.Label(f_btns, text="", font=(f_font, 7, "bold"), fg=THEME["accent_green"],
                                      bg=THEME["card_bg"])
        self.lbl_rtss_note.pack(side="left", padx=8)

        self.refresh_rtss_preview()

    def open_color_picker_menu(self, btn, color_key, entry_widget):
        menu = tk.Menu(self.root, tearoff=0, bg="#121624", fg="#F1F5F9",
                       activebackground="#1E263D", activeforeground="#FFFFFF",
                       font=(THEME["font_family"], 8, "bold"))
        for name, hex_code in self.RTSS_PALETTE:
            def pick_color(code=hex_code):
                self.rtss_colors[color_key] = code
                self.config[color_key] = code
                btn.config(fg=code, activeforeground=code)
                entry_widget.config(fg=code, highlightcolor=code)
                self.save_config()
                self.on_rtss_change()
            menu.add_command(label=f"● {name}", foreground=hex_code, command=pick_color)

        try:
            menu.tk_popup(btn.winfo_rootx(), btn.winfo_rooty() + btn.winfo_height())
        finally:
            menu.grab_release()

    def on_rtss_change(self, *_):
        """Oyun içi gösterge ayarları anında uygulanır ve kaydedilir."""
        c = self.config
        c["rtss_enabled"] = self.rtss_enabled_var.get()
        c["rtss_multiline"] = self.rtss_multiline_var.get()
        c["rtss_show_kwh"] = self.rtss_kwh_var.get()
        for item in self.RTSS_ROWS:
            show_key, label_key, color_key, size_key = item[0], item[1], item[2], item[3]
            c[show_key] = self.rtss_vars[show_key].get()
            c[label_key] = self.rtss_entries[label_key].get().strip()
            if color_key in self.rtss_colors:
                c[color_key] = self.rtss_colors[color_key]
            if size_key in self.rtss_size_entries:
                sz_str = self.rtss_size_entries[size_key].get().strip()
                c[size_key] = sz_str if sz_str else "100"
        self.save_config()
        self.refresh_rtss_preview()

        # Ayar degistigi anda gecikmesiz olarak RTSS oyun ici ekranina gonder
        if hasattr(self, "rtss") and self.rtss:
            if not c.get("rtss_enabled", True):
                self.rtss.release_osd()
            else:
                vals = getattr(self, "_last_vals", (150.0, 0.40, 0.0, 0.0, 0.0))
                hw = getattr(self, "_last_hw", None)
                txt = self.get_rtss_text(vals[0], vals[1], vals[2], vals[3], vals[4], hw_stats=hw)
                if txt and txt.strip():
                    self.rtss.update_osd(txt)
                else:
                    self.rtss.release_osd()

    def refresh_rtss_preview(self, vals=None):
        if vals is not None:
            self._last_vals = vals
        w, hourly, sess_tl, kwh, today_tl = getattr(self, "_last_vals", (165.0, 0.43, 1.25, 0.48, 5.80))
        if not hasattr(self, "lbl_rtss_preview"):
            return
        if not self.config.get("rtss_enabled", True):
            self.lbl_rtss_preview.config(text="(Gösterge kapalı)", fg=THEME["text_muted"])
            return
        hw = getattr(self, "_last_hw", None)
        txt = self.get_rtss_text(w, hourly, sess_tl, kwh, today_tl, hw_stats=hw)
        if txt:
            # Önizleme kutusunda görünmesi için RTSS <S=...> ve <C=...> etiketlerini temizle
            clean_disp = re.sub(r'<[SC][^>]*>', '', txt)
            if "<FR>" in clean_disp:
                live_fps = self.rtss.get_active_fps() if hasattr(self, 'rtss') and self.rtss else 0.0
                fps_disp = f"{int(live_fps)}" if live_fps > 0 else "144"
                clean_disp = clean_disp.replace("<FR>", fps_disp)
            self.lbl_rtss_preview.config(text=clean_disp, fg="#38BDF8")
        else:
            self.lbl_rtss_preview.config(text="(Hiçbir değer seçilmedi)", fg=THEME["text_muted"])

    def clear_rtss_now(self):
        if hasattr(self, "rtss") and self.rtss:
            self.rtss.release_osd()
        self.lbl_rtss_note.config(text="✓ Temizlendi (kapalıysa yeniden yazılmaz)")
        self.root.after(2500, lambda: self.lbl_rtss_note.config(text=""))

    def reset_session(self):
        self.session_start = time.time()
        self.total_energy_wh = 0.0
        self.last_update = time.time()

    def get_rtss_text(self, total_wall_w, hourly_tl, total_tl, kwh, today_tl=0.0, hw_stats=None, custom_cfg=None):
        cfg = custom_cfg if custom_cfg is not None else self.config
        hw = hw_stats or getattr(self, "_last_hw", {})
        
        cpu_uti = hw.get("cpu_uti", 30)
        cpu_temp = hw.get("cpu_temp", 42)
        gpu_uti = hw.get("gpu_uti", 15)
        gpu_temp = hw.get("gpu_temp", 38)
        ram_uti = hw.get("ram_uti", 50)
        ram_gb = hw.get("ram_gb", 16.0)
        fan_rpm = hw.get("fan_rpm", 3100)

        def _fmt(show_key, label_key, color_key, size_key, def_label, def_color, def_size, val_str):
            if not cfg.get(show_key, False):
                return None
            lbl = str(cfg.get(label_key, def_label)).strip()
            hex_color = str(cfg.get(color_key, def_color)).replace("#", "").upper()
            try:
                raw_size = int(str(cfg.get(size_key, def_size)).strip())
                if 5 < raw_size <= 30:
                    scale = int(raw_size * 7.5)
                else:
                    scale = max(50, min(300, raw_size))
            except Exception:
                scale = 100

            txt_item = f"{lbl}: {val_str}" if lbl else val_str
            res = ""
            if scale != 100:
                res += f"<S={scale}>"
            if hex_color and hex_color != "FFFFFF":
                res += f"<C={hex_color}>"
            res += txt_item
            if hex_color and hex_color != "FFFFFF":
                res += "<C>"
            if scale != 100:
                res += "<S>"
            return res

        parts_l1 = []
        p_fps = _fmt("rtss_show_fps", "rtss_label_fps", "rtss_color_fps", "rtss_size_fps", "FPS", "#F43F5E", "100", "<FR>")
        if p_fps: parts_l1.append(p_fps)

        p_pwr = _fmt("rtss_show_power", "rtss_label_power", "rtss_color_power", "rtss_size_power", "GUC", "#00E5FF", "100", f"{total_wall_w:.0f} W")
        if p_pwr: parts_l1.append(p_pwr)

        p_hr = _fmt("rtss_show_hourly", "rtss_label_hourly", "rtss_color_hourly", "rtss_size_hourly", "TUKETIM", "#10B981", "100", f"{hourly_tl:.2f}TL")
        if p_hr: parts_l1.append(p_hr)

        p_cpu = _fmt("rtss_show_cpu", "rtss_label_cpu", "rtss_color_cpu", "rtss_size_cpu", "CPU", "#F59E0B", "100", f"%{cpu_uti} {cpu_temp}°C")
        if p_cpu: parts_l1.append(p_cpu)

        cpu_w = hw.get("cpu_w", 0)
        p_cpu_w = _fmt("rtss_show_cpu_w", "rtss_label_cpu_w", "rtss_color_cpu_w", "rtss_size_cpu_w", "CPU-W", "#F59E0B", "100", f"{cpu_w:.0f} W")
        if p_cpu_w: parts_l1.append(p_cpu_w)

        cpu_clk = hw.get("cpu_clk", 0)
        if cpu_clk > 0:
            clk_str = f"{cpu_clk/1000.0:.2f} GHz" if cpu_clk >= 1000 else f"{cpu_clk} MHz"
            p_cpu_clk = _fmt("rtss_show_cpu_clk", "rtss_label_cpu_clk", "rtss_color_cpu_clk", "rtss_size_cpu_clk", "CPU-CLK", "#FCD34D", "100", clk_str)
            if p_cpu_clk: parts_l1.append(p_cpu_clk)

        p_gpu = _fmt("rtss_show_gpu", "rtss_label_gpu", "rtss_color_gpu", "rtss_size_gpu", "GPU", "#00E5FF", "100", f"%{gpu_uti} {gpu_temp}°C")
        if p_gpu: parts_l1.append(p_gpu)

        gpu_w = hw.get("gpu_w", 0)
        p_gpu_w = _fmt("rtss_show_gpu_w", "rtss_label_gpu_w", "rtss_color_gpu_w", "rtss_size_gpu_w", "GPU-W", "#00E5FF", "100", f"{gpu_w:.0f} W")
        if p_gpu_w: parts_l1.append(p_gpu_w)

        gpu_clk = hw.get("gpu_clk", 0)
        if gpu_clk > 0:
            p_gpu_clk = _fmt("rtss_show_gpu_clk", "rtss_label_gpu_clk", "rtss_color_gpu_clk", "rtss_size_gpu_clk", "GPU-CLK", "#38BDF8", "100", f"{gpu_clk} MHz")
            if p_gpu_clk: parts_l1.append(p_gpu_clk)

        parts_l2 = []
        vram_mb = hw.get("vram_mb", 0)
        if vram_mb > 0:
            p_vram = _fmt("rtss_show_vram", "rtss_label_vram", "rtss_color_vram", "rtss_size_vram", "VRAM", "#818CF8", "100", f"{vram_mb/1024.0:.1f} GB")
            if p_vram: parts_l2.append(p_vram)

        p_ram = _fmt("rtss_show_ram", "rtss_label_ram", "rtss_color_ram", "rtss_size_ram", "RAM", "#A855F7", "100", f"%{ram_uti}")
        if p_ram: parts_l2.append(p_ram)

        if fan_rpm > 0:
            p_fan = _fmt("rtss_show_fan", "rtss_label_fan", "rtss_color_fan", "rtss_size_fan", "FAN", "#34D399", "100", f"{fan_rpm} RPM")
            if p_fan: parts_l2.append(p_fan)

        kwh_str = f" ({kwh:.2f} kWh)" if cfg.get("rtss_show_kwh", True) else ""
        p_sess = _fmt("rtss_show_session", "rtss_label_session", "rtss_color_session", "rtss_size_session", "OTURUM", "#F59E0B", "100", f"{total_tl:.2f} TL{kwh_str}")
        if p_sess: parts_l2.append(p_sess)

        p_td = _fmt("rtss_show_today", "rtss_label_today", "rtss_color_today", "rtss_size_today", "BUGUN", "#A855F7", "100", f"{today_tl:.2f} TL")
        if p_td: parts_l2.append(p_td)

        try:
            month_tl = HistoryManager.get_summary().get("month_tl", 0.0)
        except Exception:
            month_tl = 0.0
        p_mo = _fmt("rtss_show_month", "rtss_label_month", "rtss_color_month", "rtss_size_month", "AY", "#EC4899", "100", f"{month_tl:.2f} TL")
        if p_mo: parts_l2.append(p_mo)

        if cfg.get("rtss_multiline", True):
            lines = []
            if parts_l1:
                lines.append(" | ".join(parts_l1))
            if parts_l2:
                lines.append(" | ".join(parts_l2))
            return "\n".join(lines)
        else:
            all_parts = parts_l1 + parts_l2
            return " | ".join(all_parts)

    def update_loop(self):
        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        sensors = self.reader.read_sensors()

        if sensors:
            source = sensors.get('_source', 'Sensör')
            self.lbl_status.config(text=f"● {source} Bağlı (1 Hz Canlı Veri)", fg=THEME["accent_green"])
            if hasattr(self, 'lbl_hw_title'):
                self.lbl_hw_title.config(text=f"CANLI DONANIM & SENSÖRLER ({source})")
            
            # CPU ve GPU okuma
            try:
                cpu_w = float(sensors.get('PCPUPKG', 0.0))
            except ValueError:
                cpu_w = 0.0

            try:
                gpu_w = float(sensors.get('PGPU1', 0.0))
            except ValueError:
                gpu_w = 0.0

            try:
                cpu_uti = int(float(sensors.get('SCPUUTI', 0.0)))
            except Exception:
                cpu_uti = 0

            try:
                cpu_temp = int(float(sensors.get('TCPU', sensors.get('TCPUPKG', 0.0))))
            except Exception:
                cpu_temp = 0

            try:
                gpu_uti = int(float(sensors.get('SGPU1UTI', 0.0)))
            except Exception:
                gpu_uti = 0

            try:
                gpu_temp = int(float(sensors.get('TGPU1', 0.0)))
            except Exception:
                gpu_temp = 0

            try:
                ram_uti = int(float(sensors.get('SMEMUTI', 0.0)))
            except Exception:
                ram_uti = 0

            try:
                ram_gb = float(sensors.get('SUSEDMEM', 0.0)) / 1024.0
            except Exception:
                ram_gb = 0.0

            try:
                fan_rpm = int(float(sensors.get('FANRPM', sensors.get('FCPU', 0.0))))
            except Exception:
                fan_rpm = 0

            try:
                cpu_clk = int(float(sensors.get('CPUCLK', 0)))
            except Exception:
                cpu_clk = 0

            try:
                gpu_clk = int(float(sensors.get('GPUCLK', 0)))
            except Exception:
                gpu_clk = 0

            try:
                vram_mb = int(float(sensors.get('VRAMMEM', 0)))
            except Exception:
                vram_mb = 0

            self._last_hw = {
                "cpu_w": cpu_w, "cpu_uti": cpu_uti, "cpu_temp": cpu_temp, "cpu_clk": cpu_clk,
                "gpu_w": gpu_w, "gpu_uti": gpu_uti, "gpu_temp": gpu_temp, "gpu_clk": gpu_clk,
                "ram_uti": ram_uti, "ram_gb": ram_gb, "vram_mb": vram_mb, "fan_rpm": fan_rpm
            }

            self.lbl_cpu.config(text=f"{cpu_w:.0f} W • %{cpu_uti} • {cpu_temp}°C")
            self.lbl_gpu.config(text=f"{gpu_w:.0f} W • %{gpu_uti} • {gpu_temp}°C")
            if hasattr(self, 'lbl_ram'):
                self.lbl_ram.config(text=f"%{ram_uti}")

            # --- LABORATUVAR KALİBRASYONU (9 Gerçek Sayaç Ölçümü) ---
            # Priz Toplam = 78.3 + 1.396*CPU + 1.178*GPU (Monitör 16.5W + Modem 10W dahil)
            # Sadece Kasa Priz Çekişi = 51.8 + 1.396*CPU + 1.178*GPU
            pc_wall_w = 51.8 + 1.396 * cpu_w + 1.178 * gpu_w

            # Harici Cihazlar (seçime göre eklenir)
            ext_wall = 0.0
            if self.asus_var.get():
                ext_wall += float(self.config.get("asus_monitor_w", 16.5))
            if self.samsung_var.get():
                ext_wall += float(self.config.get("samsung_monitor_w", 19.0))
            if self.modem_var.get():
                ext_wall += float(self.config.get("modem_w", 10.0))

            total_wall_w = max(40.0, pc_wall_w + ext_wall)

            # Dinamik Yük Gösterge Metni (RTX 5070 için 480W eşiği)
            if total_wall_w > 480:
                self.lbl_power_status.config(text="🔥 TAM YÜK", fg=THEME["accent_rose"])
            elif total_wall_w > 260:
                self.lbl_power_status.config(text="🎮 OYUN / YÜK", fg="#38BDF8")
            else:
                self.lbl_power_status.config(text="🌱 TASARRUF / BOŞTA", fg=THEME["accent_green"])

            # Kümülatif Enerji (Oturum)
            wh_delta = total_wall_w * (dt / 3600.0)
            self.total_energy_wh += wh_delta
            kwh = self.total_energy_wh / 1000.0
            price = float(self.config.get("kwh_price_tl", 2.60))
            total_tl = kwh * price
            hourly_tl = (total_wall_w / 1000.0) * price
            daily_tl = hourly_tl * 24.0
            monthly_tl = daily_tl * 30.0

            # Günlük & Aylık Geçmiş Veritabanına Ekle
            HistoryManager.add_energy(wh_delta, price)

            # UI Güncelle
            self.lbl_power.config(text=f"{total_wall_w:.0f} W")
            self.lbl_rate_hour.config(text=f"{hourly_tl:.2f} TL")
            self.lbl_rate_day.config(text=f"{daily_tl:.1f} TL")
            self.lbl_rate_month.config(text=f"{monthly_tl:.0f} TL")

            self.lbl_cost.config(text=f"{total_tl:.2f} TL")
            self.lbl_kwh.config(text=f"Tüketim: {kwh:.3f} kWh")

            # Süreler
            elapsed = int(now - self.session_start)
            hrs = elapsed // 3600
            mins = (elapsed % 3600) // 60
            secs = elapsed % 60
            self.lbl_time.config(text=f"Oturum: {hrs:02d}:{mins:02d}:{secs:02d}")

            # AIDA64 PC Uptime (SUPTIME) ve Senaryo Hesaplaması
            up_sec = ctypes.windll.kernel32.GetTickCount64() // 1000
            hrs_up = up_sec / 3600.0
            
            pc_uptime_str = sensors.get('SUPTIME', '')
            if not pc_uptime_str:
                pc_uptime_str = f"{up_sec//3600:02d}:{(up_sec%3600)//60:02d}:{up_sec%60:02d}"
            self.lbl_pc_uptime.config(text=f"🖥 PC Açık Kalma: {pc_uptime_str}")

            # Senaryo 1: PC hep Boşta/Tasarrufta kalsaydı (Ref: 145W)
            # Senaryo 2: PC hep Oyunda kalsaydı (Ref: 355W)
            saver_tl = (145.0 / 1000.0) * hrs_up * price
            game_tl = (355.0 / 1000.0) * hrs_up * price

            self.lbl_saver_est.config(text=f"🌱 Tasarruf: {saver_tl:.2f} TL")
            self.lbl_game_est.config(text=f"🎮 Oyunda: {game_tl:.2f} TL")

            self._last_watt = total_wall_w
            self._last_hourly = hourly_tl

            # Sistem Tepsisini Canlı Güncelle (Tooltip, Canlı Sıcaklık & Menü)
            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    # 1. Tooltip (Fare saatin oradaki simgeye gelince)
                    self.tray_icon.title = f"WattCost HaYTooL: {total_wall_w:.0f}W | CPU: {cpu_temp}°C (%{cpu_uti}) | GPU: {gpu_temp}°C (%{gpu_uti}) | {hourly_tl:.2f} TL/sa"
                    
                    # 2. Canlı Menü Öğeleri
                    self.tray_watt_str = f"⚡ Anlık Güç: {total_wall_w:.0f} W"
                    self.tray_temp_str = f"🌡️ Donanım: CPU {cpu_temp}°C (%{cpu_uti})  |  GPU {gpu_temp}°C (%{gpu_uti})"
                    self.tray_hourly_str = f"₺ Saatlik Maliyet: {hourly_tl:.2f} TL/sa"
                    
                    # 3. İkon Üzerindeki Canlı Gösterge (Seçili tray_mode'a göre)
                    self.tray_icon.icon = self.create_tray_image(
                        watt=total_wall_w, cpu_temp=cpu_temp, gpu_temp=gpu_temp,
                        cpu_uti=cpu_uti, gpu_uti=gpu_uti, hourly_tl=hourly_tl
                    )
                except Exception:
                    pass

            # 4. RivaTuner (RTSS) Oyun İçi Overlay Güncellemesi
            try:
                today_tl = HistoryManager.get_summary().get("today_tl", 0.0)
            except Exception:
                today_tl = 0.0
            self.refresh_rtss_preview((total_wall_w, hourly_tl, total_tl, kwh, today_tl))
            if hasattr(self, 'rtss') and self.rtss:
                if self.config.get("rtss_enabled", True):
                    try:
                        rtss_text = self.get_rtss_text(total_wall_w, hourly_tl, total_tl, kwh, today_tl, hw_stats=self._last_hw)
                        if rtss_text and rtss_text.strip():
                            self.rtss.update_osd(rtss_text)
                        else:
                            self.rtss.release_osd()
                    except Exception:
                        pass
                else:
                    try:
                        self.rtss.release_osd()
                    except Exception:
                        pass

        else:
            self.lbl_status.config(text="⚠ Donanım Sensörü Okunamadı (MSI Afterburner veya AIDA64 açın)", fg="#EF4444")
            self.lbl_power_status.config(text="• BAĞLANTI YOK", fg=THEME["text_muted"])

        # 1 saniyede bir tekrarla
        self.root.after(1000, self.update_loop)

    def open_history_report(self):
        f_font = THEME["font_family"]
        top = tk.Toplevel(self.root)
        top.title("Tüketim & Maliyet Raporu")
        top.geometry("380x480")
        top.configure(bg=THEME["bg"])
        top.resizable(False, False)
        top.transient(self.root)

        summary = HistoryManager.get_summary()

        lbl_head = tk.Label(top, text="📊 GÜNLÜK & AYLIK ELEKTRİK RAPORU", font=(f_font, 10, "bold"),
                            fg=THEME["accent_cyan"], bg=THEME["bg"])
        lbl_head.pack(pady=(14, 8))

        # Özet Kartı
        f_sum_card = tk.Frame(top, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_sum_card.pack(fill="x", padx=14, pady=6)

        # Bugün Satırı
        f_row_today = tk.Frame(f_sum_card, bg=THEME["card_bg"])
        f_row_today.pack(fill="x", padx=12, pady=6)
        tk.Label(f_row_today, text="BUGÜNKÜ TOPLAM:", font=(f_font, 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")
        tk.Label(f_row_today, text=f"{summary['today_tl']:.2f} TL  ({summary['today_kwh']:.3f} kWh)",
                 font=(f_font, 9, "bold"), fg=THEME["accent_green"], bg=THEME["card_bg"]).pack(side="right")

        tk.Frame(f_sum_card, bg=THEME["card_border"], height=1).pack(fill="x", padx=10)

        # Bu Ay Satırı
        f_row_month = tk.Frame(f_sum_card, bg=THEME["card_bg"])
        f_row_month.pack(fill="x", padx=12, pady=6)
        tk.Label(f_row_month, text="BU AYKİ TOPLAM (FATURA):", font=(f_font, 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")
        tk.Label(f_row_month, text=f"{summary['month_tl']:.2f} TL  ({summary['month_kwh']:.2f} kWh)",
                 font=(f_font, 9, "bold"), fg=THEME["accent_amber"], bg=THEME["card_bg"]).pack(side="right")

        # Geçmiş Günler Başlığı
        tk.Label(top, text="SON GÜNLERİN TÜKETİM GEÇMİŞİ", font=(f_font, 7, "bold"),
                 fg=THEME["text_muted"], bg=THEME["bg"]).pack(anchor="w", padx=16, pady=(10, 4))

        # Liste Kutusu (Frame + Scroll)
        f_list = tk.Frame(top, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_list.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # Gün gün ters kronolojik sırala
        history_items = sorted(summary["history"].items(), key=lambda x: x[0], reverse=True)
        if not history_items:
            tk.Label(f_list, text="Henüz kayıtlı geçmiş bulunmuyor.", font=(f_font, 8), fg=THEME["text_muted"], bg=THEME["card_bg"]).pack(pady=20)
        else:
            for d_str, d_data in history_items[:8]:
                r = tk.Frame(f_list, bg=THEME["card_bg"])
                r.pack(fill="x", padx=10, pady=3)
                
                # Süre formatı
                secs = d_data.get("active_seconds", 0)
                dur_str = f"{secs//3600:02d}s {((secs%3600)//60):02d}d"
                
                tk.Label(r, text=f"{d_str} ({dur_str})", font=(f_font, 8), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")
                tk.Label(r, text=f"{d_data.get('cost_tl', 0.0):.2f} TL", font=(f_font, 8, "bold"), fg=THEME["text_primary"], bg=THEME["card_bg"]).pack(side="right")
                tk.Label(r, text=f"{d_data.get('kwh', 0.0):.2f} kWh", font=(f_font, 7), fg=THEME["text_muted"], bg=THEME["card_bg"]).pack(side="right", padx=6)

    def open_settings(self):
        f_font = THEME["font_family"]
        top = tk.Toplevel(self.root)
        top.title("Ayarlar")
        top.geometry("360x530")
        top.configure(bg=THEME["card_bg"])
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        tk.Label(top, text="⚙ TARİFE VE SİSTEM AYARLARI", font=(f_font, 10, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(pady=(14, 4))
        tk.Label(top, text="Oyun içi gösterge ayarları ana ekrandaki 🎮 sekmesindedir.",
                 font=(f_font, 7), fg=THEME["text_muted"], bg=THEME["card_bg"]).pack(pady=(0, 8))

        entries = {}
        fields = [
            ("Elektrik Fiyatı (TL / kWh):", "kwh_price_tl", 2.60),
            ("Asus VP249 Tüketimi (W):", "asus_monitor_w", 16.5),
            ("Samsung 2. Monitör (W):", "samsung_monitor_w", 19.0),
            ("Keenetic Modem (W):", "modem_w", 10.0),
        ]
        f_form = tk.Frame(top, bg=THEME["card_bg"])
        f_form.pack(fill="x", padx=20)
        for label_text, key, default in fields:
            f_row = tk.Frame(f_form, bg=THEME["card_bg"])
            f_row.pack(fill="x", pady=3)
            tk.Label(f_row, text=label_text, font=(f_font, 8), fg=THEME["text_secondary"],
                     bg=THEME["card_bg"]).pack(anchor="w")
            ent = tk.Entry(f_row, font=(f_font, 9), bg=THEME["card_inner"], fg=THEME["text_primary"],
                           insertbackground=THEME["text_primary"], relief="flat",
                           highlightbackground=THEME["card_border"], highlightcolor=THEME["accent_cyan"],
                           highlightthickness=1)
            ent.insert(0, str(self.config.get(key, default)))
            ent.pack(fill="x", ipady=3)
            entries[key] = ent

        tk.Frame(top, bg=THEME["card_border"], height=1).pack(fill="x", padx=20, pady=(10, 4))

        # Saatteki Simge Göstergesi Seçimi (Tray Mode)
        f_tray_mode = tk.Frame(top, bg=THEME["card_bg"])
        f_tray_mode.pack(fill="x", padx=20, pady=(2, 4))
        tk.Label(f_tray_mode, text="📌 Saatteki Simge Göstergesi (Tray):", font=(f_font, 8, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w")

        tray_mode_map = {
            "dual_temp": "CPU & GPU Sıcaklığı (°C)",
            "cpu_uti":   "CPU Kullanımı (%)",
            "gpu_uti":   "GPU Kullanımı (%)",
            "cpu_temp":  "CPU Sıcaklığı (°C)",
            "gpu_temp":  "GPU Sıcaklığı (°C)",
            "power_w":   "Prizden Toplam Güç (Watt)",
            "hourly_tl": "Saatlik Harcama (TL/sa)",
            "logo":      "Sabit WattCost Logosu"
        }
        rev_tray_map = {v: k for k, v in tray_mode_map.items()}
        current_display_name = tray_mode_map.get(self.config.get("tray_mode", "dual_temp"), "CPU & GPU Sıcaklığı (°C)")

        opt_tray = ttk.Combobox(f_tray_mode, values=list(tray_mode_map.values()), state="readonly", font=(f_font, 8))
        opt_tray.set(current_display_name)
        opt_tray.pack(fill="x", pady=(2, 0))

        tk.Frame(top, bg=THEME["card_border"], height=1).pack(fill="x", padx=20, pady=(10, 4))

        autostart_var = tk.BooleanVar(value=WindowsAutoStart.is_enabled())
        self.make_check(top, "Windows başlangıcında otomatik başlat", autostart_var, None,
                        fg=THEME["text_primary"], bold=True).pack(anchor="w", padx=20, pady=2)

        close_to_tray_var = tk.BooleanVar(value=self.config.get("close_to_tray", False))
        self.make_check(top, "Çarpı (X) ile kapatınca tepsiye gizle", close_to_tray_var, None).pack(anchor="w", padx=20, pady=2)
        tk.Label(top, text="İşaretsizse X'e basınca program tamamen kapanır ve oyun ekranı temizlenir.",
                 font=(f_font, 7, "italic"), fg=THEME["text_muted"], bg=THEME["card_bg"],
                 wraplength=310, justify="left").pack(anchor="w", padx=38)

        def save_and_close():
            try:
                values = {k: float(entries[k].get().replace(',', '.')) for k in entries}
            except ValueError:
                messagebox.showerror("Hata", "Lütfen geçerli sayısal değerler girin!", parent=top)
                return
            self.config.update(values)
            self.config["close_to_tray"] = close_to_tray_var.get()
            selected_mode_name = opt_tray.get()
            self.config["tray_mode"] = rev_tray_map.get(selected_mode_name, "dual_temp")
            self.save_config()
            WindowsAutoStart.set_enabled(autostart_var.get())
            self.refresh_device_labels()
            self.set_tray_mode(self.config["tray_mode"])
            top.destroy()

        self.make_btn(top, "💾 Kaydet", save_and_close, fg="#FFFFFF", bg="#2563EB", pady=7).pack(
            fill="x", padx=20, pady=(12, 10))

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--watch":
        from rtss_overlay import _watch_and_clear
        _watch_and_clear(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "WattCost")
        sys.exit(0)

    root = tk.Tk()
    app = PowerTrackerApp(root)
    root.mainloop()
