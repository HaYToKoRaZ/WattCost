"""
WattCost HaYTooL - Çoklu Dil (i18n) ve Yerelleştirme Yöneticisi
Uygulamanın dil dosyalarını (languages/*.json) dinamik olarak tarar,
sistem dilini otomatik algılar ve bayraklı dil seçimi sağlar.
Kullanıcı languages/ klasörüne yeni bir *.json dosyası eklediğinde (örneğin balbal.json),
uygulama bunu otomatik olarak algılar ve dil seçim menüsünde gösterir.
"""
import os
import sys
import json
import locale
import ctypes
import math
from typing import Dict, List, Optional, Any, Callable
from PIL import Image, ImageDraw, ImageTk

# Tanınan yaygın dil kodları için varsayılan bayrak eşleştirmeleri
DEFAULT_FLAGS = {
    "tr": "🇹🇷",
    "en": "🇬🇧",
    "us": "🇺🇸",
    "de": "🇩🇪",
    "fr": "🇫🇷",
    "es": "🇪🇸",
    "it": "🇮🇹",
    "ru": "🇷🇺",
    "az": "🇦🇿",
    "uk": "🇺🇦",
    "nl": "🇳🇱",
    "pl": "🇵🇱",
    "pt": "🇵🇹",
    "br": "🇧🇷",
    "ja": "🇯🇵",
    "ko": "🇰🇷",
    "zh": "🇨🇳",
    "ar": "🇸🇦",
    "el": "🇬🇷",
    "sv": "🇸🇪",
    "no": "🇳🇴",
    "fi": "🇫🇮",
    "da": "🇩🇰",
}

# Gömülü varsayılan Türkçe çeviriler
DEFAULT_TR = {
    "_lang_code": "tr",
    "_lang_name": "Türkçe",
    "_lang_flag": "🇹🇷",
    
    # Genel & Header
    "app_title": "WattCost HaYTooL • PC Güç & TL Monitörü",
    "app_subtitle": "HaYTooL • PC Güç & TL Monitörü",
    "tab_cost": "⚡ Maliyet",
    "tab_powerplan": "⚙️ Güç Planı",
    "tab_smartswitch": "🤖 Akıllı Geçiş",
    "tab_compare": "⚖️ Karşılaştırma",
    
    # Header Buton Tooltipleri
    "tooltip_settings": "⚙️ Ayarlar: Elektrik birim fiyatı, harici cihazlar, Zalman ve sistem ayarları",
    "tooltip_test_screen": "🎮 OSD Test Ekranı: Oyun açmadan RTSS oyun içi göstergesini masaüstünde canlı test edin",
    "tooltip_hide_tray": "📥 Tepsiye Gizle: Uygulama penceresini kapatmadan Windows saat yanına küçültün",
    "tooltip_history": "📊 Tüketim Raporu: Günlük ve aylık detaylı elektrik harcama geçmişini görüntüleyin",
    "sensor_status_init": "● Başlatılıyor...",
    "sensor_status_connected": "● Sensörler Bağlı",
    "sensor_status_offline": "● Sensör Bekleniyor",
    "tooltip_sensor_status": "Canlı Sensör Durumu: MSI Afterburner ve AIDA64 sensör bağlantısı",
    "tooltip_language": "🌐 Dil Seçimi: Arayüz dilini anında değiştirin",
    
    # Hero Kart (Elektrik Güç & Maliyet)
    "hero_wall_power": "PRİZDEN ÇEKİLEN ANLIK GÜÇ",
    "hero_stable": "• KARARLI",
    "hero_hourly": "SAATLİK",
    "hero_session": "OTURUM",
    "hero_daily": "GÜNLÜK",
    "hero_monthly": "AYLIK PROJEKSİYON",
    "hero_calculating": "Hesaplanıyor...",
    
    # Donanım Güç Dağılım Kartı
    "card_hw_breakdown": "SİSTEM DONANIM GÜÇ DAĞILIMI",
    "hw_gpu": "Ekran Kartı (GPU)",
    "hw_cpu": "İşlemci (CPU)",
    "hw_case_fans": "Kasa & Fanlar (Taban)",
    "hw_psu_loss": "PSU Kayıp Güç",
    "hw_external_devices": "Harici Cihazlar & Çevre Birimleri",
    "hw_unit_price": "Elektrik Birim Fiyatı",
    "hw_tariff": "Tarife",
    "hw_monitors": "Monitörler",
    "hw_modem": "Modem",
    
    # PowerPlan Tab
    "active_plan_title": "ŞU ANDA AKTİF OLAN GÜÇ DÜZENİ",
    "plans_list_title": "SİSTEMDEKİ GÜÇ DÜZENLERİ (TEK TIKLA GEÇİŞ)",
    "btn_refresh": "🔄 Yenile",
    "btn_add_wattcost_plans": "⚡ WattCost Planlarını Ekle",
    "btn_add_amd_plans": "🔴 AMD Ryzen Planları Ekle",
    "btn_add_ultimate": "⚡ Ultimate Performance",
    "btn_restore_defaults": "↩️ Windows Varsayılana Sıfırla",
    "btn_unlock_hidden": "🔓 Windows Gizli Ayarları Aç",
    "btn_lock_hidden": "🔒 Gizli Ayarları Kapat",
    "btn_open_power_cpl": "⚙️ Windows Güç Seçenekleri (cpl)",
    "btn_open_adv_cpl": "🛠️ Gelişmiş Güç Ayarları",
    "badge_active_plan": "● AKTİF PLAN",
    "btn_make_active": "⚡ Aktif Yap",
    "btn_clone": "📋 Klonla",
    "btn_delete": "✕",
    
    # Tooltipler - PowerPlan
    "tooltip_refresh_plans": "Sistemdeki güç planlarını yeniden tarar ve listeyi günceller",
    "tooltip_add_wattcost": "Özel optimize edilmiş 4 kademeli (Maximum Power Saver, Balanced, High Performance, Maximum Performance) WattCost güç planlarını sisteme yükler",
    "tooltip_add_amd": "AMD Ryzen işlemciler için özel enerji ve boost profillerini sisteme ekler",
    "tooltip_add_ultimate": "Windows'un resmi Ultimate Performance güç modunu sisteme tanıtır",
    "tooltip_restore_defaults": "Windows varsayılan güç planlarını geri yükler (Dengeli, Güç Tasarrufu, Yüksek Performans)",
    "tooltip_unlock_hidden": "Windows güç seçeneklerinde gizli olan işlemci frekansı, çekirdek park etme ve uyku gibi onlarca gizli ayarın kilidini açar",
    "tooltip_lock_hidden": "Windows güç ayarlarındaki gelişmiş gizli seçenekleri tekrar gizler ve sadeleştirir",
    "tooltip_open_power_cpl": "Klasik Windows Güç Seçenekleri Denetim Masası penceresini açar",
    "tooltip_open_adv_cpl": "Aktif güç planının gelişmiş ince ayar penceresini (işlemci yönetimi, uyku, PCI Express vb.) doğrudan açar",
    "tooltip_make_active": "Bu güç planını sistemde etkin güç modu olarak ayarlar",
    "tooltip_clone_plan": "Bu güç planının tüm ayarlarıyla birebir bir kopyasını oluşturur",
    "tooltip_delete_plan": "Bu güç planını sistemden kalıcı olarak siler",
    
    # Compare Tab
    "compare_title": "GÜÇ DÜZENLERİ AYAR & PERFORMANS KARŞILAŞTIRMA MATRİSİ",
    "compare_btn_refresh": "🔄 Yeniden Oku",
    "compare_filter_diff": "Yalnızca Farklı Olan Ayarları Göster (Filtre)",
    "compare_tip": "💡 İpucu: Plan başlığına tıklayarak o plana geçebilir; hücreye çift tıklayarak ayarları düzenleyebilirsiniz.",
    
    # Compare Rows
    "row_cpu_min": "En Düşük İşlemci (Min CPU)",
    "row_cpu_max": "En Yüksek İşlemci (Max CPU)",
    "row_cpu_freq": "Maksimum İşlemci Frekansı",
    "row_cpu_epp": "İşlemci Enerji Tercihi (EPP)",
    "row_cpu_boost": "İşlemci Turbo Boost Modu",
    "row_cooling": "Sistem Soğutma İlkesi",
    "row_core_park_min": "Çekirdek Park Etme Min",
    "row_core_park_max": "Çekirdek Park Etme Maks",
    "row_pcie_aspm": "PCIe Güç Tasarrufu (ASPM)",
    "row_usb_suspend": "USB Seçici Askıya Alma",
    "row_wifi_saving": "Kablosuz (Wi-Fi) Güç Tasarrufu",
    "row_video_timeout": "Ekranı Kapatma Süresi",
    "row_sleep_timeout": "Uykuya Geçiş Süresi",
    "row_hybrid_sleep": "Karma (Hibrit) Uyku",
    "row_hibernate_timeout": "Hazırda Bekleme Süresi",
    "row_wake_timers": "Uyandırma Zamanlayıcıları",
    "row_power_btn": "Güç Düğmesi Eylemi",
    "row_sleep_btn": "Uyku Düğmesi Eylemi",
    "row_disk_timeout": "Sabit Diski Kapatma",
    
    # SmartSwitch Tab
    "smart_title": "4 KADEMELİ AKILLI GÜÇ & HZ OTOMASYONU (SMARTSWITCH)",
    "smart_enable_lbl": "Akıllı Otomatik Güç Planı Geçişini Etkinleştir",
    "smart_hz_enable_lbl": "Akıllı Monitör Yenileme Hızı (Hz) Otomasyonunu Etkinleştir",
    "smart_toast_lbl": "Geçiş Yapıldığında Bildirim (Toast) Göster",
    "smart_sound_lbl": "Geçiş Yapıldığında Ses Efekti Çal",
    "smart_t1_title": "KADEME 1: BOŞTA / ULTRA TASARRUF",
    "smart_t2_title": "KADEME 2: GÜNLÜK / MEDYA & WEB",
    "smart_t3_title": "KADEME 3: ÇOKLU GÖREV / ORTA YÜK",
    "smart_t4_title": "KADEME 4: OYUN / MAKSİMUM PERFORMANS",
}

# Gömülü varsayılan İngilizce çeviriler
DEFAULT_EN = {
    "_lang_code": "en",
    "_lang_name": "English",
    "_lang_flag": "🇬🇧",
    
    # General & Header
    "app_title": "WattCost HaYTooL • PC Power & Cost Monitor",
    "app_subtitle": "HaYTooL • PC Power & Cost Monitor",
    "tab_cost": "⚡ Cost",
    "tab_powerplan": "⚙️ Power Plan",
    "tab_smartswitch": "🤖 SmartSwitch",
    "tab_compare": "⚖️ Compare",
    
    # Header Action Tooltips
    "tooltip_settings": "⚙️ Settings: Electricity tariff, external devices, Zalman LCD and system options",
    "tooltip_test_screen": "🎮 OSD Test Screen: Live test RTSS in-game OSD directly on desktop without launching games",
    "tooltip_hide_tray": "📥 Minimize to Tray: Keep running in background next to Windows clock",
    "tooltip_history": "📊 Consumption Report: View detailed daily and monthly electricity cost logs",
    "sensor_status_init": "● Initializing...",
    "sensor_status_connected": "● Sensors Connected",
    "sensor_status_offline": "● Waiting for Sensors",
    "tooltip_sensor_status": "Live Sensor Status: MSI Afterburner and AIDA64 hardware monitoring connection",
    "tooltip_language": "🌐 Language Selection: Change interface language instantly",
    
    # Hero Card (Power & Cost)
    "hero_wall_power": "REAL-TIME WALL POWER DRAW",
    "hero_stable": "• STABLE",
    "hero_hourly": "HOURLY",
    "hero_session": "SESSION",
    "hero_daily": "DAILY",
    "hero_monthly": "MONTHLY PROJECTION",
    "hero_calculating": "Calculating...",
    
    # Hardware Breakdown Card
    "card_hw_breakdown": "HARDWARE POWER BREAKDOWN",
    "hw_gpu": "Graphics Card (GPU)",
    "hw_cpu": "Processor (CPU)",
    "hw_case_fans": "Case & Fans (Base)",
    "hw_psu_loss": "PSU Power Loss",
    "hw_external_devices": "External Devices & Peripherals",
    "hw_unit_price": "Electricity Unit Price",
    "hw_tariff": "Tariff",
    "hw_monitors": "Monitors",
    "hw_modem": "Modem / Router",
    
    # PowerPlan Tab
    "active_plan_title": "CURRENT ACTIVE POWER PLAN",
    "plans_list_title": "SYSTEM POWER PLANS (ONE-CLICK SWITCH)",
    "btn_refresh": "🔄 Refresh",
    "btn_add_wattcost_plans": "⚡ Add WattCost Plans",
    "btn_add_amd_plans": "🔴 Add AMD Ryzen Plans",
    "btn_add_ultimate": "⚡ Ultimate Performance",
    "btn_restore_defaults": "↩️ Restore Windows Defaults",
    "btn_unlock_hidden": "🔓 Unlock Windows Hidden Settings",
    "btn_lock_hidden": "🔒 Lock Hidden Settings",
    "btn_open_power_cpl": "⚙️ Windows Power Options (cpl)",
    "btn_open_adv_cpl": "🛠️ Advanced Power Settings",
    "badge_active_plan": "● ACTIVE PLAN",
    "btn_make_active": "⚡ Set Active",
    "btn_clone": "📋 Clone",
    "btn_delete": "✕",
    
    # Tooltips - PowerPlan
    "tooltip_refresh_plans": "Rescans power schemes in system and refreshes the list",
    "tooltip_add_wattcost": "Installs 4 custom optimized WattCost power plans (Maximum Power Saver, Balanced, High Performance, Maximum Performance)",
    "tooltip_add_amd": "Installs dedicated energy and boost profiles optimized for AMD Ryzen processors",
    "tooltip_add_ultimate": "Registers Windows official Ultimate Performance power scheme to your system",
    "tooltip_restore_defaults": "Restores original Windows default schemes (Balanced, Power Saver, High Performance)",
    "tooltip_unlock_hidden": "Unlocks hidden advanced power settings (CPU frequency limit, core parking, turbo boost, sleep) in Windows Control Panel",
    "tooltip_lock_hidden": "Re-hides advanced hidden power settings in Windows Control Panel for simplicity",
    "tooltip_open_power_cpl": "Opens classic Windows Power Options Control Panel window",
    "tooltip_open_adv_cpl": "Opens the advanced power settings dialog for the active plan directly",
    "tooltip_make_active": "Sets this scheme as the currently active system power mode",
    "tooltip_clone_plan": "Creates an exact duplicate copy of this power scheme with all its settings",
    "tooltip_delete_plan": "Permanently deletes this power scheme from the system",
    
    # Compare Tab
    "compare_title": "POWER SCHEMES CONFIGURATION & PERFORMANCE MATRIX",
    "compare_btn_refresh": "🔄 Refresh",
    "compare_filter_diff": "Show Only Differences (Filter)",
    "compare_tip": "💡 Tip: Click any plan header to activate it; double-click any cell to edit settings interactively.",
    
    # Compare Rows
    "row_cpu_min": "Minimum Processor State (Min CPU)",
    "row_cpu_max": "Maximum Processor State (Max CPU)",
    "row_cpu_freq": "Maximum Processor Frequency",
    "row_cpu_epp": "Energy Performance Preference (EPP)",
    "row_cpu_boost": "Processor Boost Mode",
    "row_cooling": "System Cooling Policy",
    "row_core_park_min": "Processor Core Parking Min",
    "row_core_park_max": "Processor Core Parking Max",
    "row_pcie_aspm": "PCIe Link State Power Mgmt (ASPM)",
    "row_usb_suspend": "USB Selective Suspend",
    "row_wifi_saving": "Wireless Adapter (Wi-Fi) Saving",
    "row_video_timeout": "Turn Off Display After",
    "row_sleep_timeout": "Sleep After",
    "row_hybrid_sleep": "Hybrid Sleep",
    "row_hibernate_timeout": "Hibernate After",
    "row_wake_timers": "Allow Wake Timers",
    "row_power_btn": "Power Button Action",
    "row_sleep_btn": "Sleep Button Action",
    "row_disk_timeout": "Turn Off Hard Disk After",
    
    # SmartSwitch Tab
    "smart_title": "4-TIER SMART POWER & MONITOR REFRESH RATE (HZ) AUTOMATION",
    "smart_enable_lbl": "Enable Smart Automatic Power Plan Switching",
    "smart_hz_enable_lbl": "Enable Smart Monitor Refresh Rate (Hz) Automation",
    "smart_toast_lbl": "Show Toast Notification on Plan Transition",
    "smart_sound_lbl": "Play Sound Effect on Plan Transition",
    "smart_t1_title": "TIER 1: IDLE / ULTRA ECO",
    "smart_t2_title": "TIER 2: DAILY / WEB & MEDIA",
    "smart_t3_title": "TIER 3: MULTITASK / MEDIUM LOAD",
    "smart_t4_title": "TIER 4: GAMING / MAXIMUM PERFORMANCE",
}


def generate_flag_image(code: str, w: int = 56, h: int = 38) -> Image.Image:
    """Belirtilen dil kodu için yüksek çözünürlüklü ve pürüzsüz bayrak resmi üretir."""
    W, H = w * 4, h * 4
    code_lower = (code or "").lower().strip()

    if code_lower == "tr":
        # Türk Bayrağı: Kırmızı zemin, beyaz hilal ve 5 köşeli yıldız
        img = Image.new('RGBA', (W, H), (227, 10, 23, 255))
        draw = ImageDraw.Draw(img)
        c_x, c_y = W * 0.38, H * 0.50
        r_out = H * 0.32
        draw.ellipse([c_x - r_out, c_y - r_out, c_x + r_out, c_y + r_out], fill=(255, 255, 255, 255))
        in_x = c_x + (H * 0.08)
        r_in = H * 0.25
        draw.ellipse([in_x - r_in, c_y - r_in, in_x + r_in, c_y + r_in], fill=(227, 10, 23, 255))
        s_x, s_y = W * 0.62, H * 0.50
        s_r = H * 0.13
        points = []
        angle_offset = -math.pi / 2
        for i in range(10):
            r = s_r if i % 2 == 0 else s_r * 0.38
            a = angle_offset + i * math.pi / 5
            points.append((s_x + r * math.cos(a), s_y + r * math.sin(a)))
        draw.polygon(points, fill=(255, 255, 255, 255))
    elif code_lower in ("en", "gb", "uk"):
        # Birleşik Krallık (Union Jack): Lacivert zemin, beyaz/kırmızı diyagonal ve merkez haçlar
        img = Image.new('RGBA', (W, H), (1, 33, 105, 255))
        draw = ImageDraw.Draw(img)
        dw = H * 0.22
        draw.line([(0, 0), (W, H)], fill=(255, 255, 255, 255), width=int(dw))
        draw.line([(0, H), (W, 0)], fill=(255, 255, 255, 255), width=int(dw))
        rw = H * 0.075
        draw.line([(0, 0), (W, H)], fill=(200, 16, 46, 255), width=int(rw))
        draw.line([(0, H), (W, 0)], fill=(200, 16, 46, 255), width=int(rw))
        cw = H * 0.35
        draw.rectangle([W/2 - cw/2, 0, W/2 + cw/2, H], fill=(255, 255, 255, 255))
        draw.rectangle([0, H/2 - cw/2, W, H/2 + cw/2], fill=(255, 255, 255, 255))
        rcw = H * 0.20
        draw.rectangle([W/2 - rcw/2, 0, W/2 + rcw/2, H], fill=(200, 16, 46, 255))
        draw.rectangle([0, H/2 - rcw/2, W, H/2 + rcw/2], fill=(200, 16, 46, 255))
    elif code_lower == "de":
        # Almanya: Siyah, Kırmızı, Sarı şeritler
        img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, H/3, W, 2*H/3], fill=(221, 0, 0, 255))
        draw.rectangle([0, 2*H/3, W, H], fill=(255, 206, 0, 255))
    elif code_lower == "fr":
        # Fransa: Mavi, Beyaz, Kırmızı dikey şeritler
        img = Image.new('RGBA', (W, H), (0, 38, 84, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([W/3, 0, 2*W/3, H], fill=(255, 255, 255, 255))
        draw.rectangle([2*W/3, 0, W, H], fill=(237, 41, 57, 255))
    elif code_lower in ("az", "aze"):
        # Azerbaycan: Mavi, Kırmızı, Yeşil yatay şeritler
        img = Image.new('RGBA', (W, H), (0, 181, 226, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, H/3, W, 2*H/3], fill=(237, 41, 57, 255))
        draw.rectangle([0, 2*H/3, W, H], fill=(63, 156, 53, 255))
        c_x, c_y = W * 0.47, H * 0.50
        r_out = H * 0.12
        draw.ellipse([c_x - r_out, c_y - r_out, c_x + r_out, c_y + r_out], fill=(255, 255, 255, 255))
        draw.ellipse([c_x + (H * 0.03) - r_out * 0.8, c_y - r_out * 0.8, c_x + (H * 0.03) + r_out * 0.8, c_y + r_out * 0.8], fill=(237, 41, 57, 255))
    else:
        # Genel Siber Küre (Globe) Bayrağı
        img = Image.new('RGBA', (W, H), (24, 29, 48, 255))
        draw = ImageDraw.Draw(img)
        cx, cy, r = W/2, H/2, H*0.38
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(0, 229, 255, 255), width=int(H*0.06), fill=(18, 22, 36, 255))
        draw.ellipse([cx-r*0.5, cy-r, cx+r*0.5, cy+r], outline=(0, 229, 255, 200), width=int(H*0.04))
        draw.line([cx-r, cy, cx+r, cy], fill=(0, 229, 255, 200), width=int(H*0.04))
        draw.line([cx, cy-r, cx, cy+r], fill=(0, 229, 255, 200), width=int(H*0.04))

    # Anti-aliasing ile istenen boyuta ölçekle
    res = img.resize((w, h), Image.Resampling.LANCZOS)
    draw_res = ImageDraw.Draw(res)
    draw_res.rectangle([0, 0, w-1, h-1], outline=(60, 75, 105, 230), width=1)
    return res


def detect_system_language() -> str:
    """Windows UI dilini veya yerel sistem dilini milisaniyeler içinde tespit eder."""
    # 1. Windows API GetUserDefaultUILanguage
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
        # 0x1F = 31: Türkçe
        if lang_id == 0x1F:
            return "tr"
        # 0x09 = 9: İngilizce
        elif lang_id == 0x09:
            return "en"
        elif lang_id == 0x07: # Almanca
            return "de"
        elif lang_id == 0x0C: # Fransızca
            return "fr"
        elif lang_id == 0x0A: # İspanyolca
            return "es"
        elif lang_id == 0x19: # Rusça
            return "ru"
        elif lang_id == 0x2C: # Azerice
            return "az"
    except Exception:
        pass

    # 2. Python locale tespiti
    try:
        loc = locale.getdefaultlocale()[0]
        if loc:
            code = loc.split("_")[0].lower()
            if code.startswith("tr"):
                return "tr"
            elif code.startswith("en"):
                return "en"
            return code
    except Exception:
        pass

    # 3. Çevre değişkenleri
    for env_var in ["LANG", "LANGUAGE", "LC_ALL"]:
        val = os.environ.get(env_var, "")
        if val:
            if "tr" in val.lower():
                return "tr"
            elif "en" in val.lower():
                return "en"

    return "en"


class LanguageManager:
    """
    WattCost HaYTooL Çoklu Dil Yöneticisi (Singleton).
    languages/ klasöründeki tüm *.json dosyalarını dinamik okur.
    Kullanıcı languages/ klasörüne yeni bir JSON dosyası eklediğinde (örneğin balbal.json),
    uygulama bunu otomatik olarak algılar ve dil seçim menüsünde gösterir.
    """
    _instance = None

    @classmethod
    def get_instance(cls) -> "LanguageManager":
        if cls._instance is None:
            cls._instance = LanguageManager()
        return cls._instance

    def __init__(self):
        self.languages_dir = self._resolve_languages_dir()
        self.available_languages: Dict[str, Dict[str, Any]] = {}
        self.active_language_code = "en"
        self.translations: Dict[str, str] = {}
        self.fallback_translations: Dict[str, str] = dict(DEFAULT_EN)
        self._refresh_callbacks: List[Callable[[], None]] = []

        # 1. Varsayılan TR ve EN dosyalarını garanti et
        self._ensure_default_files()
        
        # 2. Klasördeki tüm dilleri tara (kullanıcının eklediği balbal.json dahil!)
        self.scan_languages()

    def _resolve_languages_dir(self) -> str:
        """languages/ klasörünün tam yolunu çözer (EXE yanında veya proje dizininde)."""
        candidates = []
        if getattr(sys, 'frozen', False):
            # EXE çalışma zamanı
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, "languages"))
        
        # Script / dev zamanı
        mod_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(mod_dir, "languages"))
        candidates.append(os.path.join(os.path.dirname(mod_dir), "languages"))
        
        if hasattr(sys, '_MEIPASS'):
            candidates.append(os.path.join(sys._MEIPASS, "languages"))

        for c in candidates:
            if os.path.isdir(c):
                return c

        # Bulunamadıysa en uygun yerde oluştur
        target = candidates[0] if candidates else os.path.join(os.getcwd(), "languages")
        try:
            os.makedirs(target, exist_ok=True)
        except Exception:
            pass
        return target

    def _ensure_default_files(self):
        """tr.json, en.json ve bayrak PNG dosyalarının diskte mevcut olmasını sağlar."""
        try:
            tr_file = os.path.join(self.languages_dir, "tr.json")
            if not os.path.exists(tr_file):
                with open(tr_file, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_TR, f, ensure_ascii=False, indent=2)

            en_file = os.path.join(self.languages_dir, "en.json")
            if not os.path.exists(en_file):
                with open(en_file, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_EN, f, ensure_ascii=False, indent=2)

            tr_png = os.path.join(self.languages_dir, "tr.png")
            if not os.path.exists(tr_png):
                generate_flag_image("tr").save(tr_png)

            en_png = os.path.join(self.languages_dir, "en.png")
            if not os.path.exists(en_png):
                generate_flag_image("en").save(en_png)

            globe_png = os.path.join(self.languages_dir, "globe.png")
            if not os.path.exists(globe_png):
                generate_flag_image("globe").save(globe_png)
        except Exception:
            pass

    def get_flag_image(self, code: str, w: int = 28, h: int = 18) -> Image.Image:
        """Belirtilen dil kodu için bayrak resmini döner (varsa dosyasından, yoksa dinamik)."""
        code_clean = (code or "").lower().strip()
        
        # 1. languages/{code}.png var mı?
        cand = os.path.join(self.languages_dir, f"{code_clean}.png")
        if os.path.exists(cand):
            try:
                raw = Image.open(cand).convert('RGBA')
                res = raw.resize((w, h), Image.Resampling.LANCZOS)
                draw_res = ImageDraw.Draw(res)
                draw_res.rectangle([0, 0, w-1, h-1], outline=(60, 75, 105, 230), width=1)
                return res
            except Exception:
                pass

        # 2. languages/flags/{code}.png var mı?
        cand_flags = os.path.join(self.languages_dir, "flags", f"{code_clean}.png")
        if os.path.exists(cand_flags):
            try:
                raw = Image.open(cand_flags).convert('RGBA')
                res = raw.resize((w, h), Image.Resampling.LANCZOS)
                draw_res = ImageDraw.Draw(res)
                draw_res.rectangle([0, 0, w-1, h-1], outline=(60, 75, 105, 230), width=1)
                return res
            except Exception:
                pass

        # 3. Dinamik pürüzsüz bayrak üret
        return generate_flag_image(code_clean, w, h)

    def get_flag_photo(self, code: str, w: int = 28, h: int = 18) -> Any:
        """Tkinter PhotoImage nesnesini döner ve bellek sızıntısını önlemek için önbellekler."""
        if not hasattr(self, '_photo_cache'):
            self._photo_cache = {}
        key = f"{code.lower()}_{w}_{h}"
        if key not in self._photo_cache:
            img = self.get_flag_image(code, w, h)
            self._photo_cache[key] = ImageTk.PhotoImage(img)
        return self._photo_cache[key]

    def scan_languages(self) -> Dict[str, Dict[str, Any]]:
        """
        languages/ klasöründeki TÜM *.json dosyalarını tarar.
        Kullanıcı 'balbal.json' eklese bile adını, bayrağını ve çevirilerini yükler.
        """
        self.available_languages.clear()
        
        # Önce gömülü varsayılanları ekle (dosya erişim hatası olursa garanti olsun)
        self.available_languages["tr"] = {
            "code": "tr",
            "name": "Türkçe",
            "flag": "🇹🇷",
            "file": os.path.join(self.languages_dir, "tr.json"),
            "data": dict(DEFAULT_TR)
        }
        self.available_languages["en"] = {
            "code": "en",
            "name": "English",
            "flag": "🇬🇧",
            "file": os.path.join(self.languages_dir, "en.json"),
            "data": dict(DEFAULT_EN)
        }

        if not os.path.isdir(self.languages_dir):
            return self.available_languages

        try:
            for fname in os.listdir(self.languages_dir):
                if not fname.lower().endswith(".json"):
                    continue
                
                fpath = os.path.join(self.languages_dir, fname)
                stem = os.path.splitext(fname)[0].lower()
                
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if not isinstance(data, dict):
                        continue

                    code = str(data.get("_lang_code", stem)).lower().strip()
                    name = str(data.get("_lang_name", stem.capitalize())).strip()
                    flag = str(data.get("_lang_flag", DEFAULT_FLAGS.get(code, "🌐"))).strip()

                    self.available_languages[code] = {
                        "code": code,
                        "name": name,
                        "flag": flag,
                        "file": fpath,
                        "data": data
                    }
                except Exception:
                    # Hatalı veya yarım yazılmış bir JSON olsa bile listede güvenle göster
                    self.available_languages[stem] = {
                        "code": stem,
                        "name": stem.capitalize(),
                        "flag": DEFAULT_FLAGS.get(stem, "🌐"),
                        "file": fpath,
                        "data": {}
                    }
        except Exception:
            pass

        return self.available_languages

    def init_language(self, config_lang: str = "auto"):
        """Uygulama açılışında config veya sistem diline göre dili başlatır."""
        self.scan_languages()
        
        target_code = ""
        if config_lang and config_lang.lower() != "auto":
            clean_c = config_lang.lower().strip()
            if clean_c in self.available_languages:
                target_code = clean_c
        
        if not target_code:
            sys_lang = detect_system_language()
            if sys_lang in self.available_languages:
                target_code = sys_lang
            else:
                target_code = "en" if "en" in self.available_languages else list(self.available_languages.keys())[0]

        self.set_language(target_code)

    def set_language(self, code: str) -> bool:
        """Aktif arayüz dilini değiştirir ve kayıtlı dinleyicileri tetikler."""
        code = (code or "").lower().strip()
        if code not in self.available_languages:
            self.scan_languages()
        
        if code not in self.available_languages:
            code = "en" if "en" in self.available_languages else list(self.available_languages.keys())[0]

        self.active_language_code = code
        lang_info = self.available_languages.get(code, {})
        
        # Dosyadan taze veriyi oku
        loaded_data = lang_info.get("data", {})
        if not loaded_data and "file" in lang_info and os.path.exists(lang_info["file"]):
            try:
                with open(lang_info["file"], "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    lang_info["data"] = loaded_data
            except Exception:
                loaded_data = {}

        self.translations = loaded_data
        
        # Dinleyicileri (UI güncelleme callback'leri) çağır
        for cb in list(self._refresh_callbacks):
            try:
                cb()
            except Exception:
                pass

        return True

    def register_refresh_callback(self, cb: Callable[[], None]):
        """Dil değiştiğinde UI öğelerini tazelemek için fonksiyon kaydeder."""
        if cb not in self._refresh_callbacks:
            self._refresh_callbacks.append(cb)

    def get_current_language_info(self) -> Dict[str, Any]:
        """Aktif dilin meta bilgilerini (code, name, flag) döner."""
        return self.available_languages.get(self.active_language_code, {
            "code": self.active_language_code,
            "name": self.active_language_code.capitalize(),
            "flag": DEFAULT_FLAGS.get(self.active_language_code, "🌐")
        })

    def get_language_list(self) -> List[Dict[str, Any]]:
        """Mevcut tüm dillerin listesini döner (Bayraklı seçim menüsü için)."""
        self.scan_languages()
        items = list(self.available_languages.values())
        # TR ve EN dillerini öne al, sonrakileri alfabetik sırala
        def _sort_key(item):
            c = item.get("code", "")
            if c == "tr": return (0, c)
            if c == "en": return (1, c)
            return (2, item.get("name", c))
        items.sort(key=_sort_key)
        return items

    def tr(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Verilen anahtarın aktif dildeki çevirisini döner.
        Bulunamazsa sırasıyla:
        1. Aktif dil sözlüğü
        2. İngilizce fallback sözlüğü
        3. Parametre olarak verilen default metin
        4. Key'in kendisi
        """
        val = self.translations.get(key)
        if val is None or val == "":
            val = self.fallback_translations.get(key)
        if val is None or val == "":
            val = default if default is not None else key

        if kwargs:
            try:
                val = val.format(**kwargs)
            except Exception:
                pass
        return str(val)


# Global yardımcı kısayol fonksiyonu
def _t(key: str, default: Optional[str] = None, **kwargs) -> str:
    return LanguageManager.get_instance().tr(key, default, **kwargs)
