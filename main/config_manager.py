"""
WattCost HaYTooL - Yapılandırma ve Tema Yöneticisi Modülü
Uygulamanın tüm INI ayar tanımları, varsayılanları, renk paleti ve ölçekleme yardımcıları.
"""
import os
import sys
import json
import socket
import ssl
import threading
import ctypes
import configparser
import urllib.request
import urllib.error
import urllib.parse

SINGLE_INSTANCE_PORT = 47892
APP_VERSION = "7.5"

def is_windows_dark_mode() -> bool:
    """Windows sistem temasının Koyu (Dark) modda olup olmadığını okur."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            val, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
            return int(val) == 0
    except Exception:
        return True


def apply_dark_titlebar(window):
    """Aktif temaya göre Windows 10/11 pencere başlık çubuğunu Koyu veya Açık moda ayarlar."""
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        is_dark = 0 if THEME.get("bg", "").upper() == "#F1F5F9" else 1
        value = ctypes.c_int(is_dark)
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

# --- Theme Factory: Açık, Koyu ve Matrix Temaları ---
AVAILABLE_THEMES = {
    "light": {
        "name_tr": "Açık",
        "name_en": "Light",
        "bg": "#F1F5F9",
        "card_bg": "#FFFFFF",
        "card_border": "#CBD5E1",
        "card_inner": "#E2E8F0",
        "text_primary": "#0F172A",
        "text_secondary": "#334155",
        "text_muted": "#64748B",
        "accent_cyan": "#0284C7",
        "accent_green": "#059669",
        "accent_amber": "#D97706",
        "accent_rose": "#E11D48",
        "accent_purple": "#7C3AED",
        "btn_bg": "#E2E8F0",
        "btn_hover": "#CBD5E1",
        "btn_active": "#94A3B8",
        "font_family": "Segoe UI",
    },
    "dark": {
        "name_tr": "Koyu",
        "name_en": "Dark",
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
    "matrix": {
        "name_tr": "Matrix",
        "name_en": "Matrix",
        "bg": "#030A05",
        "card_bg": "#07140B",
        "card_border": "#144222",
        "card_inner": "#0C2112",
        "text_primary": "#D1FAE5",
        "text_secondary": "#6EE7B7",
        "text_muted": "#34A853",
        "accent_cyan": "#00FF66",
        "accent_green": "#22C55E",
        "accent_amber": "#A3E635",
        "accent_rose": "#F43F5E",
        "accent_purple": "#10B981",
        "btn_bg": "#0F2B17",
        "btn_hover": "#163F22",
        "btn_active": "#1E542E",
        "font_family": "Consolas",
    },
}

THEME = dict(AVAILABLE_THEMES["dark" if is_windows_dark_mode() else "light"])

def resolve_theme_key(theme_key: str) -> str:
    """'auto' veya eski tema anahtarlarını 'light' / 'dark' / 'matrix' olarak çözer."""
    k = str(theme_key or "auto").strip().lower()
    if k in AVAILABLE_THEMES:
        return k
    return "dark" if is_windows_dark_mode() else "light"

def set_active_theme(theme_key: str) -> bool:
    """Uygulamanın aktif görsel tema paletini günceller."""
    resolved = resolve_theme_key(theme_key)
    THEME.update(AVAILABLE_THEMES[resolved])
    return True

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


def get_app_data_path(filename: str) -> str:
    """Veri dosyalarını CWD'den bağımsız olarak doğrudan EXE/proje kök dizinine sabitler."""
    return os.path.join(_app_dir, filename)


def calculate_wall_power_w(cpu_w: float, gpu_w: float, cfg: dict, custom_devices=None) -> float:
    """Kalibre edilmiş priz gücü formülü + etkin harici cihazları hesaplar."""
    base_w = 46.7
    try:
        base_w = float(cfg.get("case_base_w", 46.7) or 46.7)
    except (TypeError, ValueError):
        base_w = 46.7
    pc_wall_w = base_w + (1.632 * float(cpu_w or 0.0)) + (1.170 * float(gpu_w or 0.0))

    if custom_devices is None:
        raw_json = cfg.get("custom_devices_json", "")
        if raw_json:
            try:
                parsed = json.loads(raw_json)
                if isinstance(parsed, list):
                    custom_devices = parsed
            except Exception:
                custom_devices = None

    ext_wall = 0.0
    if custom_devices:
        for dev in custom_devices:
            if dev.get("enabled", True) and dev.get("active", False):
                try:
                    ext_wall += float(dev.get("watt", 0.0))
                except (TypeError, ValueError):
                    pass
    else:
        if cfg.get("asus_mon_active", True):
            ext_wall += float(cfg.get("asus_monitor_w", 16.5) or 0.0)
        if cfg.get("samsung_mon_active", False):
            ext_wall += float(cfg.get("samsung_monitor_w", 19.0) or 0.0)
        if cfg.get("modem_active", True):
            ext_wall += float(cfg.get("modem_w", 10.0) or 0.0)

    return max(40.0, pc_wall_w + ext_wall)

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
    {"section": "Genel_Ayarlar", "key": "theme", "default": "auto",
     "tr": "Arayuz temasi ('auto'=Sistem Temasi, 'light'=Acik, 'dark'=Koyu, 'matrix'=Matrix)",
     "en": "UI theme ('auto'=System Theme, 'light'=Light, 'dark'=Dark, 'matrix'=Matrix)"},
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
    {"section": "Guc_Yonetimi", "key": "smart_switch_hotkeys_enabled", "default": False, "tr": "Akilli kademe global kisayol tuslari aktif olsun mu? (true / false)", "en": "Enable global keyboard shortcuts for smart tiers? (true / false)"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t1_hotkey", "default": "Ctrl+Alt+1", "tr": "Kademe 1 global klavye kisayolu ('Ctrl+Alt+1' .. 'none')", "en": "Tier 1 global keyboard shortcut ('Ctrl+Alt+1' .. 'none')"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t2_hotkey", "default": "Ctrl+Alt+2", "tr": "Kademe 2 global klavye kisayolu ('Ctrl+Alt+2' .. 'none')", "en": "Tier 2 global keyboard shortcut ('Ctrl+Alt+2' .. 'none')"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t3_hotkey", "default": "Ctrl+Alt+3", "tr": "Kademe 3 global klavye kisayolu ('Ctrl+Alt+3' .. 'none')", "en": "Tier 3 global keyboard shortcut ('Ctrl+Alt+3' .. 'none')"},
    {"section": "Guc_Yonetimi", "key": "smart_switch_t4_hotkey", "default": "Ctrl+Alt+4", "tr": "Kademe 4 global klavye kisayolu ('Ctrl+Alt+4' .. 'none')", "en": "Tier 4 global keyboard shortcut ('Ctrl+Alt+4' .. 'none')"},
    {"section": "Genel_Ayarlar", "key": "github_gist_token", "default": "", "tr": "GitHub Gist yedekleme tokeni (sadece yerel saklanir, yedeklenmez)", "en": "GitHub Gist backup token (stored locally only, never uploaded)"},
    {"section": "Genel_Ayarlar", "key": "github_gist_id", "default": "", "tr": "Ayar yedegi icin kullanilan GitHub Gist ID", "en": "GitHub Gist ID used for settings backup"},
]

DEFAULT_CONFIG = {item["key"]: item["default"] for item in CONFIG_METADATA}


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


_DPAPI_ENC_CACHE = {}


def encrypt_dpapi(plain: str) -> str:
    """Windows DPAPI (CryptProtectData) ile metni geçerli kullanıcıya özel şifreler."""
    plain = (plain or "").strip()
    if not plain or plain.startswith("dpapi:"):
        return plain
    if plain in _DPAPI_ENC_CACHE:
        return _DPAPI_ENC_CACHE[plain]
    try:
        import base64
        raw = plain.encode("utf-8")
        buf = ctypes.create_string_buffer(raw, len(raw))
        blob_in = _DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        blob_out = _DATA_BLOB()
        if ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in), None, None, None, None, 0x01, ctypes.byref(blob_out)
        ):
            try:
                enc_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                res = "dpapi:" + base64.b64encode(enc_bytes).decode("ascii")
                _DPAPI_ENC_CACHE[plain] = res
                return res
            finally:
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    except Exception:
        pass
    return plain


def decrypt_dpapi(val: str) -> str:
    """Windows DPAPI (CryptUnprotectData) ile 'dpapi:...' şifreli metni çözer; düz metinse olduğu gibi döner."""
    val = (val or "").strip()
    if not val or not val.startswith("dpapi:"):
        return val
    try:
        import base64
        enc_bytes = base64.b64decode(val[6:])
        buf = ctypes.create_string_buffer(enc_bytes, len(enc_bytes))
        blob_in = _DATA_BLOB(len(enc_bytes), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        blob_out = _DATA_BLOB()
        if ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0x01, ctypes.byref(blob_out)
        ):
            try:
                dec_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                return dec_bytes.decode("utf-8")
            finally:
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return ""
    except Exception:
        return ""


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
                if k == "github_gist_token" and val_str:
                    val_str = encrypt_dpapi(val_str)
                def_str = str(def_v).lower() if isinstance(def_v, bool) else str(def_v)
                lines.append(f"; TR: {item['tr']}")
                lines.append(f"; EN: {item['en']}")
                lines.append(f"; Varsayilan / Default: {def_str}")
                lines.append(f"{k} = {val_str}")
                lines.append("")
        return "\n".join(lines)

    def load_config(self):
        self.config = self.DEFAULT_CONFIG.copy()
        ini_path = get_config_path(CONFIG_FILE_NAME)
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
                            elif k == "github_gist_token":
                                self.config[k] = decrypt_dpapi(v)
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

        # Aktif görsel temayı yükle (auto veya eski tema adıysa Windows sistem moduna göre çöz)
        th_key = resolve_theme_key(self.config.get("theme", "auto"))
        self.config["theme"] = th_key
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
            for r in (1, 2, 3, 4):
                self.config[f"smart_switch_t{r}_hz"] = int(getattr(self.smart_switcher, f"tier{r}_hz", self.config.get(f"smart_switch_t{r}_hz", 0)) or 0)
                self.config[f"smart_switch_t{r}_hz2"] = int(getattr(self.smart_switcher, f"tier{r}_hz2", self.config.get(f"smart_switch_t{r}_hz2", 0)) or 0)
            self.config["smart_switch_tier_count"] = int(getattr(self.smart_switcher, 'tier_count', self.config.get("smart_switch_tier_count", 4)) or 4)
        if hasattr(self, 'smart_use_rtss_var'):
            self.config["smart_switch_use_rtss"] = self.smart_use_rtss_var.get()
        if hasattr(self, 'smart_use_watt_var'):
            self.config["smart_switch_use_watt"] = self.smart_use_watt_var.get()
        if hasattr(self, 'smart_switch_sound_var'):
            self.config["smart_switch_sound"] = self.smart_switch_sound_var.get()
        if hasattr(self, 'smart_switch_toast_var'):
            self.config["smart_switch_toast"] = self.smart_switch_toast_var.get()
        try:
            self.CONFIG_FILE = get_config_path(CONFIG_FILE_NAME)
            content = self._generate_ini_content()
            if getattr(self, "_last_written_ini", None) == content and os.path.exists(self.CONFIG_FILE):
                return
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            self._last_written_ini = content
            app_d = os.path.dirname(os.path.abspath(self.CONFIG_FILE))
            parent_d = os.path.dirname(app_d)
            if os.path.basename(app_d).lower() == "dist" and os.path.isdir(os.path.join(parent_d, "main")):
                try:
                    with open(os.path.join(parent_d, CONFIG_FILE_NAME), "w", encoding="utf-8") as rf:
                        rf.write(content)
                except Exception:
                    pass
            elif os.path.isdir(os.path.join(app_d, "dist")) and os.path.isdir(os.path.join(app_d, "main")):
                try:
                    with open(os.path.join(app_d, "dist", CONFIG_FILE_NAME), "w", encoding="utf-8") as df:
                        df.write(content)
                except Exception:
                    pass
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
                        elif k == "github_gist_token":
                            cfg[k] = decrypt_dpapi(v)
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


def _find_wattcost_gist_id(token: str) -> str:
    """Kullanıcının Gist listesinde mevcut WattCost ayar yedeğini otomatik bulur."""
    import urllib.request
    token = (token or "").strip()
    if not token:
        return ""
    try:
        req = urllib.request.Request(
            "https://api.github.com/gists?per_page=100",
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": f"WattCost-HaYTooL/{APP_VERSION}",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            gists = json.loads(resp.read().decode("utf-8"))
        for g in gists:
            files = g.get("files") or {}
            desc = str(g.get("description") or "")
            if CONFIG_FILE_NAME in files or "WattCost HaYTooL" in desc:
                return str(g.get("id") or "")
    except Exception:
        pass
    return ""


def fetch_github_user_and_backup_gist(token: str) -> tuple:
    """Token ile GitHub kullanıcı adını, profil resmini (bytes) ve varsa yedek Gist ID'yi döner."""
    import urllib.request
    import urllib.error

    token = (token or "").strip()
    if not token:
        return False, {}, "Missing token"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": f"WattCost-HaYTooL/{APP_VERSION}",
    }
    try:
        req = urllib.request.Request("https://api.github.com/user", method="GET", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            u = json.loads(resp.read().decode("utf-8"))
        login = str(u.get("login") or "")
        avatar_url = str(u.get("avatar_url") or "")
        avatar_bytes = b""
        if avatar_url:
            sep = "&" if "?" in avatar_url else "?"
            av_req = urllib.request.Request(
                f"{avatar_url}{sep}s=64",
                headers={"User-Agent": f"WattCost-HaYTooL/{APP_VERSION}"},
            )
            try:
                with urllib.request.urlopen(av_req, timeout=10) as av_resp:
                    avatar_bytes = av_resp.read()
            except Exception:
                avatar_bytes = b""

        found_gist_id = _find_wattcost_gist_id(token)
        return True, {"login": login, "avatar_bytes": avatar_bytes, "gist_id": found_gist_id}, ""
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="ignore")
            err_msg = json.loads(err_body).get("message", f"HTTP {e.code}")
        except Exception:
            err_msg = f"HTTP {e.code}"
        return False, {}, err_msg
    except Exception as e:
        return False, {}, str(e)


def backup_settings_to_gist(token: str, gist_id: str = "") -> tuple:
    """WattCost. HaYTooL.ini ayarlarını (token hariç) GitHub Secret Gist'e yedekler."""
    import urllib.request
    import urllib.error
    import re as _re

    token = (token or "").strip()
    gist_id = (gist_id or "").strip()
    if not token:
        return False, gist_id, "Missing token"

    ini_path = get_config_path(CONFIG_FILE_NAME)
    if not os.path.exists(ini_path):
        return False, gist_id, "INI file not found"

    try:
        with open(ini_path, "r", encoding="utf-8") as f:
            raw_ini = f.read()
        # Güvenlik: GitHub PAT asla Gist içine yüklenmez
        sanitized_ini = _re.sub(
            r"(?im)^github_gist_token\s*=.*$",
            "github_gist_token = ",
            raw_ini,
        )

        payload = {
            "description": f"WattCost HaYTooL v{APP_VERSION} Settings Backup",
            "public": False,
            "files": {
                CONFIG_FILE_NAME: {"content": sanitized_ini}
            },
        }
        if not gist_id:
            gist_id = _find_wattcost_gist_id(token)
        url = f"https://api.github.com/gists/{gist_id}" if gist_id else "https://api.github.com/gists"
        method = "PATCH" if gist_id else "POST"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": f"WattCost-HaYTooL/{APP_VERSION}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            new_id = str(data.get("id", gist_id))
            html_url = str(data.get("html_url", ""))
            return True, new_id, html_url
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="ignore")
            err_msg = json.loads(err_body).get("message", f"HTTP {e.code}")
        except Exception:
            err_msg = f"HTTP {e.code}"
        return False, gist_id, err_msg
    except Exception as e:
        return False, gist_id, str(e)


def restore_settings_from_gist(gist_id: str, token: str = "") -> tuple:
    """Belirtilen GitHub Gist ID'den WattCost. HaYTooL.ini ayarlarını indirip uygular."""
    import urllib.request
    import urllib.error

    gist_id = (gist_id or "").strip()
    token = (token or "").strip()
    if not gist_id and token:
        gist_id = _find_wattcost_gist_id(token)
    if not gist_id:
        return False, "No backup Gist found"

    # Tam URL yapıştırıldıysa sondaki ID'yi çıkar
    if "/" in gist_id:
        gist_id = gist_id.rstrip("/").split("/")[-1]

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"WattCost-HaYTooL/{APP_VERSION}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = urllib.request.Request(
            f"https://api.github.com/gists/{gist_id}",
            method="GET",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        files = data.get("files", {})
        ini_content = None
        if CONFIG_FILE_NAME in files:
            ini_content = files[CONFIG_FILE_NAME].get("content")
        else:
            for fname, fobj in files.items():
                if fname.lower().endswith(".ini") and fobj.get("content"):
                    ini_content = fobj["content"]
                    break
        if not ini_content:
            return False, "No .ini file found in Gist"

        ini_path = get_config_path(CONFIG_FILE_NAME)
        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(ini_content)
        return True, gist_id
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="ignore")
            err_msg = json.loads(err_body).get("message", f"HTTP {e.code}")
        except Exception:
            err_msg = f"HTTP {e.code}"
        return False, err_msg
    except Exception as e:
        return False, str(e)


def fetch_gist_ini_preview(gist_id: str, token: str = "") -> tuple:
    """GitHub Gist'teki kayıtlı INI içeriğini ve son güncelleme tarihini uygula-madan okur."""
    gist_id = (gist_id or "").strip()
    token = (token or "").strip()
    if not gist_id and token:
        gist_id = _find_wattcost_gist_id(token)
    if not gist_id:
        return False, "No backup Gist found", ""

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"WattCost-HaYTooL/{APP_VERSION}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = urllib.request.Request(
            f"https://api.github.com/gists/{gist_id}",
            method="GET",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        files = data.get("files", {})
        ini_content = None
        if CONFIG_FILE_NAME in files:
            ini_content = files[CONFIG_FILE_NAME].get("content")
        else:
            for fname, fobj in files.items():
                if fname.lower().endswith(".ini") and fobj.get("content"):
                    ini_content = fobj["content"]
                    break
        if not ini_content:
            return False, "No .ini file found in Gist", ""
        return True, ini_content, str(data.get("updated_at") or "")
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="ignore")
            err_msg = json.loads(err_body).get("message", f"HTTP {e.code}")
        except Exception:
            err_msg = f"HTTP {e.code}"
        return False, err_msg, ""
    except Exception as e:
        return False, str(e), ""


