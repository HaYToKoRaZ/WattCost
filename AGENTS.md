# WATTCOST HaYTooL RULES

## 1. GELİŞTİRME DÖNGÜSÜ
1. **Yedek & Sürüm (İLK İŞ):** Kod değiştirmeden önce `backup.ps1` çalıştır (asıl betik: `.agents/backup.ps1`). Betik hem `backup/*.7z` yedeğini alır hem de sürümü otomatik minor +1 yapar (`0.9` -> `1.0`, `1.9` -> `2.0`). Sürümün senkron kaldığı dosyalar: `main/version.json`, `main/config_manager.py` (`APP_VERSION`), `main/version_info.txt`, `main/app.manifest`; UI başlıkları `APP_VERSION` değişkeninden okunur, elle güncellenmez.
2. **Çift Dil & Sıfır Hardcode:** `main/*.py` içinde sabit string yasak; tüm metinler `_t()` ile çağrılır. Yeni/değişen anahtarlar `tr.json` ve `en.json` dosyalarına eşzamanlı eklenir.
3. **Otomatik Derleme (SON İŞ):** Değişiklik ve testler bittiğinde onay beklemeden `build.ps1` çalıştır; `dist/WattCost. HaYTooL.exe` üret.
4. **Git Branch Ayrımı:** Masaüstü kodu `main` dalına, web sitesi kodu `websites` dalına pushlanır.

## 2. FORMÜLLER & MİMARİ
- **Priz Gücü:**  
  $$\text{Kasa Gücü (W)} = 46.7 + 1.632 \times CPU_{\text{Watt}} + 1.170 \times GPU_{\text{Watt}}$$  
  $$\text{Toplam Güç (W)} = \text{Kasa Gücü} + \text{Monitör(ler)} + \text{Modem}$$
- **Sensör:** MSI Afterburner (`MAHMSharedMemory`) öncelikli; yoksa AIDA64.
- **RTSS OSD:** Çift metin hatasını önlemek için `szOSD = ""` (boş); yalnızca `szOSDEx` formatlanır.
