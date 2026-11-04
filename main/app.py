"""
PC Canlı Elektrik & TL Harcama Takipçisi (AIDA64 Destekli)
UI/UX Pro Max Standartlarında Modern Cyber-Tech Masaüstü Widget'ı

Modüler Mimari:
- config_manager: Ayarlar, INI kalıcılığı ve tema yapılandırması
- sensor_reader: MSI Afterburner ve AIDA64 sensör okuyucuları
- history_manager: Günlük/Aylık tüketim geçmişi ve raporlama
- hotkey_manager: Windows genel klavye kısayolu yöneticisi
- ui_components: Ortak UI kartları, butonlar, pencere yönetimi ve test ekranı
- tab_cost: Elektrik maliyet, donanım kartları ve RTSS OSD panel ayarları
- tab_powerplan: Güç planları yönetimi, klonlama ve hazır planlar
- tab_smartswitch: 4 Kademeli akıllı otomatik güç ve monitör Hz otomasyonu
- tab_compare: Güç planları mikro ayar karşılaştırma matrisi
- tray_manager: Windows saat yanı sistem tepsisi ve dinamik simge çizimi
"""
import ctypes
import os
import re
import sys
import threading
import time
import tkinter as tk
from PIL import Image, ImageTk

# Modüler Bileşenler ve Mixin'ler
from config_manager import (
    THEME, UI_SCALE, fs,
    apply_dark_titlebar,
    notify_existing_instance,
    start_instance_listener,
    get_asset_path,
    ConfigManagerMixin,
    APP_VERSION
)
from language_manager import LanguageManager, _t
from sensor_reader import UnifiedSensorReader
from headset_reader import HeadsetBatteryReader
from history_manager import HistoryManager, HistoryReportMixin, WindowsAutoStart
from hotkey_manager import GlobalHotkeyManager
from ui_components import UIComponentsMixin
from tab_cost import CostTabMixin
from tab_powerplan import PowerPlanTabMixin
from tab_smartswitch import SmartSwitchTabMixin
from tab_compare import CompareTabMixin
from tray_manager import TrayManagerMixin

from power_manager import (
    PowerManagerService,
    SmartAutoSwitcher
)
from rtss_overlay import RTSSOverlay
from jumplist_manager import init_app_user_model_id, setup_jump_list


class PowerTrackerApp(
    ConfigManagerMixin,
    UIComponentsMixin,
    HistoryReportMixin,
    CostTabMixin,
    PowerPlanTabMixin,
    SmartSwitchTabMixin,
    CompareTabMixin,
    TrayManagerMixin
):
    """WattCost HaYTooL Ana Uygulama Koordinatörü."""

    def __init__(self, root, start_in_tray: bool = False):
        self.root = root
        self.root.withdraw()  # Açılışta pencere boyut zıplamasını ve titremeyi önlemek için hazır olana dek gizle
        self.load_config()

        # Çoklu Dil (i18n) & Yerelleştirme Yöneticisi
        self.lang_mgr = LanguageManager.get_instance()
        self.lang_mgr.init_language(self.config.get("language", "auto"))
        self.lang_mgr.register_refresh_callback(self.on_language_changed)

        self.root.title(f"{_t('app_title', 'WattCost HaYTooL • PC Güç & TL Monitörü')} v{APP_VERSION}")

        # Standart Kararlı Dashboard Düzeni (Tüm sekmeleri ve karşılaştırma matrisini kapsayan nihai standart ölçü)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        standard_w = int(1060 * UI_SCALE)
        standard_h = int(770 * UI_SCALE)
        max_allowed_w = max(800, screen_w - 40)
        max_allowed_h = max(550, screen_h - 70)
        win_w = min(standard_w, max_allowed_w)
        win_h = min(standard_h, max_allowed_h)

        # Son kapatılan pencere konumu ve boyutu varsa onu geri yükle
        geometry_restored = self._restore_window_geometry(screen_w, screen_h)
        if not geometry_restored:
            pos_x = max(10, (screen_w - win_w) // 2)
            pos_y = max(10, (screen_h - win_h) // 2)
            self.root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")

        self.root.minsize(min(win_w, int(860 * UI_SCALE)), min(win_h, int(580 * UI_SCALE)))
        self.root.resizable(True, True)
        self.root.configure(bg=THEME["bg"])
        self.apply_window_icon(self.root)
        apply_dark_titlebar(self.root)

        # X butonuna basınca (Varsayılan: Tepsiye Gizle veya Temiz Çıkış)
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close_clicked)

        # Sensör ve RTSS Katmanları
        self.reader = UnifiedSensorReader()
        self.rtss = RTSSOverlay()
        self.load_config()

        # Kulaklık bataryası: USB (SteelSeries HID) ve Bluetooth (Windows HFP) ayrı ayrı
        try:
            _hs_poll = float(self.config.get("headset_poll_sec", 30) or 30)
        except (TypeError, ValueError):
            _hs_poll = 30.0
        self.headset = HeadsetBatteryReader(
            exe_path=self.config.get("headset_exe", ""),
            poll_interval=_hs_poll,
            usb_enabled=bool(self.config.get("headset_usb_active", True)),
            bt_enabled=bool(self.config.get("headset_bt_active", True)),
        )
        if self.headset.any_enabled():
            self.headset.start()

        # Genel Kısayol Dinleyicisi
        self.hotkey_mgr = GlobalHotkeyManager(on_trigger=lambda: self.root.after(0, self.toggle_rtss))
        self.hotkey_mgr.start(
            self.config.get("rtss_hotkey", "Alt+Shift+R"),
            vk=self.config.get("rtss_hotkey_vk"),
            mod=self.config.get("rtss_hotkey_mod", 5)
        )

        # Oturum İstatistikleri
        self.session_start = time.time()
        self.last_update = time.time()
        self.total_energy_wh = 0.0

        # UI Durum Değişkenleri
        self.asus_var = tk.BooleanVar(value=self.config.get("asus_mon_active", True))
        self.samsung_var = tk.BooleanVar(value=self.config.get("samsung_mon_active", False))
        self.modem_var = tk.BooleanVar(value=self.config.get("modem_active", True))
        self.on_top_var = tk.BooleanVar(value=self.config.get("always_on_top", True))
        self.zalman_active_var = tk.BooleanVar(value=self.config.get("zalman_active", True))
        self.zalman_source_var = tk.StringVar(value=self.config.get("zalman_source", "cpu"))
        self.zalman_blank_var = tk.IntVar(value=int(self.config.get("zalman_blank_sec", 4)))
        self.zalman_temp_var = tk.IntVar(value=int(self.config.get("zalman_temp_sec", 10)))
        self.zalman_cycle_start = time.time()
        self.sync_legacy_device_vars()

        # Güç Planı Yöneticisi & 4 Kademeli Akıllı Otomasyon
        self.power_plans = []
        self.active_power_plan = None
        self._last_detected_plan_guid = PowerManagerService.get_active_guid_fast()
        self._last_toast_time = 0
        self.smart_switcher = SmartAutoSwitcher(on_plan_switched=self.on_smart_plan_switched)
        self.smart_switcher.enabled = self.config.get("smart_switch_enabled", False)
        self.smart_switcher.set_tier_count(self.config.get("smart_switch_tier_count", 4))
        self.smart_switcher.hz_enabled = bool(self.config.get("smart_switch_hz_enabled", True))

        # 4 Kademe GUID'leri
        self.smart_switcher.tier1_plan_guid = self.config.get("smart_switch_t1_guid", self.config.get("smart_switch_low_guid", ""))
        self.smart_switcher.tier2_plan_guid = self.config.get("smart_switch_t2_guid", self.config.get("smart_switch_med_guid", ""))
        self.smart_switcher.tier3_plan_guid = self.config.get("smart_switch_t3_guid", "")
        self.smart_switcher.tier4_plan_guid = self.config.get("smart_switch_t4_guid", self.config.get("smart_switch_high_guid", ""))

        # 4 Kademe Monitör Hz Hedefleri (0 = Değiştirme)
        self.smart_switcher.tier1_hz = int(self.config.get("smart_switch_t1_hz", 0))
        self.smart_switcher.tier2_hz = int(self.config.get("smart_switch_t2_hz", 0))
        self.smart_switcher.tier3_hz = int(self.config.get("smart_switch_t3_hz", 0))
        self.smart_switcher.tier4_hz = int(self.config.get("smart_switch_t4_hz", 0))
        self.smart_switcher.tier1_hz2 = int(self.config.get("smart_switch_t1_hz2", 0))
        self.smart_switcher.tier2_hz2 = int(self.config.get("smart_switch_t2_hz2", 0))
        self.smart_switcher.tier3_hz2 = int(self.config.get("smart_switch_t3_hz2", 0))
        self.smart_switcher.tier4_hz2 = int(self.config.get("smart_switch_t4_hz2", 0))

        # Kullanıcı Tanımlı GPU ve CPU Eşikleri (%)
        self.smart_switcher.tier2_gpu_pct = float(self.config.get("smart_switch_t2_gpu", 15.0))
        self.smart_switcher.tier2_cpu_pct = float(self.config.get("smart_switch_t2_cpu", 20.0))
        self.smart_switcher.tier3_gpu_pct = float(self.config.get("smart_switch_t3_gpu", 40.0))
        self.smart_switcher.tier3_cpu_pct = float(self.config.get("smart_switch_t3_cpu", 45.0))
        self.smart_switcher.tier4_gpu_pct = float(self.config.get("smart_switch_t4_gpu", 70.0))
        self.smart_switcher.tier4_cpu_pct = float(self.config.get("smart_switch_t4_cpu", 75.0))

        self.smart_switcher.watt_threshold = float(self.config.get("smart_switch_watt_threshold", 260.0))
        self.smart_switcher.use_rtss_trigger = self.config.get("smart_switch_use_rtss", True)
        self.smart_switcher.use_watt_trigger = self.config.get("smart_switch_use_watt", True)
        self.smart_switcher.trigger_seconds = int(self.config.get("smart_switch_trigger_sec", 2))
        self.smart_switcher.revert_seconds = int(self.config.get("smart_switch_revert_sec", 5))

        # Tkinter UI Değişkenleri
        self.smart_switch_var = tk.BooleanVar(value=self.smart_switcher.enabled)
        self.smart_switch_sound_var = tk.BooleanVar(value=bool(self.config.get("smart_switch_sound", True)))
        self.smart_switch_toast_var = tk.BooleanVar(value=bool(self.config.get("smart_switch_toast", True)))
        self.smart_hz_auto_var = tk.BooleanVar(value=self.smart_switcher.hz_enabled)

        self.smart_t1_guid_var = tk.StringVar(value=self.smart_switcher.tier1_plan_guid)
        self.smart_t2_guid_var = tk.StringVar(value=self.smart_switcher.tier2_plan_guid)
        self.smart_t3_guid_var = tk.StringVar(value=self.smart_switcher.tier3_plan_guid)
        self.smart_t4_guid_var = tk.StringVar(value=self.smart_switcher.tier4_plan_guid)

        # Kademe Hz UI Değişkenleri
        self.smart_t1_hz_var = tk.StringVar(value=str(self.smart_switcher.tier1_hz) if self.smart_switcher.tier1_hz > 0 else "")
        self.smart_t2_hz_var = tk.StringVar(value=str(self.smart_switcher.tier2_hz) if self.smart_switcher.tier2_hz > 0 else "")
        self.smart_t3_hz_var = tk.StringVar(value=str(self.smart_switcher.tier3_hz) if self.smart_switcher.tier3_hz > 0 else "")
        self.smart_t4_hz_var = tk.StringVar(value=str(self.smart_switcher.tier4_hz) if self.smart_switcher.tier4_hz > 0 else "")

        # İkinci monitör Hz UI Değişkenleri
        self.smart_t1_hz2_var = tk.StringVar(value=str(self.smart_switcher.tier1_hz2) if self.smart_switcher.tier1_hz2 > 0 else "")
        self.smart_t2_hz2_var = tk.StringVar(value=str(self.smart_switcher.tier2_hz2) if self.smart_switcher.tier2_hz2 > 0 else "")
        self.smart_t3_hz2_var = tk.StringVar(value=str(self.smart_switcher.tier3_hz2) if self.smart_switcher.tier3_hz2 > 0 else "")
        self.smart_t4_hz2_var = tk.StringVar(value=str(self.smart_switcher.tier4_hz2) if self.smart_switcher.tier4_hz2 > 0 else "")

        self.smart_t2_gpu_var = tk.StringVar(value=str(int(self.smart_switcher.tier2_gpu_pct)))
        self.smart_t2_cpu_var = tk.StringVar(value=str(int(self.smart_switcher.tier2_cpu_pct)))
        self.smart_t3_gpu_var = tk.StringVar(value=str(int(self.smart_switcher.tier3_gpu_pct)))
        self.smart_t3_cpu_var = tk.StringVar(value=str(int(self.smart_switcher.tier3_cpu_pct)))
        self.smart_t4_gpu_var = tk.StringVar(value=str(int(self.smart_switcher.tier4_gpu_pct)))
        self.smart_t4_cpu_var = tk.StringVar(value=str(int(self.smart_switcher.tier4_cpu_pct)))
        self.smart_watt_thresh_var = tk.StringVar(value=str(int(self.smart_switcher.watt_threshold)))
        self.smart_trig_sec_var = tk.StringVar(value=str(int(self.smart_switcher.trigger_seconds)))
        self.smart_rev_sec_var = tk.StringVar(value=str(int(self.smart_switcher.revert_seconds)))

        self.smart_use_rtss_var = tk.BooleanVar(value=self.smart_switcher.use_rtss_trigger)
        self.smart_use_watt_var = tk.BooleanVar(value=self.smart_switcher.use_watt_trigger)
        self.compare_diff_only_var = tk.BooleanVar(value=False)

        # Başlangıç sekmesi argümanı (--tab)
        startup_tab = "cost"
        if "--tab" in sys.argv:
            try:
                t_idx = sys.argv.index("--tab")
                if t_idx + 1 < len(sys.argv):
                    cand_tab = sys.argv[t_idx + 1].strip().lower()
                    if cand_tab in ("cost", "powerplan", "smart", "compare"):
                        startup_tab = cand_tab
            except Exception:
                pass
        self.current_tab = startup_tab
        self.tab_buttons = {}

        # Zalman Alpha2 LCD Pompa Denetleyicisi
        try:
            from zalman_display import ZalmanDisplay
            self.zalman = ZalmanDisplay(update_interval=0.25)
            self.zalman.set_enabled(self.zalman_active_var.get())
            self.zalman.start_background_loop()
        except Exception:
            self.zalman = None

        self.apply_always_on_top()
        self.build_ui()
        if hasattr(self, 'set_headset_block_visible'):
            self.set_headset_block_visible(self.headset.any_enabled() if getattr(self, 'headset', None) else False)
        if hasattr(self, 'update_zalman_visibility'):
            self.update_zalman_visibility()
        if not geometry_restored:
            self.auto_fit_window()
        if start_in_tray:
            # Windows açılışında pencere gösterme: doğrudan sistem tepsisinde başla
            self.root.withdraw()
        else:
            self.root.deiconify()  # Pencere nihai boyutu ve tüm arayüz bileşenleriyle hazır olunca tek seferde pürüzsüz göster
        self.init_tray_icon()
        self.instance_server = start_instance_listener(self)

        # Windows Görev Çubuğu Hızlı Görevler (Jump List) Kurulumu
        try:
            import threading
            threading.Thread(target=setup_jump_list, daemon=True).start()
        except Exception:
            pass

        self.update_loop()

        # Otomasyon açıksa, açılışta aktif kademenin planını ve Hz'ini hemen uygula
        # (Tk ana thread'inde çalışmalı: geri bildirim root.after kullanıyor)
        if getattr(self, 'smart_switcher', None) and self.smart_switcher.enabled:
            try:
                self.root.after(600, self.smart_switcher.force_apply_current)
            except Exception:
                pass

    GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$")

    def _restore_window_geometry(self, screen_w, screen_h) -> bool:
        """Son kapatılan pencere konumu/boyutunu uygular; geçerli kayıt yoksa False döner."""
        geom = str(self.config.get("window_geometry", "") or "").strip()
        match = self.GEOMETRY_RE.match(geom)
        if not match:
            return False

        try:
            width, height, pos_x, pos_y = (int(value) for value in match.groups())
        except (TypeError, ValueError):
            return False

        min_w = int(860 * UI_SCALE)
        min_h = int(580 * UI_SCALE)
        if width < min_w or height < min_h:
            return False

        # Ekran değişmiş olabilir: pencereyi ekranın içine sığdır
        width = min(width, max(800, screen_w - 20))
        height = min(height, max(550, screen_h - 40))
        pos_x = max(-width + 120, min(pos_x, screen_w - 120))
        pos_y = max(0, min(pos_y, screen_h - 80))

        try:
            self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        except Exception:
            return False

        if self.config.get("window_maximized", False):
            try:
                self.root.state("zoomed")
            except Exception:
                pass
        return True

    def _save_window_geometry(self):
        """Kapanışta mevcut pencere konumu/boyutunu INI'ye yazar."""
        try:
            if self.root.state() == "iconic":
                return
            maximized = self.root.state() == "zoomed"
            geom = self.root.geometry()
        except Exception:
            return

        if maximized:
            # Tam ekran/zoom durumunda boyutu ezme, sadece durumu hatırla
            self.config["window_maximized"] = True
        elif self.GEOMETRY_RE.match(str(geom or "")):
            self.config["window_geometry"] = geom
            self.config["window_maximized"] = False
        else:
            return

        try:
            self.save_config()
        except Exception:
            pass

    def build_ui(self):
        f_font = THEME["font_family"]

        # --- 1. ÜST HEADER BAR ---
        self.f_header = tk.Frame(self.root, bg=THEME["bg"])
        self.f_header.pack(fill="x", padx=14, pady=(10, 6))
        header = self.f_header

        f_brand = tk.Frame(header, bg=THEME["bg"])
        f_brand.pack(side="left")

        # Yeni Logo Gösterimi (%25 büyütülmüş 35x35)
        logo_loaded = False
        logo_sz = int(28 * UI_SCALE)
        cand_p = get_asset_path("app_icon.png")
        if os.path.exists(cand_p):
            try:
                raw_logo = Image.open(cand_p).convert('RGBA').resize((logo_sz, logo_sz), Image.Resampling.LANCZOS)
                self.img_brand_logo = ImageTk.PhotoImage(raw_logo)
                lbl_logo = tk.Label(f_brand, image=self.img_brand_logo, bg=THEME["bg"])
                lbl_logo.pack(side="left", padx=(0, 7))
                logo_loaded = True
            except Exception:
                pass
        if not logo_loaded:
            tk.Label(f_brand, text="⚡", font=(f_font, fs(14), "bold"), fg=THEME["accent_cyan"],
                     bg=THEME["bg"]).pack(side="left", padx=(0, 5))

        f_title = tk.Frame(f_brand, bg=THEME["bg"])
        f_title.pack(side="left")
        tk.Label(f_title, text=f"WATTCOST v{APP_VERSION}", font=(f_font, fs(10), "bold"),
                 fg=THEME["text_primary"], bg=THEME["bg"]).pack(anchor="w")
        self.lbl_subtitle = tk.Label(f_title, text=_t("app_subtitle", "HaYTooL • PC Güç & TL Monitörü"), font=(f_font, fs(7)),
                                     fg=THEME["text_muted"], bg=THEME["bg"])
        self.lbl_subtitle.pack(anchor="w")

        # --- ÜST MENÜ TABLARI (⚡ Cost | ⚙️ PowerPlan | 🤖 SmartSwitch | ⚖️ Compare) ---
        self.f_tabs = tk.Frame(header, bg=THEME["bg"])
        self.f_tabs.pack(side="left", padx=(16, 6))

        self.tab_buttons = {}
        self.tab_indicators = {}
        for tab_id, tab_key, tab_def in [
            ("cost", "tab_cost", "⚡ Maliyet"),
            ("powerplan", "tab_powerplan", "⚙️ Güç Planı"),
            ("smart", "tab_smartswitch", "🤖 Akıllı Geçiş"),
            ("compare", "tab_compare", "⚖️ Karşılaştırma")
        ]:
            tab_label = _t(tab_key, tab_def)
            is_active = (tab_id == self.current_tab)
            item_frame = tk.Frame(self.f_tabs, bg=THEME["bg"])
            item_frame.pack(side="left", padx=3)

            btn = tk.Button(
                item_frame, text=tab_label,
                font=(f_font, fs(8), "bold"),
                bg=THEME["card_inner"] if is_active else THEME["bg"],
                fg=THEME["accent_cyan"] if is_active else THEME["text_muted"],
                activebackground=THEME["card_inner"],
                activeforeground=THEME["accent_cyan"],
                relief="flat", bd=0, padx=int(10 * UI_SCALE), pady=int(4 * UI_SCALE), cursor="hand2",
                command=lambda tid=tab_id: self.switch_tab(tid)
            )
            btn.pack(side="top")

            # Aktif sekme altı parıldayan modern gösterge çizgisi (2px indicator bar)
            ind = tk.Frame(item_frame, bg=THEME["accent_cyan"] if is_active else THEME["bg"], height=int(2 * UI_SCALE))
            ind.pack(side="bottom", fill="x", pady=(2, 0))

            def _on_hover(e, b=btn, tid=tab_id):
                if tid != self.current_tab:
                    b.config(bg=THEME["btn_hover"], fg=THEME["text_primary"])
            def _on_leave(e, b=btn, tid=tab_id):
                if tid != self.current_tab:
                    b.config(bg=THEME["bg"], fg=THEME["text_muted"])
            btn.bind("<Enter>", _on_hover, add="+")
            btn.bind("<Leave>", _on_leave, add="+")

            self.tab_buttons[tab_id] = btn
            self.tab_indicators[tab_id] = ind

        f_actions = tk.Frame(header, bg=THEME["bg"])
        f_actions.pack(side="right")

        # 🌐 Bayraklı Dil Seçim Butonu (Gerçek PNG Bayrak Simgesi ile)
        cur_code = self.lang_mgr.active_language_code
        flag_photo = self.lang_mgr.get_flag_photo(cur_code, w=int(22 * UI_SCALE), h=int(14 * UI_SCALE))
        self.btn_lang = tk.Button(
            f_actions,
            image=flag_photo,
            text=f"  {cur_code.upper()}",
            compound="left",
            font=(f_font, fs(8), "bold"),
            fg=THEME["text_primary"],
            bg=THEME["card_inner"],
            activebackground=THEME["btn_active"],
            activeforeground=THEME["accent_cyan"],
            relief="flat", bd=0, padx=int(8 * UI_SCALE), pady=int(3 * UI_SCALE), cursor="hand2",
            highlightbackground=THEME["card_border"], highlightthickness=1,
            command=self.show_language_menu
        )
        self.btn_lang.image = flag_photo
        self.btn_lang.pack(side="right", padx=(4, 0))
        self.add_tooltip(self.btn_lang, lambda: _t("tooltip_language", "🌐 Dil Seçimi: Arayüz dilini anında değiştirin"))

        # 🎨 Büyükşehir Temaları Seçim Butonu
        self.btn_theme_menu = tk.Button(
            f_actions,
            text="🎨",
            font=(f_font, fs(8), "bold"),
            fg=THEME["accent_cyan"],
            bg=THEME["card_inner"],
            activebackground=THEME["btn_active"],
            activeforeground=THEME["accent_cyan"],
            relief="flat", bd=0, padx=int(8 * UI_SCALE), pady=int(3 * UI_SCALE), cursor="hand2",
            highlightbackground=THEME["card_border"], highlightthickness=1,
            command=self.show_theme_menu
        )
        self.btn_theme_menu.pack(side="right", padx=(4, 0))
        self.add_tooltip(self.btn_theme_menu, lambda: _t("tooltip_theme", "🎨 Tema Seçimi: Arayüz renk paletini anında değiştirin"))

        self.btn_settings = self.make_btn(f_actions, "⚙", self.open_settings, padx=int(8 * UI_SCALE),
                                          tooltip=lambda: _t("tooltip_settings", "⚙️ Ayarlar: Elektrik birim fiyatı, harici cihazlar, Zalman ve sistem ayarları"))
        self.btn_settings.pack(side="right", padx=(4, 0))

        self.btn_cli_guide = self.make_btn(f_actions, "💻", self.open_cli_guide, fg=THEME["accent_cyan"], padx=int(8 * UI_SCALE),
                                           tooltip=lambda: _t("tooltip_cli_guide", "💻 CLI Komut Kılavuzu: Terminal komutları, otomasyon ve parametre rehberi"))
        self.btn_cli_guide.pack(side="right", padx=(4, 0))

        self.btn_test_screen = self.make_btn(f_actions, "🎮", self.toggle_test_screen, fg="#00E5FF", padx=int(8 * UI_SCALE),
                                             tooltip=lambda: _t("tooltip_test_screen", "🎮 OSD Test Ekranı: Oyun açmadan RTSS oyun içi göstergesini masaüstünde canlı test edin"))
        self.btn_test_screen.pack(side="right", padx=(4, 0))

        self.btn_hide_tray = self.make_btn(f_actions, "📥", self.hide_to_tray, fg=THEME["text_muted"], padx=int(8 * UI_SCALE),
                                           tooltip=lambda: _t("tooltip_hide_tray", "📥 Tepsiye Gizle: Uygulama penceresini kapatmadan Windows saat yanına küçültün"))
        self.btn_hide_tray.pack(side="right", padx=(4, 0))

        self.btn_history = self.make_btn(f_actions, "📊", self.open_history_report, fg="#38BDF8", padx=int(8 * UI_SCALE),
                                         tooltip=lambda: _t("tooltip_history", "📊 Tüketim Raporu: Günlük ve aylık detaylı elektrik harcama geçmişini görüntüleyin"))
        self.btn_history.pack(side="right", padx=(4, 0))

        # --- TAB SAYFALARI KONTEYNERİ ---
        self.tab_container = tk.Frame(self.root, bg=THEME["bg"])
        self.tab_container.pack(fill="both", expand=True)

        self.tab_cost = tk.Frame(self.tab_container, bg=THEME["bg"])
        self.tab_cost.pack(fill="both", expand=True)

        self.tab_powerplan = tk.Frame(self.tab_container, bg=THEME["bg"])
        self.tab_smart = tk.Frame(self.tab_container, bg=THEME["bg"])
        self.tab_compare = tk.Frame(self.tab_container, bg=THEME["bg"])

        # --- 2. ANA GÜÇ & PROJEKSİYON KARTI (HERO KART) ---
        card_power = self.create_card(self.tab_cost, pady=(0, 6))
        self.f_hero_card = card_power
        tk.Frame(card_power, bg=THEME["accent_cyan"], height=2).pack(fill="x")

        f_hero = tk.Frame(card_power, bg=THEME["card_bg"])
        f_hero.pack(fill="x", padx=12, pady=(6, 8))

        f_hero_left = tk.Frame(f_hero, bg=THEME["card_bg"])
        f_hero_left.pack(side="left", padx=(0, 15))
        self.lbl_hero_power_title = tk.Label(f_hero_left, text=_t("hero_wall_power", "PRİZDEN ÇEKİLEN ANLIK GÜÇ"), font=(f_font, fs(7), "bold"),
                                             fg=THEME["accent_cyan"], bg=THEME["card_bg"])
        self.lbl_hero_power_title.pack(anchor="w")

        f_val_row = tk.Frame(f_hero_left, bg=THEME["card_bg"])
        f_val_row.pack(anchor="w")
        self.lbl_power = tk.Label(f_val_row, text="--- W", font=(f_font, fs(24), "bold"),
                                  fg=THEME["accent_cyan"], bg=THEME["card_bg"])
        self.lbl_power.pack(side="left")
        self.lbl_power_status = tk.Label(f_val_row, text=_t("hero_stable", "• KARARLI"), font=(f_font, fs(8), "bold"),
                                         fg=THEME["text_muted"], bg=THEME["card_bg"])
        self.lbl_power_status.pack(side="left", padx=(8, 0), pady=(6, 0))

        f_rates = tk.Frame(f_hero, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_rates.pack(side="right", fill="both", expand=True)

        def rate_col(title, color, attr, last=False):
            col = tk.Frame(f_rates, bg=THEME["card_inner"])
            col.pack(side="left", expand=True, fill="both", pady=2, padx=2)
            lbl_title = tk.Label(col, text=title, font=(f_font, fs(8), "bold"), fg=THEME["text_muted"], bg=THEME["card_inner"])
            lbl_title.pack(pady=(2, 0))
            setattr(self, f"{attr}_title", lbl_title)
            lbl = tk.Label(col, text=self.format_currency(0.0), font=(f_font, fs(15), "bold"), fg=color, bg=THEME["card_inner"])
            lbl.pack(pady=(0, 2))
            setattr(self, attr, lbl)
            if not last:
                tk.Frame(f_rates, bg=THEME["card_border"], width=1).pack(side="left", fill="y", pady=3)

        rate_col(_t("hero_hourly", "SAATLİK TL"), THEME["accent_green"], "lbl_rate_hour")
        rate_col(_t("hero_daily", "GÜNLÜK"), "#38BDF8", "lbl_rate_day")
        rate_col(_t("hero_monthly", "AYLIK (30G)"), THEME["accent_purple"], "lbl_rate_month", last=True)

        # --- 3. BİRLEŞİK 2 SÜTUNLU GÖVDE ---
        f_main_grid = tk.Frame(self.tab_cost, bg=THEME["bg"])
        f_main_grid.pack(fill="both", expand=True, padx=12, pady=(0, 4))
        self.f_main_grid = f_main_grid

        f_col_sys = tk.Frame(f_main_grid, bg=THEME["bg"], width=int(340 * UI_SCALE))
        f_col_sys.pack(side="left", fill="both", expand=False, padx=(0, 6))
        f_col_sys.pack_propagate(False)
        self.f_col_sys = f_col_sys

        f_col_rtss = tk.Frame(f_main_grid, bg=THEME["bg"])
        f_col_rtss.pack(side="right", fill="both", expand=True, padx=(4, 0))
        self.f_col_rtss = f_col_rtss

        # Sol Kolon İçeriği
        self.build_tab_genel(f_col_sys)
        self.build_tab_cihaz(f_col_sys)
        self.build_zalman_card(f_col_sys)

        # Sağ Kolon İçeriği
        self.build_rtss_panel(f_col_rtss)

        # Diğer Sekmelerin Sayfalarını Oluştur
        self.build_tab_powerplan()
        self.build_tab_smart()
        self.build_tab_compare()

    def switch_tab(self, tab_id):
        self.current_tab = tab_id
        for tid, btn in self.tab_buttons.items():
            ind = self.tab_indicators.get(tid)
            if tid == tab_id:
                btn.config(bg=THEME["card_inner"], fg=THEME["accent_cyan"])
                if ind:
                    ind.config(bg=THEME["accent_cyan"])
            else:
                btn.config(bg=THEME["bg"], fg=THEME["text_muted"])
                if ind:
                    ind.config(bg=THEME["bg"])

        if tab_id == "cost":
            self.tab_powerplan.pack_forget()
            self.tab_smart.pack_forget()
            self.tab_compare.pack_forget()
            self.tab_cost.pack(fill="both", expand=True)
        elif tab_id == "powerplan":
            self.tab_cost.pack_forget()
            self.tab_smart.pack_forget()
            self.tab_compare.pack_forget()
            self.tab_powerplan.pack(fill="both", expand=True)
            self.refresh_power_plans_ui()
        elif tab_id == "smart":
            self.tab_cost.pack_forget()
            self.tab_powerplan.pack_forget()
            self.tab_compare.pack_forget()
            self.tab_smart.pack(fill="both", expand=True)
            self.refresh_smart_tab_ui()
        elif tab_id == "compare":
            self.tab_cost.pack_forget()
            self.tab_powerplan.pack_forget()
            self.tab_smart.pack_forget()
            self.tab_compare.pack(fill="both", expand=True)
            self.refresh_compare_matrix_ui()

    def apply_theme_to_ui(self, theme_key: str):
        """Kullanıcı tema değiştirdiğinde GUI renklerini çalışma anında yeniler."""
        from config_manager import set_active_theme, THEME
        if not set_active_theme(theme_key):
            return
        self.config["theme"] = theme_key
        self.save_config()

        # Ana zeminler
        self.root.configure(bg=THEME["bg"])
        if hasattr(self, 'f_header') and self.f_header:
            self.f_header.configure(bg=THEME["bg"])
        if hasattr(self, 'f_tabs') and self.f_tabs:
            self.f_tabs.configure(bg=THEME["bg"])
        if hasattr(self, 'tab_cost') and self.tab_cost:
            self.tab_cost.configure(bg=THEME["bg"])
        if hasattr(self, 'tab_powerplan') and self.tab_powerplan:
            self.tab_powerplan.configure(bg=THEME["bg"])
        if hasattr(self, 'tab_smart') and self.tab_smart:
            self.tab_smart.configure(bg=THEME["bg"])
        if hasattr(self, 'tab_compare') and self.tab_compare:
            self.tab_compare.configure(bg=THEME["bg"])

        # Aksiyon butonları
        if hasattr(self, 'btn_theme_menu') and self.btn_theme_menu.winfo_exists():
            self.btn_theme_menu.configure(bg=THEME["card_inner"], fg=THEME["accent_cyan"],
                                          activebackground=THEME["btn_active"], activeforeground=THEME["accent_cyan"],
                                          highlightbackground=THEME["card_border"])
        if hasattr(self, 'btn_lang') and self.btn_lang.winfo_exists():
            self.btn_lang.configure(bg=THEME["card_inner"], fg=THEME["text_primary"],
                                    activebackground=THEME["btn_active"], activeforeground=THEME["accent_cyan"],
                                    highlightbackground=THEME["card_border"])

        # Sekme çubuğunu yeniden çiz
        self.switch_tab(self.current_tab)

        # Sekme içeriklerini yeniden oluştur
        if hasattr(self, 'refresh_cost_tab_ui'):
            self.refresh_cost_tab_ui()
        if hasattr(self, 'refresh_power_plans_ui'):
            self.refresh_power_plans_ui()
        if hasattr(self, 'refresh_smart_tab_ui'):
            self.refresh_smart_tab_ui()
        if hasattr(self, 'refresh_compare_matrix_ui'):
            self.refresh_compare_matrix_ui()

    def show_language_menu(self):
        """Bayraklı dil seçim penceresini gerçek pürüzsüz bayrak resimleriyle açar."""
        if hasattr(self, '_lang_popup') and self._lang_popup and self._lang_popup.winfo_exists():
            self._lang_popup.destroy()
            self._lang_popup = None
            return

        popup = tk.Toplevel(self.root)
        self._lang_popup = popup
        popup.overrideredirect(True)
        popup.configure(bg=THEME["card_border"])
        f_font = THEME["font_family"]

        f_inner = tk.Frame(popup, bg=THEME["card_bg"], padx=6, pady=6)
        f_inner.pack(fill="both", expand=True, padx=1, pady=1)

        f_pop_title = tk.Frame(f_inner, bg=THEME["card_bg"])
        f_pop_title.pack(fill="x", padx=6, pady=(3, 6))
        tk.Label(f_pop_title, text="🌐 DİL SEÇİMİ / LANGUAGE", font=(f_font, fs(7), "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(side="left")

        langs = self.lang_mgr.get_language_list()
        cur_code = self.lang_mgr.active_language_code
        popup._img_refs = []

        for item in langs:
            c = item.get("code", "")
            n = item.get("name", c.capitalize())
            is_cur = (c.lower() == cur_code.lower())

            flag_img = self.lang_mgr.get_flag_photo(c, w=28, h=18)
            popup._img_refs.append(flag_img)

            row = tk.Frame(f_inner, bg=THEME["card_inner"] if is_cur else THEME["card_bg"],
                           cursor="hand2", padx=8, pady=5)
            row.pack(fill="x", pady=2)

            lbl_flag = tk.Label(row, image=flag_img, bg=row["bg"])
            lbl_flag.pack(side="left", padx=(0, 8))

            lbl_name = tk.Label(row, text=n, font=(f_font, fs(8), "bold" if is_cur else "normal"),
                                fg=THEME["accent_cyan"] if is_cur else THEME["text_primary"], bg=row["bg"])
            lbl_name.pack(side="left")

            lbl_code = tk.Label(row, text=f"[{c.upper()}]", font=(f_font, fs(7)),
                                fg=THEME["text_muted"], bg=row["bg"])
            lbl_code.pack(side="left", padx=(6, 0))

            if is_cur:
                tk.Label(row, text="●", font=(f_font, fs(8), "bold"),
                         fg=THEME["accent_green"], bg=row["bg"]).pack(side="right", padx=(8, 0))

            def _on_enter(e, r=row, cur=is_cur):
                if not cur:
                    r.config(bg=THEME["btn_hover"])
                    for child in r.winfo_children():
                        child.config(bg=THEME["btn_hover"])

            def _on_leave(e, r=row, cur=is_cur):
                bg_col = THEME["card_inner"] if cur else THEME["card_bg"]
                r.config(bg=bg_col)
                for child in r.winfo_children():
                    child.config(bg=bg_col)

            def _on_click(e, code=c):
                popup.destroy()
                self._lang_popup = None
                self.switch_language(code)

            for w_elem in [row, lbl_flag, lbl_name, lbl_code]:
                w_elem.bind("<Enter>", _on_enter)
                w_elem.bind("<Leave>", _on_leave)
                w_elem.bind("<Button-1>", _on_click)

        popup.update_idletasks()
        pw = max(popup.winfo_reqwidth(), int(210 * UI_SCALE))
        ph = popup.winfo_reqheight()

        bx = self.btn_lang.winfo_rootx()
        by = self.btn_lang.winfo_rooty() + self.btn_lang.winfo_height() + 4
        px = max(10, bx + self.btn_lang.winfo_width() - pw)
        popup.geometry(f"{pw}x{ph}+{px}+{by}")

        def _close_lang_popup(e=None):
            if hasattr(self, '_lang_popup') and self._lang_popup and self._lang_popup.winfo_exists():
                try:
                    x, y = self.root.winfo_pointerxy()
                    gx, gy = popup.winfo_rootx(), popup.winfo_rooty()
                    gw, gh = popup.winfo_width(), popup.winfo_height()
                    if not (gx <= x <= gx + gw and gy <= y <= gy + gh):
                        popup.destroy()
                        self._lang_popup = None
                except Exception:
                    pass

        popup.bind("<FocusOut>", lambda e: _close_lang_popup())
        self.root.bind("<Button-1>", _close_lang_popup, add="+")

    def show_theme_menu(self):
        """Kullanıcının büyükşehir temalarını tek tıkla seçebileceği açılır menü."""
        if hasattr(self, '_theme_popup') and self._theme_popup and self._theme_popup.winfo_exists():
            self._theme_popup.destroy()
            self._theme_popup = None
            return

        popup = tk.Toplevel(self.root)
        self._theme_popup = popup
        popup.overrideredirect(True)
        popup.configure(bg=THEME["card_border"])
        f_font = THEME["font_family"]

        f_inner = tk.Frame(popup, bg=THEME["card_bg"], padx=6, pady=6)
        f_inner.pack(fill="both", expand=True, padx=1, pady=1)

        f_pop_title = tk.Frame(f_inner, bg=THEME["card_bg"])
        f_pop_title.pack(fill="x", padx=6, pady=(3, 6))
        tk.Label(f_pop_title, text="🎨 ŞEHİR TEMALARI", font=(f_font, fs(7), "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(side="left")

        from config_manager import AVAILABLE_THEMES
        cur_theme = self.config.get("theme", "obsidian_cyber")
        is_tr = (self.lang_mgr.active_language_code == "tr") if hasattr(self, 'lang_mgr') else True

        for code, th in AVAILABLE_THEMES.items():
            name = th["name_tr"] if is_tr else th["name_en"]
            is_cur = (code == cur_theme)

            row = tk.Frame(f_inner, bg=THEME["card_inner"] if is_cur else THEME["card_bg"],
                           cursor="hand2", padx=8, pady=4)
            row.pack(fill="x", pady=1)

            # Temanın renklerini gösteren 3 minik palet kutucuğu
            f_dots = tk.Frame(row, bg=row["bg"])
            f_dots.pack(side="left", padx=(0, 8))
            for c in [th["bg"], th["card_bg"], th["accent_cyan"]]:
                tk.Label(f_dots, text="■", font=(f_font, fs(7)), fg=c, bg=row["bg"]).pack(side="left", padx=1)

            lbl_name = tk.Label(row, text=name, font=(f_font, fs(8), "bold" if is_cur else "normal"),
                                fg=THEME["accent_cyan"] if is_cur else THEME["text_primary"], bg=row["bg"])
            lbl_name.pack(side="left")

            if is_cur:
                lbl_chk = tk.Label(row, text="✓", font=(f_font, fs(8), "bold"),
                                   fg=THEME["accent_cyan"], bg=row["bg"])
                lbl_chk.pack(side="right")
            else:
                lbl_chk = None

            def _on_enter(e, r=row):
                r.config(bg=THEME["btn_hover"])
                for child in r.winfo_children():
                    child.config(bg=THEME["btn_hover"])
                    for sub in child.winfo_children():
                        sub.config(bg=THEME["btn_hover"])

            def _on_leave(e, r=row, cur=is_cur):
                bg_col = THEME["card_inner"] if cur else THEME["card_bg"]
                r.config(bg=bg_col)
                for child in r.winfo_children():
                    child.config(bg=bg_col)
                    for sub in child.winfo_children():
                        sub.config(bg=bg_col)

            def _on_click(e, c=code):
                popup.destroy()
                self._theme_popup = None
                self.apply_theme_to_ui(c)

            targets = [row, f_dots, lbl_name]
            if lbl_chk:
                targets.append(lbl_chk)
            for w_elem in targets:
                w_elem.bind("<Enter>", _on_enter)
                w_elem.bind("<Leave>", _on_leave)
                w_elem.bind("<Button-1>", _on_click)

        popup.update_idletasks()
        pw = max(popup.winfo_reqwidth(), int(190 * UI_SCALE))
        ph = popup.winfo_reqheight()

        bx = self.btn_theme_menu.winfo_rootx()
        by = self.btn_theme_menu.winfo_rooty() + self.btn_theme_menu.winfo_height() + 4
        px = max(10, bx + self.btn_theme_menu.winfo_width() - pw)
        popup.geometry(f"{pw}x{ph}+{px}+{by}")

        def _close_th_popup(e=None):
            if hasattr(self, '_theme_popup') and self._theme_popup and self._theme_popup.winfo_exists():
                try:
                    x, y = self.root.winfo_pointerxy()
                    gx, gy = popup.winfo_rootx(), popup.winfo_rooty()
                    gw, gh = popup.winfo_width(), popup.winfo_height()
                    if not (gx <= x <= gx + gw and gy <= y <= gy + gh):
                        popup.destroy()
                        self._theme_popup = None
                except Exception:
                    pass

        popup.bind("<FocusOut>", lambda e: _close_th_popup())
        self.root.bind("<Button-1>", _close_th_popup, add="+")

    def switch_language(self, code: str):
        """Kullanıcı bir dili seçtiğinde dili değiştirir, INI'ye kaydeder ve UI'ı anında günceller."""
        self.config["language"] = code
        self.save_config()
        self.lang_mgr.set_language(code)

    def on_language_changed(self):
        """Dil değiştiğinde tüm UI başlıklarını, butonlarını ve sekmelerini anında yeniler."""
        cur = self.lang_mgr.get_current_language_info()
        code = cur.get("code", "en").upper()

        if hasattr(self, 'btn_lang') and self.btn_lang.winfo_exists():
            flag_photo = self.lang_mgr.get_flag_photo(code.lower(), w=int(22 * UI_SCALE), h=int(14 * UI_SCALE))
            self.btn_lang.config(image=flag_photo, text=f"  {code.upper()}")
            self.btn_lang.image = flag_photo

        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.title(f"{_t('app_title', 'WattCost HaYTooL • PC Güç & TL Monitörü')} v{APP_VERSION}")

        if hasattr(self, 'lbl_subtitle') and self.lbl_subtitle.winfo_exists():
            self.lbl_subtitle.config(text=_t("app_subtitle", "HaYTooL • PC Güç & TL Monitörü"))

        if hasattr(self, 'tab_buttons'):
            tab_labels = {
                "cost": _t("tab_cost", "⚡ Maliyet"),
                "powerplan": _t("tab_powerplan", "⚙️ Güç Planı"),
                "smart": _t("tab_smartswitch", "🤖 Akıllı Geçiş"),
                "compare": _t("tab_compare", "⚖️ Karşılaştırma")
            }
            for tid, lbl in tab_labels.items():
                if tid in self.tab_buttons and self.tab_buttons[tid].winfo_exists():
                    self.tab_buttons[tid].config(text=lbl)

        if hasattr(self, 'lbl_hero_power_title') and self.lbl_hero_power_title.winfo_exists():
            self.lbl_hero_power_title.config(text=_t("hero_wall_power", "PRİZDEN ÇEKİLEN ANLIK GÜÇ"))

        if hasattr(self, 'lbl_rate_hour_title') and self.lbl_rate_hour_title.winfo_exists():
            self.lbl_rate_hour_title.config(text=_t("hero_hourly", "SAATLİK TL"))

        if hasattr(self, 'lbl_rate_day_title') and self.lbl_rate_day_title.winfo_exists():
            self.lbl_rate_day_title.config(text=_t("hero_daily", "GÜNLÜK"))

        if hasattr(self, 'lbl_rate_month_title') and self.lbl_rate_month_title.winfo_exists():
            self.lbl_rate_month_title.config(text=_t("hero_monthly", "AYLIK (30G)"))

        # Sekmeleri güncel dille yeniden oluştur
        if hasattr(self, 'build_tab_powerplan'):
            self.build_tab_powerplan()
        if hasattr(self, 'build_tab_smart'):
            self.build_tab_smart()
        if hasattr(self, 'build_tab_compare'):
            self.build_tab_compare()
        if hasattr(self, 'refresh_cost_tab_ui'):
            self.refresh_cost_tab_ui()

        # Aktif sekmeyi görünür tut
        cur_tab = getattr(self, "current_tab", "cost")
        self.switch_tab(cur_tab)

        # Sistem tepsisi menüsünü güncel dille güncelle
        if hasattr(self, 'tray_icon') and self.tray_icon and hasattr(self, 'build_tray_menu'):
            try:
                self.tray_icon.menu = self.build_tray_menu()
                self.tray_icon.update_menu()
            except Exception:
                pass

        # Windows Görev Çubuğu Jump List'i güncel dille yenile
        try:
            import threading
            threading.Thread(target=setup_jump_list, daemon=True).start()
        except Exception:
            pass

    def toggle_rtss(self):
        cur = self.config.get("rtss_enabled", True)
        new_val = not cur
        self.config["rtss_enabled"] = new_val
        if hasattr(self, "rtss_enabled_var"):
            self.rtss_enabled_var.set(new_val)
        self.save_config()

        if not new_val:
            if hasattr(self, "rtss") and self.rtss:
                self.rtss.release_osd()
        else:
            vals = getattr(self, "_last_vals", (150.0, 0.40, 0.0, 0.0, 0.0))
            hw = getattr(self, "_last_hw", None)
            txt = self.get_rtss_text(vals[0], vals[1], vals[2], vals[3], vals[4], hw_stats=hw)
            if txt and txt.strip() and hasattr(self, "rtss") and self.rtss:
                self.rtss.update_osd(txt)

        self.refresh_rtss_preview()
        if hasattr(self, "lbl_rtss_note"):
            status_txt = _t("rtss_status_opened", "Açıldı") if new_val else _t("rtss_status_closed", "Kapatıldı")
            hk = self.config.get("rtss_hotkey", _t("rtss_note_shortcut", "Kısayol"))
            self.lbl_rtss_note.config(text=f"✓ OSD {status_txt} ({hk})")
            self.root.after(2500, lambda: self.lbl_rtss_note.config(text="") if hasattr(self, "lbl_rtss_note") else None)

    def _update_label_text(self, lbl, text):
        """Yalnızca metin değiştiğinde Tkinter config çağrısı yaparak gereksiz C-level yerleşim ve yeniden çizimleri engeller."""
        if lbl and lbl.winfo_exists():
            attr = f"_last_txt_{id(lbl)}"
            if getattr(self, attr, None) != text:
                setattr(self, attr, text)
                lbl.config(text=text)

    def _update_status_label(self, lbl, text, fg=None, bg=None):
        """Yalnızca metin veya renk değiştiğinde Tkinter config çağrısı yapar."""
        if lbl and lbl.winfo_exists():
            state = (text, fg, bg)
            attr = f"_last_st_{id(lbl)}"
            if getattr(self, attr, None) != state:
                setattr(self, attr, state)
                kwargs = {"text": text}
                if fg is not None:
                    kwargs["fg"] = fg
                if bg is not None:
                    kwargs["bg"] = bg
                lbl.config(**kwargs)

    def apply_headset_enabled(self, source: str, enabled: bool):
        """Kulaklık kaynağını (usb / bt) açar/kapatır; ikisi de kapalıysa okuma tamamen durur."""
        enabled = bool(enabled)
        key = "headset_usb_active" if source == "usb" else "headset_bt_active"
        self.config[key] = enabled

        reader = getattr(self, 'headset', None)
        if reader is not None:
            if source == "usb":
                reader.set_sources(usb=enabled)
            else:
                reader.set_sources(bt=enabled)
            try:
                if reader.any_enabled():
                    reader.start()
                    if enabled:
                        # Kaynak yeniden açıldığında 30 sn bekletme: hemen bir kez oku
                        threading.Thread(target=reader.refresh, daemon=True).start()
                else:
                    reader.stop()
            except Exception:
                pass

        if hasattr(self, 'update_headset_ui'):
            self.update_headset_ui()
        self.save_config()

    def _build_headset_tray_suffix(self) -> str:
        """Tepsi ipucu için bağlı tüm kulaklıkların bataryasını kısa biçimde döndürür."""
        reader = getattr(self, 'headset', None)
        if reader is None or not reader.any_enabled():
            return ""
        try:
            devices = reader.snapshot().get("devices") or []
        except Exception:
            return ""

        parts = []
        for data in devices:
            level = data.get("level")
            # 0% = kapalı/şarjda; ipucunda gösterme
            if level is None or level <= 0:
                continue
            name = (data.get("name") or "").strip()
            if len(name) > 12:
                name = name[:11] + "…"
            parts.append(f"{name} %{int(level)}")

        # Windows tepsi ipucu ~128 karakter; taşarsa sondan kırp
        suffix = ""
        for part in parts:
            candidate = f"{suffix} · {part}" if suffix else part
            if len(candidate) > 70:
                break
            suffix = candidate

        return (" | 🎧 " + suffix) if suffix else ""

    def update_loop(self):
        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Yerel fonksiyon referansları (MRO zincirini atlayarak CPU döngüsünü hızlandırır)
        fmt_curr = self.format_currency
        fmt_rate = self.format_rate_hour
        tr = _t
        set_lbl = self._update_label_text
        set_status_lbl = self._update_status_label

        sensors = self.reader.read_sensors()

        if sensors:
            source = sensors.get('_source', tr("sensor_default_src", "Sensör"))
            clean_source = source.replace("MSI ", "").strip()
            if hasattr(self, 'lbl_status'):
                set_status_lbl(self.lbl_status, f"● {clean_source} {tr('sensor_status_connected', 'Bağlı')}", fg=THEME["accent_green"], bg=THEME["card_inner"])
            if hasattr(self, 'lbl_hw_title'):
                set_lbl(self.lbl_hw_title, tr('live_hw_title', 'CANLI DONANIM & SENSÖRLER'))
            
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

            set_lbl(self.lbl_cpu, f"{cpu_w:.0f} W • %{cpu_uti} • {cpu_temp}°C")
            set_lbl(self.lbl_gpu, f"{gpu_w:.0f} W • %{gpu_uti} • {gpu_temp}°C")
            if hasattr(self, 'lbl_ram'):
                set_lbl(self.lbl_ram, f"%{ram_uti}")

            # Zalman Alpha2 Pompa LCD Güncellemesi
            if hasattr(self, 'zalman') and self.zalman:
                zalman_on = self.zalman_active_var.get() if hasattr(self, 'zalman_active_var') else False
                self.zalman.set_enabled(zalman_on)
                if zalman_on:
                    z_src = self.zalman_source_var.get() if hasattr(self, 'zalman_source_var') else "cpu"
                    if z_src == "cycle":
                        temp_dur = max(1, int(self.config.get("zalman_temp_sec", 10)))
                        blank_dur = max(1, int(self.config.get("zalman_blank_sec", 4)))
                        half_cycle = temp_dur + blank_dur
                        total_cycle = half_cycle * 2
                        if not hasattr(self, 'zalman_cycle_start'):
                            self.zalman_cycle_start = now
                        phase = (now - self.zalman_cycle_start) % total_cycle

                        if phase < temp_dur:
                            self.zalman.set_blank(False)
                            self.zalman.set_temperature(cpu_temp)
                            rem = int(temp_dur - phase) + 1
                            z_tag = f"CPU {cpu_temp}°C [{rem}s]"
                            is_in_blank = False
                        elif phase < half_cycle:
                            self.zalman.set_blank(True)
                            rem = int(half_cycle - phase) + 1
                            lbl = tr("zalman_blank_to_gpu", "Boşluk (GPU'ya)")
                            z_tag = f"{lbl} [{rem}s]"
                            is_in_blank = True
                        elif phase < (half_cycle + temp_dur):
                            self.zalman.set_blank(False)
                            self.zalman.set_temperature(gpu_temp)
                            rem = int((half_cycle + temp_dur) - phase) + 1
                            z_tag = f"GPU {gpu_temp}°C [{rem}s]"
                            is_in_blank = False
                        else:
                            self.zalman.set_blank(True)
                            rem = int(total_cycle - phase) + 1
                            lbl = tr("zalman_blank_to_cpu", "Boşluk (CPU'ya)")
                            z_tag = f"{lbl} [{rem}s]"
                            is_in_blank = True
                    else:
                        self.zalman.set_blank(False)
                        is_in_blank = False
                        if z_src == "gpu":
                            self.zalman.set_temperature(gpu_temp)
                            z_tag = f"{gpu_temp}°C (GPU)"
                        elif z_src == "max":
                            z_val = max(cpu_temp, gpu_temp)
                            self.zalman.set_temperature(z_val)
                            z_tag = f"{z_val}°C (MAX)"
                        else:
                            self.zalman.set_temperature(cpu_temp)
                            z_tag = f"{cpu_temp}°C (CPU)"

                    if hasattr(self, 'lbl_zalman_status'):
                        if self.zalman.is_connected:
                            z_fg = THEME["text_muted"] if is_in_blank else THEME["accent_green"]
                            z_bullet = "○" if is_in_blank else "●"
                            set_status_lbl(self.lbl_zalman_status, f"{z_bullet} {z_tag}", fg=z_fg)
                        else:
                            set_status_lbl(self.lbl_zalman_status, tr('zalman_searching', "○ Aygıt Aranıyor..."), fg=THEME["accent_amber"])
                else:
                    self.zalman.set_blank(True)
                    if hasattr(self, 'lbl_zalman_status'):
                        set_status_lbl(self.lbl_zalman_status, tr('zalman_passive', "○ Pasif"), fg=THEME["text_muted"])

            # Laboratuvar Kalibrasyonu (RTX 5070 12GB + Ryzen 7 5800X)
            pc_wall_w = 46.7 + 1.632 * cpu_w + 1.170 * gpu_w

            ext_wall = 0.0
            if hasattr(self, 'custom_devices') and self.custom_devices:
                for dev in self.custom_devices:
                    if dev.get("enabled", True) and dev.get("active", False):
                        try:
                            ext_wall += float(dev.get("watt", 0.0))
                        except (ValueError, TypeError):
                            pass
            else:
                if self.asus_var.get():
                    ext_wall += float(self.config.get("asus_monitor_w", 16.5))
                if self.samsung_var.get():
                    ext_wall += float(self.config.get("samsung_monitor_w", 19.0))
                if self.modem_var.get():
                    ext_wall += float(self.config.get("modem_w", 10.0))

            total_wall_w = max(40.0, pc_wall_w + ext_wall)

            if total_wall_w > 480:
                set_status_lbl(self.lbl_power_status, tr("status_full_load", "🔥 TAM YÜK"), fg=THEME["accent_rose"])
            elif total_wall_w > 260:
                set_status_lbl(self.lbl_power_status, tr("status_game_load", "🎮 OYUN / YÜK"), fg="#38BDF8")
            else:
                set_status_lbl(self.lbl_power_status, tr("status_idle_save", "🌱 TASARRUF / BOŞTA"), fg=THEME["accent_green"])

            wh_delta = total_wall_w * (dt / 3600.0)
            self.total_energy_wh += wh_delta
            kwh = self.total_energy_wh / 1000.0
            price = float(self.config.get("kwh_price_tl", 2.60))
            total_tl = kwh * price
            hourly_tl = (total_wall_w / 1000.0) * price
            daily_tl = hourly_tl * 24.0
            monthly_tl = daily_tl * 30.0

            HistoryManager.add_energy(wh_delta, price)

            set_lbl(self.lbl_power, f"{total_wall_w:.0f} W")
            set_lbl(self.lbl_rate_hour, fmt_rate(hourly_tl))
            set_lbl(self.lbl_rate_day, fmt_curr(daily_tl, 1))
            set_lbl(self.lbl_rate_month, fmt_curr(monthly_tl, 0))

            set_lbl(self.lbl_cost, fmt_curr(total_tl, 2))
            set_lbl(self.lbl_kwh, f"{tr('lbl_consumption', 'Tüketim')}: {kwh:.3f} kWh")

            elapsed = int(now - self.session_start)
            hrs = elapsed // 3600
            mins = (elapsed % 3600) // 60
            secs = elapsed % 60
            set_lbl(self.lbl_time, f"{tr('lbl_session_time', 'Oturum')}: {hrs:02d}:{mins:02d}:{secs:02d}")

            up_sec = ctypes.windll.kernel32.GetTickCount64() // 1000
            hrs_up = up_sec / 3600.0
            
            pc_uptime_str = sensors.get('SUPTIME', '')
            if not pc_uptime_str:
                pc_uptime_str = f"{up_sec//3600:02d}:{(up_sec%3600)//60:02d}:{up_sec%60:02d}"
            set_lbl(self.lbl_pc_uptime, f"{tr('lbl_pc_uptime', '🖥 PC Açık Kalma')}: {pc_uptime_str}")

            saver_tl = (145.0 / 1000.0) * hrs_up * price
            game_tl = (355.0 / 1000.0) * hrs_up * price

            set_lbl(self.lbl_saver_est, f"{tr('lbl_saving_est', '🌱 Tasarruf')}: {fmt_curr(saver_tl, 2)}")
            set_lbl(self.lbl_game_est, f"{tr('lbl_gaming_est', '🎮 Oyunda')}: {fmt_curr(game_tl, 2)}")

            self._last_watt = total_wall_w
            self._last_hourly = hourly_tl

            if hasattr(self, 'smart_switcher') and self.smart_switcher.enabled:
                try:
                    is_rtss_active = hasattr(self, 'rtss') and getattr(self.rtss, 'is_running', False)
                    self.smart_switcher.evaluate(is_rtss_active, gpu_uti, cpu_uti, total_wall_w)
                except Exception:
                    pass

            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    title_txt = f"{total_wall_w:.0f}W | CPU: {cpu_temp}°C (%{cpu_uti}) | GPU: {gpu_temp}°C (%{gpu_uti}) | {fmt_rate(hourly_tl)}{self._build_headset_tray_suffix()}"
                    if getattr(self, '_last_tray_title', None) != title_txt:
                        self._last_tray_title = title_txt
                        self.tray_icon.title = title_txt

                    self.tray_watt_str = f"⚡ {tr('tray_instant_watt', 'Anlık Güç')}: {total_wall_w:.0f} W"
                    self.tray_temp_str = f"🌡️ {tr('tray_hardware', 'Donanım')}: CPU {cpu_temp}°C (%{cpu_uti})  |  GPU {gpu_temp}°C (%{gpu_uti})"
                    self.tray_hourly_str = f"{tr('currency_sign', '₺')} {tr('tray_hourly_cost', 'Saatlik Maliyet')}: {fmt_rate(hourly_tl)}"
                    
                    new_icon = self.create_tray_image(
                        watt=total_wall_w, cpu_temp=cpu_temp, gpu_temp=gpu_temp,
                        cpu_uti=cpu_uti, gpu_uti=gpu_uti, hourly_tl=hourly_tl
                    )
                    # Yalnızca simge referansı değiştiğinde Windows Shell_NotifyIcon IPC çağrısı yap
                    if new_icon is not getattr(self, '_last_assigned_tray_icon', None):
                        self._last_assigned_tray_icon = new_icon
                        self.tray_icon.icon = new_icon
                except Exception:
                    pass

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
            if hasattr(self, 'lbl_status'):
                set_status_lbl(self.lbl_status, f"⚠ {tr('sensor_status_disconnected', 'Afterburner Kapalı!')}", fg="#EF4444", bg="#2B1515")
            set_status_lbl(self.lbl_power_status, f"• {tr('power_status_no_conn', 'BAĞLANTI YOK')}", fg=THEME["text_muted"])
            if hasattr(self, 'lbl_zalman_status'):
                set_status_lbl(self.lbl_zalman_status, f"○ {tr('zalman_no_sensor', 'Sensör Yok')}", fg=THEME["text_muted"])

            # Afterburner kapalıyken de tepsi ipucu kulaklık bataryalarını göstermeye devam etsin
            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    title_txt = _t("tray_app_tooltip", "WattCost HaYTooL") + self._build_headset_tray_suffix()
                    if getattr(self, '_last_tray_title', None) != title_txt:
                        self._last_tray_title = title_txt
                        self.tray_icon.title = title_txt
                except Exception:
                    pass

        # Kulaklık bataryası (Afterburner/AIDA64 bağlantısından bağımsız çalışır)
        if hasattr(self, 'update_headset_ui'):
            self.update_headset_ui()

        # Akıllı geçiş sekmesindeki canlı şerit (CPU/GPU yükü + monitör Hz)
        if hasattr(self, 'update_smart_live'):
            self.update_smart_live()

        # 2. monitör takılıysa cihaz listesindeki ikinci monitörü otomatik işaretle (5 sn'de bir)
        if now - getattr(self, '_last_monitor_sync', 0) >= 5:
            self._last_monitor_sync = now
            if hasattr(self, 'sync_second_monitor_device'):
                try:
                    self.sync_second_monitor_device()
                except Exception:
                    pass

        # Aktif güç planı değişimi kontrolü (Windows veya dışarıdan yapılan değişimleri yakalar)
        try:
            curr_guid = PowerManagerService.get_active_guid_fast()
            if curr_guid and curr_guid != getattr(self, '_last_detected_plan_guid', None):
                prev_guid = getattr(self, '_last_detected_plan_guid', None)
                self._last_detected_plan_guid = curr_guid
                if prev_guid is not None and (time.time() - getattr(self, '_last_toast_time', 0)) > 2.0:
                    p_name = _t("power_plan_default", "Güç Planı")
                    p_icon = "⚡"
                    if getattr(self, 'power_plans', None):
                        for p in self.power_plans:
                            if p.guid.lower() == curr_guid:
                                p_name = p.name
                                p_icon = p.badge_icon
                                break
                    if hasattr(self, 'refresh_power_plans_ui'):
                        self.refresh_power_plans_ui()
                    if hasattr(self, 'show_power_plan_toast'):
                        self.show_power_plan_toast(plan_name=p_name, icon=p_icon, subtitle=_t("toast_win_plan_updated", "Windows güç modu güncellendi"))
        except Exception:
            pass

        self.root.after(1000, self.update_loop)


    def handle_remote_cli(self, cmd_body: str) -> str:
        """Konsoldan (CLI) soket üzerinden gelen komutları GUI thread'inde işler."""
        try:
            parts = cmd_body.strip().split()
            if not parts:
                return "ERR: Empty command"

            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "set_plan":
                guid = arg.lower()
                ok = PowerManagerService.set_active_plan(guid)
                if ok:
                    p_name = _t("power_plan_default", "Güç Planı")
                    p_icon = "⚡"
                    if getattr(self, 'power_plans', None):
                        for p in self.power_plans:
                            if p.guid.lower() == guid:
                                p_name = p.name
                                p_icon = p.badge_icon
                                break
                    self.root.after(0, self.refresh_power_plans_ui)
                    self.root.after(0, lambda: self.show_power_plan_toast(
                        plan_name=p_name,
                        icon=p_icon,
                        subtitle=_t("toast_applied_via_cli", "CLI komutu ile uygulandı")
                    ))
                    return f"OK: Plan {p_name} ({guid}) uygulandi."
                return "ERR: Failed to set plan"

            elif cmd == "smart":
                act = arg.lower()
                cur = bool(self.config.get("smart_switch_enabled", False))
                if act == "status":
                    return f"OK: {'Aktif (Acik)' if cur else 'Devre Disi (Kapali)'}"
                new_state = not cur if act == "toggle" else (act in ("on", "1", "true"))
                self.config["smart_switch_enabled"] = new_state
                self.save_config()
                if hasattr(self, 'smart_switch_var'):
                    self.root.after(0, lambda: self.smart_switch_var.set(new_state))
                if hasattr(self, 'smart_switcher') and self.smart_switcher:
                    self.smart_switcher.enabled = new_state
                if hasattr(self, 'update_smart_ui_state'):
                    self.root.after(0, self.update_smart_ui_state)
                st_str = "Acik (Aktif)" if new_state else "Kapali (Devre Disi)"
                return f"OK: Akilli Guc Modu: {st_str}"

            elif cmd == "tab":
                target_tab = arg.lower()
                valid_tabs = ["cost", "powerplan", "smart", "compare"]
                if target_tab in valid_tabs:
                    self.root.after(0, lambda: self.switch_tab(target_tab))
                    self.root.after(0, self.bring_to_front)
                    return f"OK: Tab switched to {target_tab}"
                return f"ERR: Unknown tab {target_tab}"

            elif cmd == "osd":
                act = arg.lower()
                cur = bool(self.config.get("rtss_enabled", True))
                new_state = not cur if act == "toggle" else (act in ("on", "1", "true"))
                self.config["rtss_enabled"] = new_state
                self.save_config()
                if hasattr(self, 'rtss_enabled_var'):
                    self.root.after(0, lambda: self.rtss_enabled_var.set(new_state))
                if hasattr(self, 'on_rtss_change'):
                    self.root.after(0, self.on_rtss_change)
                return f"OK: RivaTuner OSD {'Acik' if new_state else 'Kapali'}"

            elif cmd == "status":
                active_guid = PowerManagerService.get_active_guid_fast()
                p_name = "Bilinmeyen Plan"
                if getattr(self, 'power_plans', None):
                    for p in self.power_plans:
                        if p.guid.lower() == active_guid:
                            p_name = p.name
                            break
                watt = getattr(self, '_last_watt', 0.0)
                hourly = getattr(self, '_last_hourly', 0.0)
                smart_on = bool(self.config.get("smart_switch_enabled", False))
                return f"OK: Aktif Plan: {p_name}; Priz Gucu: {watt:.0f} W; Saatlik: {hourly:.2f} TL/sa; Akilli Mod: {'Acik' if smart_on else 'Kapali'}"

            return "ERR: Unknown command"
        except Exception as e:
            return f"ERR: {e}"


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--watch":
        from rtss_overlay import _watch_and_clear
        _watch_and_clear(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "WattCost")
        sys.exit(0)

    # Windows acilisinda (Run anahtari) --tray ile cagrilir: pencere gostermeden tepside basla
    start_in_tray = "--tray" in sys.argv
    if start_in_tray:
        sys.argv = [arg for arg in sys.argv if arg != "--tray"]

    # 1. CLI Argüman Kontrolü (Konsoldan komut verilmişse işlet ve çık)
    from cli_handler import handle_cli_args
    if handle_cli_args():
        sys.exit(0)

    # 2. Zaten açık olan bir WattCost kopyası varsa onu öne getir ve yeni kopyayı sonlandır
    if notify_existing_instance():
        sys.exit(0)

    # Windows Görev Çubuğu Gruplama & Jump List AppID Bildirimi
    init_app_user_model_id()

    # Eski otomatik başlatma kayıtlarına --tray ekle (açılışta pencere değil tepsi)
    try:
        WindowsAutoStart.ensure_tray_flag()
    except Exception:
        pass

    root = tk.Tk()
    app = PowerTrackerApp(root, start_in_tray=start_in_tray)
    root.mainloop()
