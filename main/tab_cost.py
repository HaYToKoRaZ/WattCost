"""
WattCost HaYTooL - Cost & RTSS Overlay Tab Modülü
Genel oturum/donanım kartları, cihazlar, Zalman LCD ve RivaTuner (RTSS) OSD ayarlarını yönetir.
"""
import time
import tkinter as tk
from tkinter import ttk
from config_manager import THEME, UI_SCALE, fs
from history_manager import HistoryManager
from language_manager import _t


class CostTabMixin:
    """Elektrik harcama takibi, donanım kartları ve RTSS OSD panel bileşenleri."""

    # 5 Kafa Renk Paleti (Mor, Cyan, Yeşil, Kırmızı, Sarı + Beyaz)
    RTSS_PALETTE = [
        ("Mor",     "#A855F7"),
        ("Cyan",    "#00E5FF"),
        ("Yeşil",   "#10B981"),
        ("Kırmızı", "#F43F5E"),
        ("Sarı",    "#F59E0B"),
        ("Beyaz",   "#FFFFFF"),
    ]

    # Varsayılanlar:
    # FPS: Boş (""), GPU%: "G", CPU%: "C", RAM%: "R", Saatlik Tüketim: "T"
    RTSS_ROWS_HW = [
        # (show_key, label_key, color_key, size_key, title, def_color, def_size, def_label, def_active)
        ("rtss_show_fps",       "rtss_label_fps",       "rtss_color_fps",       "rtss_size_fps",       "Anlık FPS",                 "#F43F5E", "100", "",      True),
        ("rtss_show_gpu_uti",   "rtss_label_gpu_uti",   "rtss_color_gpu_uti",   "rtss_size_gpu_uti",   "GPU Kullanımı (%)",         "#00E5FF", "100", "G",     False),
        ("rtss_show_gpu_temp",  "rtss_label_gpu_temp",  "rtss_color_gpu_temp",  "rtss_size_gpu_temp",  "GPU Sıcaklığı (°C)",        "#00E5FF", "100", "GPU-C",   False),
        ("rtss_show_gpu_w",     "rtss_label_gpu_w",     "rtss_color_gpu_w",     "rtss_size_gpu_w",     "GPU Gücü (Watt)",           "#00E5FF", "100", "GPU-W",   False),
        ("rtss_show_gpu_clk",   "rtss_label_gpu_clk",   "rtss_color_gpu_clk",   "rtss_size_gpu_clk",   "GPU Hızı (MHz)",            "#38BDF8", "100", "GPU-CLK", False),
        ("rtss_show_vram",      "rtss_label_vram",      "rtss_color_vram",      "rtss_size_vram",      "VRAM Bellek (GB)",          "#818CF8", "100", "VRAM",    False),
        ("rtss_show_cpu_uti",   "rtss_label_cpu_uti",   "rtss_color_cpu_uti",   "rtss_size_cpu_uti",   "CPU Kullanımı (%)",         "#F59E0B", "100", "C",     False),
        ("rtss_show_cpu_temp",  "rtss_label_cpu_temp",  "rtss_color_cpu_temp",  "rtss_size_cpu_temp",  "CPU Sıcaklığı (°C)",        "#F59E0B", "100", "CPU-C",   False),
        ("rtss_show_cpu_w",     "rtss_label_cpu_w",     "rtss_color_cpu_w",     "rtss_size_cpu_w",     "CPU Gücü (Watt)",           "#F59E0B", "100", "CPU-W",   False),
        ("rtss_show_cpu_clk",   "rtss_label_cpu_clk",   "rtss_color_cpu_clk",   "rtss_size_cpu_clk",   "CPU Hızı (MHz)",            "#FCD34D", "100", "CPU-CLK", False),
        ("rtss_show_ram",       "rtss_label_ram",       "rtss_color_ram",       "rtss_size_ram",       "Sistem RAM (%)",            "#A855F7", "100", "R",     False),
        ("rtss_show_fan",       "rtss_label_fan",       "rtss_color_fan",       "rtss_size_fan",       "Fan Devri (RPM)",           "#34D399", "100", "FAN",     False),
    ]

    RTSS_ROWS_PWR = [
        ("rtss_show_power",     "rtss_label_power",     "rtss_color_power",     "rtss_size_power",     "Prizden Güç (Toplam W)",    "#00E5FF", "100", "GUC",     True),
        ("rtss_show_hourly",    "rtss_label_hourly",    "rtss_color_hourly",    "rtss_size_hourly",    "Saatlik Tüketim (TL/sa)",   "#10B981", "100", "T",       True),
        ("rtss_show_session",   "rtss_label_session",   "rtss_color_session",   "rtss_size_session",   "Oturum Tutarı (TL)",        "#F59E0B", "100", "OTURUM",  True),
        ("rtss_show_today",     "rtss_label_today",     "rtss_color_today",     "rtss_size_today",     "Bugünkü Toplam (TL)",       "#A855F7", "100", "BUGUN",   False),
        ("rtss_show_month",     "rtss_label_month",     "rtss_color_month",     "rtss_size_month",     "Bu Ayki Fatura (TL)",       "#EC4899", "100", "AY",      False),
    ]

    RTSS_ROWS = RTSS_ROWS_HW + RTSS_ROWS_PWR

    def build_tab_genel(self, parent):
        f_font = THEME["font_family"]

        card_session = self.create_card(parent, pady=(0, 8))
        self.make_card_title(card_session, _t("session_spent_title", "BU OTURUMDA HARCANAN"), THEME["accent_amber"])

        f_cost_row = tk.Frame(card_session, bg=THEME["card_bg"])
        f_cost_row.pack(fill="x", padx=14, pady=(0, 4))
        self.lbl_cost = tk.Label(f_cost_row, text=self.format_currency(0.0), font=(f_font, fs(20), "bold"),
                                 fg=THEME["accent_amber"], bg=THEME["card_bg"])
        self.lbl_cost.pack(side="left")
        self.make_btn(f_cost_row, _t("btn_reset_session", "↺ Sıfırla"), self.reset_session, fg=THEME["text_primary"],
                      bg=THEME["card_inner"],
                      tooltip=_t("tooltip_reset_session", "Bu oturumun elektrik ve süre sayacını sıfırlar (Geçmiş kayıtlar silinmez)")).pack(side="right")

        f_details = tk.Frame(card_session, bg=THEME["card_bg"])
        f_details.pack(fill="x", padx=14, pady=(0, 6))
        self.lbl_kwh = tk.Label(f_details, text=f"{_t('lbl_consumption', 'Tüketim')}: 0.000 kWh", font=(f_font, fs(8)),
                                fg=THEME["text_secondary"], bg=THEME["card_bg"])
        self.lbl_kwh.pack(side="left")
        self.lbl_time = tk.Label(f_details, text=f"{_t('lbl_session_time', 'Oturum')}: 00:00:00", font=(f_font, fs(8)),
                                 fg=THEME["text_muted"], bg=THEME["card_bg"])
        self.lbl_time.pack(side="right")

        f_up_box = tk.Frame(card_session, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_up_box.pack(fill="x", padx=12, pady=(2, 10))
        self.lbl_pc_uptime = tk.Label(f_up_box, text=f"{_t('lbl_pc_uptime', '🖥 PC Açık Kalma')}: --:--:--", font=(f_font, fs(8), "bold"),
                                      fg=THEME["text_secondary"], bg=THEME["card_inner"])
        self.lbl_pc_uptime.pack(anchor="w", padx=10, pady=(5, 2))
        f_up_compare = tk.Frame(f_up_box, bg=THEME["card_inner"])
        f_up_compare.pack(fill="x", padx=10, pady=(0, 5))
        self.lbl_saver_est = tk.Label(f_up_compare, text=f"{_t('lbl_saving_est', '🌱 Tasarruf')}: {self.format_currency(0.0)}", font=(f_font, fs(8), "bold"),
                                      fg=THEME["accent_green"], bg=THEME["card_inner"])
        self.lbl_saver_est.pack(side="left")
        tk.Label(f_up_compare, text="•", font=(f_font, fs(8)), fg=THEME["text_muted"],
                 bg=THEME["card_inner"]).pack(side="left", padx=5)
        self.lbl_game_est = tk.Label(f_up_compare, text=f"{_t('lbl_gaming_est', '🎮 Oyunda')}: {self.format_currency(0.0)}", font=(f_font, fs(8), "bold"),
                                     fg=THEME["accent_rose"], bg=THEME["card_inner"])
        self.lbl_game_est.pack(side="left")

        card_hw = self.create_card(parent, pady=(0, 8))

        def _make_hw_status(title_row):
            self.lbl_status = tk.Label(
                title_row,
                text=_t("sensor_status_init", "● Başlatılıyor..."),
                font=(f_font, fs(7), "bold"),
                fg=THEME["accent_green"],
                bg=THEME["card_inner"],
                padx=int(6 * UI_SCALE),
                pady=int(1 * UI_SCALE),
                relief="flat",
                highlightbackground=THEME["card_border"],
                highlightthickness=1
            )
            self.lbl_status.pack(side="right")
            self.add_tooltip(self.lbl_status, lambda: _t("tooltip_sensor_status", "Canlı Sensör Durumu: Afterburner ve AIDA64 sensör bağlantısı"))

        self.lbl_hw_title = self.make_card_title(
            card_hw,
            _t("live_hw_title", "Canlı Donanım & Sensörler"),
            THEME["accent_purple"],
            right_widget_factory=_make_hw_status
        )
        hw_rows = (
            ("CPU (Ryzen 5800X):", "lbl_cpu", (1, 1)),
            ("GPU (RTX 5070 12GB):", "lbl_gpu", (1, 1)),
            (_t("lbl_ram_usage", "RAM Kullanımı:"),     "lbl_ram", (1, 6)),
        )
        for text, attr, pad in hw_rows:
            r = tk.Frame(card_hw, bg=THEME["card_bg"])
            r.pack(fill="x", padx=12, pady=pad)
            tk.Label(r, text=text, font=(f_font, fs(8)), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")
            lbl = tk.Label(r, text="--", font=(f_font, fs(8), "bold"), fg=THEME["text_primary"], bg=THEME["card_bg"])
            lbl.pack(side="right")
            setattr(self, attr, lbl)

        # Kablosuz kulaklık bataryası (SteelSeries Arctis 7 / HeadsetControl)
        self.build_headset_block(card_hw)

    def build_headset_block(self, card):
        """Donanım kartına kulaklık batarya bloklarını ekler (cihaz sayısı dinamiktir)."""
        f_font = THEME["font_family"]

        # Tüm satırlar tek bir kapsayıcıda: ayarlardan kapatılınca blok bütünüyle gizlenir
        self.f_headset_block = tk.Frame(card, bg=THEME["card_bg"])
        self.f_headset_block.pack(fill="x")
        block = self.f_headset_block

        tk.Frame(block, bg=THEME["card_border"], height=1).pack(fill="x", padx=12, pady=(4, 5))

        self._headset_rows = {}
        self._headset_keys = ()
        self.lbl_headset_none = tk.Label(block, text=_t("headset_scanning", "● Aranıyor..."),
                                         font=(f_font, fs(7), "italic"), fg=THEME["text_muted"],
                                         bg=THEME["card_bg"])

    def _build_headset_row(self, key):
        """Yeni bir cihaz için satır oluşturur ve kaydeder."""
        f_font = THEME["font_family"]
        frame = tk.Frame(self.f_headset_block, bg=THEME["card_bg"])

        f_top = tk.Frame(frame, bg=THEME["card_bg"])
        f_top.pack(fill="x", padx=12, pady=(0, 2))
        lbl_name = tk.Label(f_top, text=f"🎧 {_t('headset_title', 'Kulaklık Bataryası')}",
                            font=(f_font, fs(8)), fg=THEME["text_secondary"], bg=THEME["card_bg"])
        lbl_name.pack(side="left")
        lbl_status = tk.Label(f_top, text=_t("headset_scanning", "● Aranıyor..."),
                              font=(f_font, fs(7), "bold"), fg=THEME["text_muted"], bg=THEME["card_bg"])
        lbl_status.pack(side="right")
        self.add_tooltip(lbl_status, lambda: _t(
            "headset_status_tooltip",
            "Kulaklık bataryası USB HID veya Windows Bluetooth cihaz özelliğinden okunur (30 saniyede bir)."))

        f_lvl = tk.Frame(frame, bg=THEME["card_bg"])
        f_lvl.pack(fill="x", padx=12, pady=(0, 2))
        tk.Label(f_lvl, text=_t("headset_level_label", "Seviye"), font=(f_font, fs(8)),
                 fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")

        f_bar_out = tk.Frame(f_lvl, bg=THEME["card_inner"], height=int(8 * UI_SCALE),
                             highlightbackground=THEME["card_border"], highlightthickness=1)
        f_bar_out.pack(side="left", fill="x", expand=True, padx=(8, 8))
        f_bar_out.pack_propagate(False)
        bar = tk.Frame(f_bar_out, bg=THEME["accent_green"])
        bar.place(x=0, y=0, relheight=1.0, relwidth=0.0)

        lbl_level = tk.Label(f_lvl, text="--", font=(f_font, fs(8), "bold"),
                             fg=THEME["text_primary"], bg=THEME["card_bg"], width=4, anchor="e")
        lbl_level.pack(side="right")

        lbl_time = tk.Label(f_lvl, text="--", font=(f_font, fs(7)),
                            fg=THEME["text_muted"], bg=THEME["card_bg"])
        lbl_time.pack(side="right", padx=(0, 8))

        row = {"frame": frame, "name": lbl_name, "status": lbl_status,
               "bar": bar, "level": lbl_level, "time": lbl_time}
        self._headset_rows[key] = row
        return row

    def set_headset_block_visible(self, visible: bool):
        """Kulaklık bloğunu göster/gizle; gizliyken arka plan okuması da durdurulur."""
        block = getattr(self, 'f_headset_block', None)
        if block is None or not block.winfo_exists():
            return
        if visible:
            if not block.winfo_ismapped():
                block.pack(fill="x")
        else:
            block.pack_forget()

    def _format_headset_time(self, minutes):
        """Dakika cinsinden kalan süreyi '9s 57dk' / '57 dk' biçimine çevirir."""
        try:
            total = max(0, int(minutes))
        except (TypeError, ValueError):
            return "--"
        hrs, mins = divmod(total, 60)
        if hrs > 0:
            return _t("headset_time_hm", "{h}s {m}dk").format(h=hrs, m=mins)
        return _t("headset_time_min", "{m} dk").format(m=mins)

    def _apply_headset_row(self, row, data):
        """Tek kulaklık satırının içeriğini günceller."""
        name = data.get("name") or _t("headset_title", "Kulaklık Bataryası")
        self._update_status_label(row["name"], f"🎧 {name}", fg=THEME["text_secondary"])

        status_key = data.get("status_key") or "headset_status_unknown"
        if status_key in ("headset_status_available", "headset_status_full"):
            status_color = THEME["accent_green"]
        elif status_key == "headset_status_charging":
            status_color = THEME["accent_cyan"]
        else:
            status_color = THEME["text_muted"]
        self._update_status_label(row["status"], f"● {_t(status_key, 'Bilinmiyor')}", fg=status_color)

        level = data.get("level")
        if level is None:
            self._update_status_label(row["level"], "--")
            row["bar"].place_configure(relwidth=0.0)
        else:
            if level >= 60:
                bar_color = THEME["accent_green"]
            elif level >= 25:
                bar_color = THEME["accent_amber"]
            else:
                bar_color = THEME["accent_rose"]
            row["bar"].configure(bg=bar_color)
            row["bar"].place_configure(relwidth=level / 100.0)
            self._update_status_label(row["level"], f"%{level}", fg=bar_color)

        self._update_status_label(row["time"], self._format_headset_time(data.get("time_to_empty_min")))

    def update_headset_ui(self):
        """Kulaklık bloklarını, o an bağlı tüm cihazlar için dinamik olarak tazeler."""
        rows = getattr(self, '_headset_rows', None)
        if rows is None:
            return

        block = getattr(self, 'f_headset_block', None)
        reader = getattr(self, 'headset', None)

        # İki kaynak da kapalıysa blok tamamen gizlenir
        if reader is not None and not reader.any_enabled():
            if block is not None and block.winfo_ismapped():
                block.pack_forget()
            return

        if block is not None and not block.winfo_ismapped():
            block.pack(fill="x")

        snapshot = reader.snapshot() if reader else {}
        devices = snapshot.get("devices") or []

        # Yeni cihazlar için satır oluştur, var olanları güncelle
        active_keys = []
        for data in devices:
            key = data.get("key") or data.get("name") or "usb"
            row = rows.get(key)
            if row is None:
                row = self._build_headset_row(key)
            self._apply_headset_row(row, data)
            active_keys.append(key)

        # Artık görünmeyen cihazların satırlarını kaldır
        for key in list(rows.keys()):
            if key not in active_keys:
                try:
                    rows[key]["frame"].destroy()
                except Exception:
                    pass
                rows.pop(key, None)

        # Satır sırası sabit kalsın (USB üstte, sonra alfabetik BT cihazları)
        if tuple(active_keys) != getattr(self, '_headset_keys', None):
            for key in active_keys:
                rows[key]["frame"].pack_forget()
            for key in active_keys:
                rows[key]["frame"].pack(fill="x")
            self._headset_keys = tuple(active_keys)

        none_lbl = getattr(self, 'lbl_headset_none', None)
        if none_lbl is not None:
            if active_keys:
                if none_lbl.winfo_ismapped():
                    none_lbl.pack_forget()
            elif not none_lbl.winfo_ismapped():
                none_lbl.pack(anchor="w", padx=12, pady=(0, 6))

    def build_tab_cihaz(self, parent):
        card = self.create_card(parent, pady=(0, 8))
        self.card_cihaz = card

        def _make_gear_btn(title_row):
            self.make_btn(title_row, _t("btn_edit", "⚙ Düzenle"), self.open_settings,
                          fg=THEME["text_muted"], bg=THEME["card_inner"],
                          padx=int(6 * UI_SCALE), pady=int(1 * UI_SCALE),
                          tooltip=_t("tooltip_edit_devices", "Prizden güç çeken harici cihazları (monitör, modem vb.) yönetin ve yeni cihaz ekleyin")).pack(side="right")

        self.make_card_title(card, _t("device_profile_title", "Prize Bağlı Cihazlar"), THEME["accent_cyan"], right_widget_factory=_make_gear_btn)

        self.f_cihaz_list = tk.Frame(card, bg=THEME["card_bg"])
        self.f_cihaz_list.pack(fill="x", padx=12, pady=(0, 2))

        self.lbl_cihaz_footer = tk.Label(
            card, text=_t("device_footer_note", "* İşaretli cihazlar toplam priz gücüne eklenir."),
            font=(THEME["font_family"], fs(7), "italic"), fg=THEME["text_muted"], bg=THEME["card_bg"]
        )
        self.lbl_cihaz_footer.pack(anchor="w", padx=12, pady=(2, 6))

        self.device_check_vars = {}
        self.refresh_devices_ui()

    def refresh_devices_ui(self):
        """Kayıtlı harici cihazları dinamik olarak kart içerisine çizer."""
        if not hasattr(self, 'f_cihaz_list') or not self.f_cihaz_list.winfo_exists():
            return

        for widget in self.f_cihaz_list.winfo_children():
            widget.destroy()

        f_font = THEME["font_family"]
        dev_list = getattr(self, 'custom_devices', [])

        visible_count = 0
        for dev in dev_list:
            # Kullanıcı ayarlardan bu cihazı kapattıysa (enabled=False), ana ekranda gösterme
            if not dev.get("enabled", True):
                continue

            visible_count += 1
            dev_id = dev.get("id", str(visible_count))
            if dev_id not in self.device_check_vars:
                self.device_check_vars[dev_id] = tk.BooleanVar(value=bool(dev.get("active", False)))
            var = self.device_check_vars[dev_id]
            var.set(bool(dev.get("active", False)))

            row = tk.Frame(self.f_cihaz_list, bg=THEME["card_bg"])
            row.pack(fill="x", pady=2)

            def _toggle_cb(d=dev, v=var):
                d["active"] = v.get()
                if hasattr(self, 'sync_legacy_device_vars'):
                    self.sync_legacy_device_vars()
                self.save_config()

            dev_name = dev.get("name", "Cihaz")
            cb = self.make_check(row, dev_name, var, _toggle_cb, fg=THEME["text_primary"],
                                 tooltip=_t("device_include_tooltip", "'{name}' cihazını anlık priz gücü hesaplamasına dahil et").format(name=dev_name))
            cb.pack(side="left")

            w_val = float(dev.get("watt", 0.0))
            lbl = tk.Label(row, text=f"{w_val:.1f} W", font=(f_font, fs(8), "bold"),
                           fg=THEME["accent_amber"], bg=THEME["card_bg"])
            lbl.pack(side="right")

        if visible_count == 0:
            lbl_none = tk.Label(self.f_cihaz_list, text=_t("device_none_active", "* Aktif harici cihaz yok (Ayarlar'dan açabilirsiniz)."),
                                font=(f_font, fs(7), "italic"), fg=THEME["text_muted"], bg=THEME["card_bg"])
            lbl_none.pack(anchor="w", pady=2)

    def sync_second_monitor_device(self, force: bool = False):
        """2. monitör bağlıysa 'Prize Bağlı Cihazlar' listesindeki ikinci monitörü otomatik işaretler."""
        if not force and not self.config.get("auto_detect_second_monitor", True):
            return

        try:
            from power_manager import DisplayManagerService
            monitor_count = len(DisplayManagerService.get_monitors())
        except Exception:
            return

        desired = monitor_count >= 2
        changed = False

        for dev in getattr(self, 'custom_devices', []) or []:
            if dev.get("id") != "samsung_mon":
                continue
            if bool(dev.get("active", False)) == desired:
                continue
            dev["active"] = desired
            var = getattr(self, 'device_check_vars', {}).get("samsung_mon")
            if var is not None:
                var.set(desired)
            changed = True

        if changed:
            self.save_config()
            if hasattr(self, 'refresh_devices_ui'):
                self.refresh_devices_ui()

    def update_zalman_visibility(self):
        """Zalman ayarı açıksa kartı göster, kapalıysa gizle."""
        if not hasattr(self, 'card_zalman') or not self.card_zalman:
            return
        is_active = bool(self.config.get("zalman_active", True))
        if is_active:
            if not self.card_zalman.winfo_ismapped():
                self.card_zalman.pack(fill="x", padx=12, pady=(0, 6))
        else:
            if self.card_zalman.winfo_ismapped():
                self.card_zalman.pack_forget()

    def build_zalman_card(self, parent):
        f_font = THEME["font_family"]
        card = self.create_card(parent, pady=(0, 8))
        self.card_zalman = card

        f_title = tk.Frame(card, bg=THEME["card_bg"])
        f_title.pack(fill="x", padx=12, pady=(6, 2))

        tk.Label(f_title, text=_t("zalman_pump_title", "❄️ Zalman Alpha2 Pompa"), font=(f_font, fs(8), "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(side="left")

        self.lbl_zalman_status = tk.Label(f_title, text=_t("sensor_status_init", "● Başlatılıyor..."), font=(f_font, fs(7), "bold"),
                                          fg=THEME["text_muted"], bg=THEME["card_bg"])
        self.lbl_zalman_status.pack(side="right")

        f_row = tk.Frame(card, bg=THEME["card_bg"])
        f_row.pack(fill="x", padx=12, pady=(2, 4))

        def _on_zalman_toggle():
            active = self.zalman_active_var.get()
            if hasattr(self, 'zalman') and self.zalman:
                self.zalman.set_enabled(active)
            self.save_config()

        self.make_check(f_row, _t("zalman_chk_send_temp", "LCD Ekrana Sıcaklık Gönder"), self.zalman_active_var,
                        _on_zalman_toggle, fg=THEME["text_primary"], bold=True,
                        tooltip=_t("zalman_chk_tooltip", "Zalman Alpha2 LCD pompa ekranına CPU ve GPU sıcaklık verilerini canlı olarak aktarır")).pack(side="left")

        f_src = tk.Frame(card, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_src.pack(fill="x", padx=10, pady=(2, 6))

        tk.Label(f_src, text=_t("zalman_lbl_source", "Kaynak:"), font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                 bg=THEME["card_inner"]).pack(side="left", padx=(6, 2), pady=3)

        def _on_src_change():
            val = self.zalman_source_var.get()
            self.config["zalman_source"] = val
            self.save_config()

        sources = [
            (_t("zalman_src_cycle", "🔄 Döngü"), "cycle", THEME["accent_green"], lambda: _t("zalman_src_cycle_tip", "CPU ve GPU sıcaklıklarını sırayla döngüsel olarak gösterir")),
            (_t("zalman_src_cpu", "CPU"), "cpu", THEME["accent_amber"], lambda: _t("zalman_src_cpu_tip", "Ekranda yalnızca işlemci (CPU) sıcaklığını sabit gösterir")),
            (_t("zalman_src_gpu", "GPU"), "gpu", THEME["accent_cyan"], lambda: _t("zalman_src_gpu_tip", "Ekranda yalnızca ekran kartı (GPU) sıcaklığını sabit gösterir")),
            (_t("zalman_src_max", "En Yüksek"), "max", THEME["accent_rose"], lambda: _t("zalman_src_max_tip", "CPU ve GPU'dan hangisi daha sıcaksa onu ekranda gösterir")),
        ]

        for text, val, col, tip in sources:
            rb = tk.Radiobutton(
                f_src, text=text, value=val, variable=self.zalman_source_var,
                command=_on_src_change, font=(f_font, fs(8), "bold"),
                fg=col, bg=THEME["card_inner"], selectcolor=THEME["card_bg"],
                activebackground=THEME["card_inner"], activeforeground=col,
                cursor="hand2", padx=2, pady=1
            )
            rb.pack(side="left", padx=2, pady=2)
            self.add_tooltip(rb, tip)

        f_dur = tk.Frame(card, bg=THEME["card_bg"])
        f_dur.pack(fill="x", padx=12, pady=(0, 6))

        def _on_dur_change(*args):
            try:
                self.config["zalman_temp_sec"] = max(1, int(self.zalman_temp_var.get()))
                self.config["zalman_blank_sec"] = max(1, int(self.zalman_blank_var.get()))
                self.save_config()
            except Exception:
                pass

        tk.Label(f_dur, text=_t("zalman_lbl_cycle", "⏱ Döngü:"), font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                 bg=THEME["card_bg"]).pack(side="left")

        tk.Label(f_dur, text=_t("zalman_lbl_temp", "Sıcaklık:"), font=(f_font, fs(7)), fg=THEME["text_secondary"],
                 bg=THEME["card_bg"]).pack(side="left", padx=(6, 2))

        sp_temp = ttk.Spinbox(f_dur, from_=1, to=120, width=3, textvariable=self.zalman_temp_var,
                              command=_on_dur_change, font=(f_font, fs(8)))
        sp_temp.pack(side="left")
        sp_temp.bind("<FocusOut>", _on_dur_change)
        sp_temp.bind("<Return>", _on_dur_change)
        self.add_tooltip(sp_temp, _t("cost_zalman_temp_stay_tip", "Döngü modunda sıcaklığın ekranda kaç saniye kalacağını belirler"))

        tk.Label(f_dur, text=_t("zalman_unit_sec", "sn"), font=(f_font, fs(7)), fg=THEME["text_muted"],
                 bg=THEME["card_bg"]).pack(side="left", padx=(2, 8))

        tk.Label(f_dur, text=_t("zalman_lbl_blank", "Boşluk:"), font=(f_font, fs(7)), fg=THEME["text_secondary"],
                 bg=THEME["card_bg"]).pack(side="left", padx=(2, 2))

        sp_blank = ttk.Spinbox(f_dur, from_=1, to=30, width=3, textvariable=self.zalman_blank_var,
                               command=_on_dur_change, font=(f_font, fs(8)))
        sp_blank.pack(side="left")
        sp_blank.bind("<FocusOut>", _on_dur_change)
        sp_blank.bind("<Return>", _on_dur_change)
        self.add_tooltip(sp_blank, _t("cost_zalman_blank_stay_tip", "CPU ve GPU geçişleri arasında ekranın kaç saniye kapalı kalacağını belirler"))

        tk.Label(f_dur, text=_t("zalman_unit_sec", "sn"), font=(f_font, fs(7)), fg=THEME["text_muted"],
                 bg=THEME["card_bg"]).pack(side="left", padx=(2, 0))

        self.update_zalman_visibility()

    def build_rtss_panel(self, parent):
        f_font = THEME["font_family"]
        cfg = self.config

        card = self.create_card(parent, pady=(0, 6))

        f_top = tk.Frame(card, bg=THEME["card_bg"])
        f_top.pack(fill="x", padx=12, pady=(8, 2))
        self.rtss_enabled_var = tk.BooleanVar(value=cfg.get("rtss_enabled", True))
        self.make_check(f_top, _t("rtss_enable", "Oyun içi göstergeyi aç (RTSS)"), self.rtss_enabled_var,
                        self.on_rtss_change, fg=THEME["accent_cyan"], bold=True,
                        tooltip=_t("cost_rtss_enable_tip", "RivaTuner ile oyun ekranında canlı FPS, donanım sıcaklıkları ve priz elektrik maliyetini gösterir")).pack(side="left")
        self.rtss_multiline_var = tk.BooleanVar(value=cfg.get("rtss_multiline", True))
        self.make_check(f_top, _t("rtss_multiline", "Alt alta dikey liste"), self.rtss_multiline_var, self.on_rtss_change,
                        tooltip=_t("cost_rtss_multiline_tip", "İşaretliyse metrikleri alt alta liste yapar; işaretsizse tek satırda yan yana dizilim uygular")).pack(side="right")

        f_pos_hk = tk.Frame(card, bg=THEME["card_bg"])
        f_pos_hk.pack(fill="x", padx=12, pady=(4, 2))

        tk.Label(f_pos_hk, text=_t("rtss_lbl_pos", "KONUM:"), font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                 bg=THEME["card_bg"]).pack(side="left")

        self.rtss_pos_var = tk.StringVar(value=cfg.get("rtss_position", "top_right"))
        pos_menu_map = {
            "top_right": _t("rtss_pos_top_right", "↗ Sağ Üst (Varsayılan)"),
            "top_left": _t("rtss_pos_top_left", "↖ Sol Üst"),
            "bottom_left": _t("rtss_pos_bottom_left", "↙ Sol Alt"),
            "bottom_right": _t("rtss_pos_bottom_right", "↘ Sağ Alt")
        }
        rev_pos_map = {v: k for k, v in pos_menu_map.items()}

        opt_pos = ttk.Combobox(f_pos_hk, values=list(pos_menu_map.values()), state="readonly",
                                font=(f_font, fs(8)), width=13)
        opt_pos.set(pos_menu_map.get(self.rtss_pos_var.get(), _t("rtss_pos_top_right", "↗ Sağ Üst (Varsayılan)")))
        opt_pos.pack(side="left", padx=(4, 10))
        self.add_tooltip(opt_pos, _t("cost_rtss_pos_tip", "Oyun içi göstergenin ekrandaki köşesi (Sol Üst, Sağ Üst vb.)"))

        def _on_pos_select(e):
            val = rev_pos_map.get(opt_pos.get(), "top_left")
            self.rtss_pos_var.set(val)
            self.config["rtss_position"] = val
            self.save_config()
            self.on_rtss_change()
        opt_pos.bind("<<ComboboxSelected>>", _on_pos_select)
        self.opt_rtss_pos = opt_pos

        tk.Label(f_pos_hk, text=_t("rtss_lbl_toggle", "AÇ/KAPAT:"), font=(f_font, fs(7), "bold"), fg=THEME["accent_amber"],
                 bg=THEME["card_bg"]).pack(side="left")

        cur_hk = cfg.get("rtss_hotkey", "Alt+Shift+R")
        btn_hk = tk.Button(f_pos_hk, text=f"⌨ {cur_hk}", font=(f_font, fs(8), "bold"),
                           bg=THEME["card_inner"], fg=THEME["text_primary"],
                           activebackground=THEME["btn_hover"], activeforeground="#FFFFFF",
                           relief="flat", bd=0, padx=8, pady=2, cursor="hand2")
        btn_hk.pack(side="left", padx=(4, 2))
        self.btn_hotkey = btn_hk
        self.add_tooltip(btn_hk, _t("cost_rtss_hotkey_tip", "Oyun içi göstergeyi açıp kapatmak için global kısayol tuşu (Tıklayıp klavyeden yeni tuşa basın)"))

        self._capturing_hotkey = False
        def _start_key_capture():
            if self._capturing_hotkey:
                return
            self._capturing_hotkey = True
            btn_hk.config(text=_t("rtss_btn_press_key", "⌨ Tuşa Basın..."), bg="#F59E0B", fg="#090B11")
            
            def _on_key(event):
                vk = event.keycode
                if vk == 27:
                    self._capturing_hotkey = False
                    self.root.unbind_all("<KeyPress>")
                    btn_hk.config(text=f"⌨ {self.config.get('rtss_hotkey', 'Alt+Shift+R')}", bg=THEME["card_inner"], fg=THEME["text_primary"])
                    return "break"

                if vk in (16, 17, 18, 160, 161, 162, 163, 164, 165, 20):
                    return "break"

                mod = 0
                parts = []
                if event.state & 0x0004:
                    mod |= MOD_CONTROL
                    parts.append("Ctrl")
                if (event.state & 0x20000) or (event.state & 0x0008):
                    mod |= MOD_ALT
                    parts.append("Alt")
                if event.state & 0x0001:
                    mod |= MOD_SHIFT
                    parts.append("Shift")

                vk_names = {
                    0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4", 0x74: "F5", 0x75: "F6",
                    0x76: "F7", 0x77: "F8", 0x78: "F9", 0x79: "F10", 0x7A: "F11", 0x7B: "F12",
                    0x2D: "Insert", 0x24: "Home", 0x21: "PageUp", 0x22: "PageDown", 0x2E: "Delete", 0x23: "End",
                    0x91: "ScrollLock", 0x13: "Pause", 0xC0: "~", 0x20: "Space", 0x09: "Tab"
                }
                if vk in vk_names:
                    key_lbl = vk_names[vk]
                elif 0x41 <= vk <= 0x5A:
                    key_lbl = chr(vk)
                elif 0x30 <= vk <= 0x39:
                    key_lbl = chr(vk)
                elif 0x60 <= vk <= 0x69:
                    key_lbl = f"Num{vk - 0x60}"
                else:
                    key_lbl = event.keysym.upper()

                parts.append(key_lbl)
                key_name = "+".join(parts)

                self._capturing_hotkey = False
                self.root.unbind_all("<KeyPress>")

                self.config["rtss_hotkey"] = key_name
                self.config["rtss_hotkey_vk"] = vk
                self.config["rtss_hotkey_mod"] = mod
                self.save_config()

                if hasattr(self, "hotkey_mgr") and self.hotkey_mgr:
                    self.hotkey_mgr.start(key_name, vk=vk, mod=mod)

                btn_hk.config(text=f"⌨ {key_name}", bg=THEME["card_inner"], fg=THEME["text_primary"])
                if hasattr(self, "lbl_rtss_note"):
                    self.lbl_rtss_note.config(text=_t("cost_rtss_hotkey_set_feedback", "✓ Kısayol: {key_name}").format(key_name=key_name))
                    self.root.after(2000, lambda: self.lbl_rtss_note.config(text="") if hasattr(self, "lbl_rtss_note") else None)
                return "break"

            self.root.bind_all("<KeyPress>", _on_key)

        btn_hk.config(command=_start_key_capture)

        def _clear_hk():
            self.config["rtss_hotkey"] = "none"
            self.config["rtss_hotkey_vk"] = 0
            self.config["rtss_hotkey_mod"] = 0
            self.save_config()
            if hasattr(self, "hotkey_mgr") and self.hotkey_mgr:
                self.hotkey_mgr.stop()
            btn_hk.config(text=f"⌨ {_t('rtss_btn_none', 'Yok')}", bg=THEME["card_inner"], fg=THEME["text_muted"])
        self.make_btn(f_pos_hk, "✕", _clear_hk, fg=THEME["text_muted"], padx=5,
                      tooltip=_t("rtss_clr_hotkey_tip", "Atanmış kısayol tuşunu kaldır")).pack(side="left")

        # Kenar Boşlukları (Margin X, Margin Y)
        f_margins = tk.Frame(card, bg=THEME["card_bg"])
        f_margins.pack(fill="x", padx=12, pady=(2, 4))
        self.f_margins = f_margins

        tk.Label(f_margins, text=_t("rtss_lbl_margins", "KENAR BOŞLUĞU:"), font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                 bg=THEME["card_bg"]).pack(side="left")

        tk.Label(f_margins, text=_t("rtss_lbl_margin_x", "Yatay (X):"), font=(f_font, fs(7)), fg=THEME["text_secondary"],
                 bg=THEME["card_bg"]).pack(side="left", padx=(6, 2))

        self.rtss_margin_x_var = tk.StringVar(value=str(cfg.get("rtss_margin_x", 1)))
        opt_mx = ttk.Combobox(f_margins, values=["0", "1", "2", "3", "4", "5", "6"], state="readonly",
                              font=(f_font, fs(8)), width=3)
        opt_mx.set(str(self.rtss_margin_x_var.get()))
        opt_mx.pack(side="left", padx=(2, 8))
        self.add_tooltip(opt_mx, _t("rtss_margin_tip", "Göstergenin ekran kenarlarına ve köşelerine yapışmaması için bırakılacak boşluk miktarı (0: Sıfıra sıfır, 1-6: Nefes payı)"))

        def _on_mx_select(e):
            val = opt_mx.get()
            self.rtss_margin_x_var.set(val)
            self.config["rtss_margin_x"] = int(val)
            self.save_config()
            self.on_rtss_change()
        opt_mx.bind("<<ComboboxSelected>>", _on_mx_select)
        self.opt_rtss_margin_x = opt_mx

        tk.Label(f_margins, text=_t("rtss_lbl_margin_y", "Dikey (Y):"), font=(f_font, fs(7)), fg=THEME["text_secondary"],
                 bg=THEME["card_bg"]).pack(side="left", padx=(4, 2))

        self.rtss_margin_y_var = tk.StringVar(value=str(cfg.get("rtss_margin_y", 1)))
        opt_my = ttk.Combobox(f_margins, values=["0", "1", "2", "3", "4", "5"], state="readonly",
                              font=(f_font, fs(8)), width=3)
        opt_my.set(str(self.rtss_margin_y_var.get()))
        opt_my.pack(side="left", padx=(2, 4))
        self.add_tooltip(opt_my, _t("rtss_margin_tip", "Göstergenin ekran kenarlarına ve köşelerine yapışmaması için bırakılacak boşluk miktarı (0: Sıfıra sıfır, 1-6: Nefes payı)"))

        def _on_my_select(e):
            val = opt_my.get()
            self.rtss_margin_y_var.set(val)
            self.config["rtss_margin_y"] = int(val)
            self.save_config()
            self.on_rtss_change()
        opt_my.bind("<<ComboboxSelected>>", _on_my_select)
        self.opt_rtss_margin_y = opt_my

        self.f_sep = tk.Frame(card, bg=THEME["card_bg"])
        if not cfg.get("rtss_multiline", True):
            self.f_sep.pack(fill="x", padx=12, pady=(4, 6))
        tk.Label(self.f_sep, text=_t("rtss_sep_title", "YAKINLIK / AYRAÇ:"), font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                 bg=THEME["card_bg"]).pack(side="left")

        cur_sep = cfg.get("rtss_sep_style", "single")
        if cur_sep == "dot":
            cur_sep = "single"
        self.rtss_sep_var = tk.StringVar(value=cur_sep)
        def _set_sep(val):
            self.rtss_sep_var.set(val)
            self.config["rtss_sep_style"] = val
            self.save_config()
            self.on_rtss_change()

        for val, label in (
            ("single", _t("rtss_sep_single", "Tek Boşluk")),
            ("compact", _t("rtss_sep_compact", "Çift Boşluk")),
            ("pipe", _t("rtss_sep_pipe", "Çizgi ( | )")),
            ("slash", _t("rtss_sep_slash", "Bölü ( / )")),
            ("dash", _t("rtss_sep_dash", "Tire ( - )"))
        ):
            rb = tk.Radiobutton(self.f_sep, text=label, variable=self.rtss_sep_var, value=val,
                                command=lambda v=val: _set_sep(v),
                                font=(f_font, fs(7), "bold"), fg=THEME["text_secondary"], bg=THEME["card_bg"],
                                selectcolor=THEME["card_inner"], activebackground=THEME["card_bg"],
                                activeforeground=THEME["text_primary"], bd=0, highlightthickness=0, cursor="hand2")
            rb.pack(side="left", padx=(5, 0))
            self.add_tooltip(rb, _t("cost_rtss_sep_tip", "Yatay dizilimde metrikler arasına '{label}' ekler").format(label=label))

        tk.Label(self.f_sep, text=_t("rtss_sep_color", "Renk:"), font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                 bg=THEME["card_bg"]).pack(side="left", padx=(10, 2))
        cur_sep_col = cfg.get("rtss_sep_color", "#64748B")
        self.btn_sep_color = tk.Button(self.f_sep, text="■", font=(f_font, fs(9), "bold"),
                                       bg=THEME["card_inner"], fg=cur_sep_col,
                                       activebackground=THEME["btn_hover"], activeforeground=cur_sep_col,
                                       relief="flat", bd=0, width=3, cursor="hand2")
        self.btn_sep_color.pack(side="left", padx=2)
        self.add_tooltip(self.btn_sep_color, _t("cost_rtss_sep_color_tip", "Yatay dizilimde metrikler arasındaki ayracın rengini seç"))

        def _open_sep_color_menu():
            menu = tk.Menu(self.root, tearoff=0, bg="#121624", fg="#F1F5F9",
                           activebackground="#1E263D", activeforeground="#FFFFFF",
                           font=(THEME["font_family"], fs(8), "bold"))
            sep_pal = [
                (_t("color_gray", "Gri / Nötr"), "#64748B"),
                (_t("color_cyan", "Cyan"),       "#00E5FF"),
                (_t("color_yellow", "Sarı"),     "#F59E0B"),
                (_t("color_green", "Yeşil"),     "#10B981"),
                (_t("color_purple", "Mor"),      "#A855F7"),
                (_t("color_red", "Kırmızı"),     "#F43F5E"),
                (_t("color_white", "Beyaz"),     "#FFFFFF"),
            ]
            for name, hex_code in sep_pal:
                def pick_col(c=hex_code):
                    self.config["rtss_sep_color"] = c
                    self.btn_sep_color.config(fg=c, activeforeground=c)
                    self.save_config()
                    self.on_rtss_change()
                menu.add_command(label=f"● {name}", foreground=hex_code, command=pick_col)
            try:
                menu.tk_popup(self.btn_sep_color.winfo_rootx(), self.btn_sep_color.winfo_rooty() + self.btn_sep_color.winfo_height())
            finally:
                menu.grab_release()

        self.btn_sep_color.config(command=_open_sep_color_menu)

        self.f_zeros = tk.Frame(card, bg=THEME["card_bg"])
        self.f_zeros.pack(fill="x", padx=12, pady=(0, 6))
        self.rtss_keep_zeros_var = tk.BooleanVar(value=cfg.get("rtss_keep_zeros", True))
        self.make_check(self.f_zeros, _t("rtss_keep_zeros", "0 olan değerleri ekranda tut (Açılıp kapanmayı ve titremeyi önle)"),
                        self.rtss_keep_zeros_var, self.on_rtss_change, fg=THEME["accent_green"],
                        tooltip=_t("cost_rtss_keep_zeros_tip", "Değer sıfır olduğunda satırın kaybolmasını engeller; ekranın titremesini ve boyut değişimini önler")).pack(side="left")

        f_cols = tk.Frame(card, bg=THEME["card_bg"])
        f_cols.pack(fill="x", padx=10, pady=(2, 6))

        f_col_left = tk.Frame(f_cols, bg=THEME["card_bg"])
        f_col_left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        f_col_right = tk.Frame(f_cols, bg=THEME["card_bg"])
        f_col_right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        self.rtss_vars = {}
        self.rtss_entries = {}
        self.rtss_size_entries = {}
        self.rtss_color_btns = {}
        self.rtss_colors = {}

        def _build_rows_group(parent_container, title_text, color_tag, row_list):
            grp_hdr = tk.Frame(parent_container, bg=THEME["card_bg"])
            grp_hdr.pack(fill="x", padx=2, pady=(4, 3))
            tk.Label(grp_hdr, text=title_text, font=(f_font, fs(7), "bold"), fg=color_tag,
                     bg=THEME["card_bg"]).pack(side="left")
            tk.Frame(grp_hdr, bg=THEME["card_border"], height=1).pack(side="left", fill="x", expand=True, padx=(6, 0))

            col_head = tk.Frame(parent_container, bg=THEME["card_bg"])
            col_head.pack(fill="x", padx=2, pady=(1, 2))
            tk.Label(col_head, text=_t("rtss_col_metric", "GÖSTERGE"), font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                     bg=THEME["card_bg"]).pack(side="left")
            f_hdr_r = tk.Frame(col_head, bg=THEME["card_bg"])
            f_hdr_r.pack(side="right")
            tk.Label(f_hdr_r, text=_t("rtss_col_label", "BAŞLIK"), font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                     bg=THEME["card_bg"], width=6).pack(side="left", padx=1)
            tk.Label(f_hdr_r, text=_t("rtss_col_size", "PUNTO"), font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                     bg=THEME["card_bg"], width=3).pack(side="left", padx=1)
            tk.Label(f_hdr_r, text=_t("rtss_col_color", "RENK"), font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                     bg=THEME["card_bg"], width=3).pack(side="left", padx=1)

            for show_key, label_key, color_key, size_key, title, def_color, def_size, def_label, def_active in row_list:
                row = tk.Frame(parent_container, bg=THEME["card_bg"])
                row.pack(fill="x", padx=2, pady=1)

                var = tk.BooleanVar(value=cfg.get(show_key, def_active))
                self.rtss_vars[show_key] = var
                display_title = _t(f"rtss_row_{show_key.replace('rtss_show_', '')}", title)
                self.make_check(row, display_title, var, self.on_rtss_change, fg=THEME["text_primary"],
                                tooltip=_t("cost_rtss_metric_vis_tip", "'{display_title}' metriğini oyun içi ekranda göster / gizle").format(display_title=display_title)).pack(side="left")

                f_ctrl = tk.Frame(row, bg=THEME["card_bg"])
                f_ctrl.pack(side="right")

                cur_color = str(cfg.get(color_key, def_color))
                self.rtss_colors[color_key] = cur_color

                ent_lbl = tk.Entry(f_ctrl, width=6, font=(f_font, fs(8), "bold"), bg=THEME["card_inner"], fg=cur_color,
                                   insertbackground=THEME["text_primary"], relief="flat", justify="center",
                                   highlightbackground=THEME["card_border"], highlightcolor=cur_color,
                                   highlightthickness=1)
                ent_lbl.insert(0, str(cfg.get(label_key, def_label)))
                ent_lbl.pack(side="left", padx=1, ipady=1)
                ent_lbl.bind("<KeyRelease>", self.on_rtss_change)
                self.rtss_entries[label_key] = ent_lbl
                self.add_tooltip(ent_lbl, _t("cost_rtss_metric_lbl_tip", "'{display_title}' için ekranda gösterilecek özel başlık metni (Boş bırakılırsa sadece sayı gösterilir)").format(display_title=display_title))

                ent_sz = tk.Entry(f_ctrl, width=3, font=(f_font, fs(8), "bold"), bg=THEME["card_inner"], fg=THEME["text_primary"],
                                  insertbackground=THEME["text_primary"], relief="flat", justify="center",
                                  highlightbackground=THEME["card_border"], highlightcolor=THEME["accent_cyan"],
                                  highlightthickness=1)
                ent_sz.insert(0, str(cfg.get(size_key, def_size)))
                ent_sz.pack(side="left", padx=1, ipady=1)
                ent_sz.bind("<KeyRelease>", self.on_rtss_change)
                self.rtss_size_entries[size_key] = ent_sz
                self.add_tooltip(ent_sz, _t("cost_rtss_metric_size_tip", "'{display_title}' metin boyutu ölçeği (Varsayılan 100, büyük için 120+, küçük için 80)").format(display_title=display_title))

                btn_col = tk.Button(f_ctrl, text="■", font=(f_font, fs(9), "bold"), bg=THEME["card_inner"], fg=cur_color,
                                    activebackground=THEME["btn_hover"], activeforeground=cur_color,
                                    relief="flat", bd=0, width=3, cursor="hand2")
                btn_col.pack(side="left", padx=1, ipady=1)
                self.add_tooltip(btn_col, _t("cost_rtss_metric_col_tip", "'{display_title}' gösterge metninin rengini değiştir").format(display_title=display_title))

                def make_color_cmd(c_key=color_key, b=btn_col, e=ent_lbl):
                    return lambda: self.open_color_picker_menu(b, c_key, e)

                btn_col.config(command=make_color_cmd())
                self.rtss_color_btns[color_key] = btn_col

                if show_key == "rtss_show_session":
                    self.rtss_kwh_var = tk.BooleanVar(value=cfg.get("rtss_show_kwh", True))
                    self.make_check(parent_container, _t("rtss_session_kwh", "  ↳ Oturum yanında kWh de göster"), self.rtss_kwh_var,
                                    self.on_rtss_change,
                                    tooltip=_t("cost_rtss_session_kwh_tip", "Oturum maliyetinin yanına harcanan toplam kWh elektriği de ekler")).pack(anchor="w", padx=(14, 0))

        _build_rows_group(f_col_left, _t("rtss_grp_hw", "🎮 OYUN & DONANIM"), "#38BDF8", self.RTSS_ROWS_HW)
        _build_rows_group(f_col_right, _t("rtss_grp_pwr", "⚡ GÜÇ & MALİYET"), THEME["accent_amber"], self.RTSS_ROWS_PWR)

        f_pwr_extra = tk.Frame(f_col_right, bg=THEME["card_bg"])
        f_pwr_extra.pack(fill="x", pady=(10, 0))

        self.btn_test_screen = self.make_btn(
            f_pwr_extra, _t("rtss_btn_test_screen", "🎮 Canlı OSD Test Ekranı"), self.toggle_test_screen, fg=THEME["accent_cyan"], pady=4,
            tooltip=_t("cost_rtss_test_screen_tip", "Oyun açmadan masaüstünde yarı saydam bir pencere ile RTSS göstergesinin konum ve renklerini canlı test edin")
        )
        self.btn_test_screen.pack(fill="x", pady=(0, 4))

        self.make_btn(f_pwr_extra, _t("rtss_btn_clear_screen", "🧹 Ekrandaki Metni Temizle"), self.clear_rtss_now, pady=3,
                      tooltip=_t("cost_rtss_clear_tip", "RTSS arabelleğini sıfırlar ve ekrandaki takılı kalmış gösterge yazılarını derhal siler")).pack(fill="x")

        self.lbl_rtss_note = tk.Label(f_pwr_extra, text="", font=(f_font, fs(7), "bold"), fg=THEME["accent_green"],
                                      bg=THEME["card_bg"])
        self.lbl_rtss_note.pack(anchor="w", pady=(2, 0))

        tk.Label(card, text=_t("rtss_footer_help", "• Boş başlık = sadece değer  • Punto: 100 normal, 120 büyük, 80 küçük  • Renk kutusuna (■) basarak palet seçin."),
                 font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["card_bg"], justify="center").pack(fill="x", padx=10, pady=(6, 8))

    def open_color_picker_menu(self, btn, color_key, entry_widget):
        menu = tk.Menu(self.root, tearoff=0, bg="#121624", fg="#F1F5F9",
                       activebackground="#1E263D", activeforeground="#FFFFFF",
                       font=(THEME["font_family"], fs(8), "bold"))
        palette_names = {
            "#A855F7": _t("color_purple", "Mor"),
            "#00E5FF": _t("color_cyan", "Cyan"),
            "#10B981": _t("color_green", "Yeşil"),
            "#F43F5E": _t("color_red", "Kırmızı"),
            "#F59E0B": _t("color_yellow", "Sarı"),
            "#FFFFFF": _t("color_white", "Beyaz"),
        }
        for name, hex_code in self.RTSS_PALETTE:
            def pick_color(code=hex_code):
                self.rtss_colors[color_key] = code
                self.config[color_key] = code
                btn.config(fg=code, activeforeground=code)
                entry_widget.config(fg=code, highlightcolor=code)
                self.save_config()
                self.on_rtss_change()
            disp_n = palette_names.get(hex_code, name)
            menu.add_command(label=f"● {disp_n}", foreground=hex_code, command=pick_color)

        try:
            menu.tk_popup(btn.winfo_rootx(), btn.winfo_rooty() + btn.winfo_height())
        finally:
            menu.grab_release()

    def on_rtss_change(self, *_):
        c = self.config
        is_multi = self.rtss_multiline_var.get()
        c["rtss_multiline"] = is_multi
        if hasattr(self, "f_sep") and self.f_sep:
            if is_multi:
                self.f_sep.pack_forget()
            else:
                if hasattr(self, "f_zeros") and self.f_zeros:
                    self.f_sep.pack(fill="x", padx=12, pady=(4, 6), before=self.f_zeros)
                else:
                    self.f_sep.pack(fill="x", padx=12, pady=(4, 6))
        c["rtss_show_kwh"] = self.rtss_kwh_var.get()
        if hasattr(self, "rtss_pos_var"):
            c["rtss_position"] = self.rtss_pos_var.get()
        if hasattr(self, "rtss_margin_x_var"):
            try:
                c["rtss_margin_x"] = int(self.rtss_margin_x_var.get())
            except Exception:
                pass
        if hasattr(self, "rtss_margin_y_var"):
            try:
                c["rtss_margin_y"] = int(self.rtss_margin_y_var.get())
            except Exception:
                pass
        if hasattr(self, "rtss_sep_var"):
            c["rtss_sep_style"] = self.rtss_sep_var.get()
        if hasattr(self, "rtss_keep_zeros_var"):
            c["rtss_keep_zeros"] = self.rtss_keep_zeros_var.get()
        c["rtss_show_gpu"] = False
        c["rtss_show_cpu"] = False
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
        if hasattr(self, "test_win") and self.test_win and self.test_win.winfo_exists():
            self.update_test_screen()

    def clear_rtss_now(self):
        if hasattr(self, "rtss") and self.rtss:
            self.rtss.release_osd()
        self.lbl_rtss_note.config(text=_t("cost_rtss_cleared_feedback", "✓ Temizlendi (kapalıysa yeniden yazılmaz)"))
        self.root.after(2500, lambda: self.lbl_rtss_note.config(text="") if hasattr(self, "lbl_rtss_note") else None)

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
        keep_zeros = cfg.get("rtss_keep_zeros", True)

        sep_mode = cfg.get("rtss_sep_style", "single")
        sep_color = str(cfg.get("rtss_sep_color", "#64748B")).replace("#", "").upper()
        if sep_mode == "single":
            sep_char = " "
        elif sep_mode == "pipe":
            sep_char = " | "
        elif sep_mode == "slash":
            sep_char = " / "
        elif sep_mode == "dash":
            sep_char = " - "
        else:
            sep_char = "  "

        if sep_mode not in ("compact", "single") and sep_color:
            sep = f"<C={sep_color}>{sep_char}<C>"
        else:
            sep = sep_char

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

            txt_item = f"{lbl} {val_str}" if lbl else val_str
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

        gpu_w = hw.get("gpu_w", 0)
        gpu_clk = hw.get("gpu_clk", 0)
        vram_mb = hw.get("vram_mb", 0)
        cpu_w = hw.get("cpu_w", 0)
        cpu_clk = hw.get("cpu_clk", 0)
        kwh_str = f" ({kwh:.2f} kWh)" if cfg.get("rtss_show_kwh", True) else ""
        clk_str = f"{cpu_clk/1000.0:.2f}GHz" if cpu_clk >= 1000 else f"{cpu_clk}MHz"

        try:
            month_tl = HistoryManager.get_summary().get("month_tl", 0.0)
        except Exception:
            month_tl = 0.0

        # Deklaratif RTSS Metrik Listesi
        metrics = [
            ("rtss_show_fps", "rtss_label_fps", "rtss_color_fps", "rtss_size_fps", "", "#F43F5E", "100", "<FR>", True),
            ("rtss_show_gpu_uti", "rtss_label_gpu_uti", "rtss_color_gpu_uti", "rtss_size_gpu_uti", "G", "#00E5FF", "100", f"%{gpu_uti}", keep_zeros or gpu_uti > 0),
            ("rtss_show_gpu_temp", "rtss_label_gpu_temp", "rtss_color_gpu_temp", "rtss_size_gpu_temp", "GPU-C", "#00E5FF", "100", f"{gpu_temp}°C", True),
            ("rtss_show_gpu_w", "rtss_label_gpu_w", "rtss_color_gpu_w", "rtss_size_gpu_w", "GPU-W", "#00E5FF", "100", f"{gpu_w:.0f}W", keep_zeros or gpu_w > 0),
            ("rtss_show_gpu_clk", "rtss_label_gpu_clk", "rtss_color_gpu_clk", "rtss_size_gpu_clk", "GPU-CLK", "#38BDF8", "100", f"{gpu_clk}MHz", keep_zeros or gpu_clk > 0),
            ("rtss_show_vram", "rtss_label_vram", "rtss_color_vram", "rtss_size_vram", "VRAM", "#818CF8", "100", f"{vram_mb/1024.0:.1f}GB", keep_zeros or vram_mb > 0),
            ("rtss_show_cpu_uti", "rtss_label_cpu_uti", "rtss_color_cpu_uti", "rtss_size_cpu_uti", "C", "#F59E0B", "100", f"%{cpu_uti}", keep_zeros or cpu_uti > 0),
            ("rtss_show_cpu_temp", "rtss_label_cpu_temp", "rtss_color_cpu_temp", "rtss_size_cpu_temp", "CPU-C", "#F59E0B", "100", f"{cpu_temp}°C", True),
            ("rtss_show_cpu_w", "rtss_label_cpu_w", "rtss_color_cpu_w", "rtss_size_cpu_w", "CPU-W", "#F59E0B", "100", f"{cpu_w:.0f}W", keep_zeros or cpu_w > 0),
            ("rtss_show_cpu_clk", "rtss_label_cpu_clk", "rtss_color_cpu_clk", "rtss_size_cpu_clk", "CPU-CLK", "#FCD34D", "100", clk_str, keep_zeros or cpu_clk > 0),
            ("rtss_show_ram", "rtss_label_ram", "rtss_color_ram", "rtss_size_ram", "R", "#A855F7", "100", f"%{ram_uti}", True),
            ("rtss_show_fan", "rtss_label_fan", "rtss_color_fan", "rtss_size_fan", "FAN", "#34D399", "100", f"{fan_rpm}RPM", keep_zeros or fan_rpm > 0),
            ("rtss_show_power", "rtss_label_power", "rtss_color_power", "rtss_size_power", "GUC", "#00E5FF", "100", f"{total_wall_w:.0f}W", True),
            ("rtss_show_hourly", "rtss_label_hourly", "rtss_color_hourly", "rtss_size_hourly", "T", "#10B981", "100", f"{hourly_tl:.2f}", True),
            ("rtss_show_session", "rtss_label_session", "rtss_color_session", "rtss_size_session", "OTURUM", "#F59E0B", "100", f"{self.format_currency(total_tl)}{kwh_str}", True),
            ("rtss_show_today", "rtss_label_today", "rtss_color_today", "rtss_size_today", "BUGUN", "#A855F7", "100", self.format_currency(today_tl), True),
            ("rtss_show_month", "rtss_label_month", "rtss_color_month", "rtss_size_month", "AY", "#EC4899", "100", self.format_currency(month_tl), True),
        ]

        all_parts = []
        for m in metrics:
            if m[8]:
                val = _fmt(m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7])
                if val:
                    all_parts.append(val)

        if not all_parts:
            return ""

        pos_mode = cfg.get("rtss_position", "top_right")
        margin_x = int(cfg.get("rtss_margin_x", 1))
        margin_y = int(cfg.get("rtss_margin_y", 1))

        pad_x = " " * max(0, margin_x)
        top_pad = f"<S=50>{' ' * margin_y}\n<S>" if margin_y > 0 else ""
        bottom_pad = f"\n<S=50>{' ' * margin_y}<S>" if margin_y > 0 else ""

        if pos_mode == "top_right":
            pos_tag = f"<P2><L1><A=-1>{top_pad}<A=-1>"
            line_break = "\n<A=-1>"
            is_right_aligned = True
        elif pos_mode == "bottom_right":
            pos_tag = f"<P8><L3><A=-1>"
            line_break = "\n<A=-1>"
            is_right_aligned = True
        elif pos_mode == "bottom_left":
            pos_tag = f"<P6><L2>"
            line_break = "\n"
            is_right_aligned = False
        else: # top_left
            pos_tag = f"<P0><L0>{top_pad}"
            line_break = "\n"
            is_right_aligned = False

        if cfg.get("rtss_multiline", True):
            if is_right_aligned:
                parts_formatted = [p + pad_x for p in all_parts]
            else:
                parts_formatted = [pad_x + p for p in all_parts]

            res = f"{pos_tag}" + line_break.join(parts_formatted)
            if pos_mode in ("bottom_left", "bottom_right") and bottom_pad:
                res += bottom_pad
            return res
        else:
            # Tek satır modunda metrikler arasında yalnızca kullanıcının seçtiği sep yer alır
            # Yatay kenar boşluğu (pad_x) sadece en dış kenara eklenir
            joined_line = sep.join(all_parts)
            if is_right_aligned:
                res = f"{pos_tag}{joined_line}{pad_x}"
            else:
                res = f"{pos_tag}{pad_x}{joined_line}"
            if pos_mode in ("bottom_left", "bottom_right") and bottom_pad:
                res += bottom_pad
            return res

    def refresh_cost_tab_ui(self):
        """Dil değiştiğinde maliyet ve RTSS sekmesindeki tüm kartları güncel dille yeniden oluşturur."""
        if hasattr(self, 'f_col_sys') and self.f_col_sys and self.f_col_sys.winfo_exists():
            for w in self.f_col_sys.winfo_children():
                w.destroy()
            self.build_tab_genel(self.f_col_sys)
            self.build_tab_cihaz(self.f_col_sys)
            self.build_zalman_card(self.f_col_sys)

        if hasattr(self, 'f_col_rtss') and self.f_col_rtss and self.f_col_rtss.winfo_exists():
            for w in self.f_col_rtss.winfo_children():
                w.destroy()
            self.build_rtss_panel(self.f_col_rtss)

