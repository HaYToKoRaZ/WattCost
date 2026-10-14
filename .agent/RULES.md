# 📜 WATTCOST HaYTooL: BİRLEŞİK PROJE ANAYASASI VE GELİŞTİRME KURALLARI (RULES.md)

Bu belge; WattCost HaYTooL sisteminin tüm kurallarını, zorunlu güvenlik anayasasını, GitHub dal ve push stratejisini, donanım envanterini, laboratuvar ölçümlerini, matematiksel modelini, kalibrasyon rehberini ve proje mimarisini tek çatı altında toplayan **nihai ve tek başvuru kaynağıdır**.

---

## 1. YAZILIM DEĞİŞİKLİK VE GÜVENLİK ANAYASASI (ZORUNLU KURALLAR)

Bu kurallar projede çalışacak her geliştirici ve yapay zeka asistanı için **istisnasız bağlayıcıdır**:

1. **Her Kod Değişikliğinden Önce 7-Zip Ultra Tam Yedek (Madde 1):**
   - Kod dosyalarında (`main/app.py`, `main/rtss_overlay.py` vb.) herhangi bir değişiklik yapılmadan önce, projenin tamamı `backup/` klasörüne 7-Zip en yüksek sıkıştırma (`-mx=9`) kullanılarak zaman damgalı arşivlenmelidir:
     ```powershell
     # Örnek Arşiv Adı:
     backup/backup_YYYYMMDD_HHMMSS.7z
     ```
   - Bu kural **istisnasız her kod değişikliğinden önce** işletilecektir. Yedek alınmadan tek satır dahi kod değiştirilemez.

2. **Sensör & Veri Kaynağı Doğrulama (Madde 2):**
   - Yeni bir veri kaynağına (örn. AIDA64'ten MSI Afterburner'a) geçiş yapılmadan veya sensör eşleştirmesi değiştirilmeden önce, her iki kaynaktan anlık paralel okuma yapılarak değerler yan yana karşılaştırılmalı ve başlık/birim eşleşmeleri doğrulanmalıdır.

3. **Çalışma Dizini ve Modüler Dizin Mimarisi (Madde 3):**
   - Tüm masaüstü uygulama dosyaları `main/` klasörü içinde yer alır.
   - Tüm web arayüzü ve tanıtım sitesi dosyaları `websites/` klasörü içinde yer alır.
   - Kök dizinde sadece başlatıcı (`Baslat.bat`), git yoksayma (`.gitignore`), anayasa klasörü (`.agent/RULES.md`) ve yedekler (`backup/`) bulunur.
   - `main/app.py` başlangıçta kendi bulunduğu dizini çalışma dizini yapar (`os.chdir(...)`). Yollar daima bağıl ve modüler kalmalıdır.

4. **GitHub Dal (Branch) ve Pushlama Kuralları (Madde 4):**
   - **`main` Dalı:** Masaüstü Python uygulaması (`main/` klasörü içeriği ve kök dosyalar) bu dala pushlanacaktır.
   - **`websites` Dalı:** Web sitesi ve web arayüzü (`websites/` klasörü içeriği) bu dala pushlanacaktır.
    - **Repo URL:** https://github.com/HaYToKoRaZ/WattCost
   - İki dal birbirine karışmayacak, her dal yalnızca kendi kapsamındaki dosyaları barındıracaktır.

---

## 2. PROJE TANIMI VE MİMARİSİ

**WattCost HaYTooL**, bilgisayarın prizden çektiği gerçek aktif gücü (Watt), donanım sıcaklıklarını ve elektrik faturası karşılığını (TL) 1 Hz hassasiyetle hesaplayan, sistem tepsisinde ve oyun içinde (RivaTuner / RTSS OSD) canlı gösteren modern bir takip yazılımıdır.

### Dosya ve Dizin Hiyerarşisi:
```text
hesaplama/
│
├── Baslat.bat                 # Kök başlatıcı: main/app.py'yi arka planda başlatır
├── .gitignore                 # Git yoksayma kuralları (backup/, pycache vb.)
│
├── .agent/                    # AGENT & PROJE YÖNETİMİ
│   └── RULES.md               # Tek proje anayasası, kurallar ve mimari (BU DOSYA)
│
├── main/                      # MASAÜSTÜ PYTHON UYGULAMASI (GitHub: main dalı)
│   ├── app.py                 # Ana arayüz, Tkinter GUI, hesaplama motoru, sistem tepsisi
│   ├── rtss_overlay.py        # RivaTuner (RTSS) OSD paylaşımlı bellek sürücüsü ve watchdog
│   ├── live_tracker.py        # AIDA64 paylaşımlı bellek (XML) okuyucu motoru
│   ├── calibrate.py           # Akıllı sayaç regresyon kalibrasyon aracı
│   ├── test_aida64.py         # Sensör doğrulama test aracı
│   ├── config.json            # Kullanıcı renk, boyut, etiket ve cihaz ayarları
│   ├── olcumler.jsonl         # Akıllı sayaç laboratuvar ölçüm kayıtları
│   ├── tuketim_gecmisi.json   # Günlük ve aylık biriken Wh / TL harcama veritabanı
│   ├── app_icon.ico           # Çok katmanlı Windows sistem ikonu
│   ├── app_icon.png           # Uygulama simgesi (PNG)
│   └── bewicon.png            # Resmi PowerPulse vektörel marka logosu
│
├── websites/                  # WEB SİTESİ & WEB ARAYÜZÜ (GitHub: websites dalı)
│   └── README.md              # Web sitesi tanıtımı ve bileşenleri
│
└── backup/                    # 7-Zip (-mx=9) ile alınmış tam zaman damgalı arşivler
```

---

## 3. REFERANS DONANIM ENVANTERİ

Sistemin matematiksel modeli aşağıdaki donanım konfigürasyonuna ve fiziksel ölçümlere dayanır:

| Kategori | Bileşen | Donanım Karakteristiği |
| :--- | :--- | :--- |
| **İşlemci (CPU)** | AMD Ryzen 7 5800X (8C / 16T - 4.85 GHz) | Boşta: ~25-32W, Tam Yük: ~125-140W |
| **Ekran Kartı (GPU)** | **NVIDIA GeForce RTX 5070 (12 GB - Çift Fan)** | Boşta: ~10-14W, Oyun/Yük: ~220-250W *(Önceki: RTX 4060 Ti 8GB)* |
| **Anakart** | Asus Prime B550M-K ARGB | Çipset ve PCIe kontrolcüleri: ~12W |
| **Bellek (RAM)** | 32 GB (2x16GB) A-Data DDR4-3200 XPG | ~7W |
| **Depolama (5 Disk)** | 2x 7200 RPM HDD + 2x NVMe SSD + 1x SATA SSD | Toplam ~4.7 TB depolama: ~16-20W |
| **Soğutma & Fanlar** | Sıvı Soğutma Pompası + 6x 120mm Fan | Motorlar ve devirdaim: ~15-20W |
| **Aydınlatma & USB** | Full ARGB (6 Fan + Kasa) + ROG/TUF Aygıtlar | Arctis 7 + ROG Impact III + TUF K1: ~14W |
| **Güç Kaynağı (PSU)** | Thermaltake 650W (5 Yıllık) | Yaşlanma ve yük eğrisine bağlı verim: ~%82-84 |
| **1. Monitör** | Asus VP249 (23.8" IPS - 144Hz) | Aktif priz çekişi: **16.5 W** |
| **2. Monitör** | Samsung SyncMaster S22E390H (22" LCD) | Opsiyonel priz çekişi: **19.0 W** |
| **Ağ Cihazı** | Keenetic Hopper KN-3610 Modem | Aynı prize takılı: **10.0 W** |

---

## 4. GERÇEK LABORATUVAR ÖLÇÜMLERİ VE MATEMATİKSEL MODEL

Tüm ölçümler akıllı sayaçtan (Volt, Amper, kW) ve AIDA64 / Afterburner paylaşımlı belleğinden 1 Hz frekansla toplanarak 30 saniyelik ortalamalarla kaydedilmiştir (`main/olcumler.jsonl`):

### Laboratuvar Test Verileri:
| No | Test Durumu | Güç Planı | Sayaç Akımı (A) | Sayaç Aktif Güç | AIDA CPU (Ort) | AIDA GPU (Ort) |
|:---:| :--- | :--- |:---:|:---:|:---:|:---:|
| **1** | **Masaüstü Boşta** | Dengeli | 0.692 A | **144 W** | 32.6 W | 12.6 W |
| **2** | **Sadece CPU Stres** | Dengeli | 1.212 A | **261 W** | 122.6 W | 14.4 W |
| **3** | **Sadece GPU Stres** | Dengeli | 1.646 A | **345 W** | 61.5 W | 159.0 W |
| **4** | **CPU + GPU Tam Stres** | Dengeli | 2.019 A | **452 W** | 125.6 W | 159.7 W |
| **5** | **Oyun (Blood of Dawnwalker)** | Dengeli | 1.665 A | **355 W** | 78.5 W | 150.6 W |
| **6** | **Masaüstü Boşta** | Tasarruf | 0.780 A | **161 W** | 26.3 W | 12.3 W |
| **7** | **CPU Stres** | Tasarruf | 0.815 A | **172 W** | 52.2 W | 8.9 W |

### Matematiksel Formül (En Küçük Kareler Regresyonu):
$$\mathbf{Kasa\ Priz\ Çekişi\ (W) = 51.8 + 1.396 \times CPU_{Watt} + 1.178 \times GPU_{Watt}}$$

$$\mathbf{Toplam\ Priz\ Gücü\ (W) = Kasa\ Priz\ Çekişi + Monitör(ler) + Modem}$$
*(Monitör 16.5W + Modem 10.0W dahil olduğunda taban 78.3 W olur).*

- **CPU Çarpanı (1.396):** VRM regülasyon kayıpları + pompa yükü + PSU verim kaybı.
- **GPU Çarpanı (1.178):** PCIe hat kayıpları + VRAM + PSU verim kaybı.
- **Model Doğruluğu:** %97.5+ hassasiyet.

### Maliyet ve Tarife Esasları:
- **Birim Fiyat:** `2.60 TL / kWh` (Kocaeli SEDAŞ / Sepaş Enerji).
- **Saatlik Maliyet:** $\text{TL / Saat} = (\text{Toplam Watt} / 1000) \times 2.60$
- **Oturum Tutarı:** Her saniye entegre edilen kWh tüketiminin birim fiyatla çarpımı.

---

## 5. ALINAN KRİTİK GELİŞTİRME KARARLARI

1. **MSI Afterburner Önceliği (Sıfır Bağımlılık):**
   - Sensör okumada ilk olarak `MAHMSharedMemory` kontrol edilir. Sistemde Afterburner açıksa harici AIDA64 çalıştırmaya gerek kalmaz. Afterburner kapalıysa otomatik olarak AIDA64'e geri düşer.
2. **RTSS szOSDEx Çözümü:**
   - RivaTuner v2.7+ belleğinde hem `szOSD` hem `szOSDEx` alanları bulunduğu için eski sürümlerde yaşanan "GUC ve WGUC" çift yazı sorunu, `szOSD` alanı boş bırakılıp sadece `szOSDEx` formatlanarak kalıcı olarak çözüldü.
3. **5 Kafa Renk Paleti:**
   - Mor (`#A855F7`), Cyan (`#00E5FF`), Yeşil (`#10B981`), Kırmızı (`#F43F5E`), Sarı (`#F59E0B`), Beyaz (`#FFFFFF`).
4. **RTX 5070 Dinamik Yük Eşikleri:**
   - 480W üzeri: `🔥 TAM YÜK`
   - 260W - 480W arası: `🎮 OYUN / YÜK`
   - 260W altı: `🌱 TASARRUF / BOŞTA`
5. **Sistem Tepsisi Canlı Dereceler (Saatin Yanı):**
   - Saatin yanındaki dinamik simgede üst satırda CPU (`C 52°`), alt satırda GPU (`G 45°`) canlı gösterilir. Parçalardan biri 80°C'yi aşarsa simge çerçevesi kırmızı alarm moduna geçer.
   - Simge tooltip'inde anlık Watt, CPU/GPU sıcaklıkları ve saatlik TL tek satırda sunulur.

---

## 6. GELECEKTE DONANIM DEĞİŞTİĞİNDE KALİBRASYON REHBERİ

Yeni bir işlemci, ekran kartı veya PSU takıldığında kodları baştan yazmaya **gerek yoktur**:

1. Akıllı prizi/sayacı bağlayın.
2. `main/` dizininde terminalden 3 durumu kaydedin:
   ```powershell
   # 1. Boştayken:
   python main/calibrate.py add "1-bosta" "dengeli" <SAYAÇTAKİ_WATT> 30

   # 2. Oyundayken:
   python main/calibrate.py add "2-oyun" "dengeli" <SAYAÇTAKİ_WATT> 30

   # 3. CPU stres testindeyken:
   python main/calibrate.py add "3-cpu" "dengeli" <SAYAÇTAKİ_WATT> 30
   ```
3. Yeni katsayıları hesaplatın:
   ```powershell
   python main/calibrate.py fit
   ```
4. Çıkan yeni formülü `main/app.py` içindeki `pc_wall_w = ...` satırına yazın. Sistem 1 dakika içinde %98 hassasiyetle yeni parçaya uyum sağlar.

---

## 7. GITHUB REPO VE DAL (BRANCH) PUSH REHBERİ

### Repo Bilgileri:
* **GitHub Repository URL:** `[HENÜZ OLUŞTURULMADI - KULLANICI LİNKİ VERDİĞİNDE BURAYA EKLENECEK]`
* **Uzak Bağlantı (Remote):** `origin`

### Dal Yapısı ve Push Hedefleri:

| Klasör | Karşılık Gelen GitHub Dalı | İçerik |
| :--- | :--- | :--- |
| **`main/`** (+ kök dosyalar) | **`main`** | Masaüstü Python GUI uygulaması, sensör motorları, RTSS overlay, başlatıcı. |
| **`websites/`** | **`websites`** | Web arayüzü, indirme/tanıtım landing page sayfaları, dokümantasyon web sitesi. |

### Kullanıcı Repoyu Oluşturduğunda Uygulanacak Push Adımları:

1. **Git Başlatma ve Remote Ekleme:**
   ```powershell
   git init
   git remote add origin <KULLANICININ_VERECEĞİ_GITHUB_URL>
   ```

2. **`main` Dalını Gönderme (Masaüstü Uygulama):**
   ```powershell
   git checkout -B main
   git add main/ Baslat.bat RULES.md .agents/
   git commit -m "feat: PowerPulse masaüstü uygulaması ve çekirdek mimari"
   git push -u origin main
   ```

3. **`websites` Dalını Gönderme (Web Sitesi):**
   ```powershell
   git checkout -B websites
   # websites klasörü içeriği bu dalın köküne alınarak pushlanır
   git add websites/
   git commit -m "feat: PowerPulse web sitesi ve arayüz dosyaları"
   git push -u origin websites
   ```

> **Not:** Kullanıcı GitHub üzerinde repoyu oluşturup linkini bildirdiği anda bu bölümdeki URL güncellenecek ve yukarıdaki adımlar otomatik olarak çalıştırılacaktır.

