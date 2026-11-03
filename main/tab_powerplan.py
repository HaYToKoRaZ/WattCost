"""
WattCost HaYTooL - PowerPlan Tab Modülü
Sistemdeki güç planlarının listelenmesi, anında geçiş, klonlama, silme ve hazır plan eklemelerini yönetir.
"""
import os
import tkinter as tk
from config_manager import THEME, fs
from power_manager import PowerManagerService
from language_manager import _t


class PowerPlanTabMixin:
    """Güç Planı Yöneticisi sekmesi arayüzü ve işlem fonksiyonları."""

    def build_tab_powerplan(self):
        container = self.tab_powerplan
        for w in container.winfo_children():
            w.destroy()

        f_font = THEME["font_family"]
        f_content = tk.Frame(container, bg=THEME["bg"])
        f_content.pack(fill="both", expand=True, padx=12, pady=6)
        self.f_powerplan_content = f_content

        # 1. Aktif Güç Düzeni Banner'ı
        card_active = self.create_card(f_content, pady=(0, 6))
        self.make_card_title(card_active, _t("active_plan_title", "ŞU ANDA AKTİF OLAN GÜÇ DÜZENİ"), THEME["accent_green"])

        f_act_row = tk.Frame(card_active, bg=THEME["card_bg"])
        f_act_row.pack(fill="x", padx=14, pady=(4, 6))

        self.lbl_active_plan_badge = tk.Label(f_act_row, text="🌱", font=(f_font, fs(18)), bg=THEME["card_bg"], fg=THEME["accent_green"])
        self.lbl_active_plan_badge.pack(side="left", padx=(0, 8))

        f_act_info = tk.Frame(f_act_row, bg=THEME["card_bg"])
        f_act_info.pack(side="left", fill="x", expand=True)

        self.lbl_active_plan_name = tk.Label(f_act_info, text="Loading...", font=(f_font, fs(12), "bold"),
                                             fg=THEME["text_primary"], bg=THEME["card_bg"])
        self.lbl_active_plan_name.pack(anchor="w")

        self.lbl_active_plan_guid = tk.Label(f_act_info, text="GUID: ---", font=(f_font, fs(7)),
                                             fg=THEME["text_muted"], bg=THEME["card_bg"])
        self.lbl_active_plan_guid.pack(anchor="w")

        # Gelişmiş Güç Araç Çubuğu Butonları
        f_act_btns = tk.Frame(card_active, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_act_btns.pack(fill="x", padx=12, pady=(2, 8))

        # 1. Satır: Plan İşlemleri ve Ekleme
        f_btn_row1 = tk.Frame(f_act_btns, bg=THEME["card_inner"])
        f_btn_row1.pack(fill="x", padx=6, pady=(5, 3))
        self.make_btn(f_btn_row1, _t("btn_refresh", "🔄 Yenile"), self.refresh_power_plans_ui, fg=THEME["accent_cyan"], bg=THEME["card_bg"],
                      tooltip=lambda: _t("tooltip_refresh_plans", "Sistemdeki güç planlarını yeniden tarar ve listeyi günceller")).pack(side="left", padx=3)
        self.make_btn(f_btn_row1, _t("btn_add_wattcost_plans", "⚡ WattCost Planlarını Ekle"), self.add_haytool_all_plans, fg=THEME["accent_green"], bg=THEME["card_bg"],
                      tooltip=lambda: _t("tooltip_add_wattcost", "Özel optimize edilmiş 4 kademeli WattCost güç planlarını sisteme yükler")).pack(side="left", padx=3)
        self.make_btn(f_btn_row1, _t("btn_add_amd_plans", "🔴 AMD Ryzen Planları Ekle"), self.add_amd_ryzen_plans, fg=THEME["accent_rose"], bg=THEME["card_bg"],
                      tooltip=lambda: _t("tooltip_add_amd", "AMD Ryzen işlemciler için özel enerji ve boost profillerini sisteme ekler")).pack(side="left", padx=3)
        self.make_btn(f_btn_row1, _t("btn_add_ultimate", "⚡ Ultimate Performance"), self.add_ultimate_performance_plan, fg=THEME["accent_amber"], bg=THEME["card_bg"],
                      tooltip=lambda: _t("tooltip_add_ultimate", "Windows'un resmi Ultimate Performance güç modunu sisteme tanıtır")).pack(side="left", padx=3)
        self.make_btn(f_btn_row1, _t("btn_restore_defaults", "↩️ Windows Varsayılana Sıfırla"), self.restore_windows_defaults, fg=THEME["text_muted"], bg=THEME["card_bg"],
                      tooltip=lambda: _t("tooltip_restore_defaults", "Windows varsayılan güç planlarını geri yükler")).pack(side="left", padx=3)

        # Ayraç
        tk.Frame(f_act_btns, bg=THEME["card_border"], height=1).pack(fill="x", padx=6, pady=2)

        # 2. Satır: Windows Güç Ayarları ve Gizli Seçenekler
        f_btn_row2 = tk.Frame(f_act_btns, bg=THEME["card_inner"])
        f_btn_row2.pack(fill="x", padx=6, pady=(3, 5))
        self.make_btn(f_btn_row2, _t("btn_unlock_hidden", "🔓 Windows Gizli Ayarları Aç"), self.unlock_hidden_power_settings, fg=THEME["accent_amber"], bg=THEME["card_bg"],
                      tooltip=lambda: _t("tooltip_unlock_hidden", "Windows güç seçeneklerinde gizli olan işlemci frekansı, çekirdek park etme ve uyku gibi onlarca gizli ayarın kilidini açar")).pack(side="left", padx=3)
        self.make_btn(f_btn_row2, _t("btn_lock_hidden", "🔒 Gizli Ayarları Kapat"), self.lock_hidden_power_settings, fg=THEME["text_muted"], bg=THEME["card_bg"],
                      tooltip=lambda: _t("tooltip_lock_hidden", "Windows güç ayarlarındaki gelişmiş gizli seçenekleri tekrar gizler ve sadeleştirir")).pack(side="left", padx=3)
        self.make_btn(f_btn_row2, _t("btn_open_adv_cpl", "🛠️ Gelişmiş Güç Ayarları"), self.open_windows_advanced_power_cpl, fg=THEME["accent_amber"], bg=THEME["card_bg"],
                      tooltip=lambda: _t("tooltip_open_adv_cpl", "Aktif güç planının gelişmiş ince ayar penceresini doğrudan açar")).pack(side="left", padx=3)
        self.make_btn(f_btn_row2, _t("btn_open_power_cpl", "⚙️ Windows Güç Seçenekleri (cpl)"), self.open_windows_power_cpl, fg=THEME["accent_cyan"], bg=THEME["card_bg"],
                      tooltip=lambda: _t("tooltip_open_power_cpl", "Klasik Windows Güç Seçenekleri Denetim Masası penceresini açar")).pack(side="left", padx=3)

        self.lbl_power_action_msg = tk.Label(card_active, text="", font=(f_font, fs(8), "bold"),
                                             fg=THEME["accent_green"], bg=THEME["card_bg"])
        self.lbl_power_action_msg.pack(anchor="w", padx=14, pady=(0, 6))

        # 2. Sistem Güç Planları Listesi
        card_list = self.create_card(f_content, pady=(0, 4))
        self.make_card_title(card_list, _t("plans_list_title", "SİSTEMDEKİ GÜÇ DÜZENLERİ (TEK TIKLA GEÇİŞ)"), THEME["accent_cyan"])

        self.f_plans_list_container = tk.Frame(card_list, bg=THEME["card_bg"])
        self.f_plans_list_container.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        self.refresh_power_plans_ui()

    def refresh_power_plans_ui(self):
        f_font = THEME["font_family"]
        self.power_plans = PowerManagerService.get_power_plans()
        self.active_power_plan = None
        for p in self.power_plans:
            if p.is_active:
                self.active_power_plan = p
                break

        if self.active_power_plan and hasattr(self, 'lbl_active_plan_name') and self.lbl_active_plan_name.winfo_exists():
            self.lbl_active_plan_badge.config(text=self.active_power_plan.badge_icon)
            self.lbl_active_plan_name.config(text=self.active_power_plan.name)
            self.lbl_active_plan_guid.config(text=f"GUID: {self.active_power_plan.guid}")

        if hasattr(self, 'f_plans_list_container') and self.f_plans_list_container.winfo_exists():
            for child in self.f_plans_list_container.winfo_children():
                child.destroy()

            for plan in self.power_plans:
                item_frame = tk.Frame(self.f_plans_list_container, bg=THEME["card_inner"],
                                      highlightbackground=THEME["accent_cyan"] if plan.is_active else THEME["card_border"],
                                      highlightthickness=1)
                item_frame.pack(fill="x", pady=3)

                f_left_info = tk.Frame(item_frame, bg=THEME["card_inner"])
                f_left_info.pack(side="left", padx=8, pady=6, fill="x", expand=True)

                f_name_row = tk.Frame(f_left_info, bg=THEME["card_inner"])
                f_name_row.pack(anchor="w")

                tk.Label(f_name_row, text=plan.badge_icon, font=(f_font, fs(10)), bg=THEME["card_inner"]).pack(side="left", padx=(0, 5))
                tk.Label(f_name_row, text=plan.name, font=(f_font, fs(8), "bold"),
                         fg=THEME["accent_cyan"] if plan.is_active else THEME["text_primary"],
                         bg=THEME["card_inner"]).pack(side="left")

                tk.Label(f_left_info, text=plan.guid, font=(f_font, fs(6)),
                         fg=THEME["text_muted"], bg=THEME["card_inner"]).pack(anchor="w")

                f_right_actions = tk.Frame(item_frame, bg=THEME["card_inner"])
                f_right_actions.pack(side="right", padx=8, pady=6)

                if plan.is_active:
                    tk.Label(f_right_actions, text=_t("badge_active_plan", "● AKTİF PLAN"), font=(f_font, fs(7), "bold"),
                             fg=THEME["accent_green"], bg=THEME["card_inner"], padx=6, pady=2).pack(side="right")
                else:
                    self.make_btn(
                        f_right_actions, _t("btn_make_active", "⚡ Aktif Yap"),
                        lambda g=plan.guid: self.activate_power_plan(g),
                        fg=THEME["accent_cyan"], bg=THEME["card_bg"], padx=6, pady=2,
                        tooltip=_t("tooltip_make_active", "Bu güç planını sistemde etkin güç modu olarak ayarlar")
                    ).pack(side="right", padx=(4, 0))

                self.make_btn(
                    f_right_actions, _t("btn_clone", "📋 Klonla"),
                    lambda g=plan.guid, n=plan.name: self.duplicate_power_plan(g, n),
                    fg=THEME["text_secondary"], bg=THEME["card_bg"], padx=5, pady=2,
                    tooltip=_t("tooltip_clone_plan", "Bu güç planının tüm ayarlarıyla birebir bir kopyasını oluşturur")
                ).pack(side="right", padx=(2, 0))

                if not plan.is_active and len(self.power_plans) > 1:
                    self.make_btn(
                        f_right_actions, _t("btn_delete", "✕"),
                        lambda g=plan.guid: self.delete_power_plan(g),
                        fg=THEME["accent_rose"], bg=THEME["card_bg"], padx=5, pady=2,
                        tooltip=_t("tooltip_delete_plan", "Bu güç planını sistemden kalıcı olarak siler")
                    ).pack(side="right", padx=(2, 0))

        if hasattr(self, 'update_smart_switch_options'):
            self.update_smart_switch_options()

        # Windows Görev Çubuğu Jump List'i güncel güç planlarıyla yenile
        try:
            import threading
            from jumplist_manager import setup_jump_list
            threading.Thread(target=setup_jump_list, args=(self.power_plans,), daemon=True).start()
        except Exception:
            pass

    def unlock_hidden_power_settings(self):
        self.show_power_action_feedback(_t("prompt_hidden_opening", "⏳ Windows gizli güç ayarları açılıyor, lütfen bekleyin..."), True)
        self.root.update_idletasks()

        def _do():
            ok = PowerManagerService.unlock_all_hidden_settings(True)
            def _ui():
                if ok:
                    self.show_power_action_feedback(_t("prompt_hidden_opened", "✅ Windows Denetim Masasındaki tüm gizli güç ayarları (Turbo Boost, EPP, Park vb.) başarıyla açıldı!"), True)
                else:
                    self.show_power_action_feedback(_t("prompt_hidden_open_err", "⚠️ Gizli ayarlar açılamadı (UAC izni verilmemiş olabilir)."), False)
                if hasattr(self, 'refresh_power_plans_ui'):
                    self.refresh_power_plans_ui()
                if hasattr(self, 'refresh_compare_matrix_ui'):
                    self.refresh_compare_matrix_ui()
            self.root.after(0, _ui)

        import threading
        threading.Thread(target=_do, daemon=True).start()

    def lock_hidden_power_settings(self):
        self.show_power_action_feedback(_t("prompt_hidden_closing", "⏳ Windows gizli güç ayarları kapatılıyor, lütfen bekleyin..."), True)
        self.root.update_idletasks()

        def _do():
            ok = PowerManagerService.unlock_all_hidden_settings(False)
            def _ui():
                if ok:
                    self.show_power_action_feedback(_t("prompt_hidden_closed", "🔒 Gizli güç ayarları Windows Denetim Masasında tekrar gizlendi."), True)
                else:
                    self.show_power_action_feedback(_t("prompt_hidden_close_err", "⚠️ Gizli ayarlar kapatılamadı."), False)
                if hasattr(self, 'refresh_power_plans_ui'):
                    self.refresh_power_plans_ui()
                if hasattr(self, 'refresh_compare_matrix_ui'):
                    self.refresh_compare_matrix_ui()
            self.root.after(0, _ui)

        import threading
        threading.Thread(target=_do, daemon=True).start()

    def open_windows_power_cpl(self):
        try:
            os.system("start control powercfg.cpl")
        except Exception:
            pass

    def open_windows_advanced_power_cpl(self):
        try:
            os.system("start control powercfg.cpl,,1")
        except Exception:
            pass

    def activate_power_plan(self, guid):
        ok = PowerManagerService.set_active_plan(guid)
        if ok:
            plan_name = _t("power_plan_default", "Güç Planı")
            badge = "⚡"
            for p in getattr(self, "power_plans", []):
                if p.guid.lower() == str(guid).lower():
                    plan_name = p.name
                    badge = p.badge_icon
                    break
            self.refresh_power_plans_ui()
            if getattr(self, "current_tab", "") == "compare" and hasattr(self, 'refresh_compare_matrix_ui'):
                self.refresh_compare_matrix_ui()
            if hasattr(self, 'show_power_plan_toast'):
                self.show_power_plan_toast(plan_name=plan_name, icon=badge, subtitle=_t("toast_user_activated", "Kullanıcı tarafından aktif edildi"))
            self._last_detected_plan_guid = str(guid).lower()
            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    self.tray_icon.update_menu()
                except Exception:
                    pass

    def duplicate_power_plan(self, guid, old_name):
        new_name = f"{old_name} (Copy)"
        new_guid = PowerManagerService.duplicate_plan(guid, new_name)
        if new_guid:
            self.refresh_power_plans_ui()

    def delete_power_plan(self, guid):
        ok = PowerManagerService.delete_plan(guid)
        if ok:
            self.refresh_power_plans_ui()

    def show_power_action_feedback(self, text: str, is_success: bool = True):
        if hasattr(self, 'lbl_power_action_msg') and self.lbl_power_action_msg.winfo_exists():
            col = THEME["accent_green"] if is_success else THEME["accent_amber"]
            self.lbl_power_action_msg.config(text=text, fg=col)
            self.root.after(5000, lambda: self.lbl_power_action_msg.config(text="") if hasattr(self, 'lbl_power_action_msg') and self.lbl_power_action_msg.winfo_exists() else None)

    def add_ultimate_performance_plan(self):
        ok, msg = PowerManagerService.add_ultimate_performance()
        self.show_power_action_feedback(msg, ok)
        self.refresh_power_plans_ui()

    def add_haytool_all_plans(self):
        results = [
            PowerManagerService.add_wattcost_max_saver(),
            PowerManagerService.add_wattcost_bal_saver(),
            PowerManagerService.add_wattcost_high_perf(),
            PowerManagerService.add_wattcost_max_perf(),
        ]
        added_count = sum(1 for ok, _ in results if ok)
        if added_count == 0:
            self.show_power_action_feedback(_t("prompt_plans_added_updated", "⚡ 4 adet WattCost güç planı güncellendi."), True)
        elif added_count == 4:
            self.show_power_action_feedback(_t("prompt_plans_added_success", "⚡ 4 adet WattCost Güç Planı başarıyla eklendi."), True)
        else:
            self.show_power_action_feedback(_t("prompt_plans_added_count", "⚡ {count} adet yeni WattCost planı eklendi (diğerleri güncellendi).").format(count=added_count), True)
        self.refresh_power_plans_ui()
        if hasattr(self, 'refresh_compare_matrix_ui'):
            self.refresh_compare_matrix_ui()

    def add_amd_ryzen_plans(self):
        results = [
            PowerManagerService.add_amd_ryzen_balanced(),
            PowerManagerService.add_amd_ryzen_high_performance(),
        ]
        added_count = sum(1 for ok, _ in results if ok)
        if added_count == 0:
            self.show_power_action_feedback(_t("prompt_ryzen_exists", "ℹ️ AMD Ryzen planları sisteminizde zaten mevcut, mükerrer eklenmedi."), False)
        elif added_count == 2:
            self.show_power_action_feedback(_t("prompt_ryzen_added", "🔴 AMD Ryzen Dengeli ve Yüksek Performans planları başarıyla eklendi."), True)
        else:
            self.show_power_action_feedback(_t("prompt_ryzen_count", "🔴 {count} adet AMD Ryzen planı eklendi.").format(count=added_count), True)
        self.refresh_power_plans_ui()

    def restore_windows_defaults(self):
        if mb.askyesno(_t("prompt_reset_default_title", "Varsayılana Sıfırla"), _t("prompt_reset_default_msg", "Tüm özel güç planları silinip Windows varsayılan güç planlarına (Dengeli, Güç Tasarrufu, Yüksek Performans) sıfırlanacak.\n\nEmin misiniz?")):
            ok = PowerManagerService.restore_defaults()
            if ok:
                self.show_power_action_feedback(_t("prompt_reset_default_done", "↩️ Tüm güç planları başarıyla Windows varsayılanına sıfırlandı."), True)
            self.refresh_power_plans_ui()
