"""
AIDA64 Shared Memory Okuma Testi
"""
import ctypes
from ctypes import wintypes
import xml.etree.ElementTree as ET
import sys

# Türkçe karakter desteği konsol için
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SHARED_MEMORY_NAME = "AIDA64_SensorValues"
FILE_MAP_READ = 0x0004

def read_aida64_data():
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenFileMappingW.restype = wintypes.HANDLE
    kernel32.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    
    kernel32.MapViewOfFile.restype = wintypes.LPVOID
    kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
    
    kernel32.UnmapViewOfFile.argtypes = [wintypes.LPCVOID]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    
    # Yerel ve Global isim alanlarını dene
    names = [SHARED_MEMORY_NAME, f"Global\\{SHARED_MEMORY_NAME}"]
    h_map = None
    for name in names:
        h_map = kernel32.OpenFileMappingW(FILE_MAP_READ, False, name)
        if h_map:
            break
            
    if not h_map:
        err = ctypes.GetLastError()
        return None, f"OpenFileMapping başarısız. Hata kodu: {err} (AIDA64 açık mı?)"
        
    p_buf = kernel32.MapViewOfFile(h_map, FILE_MAP_READ, 0, 0, 0)
    if not p_buf:
        err = ctypes.GetLastError()
        kernel32.CloseHandle(h_map)
        return None, f"MapViewOfFile başarısız. Hata kodu: {err}"
        
    try:
        raw_bytes = ctypes.string_at(p_buf)
        xml_text = raw_bytes.decode('utf-8', errors='ignore').strip()
    finally:
        kernel32.UnmapViewOfFile(p_buf)
        kernel32.CloseHandle(h_map)

    if not xml_text:
        return None, "Paylaşımlı bellek boş veya okunamadı."
        
    try:
        wrapped_xml = f"<root>{xml_text}</root>"
        root = ET.fromstring(wrapped_xml)
        
        sensors = []
        for child in root:
            sensor = {
                'type': child.tag,
                'id': child.findtext('id', default=''),
                'label': child.findtext('label', default=''),
                'value': child.findtext('value', default='')
            }
            sensors.append(sensor)
        return sensors, None
    except Exception as e:
        return None, f"XML ayrıştırma hatası: {e}"

if __name__ == "__main__":
    print("=" * 60)
    print("AIDA64 Sensör Verisi Okuma Testi Başlatılıyor...")
    print("=" * 60)
    
    sensors, err = read_aida64_data()
    if err:
        print(f"[UYARI] {err}")
    else:
        print(f"Başarılı! Toplam {len(sensors)} sensör bulundu.\n")
        
        pwr_sensors = [s for s in sensors if s['type'].lower() == 'pwr' or 'watt' in s['label'].lower() or 'pwr' in s['id'].lower()]
        
        if pwr_sensors:
            print("--- ⚡ GÜÇ (POWER / WATT) SENSÖRLERİ ---")
            total_watt = 0.0
            for s in pwr_sensors:
                val = s['value']
                print(f"  • {s['label']:<25} [ID: {s['id']:<10}] : {val} W")
                try:
                    total_watt += float(val)
                except ValueError:
                    pass
            print("-" * 50)
            print(f"  TOPLAM ÖLÇÜLEN GÜÇ: {total_watt:.2f} W")
        else:
            print("[BİLGİ] Henüz 'pwr' tipinde sensör algılanmadı. Mevcut tüm sensörler:")
            for s in sensors[:20]:
                print(f"  [{s['type']}] {s['label']} ({s['id']}): {s['value']}")
