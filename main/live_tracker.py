"""
Canlı AIDA64 Güç ve TL Maliyet Takip Motoru
"""
import ctypes
from ctypes import wintypes
import xml.etree.ElementTree as ET
import time
import sys
import os

SHARED_MEMORY_NAME = "AIDA64_SensorValues"
FILE_MAP_READ = 0x0004

class AIDA64Reader:
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.kernel32.OpenFileMappingW.restype = wintypes.HANDLE
        self.kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel32.MapViewOfFile.restype = wintypes.LPVOID
        self.kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
        self.kernel32.UnmapViewOfFile.argtypes = [wintypes.LPCVOID]
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    def read_sensors(self):
        names = [SHARED_MEMORY_NAME, f"Global\\{SHARED_MEMORY_NAME}"]
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
            sensor_dict = {}
            for child in root:
                sid = child.findtext('id', default='').strip()
                val = child.findtext('value', default='0').strip()
                sensor_dict[sid] = val
            return sensor_dict
        except Exception:
            return None

def main():
    reader = AIDA64Reader()
    
    # --- KALİBRASYON VE MALİYET AYARLARI ---
    KWH_PRICE_TL = 2.50       # 1 kWh Elektrik Fiyatı (TL)
    MONITOR_WATT = 35.0       # Monitör tüketimi (W)
    MODEM_WATT = 10.0         # Keenetic modem (W) (Sayaçta takılı olduğu için ekliyoruz)
    BASE_SYSTEM_WATT = 28.0   # Anakart, Fanlar, RAM, SSD, USB aygıtlar (W)
    PSU_EFFICIENCY = 0.88     # %88 Verimlilik (80+ Gold seviyesi)
    
    total_energy_wh = 0.0
    start_time = time.time()
    last_tick = time.time()
    
    print("\n" + "="*65)
    print("      PC CANLI ELEKTRİK & TL TÜKETİM HESAPLAYICI (TEST MODU)")
    print("="*65)
    print(f" Tarife: {KWH_PRICE_TL:.2f} TL/kWh | Monitör: {MONITOR_WATT}W | Modem: {MODEM_WATT}W")
    print(f" Kasa Baz: {BASE_SYSTEM_WATT}W | PSU Verimi: %{int(PSU_EFFICIENCY*100)}")
    print(" Veriler AIDA64'ten canlı okunuyor... (Durdurmak için Ctrl+C)")
    print("="*65 + "\n")
    
    try:
        while True:
            sensors = reader.read_sensors()
            now = time.time()
            dt = now - last_tick
            last_tick = now
            
            if sensors:
                # CPU Package (PCPUPKG)
                cpu_watt = float(sensors.get('PCPUPKG', 0.0))
                # GPU (PGPU1)
                gpu_watt = float(sensors.get('PGPU1', 0.0))
                
                # Toplam kasa içi bileşenler
                internal_dc_watt = cpu_watt + gpu_watt + BASE_SYSTEM_WATT
                # PSU şebeke çekişi
                pc_wall_watt = internal_dc_watt / PSU_EFFICIENCY
                # Prizdeki toplam (PC + Monitör + Modem)
                total_wall_watt = pc_wall_watt + MONITOR_WATT + MODEM_WATT
                
                # Kümülatif Enerji (Watt-saat)
                total_energy_wh += total_wall_watt * (dt / 3600.0)
                total_kwh = total_energy_wh / 1000.0
                total_cost_tl = total_kwh * KWH_PRICE_TL
                
                # Anlık Saatlik Harcama
                hourly_tl = (total_wall_watt / 1000.0) * KWH_PRICE_TL
                
                # Geçen süre
                elapsed_sec = int(now - start_time)
                elapsed_str = f"{elapsed_sec//3600:02d}:{(elapsed_sec%3600)//60:02d}:{elapsed_sec%60:02d}"
                
                # Tek satırda veya temiz blok olarak yaz
                status = (
                    f"\r[CANLI] CPU: {cpu_watt:4.1f}W | GPU: {gpu_watt:4.1f}W | "
                    f"PRIZ (HESAPLANAN): {total_wall_watt:5.1f}W | "
                    f"ANLIK HIZ: {hourly_tl:5.2f} TL/saat | "
                    f"TOPLAM: {total_cost_tl:5.3f} TL ({elapsed_str})"
                )
                sys.stdout.write(status)
                sys.stdout.flush()
            else:
                sys.stdout.write("\r[BEKLENİYOR] AIDA64 sensör verisi okunamadı...")
                sys.stdout.flush()
                
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\n\nTest durduruldu.")

if __name__ == "__main__":
    main()
