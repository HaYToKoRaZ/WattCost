"""
WattCost HaYTooL - Yapılandırma ve Tema Yöneticisi Modülü
Uygulamanın tüm INI ayar tanımları, varsayılanları, renk paleti ve ölçekleme yardımcıları.
"""
import os
import sys
import json
import socket
import threading
import ctypes
import configparser

SINGLE_INSTANCE_PORT = 47892
APP_VERSION = "6.2"

def apply_dark_titlebar(window):
    """Windows 10/11 DWM Immersive Dark Mode uygulayarak beyaz pencere parlamasını önler."""
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1)
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value), ctypes.sizeof(value)
        )
        if res != 0:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 19,
                ctypes.byref(value), ctypes.sizeof(value)
            )
    except Exception:
        pass

def send_instance_command(cmd: str, timeout: float = 1.5):
    """Zaten açık olan WattCost kopyasına komut yollar ve yanıtını döner (ok: bool, resp: str)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(('127.0.0.1', SINGLE_INSTANCE_PORT))
        s.sendall(cmd.encode('utf-8', errors='ignore') + b'\n')
        resp = s.recv(4096).decode('utf-8', errors='ignore').strip()
        s.close()
        return True, resp
    except Exception as e:
        return False, str(e)

def notify_existing_instance():
    """Zaten açık olan WattCost kopyası varsa onu öne getir ve True dön."""
    ok, _ = send_instance_command('SHOW', timeout=0.6)
    return ok

def start_instance_listener(app_instance):
    """İlk kopya için arka planda 'SHOW' ve 'CMD:...' isteklerini dinleyen hafif soket sunucusu."""
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        server.listen(5)
        def _listen():
            while True:
                try:
                    conn, _ = server.accept()
                    raw = conn.recv(4096)
                    msg = raw.decode('utf-8', errors='ignore').strip()
                    if msg == 'SHOW':
                        app_instance.root.after(0, app_instance.bring_to_front)
                        conn.sendall(b'OK\n')
                    elif msg.startswith('CMD:'):
                        cmd_body = msg[4:].strip()
                        resp = "OK"
                        if hasattr(app_instance, 'handle_remote_cli'):
                            resp = app_instance.handle_remote_cli(cmd_body)
                        conn.sendall(resp.encode('utf-8', errors='ignore') + b'\n')
                    else:
                        conn.sendall(b'ERR: Unknown\n')
                    conn.close()
                except Exception:
                    break
        t = threading.Thread(target=_listen, daemon=True)
        t.start()
        return server
    except Exception:
        return None

if getattr(sys, 'frozen', False):
    _app_dir = os.path.dirname(sys.executable)
else:
    _mod_dir = os.path.dirname(os.path.abspath(__file__))
    _app_dir = os.path.dirname(_mod_dir) if os.path.basename(_mod_dir).lower() == "main" else _mod_dir

def get_asset_path(filename):
    """PyInstaller _MEIPASS (_internal) ve yerel çalışma dizinlerindeki asset yolunu döner."""
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, filename)
        if os.path.exists(p):
            return p
    if os.path.exists(filename):
        return filename
    p = os.path.join(_app_dir, filename)
    if os.path.exists(p):
        return p
    return filename

# --- Theme Factory: 8 Profesyonel Masaüstü Renk Paleti ---
AVAILABLE_THEMES = {
    "obsidian_cyber": {
        "name_tr": "İstanbul",
        "name_en": "Istanbul",
        "bg": "#090B11",
        "card_bg": "#121624",
        "card_border": "#1E263D",
        "card_inner": "#181D30",
        "text_primary": "#F1F5F9",
        "text_secondary": "#94A3B8",
        "text_muted": "#64748B",
        "accent_cyan": "#00E5FF",
        "accent_green": "#10B981",
        "accent_amber": "#F59E0B",
        "accent_rose": "#F43F5E",
        "accent_purple": "#8B5CF6",
        "btn_bg": "#1E263D",
        "btn_hover": "#2B3554",
        "btn_active": "#3B476F",
        "font_family": "Segoe UI",
    },
    "midnight_galaxy": {
        "name_tr": "Ankara",
        "name_en": "Ankara",
        "bg": "#0B0C14",
        "card_bg": "#141424",
        "card_border": "#2B2644",
        "card_inner": "#1D1C33",
        "text_primary": "#F5F3FF",
        "text_secondary": "#A78BFA",
        "text_muted": "#6D688D",
        "accent_cyan": "#38BDF8",
        "accent_green": "#34D399",
        "accent_amber": "#FBBF24",
        "accent_rose": "#F43F5E",
        "accent_purple": "#C084FC",
        "btn_bg": "#2B2644",
        "btn_hover": "#3B335E",
        "btn_active": "#4C417A",
        "font_family": "Segoe UI",
    },
    "arctic_frost": {
        "name_tr": "İzmir",
        "name_en": "Izmir",
        "bg": "#060D17",
        "card_bg": "#0E1A2C",
        "card_border": "#1A304F",
        "card_inner": "#14243D",
        "text_primary": "#F0F9FF",
        "text_secondary": "#7DD3FC",
        "text_muted": "#476A8A",
        "accent_cyan": "#00F5FF",
        "accent_green": "#2DD4BF",
        "accent_amber": "#FCD34D",
        "accent_rose": "#FB7185",
        "accent_purple": "#A78BFA",
        "btn_bg": "#1A304F",
        "btn_hover": "#254570",
        "btn_active": "#305A91",
        "font_family": "Segoe UI",
    },
    "ocean_depths": {
        "name_tr": "Antalya",
        "name_en": "Antalya",
        "bg": "#050F1A",
        "card_bg": "#0B1E33",
        "card_border": "#14375E",
        "card_inner": "#0E2845",
        "text_primary": "#E0F2FE",
        "text_secondary": "#38BDF8",
        "text_muted": "#4B7294",
        "accent_cyan": "#38BDF8",
        "accent_green": "#10B981",
        "accent_amber": "#F59E0B",
        "accent_rose": "#F43F5E",
        "accent_purple": "#818CF8",
        "btn_bg": "#14375E",
        "btn_hover": "#1D4E85",
        "btn_active": "#2666AD",
        "font_family": "Segoe UI",
    },
    "forest_canopy": {
        "name_tr": "Bursa",
        "name_en": "Bursa",
        "bg": "#06120D",
        "card_bg": "#0D2118",
        "card_border": "#1A3D2D",
        "card_inner": "#122E22",
        "text_primary": "#ECFDF5",
        "text_secondary": "#6EE7B7",
        "text_muted": "#45735E",
        "accent_cyan": "#2DD4BF",
        "accent_green": "#10B981",
        "accent_amber": "#FBBF24",
        "accent_rose": "#F87171",
        "accent_purple": "#A78BFA",
        "btn_bg": "#1A3D2D",
        "btn_hover": "#26543E",
        "btn_active": "#326C50",
        "font_family": "Segoe UI",
    },
    "golden_hour": {
        "name_tr": "Konya",
        "name_en": "Konya",
        "bg": "#120D08",
        "card_bg": "#211710",
        "card_border": "#3D2B1E",
        "card_inner": "#2B1E16",
        "text_primary": "#FFFBEB",
        "text_secondary": "#FDE68A",
        "text_muted": "#82664B",
        "accent_cyan": "#38BDF8",
        "accent_green": "#34D399",
        "accent_amber": "#F59E0B",
        "accent_rose": "#F43F5E",
        "accent_purple": "#C084FC",
        "btn_bg": "#3D2B1E",
        "btn_hover": "#573D2B",
        "btn_active": "#704F38",
        "font_family": "Segoe UI",
    },
    "sunset_boulevard": {
        "name_tr": "Adana",
        "name_en": "Adana",
        "bg": "#140718",
        "card_bg": "#250E2D",
        "card_border": "#471A57",
        "card_inner": "#33133D",
        "text_primary": "#FDF2F8",
        "text_secondary": "#F472B6",
        "text_muted": "#7E498A",
        "accent_cyan": "#00E5FF",
        "accent_green": "#10B981",
        "accent_amber": "#F59E0B",
        "accent_rose": "#F43F5E",
        "accent_purple": "#EC4899",
        "btn_bg": "#471A57",
        "btn_hover": "#63247A",
        "btn_active": "#7E2E9C",
        "font_family": "Segoe UI",
    },
    "modern_minimalist": {
        "name_tr": "Eskişehir",
        "name_en": "Eskisehir",
        "bg": "#0D0D0E",
        "card_bg": "#18181B",
        "card_border": "#2E2E33",
        "card_inner": "#212126",
        "text_primary": "#FAFAFA",
        "text_secondary": "#D4D4D8",
        "text_muted": "#71717A",
        "accent_cyan": "#38BDF8",
        "accent_green": "#34D399",
        "accent_amber": "#FBBF24",
        "accent_rose": "#F87171",
        "accent_purple": "#A78BFA",
        "btn_bg": "#2E2E33",
        "btn_hover": "#3F3F46",
        "btn_active": "#52525B",
        "font_family": "Segoe UI",
    },
}

THEME = dict(AVAILABLE_THEMES["obsidian_cyber"])

def set_active_theme(theme_key: str) -> bool:
    """Uygulamanın aktif görsel tema paletini günceller."""
    if theme_key in AVAILABLE_THEMES:
        THEME.update(AVAILABLE_THEMES[theme_key])
        return True
    return False

# --- %25 Büyütülmüş Dinamik UI & Tipografi Ölçeği ---
UI_SCALE = 1.25

def fs(size: int) -> int:
    """Tüm metin ve yazı tiplerini %25 ölçekleyerek döndürür."""
    return max(8, int(round(size * UI_SCALE)))

DEFAULT_CUSTOM_DEVICES = [
    {"id": "asus_mon", "name": "Asus VP249 (144Hz IPS)", "watt": 16.5, "active": True, "enabled": True},
    {"id": "samsung_mon", "name": "Samsung 2. Monitör (22\")", "watt": 19.0, "active": False, "enabled": True},
    {"id": "modem", "name": "Keenetic Hopper Modem", "watt": 10.0, "active": True, "enabled": True},
]

CONFIG_FILE_NAME = "WattCost. HaYTooL.ini"

def get_config_path(filename=CONFIG_FILE_NAME):
    """Kullanıcı tarafından düzenlenebilir INI/JSON dosyalarının EXE/Proje kök dizinindeki yolunu döner."""
    # 1. Öncelik: Uygulama/EXE kök dizini
    cand_app = os.path.join(_app_dir, filename)
    if os.path.exists(cand_app):
        return cand_app
    # 2. Çalışma dizini (CWD)
    if os.path.exists(filename):
        return os.path.abspath(filename)
    # 3. Henüz yoksa doğrudan uygulama kök dizinine hedefle
    return cand_app

CONFIG_METADATA = [
    # --- [Genel_Ayarlar] ---
    {"section": "Genel_Ayarlar", "key": "always_on_top", "default": False,
     "tr": "Uygulama penceresi her zaman diger pencerelerin ustunde sabitlensin mi? (true / false)",
     "en": "Keep application window always on top of other windows? (true / false)"},
    {"section": "Genel_Ayarlar", "key": "close_to_tray", "default": True,
     "tr": "Kapat (X) butonuna basildiginda sistem tepsisinde arka planda calismaya devam etsin mi? (true / false)",
     "en": "Minimize to system tray when the close (X) button is clicked? (true / false)"},
    {"section": "Genel_Ayarlar", "key": "power_plan_toast", "default": True,
     "tr": "Guc plani degistiginde Windows bildirim baloncugu (Toast) gosterilsin mi? (true / false)",
     "en": "Show Windows toast notification when power plan changes? (true / false)"},
    {"section": "Genel_Ayarlar", "key": "power_plan_sound", "default": True,
     "tr": "Guc plani degistiginde sesli uyari calinsin mi? (true / false)",
     "en": "Play audio alert when power plan changes? (true / false)"},
    {"section": "Genel_Ayarlar", "key": "ui_tab", "default": "genel",
     "tr": "Acilista aktif olacak arayuz sekmesi ('genel' / 'oyun' / 'priz' / 'gecmis')",
     "en": "Startup active UI tab ('genel' / 'oyun' / 'priz' / 'gecmis')"},
    {"section": "Genel_Ayarlar", "key": "language", "default": "auto",
     "tr": "Arayuz dili ('auto', 'tr', 'en' veya languages klasorundeki ozel dil)",
     "en": "UI language ('auto', 'tr', 'en' or custom language in languages folder)"},
    {"section": "Genel_Ayarlar", "key": "theme", "default": "obsidian_cyber",
     "tr": "Arayuz temasi ('obsidian_cyber', 'midnight_galaxy', 'arctic_frost', 'ocean_depths', 'forest_canopy', 'golden_hour', 'sunset_boulevard', 'modern_minimalist')",
     "en": "UI theme ('obsidian_cyber', 'midnight_galaxy', 'arctic_frost', 'ocean_depths', 'forest_canopy', 'golden_hour', 'sunset_boulevard', 'modern_minimalist')"},
    {"section": "Genel_Ayarlar", "key": "window_geometry", "default": "",
     "tr": "Son pencere konumu ve boyutu (orn. 1325x962+298+49); bos = varsayilan olcu",
     "en": "Last window position and size (e.g. 1325x962+298+49); empty = default size"},
    {"section": "Genel_Ayarlar", "key": "window_maximized", "default": False,
     "tr": "Pencere tam ekran (zoom) durumunda kapatildi mi? (true / false)",
     "en": "Was the window maximized when closed? (true / false)"},

    # --- [Tarife_Ve_Donanim] ---
    {"section": "Tarife_Ve_Donanim", "key": "kwh_price_tl", "default": 4.86,
     "tr": "Elektrik birim fiyati (TL/kWh)",
     "en": "Electricity unit price (TL/kWh)"},
    {"section": "Tarife_Ve_Donanim", "key": "tariff_tier", "default": "high",
     "tr": "Elektrik tarifesi kademesi ('low'=Dusuk 3.24, 'high'=Yuksek 4.86, 'custom'=Ozel)",
     "en": "Electricity tariff tier ('low'=3.24, 'high'=4.86, 'custom'=Custom)"},
    {"section": "Tarife_Ve_Donanim", "key": "case_base_w", "default": 46.7,
     "tr": "Kasa taban guc tuketimi (Anakart, fanlar, RGB vb. watt)",
     "en": "Base case power consumption (Motherboard, fans, RGB etc. watts)"},
    {"section": "Tarife_Ve_Donanim", "key": "psu_efficiency", "default": 0.85,
     "tr": "Guc kaynagi (PSU) verimlilik katsayisi (0.50 - 1.00 arasi)",
     "en": "Power supply unit (PSU) efficiency coefficient (between 0.50 and 1.00)"},
    {"section": "Tarife_Ve_Donanim", "key": "asus_monitor_w", "default": 16.5,
     "tr": "1. Monitor guc tuketimi (Watt)",
     "en": "Primary monitor power consumption (Watts)"},
    {"section": "Tarife_Ve_Donanim", "key": "asus_mon_active", "default": True,
     "tr": "1. Monitor hesaplamaya dahil edilsin mi? (true / false)",
     "en": "Include primary monitor in power calculation? (true / false)"},
    {"section": "Tarife_Ve_Donanim", "key": "samsung_monitor_w", "default": 19.0,
     "tr": "2. Monitor guc tuketimi (Watt)",
     "en": "Secondary monitor power consumption (Watts)"},
    {"section": "Tarife_Ve_Donanim", "key": "samsung_mon_active", "default": False,
     "tr": "2. Monitor hesaplamaya dahil edilsin mi? (true / false)",
     "en": "Include secondary monitor in power calculation? (true / false)"},
    {"section": "Tarife_Ve_Donanim", "key": "modem_w", "default": 10.0,
     "tr": "Modem guc tuketimi (Watt)",
     "en": "Modem/Router power consumption (Watts)"},
    {"section": "Tarife_Ve_Donanim", "key": "modem_active", "default": True,
     "tr": "Modem hesaplamaya dahil edilsin mi? (true / false)",
     "en": "Include modem in power calculation? (true / false)"},

    # --- [Harici_Cihazlar] ---
    {"section": "Harici_Cihazlar", "key": "auto_detect_second_monitor", "default": True,
     "tr": "2. monitor bagliysa cihaz listesinde otomatik isaretlensin mi? (true / false)",
     "en": "Auto-check the 2nd monitor in the device list when it is connected? (true / false)"},
    {"section": "Harici_Cihazlar", "key": "custom_devices_json", "default": json.dumps(DEFAULT_CUSTOM_DEVICES, ensure_ascii=False),
     "tr": "Prizden cekilen ek harici cihazlar listesi (JSON formati)",
     "en": "External peripherals list drawn from wall outlet (JSON format)"},

    # --- [Zalman_Pompa] ---
    {"section": "Zalman_Pompa", "key": "zalman_active", "default": True,
     "tr": "Zalman Alpha2 LCD pompa ekranina sicaklik aktarimi aktif olsun mu? (true / false)",
     "en": "Enable temperature transfer to Zalman Alpha2 LCD pump? (true / false)"},
    {"section": "Zalman_Pompa", "key": "zalman_source", "default": "cpu",
     "tr": "Zalman LCD ekraninda gosterilecek sicaklik kaynagi ('cycle', 'cpu', 'gpu', 'max')",
     "en": "Temperature source to display on Zalman LCD ('cycle', 'cpu', 'gpu', 'max')"},
    {"section": "Zalman_Pompa", "key": "zalman_blank_sec", "default": 4,
     "tr": "Dongusel modda gecisler arasi ekranin kapali/bos kalma suresi (saniye)",
     "en": "Duration of dark/blank screen between temperature switches in cycle mode (seconds)"},
    {"section": "Zalman_Pompa", "key": "zalman_temp_sec", "default": 10,
     "tr": "Dongusel modda sicakligin ekranda kalma suresi (saniye)",
     "en": "Duration to display temperature in cycle mode (seconds)"},

    # --- [Kulaklik_Batarya] ---
    {"section": "Kulaklik_Batarya", "key": "headset_usb_active", "default": True,
     "tr": "USB kulaklik (SteelSeries Arctis) bataryasi gosterilsin mi? (true / false)",
     "en": "Show USB headset (SteelSeries Arctis) battery? (true / false)"},
    {"section": "Kulaklik_Batarya", "key": "headset_bt_active", "default": True,
     "tr": "Bluetooth kulaklik bataryasi gosterilsin mi? (Windows HFP) (true / false)",
     "en": "Show Bluetooth headset battery? (Windows HFP) (true / false)"},
    {"section": "Kulaklik_Batarya", "key": "headset_exe", "default": "",
     "tr": "Istege bagli yedek: HeadsetControl araci yolu. Bos birakilirsa harici arac hic kullanilmaz (batarya USB HID ile okunur)",
     "en": "Optional fallback: HeadsetControl tool path. Leave empty to never use an external tool (battery is read via USB HID)"},
    {"section": "Kulaklik_Batarya", "key": "headset_poll_sec", "default": 30,
     "tr": "Kulaklik batarya sorgusu arasi (saniye, en az 10)",
     "en": "Headset battery poll interval (seconds, minimum 10)"},

    # --- [Sistem_Tepsisi] ---
    {"section": "Sistem_Tepsisi", "key": "tray_mode", "default": "power_w",
     "tr": "Sistem tepsisi simge modu ('power_w', 'dual_temp', 'cpu_uti', 'gpu_uti', 'cpu_temp', 'gpu_temp', 'hourly_tl', 'logo')",
     "en": "System tray icon mode ('power_w', 'dual_temp', 'cpu_uti', 'gpu_uti', 'cpu_temp', 'gpu_temp', 'hourly_tl', 'logo')"},
    {"section": "Sistem_Tepsisi", "key": "tray_font", "default": "bahnschrift",
     "tr": "Sistem tepsisi yazi tipi fontu ('bahnschrift', 'segoe', 'arial', 'consola', 'impact')",
     "en": "System tray font ('bahnschrift', 'segoe', 'arial', 'consola', 'impact')"},
    {"section": "Sistem_Tepsisi", "key": "tray_font_size", "default": "max",
     "tr": "Sistem tepsisi yazi boyutu ('small', 'normal', 'large', 'xlarge', 'max')",
     "en": "System tray font size ('small', 'normal', 'large', 'xlarge', 'max')"},
    {"section": "Sistem_Tepsisi", "key": "tray_bg", "default": "transparent",
     "tr": "Sistem tepsisi simge arka plani ('transparent', 'dark', 'cyan', 'green', 'rose', 'amber', 'white')",
     "en": "System tray icon background ('transparent', 'dark', 'cyan', 'green', 'rose', 'amber', 'white')"},
    {"section": "Sistem_Tepsisi", "key": "tray_fg", "default": "auto",
     "tr": "Sistem tepsisi metin rengi ('auto', 'cyan', 'green', 'amber', 'rose', 'white', 'black', 'purple')",
     "en": "System tray text color ('auto', 'cyan', 'green', 'amber', 'rose', 'white', 'black', 'purple')"},
    {"section": "Sistem_Tepsisi", "key": "tray_watt_warn", "default": 250.0,
     "tr": "Sistem tepsisi sari/orta yuk renk esigi (Watt)",
     "en": "System tray yellow/medium load threshold (Watts)"},
    {"section": "Sistem_Tepsisi", "key": "tray_watt_crit", "default": 450.0,
     "tr": "Sistem tepsisi kirmizi/yuksek yuk renk esigi (Watt)",
     "en": "System tray red/high load threshold (Watts)"},

    # --- [RTSS_Oyun_Ici_Gosterge] ---
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_enabled", "default": True,
     "tr": "RivaTuner Statistics Server (RTSS) OSD gostergesi aktif olsun mu? (true / false)",
     "en": "Enable RivaTuner Statistics Server (RTSS) in-game OSD? (true / false)"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_hotkey", "default": "Alt+Shift+R",
     "tr": "OSD acma/kapatma genel kisayol tusu ('Alt+Shift+R', 'Ctrl+Alt+R', 'F9', 'F10', 'F11', 'F12', 'Insert', 'Home', 'Pause', 'ScrollLock' vb.)",
     "en": "Global hotkey to toggle in-game OSD on/off ('Alt+Shift+R', 'Ctrl+Alt+R', 'F9', 'F10', 'F11', 'F12', 'Insert', 'Home', 'Pause', 'ScrollLock' etc.)"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_hotkey_vk", "default": 82,
     "tr": "Kisayol tusu Windows Virtual-Key (VK) kodu (Alt+Shift+R icin 82)",
     "en": "Hotkey Windows Virtual-Key (VK) code (82 for Alt+Shift+R)"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_hotkey_mod", "default": 5,
     "tr": "Kisayol tusu degistirici tus kodu (0=Yok, Alt=1, Ctrl=2, Ctrl+Alt=3, Shift=4, Alt+Shift=5)",
     "en": "Hotkey modifier key mask (0=None, Alt=1, Ctrl=2, Ctrl+Alt=3, Shift=4, Alt+Shift=5)"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_multiline", "default": False,
     "tr": "Dikey liste gorunumu (Her metrik ayri satirda) (true = Dikey / false = Yatay)",
     "en": "Vertical list view (Each metric on its own line) (true = Vertical / false = Horizontal)"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_multiline_h2", "default": False,
     "tr": "Ikinci satiri aktif et (Sadece yatay modda gecerli) (true / false)",
     "en": "Enable second line (Only valid in horizontal mode) (true / false)"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_sep_style", "default": "single",
     "tr": "Yatay modda ayrac stili ('single'=Tek Bosluk, 'compact'=Cift Bosluk, 'pipe'=Cizgi |, 'slash'=Bolu /, 'dash'=Tire -)",
     "en": "Separator style in horizontal mode ('single'=Single space, 'compact'=Double space, 'pipe'=Pipe |, 'slash'=Slash /, 'dash'=Dash -)"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_sep_color", "default": "#64748B",
     "tr": "Yatay modda ayrac rengi (HEX formatinda orn: #64748B)",
     "en": "Separator color in horizontal mode (HEX format e.g. #64748B)"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_margin_x", "default": 1,
     "tr": "RTSS OSD yatay kenar boslugu (0: sifir, 1-6 karakter)",
     "en": "RTSS OSD horizontal margin (0: flush, 1-6 characters)"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_margin_y", "default": 1,
     "tr": "RTSS OSD dikey kenar boslugu (0: sifir, 1-5 adim)",
     "en": "RTSS OSD vertical margin (0: flush, 1-5 steps)"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_keep_zeros", "default": True,
     "tr": "Deger 0 olsa bile metrik ekranda tutulsun mu? Titremeyi ve kaymayi onler (true / false)",
     "en": "Keep metric visible on screen even if value is 0? Prevents flickering (true / false)"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_position", "default": "top_right",
     "tr": "RTSS OSD ekran konumu ('top_left', 'top_right', 'bottom_left', 'bottom_right')",
     "en": "RTSS in-game OSD position ('top_left', 'top_right', 'bottom_left', 'bottom_right')"},
    {"section": "RTSS_Oyun_Ici_Gosterge", "key": "rtss_show_kwh", "default": False,
     "tr": "Saatlik tuketimin yaninda kWh birimini de goster (true / false)",
     "en": "Show kWh unit alongside hourly consumption (true / false)"},

    # --- [RTSS_Metrikleri] (Kullanıcı Talebine Göre Varsayılanlar: FPS='', GPU='G', CPU='C', RAM='R', Hourly='T') ---
    {"section": "RTSS_Metrikleri", "key": "rtss_show_fps", "default": True, "tr": "FPS (Kare Hizi) gosterilsin mi? (true / false)", "en": "Show FPS (Frame Rate)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_fps", "default": "", "tr": "FPS etiketi metni (Bos birakilabilir)", "en": "FPS label text (Can be empty)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_fps", "default": "#F43F5E", "tr": "FPS metin rengi (HEX)", "en": "FPS text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_fps", "default": "100", "tr": "FPS yazi boyutu olcegi (%100 standart)", "en": "FPS text size scale (%100 standard)"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_gpu_uti", "default": True, "tr": "GPU kullanim yuzdesi (%) gosterilsin mi? (true / false)", "en": "Show GPU usage percentage (%)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_gpu_uti", "default": "G", "tr": "GPU kullanim etiketi", "en": "GPU usage label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_gpu_uti", "default": "#00E5FF", "tr": "GPU kullanim metin rengi (HEX)", "en": "GPU usage text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_gpu_uti", "default": "100", "tr": "GPU kullanim yazi boyutu", "en": "GPU usage text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_gpu_temp", "default": False, "tr": "GPU sicakligi (degC) gosterilsin mi? (true / false)", "en": "Show GPU temperature (degC)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_gpu_temp", "default": "GPU-C", "tr": "GPU sicaklik etiketi", "en": "GPU temperature label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_gpu_temp", "default": "#00E5FF", "tr": "GPU sicaklik metin rengi (HEX)", "en": "GPU temperature text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_gpu_temp", "default": "100", "tr": "GPU sicaklik yazi boyutu", "en": "GPU temperature text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_gpu_w", "default": False, "tr": "GPU guc tuketimi (Watt) gosterilsin mi? (true / false)", "en": "Show GPU power consumption (Watts)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_gpu_w", "default": "GPU-W", "tr": "GPU guc etiketi", "en": "GPU power label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_gpu_w", "default": "#00E5FF", "tr": "GPU guc metin rengi (HEX)", "en": "GPU power text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_gpu_w", "default": "100", "tr": "GPU guc yazi boyutu", "en": "GPU power text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_gpu_clk", "default": False, "tr": "GPU cekirdek frekansi (MHz) gosterilsin mi? (true / false)", "en": "Show GPU core clock (MHz)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_gpu_clk", "default": "GPU-CLK", "tr": "GPU frekans etiketi", "en": "GPU core clock label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_gpu_clk", "default": "#38BDF8", "tr": "GPU frekans metin rengi (HEX)", "en": "GPU core clock text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_gpu_clk", "default": "100", "tr": "GPU frekans yazi boyutu", "en": "GPU core clock text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_vram", "default": False, "tr": "Ekran karti bellek (VRAM GB) gosterilsin mi? (true / false)", "en": "Show GPU VRAM usage (GB)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_vram", "default": "VRAM", "tr": "VRAM etiketi", "en": "VRAM label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_vram", "default": "#818CF8", "tr": "VRAM metin rengi (HEX)", "en": "VRAM text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_vram", "default": "100", "tr": "VRAM yazi boyutu", "en": "VRAM text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_cpu_uti", "default": True, "tr": "CPU islemci kullanim yuzdesi (%) gosterilsin mi? (true / false)", "en": "Show CPU usage percentage (%)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_cpu_uti", "default": "C", "tr": "CPU kullanim etiketi", "en": "CPU usage label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_cpu_uti", "default": "#F59E0B", "tr": "CPU kullanim metin rengi (HEX)", "en": "CPU usage text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_cpu_uti", "default": "100", "tr": "CPU kullanim yazi boyutu", "en": "CPU usage text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_cpu_temp", "default": False, "tr": "CPU sicakligi (degC) gosterilsin mi? (true / false)", "en": "Show CPU temperature (degC)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_cpu_temp", "default": "CPU-C", "tr": "CPU sicaklik etiketi", "en": "CPU temperature label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_cpu_temp", "default": "#F59E0B", "tr": "CPU sicaklik metin rengi (HEX)", "en": "CPU temperature text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_cpu_temp", "default": "100", "tr": "CPU sicaklik yazi boyutu", "en": "CPU temperature text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_cpu_w", "default": False, "tr": "CPU paket guc tuketimi (Watt) gosterilsin mi? (true / false)", "en": "Show CPU package power (Watts)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_cpu_w", "default": "CPU-W", "tr": "CPU guc etiketi", "en": "CPU power label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_cpu_w", "default": "#F59E0B", "tr": "CPU guc metin rengi (HEX)", "en": "CPU power text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_cpu_w", "default": "100", "tr": "CPU guc yazi boyutu", "en": "CPU power text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_cpu_clk", "default": False, "tr": "CPU saat frekansi (MHz) gosterilsin mi? (true / false)", "en": "Show CPU core clock (MHz)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_cpu_clk", "default": "CPU-CLK", "tr": "CPU saat frekansi etiketi", "en": "CPU core clock label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_cpu_clk", "default": "#FCD34D", "tr": "CPU saat frekansi metin rengi (HEX)", "en": "CPU core clock text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_cpu_clk", "default": "100", "tr": "CPU saat frekansi yazi boyutu", "en": "CPU core clock text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_ram", "default": True, "tr": "RAM kullanim yuzdesi (%) gosterilsin mi? (true / false)", "en": "Show RAM usage percentage (%)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_ram", "default": "R", "tr": "RAM etiketi", "en": "RAM label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_ram", "default": "#A855F7", "tr": "RAM metin rengi (HEX)", "en": "RAM text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_ram", "default": "100", "tr": "RAM yazi boyutu", "en": "RAM text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_fan", "default": False, "tr": "Kasa / CPU fan devri (RPM) gosterilsin mi? (true / false)", "en": "Show fan speed (RPM)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_fan", "default": "FAN", "tr": "Fan hizi etiketi", "en": "Fan speed label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_fan", "default": "#34D399", "tr": "Fan hizi metin rengi (HEX)", "en": "Fan speed text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_fan", "default": "100", "tr": "Fan hizi yazi boyutu", "en": "Fan speed text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_power", "default": True, "tr": "Prizden cekilen anlik toplam guc (Watt) gosterilsin mi? (true / false)", "en": "Show total real power drawn from wall outlet (Watts)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_power", "default": "GUC", "tr": "Prizden guc etiketi", "en": "Wall power label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_power", "default": "#00E5FF", "tr": "Prizden guc metin rengi (HEX)", "en": "Wall power text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_power", "default": "100", "tr": "Prizden guc yazi boyutu", "en": "Wall power text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_hourly", "default": True, "tr": "Saatlik tahmini tuketim bedeli (TL/sa) gosterilsin mi? (true / false)", "en": "Show estimated hourly electricity cost (TL/hr)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_hourly", "default": "T", "tr": "Saatlik maliyet etiketi", "en": "Hourly cost label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_hourly", "default": "#10B981", "tr": "Saatlik maliyet metin rengi (HEX)", "en": "Hourly cost text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_hourly", "default": "100", "tr": "Saatlik maliyet yazi boyutu", "en": "Hourly cost text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_session", "default": False, "tr": "Mevcut oturumun toplam elektrik harcamasi (TL) gosterilsin mi? (true / false)", "en": "Show current session total electricity cost (TL)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_session", "default": "OTURUM", "tr": "Oturum maliyeti etiketi", "en": "Session cost label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_session", "default": "#FBBF24", "tr": "Oturum maliyeti metin rengi (HEX)", "en": "Session cost text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_session", "default": "100", "tr": "Oturum maliyeti yazi boyutu", "en": "Session cost text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_today", "default": False, "tr": "Bugunun toplam elektrik harcamasi (TL) gosterilsin mi? (true / false)", "en": "Show today's total electricity cost (TL)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_today", "default": "BUGUN", "tr": "Bugun maliyeti etiketi", "en": "Today's cost label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_today", "default": "#C084FC", "tr": "Bugun maliyeti metin rengi (HEX)", "en": "Today's cost text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_today", "default": "100", "tr": "Bugun maliyeti yazi boyutu", "en": "Today's cost text size"},

    {"section": "RTSS_Metrikleri", "key": "rtss_show_month", "default": False, "tr": "Bu ayin toplam elektrik harcamasi (TL) gosterilsin mi? (true / false)", "en": "Show current month total electricity cost (TL)? (true / false)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_label_month", "default": "AY", "tr": "Bu ay maliyeti etiketi", "en": "Current month cost label"},
    {"section": "RTSS_Metrikleri", "key": "rtss_color_month", "default": "#EC4899", "tr": "Bu ay maliyeti metin rengi (HEX)", "en": "Current month cost text color (HEX)"},
    {"section": "RTSS_Metrikleri", "key": "rtss_size_month", "default": "100", "tr": "Bu ay maliyeti yazi boyutu", "en": "Current month cost text size"},

    # --- [Guc_Yonetimi] ---
    {"section": "Guc_Yonetimi", "key": "smart_switch_enabled", "default": False, "tr": "4 Kademeli akilli otomatik guc plani gecisi etkin mi?", "en": "Is 4-tier smart power plan auto switch enabled?"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_tier_count", "default": 4, "tr": "Akilli gecis kademe sayisi (2, 3 veya 4)", "en": "Smart switch tier count (2, 3 or 4)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_hz_enabled", "default": True, "tr": "Akilli monitor yenileme hizi (Hz) otomasyonu etkin mi?", "en": "Is smart monitor refresh rate (Hz) automation enabled?"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t1_guid", "default": "", "tr": "Kademe 1 (Bosta / Ultra Tasarruf) guc plani GUID", "en": "Tier 1 (Idle / Eco) power plan GUID"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t2_guid", "default": "", "tr": "Kademe 2 (Dusuk / Gunluk & Medya) guc plani GUID", "en": "Tier 2 (Low / Daily & Media) power plan GUID"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t3_guid", "default": "", "tr": "Kademe 3 (Orta / Agir Is & Multitask) guc plani GUID", "en": "Tier 3 (Medium / Multitask) power plan GUID"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t4_guid", "default": "", "tr": "Kademe 4 (Maksimum / Oyun & Render) guc plani GUID", "en": "Tier 4 (Max / Gaming & Render) power plan GUID"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t1_hz", "default": 0, "tr": "Kademe 1 hedef monitor yenileme hizi (Hz) (0 = Degistirme)", "en": "Tier 1 target monitor refresh rate (Hz) (0 = Do not change)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t2_hz", "default": 0, "tr": "Kademe 2 hedef monitor yenileme hizi (Hz) (0 = Degistirme)", "en": "Tier 2 target monitor refresh rate (Hz) (0 = Do not change)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t3_hz", "default": 0, "tr": "Kademe 3 hedef monitor yenileme hizi (Hz) (0 = Degistirme)", "en": "Tier 3 target monitor refresh rate (Hz) (0 = Do not change)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t4_hz", "default": 0, "tr": "Kademe 4 hedef monitor yenileme hizi (Hz) (0 = Degistirme)", "en": "Tier 4 target monitor refresh rate (Hz) (0 = Do not change)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t1_hz2", "default": 0, "tr": "Kademe 1 ikinci monitor hedef Hz (0 = Degistirme)", "en": "Tier 1 second monitor target Hz (0 = Do not change)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t2_hz2", "default": 0, "tr": "Kademe 2 ikinci monitor hedef Hz (0 = Degistirme)", "en": "Tier 2 second monitor target Hz (0 = Do not change)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t3_hz2", "default": 0, "tr": "Kademe 3 ikinci monitor hedef Hz (0 = Degistirme)", "en": "Tier 3 second monitor target Hz (0 = Do not change)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t4_hz2", "default": 0, "tr": "Kademe 4 ikinci monitor hedef Hz (0 = Degistirme)", "en": "Tier 4 second monitor target Hz (0 = Do not change)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t2_gpu", "default": 15.0, "tr": "Kademe 2 gecis GPU yuku (%)", "en": "Tier 2 GPU load threshold (%)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t2_cpu", "default": 20.0, "tr": "Kademe 2 gecis CPU yuku (%)", "en": "Tier 2 CPU load threshold (%)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t3_gpu", "default": 40.0, "tr": "Kademe 3 gecis GPU yuku (%)", "en": "Tier 3 GPU load threshold (%)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t3_cpu", "default": 45.0, "tr": "Kademe 3 gecis CPU yuku (%)", "en": "Tier 3 CPU load threshold (%)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t4_gpu", "default": 70.0, "tr": "Kademe 4 gecis GPU yuku (%)", "en": "Tier 4 GPU load threshold (%)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t4_cpu", "default": 75.0, "tr": "Kademe 4 gecis CPU yuku (%)", "en": "Tier 4 CPU load threshold (%)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_use_rtss", "default": True, "tr": "RTSS 3D oyun algilandiginda dogrudan Kademe 4'e gec", "en": "Switch to Tier 4 on RTSS game detection"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_use_watt", "default": True, "tr": "Priz gucu esigi asildiginda dogrudan Kademe 4'e gec", "en": "Switch to Tier 4 when wall power exceeds threshold"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_watt_threshold", "default": 260.0, "tr": "Kademe 4 priz guc tetikleyici esigi (Watt)", "en": "Tier 4 wall power trigger threshold (Watts)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_trigger_sec", "default": 2, "tr": "Yuksek kademeye gecis gecikmesi (sn)", "en": "Delay before switching to higher tier (sec)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_revert_sec", "default": 5, "tr": "Dusuk kademeye donus gecikmesi (sn)", "en": "Delay before reverting to lower tier (sec)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_sound", "default": True, "tr": "Akilli gecislerde sesli uyari calinsin mi? (true / false)", "en": "Play audio alert on smart switch transitions? (true / false)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_toast", "default": True, "tr": "Akilli gecislerde toast bildirimi gosterilsin mi? (true / false)", "en": "Show toast notification on smart switch transitions? (true / false)"},
]

DEFAULT_CONFIG = {item["key"]: item["default"] for item in CONFIG_METADATA}


class ConfigManagerMixin:
    """Uygulamanın INI dosyası ile okuma ve yazma işlemlerini yöneten mixin sınıfı."""

    CONFIG_FILE = CONFIG_FILE_NAME
    CONFIG_METADATA = CONFIG_METADATA
    DEFAULT_CONFIG = DEFAULT_CONFIG

    def _generate_ini_content(self) -> str:
        lines = [
            "; ==============================================================================",
            "; WattCost HaYTooL - Yapilandirma Dosyasi (Configuration File)",
            "; TR: Bu dosya uygulama ayarlarini saklar. Degerleri buradan degistirebilirsiniz.",
            "; EN: This file stores application settings. You can edit values here.",
            "; ==============================================================================",
            ""
        ]
        sections = {}
        for item in self.CONFIG_METADATA:
            sec = item["section"]
            if sec not in sections:
                sections[sec] = []
            sections[sec].append(item)

        for sec, items in sections.items():
            lines.append(f"[{sec}]")
            for item in items:
                k = item["key"]
                def_v = item["default"]
                cur_v = self.config.get(k, def_v)
                val_str = str(cur_v).lower() if isinstance(cur_v, bool) else str(cur_v)
                def_str = str(def_v).lower() if isinstance(def_v, bool) else str(def_v)
                lines.append(f"; TR: {item['tr']}")
                lines.append(f"; EN: {item['en']}")
                lines.append(f"; Varsayilan / Default: {def_str}")
                lines.append(f"{k} = {val_str}")
                lines.append("")
        return "\n".join(lines)

    def load_config(self):
        self.config = self.DEFAULT_CONFIG.copy()
        ini_path = get_config_path(self.CONFIG_FILE)
        self.CONFIG_FILE = ini_path
        loaded = False
        if os.path.exists(ini_path):
            try:
                cp = configparser.ConfigParser()
                cp.read(ini_path, encoding="utf-8")
                for sec in cp.sections():
                    for k, v in cp.items(sec):
                        if k in self.DEFAULT_CONFIG:
                            def_v = self.DEFAULT_CONFIG[k]
                            if isinstance(def_v, bool):
                                self.config[k] = v.lower() in ("true", "1", "yes", "on")
                            elif isinstance(def_v, int) and not isinstance(def_v, bool):
                                try: self.config[k] = int(v)
                                except ValueError: pass
                            elif isinstance(def_v, float):
                                try: self.config[k] = float(v)
                                except ValueError: pass
                            else:
                                self.config[k] = v
                loaded = True
            except Exception:
                pass

        if not loaded and os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.config.update(saved)
                loaded = True
                self.save_config()
            except Exception:
                pass

        # Harici Cihazlar JSON listesini ayrıştır veya varsayılanı yükle
        dev_json = self.config.get("custom_devices_json", "")
        if dev_json:
            try:
                parsed = json.loads(dev_json)
                if isinstance(parsed, list) and len(parsed) > 0:
                    self.custom_devices = parsed
                else:
                    self.custom_devices = [dict(d) for d in DEFAULT_CUSTOM_DEVICES]
            except Exception:
                self.custom_devices = [dict(d) for d in DEFAULT_CUSTOM_DEVICES]
        else:
            self.custom_devices = [dict(d) for d in DEFAULT_CUSTOM_DEVICES]
            # Eski INI'den özel değerler varsa aktar
            for d in self.custom_devices:
                if d.get("id") == "asus_mon":
                    d["watt"] = float(self.config.get("asus_monitor_w", 16.5))
                    d["active"] = bool(self.config.get("asus_mon_active", True))
                elif d.get("id") == "samsung_mon":
                    d["watt"] = float(self.config.get("samsung_monitor_w", 19.0))
                    d["active"] = bool(self.config.get("samsung_mon_active", False))
                elif d.get("id") == "modem":
                    d["watt"] = float(self.config.get("modem_w", 10.0))
                    d["active"] = bool(self.config.get("modem_active", True))

        # Aktif görsel temayı yükle
        th_key = self.config.get("theme", "obsidian_cyber")
        set_active_theme(th_key)

        if not loaded:
            self.save_config()

    def sync_legacy_device_vars(self):
        """Eski checkbox değişkenleri ile custom_devices listesini senkronize eder."""
        if not hasattr(self, 'custom_devices'):
            return
        for d in self.custom_devices:
            did = d.get("id")
            if did == "asus_mon" and hasattr(self, 'asus_var'):
                self.asus_var.set(bool(d.get("active", True)))
            elif did == "samsung_mon" and hasattr(self, 'samsung_var'):
                self.samsung_var.set(bool(d.get("active", False)))
            elif did == "modem" and hasattr(self, 'modem_var'):
                self.modem_var.set(bool(d.get("active", True)))

    def save_config(self):
        if hasattr(self, 'custom_devices') and self.custom_devices is not None:
            self.config["custom_devices_json"] = json.dumps(self.custom_devices, ensure_ascii=False)
            for d in self.custom_devices:
                did = d.get("id")
                if did == "asus_mon":
                    self.config["asus_monitor_w"] = float(d.get("watt", 16.5))
                    self.config["asus_mon_active"] = bool(d.get("active", True))
                elif did == "samsung_mon":
                    self.config["samsung_monitor_w"] = float(d.get("watt", 19.0))
                    self.config["samsung_mon_active"] = bool(d.get("active", False))
                elif did == "modem":
                    self.config["modem_w"] = float(d.get("watt", 10.0))
                    self.config["modem_active"] = bool(d.get("active", True))

        if hasattr(self, 'asus_var'):
            self.config["asus_mon_active"] = self.asus_var.get()
        if hasattr(self, 'samsung_var'):
            self.config["samsung_mon_active"] = self.samsung_var.get()
        if hasattr(self, 'modem_var'):
            self.config["modem_active"] = self.modem_var.get()
        if hasattr(self, 'on_top_var'):
            self.config["always_on_top"] = self.on_top_var.get()
        if hasattr(self, 'zalman_active_var'):
            self.config["zalman_active"] = self.zalman_active_var.get()
        if hasattr(self, 'zalman_source_var'):
            self.config["zalman_source"] = self.zalman_source_var.get()
        if hasattr(self, 'zalman_blank_var'):
            try: self.config["zalman_blank_sec"] = max(1, int(self.zalman_blank_var.get()))
            except Exception: pass
        if hasattr(self, 'zalman_temp_var'):
            try: self.config["zalman_temp_sec"] = max(1, int(self.zalman_temp_var.get()))
            except Exception: pass
        if hasattr(self, 'smart_switch_var'):
            self.config["smart_switch_enabled"] = self.smart_switch_var.get()
        if hasattr(self, 'smart_hz_auto_var'):
            self.config["smart_switch_hz_enabled"] = self.smart_hz_auto_var.get()
        if hasattr(self, 'smart_switcher') and self.smart_switcher:
            if getattr(self.smart_switcher, 'tier1_plan_guid', None):
                self.config["smart_switch_t1_guid"] = self.smart_switcher.tier1_plan_guid
            if getattr(self.smart_switcher, 'tier2_plan_guid', None):
                self.config["smart_switch_t2_guid"] = self.smart_switcher.tier2_plan_guid
            if getattr(self.smart_switcher, 'tier3_plan_guid', None):
                self.config["smart_switch_t3_guid"] = self.smart_switcher.tier3_plan_guid
            if getattr(self.smart_switcher, 'tier4_plan_guid', None):
                self.config["smart_switch_t4_guid"] = self.smart_switcher.tier4_plan_guid
        if hasattr(self, 'smart_use_rtss_var'):
            self.config["smart_switch_use_rtss"] = self.smart_use_rtss_var.get()
        if hasattr(self, 'smart_use_watt_var'):
            self.config["smart_switch_use_watt"] = self.smart_use_watt_var.get()
        if hasattr(self, 'smart_switch_sound_var'):
            self.config["smart_switch_sound"] = self.smart_switch_sound_var.get()
        if hasattr(self, 'smart_switch_toast_var'):
            self.config["smart_switch_toast"] = self.smart_switch_toast_var.get()
        try:
            self.CONFIG_FILE = get_config_path(self.CONFIG_FILE)
            content = self._generate_ini_content()
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass


def load_config_dict() -> dict:
    """ConfigManagerMixin olmadan bağımsız INI dosyasını okuyup dict olarak döner."""
    cfg = ConfigManagerMixin.DEFAULT_CONFIG.copy()
    ini_path = get_config_path(CONFIG_FILE_NAME)
    if os.path.exists(ini_path):
        try:
            cp = configparser.ConfigParser()
            cp.read(ini_path, encoding="utf-8")
            for sec in cp.sections():
                for k, v in cp.items(sec):
                    if k in ConfigManagerMixin.DEFAULT_CONFIG:
                        def_v = ConfigManagerMixin.DEFAULT_CONFIG[k]
                        if isinstance(def_v, bool):
                            cfg[k] = v.lower() in ("true", "1", "yes", "on")
                        elif isinstance(def_v, int) and not isinstance(def_v, bool):
                            try: cfg[k] = int(v)
                            except ValueError: pass
                        elif isinstance(def_v, float):
                            try: cfg[k] = float(v)
                            except ValueError: pass
                        else:
                            cfg[k] = v
        except Exception:
            pass
    return cfg


def save_config_dict(cfg: dict):
    """ConfigManagerMixin olmadan bağımsız dict ayarlarını INI dosyasına kaydeder."""
    ini_path = get_config_path(CONFIG_FILE_NAME)
    class _DummyApp(ConfigManagerMixin):
        def __init__(self, c, p):
            self.config = c
            self.CONFIG_FILE = p
            self.custom_devices = []
    dummy = _DummyApp(cfg, ini_path)
    try:
        content = dummy._generate_ini_content()
        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

