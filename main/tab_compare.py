"""
WattCost HaYTooL - Compare Tab Modülü
Sistemdeki tüm güç planlarının mikro ayarlarını (CPU Min/Max, EPP, Boost, Soğutma, ASPM vb.) yan yana karşılaştırır.
Kullanıcı plan başlığına tıklayarak doğrudan o plana geçebilir;
İstediği satır ve sütundaki hücreye çift tıklayarak ayarları interaktif olarak anında değiştirebilir.
"""
import tkinter as tk
from tkinter import ttk
from config_manager import THEME, UI_SCALE, fs, apply_dark_titlebar
from power_manager import PowerManagerService, PowerPlanItem
from language_manager import _t


class CompareTabMixin:
    """Güç Planları Karşılaştırma ve İnteraktif Düzenleme Matrisi Sekmesi."""

    def build_tab_compare(self):
        container = self.tab_compare
        for w in container.winfo_children():
            w.destroy()

        f_font = THEME["font_family"]
        card_matrix = tk.Frame(container, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
        card_matrix.pack(fill="both", expand=True, padx=12, pady=8)
        def _make_tip(row):
            self.lbl_compare_status = tk.Label(
                row, text=_t("compare_tip", "💡 İpucu: Plan başlığına tıklayarak o plana geçebilir; hücreye çift tıklayarak ayarları düzenleyebilirsiniz."),
                font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["card_bg"]
            )
            self.lbl_compare_status.pack(side="right", padx=(0, 4))

        self.make_card_title(card_matrix, _t("compare_title", "GÜÇ DÜZENLERİ AYAR & PERFORMANS KARŞILAŞTIRMA MATRİSİ"),
                             THEME["accent_cyan"], right_widget_factory=_make_tip)

        f_toolbar = tk.Frame(card_matrix, bg=THEME["card_bg"])
        f_toolbar.pack(fill="x", padx=14, pady=(2, 6))

        self.make_btn(f_toolbar, _t("compare_btn_refresh", "🔄 Yeniden Oku"), self.refresh_compare_matrix_ui,
                      fg=THEME["accent_cyan"], bg=THEME["card_inner"],
                      tooltip=_t("compare_tip_refresh", "Tüm güç planlarının Windows kayıt defteri ayarlarını sıfırdan okuyup tabloyu günceller")).pack(side="left", padx=(0, 6))

        self.make_btn(f_toolbar, _t("btn_unlock_hidden", "🔓 Windows Gizli Ayarları Aç"), self.unlock_hidden_power_settings,
                      fg=THEME["accent_amber"], bg=THEME["card_inner"],
                      tooltip=_t("compare_tip_unlock", "Windows güç seçeneklerinde gizli olan işlemci frekansı, çekirdek park etme ve uyku gibi onlarca gizli ayarın kilidini açar")).pack(side="left", padx=(0, 4))

        self.make_btn(f_toolbar, _t("btn_lock_hidden", "🔒 Gizli Ayarları Kapat"), self.lock_hidden_power_settings,
                      fg=THEME["text_muted"], bg=THEME["card_inner"],
                      tooltip=_t("compare_tip_lock", "Windows güç seçeneklerindeki gelişmiş gizli ayarları tekrar gizler ve sadeleştirir")).pack(side="left", padx=(0, 6))

        self.make_btn(f_toolbar, _t("btn_open_power_cpl", "⚙️ Windows Güç Seçenekleri"), self.open_windows_power_cpl,
                      fg=THEME["text_secondary"], bg=THEME["card_inner"],
                      tooltip=_t("compare_tip_power_cpl", "Klasik Windows Denetim Masası Güç Seçenekleri penceresini açar")).pack(side="left", padx=(0, 4))

        self.make_btn(f_toolbar, _t("btn_open_adv_cpl", "🛠️ Gelişmiş Güç Ayarları"), self.open_windows_advanced_power_cpl,
                      fg=THEME["accent_amber"], bg=THEME["card_inner"],
                      tooltip=_t("compare_tip_adv_cpl", "Aktif güç planının gelişmiş ince ayar penceresini doğrudan açar")).pack(side="left", padx=(0, 8))

        self.make_check(f_toolbar, _t("compare_filter_diff", "Yalnızca Farklı Olan Ayarları Göster (Filtre)"),
                        self.compare_diff_only_var, self.refresh_compare_matrix_ui,
                        fg=THEME["text_primary"], bg=THEME["card_bg"],
                        tooltip=_t("compare_tip_diff_only", "Tüm planlarda aynı değere sahip satırları gizler; sadece planlar arasında farklılık gösteren ayarları listeler")).pack(side="left")

        self.f_matrix_container = tk.Frame(card_matrix, bg=THEME["card_inner"],
                                           highlightbackground=THEME["card_border"], highlightthickness=1)
        self.f_matrix_container.pack(fill="both", expand=True, padx=12, pady=(0, 10))

    def refresh_compare_matrix_ui(self):
        f_font = THEME["font_family"]
        if not hasattr(self, 'f_matrix_container') or not self.f_matrix_container.winfo_exists():
            return

        for child in self.f_matrix_container.winfo_children():
            child.destroy()

        plans = PowerManagerService.get_power_plans()
        if not plans:
            tk.Label(self.f_matrix_container, text="Güç planı bulunamadı.", fg=THEME["text_muted"], bg=THEME["card_inner"]).pack(pady=20)
            return

        settings_list = []
        for p in plans:
            s = PowerManagerService.get_plan_settings(p.guid, p.name)
            settings_list.append((p, s))

        # (Başlık, Değer Alıcı Fonksiyon, Formatlayıcı, Key, Düzenleyici Tipi, Ek Bilgi)
        compare_rows = [
            (_t("row_cpu_min", "En Düşük İşlemci (Min CPU)"), lambda s: s.cpu_min_ac, lambda v: f"%{v}", "cpu_min_ac", "percent", (0, 100)),
            (_t("row_cpu_max", "En Yüksek İşlemci (Max CPU)"), lambda s: s.cpu_max_ac, lambda v: f"%{v}", "cpu_max_ac", "percent", (0, 100)),
            (_t("row_cpu_freq", "Maksimum İşlemci Frekansı"), lambda s: s.cpu_max_freq_ac, lambda v: _t("val_unlimited", "Sınırsız (0)") if v == 0 else f"{v} MHz", "cpu_max_freq_ac", "freq", {}),
            (_t("row_cpu_epp", "İşlemci Enerji Tercihi (EPP)"), lambda s: s.energy_perf_pref_ac, lambda v: f"{v} (0=Max, 100=Saver)", "energy_perf_pref_ac", "epp", (0, 100)),
            (_t("row_cpu_boost", "İşlemci Turbo Boost Modu"), lambda s: s.boost_mode_ac, lambda v: {0: _t("val_disabled", "Kapalı"), 1: _t("val_enabled", "Etkin"), 2: _t("val_aggressive", "Agresif"), 3: _t("val_efficient_enabled", "Verimli Etkin"), 4: _t("val_efficient_aggressive", "Verimli Agresif")}.get(v, str(v)), "boost_mode_ac", "boost", {}),
            (_t("row_cooling", "Sistem Soğutma İlkesi"), lambda s: s.cooling_policy_ac, lambda v: _t("val_cooling_active", "Etkin (Fan Önce)") if v == 1 else _t("val_cooling_passive", "Edilgin (Frekans Düşür)"), "cooling_policy_ac", "cooling", {}),
            (_t("row_core_park_min", "Çekirdek Park Etme Min"), lambda s: s.core_parking_min_ac, lambda v: f"%{v}", "core_parking_min_ac", "percent", (0, 100)),
            (_t("row_core_park_max", "Çekirdek Park Etme Maks"), lambda s: s.core_parking_max_ac, lambda v: f"%{v}", "core_parking_max_ac", "percent", (0, 100)),
            (_t("row_pcie_aspm", "PCIe Güç Tasarrufu (ASPM)"), lambda s: s.pcie_aspm_ac, lambda v: {0: _t("val_aspm_off", "Kapalı (Maks Hız)"), 1: _t("val_aspm_med", "Orta"), 2: _t("val_aspm_max", "Maksimum")}.get(v, str(v)), "pcie_aspm_ac", "aspm", {}),
            (_t("row_usb_suspend", "USB Seçici Askıya Alma"), lambda s: s.usb_suspend_ac, lambda v: _t("val_usb_always_on", "Kapalı (Sürekli Açık)") if v == 0 else _t("val_usb_suspend", "Etkin (Askıya Al)"), "usb_suspend_ac", "usb", {}),
            (_t("row_wifi_saving", "Kablosuz (Wi-Fi) Güç Tasarrufu"), lambda s: s.wifi_power_saving_ac, lambda v: {0: _t("val_max_perf", "En Yüksek Performans"), 1: _t("val_low_saving", "Düşük Tasarruf"), 2: _t("val_med_saving", "Orta Tasarruf"), 3: _t("val_max_saving", "Maksimum Tasarruf")}.get(v, str(v)), "wifi_power_saving_ac", "wifi", {}),
            (_t("row_video_timeout", "Ekranı Kapatma Süresi"), lambda s: s.video_timeout_ac, lambda v: _t("val_never", "Asla") if v == 0 else f"{v} {_t('val_unit_min', 'dk')}", "video_timeout_ac", "minutes", (0, 300)),
            (_t("row_sleep_timeout", "Uykuya Geçiş Süresi"), lambda s: s.sleep_timeout_ac, lambda v: _t("val_never", "Asla") if v == 0 else f"{v} {_t('val_unit_min', 'dk')}", "sleep_timeout_ac", "minutes", (0, 300)),
            (_t("row_hybrid_sleep", "Karma (Hibrit) Uyku"), lambda s: s.hybrid_sleep_ac, lambda v: _t("val_disabled", "Kapalı") if v == 0 else _t("val_enabled", "Etkin / Açık"), "hybrid_sleep_ac", "switch_bool", {}),
            (_t("row_hibernate_timeout", "Hazırda Bekleme Süresi"), lambda s: s.hibernate_timeout_ac, lambda v: _t("val_never", "Asla") if v == 0 else f"{v} {_t('val_unit_min', 'dk')}", "hibernate_timeout_ac", "minutes", (0, 300)),
            (_t("row_wake_timers", "Uyandırma Zamanlayıcıları"), lambda s: s.allow_wake_timers_ac, lambda v: {0: _t("val_disabled", "Devre Dışı"), 1: _t("val_enabled", "Etkin"), 2: _t("val_important_only", "Yalnızca Önemli")}.get(v, str(v)), "allow_wake_timers_ac", "wake_timers", {}),
            (_t("row_power_btn", "Güç Düğmesi Eylemi"), lambda s: s.power_button_ac, lambda v: {0: _t("val_no_action", "Eylem Yok"), 1: _t("val_sleep", "Uyku"), 2: _t("val_hibernate", "Hazırda Beklet"), 3: _t("val_shutdown", "Kapat"), 4: _t("val_turn_off_display", "Ekranı Kapat")}.get(v, str(v)), "power_button_ac", "btn_action", {}),
            (_t("row_sleep_btn", "Uyku Düğmesi Eylemi"), lambda s: s.sleep_button_ac, lambda v: {0: _t("val_no_action", "Eylem Yok"), 1: _t("val_sleep", "Uyku"), 2: _t("val_hibernate", "Hazırda Beklet"), 3: _t("val_shutdown", "Kapat"), 4: _t("val_turn_off_display", "Ekranı Kapat")}.get(v, str(v)), "sleep_button_ac", "btn_action", {}),
            (_t("row_disk_timeout", "Sabit Diski Kapatma"), lambda s: s.disk_timeout_ac, lambda v: _t("val_never", "Asla") if v == 0 else f"{v} {_t('val_unit_min', 'dk')}", "disk_timeout_ac", "minutes", (0, 300)),
        ]

        diff_only = self.compare_diff_only_var.get()

        canvas = tk.Canvas(self.f_matrix_container, bg=THEME["card_inner"], highlightthickness=0)
        scrollable_frame = tk.Frame(canvas, bg=THEME["card_inner"])

        canvas.pack(fill="both", expand=True, padx=2, pady=2)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def _on_mousewheel(event):
            try:
                # Shift basılıysa veya yatay tekerlekse yatay, değilse dikey kaydır
                if event.state & 0x0001:
                    canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
                else:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        def _bind_mw(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_mw(child)

        hdr_frame = tk.Frame(scrollable_frame, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
        hdr_frame.pack(fill="x", pady=(2, 4))

        w_col = int(145 * UI_SCALE)
        w_lbl = int(24 * UI_SCALE)

        tk.Label(hdr_frame, text="PARAMETRE / AYAR ADI", font=(f_font, fs(7), "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"], width=w_lbl, anchor="w", padx=8, pady=6).pack(side="left")

        # Sütun Başlıkları: Güç Planları ve Tek Tıkla Geçiş Butonları
        for plan, _ in settings_list:
            col_hdr = tk.Frame(hdr_frame, bg="#131B2E" if plan.is_active else THEME["card_bg"],
                               highlightbackground=THEME["accent_green"] if plan.is_active else THEME["card_border"],
                               highlightthickness=1, width=w_col, height=int(56 * UI_SCALE))
            col_hdr.pack(side="left", fill="y", padx=2, pady=2)
            col_hdr.pack_propagate(False)

            p_text = f"{plan.badge_icon} {plan.name}"
            lbl_title = tk.Label(col_hdr, text=p_text, font=(f_font, fs(7), "bold"),
                                 fg=THEME["accent_green"] if plan.is_active else THEME["text_primary"],
                                 bg=col_hdr["bg"], anchor="center", cursor="hand2",
                                 wraplength=int(138 * UI_SCALE), justify="center")
            lbl_title.pack(fill="x", padx=2, pady=(3, 1))
            self.add_tooltip(lbl_title, lambda n=plan.name: _t("compare_plan_click_tip", "'{name}' güç planını aktif yapmak için tıklayın").format(name=n))

            # Başlığa tıklayınca doğrudan o plana geç
            lbl_title.bind("<Button-1>", lambda e, g=plan.guid: self.activate_power_plan(g))
            col_hdr.bind("<Button-1>", lambda e, g=plan.guid: self.activate_power_plan(g))

            if plan.is_active:
                lbl_act = tk.Label(col_hdr, text=_t("badge_active_plan", "● AKTİF PLAN"), font=(f_font, fs(6), "bold"),
                                   fg=THEME["accent_green"], bg=col_hdr["bg"])
                lbl_act.pack()
                self.add_tooltip(lbl_act, lambda n=plan.name: _t("compare_plan_active_tip", "'{name}' şu anda Windows üzerinde etkin olan güç planıdır").format(name=n))
            else:
                btn_act = self.make_btn(
                    col_hdr, _t("btn_activate", "⚡ Aktif Yap"), lambda g=plan.guid: self.activate_power_plan(g),
                    fg=THEME["accent_cyan"], bg=THEME["card_inner"], padx=3, pady=1,
                    tooltip=lambda n=plan.name: _t("compare_plan_btn_tip", "'{name}' planını hemen aktif et").format(name=n)
                )
                btn_act.pack(pady=(0, 2))

        # Satır açıklamaları sözlüğü
        row_tooltips = {
            "cpu_min_ac": _t("row_tip_cpu_min_ac", "İşlemcinin boştayken düşebileceği minimum çalışma frekansı yüzdesi"),
            "cpu_max_ac": _t("row_tip_cpu_max_ac", "İşlemcinin yük altındayken çıkabileceği maksimum frekans yüzdesi (%99 yapılırsa Turbo Boost kapanır)"),
            "cpu_max_freq_ac": _t("row_tip_cpu_max_freq_ac", "İşlemcinin çıkabileceği tavan saat frekansı sınırı (0 = Sınırsız / Donanım Limiti)"),
            "energy_perf_pref_ac": _t("row_tip_energy_perf_pref_ac", "İşlemcinin güç tasarrufu ile performans arasındaki agresiflik dengesi (0=Maksimum Performans, 100=Maksimum Tasarruf)"),
            "boost_mode_ac": _t("row_tip_boost_mode_ac", "İşlemcinin temel saat hızının üzerine çıkma algoritması (Agresif, Etkin vb.)"),
            "cooling_policy_ac": _t("row_tip_cooling_policy_ac", "Etkin: Isınmadan önce fanı hızlandırır; Edilgin: Fan yerine işlemci frekansını kısarak soğutur"),
            "core_parking_min_ac": _t("row_tip_core_parking_min_ac", "Boştayken uyutulmayan (aktif tutulan) minimum CPU çekirdeği yüzdesi"),
            "core_parking_max_ac": _t("row_tip_core_parking_max_ac", "Boştayken uykuya (park moduna) alınabilecek maksimum CPU çekirdeği yüzdesi (%100 = Tümü park edilebilir)"),
            "pcie_aspm_ac": _t("row_tip_pcie_aspm_ac", "PCI Express veri yollarında enerji tasarrufu seviyesi (Ekran kartı ve NVMe SSD gecikmesini etkiler)"),
            "usb_suspend_ac": _t("row_tip_usb_suspend_ac", "Kullanılmayan USB portlarına giden elektriği keserek tasarruf sağlar"),
            "wifi_power_saving_ac": _t("row_tip_wifi_power_saving_ac", "Kablosuz ağ kartı güç tasarruf modu (Oyunlarda ping gecikmesini önlemek için 'En Yüksek Performans' önerilir)"),
            "video_timeout_ac": _t("row_tip_video_timeout_ac", "Sistem boşta kalınca ekranın otomatik kapanma süresi"),
            "sleep_timeout_ac": _t("row_tip_sleep_timeout_ac", "Sistem boşta kalınca bilgisayarın uyku moduna geçme süresi"),
            "hybrid_sleep_ac": _t("row_tip_hybrid_sleep_ac", "Uykuya geçerken RAM verilerini aynı anda diske de yazarak olası elektrik kesintisinde veri kaybını önler"),
            "hibernate_timeout_ac": _t("row_tip_hibernate_timeout_ac", "Sistem boşta kaldığında oturumu diske yazıp sistemi tamamen kapatma süresi (0 = Asla)"),
            "allow_wake_timers_ac": _t("row_tip_allow_wake_timers_ac", "Windows Görev Zamanlayıcısı veya güncellemelerin bilgisayarı uykudan uyandırmasına izin verme durumu"),
            "power_button_ac": _t("row_tip_power_button_ac", "Kasa üzerindeki fiziksel güç düğmesine basıldığında yapılacak eylem"),
            "sleep_button_ac": _t("row_tip_sleep_button_ac", "Klavye üzerindeki uyku düğmesine basıldığında yapılacak eylem"),
            "disk_timeout_ac": _t("row_tip_disk_timeout_ac", "Boşta kalan mekanik sabit disklerin motorunu durdurma süresi"),
        }

        # Matris Satırları ve İnteraktif Çift Tıklama Hücreleri
        for row_idx, (title, val_fn, fmt_fn, key, edit_type, edit_meta) in enumerate(compare_rows):
            vals = [val_fn(s) for _, s in settings_list]
            is_different = len(set(vals)) > 1

            if diff_only and not is_different:
                continue

            row_bg = "#182238" if is_different else ("#121827" if row_idx % 2 == 0 else "#0E1420")
            row_frame = tk.Frame(scrollable_frame, bg=row_bg,
                                 highlightbackground="#2C3B60" if is_different else "#1B2335",
                                 highlightthickness=1)
            row_frame.pack(fill="x", pady=1)

            lbl_pname = tk.Label(
                row_frame, text=title, font=(f_font, fs(7), "bold" if is_different else "normal"),
                fg=THEME["accent_amber"] if is_different else THEME["text_secondary"],
                bg=row_bg, width=w_lbl, anchor="w", padx=8, pady=4
            )
            lbl_pname.pack(side="left")
            self.add_tooltip(lbl_pname, lambda k=key, t=title: row_tooltips.get(k, f"'{t}'"))

            for plan, s in settings_list:
                v = val_fn(s)
                formatted_v = fmt_fn(v)
                col_box = tk.Frame(row_frame, bg=row_bg, width=w_col, height=int(26 * UI_SCALE),
                                   highlightbackground=THEME["card_border"], highlightthickness=1,
                                   cursor="hand2")
                col_box.pack(side="left", fill="y", padx=2)
                col_box.pack_propagate(False)

                lbl_val = tk.Label(
                    col_box, text=formatted_v, font=(f_font, fs(7), "bold" if is_different else "normal"),
                    fg=THEME["accent_cyan"] if is_different else THEME["text_primary"],
                    bg=row_bg, anchor="center", cursor="hand2"
                )
                lbl_val.pack(fill="both", expand=True)
                self.add_tooltip(lbl_val, lambda pn=plan.name, t=title: _t("compare_cell_tip", "Çift tıklayarak '{plan_name}' için '{title}' ayarını değiştirin").format(plan_name=pn, title=t))

                # Hover Efekti
                def _on_enter(e, box=col_box, lbl=lbl_val):
                    box.config(highlightbackground=THEME["accent_cyan"], highlightthickness=1)
                    lbl.config(fg="#FFFFFF")

                def _on_leave(e, box=col_box, lbl=lbl_val, is_diff=is_different):
                    box.config(highlightbackground=THEME["card_border"], highlightthickness=1)
                    lbl.config(fg=THEME["accent_cyan"] if is_diff else THEME["text_primary"])

                col_box.bind("<Enter>", _on_enter)
                col_box.bind("<Leave>", _on_leave)
                lbl_val.bind("<Enter>", _on_enter)
                lbl_val.bind("<Leave>", _on_leave)

                # ÇİFT TIKLAMA İLE DÜZENLEME
                def _open_editor(e, p=plan, k=key, t=title, cur_v=v, e_type=edit_type, e_meta=edit_meta):
                    self.open_compare_cell_editor(p, k, t, cur_v, e_type, e_meta)

                col_box.bind("<Double-Button-1>", _open_editor)
                lbl_val.bind("<Double-Button-1>", _open_editor)

        _bind_mw(scrollable_frame)

    def open_compare_cell_editor(self, plan: PowerPlanItem, key: str, title: str, current_value: int, edit_type: str, edit_meta):
        """Kullanıcının çift tıkladığı satır ve sütundaki ayarı düzenlemesi için modern diyalog açar."""
        f_font = THEME["font_family"]

        top = tk.Toplevel(self.root)
        self.apply_window_icon(top)
        top.title(_t("edit_setting_title", "Ayar Düzenle • {title}").format(title=title))
        top.geometry(f"{int(480 * UI_SCALE)}x{int(380 * UI_SCALE)}")
        top.configure(bg=THEME["bg"])
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()
        apply_dark_titlebar(top)

        # Üst Başlık Kartı
        f_head = tk.Frame(top, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_head.pack(fill="x", padx=14, pady=(12, 8))

        f_head_row = tk.Frame(f_head, bg=THEME["card_bg"])
        f_head_row.pack(fill="x", padx=12, pady=8)

        tk.Label(f_head_row, text=plan.badge_icon, font=(f_font, fs(16)), bg=THEME["card_bg"]).pack(side="left", padx=(0, 8))
        f_title_col = tk.Frame(f_head_row, bg=THEME["card_bg"])
        f_title_col.pack(side="left", fill="x", expand=True)

        tk.Label(f_title_col, text=plan.name, font=(f_font, fs(10), "bold"), fg=THEME["accent_green"], bg=THEME["card_bg"]).pack(anchor="w")
        tk.Label(f_title_col, text=title, font=(f_font, fs(8), "bold"), fg=THEME["accent_amber"], bg=THEME["card_bg"]).pack(anchor="w")

        # Düzenleyici Gövde Kartı
        f_body = tk.Frame(top, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_body.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        val_var = tk.IntVar(value=int(current_value))

        # 1. Yüzdelik Değerler (Min CPU, Max CPU, Core Parking Min/Maks)
        if edit_type == "percent":
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=12)

            f_val_disp = tk.Frame(f_box, bg=THEME["card_inner"])
            f_val_disp.pack(fill="x", pady=(0, 8))
            lbl_cur = tk.Label(f_val_disp, text=f"%{val_var.get()}", font=(f_font, fs(18), "bold"),
                               fg=THEME["accent_cyan"], bg=THEME["card_inner"])
            lbl_cur.pack(side="left")

            def _on_slider(val):
                lbl_cur.config(text=f"%{int(float(val))}")

            slider = tk.Scale(f_box, from_=0, to=100, orient="horizontal", variable=val_var,
                              command=_on_slider, bg=THEME["card_inner"], fg=THEME["text_primary"],
                              highlightthickness=0, troughcolor=THEME["card_bg"], activebackground=THEME["accent_cyan"])
            slider.pack(fill="x", pady=6)

            # Hızlı Değer Butonları
            f_presets = tk.Frame(f_box, bg=THEME["card_inner"])
            f_presets.pack(fill="x", pady=6)
            tk.Label(f_presets, text=_t("lbl_ready", "Hazır:"), font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["card_inner"]).pack(side="left", padx=(0, 4))
            for p_val in [0, 5, 20, 50, 80, 99, 100]:
                self.make_btn(
                    f_presets, f"%{p_val}",
                    lambda pv=p_val: (val_var.set(pv), lbl_cur.config(text=f"%{pv}")),
                    fg=THEME["text_secondary"], bg=THEME["card_bg"], padx=4, pady=2
                ).pack(side="left", padx=2)

        # 2. Maksimum İşlemci Frekansı (MHz)
        elif edit_type == "freq":
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=10)

            f_val_disp = tk.Frame(f_box, bg=THEME["card_inner"])
            f_val_disp.pack(fill="x", pady=(0, 6))

            def _get_freq_str(fv):
                return _t("lbl_freq_unlimited", "Sınırsız (0 MHz - Donanım Limiti)") if fv == 0 else f"{fv} MHz"

            lbl_freq_disp = tk.Label(f_val_disp, text=_get_freq_str(val_var.get()),
                                     font=(f_font, fs(14), "bold"), fg=THEME["accent_cyan"], bg=THEME["card_inner"])
            lbl_freq_disp.pack(side="left")

            def _on_freq_spin():
                lbl_freq_disp.config(text=_get_freq_str(val_var.get()))

            f_spin_row = tk.Frame(f_box, bg=THEME["card_inner"])
            f_spin_row.pack(fill="x", pady=6)
            tk.Label(f_spin_row, text=_t("lbl_freq_limit", "Frekans Sınırı:"), font=(f_font, fs(8), "bold"),
                     fg=THEME["text_secondary"], bg=THEME["card_inner"]).pack(side="left", padx=(0, 6))

            sp_freq = ttk.Spinbox(f_spin_row, from_=0, to=6000, increment=50, width=7,
                                  textvariable=val_var, command=_on_freq_spin, font=(f_font, fs(9), "bold"))
            sp_freq.pack(side="left", padx=4)
            sp_freq.bind("<KeyRelease>", lambda e: _on_freq_spin())
            tk.Label(f_spin_row, text=_t("lbl_freq_unit", "MHz (0 = Sınırsız)"), font=(f_font, fs(7)),
                     fg=THEME["text_muted"], bg=THEME["card_inner"]).pack(side="left", padx=4)

            # Hazır Frekans Butonları
            f_presets = tk.Frame(f_box, bg=THEME["card_inner"])
            f_presets.pack(fill="x", pady=6)
            for f_val, f_lbl in [(0, _t("val_unlimited", "Sınırsız (0)")), (3600, "3.6 GHz"), (4200, "4.2 GHz"), (4500, "4.5 GHz"), (4850, "4.85 GHz")]:
                self.make_btn(
                    f_presets, f_lbl,
                    lambda fv=f_val: (val_var.set(fv), lbl_freq_disp.config(text=_get_freq_str(fv))),
                    fg=THEME["text_secondary"], bg=THEME["card_bg"], padx=4, pady=2
                ).pack(side="left", padx=2)

        # 3. EPP (İşlemci Enerji Tercihi)
        elif edit_type == "epp":
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=10)

            lbl_epp_text = tk.Label(f_box, text="", font=(f_font, fs(9), "bold"), fg=THEME["accent_green"], bg=THEME["card_inner"])
            lbl_epp_text.pack(anchor="w", pady=(0, 4))

            def _update_epp_lbl(val):
                iv = int(float(val))
                if iv == 0:
                    lbl_epp_text.config(text=_t("epp_0", "0: Maksimum Performans (Gecikmesiz)"), fg=THEME["accent_rose"])
                elif iv < 50:
                    lbl_epp_text.config(text=_t("epp_high", "{iv}: Yüksek Performans Ağırlıklı").format(iv=iv), fg=THEME["accent_amber"])
                elif iv == 50:
                    lbl_epp_text.config(text=_t("epp_balanced", "50: Dengeli (Standart Güç Tercihi)"), fg=THEME["accent_cyan"])
                else:
                    lbl_epp_text.config(text=_t("epp_saving", "{iv}: Tasarruf / Düşük Güç Ağırlıklı").format(iv=iv), fg=THEME["accent_green"])

            slider = tk.Scale(f_box, from_=0, to=100, orient="horizontal", variable=val_var,
                              command=_update_epp_lbl, bg=THEME["card_inner"], fg=THEME["text_primary"],
                              highlightthickness=0, troughcolor=THEME["card_bg"], activebackground=THEME["accent_cyan"])
            slider.pack(fill="x", pady=4)
            _update_epp_lbl(val_var.get())

            f_presets = tk.Frame(f_box, bg=THEME["card_inner"])
            f_presets.pack(fill="x", pady=4)
            for p_val, p_lbl in [
                (0, _t("epp_p_0", "0 (Maks Performans)")),
                (33, _t("epp_p_33", "33 (Oyun)")),
                (50, _t("epp_p_50", "50 (Dengeli)")),
                (80, _t("epp_p_80", "80 (Tasarruf)")),
                (100, _t("epp_p_100", "100 (Max Tasarruf)"))
            ]:
                self.make_btn(
                    f_presets, p_lbl,
                    lambda pv=p_val: (val_var.set(pv), _update_epp_lbl(pv)),
                    fg=THEME["text_secondary"], bg=THEME["card_bg"], padx=4, pady=2
                ).pack(side="left", padx=2)

        # 4. Turbo Boost Modu
        elif edit_type == "boost":
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=8)

            boost_options = [
                (0, _t("boost_opt_0", "0: Devre Dışı / Kapalı (Isınmayı ve fan gürültüsünü önler)"), THEME["accent_green"]),
                (1, _t("boost_opt_1", "1: Etkin (Standart Turbo Boost)"), THEME["accent_cyan"]),
                (2, _t("boost_opt_2", "2: Agresif (Maksimum Saat Frekansı & Oyun)"), THEME["accent_rose"]),
                (3, _t("boost_opt_3", "3: Verimli Etkin (Gerektiğinde Boost)"), "#38BDF8"),
                (4, _t("boost_opt_4", "4: Verimli Agresif"), THEME["accent_amber"]),
            ]
            for b_val, b_lbl, col in boost_options:
                tk.Radiobutton(
                    f_box, text=b_lbl, value=b_val, variable=val_var,
                    font=(f_font, fs(7), "bold"), fg=col, bg=THEME["card_inner"],
                    selectcolor=THEME["card_bg"], activebackground=THEME["card_inner"],
                    activeforeground=col, bd=0, highlightthickness=0, cursor="hand2"
                ).pack(anchor="w", pady=2)

        # 5. Sistem Soğutma İlkesi
        elif edit_type == "cooling":
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=16)

            tk.Radiobutton(
                f_box, text=_t("cooling_opt_1", "1: Etkin (Isınmadan Önce Fan Devri Yükselir - Önerilen)"),
                value=1, variable=val_var, font=(f_font, fs(8), "bold"), fg=THEME["accent_green"],
                bg=THEME["card_inner"], selectcolor=THEME["card_bg"], bd=0, highlightthickness=0, cursor="hand2"
            ).pack(anchor="w", pady=6)

            tk.Radiobutton(
                f_box, text=_t("cooling_opt_0", "0: Edilgin (Fan yerine işlemci saat hızı kısılarak soğutulur)"),
                value=0, variable=val_var, font=(f_font, fs(8), "bold"), fg=THEME["accent_amber"],
                bg=THEME["card_inner"], selectcolor=THEME["card_bg"], bd=0, highlightthickness=0, cursor="hand2"
            ).pack(anchor="w", pady=6)

        # 6. PCIe ASPM
        elif edit_type == "aspm":
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=12)

            for a_val, a_lbl, col in [
                (0, _t("aspm_opt_0", "0: Kapalı (Maksimum GPU & SSD Hızı - Önerilen)"), THEME["accent_rose"]),
                (1, _t("aspm_opt_1", "1: Orta Düzey Güç Tasarrufu"), THEME["accent_amber"]),
                (2, _t("aspm_opt_2", "2: Maksimum Güç Tasarrufu"), THEME["accent_green"]),
            ]:
                tk.Radiobutton(
                    f_box, text=a_lbl, value=a_val, variable=val_var,
                    font=(f_font, fs(8), "bold"), fg=col, bg=THEME["card_inner"],
                    selectcolor=THEME["card_bg"], bd=0, highlightthickness=0, cursor="hand2"
                ).pack(anchor="w", pady=4)

        # 7. USB Askıya Alma
        elif edit_type == "usb":
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=16)

            tk.Radiobutton(
                f_box, text=_t("usb_opt_0", "0: Devre Dışı (Sürekli Açık - Fare/Klavye kopmalarını önler)"),
                value=0, variable=val_var, font=(f_font, fs(8), "bold"), fg=THEME["accent_cyan"],
                bg=THEME["card_inner"], selectcolor=THEME["card_bg"], bd=0, highlightthickness=0, cursor="hand2"
            ).pack(anchor="w", pady=6)

            tk.Radiobutton(
                f_box, text=_t("usb_opt_1", "1: Etkin (Boştaki USB Cihazlarını Askıya Al)"),
                value=1, variable=val_var, font=(f_font, fs(8), "bold"), fg=THEME["accent_green"],
                bg=THEME["card_inner"], selectcolor=THEME["card_bg"], bd=0, highlightthickness=0, cursor="hand2"
            ).pack(anchor="w", pady=6)

        # 8. Karma (Hibrit) Uyku
        elif edit_type == "switch_bool":
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=16)

            tk.Radiobutton(
                f_box, text=_t("hybrid_opt_0", "0: Kapalı (Klasik Hızlı Uyku - Diske yazma yapılmaz)"),
                value=0, variable=val_var, font=(f_font, fs(8), "bold"), fg=THEME["accent_cyan"],
                bg=THEME["card_inner"], selectcolor=THEME["card_bg"], bd=0, highlightthickness=0, cursor="hand2"
            ).pack(anchor="w", pady=6)

            tk.Radiobutton(
                f_box, text=_t("hybrid_opt_1", "1: Etkin / Açık (RAM verisini diske de kaydet - Elektrik kesintisine korumalı)"),
                value=1, variable=val_var, font=(f_font, fs(8), "bold"), fg=THEME["accent_green"],
                bg=THEME["card_inner"], selectcolor=THEME["card_bg"], bd=0, highlightthickness=0, cursor="hand2"
            ).pack(anchor="w", pady=6)

        # 9. Uyandırma Zamanlayıcıları
        elif edit_type == "wake_timers":
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=12)

            for w_val, w_lbl, col in [
                (0, _t("wake_opt_0", "0: Devre Dışı (PC hiçbir zaman kendiliğinden uyanmaz)"), THEME["accent_green"]),
                (1, _t("wake_opt_1", "1: Etkin (Görev Zamanlayıcısı ve programlar PC'yi uyandırabilir)"), THEME["accent_cyan"]),
                (2, _t("wake_opt_2", "2: Yalnızca Önemli Zamanlayıcılar (Kritik sistem olayları)"), THEME["accent_amber"]),
            ]:
                tk.Radiobutton(
                    f_box, text=w_lbl, value=w_val, variable=val_var,
                    font=(f_font, fs(8), "bold"), fg=col, bg=THEME["card_inner"],
                    selectcolor=THEME["card_bg"], bd=0, highlightthickness=0, cursor="hand2"
                ).pack(anchor="w", pady=4)

        # 10. Kablosuz Wi-Fi Güç Tasarrufu
        elif edit_type == "wifi":
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=10)

            for wf_val, wf_lbl, col in [
                (0, _t("wifi_opt_0", "0: En Yüksek Performans (Gecikmesiz - Oyunlar için önerilir)"), THEME["accent_rose"]),
                (1, _t("wifi_opt_1", "1: Düşük Düzey Güç Tasarrufu"), THEME["accent_amber"]),
                (2, _t("wifi_opt_2", "2: Orta Düzey Güç Tasarrufu"), THEME["accent_cyan"]),
                (3, _t("wifi_opt_3", "3: Maksimum Güç Tasarrufu"), THEME["accent_green"]),
            ]:
                tk.Radiobutton(
                    f_box, text=wf_lbl, value=wf_val, variable=val_var,
                    font=(f_font, fs(8), "bold"), fg=col, bg=THEME["card_inner"],
                    selectcolor=THEME["card_bg"], bd=0, highlightthickness=0, cursor="hand2"
                ).pack(anchor="w", pady=3)

        # 11. Güç ve Uyku Düğmesi Eylemleri
        elif edit_type == "btn_action":
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=8)

            for a_val, a_lbl, col in [
                (0, _t("btn_act_0", "0: Hiçbir Şey Yapma (Eylem Yok)"), THEME["text_muted"]),
                (1, _t("btn_act_1", "1: Uyku Moduna Al"), THEME["accent_cyan"]),
                (2, _t("btn_act_2", "2: Hazırda Beklet (Oturumu diske yaz)"), THEME["accent_amber"]),
                (3, _t("btn_act_3", "3: Bilgisayarı Kapat (Kapatma komutu ver)"), THEME["accent_rose"]),
                (4, _t("btn_act_4", "4: Yalnızca Ekranı Kapat"), THEME["accent_green"]),
            ]:
                tk.Radiobutton(
                    f_box, text=a_lbl, value=a_val, variable=val_var,
                    font=(f_font, fs(8), "bold"), fg=col, bg=THEME["card_inner"],
                    selectcolor=THEME["card_bg"], bd=0, highlightthickness=0, cursor="hand2"
                ).pack(anchor="w", pady=2)

        # 12. Dakika Değerleri (Ekran, Uyku, Disk, Hazırda Bekleme Zaman Aşımları)
        else:
            f_box = tk.Frame(f_body, bg=THEME["card_inner"])
            f_box.pack(fill="both", expand=True, padx=16, pady=12)

            f_sp_row = tk.Frame(f_box, bg=THEME["card_inner"])
            f_sp_row.pack(anchor="w", pady=(0, 8))

            tk.Label(f_sp_row, text=_t("compare_lbl_duration", "Süre:"), font=(f_font, fs(8), "bold"), fg=THEME["text_secondary"], bg=THEME["card_inner"]).pack(side="left")
            sp = ttk.Spinbox(f_sp_row, from_=0, to=360, width=5, textvariable=val_var, font=(f_font, fs(9), "bold"))
            sp.pack(side="left", padx=6)
            tk.Label(f_sp_row, text=_t("compare_lbl_minutes_never", "dakika (0 = Asla Kapatma)"), font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["card_inner"]).pack(side="left")

            f_presets = tk.Frame(f_box, bg=THEME["card_inner"])
            f_presets.pack(fill="x", pady=6)
            for m_val, m_lbl in [
                (0, _t("compare_preset_never", "Asla (0)")),
                (5, _t("compare_preset_5m", "5 dk")),
                (10, _t("compare_preset_10m", "10 dk")),
                (15, _t("compare_preset_15m", "15 dk")),
                (30, _t("compare_preset_30m", "30 dk")),
                (60, _t("compare_preset_1h", "1 saat"))
            ]:
                self.make_btn(
                    f_presets, m_lbl, lambda mv=m_val: val_var.set(mv),
                    fg=THEME["text_secondary"], bg=THEME["card_bg"], padx=5, pady=2
                ).pack(side="left", padx=2)

        # Alt Butonlar (Kaydet & İptal)
        f_actions = tk.Frame(top, bg=THEME["bg"])
        f_actions.pack(fill="x", padx=14, pady=(0, 12))

        def _save_and_apply():
            new_v = val_var.get()
            ok = PowerManagerService.update_plan_setting(plan.guid, key, new_v)
            if ok:
                top.destroy()
                if hasattr(self, 'lbl_compare_status') and self.lbl_compare_status.winfo_exists():
                    self.lbl_compare_status.config(
                        text=_t("compare_feedback_updated", "✓ '{plan_name}' planında '{title}' ayarı başarıyla güncellendi.").format(plan_name=plan.name, title=title),
                        fg=THEME["accent_green"]
                    )
                    self.root.after(4000, lambda: self.lbl_compare_status.config(
                        text=_t("compare_status_tip", "💡 İpucu: Plan başlığına tıklayarak o plana geçebilir; herhangi bir hücreye çift tıklayarak ayarı düzenleyebilirsiniz."),
                        fg=THEME["text_muted"]
                    ) if hasattr(self, 'lbl_compare_status') and self.lbl_compare_status.winfo_exists() else None)
                self.refresh_compare_matrix_ui()

        self.make_btn(f_actions, _t("btn_save_apply", "💾 Windows'a Kaydet ve Uygula"), _save_and_apply,
                      fg=THEME["accent_green"], bg=THEME["card_inner"], padx=12, pady=5).pack(side="right", padx=(6, 0))

        self.make_btn(f_actions, _t("btn_cancel", "✕ İptal"), top.destroy,
                      fg=THEME["text_muted"], bg=THEME["card_bg"], padx=10, pady=5).pack(side="right")
