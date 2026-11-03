"""
WattCost HaYTooL - SmartSwitch Tab Modülü
4 Kademeli akıllı otomatik güç planı otomasyonunu yönetir.
"""
import tkinter as tk
from config_manager import THEME, UI_SCALE, fs
from language_manager import _t


class SmartSwitchTabMixin:
    """4 Kademeli Akıllı Güç Planı Otomasyonu Sekmesi."""

    def build_tab_smart(self):
        container = self.tab_smart
        for w in container.winfo_children():
            w.destroy()

        f_font = THEME["font_family"]
        f_scroll_box = tk.Frame(container, bg=THEME["bg"])
        f_scroll_box.pack(fill="both", expand=True, padx=12, pady=6)

        # 1. Kontrol Merkezi & Durum Kartı
        card_ctrl = self.create_card(f_scroll_box, pady=(0, 6))
        self.make_card_title(card_ctrl, _t("smart_ctrl_title", "AKILLI GÜÇ OTOMASYONU YÖNETİM MERKEZİ"), THEME["accent_rose"])

        f_ctrl_row = tk.Frame(card_ctrl, bg=THEME["card_bg"])
        f_ctrl_row.pack(fill="x", padx=14, pady=(4, 6))

        f_switches = tk.Frame(f_ctrl_row, bg=THEME["card_bg"])
        f_switches.pack(side="left", fill="x", expand=True)

        self.make_check(
            f_switches, _t("smart_enable_lbl", "🤖 Akıllı Geçişi Aktif Et"),
            self.smart_switch_var, self.on_smart_switch_toggled,
            fg=THEME["accent_cyan"], bold=True, bg=THEME["card_bg"],
            tooltip=_t("smart_enable_tip", "Sistem GPU/CPU yüküne ve oyun durumuna göre güç planını ve Kademe 1-4 arasında otomatik değiştirir")
        ).pack(anchor="w", pady=(0, 4))

        self.make_check(
            f_switches, _t("smart_hz_enable_lbl", "🖥️ Monitör Hz Otomasyonu (kademe Hz hedeflerini uygula)"),
            self.smart_hz_auto_var, self.on_smart_hz_toggled,
            fg=THEME["accent_cyan"], bold=True, bg=THEME["card_bg"],
            tooltip=_t("smart_hz_enable_tip", "Açıkken her kademe geçişinde 1. ve 2. monitör için seçtiğin Hz değerleri uygulanır")
        ).pack(anchor="w", pady=(0, 4))

        f_feedback_row = tk.Frame(f_switches, bg=THEME["card_bg"])
        f_feedback_row.pack(anchor="w", pady=(2, 0))

        self.make_check(
            f_feedback_row, _t("smart_sound_lbl", "🔔 Geçişte Ses Çal"),
            self.smart_switch_sound_var, self.on_smart_feedback_toggled,
            fg=THEME["text_secondary"], bg=THEME["card_bg"],
            tooltip=_t("smart_sound_tip", "Otomasyon kademe değiştirdiğinde sesli bildirim çalar")
        ).pack(side="left", padx=(0, 14))

        self.make_check(
            f_feedback_row, _t("smart_toast_lbl", "💬 Geçişte Toast Bildirim Göster"),
            self.smart_switch_toast_var, self.on_smart_feedback_toggled,
            fg=THEME["text_secondary"], bg=THEME["card_bg"],
            tooltip=_t("smart_toast_tip", "Otomasyon güç planı değiştirdiğinde ekranın sağ altında açılan bilgi kutusunu gösterir")
        ).pack(side="left")

        f_badge_col = tk.Frame(f_ctrl_row, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_badge_col.pack(side="right", padx=(10, 0), pady=2)

        self.lbl_smart_status = tk.Label(
            f_badge_col,
            text=_t("smart_status_disabled", "● Durum: Devre Dışı (Manuel Yönetim)"),
            font=(f_font, fs(8), "bold"), fg=THEME["text_muted"], bg=THEME["card_inner"],
            padx=int(10 * UI_SCALE), pady=int(6 * UI_SCALE), wraplength=int(260 * UI_SCALE), justify="center"
        )
        self.lbl_smart_status.pack()

        # Açılışta mevcut otomasyon durumunu yansıt (yanlış "Devre Dışı" görünmesin)
        if self.smart_switch_var.get():
            self.lbl_smart_status.config(
                text=_t("smart_status_idle_listening", "● Aktif (Sensörler Dinleniyor)"),
                fg=THEME["accent_green"]
            )

        # Canlı durum şeridi: CPU / GPU yükü ve monitör Hz değerleri
        f_live = tk.Frame(card_ctrl, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_live.pack(fill="x", padx=14, pady=(0, 6))
        self.lbl_smart_live = tk.Label(
            f_live, text=_t("smart_live_loading", "⚡ Canlı: sensörler bekleniyor..."),
            font=(f_font, fs(8), "bold"), fg=THEME["accent_cyan"], bg=THEME["card_inner"],
            anchor="w", padx=8, pady=3
        )
        self.lbl_smart_live.pack(fill="x")
        self.add_tooltip(self.lbl_smart_live, self._smart_threshold_tooltip)

        # 2. Kademeli Güç Planı ve Monitör Hz Matrisi
        card_tiers = self.create_card(f_scroll_box, pady=(0, 6))
        self.make_card_title(card_tiers, _t("smart_matrix_title", "KADEMELİ GÜÇ DÜZENİ SEÇİMLERİ"), THEME["accent_cyan"])

        # Kademe sayısı seçimi (2 / 3 / 4)
        f_count = tk.Frame(card_tiers, bg=THEME["card_bg"])
        f_count.pack(fill="x", padx=12, pady=(0, 4))

        tk.Label(f_count, text=_t("smart_lbl_tier_count", "Kademe Sayısı:"), font=(f_font, fs(7), "bold"),
                 fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left", padx=(0, 6))

        if not hasattr(self, 'smart_tier_count_var'):
            import tkinter as _tk
            self.smart_tier_count_var = _tk.IntVar(value=int(getattr(self.smart_switcher, 'tier_count', 4)))

        for _n in (2, 3, 4):
            _rb = tk.Radiobutton(
                f_count, text=str(_n), variable=self.smart_tier_count_var, value=_n,
                command=self.on_smart_tier_count_changed,
                font=(f_font, fs(8), "bold"), bg=THEME["card_bg"], fg=THEME["accent_cyan"],
                activebackground=THEME["card_bg"], activeforeground=THEME["accent_cyan"],
                selectcolor=THEME["card_inner"], bd=0, highlightthickness=0, cursor="hand2", padx=4
            )
            _rb.pack(side="left", padx=2)
            self.add_tooltip(_rb, _t("smart_tier_count_tip", "Otomasyonun kullanacağı kademe sayısı: 2 = Boşta + Yük, 3 = Boşta + Orta + Yük, 4 = Boşta + Düşük + Orta + Maksimum"))

        tk.Label(f_count, text=_t("smart_tier_count_hint", "(2: Boşta+Yük, 3: Boşta+Orta+Yük, 4: tam dört kademe)"),
                 font=(f_font, fs(6), "italic"), fg=THEME["text_muted"], bg=THEME["card_bg"]).pack(side="left", padx=(8, 0))

        # Algılanan Monitör ve Desteklenen Hz Bilgi Çubuğu
        f_mon_info = tk.Frame(card_tiers, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_mon_info.pack(fill="x", padx=12, pady=(0, 6))

        f_mon_info_top = tk.Frame(f_mon_info, bg=THEME["card_inner"])
        f_mon_info_top.pack(fill="x", padx=8, pady=(4, 1))

        self.lbl_mon_detect = tk.Label(
            f_mon_info_top,
            text=_t("smart_mon_detecting", "🖥️ Algılanan Monitör: Algılanıyor..."),
            font=(f_font, fs(7), "bold"), fg=THEME["accent_cyan"], bg=THEME["card_inner"],
            anchor="w", padx=8, pady=2
        )
        self.lbl_mon_detect.pack(side="left", fill="x", expand=True)

        self.make_btn(
            f_mon_info_top, _t("smart_btn_refresh_mon", "🔄 Monitörü Yeniden Algıla"),
            self.update_smart_switch_options,
            fg=THEME["accent_cyan"], bg=THEME["card_bg"], padx=8, pady=2,
            tooltip=_t("smart_btn_refresh_mon_tip", "Bağlı monitör çözünürlüğünü ve desteklenen Hz değerlerini yeniden tarar")
        ).pack(side="right", padx=6, pady=2)

        self.make_btn(
            f_mon_info_top, _t("smart_btn_hz_test", "🖥️ Hz Değişimini Test Et"),
            self.test_refresh_rate,
            fg=THEME["accent_green"], bg=THEME["card_bg"], padx=8, pady=2,
            tooltip=_t("smart_btn_hz_test_tip", "Aktif kademenin hedef Hz değerini uygular ve monitörün gerçekten o hıza geçip geçmediğini kontrol eder")
        ).pack(side="right", padx=6, pady=2)

        self.lbl_mon_rates = tk.Label(
            f_mon_info,
            text=_t("smart_rates_detecting", "✨ Monitörünüzün Desteklediği Hz Değerleri: Algılanıyor..."),
            font=(f_font, fs(7)), fg=THEME["accent_green"], bg=THEME["card_inner"],
            anchor="w", padx=8, pady=2
        )
        self.lbl_mon_rates.pack(fill="x", pady=(0, 4))

        f_grid = tk.Frame(card_tiers, bg=THEME["card_bg"])
        f_grid.pack(fill="x", padx=12, pady=(0, 6))
        f_grid.columnconfigure(0, weight=1, uniform="tier_col")
        f_grid.columnconfigure(1, weight=1, uniform="tier_col")
        f_grid.rowconfigure(0, weight=1, uniform="tier_row")
        f_grid.rowconfigure(1, weight=1, uniform="tier_row")

        # Kademe sayısına göre başlık/açıklama: 2 ve 3 kademede en üst kart "Yük" rolündedir
        tier_count_now = max(2, min(4, int(getattr(self.smart_switcher, 'tier_count', 4))))
        t2_title = _t("smart_t2_title", "🌿 KADEME 2: DÜŞÜK / GÜNLÜK & MEDYA")
        t2_sub = _t("smart_t2_sub", "Web gezintisi, video izleme ve hafif ofis yükü (GPU veya CPU ≥ Eşik 2).")
        if tier_count_now == 2:
            t2_title = _t("smart_t2_top_title", "🌿 KADEME 2: YÜK / PERFORMANS (EN ÜST)")
            t2_sub = _t("smart_t2_top_sub", "Eşik 2 aşıldığında devreye giren en üst kademe. RTSS oyun ve priz Watt tetikleyicileri de buraya geçer.")

        t3_title = _t("smart_t3_title", "⚖️ KADEME 3: ORTA / MULTITASK & İŞ")
        t3_sub = _t("smart_t3_sub", "Çoklu görev, derleme veya orta grafik yükü (GPU veya CPU ≥ Eşik 3).")
        if tier_count_now == 3:
            t3_title = _t("smart_t3_top_title", "⚖️ KADEME 3: YÜK / MAKSİMUM (EN ÜST)")
            t3_sub = _t("smart_t3_top_sub", "Eşik 3 aşıldığında devreye giren en üst kademe. RTSS oyun ve priz Watt tetikleyicileri de buraya geçer.")

        def _build_tier_card(parent, tier_num, title, color, guid_var, hz_var, hz2_var, sub_txt):
            f_box = tk.Frame(parent, bg=THEME["card_inner"], highlightbackground=color, highlightthickness=1)
            
            f_head = tk.Frame(f_box, bg=THEME["card_inner"])
            f_head.pack(fill="x", padx=8, pady=(5, 2))
            tk.Label(f_head, text=title, font=(f_font, fs(8), "bold"), fg=color, bg=THEME["card_inner"]).pack(side="left")

            lbl_desc = tk.Label(f_box, text=sub_txt, font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["card_inner"],
                                wraplength=int(420 * UI_SCALE), justify="left", height=2, anchor="nw")
            lbl_desc.pack(fill="x", padx=8, pady=(0, 4))

            # Form Düzeni: Güç Planı ve Monitör Hz Seçimi
            f_form = tk.Frame(f_box, bg=THEME["card_inner"])
            f_form.pack(fill="x", padx=8, pady=(0, 6))
            f_form.columnconfigure(1, weight=1)

            lbl_plan = tk.Label(f_form, text=_t("smart_lbl_plan", "Güç Planı:"), font=(f_font, fs(7), "bold"),
                                fg=THEME["text_secondary"], bg=THEME["card_inner"], anchor="w")
            lbl_plan.grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 2))

            om_plan = tk.OptionMenu(f_form, guid_var, "")
            om_plan.config(bg=THEME["card_bg"], fg=THEME["text_primary"], activebackground=THEME["card_inner"],
                           relief="flat", highlightthickness=1, font=(f_font, fs(7), "bold"), anchor="w")
            om_plan.grid(row=0, column=1, sticky="ew", pady=(0, 2))
            self.add_tooltip(om_plan, lambda t=title: _t("smart_tier_plan_tip", "{title} aktif olduğunda uygulanacak Windows güç planı").format(title=t))

            # 2. Satır: Monitör Yenileme Hızı (Hz) - 1. ve 2. monitör ayrı ayrı
            lbl_hz = tk.Label(f_form, text=_t("smart_lbl_hz", "Ekran Hz:"), font=(f_font, fs(7), "bold"),
                              fg=THEME["text_secondary"], bg=THEME["card_inner"], anchor="w")
            lbl_hz.grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(2, 0))

            f_hz_row = tk.Frame(f_form, bg=THEME["card_inner"])
            f_hz_row.grid(row=1, column=1, sticky="ew", pady=(2, 0))
            f_hz_row.columnconfigure(1, weight=1, uniform="hz_col")
            f_hz_row.columnconfigure(3, weight=1, uniform="hz_col")

            tk.Label(f_hz_row, text="1:", font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                     bg=THEME["card_inner"]).grid(row=0, column=0, padx=(0, 2))

            om_hz = tk.OptionMenu(f_hz_row, hz_var, "")
            om_hz.config(bg=THEME["card_bg"], fg=THEME["accent_cyan"], activebackground=THEME["card_inner"],
                         relief="flat", highlightthickness=1, font=(f_font, fs(7), "bold"), anchor="w")
            om_hz.grid(row=0, column=1, sticky="ew", padx=(0, 8))
            self.add_tooltip(om_hz, lambda t=title: _t("smart_tier_hz_tip", "{title} devreye girdiğinde 1. monitörün çalışacağı yenileme hızı (Hz)").format(title=t))

            tk.Label(f_hz_row, text="2:", font=(f_font, fs(7), "bold"), fg=THEME["text_muted"],
                     bg=THEME["card_inner"]).grid(row=0, column=2, padx=(0, 2))

            om_hz2 = tk.OptionMenu(f_hz_row, hz2_var, "")
            om_hz2.config(bg=THEME["card_bg"], fg=THEME["accent_amber"], activebackground=THEME["card_inner"],
                          relief="flat", highlightthickness=1, font=(f_font, fs(7), "bold"), anchor="w")
            om_hz2.grid(row=0, column=3, sticky="ew")
            self.add_tooltip(om_hz2, lambda t=title: _t("smart_tier_hz2_tip", "{title} devreye girdiğinde 2. monitörün çalışacağı yenileme hızı (Hz)").format(title=t))

            return f_box, om_plan, om_hz, om_hz2

        f_t1, self.om_t1_plan, self.om_t1_hz, self.om_t1_hz2 = _build_tier_card(
            f_grid, 1, _t("smart_t1_title", "🌱 KADEME 1: BOŞTA / ULTRA TASARRUF"), THEME["accent_green"],
            self.smart_t1_guid_var, self.smart_t1_hz_var, self.smart_t1_hz2_var,
            _t("smart_t1_sub", "Sistem dinlenirken (GPU < Eşik 2 & CPU < Eşik 2). Minimum güç tüketimi.")
        )
        f_t1.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))

        f_t2, self.om_t2_plan, self.om_t2_hz, self.om_t2_hz2 = _build_tier_card(
            f_grid, 2, t2_title, THEME["accent_cyan"],
            self.smart_t2_guid_var, self.smart_t2_hz_var, self.smart_t2_hz2_var,
            t2_sub
        )
        f_t2.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))

        f_t3, self.om_t3_plan, self.om_t3_hz, self.om_t3_hz2 = _build_tier_card(
            f_grid, 3, t3_title, THEME["accent_amber"],
            self.smart_t3_guid_var, self.smart_t3_hz_var, self.smart_t3_hz2_var,
            t3_sub
        )
        f_t3.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))

        f_t4, self.om_t4_plan, self.om_t4_hz, self.om_t4_hz2 = _build_tier_card(
            f_grid, 4, _t("smart_t4_title", "🎮 KADEME 4: MAKSİMUM / OYUN & RENDER"), THEME["accent_rose"],
            self.smart_t4_guid_var, self.smart_t4_hz_var, self.smart_t4_hz2_var,
            _t("smart_t4_sub", "Ağır yük, render, RTSS 3D oyun veya yüksek priz watt çekişi (≥ Eşik 4).")
        )
        f_t4.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

        self._smart_tier_cards = {1: f_t1, 2: f_t2, 3: f_t3, 4: f_t4}
        self._smart_grid = f_grid

        tk.Label(card_tiers,
                 text=_t("smart_hz_all_monitors_note", "* Kademe Hz hedefi tüm bağlı monitörlere uygulanır; hedefi desteklemeyen monitör atlanır."),
                 font=(f_font, fs(6), "italic"), fg=THEME["text_muted"], bg=THEME["card_bg"],
                 anchor="w", justify="left").pack(fill="x", padx=12, pady=(0, 4))

        # 3. Kullanıcı Tanımlı Eşik ve Hızlı Tetikleyici Ayarları
        card_thresh = self.create_card(f_scroll_box, pady=(0, 4))
        self.make_card_title(card_thresh, _t("smart_thresh_card_title", "KULLANICI TANIMLI GPU/CPU GEÇİŞ EŞİKLERİ VE HIZLI TETİKLEYİCİLER"), THEME["accent_amber"])

        f_cfg_box = tk.Frame(card_thresh, bg=THEME["card_bg"])
        f_cfg_box.pack(fill="x", padx=12, pady=(4, 6))

        # GPU ve CPU Eşikleri Tablosu (3 Sütunlu Grid)
        f_tbl = tk.Frame(f_cfg_box, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_tbl.pack(fill="x", pady=(0, 6))

        f_tbl_head = tk.Frame(f_tbl, bg=THEME["card_inner"])
        f_tbl_head.pack(fill="x", padx=10, pady=(4, 2))
        tk.Label(f_tbl_head, text=_t("smart_lbl_load_thresholds", "GEÇİŞ YÜK EŞİKLERİ (GPU & CPU):"),
                 font=(f_font, fs(7), "bold"), fg=THEME["accent_cyan"], bg=THEME["card_inner"]).pack(side="left")

        f_cols = tk.Frame(f_tbl, bg=THEME["card_inner"])
        f_cols.pack(fill="x", padx=6, pady=(0, 6))
        f_cols.columnconfigure(0, weight=1)
        f_cols.columnconfigure(1, weight=1)
        f_cols.columnconfigure(2, weight=1)

        def _make_tier_thresh_col(parent, col_idx, tier_title, tier_color, gpu_var, cpu_var):
            c_box = tk.Frame(parent, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
            c_box.grid(row=0, column=col_idx, sticky="nsew", padx=3, pady=2)

            h_row = tk.Frame(c_box, bg=THEME["card_bg"])
            h_row.pack(fill="x", padx=6, pady=(3, 2))
            tk.Label(h_row, text=tier_title, font=(f_font, fs(7), "bold"), fg=tier_color, bg=THEME["card_bg"]).pack(side="left")

            f_inputs = tk.Frame(c_box, bg=THEME["card_bg"])
            f_inputs.pack(fill="x", padx=6, pady=(0, 4))

            tk.Label(f_inputs, text="GPU:", font=(f_font, fs(7), "bold"), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")
            e_gpu = tk.Entry(f_inputs, textvariable=gpu_var, font=(f_font, fs(8), "bold"), width=4, justify="center",
                             bg=THEME["card_inner"], fg=THEME["accent_cyan"], insertbackground="#FFFFFF", relief="flat", highlightthickness=1)
            e_gpu.pack(side="left", padx=(2, 1))
            self.add_tooltip(e_gpu, lambda t=tier_title: _t("smart_thresh_field_tip", "{label} tetikleme eşiği ({unit})").format(label=f"{t} GPU", unit="%"))
            tk.Label(f_inputs, text="%", font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["card_bg"]).pack(side="left", padx=(0, 8))

            tk.Label(f_inputs, text="CPU:", font=(f_font, fs(7), "bold"), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")
            e_cpu = tk.Entry(f_inputs, textvariable=cpu_var, font=(f_font, fs(8), "bold"), width=4, justify="center",
                             bg=THEME["card_inner"], fg=THEME["accent_cyan"], insertbackground="#FFFFFF", relief="flat", highlightthickness=1)
            e_cpu.pack(side="left", padx=(2, 1))
            self.add_tooltip(e_cpu, lambda t=tier_title: _t("smart_thresh_field_tip", "{label} tetikleme eşiği ({unit})").format(label=f"{t} CPU", unit="%"))
            tk.Label(f_inputs, text="%", font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["card_bg"]).pack(side="left")

            return c_box

        th_box2 = _make_tier_thresh_col(f_cols, 0, _t("smart_t2_title_short", "🌿 Kademe 2 (Düşük/Medya)"), THEME["accent_cyan"], self.smart_t2_gpu_var, self.smart_t2_cpu_var)
        th_box3 = _make_tier_thresh_col(f_cols, 1, _t("smart_t3_title_short", "⚖️ Kademe 3 (Orta/İş)"), THEME["accent_amber"], self.smart_t3_gpu_var, self.smart_t3_cpu_var)
        th_box4 = _make_tier_thresh_col(f_cols, 2, _t("smart_t4_title_short", "🎮 Kademe 4 (Maksimum/Oyun)"), THEME["accent_rose"], self.smart_t4_gpu_var, self.smart_t4_cpu_var)

        self._smart_thresh_boxes = {2: th_box2, 3: th_box3, 4: th_box4}
        self._smart_thresh_grid = f_cols

        # Hızlı Tetikleyiciler & Debounce
        f_trig_row = tk.Frame(f_cfg_box, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_trig_row.pack(fill="x", pady=(0, 6))

        # Üst Satır: Hızlı Tetikleyiciler (RTSS ve Priz Gücü)
        f_trig_top = tk.Frame(f_trig_row, bg=THEME["card_inner"])
        f_trig_top.pack(fill="x", padx=8, pady=(4, 3))
        f_trig_top.columnconfigure(0, weight=1)
        f_trig_top.columnconfigure(1, weight=1)

        f_rtss_box = tk.Frame(f_trig_top, bg=THEME["card_inner"])
        f_rtss_box.grid(row=0, column=0, sticky="w")
        top_rank = max(2, min(4, int(getattr(self.smart_switcher, 'tier_count', 4))))
        self.make_check(
            f_rtss_box, _t("smart_chk_rtss_game", "🎮 RTSS 3D Oyun Algılandığında Doğrudan En Üst Kademeye (Kademe {top}) Geç").format(top=top_rank),
            self.smart_use_rtss_var, self.on_smart_trigger_toggled,
            fg=THEME["text_primary"], bg=THEME["card_inner"],
            tooltip=_t("smart_chk_rtss_game_tip", "Bir 3D oyun veya tam ekran grafik uygulaması başladığında yükü beklemeden doğrudan en üst kademeye (Kademe {top}) geçer").format(top=top_rank)
        ).pack(side="left")

        f_watt_box = tk.Frame(f_trig_top, bg=THEME["card_inner"])
        f_watt_box.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.make_check(
            f_watt_box, _t("smart_lbl_wall_power_prefix", "⚡ Priz Gücü >"),
            self.smart_use_watt_var, self.on_smart_trigger_toggled,
            fg=THEME["text_primary"], bg=THEME["card_inner"],
            tooltip=_t("smart_chk_wall_watt_tip", "Akıllı priz veya PSU toplam çekişi bu Watt değerini aşınca doğrudan en üst kademeye (Kademe {top}) geçer").format(top=top_rank)
        ).pack(side="left")
        ent_watt = tk.Entry(f_watt_box, textvariable=self.smart_watt_thresh_var, font=(f_font, fs(8), "bold"), width=5, justify="center",
                            bg=THEME["card_bg"], fg=THEME["accent_amber"], insertbackground="#FFFFFF", relief="flat", highlightthickness=1)
        ent_watt.pack(side="left", padx=4)
        self.add_tooltip(ent_watt, _t("smart_ent_watt_tip", "Watt tetikleme eşiği (Toplam sistem çekişi bu gücü aşarsa en üst kademe, yani Kademe {top} devreye girer)").format(top=top_rank))
        tk.Label(f_watt_box, text=_t("smart_lbl_wall_power_suffix", "Watt ise En Üst Kademeye (Kademe {top}) Geç").format(top=top_rank),
                 font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["card_inner"]).pack(side="left")

        # Alt Satır: Kararlılık Gecikmeleri & Kaydet Butonu
        f_deb_row = tk.Frame(f_trig_row, bg=THEME["card_inner"])
        f_deb_row.pack(fill="x", padx=8, pady=(3, 6))

        f_deb_left = tk.Frame(f_deb_row, bg=THEME["card_inner"])
        f_deb_left.pack(side="left")

        tk.Label(f_deb_left, text=_t("smart_lbl_delays", "⏱️ GECİKMELER:"), font=(f_font, fs(7), "bold"), fg=THEME["accent_amber"], bg=THEME["card_inner"]).pack(side="left", padx=(0, 6))

        tk.Label(f_deb_left, text=_t("smart_lbl_delay_up", "Yükselme:"), font=(f_font, fs(7), "bold"), fg=THEME["text_secondary"], bg=THEME["card_inner"]).pack(side="left")
        ent_up = tk.Entry(f_deb_left, textvariable=self.smart_trig_sec_var, font=(f_font, fs(8), "bold"), width=4, justify="center",
                          bg=THEME["card_bg"], fg=THEME["accent_cyan"], insertbackground="#FFFFFF", relief="flat", highlightthickness=1)
        ent_up.pack(side="left", padx=3)
        self.add_tooltip(ent_up, _t("smart_delay_up_tip", "Yükselme tetikleme gecikmesi (sn)"))
        tk.Label(f_deb_left, text=_t("zalman_unit_sec", "sn"), font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["card_inner"]).pack(side="left", padx=(0, 10))

        tk.Label(f_deb_left, text=_t("smart_lbl_delay_down", "Düşme / İade:"), font=(f_font, fs(7), "bold"), fg=THEME["text_secondary"], bg=THEME["card_inner"]).pack(side="left")
        ent_down = tk.Entry(f_deb_left, textvariable=self.smart_rev_sec_var, font=(f_font, fs(8), "bold"), width=4, justify="center",
                            bg=THEME["card_bg"], fg=THEME["accent_cyan"], insertbackground="#FFFFFF", relief="flat", highlightthickness=1)
        ent_down.pack(side="left", padx=3)
        self.add_tooltip(ent_down, _t("smart_delay_down_tip", "Düşme / geri dönüş gecikmesi (sn)"))
        tk.Label(f_deb_left, text=_t("zalman_unit_sec", "sn"), font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["card_inner"]).pack(side="left", padx=(0, 8))

        self.make_btn(
            f_deb_row, _t("smart_btn_save_thresh", "💾 Eşikleri Kaydet ve Uygula"),
            self.save_smart_thresholds,
            fg=THEME["accent_green"], bg=THEME["card_bg"], padx=10, pady=3,
            tooltip=_t("smart_btn_save_thresh_tip", "Yukarıda ayarlanan tüm GPU, CPU, Watt ve gecikme eşiklerini kalıcı olarak kaydeder ve otomasyona uygular")
        ).pack(side="right")

        self.make_btn(
            f_deb_row, _t("smart_btn_reset_defaults", "🔄 Varsayılanlara Sıfırla"),
            self.reset_smart_switch_to_defaults,
            fg=THEME["accent_amber"], bg=THEME["card_bg"], padx=8, pady=3,
            tooltip=_t("smart_btn_reset_defaults_tip", "Tüm akıllı geçiş eşiklerini, gecikmeleri ve tetikleyicileri fabrika varsayılanlarına sıfırlar")
        ).pack(side="right", padx=(0, 6))

        self.lbl_smart_feedback = tk.Label(card_thresh, text="", font=(f_font, fs(7), "bold"), fg=THEME["accent_green"], bg=THEME["card_bg"])
        self.lbl_smart_feedback.pack(anchor="w", padx=14, pady=(0, 4))

        self._apply_smart_tier_layout()
        self.update_smart_switch_options()

    def _smart_threshold_tooltip(self):
        """Canlı şeridin tooltip'i: hangi eşikte hangi kademeye geçileceğini yazar."""
        sw = getattr(self, 'smart_switcher', None)
        if sw is None:
            return ""
        parts = []
        for r in range(2, int(getattr(sw, 'tier_count', 4)) + 1):
            parts.append(_t("smart_thresh_line", "Kademe {n}: GPU ≥ %{gpu} veya CPU ≥ %{cpu}").format(
                n=r, gpu=int(sw._tier_gpu_thr(r)), cpu=int(sw._tier_cpu_thr(r))))
        parts.append(_t("smart_thresh_watt_line", "Priz ≥ {watt} W → en üst kademe").format(watt=int(sw.watt_threshold)))
        return "   •   ".join(parts)

    def update_smart_live(self):
        """Sekmedeki canlı şeridi (CPU/GPU yükü + monitör Hz) günceller."""
        lbl = getattr(self, 'lbl_smart_live', None)
        if lbl is None or not lbl.winfo_exists():
            return

        hw = getattr(self, '_last_hw', {}) or {}
        cpu = int(hw.get('cpu_uti', 0) or 0)
        gpu = int(hw.get('gpu_uti', 0) or 0)

        from power_manager import DisplayManagerService
        try:
            monitors = DisplayManagerService.get_monitors()
        except Exception:
            monitors = []

        mon_parts = []
        for idx, mon in enumerate(monitors, start=1):
            mon_parts.append(f"{idx}: {mon.get('name', '?')[:24]} {mon.get('current_hz', 0)} Hz")
        mon_txt = "  ·  ".join(mon_parts) if mon_parts else _t("smart_live_no_monitor", "monitör yok")

        hz_enabled = bool(getattr(self.smart_switcher, 'hz_enabled', False)) if getattr(self, 'smart_switcher', None) else False

        # Kademe kararı: mevcut kademe ve (varsa) bekleyen hedef kademe
        sw = getattr(self, 'smart_switcher', None)
        tier_txt = ""
        if sw is not None and getattr(sw, 'enabled', False):
            cur_rank = sw._tier_rank(getattr(sw, 'current_tier', 'tier1'))
            tgt_rank = sw._tier_rank(getattr(sw, 'last_target_tier', f'tier{cur_rank}'))
            if tgt_rank != cur_rank:
                tier_txt = _t("smart_live_tier_pending", "🎯 Kademe {cur} → {tgt} (GPU %{gpu} · CPU %{cpu})").format(
                    cur=cur_rank, tgt=tgt_rank, gpu=gpu, cpu=cpu)
            else:
                tier_txt = _t("smart_live_tier_same", "🎯 Kademe {cur}").format(cur=cur_rank)
        else:
            tier_txt = _t("smart_live_tier_off", "🎯 Otomasyon kapalı")

        text = _t("smart_live_line2", "⚡ CPU %{cpu} · GPU %{gpu}   |   {tier}   |   🖥️ {mons}   |   Hz: {hz_state}").format(
            cpu=cpu, gpu=gpu, tier=tier_txt, mons=mon_txt,
            hz_state=_t("smart_live_on", "Açık") if hz_enabled else _t("smart_live_off", "Kapalı")
        )

        if lbl.cget("text") != text:
            lbl.config(text=text)

    def _apply_smart_tier_layout(self):
        """Kademe sayısına göre kartları ve eşik sütunlarını yerleştirir (2/3/4)."""
        try:
            count = max(2, min(4, int(getattr(self.smart_switcher, 'tier_count', 4))))
        except (TypeError, ValueError):
            count = 4

        cards = getattr(self, '_smart_tier_cards', {})
        grid = getattr(self, '_smart_grid', None)
        if cards and grid is not None:
            for frame in cards.values():
                frame.grid_forget()
            for idx in range(1, count + 1):
                row, col = divmod(idx - 1, 2)
                cards[idx].grid(
                    row=row, column=col, sticky="nsew",
                    padx=(0, 4) if col == 0 else (4, 0),
                    pady=(0, 4) if row == 0 else (4, 0)
                )
            # Kullanılmayan satırı tamamen daralt (uniform eşitlemesi boşluk bırakmasın)
            rows_needed = (count + 1) // 2
            for r in range(2):
                if r < rows_needed:
                    grid.rowconfigure(r, weight=1, uniform="tier_row")
                else:
                    grid.rowconfigure(r, weight=0, uniform="")

        boxes = getattr(self, '_smart_thresh_boxes', {})
        tgrid = getattr(self, '_smart_thresh_grid', None)
        if boxes and tgrid is not None:
            for box in boxes.values():
                box.grid_forget()
            col = 0
            for idx in range(2, count + 1):
                boxes[idx].grid(row=0, column=col, sticky="nsew", padx=3, pady=2)
                col += 1
            used = max(1, count - 1)
            for c in range(3):
                tgrid.columnconfigure(c, weight=1 if c < used else 0)

    def on_smart_tier_count_changed(self):
        """2 / 3 / 4 kademe seçimini uygular ve sekmeyi yeniden çizer."""
        try:
            count = int(self.smart_tier_count_var.get())
        except (TypeError, ValueError):
            count = 4
        count = max(2, min(4, count))

        self.smart_switcher.set_tier_count(count)
        self.config["smart_switch_tier_count"] = count
        self.save_config()

        self.build_tab_smart()

        if hasattr(self, 'lbl_smart_feedback') and self.lbl_smart_feedback.winfo_exists():
            self.lbl_smart_feedback.config(
                text=_t("smart_feedback_tier_count", "✓ Kademe sayısı {n} olarak ayarlandı.").format(n=count),
                fg=THEME["accent_green"]
            )
            self.root.after(4000, lambda: self.lbl_smart_feedback.config(text="") if hasattr(self, 'lbl_smart_feedback') and self.lbl_smart_feedback.winfo_exists() else None)

    def test_refresh_rate(self):
        """Aktif kademenin 1. ve 2. monitör Hz hedeflerini uygular ve doğrular."""
        from power_manager import DisplayManagerService

        tier = getattr(self.smart_switcher, "current_tier", "tier1")
        rank = self.smart_switcher._tier_rank(tier)
        hz1 = int(getattr(self.smart_switcher, f"tier{rank}_hz", 0) or 0)
        hz2 = int(getattr(self.smart_switcher, f"tier{rank}_hz2", 0) or 0)

        # Aktif kademede hedef yoksa, tanımlı ilk pozitif hedefi dene
        if hz1 <= 0 and hz2 <= 0:
            for r in range(int(getattr(self.smart_switcher, 'tier_count', 4)), 0, -1):
                c1 = int(getattr(self.smart_switcher, f"tier{r}_hz", 0) or 0)
                c2 = int(getattr(self.smart_switcher, f"tier{r}_hz2", 0) or 0)
                if c1 > 0 or c2 > 0:
                    rank, hz1, hz2 = r, c1, c2
                    break

        if hz1 <= 0 and hz2 <= 0:
            if hasattr(self, 'lbl_smart_feedback') and self.lbl_smart_feedback.winfo_exists():
                self.lbl_smart_feedback.config(
                    text=_t("smart_hz_test_no_target", "⚠ Hiçbir kademede Hz hedefi seçili değil. Önce bir kademeye Hz atayın."),
                    fg=THEME["accent_amber"]
                )
            return

        monitors = DisplayManagerService.get_monitors()
        results = []
        detail_parts = []

        for idx, mon in enumerate(monitors[:2], start=1):
            want = hz1 if idx == 1 else hz2
            if want <= 0:
                continue
            dev = mon.get("device_name")
            rates = DisplayManagerService.get_supported_rates_for(dev)
            skipped = want not in rates
            if not skipped:
                DisplayManagerService.set_refresh_rate_for(dev, want)
            actual = DisplayManagerService.get_current_refresh_rate_for(dev)
            ok = (not skipped) and int(actual) == int(want)
            results.append({"device_name": dev, "name": mon.get("name", ""), "target": want,
                            "ok": ok, "skipped": skipped, "actual": actual})

            mon_label = f"{idx}. {mon.get('name') or dev}"
            if skipped:
                detail_parts.append(_t("smart_hz_res_skip", "{name}: {hz} Hz desteklenmiyor").format(name=mon_label, hz=want))
            elif ok:
                detail_parts.append(f"{mon_label}: {want} Hz ✓")
            else:
                detail_parts.append(_t("smart_hz_res_fail", "{name}: {hz} Hz ✕ (şu an {actual} Hz)").format(
                    name=mon_label, hz=want, actual=actual))

        applied = [r for r in results if not r.get("skipped")]
        ok_all = bool(applied) and all(r.get("ok") for r in applied)

        if hasattr(self, 'lbl_smart_feedback') and self.lbl_smart_feedback.winfo_exists():
            head = _t("smart_hz_test_head2", "Kademe {n} Hz testi: ").format(n=rank)
            mark = "✓ " if ok_all else "✕ "
            self.lbl_smart_feedback.config(
                text=mark + head + "  ·  ".join(detail_parts),
                fg=THEME["accent_green"] if ok_all else THEME["accent_rose"],
                wraplength=int(900 * UI_SCALE), justify="left"
            )
            self.root.after(7000, lambda: self.lbl_smart_feedback.config(text="") if hasattr(self, 'lbl_smart_feedback') and self.lbl_smart_feedback.winfo_exists() else None)

        self.update_smart_live()
        return results, rank

    def on_smart_hz_toggled(self):
        """Monitör Hz otomasyonunu açar/kapatır; açılınca aktif kademenin Hz'ini hemen uygular."""
        enabled = self.smart_hz_auto_var.get()
        self.smart_switcher.hz_enabled = enabled
        self.config["smart_switch_hz_enabled"] = enabled
        self.save_config()

        if enabled:
            try:
                self.smart_switcher.apply_current_hz()
            except Exception:
                pass

        if hasattr(self, 'update_smart_live'):
            self.update_smart_live()

    def on_smart_switch_toggled(self):
        enabled = self.smart_switch_var.get()
        self.smart_switcher.enabled = enabled
        self.config["smart_switch_enabled"] = enabled
        self.save_config()

        # Açılır açılmaz mevcut kademenin planı ve Hz'i uygulanır
        if enabled:
            try:
                self.smart_switcher.force_apply_current()
            except Exception:
                pass
        if hasattr(self, 'lbl_smart_status') and self.lbl_smart_status.winfo_exists():
            if enabled:
                self.lbl_smart_status.config(text=_t("smart_status_idle_listening", "● Akıllı Otomasyon Aktif (Sensörler Dinleniyor)"), fg=THEME["accent_green"])
            else:
                self.lbl_smart_status.config(text=_t("smart_status_disabled_manual", "● Durum: Devre Dışı (Manuel Yönetim)"), fg=THEME["text_muted"])

    def on_smart_trigger_toggled(self):
        self.smart_switcher.use_rtss_trigger = self.smart_use_rtss_var.get()
        self.smart_switcher.use_watt_trigger = self.smart_use_watt_var.get()
        self.config["smart_switch_use_rtss"] = self.smart_switcher.use_rtss_trigger
        self.config["smart_switch_use_watt"] = self.smart_switcher.use_watt_trigger
        self.save_config()

    def on_smart_feedback_toggled(self):
        self.config["smart_switch_sound"] = self.smart_switch_sound_var.get()
        self.config["smart_switch_toast"] = self.smart_switch_toast_var.get()
        self.save_config()

    def reset_smart_switch_to_defaults(self):
        """Akıllı geçişteki tüm eşikleri, gecikmeleri ve tetikleyicileri fabrika varsayılanlarına döndürür."""
        try:
            def_t2_gpu = 15.0
            def_t2_cpu = 20.0
            def_t3_gpu = 40.0
            def_t3_cpu = 45.0
            def_t4_gpu = 70.0
            def_t4_cpu = 75.0
            def_watt_th = 260.0
            def_trig_s = 2
            def_rev_s = 5
            def_use_rtss = True
            def_use_watt = True
            def_sound = True
            def_toast = True

            self.smart_t2_gpu_var.set(f"{def_t2_gpu:.1f}")
            self.smart_t2_cpu_var.set(f"{def_t2_cpu:.1f}")
            self.smart_t3_gpu_var.set(f"{def_t3_gpu:.1f}")
            self.smart_t3_cpu_var.set(f"{def_t3_cpu:.1f}")
            self.smart_t4_gpu_var.set(f"{def_t4_gpu:.1f}")
            self.smart_t4_cpu_var.set(f"{def_t4_cpu:.1f}")
            self.smart_watt_thresh_var.set(f"{def_watt_th:.1f}")
            self.smart_trig_sec_var.set(str(def_trig_s))
            self.smart_rev_sec_var.set(str(def_rev_s))

            self.smart_use_rtss_var.set(def_use_rtss)
            self.smart_use_watt_var.set(def_use_watt)
            self.smart_switch_sound_var.set(def_sound)
            self.smart_switch_toast_var.set(def_toast)

            self.smart_switcher.tier2_gpu_pct = def_t2_gpu
            self.smart_switcher.tier2_cpu_pct = def_t2_cpu
            self.smart_switcher.tier3_gpu_pct = def_t3_gpu
            self.smart_switcher.tier3_cpu_pct = def_t3_cpu
            self.smart_switcher.tier4_gpu_pct = def_t4_gpu
            self.smart_switcher.tier4_cpu_pct = def_t4_cpu
            self.smart_switcher.watt_threshold = def_watt_th
            self.smart_switcher.trigger_seconds = def_trig_s
            self.smart_switcher.revert_seconds = def_rev_s
            self.smart_switcher.use_rtss_trigger = def_use_rtss
            self.smart_switcher.use_watt_trigger = def_use_watt

            self.config["smart_switch_t2_gpu"] = def_t2_gpu
            self.config["smart_switch_t2_cpu"] = def_t2_cpu
            self.config["smart_switch_t3_gpu"] = def_t3_gpu
            self.config["smart_switch_t3_cpu"] = def_t3_cpu
            self.config["smart_switch_t4_gpu"] = def_t4_gpu
            self.config["smart_switch_t4_cpu"] = def_t4_cpu
            self.config["smart_switch_watt_threshold"] = def_watt_th
            self.config["smart_switch_trigger_sec"] = def_trig_s
            self.config["smart_switch_revert_sec"] = def_rev_s
            self.config["smart_switch_use_rtss"] = def_use_rtss
            self.config["smart_switch_use_watt"] = def_use_watt
            self.config["smart_switch_sound"] = def_sound
            self.config["smart_switch_toast"] = def_toast
            self.save_config()

            if hasattr(self, 'lbl_smart_feedback') and self.lbl_smart_feedback.winfo_exists():
                self.lbl_smart_feedback.config(text=_t("smart_feedback_reset", "✓ Tüm akıllı geçiş eşikleri ve ayarları fabrika varsayılanlarına döndürüldü."), fg=THEME["accent_green"])
                self.root.after(4000, lambda: self.lbl_smart_feedback.config(text="") if hasattr(self, 'lbl_smart_feedback') and self.lbl_smart_feedback.winfo_exists() else None)
        except Exception as e:
            if hasattr(self, 'lbl_smart_feedback') and self.lbl_smart_feedback.winfo_exists():
                self.lbl_smart_feedback.config(text=_t("smart_feedback_error", "✕ Hata: Sayısal değerleri kontrol edin ({e})").format(e=e), fg=THEME["accent_rose"])

    def save_smart_thresholds(self):
        try:
            t2_gpu = float(self.smart_t2_gpu_var.get())
            t2_cpu = float(self.smart_t2_cpu_var.get())
            t3_gpu = float(self.smart_t3_gpu_var.get())
            t3_cpu = float(self.smart_t3_cpu_var.get())
            t4_gpu = float(self.smart_t4_gpu_var.get())
            t4_cpu = float(self.smart_t4_cpu_var.get())
            watt_th = float(self.smart_watt_thresh_var.get())
            trig_s = max(1, int(self.smart_trig_sec_var.get()))
            rev_s = max(1, int(self.smart_rev_sec_var.get()))

            self.smart_switcher.tier2_gpu_pct = t2_gpu
            self.smart_switcher.tier2_cpu_pct = t2_cpu
            self.smart_switcher.tier3_gpu_pct = t3_gpu
            self.smart_switcher.tier3_cpu_pct = t3_cpu
            self.smart_switcher.tier4_gpu_pct = t4_gpu
            self.smart_switcher.tier4_cpu_pct = t4_cpu
            self.smart_switcher.watt_threshold = watt_th
            self.smart_switcher.trigger_seconds = trig_s
            self.smart_switcher.revert_seconds = rev_s

            self.config["smart_switch_t2_gpu"] = t2_gpu
            self.config["smart_switch_t2_cpu"] = t2_cpu
            self.config["smart_switch_t3_gpu"] = t3_gpu
            self.config["smart_switch_t3_cpu"] = t3_cpu
            self.config["smart_switch_t4_gpu"] = t4_gpu
            self.config["smart_switch_t4_cpu"] = t4_cpu
            self.config["smart_switch_watt_threshold"] = watt_th
            self.config["smart_switch_trigger_sec"] = trig_s
            self.config["smart_switch_revert_sec"] = rev_s
            self.save_config()

            if hasattr(self, 'lbl_smart_feedback') and self.lbl_smart_feedback.winfo_exists():
                self.lbl_smart_feedback.config(text=_t("smart_feedback_saved", "✓ Tüm eşik değerleri ve gecikmeler başarıyla kaydedildi."), fg=THEME["accent_green"])
                self.root.after(3000, lambda: self.lbl_smart_feedback.config(text="") if hasattr(self, 'lbl_smart_feedback') and self.lbl_smart_feedback.winfo_exists() else None)
        except Exception as e:
            if hasattr(self, 'lbl_smart_feedback') and self.lbl_smart_feedback.winfo_exists():
                self.lbl_smart_feedback.config(text=_t("smart_feedback_error", "✕ Hata: Sayısal değerleri kontrol edin ({e})").format(e=e), fg=THEME["accent_rose"])

    def on_smart_plan_switched(self, tier, guid, target_hz=0, reason="", hz_actual=None, hz_ok=None):
        def _apply():
            tier_info = {
                "tier4": (_t("smart_t4_title", "KADEME 4: OYUN / MAKSİMUM PERFORMANS"), THEME["accent_rose"], "🎮"),
                "tier3": (_t("smart_t3_title", "KADEME 3: ÇOKLU GÖREV / ORTA YÜK"), THEME["accent_amber"], "⚖️"),
                "tier2": (_t("smart_t2_title", "KADEME 2: GÜNLÜK / MEDYA & WEB"), THEME["accent_cyan"], "🌿"),
                "tier1": (_t("smart_t1_title", "KADEME 1: BOŞTA / ULTRA TASARRUF"), THEME["accent_green"], "🌱"),
            }
            t_data = tier_info.get(tier, (f"KADEME {tier}", THEME["accent_cyan"], "⚡"))
            tier_str, col, icon = t_data[0], t_data[1], t_data[2]
            hz_info = ""
            if target_hz and int(target_hz) > 0:
                if hz_ok is None:
                    hz_info = f" · {int(target_hz)} Hz"
                elif hz_ok:
                    hz_info = f" · {int(target_hz)} Hz ✓"
                else:
                    hz_info = f" · {int(target_hz)} Hz ✕ (ekran {hz_actual} Hz)"
            reason_info = f" ({reason})" if reason else ""
            if hasattr(self, 'lbl_smart_status') and self.lbl_smart_status.winfo_exists():
                rank = self.smart_switcher._tier_rank(tier)
                hz_short = f" · {int(target_hz)} Hz" if target_hz and int(target_hz) > 0 else ""
                self.lbl_smart_status.config(
                    text=_t("smart_status_active_short", "● Kademe {n}{hz}").format(n=rank, hz=hz_short),
                    fg=col
                )
            if hasattr(self, 'refresh_power_plans_ui'):
                self.refresh_power_plans_ui()

            plan_name = tier_str
            for p in getattr(self, "power_plans", []):
                if p.guid.lower() == str(guid).lower():
                    plan_name = p.name
                    icon = p.badge_icon
                    break

            # Sesli bildirim çal (Kullanıcı kapatmadıysa)
            if hasattr(self, 'play_notification_sound'):
                self.play_notification_sound(is_smart=True)

            # Toast bildirimi göster (Kullanıcı kapatmadıysa)
            if hasattr(self, 'show_power_plan_toast') and self.config.get("smart_switch_toast", True):
                self.show_power_plan_toast(
                    plan_name=plan_name,
                    icon=icon,
                    subtitle=reason,
                    tier_name=tier_str,
                    hz=target_hz,
                    play_sound=False
                )
            self._last_detected_plan_guid = str(guid).lower()
        try:
            self.root.after(0, _apply)
        except RuntimeError:
            # Tk döngüsü hazır değilse (nadir) doğrudan uygula
            _apply()

    def refresh_smart_tab_ui(self):
        self.build_tab_smart()

    def update_smart_switch_options(self):
        if not hasattr(self, 'om_t1_plan') or not self.om_t1_plan.winfo_exists():
            return

        if not getattr(self, 'power_plans', None):
            self.power_plans = PowerManagerService.get_power_plans()

        plan_map = {}
        for p in self.power_plans:
            plan_map[p.guid] = f"{p.badge_icon} {p.name}"

        menus = [
            (1, self.om_t1_plan, self.smart_t1_guid_var),
            (2, self.om_t2_plan, self.smart_t2_guid_var),
            (3, self.om_t3_plan, self.smart_t3_guid_var),
            (4, self.om_t4_plan, self.smart_t4_guid_var),
        ]

        for t_idx, om, var in menus:
            m = om["menu"]
            m.delete(0, "end")
            m.config(
                bg=THEME["card_bg"], fg=THEME["text_primary"],
                activebackground=THEME["card_inner"], activeforeground=THEME["accent_cyan"],
                font=(THEME["font_family"], fs(7), "bold"), relief="flat", bd=1
            )
            for p in self.power_plans:
                lbl = f"{p.badge_icon} {p.name}"
                m.add_command(label=lbl, command=lambda idx=t_idx, g=p.guid: self._set_smart_tier_plan(idx, g))

        # GUID Doğrulaması ve Kalıcı Kurtarma (Self-Healing)
        valid_guids = {p.guid.lower(): p.guid for p in self.power_plans}
        plan_by_name = {p.name.lower(): p.guid for p in self.power_plans}

        def _resolve_valid_guid(curr_val, fallback_keywords):
            if curr_val and str(curr_val).lower() in valid_guids:
                return valid_guids[str(curr_val).lower()]
            # İsimden kurtarmayı dene
            c_str = str(curr_val).lower()
            for emo in ["🌱", "🌿", "⚖️", "🎮", "⚡", "●"]:
                c_str = c_str.replace(emo, "")
            c_str = c_str.strip()
            if c_str and "seçiniz" not in c_str and "select" not in c_str:
                for p_name, g in plan_by_name.items():
                    if c_str in p_name or p_name in c_str:
                        return g
            # Anahtar kelimelerden otomatik seç
            for p in self.power_plans:
                if any(k in p.name.lower() for k in fallback_keywords):
                    return p.guid
            return self.power_plans[0].guid if self.power_plans else ""

        if self.power_plans:
            self.smart_switcher.tier1_plan_guid = _resolve_valid_guid(self.smart_switcher.tier1_plan_guid, ["eco", "stealth", "tasarruf", "saver"])
            self.config["smart_switch_t1_guid"] = self.smart_switcher.tier1_plan_guid

            self.smart_switcher.tier2_plan_guid = _resolve_valid_guid(self.smart_switcher.tier2_plan_guid, ["smart balanced", "dengeli", "balanced", "ryzen™ dengeli"])
            self.config["smart_switch_t2_guid"] = self.smart_switcher.tier2_plan_guid

            self.smart_switcher.tier3_plan_guid = _resolve_valid_guid(self.smart_switcher.tier3_plan_guid, ["yüksek", "high performance", "ryzen™ yüksek"])
            self.config["smart_switch_t3_guid"] = self.smart_switcher.tier3_plan_guid

            self.smart_switcher.tier4_plan_guid = _resolve_valid_guid(self.smart_switcher.tier4_plan_guid, ["maximum performance", "maksimum performans", "wattcost maximum", "ultimate", "apex", "nihai", "oyun"])

            # Aynı güç planı birden fazla kademeye atanmışsa isimden ayırmaya çalış
            def _dedupe_tier(tier_no, keywords):
                current = getattr(self.smart_switcher, f"tier{tier_no}_plan_guid")
                others = {
                    getattr(self.smart_switcher, f"tier{r}_plan_guid")
                    for r in (1, 2, 3, 4) if r != tier_no
                }
                if current and current not in others:
                    return
                for plan in self.power_plans:
                    name = plan.name.lower()
                    if any(k in name for k in keywords) and plan.guid not in others:
                        setattr(self.smart_switcher, f"tier{tier_no}_plan_guid", plan.guid)
                        self.config[f"smart_switch_t{tier_no}_guid"] = plan.guid
                        return

            _dedupe_tier(4, ["maximum performance", "maksimum performans", "wattcost maximum"])
            _dedupe_tier(3, ["high performance", "yüksek", "ryzen™ yüksek"])
            _dedupe_tier(2, ["balanced", "dengeli"])
            _dedupe_tier(1, ["maximum power saver", "saver", "tasarruf"])
            self.config["smart_switch_t4_guid"] = self.smart_switcher.tier4_plan_guid

        lbl_select = _t("select_option", "Seçiniz...")
        self.smart_t1_guid_var.set(plan_map.get(self.smart_switcher.tier1_plan_guid, lbl_select))
        self.smart_t2_guid_var.set(plan_map.get(self.smart_switcher.tier2_plan_guid, lbl_select))
        self.smart_t3_guid_var.set(plan_map.get(self.smart_switcher.tier3_plan_guid, lbl_select))
        self.smart_t4_guid_var.set(plan_map.get(self.smart_switcher.tier4_plan_guid, lbl_select))
        self.save_config()

        # 1. Monitör Bilgilerini ve Desteklenen Hz Değerlerini Oku & Bilgi Kartını Güncelle
        from power_manager import DisplayManagerService
        monitors = DisplayManagerService.get_monitors()
        mon_info = DisplayManagerService.get_monitor_info()
        if not monitors:
            monitors = [dict(mon_info, is_primary=True)]

        mon_parts = []
        for idx, mon in enumerate(monitors, start=1):
            prim = _t("smart_mon_primary_tag", " (birincil)") if mon.get("is_primary") else ""
            mon_parts.append(
                _t("smart_monitor_line", "{i}. {name} • {res} • {hz} Hz{prim}").format(
                    i=idx, name=mon.get("name", "?"), res=mon.get("resolution", "-"),
                    hz=mon.get("current_hz", 0), prim=prim
                )
            )
        detect_prefix = _t("smart_detected_monitors", "🖥️ Bağlı Monitörler ({n}): ").format(n=len(monitors))

        primary = monitors[0]
        supported_rates = DisplayManagerService.get_supported_rates_for(primary.get("device_name"))
        if not supported_rates:
            supported_rates = [primary.get("current_hz", 60) or 60]

        rates_str = ", ".join(f"{r} Hz" for r in supported_rates)

        if hasattr(self, 'lbl_mon_detect') and self.lbl_mon_detect.winfo_exists():
            self.lbl_mon_detect.config(
                text=detect_prefix + "   |   ".join(mon_parts),
                wraplength=int(560 * UI_SCALE), justify="left"
            )

        if hasattr(self, 'lbl_mon_rates') and self.lbl_mon_rates.winfo_exists():
            tmpl_rates = _t("smart_detected_hz_rates", "✨ {mon} için desteklenen Hz ({count} adet): {rates}")
            self.lbl_mon_rates.config(
                text=tmpl_rates.format(mon=primary.get("name", "?"), count=len(supported_rates), rates=rates_str)
            )

        # 2. Monitör Hz Seçenek Menülerini Doldur (1. ve 2. monitör ayrı ayrı)
        no_change_lbl = _t("smart_hz_no_change_short", "—")
        no_mon2_lbl = _t("smart_hz_no_monitor2", "2. monitör yok")

        second = monitors[1] if len(monitors) > 1 else None
        mon2_rates = DisplayManagerService.get_supported_rates_for(second.get("device_name")) if second else []
        if second is None:
            mon2_rates = []

        f_font = THEME["font_family"]
        hz_menus = [
            (1, 1, getattr(self, 'om_t1_hz', None), getattr(self, 'smart_t1_hz_var', None), getattr(self.smart_switcher, 'tier1_hz', 0), supported_rates),
            (2, 1, getattr(self, 'om_t2_hz', None), getattr(self, 'smart_t2_hz_var', None), getattr(self.smart_switcher, 'tier2_hz', 0), supported_rates),
            (3, 1, getattr(self, 'om_t3_hz', None), getattr(self, 'smart_t3_hz_var', None), getattr(self.smart_switcher, 'tier3_hz', 0), supported_rates),
            (4, 1, getattr(self, 'om_t4_hz', None), getattr(self, 'smart_t4_hz_var', None), getattr(self.smart_switcher, 'tier4_hz', 0), supported_rates),
            (1, 2, getattr(self, 'om_t1_hz2', None), getattr(self, 'smart_t1_hz2_var', None), getattr(self.smart_switcher, 'tier1_hz2', 0), mon2_rates),
            (2, 2, getattr(self, 'om_t2_hz2', None), getattr(self, 'smart_t2_hz2_var', None), getattr(self.smart_switcher, 'tier2_hz2', 0), mon2_rates),
            (3, 2, getattr(self, 'om_t3_hz2', None), getattr(self, 'smart_t3_hz2_var', None), getattr(self.smart_switcher, 'tier3_hz2', 0), mon2_rates),
            (4, 2, getattr(self, 'om_t4_hz2', None), getattr(self, 'smart_t4_hz2_var', None), getattr(self.smart_switcher, 'tier4_hz2', 0), mon2_rates),
        ]

        for t_idx, mon_no, om_hz, var_hz, cur_hz_val, rates in hz_menus:
            if not om_hz or not om_hz.winfo_exists() or var_hz is None:
                continue

            m_hz = om_hz["menu"]
            m_hz.delete(0, "end")
            m_hz.config(
                bg=THEME["card_bg"],
                fg=THEME["text_primary"],
                activebackground=THEME["card_inner"],
                activeforeground=THEME["accent_cyan"],
                font=(f_font, fs(7), "bold"),
                relief="flat",
                bd=1
            )

            if not rates:
                m_hz.add_command(label=no_mon2_lbl, command=lambda: None)
                var_hz.set(no_mon2_lbl)
                continue

            m_hz.add_command(label=f"⚪ {no_change_lbl}",
                             command=lambda idx=t_idx, mn=mon_no: self._set_smart_tier_hz(idx, 0, mn))
            for rate in rates:
                m_hz.add_command(label=f"🖥️ {rate} Hz",
                                 command=lambda idx=t_idx, r=rate, mn=mon_no: self._set_smart_tier_hz(idx, r, mn))

            if cur_hz_val > 0:
                var_hz.set(f"🖥️ {cur_hz_val} Hz")
            else:
                var_hz.set(f"⚪ {no_change_lbl}")

    def _set_smart_tier_hz(self, tier_idx: int, hz: int, monitor: int = 1):
        """Kademenin 1. veya 2. monitör Hz hedefini kaydeder."""
        no_change_lbl = _t("smart_hz_no_change_short", "—")
        disp_txt = f"🖥️ {hz} Hz" if hz > 0 else f"⚪ {no_change_lbl}"

        if tier_idx not in (1, 2, 3, 4):
            return

        if monitor == 2:
            setattr(self.smart_switcher, f"tier{tier_idx}_hz2", hz)
            self.config[f"smart_switch_t{tier_idx}_hz2"] = hz
            var = getattr(self, f"smart_t{tier_idx}_hz2_var", None)
        else:
            setattr(self.smart_switcher, f"tier{tier_idx}_hz", hz)
            self.config[f"smart_switch_t{tier_idx}_hz"] = hz
            var = getattr(self, f"smart_t{tier_idx}_hz_var", None)

        if var is not None:
            var.set(disp_txt)
        self.save_config()

        # Değiştirilen kademe şu an aktifse hemen uygula
        try:
            if self.smart_switcher.enabled and self.smart_switcher._tier_rank(self.smart_switcher.current_tier) == tier_idx:
                self.smart_switcher.force_apply_current()
        except Exception:
            pass

    def _set_smart_tier_plan(self, tier_idx: int, guid: str):
        for p in self.power_plans:
            if p.guid == guid:
                lbl = f"{p.badge_icon} {p.name}"
                if tier_idx == 1:
                    self.smart_switcher.tier1_plan_guid = guid
                    self.config["smart_switch_t1_guid"] = guid
                    self.smart_t1_guid_var.set(lbl)
                elif tier_idx == 2:
                    self.smart_switcher.tier2_plan_guid = guid
                    self.config["smart_switch_t2_guid"] = guid
                    self.smart_t2_guid_var.set(lbl)
                elif tier_idx == 3:
                    self.smart_switcher.tier3_plan_guid = guid
                    self.config["smart_switch_t3_guid"] = guid
                    self.smart_t3_guid_var.set(lbl)
                elif tier_idx == 4:
                    self.smart_switcher.tier4_plan_guid = guid
                    self.config["smart_switch_t4_guid"] = guid
                    self.smart_t4_guid_var.set(lbl)
                self.save_config()
                break

        # Değiştirilen kademe şu an aktifse planı hemen uygula
        try:
            if self.smart_switcher.enabled and self.smart_switcher._tier_rank(self.smart_switcher.current_tier) == tier_idx:
                self.smart_switcher.force_apply_current()
        except Exception:
            pass


