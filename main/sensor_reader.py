"""
WattCost HaYTooL - Donanım Sensör Okuyucu Modülü
MSI Afterburner (MAHMSharedMemory) ve AIDA64 Paylaşımlı Bellek Entegrasyonu.
"""
import ctypes
from ctypes import wintypes
import xml.etree.ElementTree as ET

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
        self._cached_entry_offsets = None
        self._cached_entry_count = -1

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

            # Sensör ofsetlerini bir defa haritala; her saniye yüzlerce string/decode işleminden kaçın
            if self._cached_entry_offsets is None or self._cached_entry_count != entry_count:
                offsets = {}
                for i in range(entry_count):
                    e_ptr = p_buf + header_size + i * entry_size
                    raw_e = ctypes.string_at(e_ptr, 260)
                    s_name = raw_e.split(b'\x00')[0].decode('latin-1', 'ignore').strip()
                    offsets[s_name] = header_size + i * entry_size + 1300
                self._cached_entry_offsets = offsets
                self._cached_entry_count = entry_count

            mahm_raw = {}
            for s_name, val_offset in self._cached_entry_offsets.items():
                mahm_raw[s_name] = ctypes.c_float.from_address(p_buf + val_offset).value
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
        data = self.msi_reader.read_sensors()
        if data:
            return data
        data = self.aida_reader.read_sensors()
        if data:
            return data
        return None
