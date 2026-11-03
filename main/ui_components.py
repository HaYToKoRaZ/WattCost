"""
WattCost HaYTooL - Temel UI Bileşenleri ve İletişim Pencereleri Modülü
Kartlar, başlıklar, butonlar, OSD test simülatörü ve Genel Ayarlar diyalogu.
"""
import os
import sys
import subprocess
import re
import time
import threading
import tkinter as tk
from tkinter import ttk
from config_manager import THEME, UI_SCALE, fs, get_asset_path, APP_VERSION
from history_manager import WindowsAutoStart
from hotkey_manager import HOTKEY_OPTIONS
from language_manager import _t

class ToolTip:
    """Cyber-Tech UI Tooltip bileşeni: Fare ile öğenin üzerine gelindiğinde zarif bilgi kutusu açar."""
    def __init__(self, widget, text, delay=350):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self._after_id = None

        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")
        self.widget.bind("<ButtonPress>", self._on_leave, add="+")
        self.widget.bind("<Destroy>", self._on_destroy, add="+")

    def _on_enter(self, event=None):
        self._cancel()
        try:
            self._after_id = self.widget.after(self.delay, self.show_tip)
        except Exception:
            pass

    def _on_leave(self, event=None):
        self._cancel()
        self.hide_tip()

    def _on_destroy(self, event=None):
        self._cancel()
        self.hide_tip()

    def _cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def show_tip(self):
        tip_text = self.text() if callable(self.text) else self.text
        if not tip_text or not self.widget.winfo_exists():
            return
        if self.tip_window or not self.widget.winfo_viewable():
            return

        try:
            x = self.widget.winfo_rootx() + 8
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4

            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.attributes("-topmost", True)
            tw.configure(bg=THEME["card_border"])

            f_inner = tk.Frame(tw, bg=THEME["card_inner"], highlightbackground=THEME["accent_cyan"], highlightthickness=1)
            f_inner.pack(fill="both", expand=True)

            lbl = tk.Label(
                f_inner, text=tip_text, font=(THEME["font_family"], fs(7)),
                fg=THEME["text_primary"], bg=THEME["card_inner"],
                justify="left", padx=8, pady=4, wraplength=int(320 * UI_SCALE)
            )
            lbl.pack()

            tw.update_idletasks()
            tip_w = tw.winfo_width()
            tip_h = tw.winfo_height()
            screen_w = tw.winfo_screenwidth()
            screen_h = tw.winfo_screenheight()

            if x + tip_w > screen_w - 10:
                x = max(10, screen_w - tip_w - 10)
            if y + tip_h > screen_h - 10:
                y = max(10, self.widget.winfo_rooty() - tip_h - 4)

            tw.wm_geometry(f"+{x}+{y}")
        except Exception:
            self.hide_tip()

    def hide_tip(self):
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None


class UIComponentsMixin:
    """Temel arayüz öğeleri, yardımcı pencereler ve diyalogları barındıran mixin sınıfı."""

    def add_tooltip(self, widget, text):
        """Herhangi bir Tkinter bileşenine fare üzeri açıklama (tooltip) ekler."""
        if widget and text:
            return ToolTip(widget, text)
        return None

    def apply_always_on_top(self):
        val = bool(self.on_top_var.get()) if hasattr(self, 'on_top_var') else bool(self.config.get("always_on_top", True))
        try:
            self.root.attributes("-topmost", val)
        except Exception:
            pass

    def toggle_always_on_top(self):
        cur = self.on_top_var.get() if hasattr(self, 'on_top_var') else self.config.get("always_on_top", True)
        new_val = not bool(cur)
        if hasattr(self, 'on_top_var'):
            self.on_top_var.set(new_val)
        self.config["always_on_top"] = new_val
        self.apply_always_on_top()
        self.save_config()
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.update_menu()
            except Exception:
                pass

    def bring_to_front(self):
        """Pencereyi tepsiye gizlenmişse geri getirir ve en öne taşır."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def play_notification_sound(self, is_smart: bool = False, force: bool = False):
        """Güç planı veya otomasyon değiştiğinde duyulabilir, zarif bir ses çalar."""
        # Akıllı geçiş ise smart_switch_sound, manuel güç planı ise power_plan_sound (varsayılan True) kontrol edilir
        if is_smart:
            sound_enabled = self.config.get("smart_switch_sound", True)
        else:
            sound_enabled = self.config.get("power_plan_sound", self.config.get("smart_switch_sound", True))

        if not sound_enabled and not force:
            return

        now = time.time()
        last_sound = getattr(self, '_last_sound_time', 0.0)
        if not force and (now - last_sound < 0.4):
            return
        self._last_sound_time = now

        def _play():
            try:
                import winsound
                win_media = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Media")
                for snd_file in ["notify.wav", "Windows Notify System.wav", "chimes.wav", "ding.wav"]:
                    full_p = os.path.join(win_media, snd_file)
                    if os.path.isfile(full_p):
                        winsound.PlaySound(full_p, winsound.SND_FILENAME | winsound.SND_ASYNC)
                        return
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                try:
                    import winsound
                    winsound.MessageBeep(0)
                except Exception:
                    pass

        try:
            threading.Thread(target=_play, daemon=True).start()
        except Exception:
            pass

    def format_currency(self, val: float, decimals: int = 2) -> str:
        """Para birimini aktif dile göre formatlar (TR: 12.50 TL / EN: $12.50)."""
        fmt = _t("currency_fmt", "{val} TL")
        if decimals == 0:
            val_str = f"{val:.0f}"
        elif decimals == 1:
            val_str = f"{val:.1f}"
        else:
            val_str = f"{val:.2f}"
        return fmt.format(val=val_str)

    def format_rate_hour(self, rate: float) -> str:
        """Saatlik maliyeti aktif dile göre formatlar (TR: 0.42 TL/sa / EN: $0.42/h)."""
        fmt = _t("currency_hour_fmt", "{val} TL/sa")
        return fmt.format(val=f"{rate:.2f}")

    def show_power_plan_toast(self, plan_name: str, icon: str = "⚡", subtitle: str = "", tier_name: str = "", hz: int = 0, play_sound: bool = True):
        """Güç planı değiştiğinde sadece aktif plan adını gösteren ultra-kompakt, modern bir bildirim kapsülü açar."""
        is_smart = bool(tier_name)

        if play_sound:
            self.play_notification_sound(is_smart=is_smart)

        # Akıllı geçiş ise smart_switch_toast, manuel ise power_plan_toast kontrol edilir
        should_toast = self.config.get("smart_switch_toast", True) if is_smart else self.config.get("power_plan_toast", True)
        if not should_toast:
            return

        self._last_toast_time = time.time()

        # Varsa önceki aktif toast penceresini kapat
        if hasattr(self, '_active_toast') and self._active_toast:
            try:
                self._active_toast.destroy()
            except Exception:
                pass
            self._active_toast = None

        try:
            toast = tk.Toplevel(self.root)
            self._active_toast = toast
            toast.wm_overrideredirect(True)
            toast.wm_attributes("-topmost", True)
            try:
                toast.wm_attributes("-alpha", 0.0)
            except Exception:
                pass
        except Exception:
            return

        # 1. Aktif Temadan Renkleri Çek (Tema Entegrasyonu)
        c_bg = THEME.get("card_bg", "#0E1424")
        c_inner = THEME.get("card_inner", "#162035")
        c_fg_primary = THEME.get("text_primary", "#FFFFFF")
        c_fg_muted = THEME.get("text_muted", "#64748B")
        f_font = THEME.get("font_family", "Segoe UI")

        # 2. Kademe / Moda Göre Dinamik Vurgu Rengi
        accent_color = THEME.get("accent_cyan", "#06B6D4")
        if "Kademe 4" in tier_name or "Tier 4" in tier_name or "Apex" in plan_name or "Nihai" in plan_name or "High" in plan_name or "Maximum Performance" in plan_name:
            accent_color = THEME.get("accent_rose", "#F43F5E")
        elif "Kademe 3" in tier_name or "Tier 3" in tier_name or "AMD" in plan_name or "High Performance" in plan_name:
            accent_color = THEME.get("accent_amber", "#F59E0B")
        elif "Kademe 2" in tier_name or "Tier 2" in tier_name:
            accent_color = THEME.get("accent_cyan", "#06B6D4")
        elif "Kademe 1" in tier_name or "Tier 1" in tier_name or "Eco" in plan_name or "Tasarruf" in plan_name or "Power Saver" in plan_name:
            accent_color = THEME.get("accent_green", "#10B981")

        # 3. Ultra-Kompakt Tek Satır Kapsül (Floating Pill)
        pill = tk.Frame(toast, bg=c_bg, highlightbackground=accent_color, highlightthickness=1)
        pill.pack(fill="both", expand=True)

        # Sol Kenar: Neon Accent Çubuğu
        accent_bar = tk.Frame(pill, bg=accent_color, width=int(3 * UI_SCALE))
        accent_bar.pack(side="left", fill="y")

        # İkon
        lbl_icon = tk.Label(pill, text=icon, font=(f_font, fs(10)), bg=c_bg, fg=accent_color, padx=int(6 * UI_SCALE))
        lbl_icon.pack(side="left")

        # Sadece Plan Adı
        lbl_name = tk.Label(pill, text=plan_name, font=(f_font, fs(9), "bold"),
                            fg=c_fg_primary, bg=c_bg, anchor="w", padx=int(4 * UI_SCALE))
        lbl_name.pack(side="left", fill="x", expand=True)

        # Kapatma Butonu (✕)
        is_closing = [False]
        def _close_toast(animate=True):
            if is_closing[0]:
                return
            is_closing[0] = True
            if hasattr(self, '_active_toast') and self._active_toast == toast:
                self._active_toast = None

            def _step_fade(cur_a):
                try:
                    if cur_a <= 0.08:
                        toast.destroy()
                    else:
                        toast.wm_attributes("-alpha", cur_a - 0.16)
                        toast.after(16, lambda: _step_fade(cur_a - 0.16))
                except Exception:
                    try:
                        toast.destroy()
                    except Exception:
                        pass

            if animate:
                try:
                    _step_fade(0.96)
                except Exception:
                    toast.destroy()
            else:
                try:
                    toast.destroy()
                except Exception:
                    pass

        btn_close = tk.Button(pill, text="✕", font=(f_font, fs(7), "bold"),
                              bg=c_bg, fg=c_fg_muted,
                              activebackground=c_inner, activeforeground="#F43F5E",
                              relief="flat", bd=0, padx=int(8 * UI_SCALE), pady=0, cursor="hand2",
                              command=lambda: _close_toast(False))
        btn_close.pack(side="right")
        self.add_tooltip(btn_close, _t("toast_btn_close_tip", "Bildirimi Kapat"))

        # Tıklayınca ana pencereyi öne getir
        def _on_click(e):
            self.bring_to_front()
            _close_toast(False)

        for w in (pill, lbl_icon, lbl_name, accent_bar):
            w.bind("<Button-1>", _on_click)

        # Otomatik Boyut & Ekran Sağ Alt Konumlandırması
        toast.update_idletasks()
        w = max(int(200 * UI_SCALE), pill.winfo_reqwidth() + int(12 * UI_SCALE))
        h = max(int(34 * UI_SCALE), pill.winfo_reqheight() + int(4 * UI_SCALE))
        screen_w = toast.winfo_screenwidth()
        screen_h = toast.winfo_screenheight()

        pos_x = screen_w - w - int(20 * UI_SCALE)
        target_pos_y = screen_h - h - int(55 * UI_SCALE)

        toast.geometry(f"{w}x{h}+{pos_x}+{target_pos_y}")

        # Yumuşak Fade-in Animasyonu
        def _fade_in(target=0.96, step=0.18):
            try:
                cur = float(toast.wm_attributes("-alpha"))
                if cur < target:
                    toast.wm_attributes("-alpha", min(target, cur + step))
                    toast.after(16, lambda: _fade_in(target, step))
                else:
                    toast.lift()
            except Exception:
                try:
                    toast.wm_attributes("-alpha", target)
                except Exception:
                    pass

        _fade_in()

        # Otomatik Kapanma (2.8 saniye) & Hover Pause
        close_timer = [None]
        def _schedule_close(ms=2800):
            close_timer[0] = toast.after(ms, _close_toast)

        def _on_enter(e):
            if close_timer[0]:
                toast.after_cancel(close_timer[0])
                close_timer[0] = None

        def _on_leave(e):
            _schedule_close(1200)

        pill.bind("<Enter>", _on_enter)
        pill.bind("<Leave>", _on_leave)
        _schedule_close(2800)

        # Ayrıca Sistem Tepsisi (Tray) bildirimini de tetikle
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.notify(plan_name, _t("toast_tag_plan_changed", "⚡ Güç Planı Değişti"))
            except Exception:
                pass

    def apply_window_icon(self, win):
        """Pencereye (root veya Toplevel) uygulamanın resmi simgesini uygular."""
        try:
            ico_p = get_asset_path("app_icon.ico")
            if os.path.exists(ico_p):
                win.iconbitmap(ico_p)
            cand_p = get_asset_path("app_icon.png")
            if os.path.exists(cand_p):
                img_ico = ImageTk.PhotoImage(file=cand_p)
                win.iconphoto(True, img_ico)
                win._app_icon_ref = img_ico
        except Exception:
            pass

    def create_card(self, parent=None, pady=(0, 6)):
        if parent is None or parent == self.root:
            parent = getattr(self, "tab_cost", self.root)
        frame = tk.Frame(parent, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
        frame.pack(fill="x", padx=12, pady=pady)
        return frame

    def make_btn(self, parent, text, command, fg=None, bg=None, padx=None, pady=None, tooltip=None, bold=True, **kwargs):
        bg = bg or THEME["btn_bg"]
        px = padx if padx is not None else int(8 * UI_SCALE)
        py = pady if pady is not None else int(3 * UI_SCALE)
        weight = "bold" if bold else "normal"
        btn = tk.Button(parent, text=text, command=command, font=(THEME["font_family"], fs(8), weight),
                        bg=bg, fg=fg or THEME["text_secondary"], activebackground=THEME.get("btn_hover", "#273548"),
                        activeforeground=THEME["text_primary"], relief="flat", bd=0,
                        padx=px, pady=py, cursor="hand2")
        btn.bind("<Enter>", lambda e: btn.config(bg=THEME["btn_hover"]) if btn["state"] != "disabled" else None, add="+")
        btn.bind("<Leave>", lambda e: btn.config(bg=bg) if btn["state"] != "disabled" else None, add="+")
        btn.bind("<ButtonPress-1>", lambda e: btn.config(relief="sunken") if btn["state"] != "disabled" else None, add="+")
        btn.bind("<ButtonRelease-1>", lambda e: btn.config(relief="flat") if btn["state"] != "disabled" else None, add="+")
        if tooltip:
            self.add_tooltip(btn, tooltip)
        return btn

    def make_check(self, parent, text, var, command, fg=None, bold=False, bg=None, tooltip=None):
        bg = bg or THEME["card_bg"]
        container = tk.Frame(parent, bg=bg, cursor="hand2")

        sw_w = int(24 * UI_SCALE)
        sw_h = int(13 * UI_SCALE)
        radius = sw_h // 2
        canvas = tk.Canvas(container, width=sw_w, height=sw_h, bg=bg, bd=0, highlightthickness=0, cursor="hand2")
        canvas.pack(side="left", padx=(0, 6), pady=1)

        lbl = tk.Label(container, text=text,
                       font=(THEME["font_family"], fs(8), "bold" if bold else "normal"),
                       fg=fg or THEME["text_secondary"], bg=bg, cursor="hand2")
        lbl.pack(side="left")

        def _draw():
            canvas.delete("all")
            val = bool(var.get())
            track_color = THEME["accent_cyan"] if val else "#1E293B"
            border_color = THEME["accent_cyan"] if val else "#334155"
            thumb_color = "#FFFFFF" if val else "#64748B"

            # Yuvarlak köşeli pill rayı
            canvas.create_oval(1, 1, sw_h - 1, sw_h - 1, fill=track_color, outline=border_color)
            canvas.create_oval(sw_w - sw_h + 1, 1, sw_w - 1, sw_h - 1, fill=track_color, outline=border_color)
            canvas.create_rectangle(radius, 1, sw_w - radius, sw_h - 1, fill=track_color, outline=track_color)

            # Kaydırıcı (Thumb)
            t_pad = 2
            t_sz = sw_h - (t_pad * 2)
            if val:
                tx1 = sw_w - sw_h + t_pad
            else:
                tx1 = t_pad
            ty1 = t_pad
            tx2 = tx1 + t_sz
            ty2 = ty1 + t_sz
            canvas.create_oval(tx1, ty1, tx2, ty2, fill=thumb_color, outline=thumb_color)

        def _toggle(e=None):
            var.set(not bool(var.get()))
            _draw()
            if command:
                command()

        canvas.bind("<Button-1>", _toggle)
        lbl.bind("<Button-1>", _toggle)
        container.bind("<Button-1>", _toggle)

        # var değiştiğinde çizimi senkronize et
        def _on_var_write(*args):
            try:
                if canvas.winfo_exists():
                    _draw()
            except Exception:
                pass
        try:
            var_trace_id = var.trace_add("write", _on_var_write)
            container._var_trace_id = var_trace_id
        except Exception:
            pass

        _draw()

        if tooltip:
            self.add_tooltip(container, tooltip)
            self.add_tooltip(canvas, tooltip)
            self.add_tooltip(lbl, tooltip)
        return container

    def make_card_title(self, card, text, color, right_widget_factory=None):
        row = tk.Frame(card, bg=THEME["card_bg"])
        row.pack(fill="x", padx=int(12 * UI_SCALE), pady=(int(8 * UI_SCALE), int(2 * UI_SCALE)))
        lbl = tk.Label(row, text=text, font=(THEME["font_family"], fs(7), "bold"),
                       fg=color, bg=THEME["card_bg"])
        lbl.pack(side="left")
        if right_widget_factory:
            right_widget_factory(row)
        return lbl

    def auto_fit_window(self):
        """Pencere boyutunu ekrandaki içeriğe tam uyacak şekilde dinamik boyutlandırır."""
        self.root.update_idletasks()

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # En geniş/büyük sekme olan Karşılaştırma ve Maliyet ekranını kapsayan standart, sabit ölçü:
        standard_w = int(1060 * UI_SCALE)
        standard_h = int(770 * UI_SCALE)

        max_allowed_w = max(800, screen_w - 40)
        max_allowed_h = max(550, screen_h - 70)

        target_w = min(standard_w, max_allowed_w)
        target_h = min(standard_h, max_allowed_h)

        cur_w = self.root.winfo_width()
        cur_h = self.root.winfo_height()

        # Boyut farkı varsa (10 px üzeri) yeniden konumlandır, aksi halde gereksiz geometry çağrısı yapma
        if abs(cur_w - target_w) > 10 or abs(cur_h - target_h) > 10:
            pos_x = max(10, (screen_w - target_w) // 2)
            pos_y = max(10, (screen_h - target_h) // 2)
            self.root.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

        self.root.minsize(min(target_w, int(860 * UI_SCALE)), min(target_h, int(580 * UI_SCALE)))

    def get_hotkey_display_name(self, code: str) -> str:
        """Kısayol kodunun kullanıcı arayüzü gösterim adını döndürür."""
        if not code or code == "none":
            return _t("hotkey_none", "Yok (Devre Dışı)")
        for raw_code, disp in HOTKEY_OPTIONS:
            if raw_code.lower() == str(code).lower():
                if raw_code == "Alt+Shift+R":
                    return _t("hotkey_default_r", "Alt + Shift + R (Varsayılan)")
                if raw_code == "Ctrl+Alt+R":
                    return _t("hotkey_ctrl_alt_r", "Ctrl + Alt + R")
                return disp
        return str(code)

    def get_hotkey_raw_from_disp(self, disp_name: str) -> str:
        """Kullanıcı arayüzünde seçilen gösterim adından ham kısayol kodunu döndürür."""
        if not disp_name or disp_name == _t("hotkey_none", "Yok (Devre Dışı)"):
            return "none"
        for raw_code, disp in HOTKEY_OPTIONS:
            if disp == disp_name:
                return raw_code
        if _t("hotkey_default_r", "Alt + Shift + R (Varsayılan)") in disp_name:
            return "Alt+Shift+R"
        if _t("hotkey_ctrl_alt_r", "Ctrl + Alt + R") in disp_name:
            return "Ctrl+Alt+R"
        return str(disp_name).replace(" ", "")

    # --- OSD Canlı Test Ekranı ---
    def toggle_test_screen(self):
        if hasattr(self, "test_win") and self.test_win and self.test_win.winfo_exists():
            self.test_win.destroy()
            self.test_win = None
            if hasattr(self, "btn_test_screen"):
                self.btn_test_screen.config(text="🎮 OSD Test Ekranı", bg=THEME["btn_bg"])
        else:
            self.open_test_screen()

    def open_test_screen(self):
        if hasattr(self, "test_win") and self.test_win and self.test_win.winfo_exists():
            self.test_win.lift()
            self.test_win.focus_force()
            return

        tw = tk.Toplevel(self.root)
        self.apply_window_icon(tw)
        tw.title(_t("test_screen_title", "🎮 WattCost • Oyun İçi OSD Canlı Test Ekranı"))
        tw.configure(bg="#05070D")
        tw.geometry("920x540")
        tw.minsize(640, 400)

        top_bar = tk.Frame(tw, bg="#0E121E", highlightbackground="#1E263D", highlightthickness=1)
        top_bar.pack(fill="x", padx=10, pady=(10, 5))

        f_hdr_left = tk.Frame(top_bar, bg="#0E121E")
        f_hdr_left.pack(side="left", padx=10, pady=6)
        tk.Label(f_hdr_left, text=_t("test_screen_hdr", "🎮 OYUN İÇİ OSD TEST SİMÜLATÖRÜ"), font=(THEME["font_family"], 9, "bold"),
                 fg=THEME["accent_cyan"], bg="#0E121E").pack(side="left")
        tk.Label(f_hdr_left, text=_t("test_screen_sub", " • Oyun açmadan göstergenin canlı duruşunu test edin"), font=(THEME["font_family"], 7),
                 fg=THEME["text_muted"], bg="#0E121E").pack(side="left", padx=(4, 0))

        f_corners = tk.Frame(top_bar, bg="#0E121E")
        f_corners.pack(side="right", padx=10)

        def set_corner_test(pos):
            self.config["rtss_position"] = pos
            if hasattr(self, "rtss_pos_var"):
                self.rtss_pos_var.set(pos)
            if hasattr(self, "opt_rtss_pos"):
                pos_menu_map = {
                    "top_left": _t("osd_pos_top_left", "↖ Sol Üst (Varsayılan)"),
                    "top_right": _t("osd_pos_top_right", "↗ Sağ Üst"),
                    "bottom_left": _t("osd_pos_bottom_left", "↙ Sol Alt"),
                    "bottom_right": _t("osd_pos_bottom_right", "↘ Sağ Alt")
                }
                self.opt_rtss_pos.set(pos_menu_map.get(pos, _t("osd_pos_top_left", "↖ Sol Üst (Varsayılan)")))
            self.save_config()
            self.on_rtss_change()
            self.update_test_screen()

        self.make_btn(f_corners, _t("osd_pos_top_left_short", "↖ Sol Üst"), lambda: set_corner_test("top_left"), padx=6).pack(side="left", padx=2)
        self.make_btn(f_corners, _t("osd_pos_top_right_short", "↗ Sağ Üst"), lambda: set_corner_test("top_right"), padx=6).pack(side="left", padx=2)
        self.make_btn(f_corners, _t("osd_pos_bottom_left_short", "↙ Sol Alt"), lambda: set_corner_test("bottom_left"), padx=6).pack(side="left", padx=2)
        self.make_btn(f_corners, _t("osd_pos_bottom_right_short", "↘ Sağ Alt"), lambda: set_corner_test("bottom_right"), padx=6).pack(side="left", padx=2)

        game_stage = tk.Frame(tw, bg="#070A12", highlightbackground="#1A233A", highlightthickness=1)
        game_stage.pack(fill="both", expand=True, padx=10, pady=5)

        lbl_bg_game = tk.Label(game_stage,
                               text=_t("test_screen_desc",
                                       "[ 3D OYUN EKRANI SİMÜLATÖRÜ ]\n\n"
                                       "Aşağıdaki/Yukarıdaki OSD değerleri seçtiğiniz konuma göre anlık render edilmektedir.\n"
                                       "Ayarlar panelinden yaptığınız renk, dikey liste veya metrik değişiklikleri burada canlı güncellenir."),
                               font=(THEME["font_family"], 9, "bold"), fg="#162038", bg="#070A12", justify="center")
        lbl_bg_game.place(relx=0.5, rely=0.5, anchor="center")

        osd_box = tk.Text(game_stage, font=("Consolas", 12, "bold"), bg="#070A12",
                          relief="flat", bd=0, highlightthickness=0, cursor="arrow",
                          height=8, width=50)
        self.test_osd_box = osd_box
        self.test_game_stage = game_stage
        self.test_win = tw

        def _on_close():
            tw.destroy()
            self.test_win = None
            if hasattr(self, "btn_test_screen"):
                self.btn_test_screen.config(text=_t("test_screen_closed_btn", "🎮 OSD Test Ekranı"), bg=THEME["btn_bg"])
        tw.protocol("WM_DELETE_WINDOW", _on_close)

        if hasattr(self, "btn_test_screen"):
            self.btn_test_screen.config(text=_t("test_screen_active_btn", "✓ Test Ekranı Açık"), bg="#1E3A5F")

        self.update_test_screen()

    def update_test_screen(self):
        if not hasattr(self, "test_win") or not self.test_win or not self.test_win.winfo_exists():
            return
        if not hasattr(self, "test_osd_box") or not self.test_osd_box:
            return

        vals = getattr(self, "_last_vals", (185.0, 0.90, 2.45, 0.50, 4.20))
        hw = getattr(self, "_last_hw", None)
        txt = self.get_rtss_text(vals[0], vals[1], vals[2], vals[3], vals[4], hw_stats=hw)

        self.test_osd_box.config(state="normal")
        self.test_osd_box.delete("1.0", "end")

        if not txt or not self.config.get("rtss_enabled", True):
            self.test_osd_box.insert("end", _t("test_screen_osd_disabled", "(OSD Göstergesi Kapalı)"), "dim")
            self.test_osd_box.tag_config("dim", foreground=THEME["text_muted"])
            self.test_osd_box.config(state="disabled")
            return

        live_fps = self.rtss.get_active_fps() if hasattr(self, 'rtss') and self.rtss else 0.0
        fps_disp = f"{int(live_fps)}" if live_fps > 0 else "144"

        pos = self.config.get("rtss_position", "top_right")

        lines = txt.split("\n")
        line_count = len(lines)
        max_line_len = 0

        for l_idx, line in enumerate(lines):
            line_str = re.sub(r'<[PLA][^>]*>', '', line)
            line_str = line_str.replace("<FR>", fps_disp)

            # Baş ve sondaki RTSS köşe boşluk satırlarını önizleme kutusunda atla
            clean_check = re.sub(r'<[^>]*>', '', line_str).strip()
            if not clean_check and (l_idx == 0 or l_idx == line_count - 1):
                continue

            tokens = re.split(r'(<C=[0-9A-Fa-f]{6}>|<C>)', line_str)
            cur_color = "#00E5FF"
            clean_line_len = 0

            for tok in tokens:
                if not tok:
                    continue
                if tok.startswith("<C=") and tok.endswith(">"):
                    cur_color = "#" + tok[3:-1]
                elif tok == "<C>":
                    cur_color = "#FFFFFF"
                else:
                    tok_clean = re.sub(r'<[SCPAL][^>]*>', '', tok)
                    if tok_clean:
                        tag_id = f"col_{cur_color.replace('#', '')}"
                        self.test_osd_box.tag_config(tag_id, foreground=cur_color)
                        self.test_osd_box.insert("end", tok_clean, tag_id)
                        clean_line_len += len(tok_clean)

            max_line_len = max(max_line_len, clean_line_len)
            if l_idx < line_count - 1:
                self.test_osd_box.insert("end", "\n")

        self.test_osd_box.config(state="disabled", height=max(2, line_count), width=max(25, max_line_len + 2))

        if pos == "top_left":
            self.test_osd_box.place(relx=0.03, rely=0.04, anchor="nw")
            self.test_osd_box.tag_configure("align", justify="left")
        elif pos == "top_right":
            self.test_osd_box.place(relx=0.97, rely=0.04, anchor="ne")
            self.test_osd_box.tag_configure("align", justify="right")
        elif pos == "bottom_left":
            self.test_osd_box.place(relx=0.03, rely=0.96, anchor="sw")
            self.test_osd_box.tag_configure("align", justify="left")
        elif pos == "bottom_right":
            self.test_osd_box.place(relx=0.97, rely=0.96, anchor="se")
            self.test_osd_box.tag_configure("align", justify="right")

    # --- Genel Ayarlar Penceresi ---
    def open_settings(self):
        f_font = THEME["font_family"]
        top = tk.Toplevel(self.root)
        self.apply_window_icon(top)
        top.title(_t("settings_title", "⚙ TARİFE VE SİSTEM AYARLARI"))
        # Geniş Yatay Dikdörtgen (Dashboard Oranı) - 2 Kolonlu Yayvan Düzen
        screen_w = top.winfo_screenwidth()
        screen_h = top.winfo_screenheight()
        target_w = min(int(screen_w * 0.96), max(860, int(920 * UI_SCALE)))
        target_h = min(int(screen_h * 0.94), max(620, int(660 * UI_SCALE)))
        pos_x = max(10, (screen_w - target_w) // 2)
        pos_y = max(10, (screen_h - target_h) // 2)

        top.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
        top.minsize(int(820 * UI_SCALE), int(560 * UI_SCALE))
        top.configure(bg=THEME["card_bg"])
        top.resizable(True, True)
        top.transient(self.root)
        top.grab_set()

        # Sabit Üst Başlık Barı (Başlık, Otomatik Kayıt & CLI Rehberi Butonu)
        f_top_header = tk.Frame(top, bg=THEME["card_bg"])
        f_top_header.pack(fill="x", padx=18, pady=(8, 4))

        f_header_left = tk.Frame(f_top_header, bg=THEME["card_bg"])
        f_header_left.pack(side="left", fill="y")

        tk.Label(f_header_left, text=f"{_t('settings_title', '⚙ TARİFE VE SİSTEM AYARLARI')} (v{APP_VERSION})", font=(f_font, 10, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w")
        lbl_autosave = tk.Label(f_header_left, text=_t("settings_autosave_note", "⚡ Tüm ayarlar anında otomatik kaydedilir"), font=(f_font, 7, "italic"),
                                fg=THEME["accent_green"], bg=THEME["card_bg"])
        lbl_autosave.pack(anchor="w")

        btn_top_cli = self.make_btn(
            f_top_header,
            _t("settings_btn_cli_guide", "💻 CLI Komut Kılavuzu & Terminal"),
            self.open_cli_guide,
            bg=THEME["card_inner"],
            fg=THEME["accent_cyan"],
            bold=True,
            tooltip=_t("settings_btn_cli_guide_tip", "WattCost'u komut satırından (CMD / PowerShell / Kısayollar) yönetmek için tüm CLI komutlarını ve parametreleri görüntüler")
        )
        btn_top_cli.pack(side="right", padx=(4, 0), pady=2)

        # 2 Kolonlu Yayvan Ana Gövde (Kaydırma Çubuğu Olmadan Tam Sığar)
        f_body = tk.Frame(top, bg=THEME["card_bg"])
        f_body.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        f_col_left = tk.Frame(f_body, bg=THEME["card_bg"])
        f_col_left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # İki kolon arasındaki zarif dikey ayırıcı çizgi
        tk.Frame(f_body, bg=THEME["card_border"], width=1).pack(side="left", fill="y", pady=4)

        f_col_right = tk.Frame(f_body, bg=THEME["card_bg"])
        f_col_right.pack(side="right", fill="both", expand=True, padx=(6, 0))

        entries = {}

        # ========================================================
        # SOL KOLON: TARİFE, ELEKTRİK BİRİM FİYATI & HARİCİ CİHAZLAR
        # ========================================================

        # --- 1. ELEKTRİK TARİFESİ KADEMESİ ---
        f_tier = tk.Frame(f_col_left, bg=THEME["card_bg"])
        f_tier.pack(fill="x", padx=6, pady=(2, 2))
        tk.Label(f_tier, text=_t("settings_tariff_tier_title", "⚡ ELEKTRİK TARİFESİ KADEMESİ:"), font=(f_font, 8, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w", pady=(0, 1))

        cur_price = float(self.config.get("kwh_price_tl", 4.86))
        init_tier = "high" if abs(cur_price - 4.86) < 0.05 else ("low" if abs(cur_price - 3.24) < 0.05 else "custom")
        tariff_var = tk.StringVar(value=init_tier)

        def on_tariff_change():
            sel = tariff_var.get()
            if "kwh_price_tl" in entries:
                if sel == "low":
                    entries["kwh_price_tl"].delete(0, "end")
                    entries["kwh_price_tl"].insert(0, "3.24")
                elif sel == "high":
                    entries["kwh_price_tl"].delete(0, "end")
                    entries["kwh_price_tl"].insert(0, "4.86")
            auto_save()

        tariff_tooltips = {
            "low": _t("settings_tariff_low_tip", "Günlük 8 kWh ve altı tüketimler için standart mesken düşük kademe birim fiyatı (3,24 TL)"),
            "high": _t("settings_tariff_high_tip", "Günlük 8 kWh aşımı sonrası uygulanan mesken yüksek kademe birim fiyatı (4,86 TL)"),
            "custom": _t("settings_tariff_custom_tip", "Birim elektrik fiyatını faturanıza göre manuel olarak girin")
        }

        for code, label_txt, col in [
            ("low",  _t("settings_tariff_low", "🟢 Düşük Kademe: 3,24 TL/kWh (Günlük ≤ 8 kWh)"), THEME["accent_green"]),
            ("high", _t("settings_tariff_high", "🟡 Yüksek Kademe: 4,86 TL/kWh (Günlük > 8 kWh)"), THEME["accent_amber"]),
            ("custom", _t("settings_tariff_custom", "⚙️ Özel Tarife (Manuel fiyat girişi)"), THEME["text_secondary"])
        ]:
            rb = tk.Radiobutton(f_tier, text=label_txt, variable=tariff_var, value=code, command=on_tariff_change,
                                font=(f_font, 7, "bold"), bg=THEME["card_bg"], fg=col,
                                activebackground=THEME["card_bg"], activeforeground=col,
                                selectcolor=THEME["card_inner"], bd=0, highlightthickness=0, cursor="hand2")
            rb.pack(anchor="w", pady=1)
            self.add_tooltip(rb, tariff_tooltips.get(code, ""))

        f_form = tk.Frame(f_col_left, bg=THEME["card_bg"])
        f_form.pack(fill="x", padx=6, pady=(1, 2))

        f_price_row = tk.Frame(f_form, bg=THEME["card_bg"])
        f_price_row.pack(fill="x", pady=1)
        tk.Label(f_price_row, text=_t("settings_price_label", "Elektrik Birim Fiyatı (TL / kWh):"), font=(f_font, 8), fg=THEME["text_secondary"],
                 bg=THEME["card_bg"]).pack(anchor="w")
        ent_price = tk.Entry(f_price_row, font=(f_font, 9), bg=THEME["card_inner"], fg=THEME["text_primary"],
                             insertbackground=THEME["text_primary"], relief="flat",
                             highlightbackground=THEME["card_border"], highlightcolor=THEME["accent_cyan"],
                             highlightthickness=1)
        ent_price.insert(0, str(self.config.get("kwh_price_tl", 4.86)))
        ent_price.pack(fill="x", ipady=2)
        self.add_tooltip(ent_price, _t("settings_price_tooltip", "1 kWh elektrik enerjisinin KDV ve dağıtım dahil güncel TL birim fiyatı"))
        entries["kwh_price_tl"] = ent_price

        tk.Frame(f_col_left, bg=THEME["card_border"], height=1).pack(fill="x", padx=6, pady=(6, 3))

        # --- 2. PRİZDEN ÇEKİLEN HARİCİ CİHAZLAR & ÇEVRE BİRİMLERİ ---
        f_devices_sec = tk.Frame(f_col_left, bg=THEME["card_bg"])
        f_devices_sec.pack(fill="x", padx=6, pady=(1, 2))

        tk.Label(f_devices_sec, text=_t("settings_devices_title", "🔌 PRİZDEN ÇEKİLEN HARİCİ CİHAZLAR:"), font=(f_font, 8, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w", pady=(0, 1))
        tk.Label(f_devices_sec, text=_t("settings_devices_desc", "Cihaz adını ve Watt değerini değiştirebilir, istemediklerinizi kapatabilir veya yeni cihaz ekleyebilirsiniz."),
                 font=(f_font, 7), fg=THEME["text_muted"], bg=THEME["card_bg"], wraplength=380, justify="left").pack(anchor="w", pady=(0, 2))

        auto_mon_var = tk.BooleanVar(value=bool(self.config.get("auto_detect_second_monitor", True)))

        def on_auto_monitor_toggle():
            self.config["auto_detect_second_monitor"] = auto_mon_var.get()
            if hasattr(self, 'sync_second_monitor_device'):
                self.sync_second_monitor_device(force=True)
            auto_save()

        self.make_check(f_devices_sec, _t("settings_auto_monitor_chk", "2. monitör bağlıysa otomatik aç"),
                        auto_mon_var, on_auto_monitor_toggle, fg=THEME["text_secondary"], bold=False,
                        tooltip=_t("settings_auto_monitor_tip", "Windows'a ikinci bir monitör bağlandığında 'Samsung 2. Monitör' cihazını listede otomatik işaretler, monitör kapanınca işareti kaldırır")).pack(anchor="w", pady=(0, 2))

        f_dev_container = tk.Frame(f_devices_sec, bg=THEME["card_bg"])
        f_dev_container.pack(fill="x", pady=1)

        dev_widgets = []

        def render_device_rows():
            for w in f_dev_container.winfo_children():
                w.destroy()
            dev_widgets.clear()

            dev_list = getattr(self, 'custom_devices', [])
            for idx, dev in enumerate(dev_list):
                row = tk.Frame(f_dev_container, bg=THEME["card_inner"],
                               highlightbackground=THEME["card_border"], highlightthickness=1)
                row.pack(fill="x", pady=2, padx=1)

                en_var = tk.BooleanVar(value=bool(dev.get("enabled", True)))

                def _on_en_toggle(d=dev, v=en_var):
                    d["enabled"] = v.get()
                    auto_save()

                cb = self.make_check(row, _t("settings_device_show", "Göster"), en_var, _on_en_toggle, fg=THEME["text_secondary"], bg=THEME["card_inner"],
                                     tooltip=_t("settings_device_show_tip", "Bu cihazın ana ekranda ve harici güç listesinde görünürlüğünü açar / kapatır"))
                cb.pack(side="left", padx=(4, 6))

                # İsim Alanı (Kullanıcı adını değiştirebilir)
                ent_name = tk.Entry(row, font=(f_font, 8), bg=THEME["card_bg"], fg=THEME["text_primary"],
                                    insertbackground=THEME["text_primary"], relief="flat",
                                    highlightbackground=THEME["card_border"], highlightcolor=THEME["accent_cyan"],
                                    highlightthickness=1, width=18)
                ent_name.insert(0, str(dev.get("name", "Cihaz")))
                ent_name.pack(side="left", fill="x", expand=True, padx=4, ipady=1)
                self.add_tooltip(ent_name, _t("settings_device_name_tip", "Cihaz adı (Örn: 27 inç Monitör, Wi-Fi 6 Modem, Hoparlör vb.)"))

                # Watt Değeri (Kullanıcı W değerini girebilir)
                ent_watt = tk.Entry(row, font=(f_font, 8, "bold"), bg=THEME["card_bg"], fg=THEME["accent_amber"],
                                    insertbackground=THEME["text_primary"], relief="flat",
                                    highlightbackground=THEME["card_border"], highlightcolor=THEME["accent_cyan"],
                                    highlightthickness=1, width=5, justify="center")
                ent_watt.insert(0, f"{float(dev.get('watt', 0.0)):.1f}")
                ent_watt.pack(side="left", padx=(4, 2), ipady=1)
                self.add_tooltip(ent_watt, _t("settings_device_watt_tip", "Cihazın prizden çektiği ortalama güç (Watt)"))

                tk.Label(row, text="W", font=(f_font, 8, "bold"), fg=THEME["accent_amber"],
                         bg=THEME["card_inner"]).pack(side="left", padx=(0, 4))

                # Silme Butonu
                def _delete_dev(d=dev):
                    if d in self.custom_devices:
                        self.custom_devices.remove(d)
                        render_device_rows()
                        auto_save()

                btn_del = tk.Button(row, text="✕", command=_delete_dev, font=(f_font, 7, "bold"),
                                    bg=THEME["card_inner"], fg=THEME["text_muted"], activebackground=THEME["btn_hover"],
                                    activeforeground=THEME["accent_rose"], relief="flat", bd=0, padx=4, pady=1, cursor="hand2")
                btn_del.pack(side="right", padx=(2, 4))
                self.add_tooltip(btn_del, _t("settings_device_del_tip", "Bu harici cihazı listeden sil"))

                dev_widgets.append((dev, en_var, ent_name, ent_watt))

                ent_name.bind("<KeyRelease>", lambda e: auto_save())
                ent_name.bind("<FocusOut>", lambda e: auto_save())
                ent_watt.bind("<KeyRelease>", lambda e: auto_save())
                ent_watt.bind("<FocusOut>", lambda e: auto_save())

        f_add_box = tk.Frame(f_devices_sec, bg=THEME["card_bg"])
        f_add_box.pack(fill="x", pady=(3, 2))

        def add_new_device():
            import time
            new_id = f"custom_dev_{int(time.time()*1000)}"
            if not hasattr(self, 'custom_devices') or self.custom_devices is None:
                self.custom_devices = []
            self.custom_devices.append({
                "id": new_id,
                "name": f"Yeni Cihaz {len(self.custom_devices)+1}",
                "watt": 15.0,
                "active": True,
                "enabled": True
            })
            render_device_rows()
            auto_save()

        self.make_btn(f_add_box, _t("settings_btn_add_device", "➕ Yeni Cihaz Ekle"), add_new_device,
                      fg=THEME["accent_cyan"], bg=THEME["card_inner"],
                      tooltip=_t("settings_device_add_tip", "Listeye prizden güç çeken yeni bir harici cihaz ekler")).pack(side="left")

        render_device_rows()

        # ========================================================
        # SAĞ KOLON: ZALMAN, TEMA, TRAY, OSD & SİSTEM DAVRANIŞI
        # ========================================================

        # --- 3. ZALMAN ALPHA2 LCD POMPA DESTEĞİ ---
        f_zalman_sec = tk.Frame(f_col_right, bg=THEME["card_bg"])
        f_zalman_sec.pack(fill="x", padx=6, pady=(2, 2))

        tk.Label(f_zalman_sec, text=_t("settings_zalman_title", "❄️ ZALMAN ALPHA2 LCD POMPA DESTEĞİ:"), font=(f_font, 8, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w", pady=(0, 1))

        zalman_on_var = tk.BooleanVar(value=bool(self.config.get("zalman_active", True)))

        def on_zalman_setting_toggle():
            is_on = zalman_on_var.get()
            self.config["zalman_active"] = is_on
            if hasattr(self, 'zalman_active_var'):
                self.zalman_active_var.set(is_on)
            if hasattr(self, 'zalman') and self.zalman:
                self.zalman.set_enabled(is_on)
                if not is_on:
                    self.zalman.set_blank(True)
            if hasattr(self, 'update_zalman_visibility'):
                self.update_zalman_visibility()
            auto_save()

        self.make_check(f_zalman_sec, _t("settings_zalman_enable", "Zalman Alpha2 LCD Pompa Desteğini Aktif Et"), zalman_on_var,
                        on_zalman_setting_toggle, fg=THEME["text_primary"], bold=True,
                        tooltip=_t("zalman_chk_tooltip", "Zalman Alpha2 sıvı soğutma LCD pompasıyla USB üzerinden haberleşmeyi ve ekran kartını kontrol eder")).pack(anchor="w", pady=1)

        tk.Label(f_zalman_sec, text=_t("settings_zalman_note", "* Kapatıldığında Zalman pompası ile USB iletişimi kesilir ve ana ekrandaki kart gizlenir."),
                 font=(f_font, 7, "italic"), fg=THEME["text_muted"], bg=THEME["card_bg"],
                 wraplength=380, justify="left").pack(anchor="w", padx=24, pady=(1, 2))

        tk.Frame(f_col_right, bg=THEME["card_border"], height=1).pack(fill="x", padx=6, pady=(4, 2))

        # --- KULAKLIK BATARYASI (USB + BLUETOOTH, BAGIMSIZ) ---
        f_headset_sec = tk.Frame(f_col_right, bg=THEME["card_bg"])
        f_headset_sec.pack(fill="x", padx=6, pady=(2, 2))

        tk.Label(f_headset_sec, text=_t("settings_headset_title", "🎧 KULAKLIK BATARYASI:"), font=(f_font, 8, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w", pady=(0, 1))

        headset_usb_var = tk.BooleanVar(value=bool(self.config.get("headset_usb_active", True)))
        headset_bt_var = tk.BooleanVar(value=bool(self.config.get("headset_bt_active", True)))

        def on_headset_usb_toggle():
            if hasattr(self, 'apply_headset_enabled'):
                self.apply_headset_enabled("usb", headset_usb_var.get())
            auto_save()

        def on_headset_bt_toggle():
            if hasattr(self, 'apply_headset_enabled'):
                self.apply_headset_enabled("bt", headset_bt_var.get())
            auto_save()

        self.make_check(f_headset_sec, _t("settings_headset_usb", "SteelSeries USB kulaklık (HID)"),
                        headset_usb_var, on_headset_usb_toggle, fg=THEME["text_primary"], bold=True,
                        tooltip=_t("settings_headset_usb_tip", "SteelSeries Arctis 7 / Pro bataryasını USB HID üzerinden okur; harici araç gerekmez")).pack(anchor="w", pady=1)

        self.make_check(f_headset_sec, _t("settings_headset_bt", "Bluetooth kulaklık (Windows HFP)"),
                        headset_bt_var, on_headset_bt_toggle, fg=THEME["text_primary"], bold=True,
                        tooltip=_t("settings_headset_bt_tip", "Bağlı Bluetooth kulaklığın bataryasını Windows'un HFP cihaz özelliğinden okur")).pack(anchor="w", pady=1)

        tk.Label(f_headset_sec, text=_t("settings_headset_note_dual", "* İki kaynak bağımsızdır: yalnızca sahip olduğunuz türü açık bırakın. İkisi de kapalıysa hiç okuma yapılmaz."),
                 font=(f_font, 7, "italic"), fg=THEME["text_muted"], bg=THEME["card_bg"],
                 wraplength=380, justify="left").pack(anchor="w", padx=24, pady=(1, 2))

        tk.Frame(f_col_right, bg=THEME["card_border"], height=1).pack(fill="x", padx=6, pady=(4, 2))
        from config_manager import AVAILABLE_THEMES
        f_theme_sec = tk.Frame(f_col_right, bg=THEME["card_bg"])
        f_theme_sec.pack(fill="x", padx=6, pady=1)
        tk.Label(f_theme_sec, text=_t("settings_theme_title", "🎨 Arayüz Teması:"), font=(f_font, 8, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w")

        is_tr = (self.lang_mgr.active_language_code == "tr") if hasattr(self, 'lang_mgr') else True
        theme_names = {}
        for k, v in AVAILABLE_THEMES.items():
            theme_names[k] = v["name_tr"] if is_tr else v["name_en"]
        rev_theme_map = {v: k for k, v in theme_names.items()}
        cur_th_key = self.config.get("theme", "obsidian_cyber")
        cur_th_name = theme_names.get(cur_th_key, theme_names.get("obsidian_cyber"))

        opt_theme = ttk.Combobox(f_theme_sec, values=list(theme_names.values()), state="readonly", font=(f_font, 8))
        opt_theme.set(cur_th_name)
        opt_theme.pack(fill="x", pady=(1, 0))
        self.add_tooltip(opt_theme, _t("settings_theme_tip", "Uygulama pencereleri ve kartlar için 8 profesyonel renk paletinden birini seçin (RTSS OSD renkleri sabit kalır)"))

        def _on_theme_change(event=None):
            sel_name = opt_theme.get()
            th_code = rev_theme_map.get(sel_name, "obsidian_cyber")
            if hasattr(self, 'apply_theme_to_ui'):
                self.apply_theme_to_ui(th_code)
            else:
                from config_manager import set_active_theme
                set_active_theme(th_code)
                self.config["theme"] = th_code
                self.save_config()
            top.configure(bg=THEME["card_bg"])
            f_top_header.configure(bg=THEME["card_bg"])
            f_body.configure(bg=THEME["card_bg"])
            f_col_left.configure(bg=THEME["card_bg"])
            f_col_right.configure(bg=THEME["card_bg"])
            auto_save()

        opt_theme.bind("<<ComboboxSelected>>", _on_theme_change)

        tk.Frame(f_col_right, bg=THEME["card_border"], height=1).pack(fill="x", padx=6, pady=(4, 2))

        # --- 4. SİSTEM TEPSİSİ (TRAY) AYARLARI ---
        f_tray_mode = tk.Frame(f_col_right, bg=THEME["card_bg"])
        f_tray_mode.pack(fill="x", padx=6, pady=1)
        tk.Label(f_tray_mode, text=_t("settings_tray_display_title", "📌 Saatteki Simge Göstergesi (Tray):"), font=(f_font, 8, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w")

        tray_mode_map = {
            "power_w":   _t("tray_mode_power_w", "Prizden Toplam Güç (Watt)"),
            "dual_temp": _t("tray_mode_dual_temp", "CPU & GPU Sıcaklığı (°C)"),
            "cpu_uti":   _t("tray_mode_cpu_uti", "CPU Kullanımı (%)"),
            "gpu_uti":   _t("tray_mode_gpu_uti", "GPU Kullanımı (%)"),
            "cpu_temp":  _t("tray_mode_cpu_temp", "CPU Sıcaklığı (°C)"),
            "gpu_temp":  _t("tray_mode_gpu_temp", "GPU Sıcaklığı (°C)"),
            "hourly_tl": _t("tray_mode_hourly_tl", "Saatlik Harcama (TL/sa)"),
            "logo":      _t("tray_mode_logo", "Sabit WattCost Logosu")
        }
        rev_tray_map = {v: k for k, v in tray_mode_map.items()}
        cur_mode_key = self.config.get("tray_mode") or "power_w"
        current_display_name = tray_mode_map.get(cur_mode_key, _t("tray_mode_power_w", "Prizden Toplam Güç (Watt)"))

        opt_tray = ttk.Combobox(f_tray_mode, values=list(tray_mode_map.values()), state="readonly", font=(f_font, 8))
        opt_tray.set(current_display_name)
        opt_tray.pack(fill="x", pady=(1, 0))
        self.add_tooltip(opt_tray, _t("settings_tray_mode_tip", "Windows görev çubuğu saat yanında simge olarak hangi canlı değerin gösterileceğini seçin"))

        # Yan yana kompakt Kutu Rengi ve Yazı Rengi seçimi
        f_tray_colors = tk.Frame(f_col_right, bg=THEME["card_bg"])
        f_tray_colors.pack(fill="x", padx=6, pady=1)

        f_tray_bg = tk.Frame(f_tray_colors, bg=THEME["card_bg"])
        f_tray_bg.pack(side="left", fill="x", expand=True, padx=(0, 3))
        tk.Label(f_tray_bg, text=_t("settings_tray_bg_title", "🎨 Simge Arka Planı:"), font=(f_font, 7, "bold"),
                 fg=THEME["accent_amber"], bg=THEME["card_bg"]).pack(anchor="w")

        tray_bg_map = {
            "transparent": _t("tray_bg_transparent", "Saydam (Sadece Değer)"),
            "dark":        _t("tray_bg_dark", "Siyah Kutu"),
            "cyan":        _t("tray_bg_cyan", "Cyan Kutu"),
            "green":       _t("tray_bg_green", "Yeşil Kutu"),
            "rose":        _t("tray_bg_rose", "Kırmızı Kutu"),
            "amber":       _t("tray_bg_amber", "Sarı Kutu"),
            "white":       _t("tray_bg_white", "Beyaz Kutu")
        }
        rev_bg_map = {v: k for k, v in tray_bg_map.items()}
        cur_bg_key = self.config.get("tray_bg") or "transparent"
        cur_bg_name = tray_bg_map.get(cur_bg_key, _t("tray_bg_transparent", "Saydam (Sadece Değer)"))

        opt_bg = ttk.Combobox(f_tray_bg, values=list(tray_bg_map.values()), state="readonly", font=(f_font, 8))
        opt_bg.set(cur_bg_name)
        opt_bg.pack(fill="x", pady=(1, 0))

        f_tray_fg = tk.Frame(f_tray_colors, bg=THEME["card_bg"])
        f_tray_fg.pack(side="right", fill="x", expand=True, padx=(3, 0))
        tk.Label(f_tray_fg, text=_t("settings_tray_fg_title", "✏️ Yazı Rengi:"), font=(f_font, 7, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w")

        tray_fg_map = {
            "auto":   _t("tray_fg_auto", "Dinamik"),
            "cyan":   _t("tray_fg_cyan", "Cyan"),
            "green":  _t("tray_fg_green", "Yeşil"),
            "amber":  _t("tray_fg_amber", "Sarı"),
            "rose":   _t("tray_fg_rose", "Kırmızı"),
            "white":  _t("tray_fg_white", "Beyaz"),
            "black":  _t("tray_fg_black", "Siyah"),
            "purple": _t("tray_fg_purple", "Mor")
        }
        rev_fg_map = {v: k for k, v in tray_fg_map.items()}
        cur_fg_key = self.config.get("tray_fg") or "auto"
        cur_fg_name = tray_fg_map.get(cur_fg_key, _t("tray_fg_auto", "Dinamik"))

        opt_fg = ttk.Combobox(f_tray_fg, values=list(tray_fg_map.values()), state="readonly", font=(f_font, 8))
        opt_fg.set(cur_fg_name)
        opt_fg.pack(fill="x", pady=(1, 0))

        # Saatteki Simge Yazı Tipi (Tray Font)
        f_tray_font = tk.Frame(f_col_right, bg=THEME["card_bg"])
        f_tray_font.pack(fill="x", padx=6, pady=1)
        tk.Label(f_tray_font, text=_t("settings_tray_font_title", "🔤 Saatteki Simge Yazı Tipi (Font):"), font=(f_font, 8, "bold"),
                 fg=THEME["accent_purple"], bg=THEME["card_bg"]).pack(anchor="w")

        tray_font_map = {
            "bahnschrift": _t("tray_font_bahnschrift", "Bahnschrift (Kompakt & Net - Varsayılan)"),
            "segoe":       _t("tray_font_segoe", "Segoe UI (Modern & İnce)"),
            "arial":       _t("tray_font_arial", "Arial (Sade)"),
            "consola":     _t("tray_font_consola", "Consolas (Dijital Monospace)"),
            "impact":      _t("tray_font_impact", "Impact (Kalın & Dolgun)")
        }
        rev_font_map = {v: k for k, v in tray_font_map.items()}
        cur_font_key = self.config.get("tray_font") or "bahnschrift"
        cur_font_name = tray_font_map.get(cur_font_key, _t("tray_font_bahnschrift", "Bahnschrift (Kompakt & Net - Varsayılan)"))

        opt_font = ttk.Combobox(f_tray_font, values=list(tray_font_map.values()), state="readonly", font=(f_font, 8))
        opt_font.set(cur_font_name)
        opt_font.pack(fill="x", pady=(1, 0))

        # Saatteki Simge Yazı Boyutu (Tray Size) & Yüke Göre Renk Eşikleri
        f_tray_extra = tk.Frame(f_col_right, bg=THEME["card_bg"])
        f_tray_extra.pack(fill="x", padx=6, pady=1)

        f_size_box = tk.Frame(f_tray_extra, bg=THEME["card_bg"])
        f_size_box.pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Label(f_size_box, text=_t("settings_tray_size_title", "📏 Yazı Boyutu:"), font=(f_font, 7, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w")

        tray_size_map = {
            "small":  _t("tray_size_small", "Kompakt (1.0x)"),
            "normal": _t("tray_size_normal", "Standart / Net (1.45x)"),
            "large":  _t("tray_size_large", "Büyük (1.75x)"),
            "xlarge": _t("tray_size_xlarge", "Ekstra Büyük (2.10x)"),
            "max":    _t("tray_size_max", "Maksimum / Dev (2.50x - Varsayılan)")
        }
        rev_size_map = {v: k for k, v in tray_size_map.items()}
        cur_sz_key = self.config.get("tray_font_size") or "max"
        cur_size_name = tray_size_map.get(cur_sz_key, _t("tray_size_max", "Maksimum / Dev (2.50x - Varsayılan)"))
        opt_size = ttk.Combobox(f_size_box, values=list(tray_size_map.values()), state="readonly", font=(f_font, 8))
        opt_size.set(cur_size_name)
        opt_size.pack(fill="x", pady=(1, 0))

        # Renk Eşikleri (Sarı / Kırmızı Watt sınırları)
        f_thresh_box = tk.Frame(f_tray_extra, bg=THEME["card_bg"])
        f_thresh_box.pack(side="right", fill="x", expand=True)
        tk.Label(f_thresh_box, text=_t("settings_tray_load_thresh_title", "⚡ Renk Eşikleri (W):"), font=(f_font, 7, "bold"),
                 fg=THEME.get("accent_amber", "#F59E0B"), bg=THEME["card_bg"]).pack(anchor="w")

        f_thresh_inputs = tk.Frame(f_thresh_box, bg=THEME["card_bg"])
        f_thresh_inputs.pack(fill="x", pady=(1, 0))

        tk.Label(f_thresh_inputs, text="🟡", font=(f_font, 7), bg=THEME["card_bg"]).pack(side="left")
        ent_tray_warn = tk.Entry(f_thresh_inputs, font=(f_font, 8), bg=THEME["card_inner"], fg=THEME["text_primary"],
                                 insertbackground=THEME["text_primary"], relief="flat", width=5, justify="center")
        ent_tray_warn.insert(0, str(int(self.config.get("tray_watt_warn", 250))))
        ent_tray_warn.pack(side="left", padx=(1, 4))

        tk.Label(f_thresh_inputs, text="🔴", font=(f_font, 7), bg=THEME["card_bg"]).pack(side="left")
        ent_tray_crit = tk.Entry(f_thresh_inputs, font=(f_font, 8), bg=THEME["card_inner"], fg=THEME["text_primary"],
                                 insertbackground=THEME["text_primary"], relief="flat", width=5, justify="center")
        ent_tray_crit.insert(0, str(int(self.config.get("tray_watt_crit", 450))))
        ent_tray_crit.pack(side="left", padx=(1, 0))

        tk.Frame(f_col_right, bg=THEME["card_border"], height=1).pack(fill="x", padx=6, pady=(4, 2))

        # --- 5. OYUN İÇİ GÖSTERGE (RTSS) AYARLARI ---
        pos_settings_map = {
            "top_right": _t("osd_pos_top_right", "↗ Sağ Üst (Varsayılan)"),
            "top_left": _t("osd_pos_top_left", "↖ Sol Üst"),
            "bottom_left": _t("osd_pos_bottom_left", "↙ Sol Alt"),
            "bottom_right": _t("osd_pos_bottom_right", "↘ Sağ Alt")
        }
        rev_pos_settings_map = {v: k for k, v in pos_settings_map.items()}

        f_rtss_row = tk.Frame(f_col_right, bg=THEME["card_bg"])
        f_rtss_row.pack(fill="x", padx=6, pady=1)

        f_pos_cfg = tk.Frame(f_rtss_row, bg=THEME["card_bg"])
        f_pos_cfg.pack(side="left", fill="x", expand=True, padx=(0, 3))
        tk.Label(f_pos_cfg, text=_t("settings_lbl_osd_pos", "🎮 OSD Konumu:"), font=(f_font, 7, "bold"), fg=THEME["accent_cyan"],
                 bg=THEME["card_bg"]).pack(anchor="w")
        opt_osd_pos = ttk.Combobox(f_pos_cfg, values=list(pos_settings_map.values()), state="readonly",
                                   font=(f_font, 8))
        opt_osd_pos.set(pos_settings_map.get(self.config.get("rtss_position", "top_right"), _t("osd_pos_top_right", "↗ Sağ Üst (Varsayılan)")))
        opt_osd_pos.pack(fill="x", pady=(1, 0))

        f_hk_cfg = tk.Frame(f_rtss_row, bg=THEME["card_bg"])
        f_hk_cfg.pack(side="right", fill="x", expand=True, padx=(3, 0))
        tk.Label(f_hk_cfg, text=_t("settings_lbl_osd_hk", "⌨️ OSD Kısayolu:"), font=(f_font, 7, "bold"), fg=THEME["accent_amber"],
                 bg=THEME["card_bg"]).pack(anchor="w")
        cur_hk_code = self.config.get("rtss_hotkey", "Alt+Shift+R")
        cur_hk_disp = self.get_hotkey_display_name(cur_hk_code)
        hk_values = [opt[1] for opt in HOTKEY_OPTIONS]
        if cur_hk_disp not in hk_values:
            hk_values.insert(0, cur_hk_disp)
        opt_osd_hk = ttk.Combobox(f_hk_cfg, values=hk_values, state="readonly",
                                   font=(f_font, 8))
        opt_osd_hk.set(cur_hk_disp)
        opt_osd_hk.pack(fill="x", pady=(1, 0))

        tk.Frame(f_col_right, bg=THEME["card_border"], height=1).pack(fill="x", padx=6, pady=(4, 2))

        # --- 6. SİSTEM DAVRANIŞI ---
        autostart_var = tk.BooleanVar(value=WindowsAutoStart.is_enabled())
        close_to_tray_var = tk.BooleanVar(value=self.config.get("close_to_tray", True))
        toast_notify_var = tk.BooleanVar(value=self.config.get("power_plan_toast", True))
        power_sound_var = tk.BooleanVar(value=self.config.get("power_plan_sound", True))
        smart_sound_var = tk.BooleanVar(value=self.config.get("smart_switch_sound", True))
        smart_toast_var = tk.BooleanVar(value=self.config.get("smart_switch_toast", True))

        def auto_save(*args):
            for k in entries:
                raw_val = entries[k].get().strip().replace(',', '.')
                try:
                    self.config[k] = float(raw_val)
                except ValueError:
                    pass

            # Harici Cihazlar Listesini Güncelle
            for d, v_en, ent_n, ent_w in dev_widgets:
                d["enabled"] = v_en.get()
                name_val = ent_n.get().strip()
                if name_val:
                    d["name"] = name_val
                w_val = ent_w.get().strip().replace(',', '.')
                try:
                    d["watt"] = max(0.0, float(w_val))
                except ValueError:
                    pass

            self.config["zalman_active"] = zalman_on_var.get()
            if hasattr(self, 'zalman_active_var'):
                self.zalman_active_var.set(zalman_on_var.get())
            if hasattr(self, 'update_zalman_visibility'):
                self.update_zalman_visibility()

            self.config["close_to_tray"] = close_to_tray_var.get()
            self.config["power_plan_toast"] = toast_notify_var.get()
            self.config["power_plan_sound"] = power_sound_var.get()
            self.config["smart_switch_sound"] = smart_sound_var.get()
            self.config["smart_switch_toast"] = smart_toast_var.get()
            if hasattr(self, 'smart_switch_sound_var'):
                self.smart_switch_sound_var.set(smart_sound_var.get())
            if hasattr(self, 'smart_switch_toast_var'):
                self.smart_switch_toast_var.set(smart_toast_var.get())

            old_mode = self.config.get("tray_mode")
            old_font = self.config.get("tray_font")
            old_size = self.config.get("tray_font_size")
            old_bg = self.config.get("tray_bg")
            old_fg = self.config.get("tray_fg")
            self.config["tariff_tier"] = tariff_var.get()
            self.config["tray_mode"] = rev_tray_map.get(opt_tray.get(), self.config.get("tray_mode", "power_w"))
            self.config["tray_font"] = rev_font_map.get(opt_font.get(), self.config.get("tray_font", "bahnschrift"))
            self.config["tray_font_size"] = rev_size_map.get(opt_size.get(), self.config.get("tray_font_size", "normal"))
            self.config["tray_bg"] = rev_bg_map.get(opt_bg.get(), self.config.get("tray_bg", "transparent"))
            self.config["tray_fg"] = rev_fg_map.get(opt_fg.get(), self.config.get("tray_fg", "auto"))

            try:
                self.config["tray_watt_warn"] = max(10.0, float(ent_tray_warn.get().replace(",", ".")))
            except (ValueError, TypeError):
                pass

            try:
                self.config["tray_watt_crit"] = max(self.config.get("tray_watt_warn", 250.0), float(ent_tray_crit.get().replace(",", ".")))
            except (ValueError, TypeError):
                pass

            # Simge, yazı tipi veya eşik değişikliklerinin derhal yansıması için önbellekleri sıfırla
            if hasattr(self, '_clear_tray_caches'):
                self._clear_tray_caches()
            elif hasattr(self, '_font_cache'):
                self._font_cache.clear()

            sel_pos = rev_pos_settings_map.get(opt_osd_pos.get(), "top_left")
            if opt_osd_hk.get() == cur_hk_disp:
                sel_hk = cur_hk_code
            else:
                sel_hk = self.get_hotkey_raw_from_disp(opt_osd_hk.get())
            self.config["rtss_position"] = sel_pos
            self.config["rtss_hotkey"] = sel_hk

            if hasattr(self, "rtss_pos_var"):
                self.rtss_pos_var.set(sel_pos)
            if hasattr(self, "opt_rtss_pos"):
                self.opt_rtss_pos.set(opt_osd_pos.get())
            if hasattr(self, "opt_rtss_hotkey"):
                self.opt_rtss_hotkey.set(opt_osd_hk.get())
            if hasattr(self, "hotkey_mgr") and self.hotkey_mgr:
                self.hotkey_mgr.start(sel_hk)

            self.save_config()
            WindowsAutoStart.set_enabled(autostart_var.get())
            if hasattr(self, 'refresh_devices_ui'):
                self.refresh_devices_ui()
            if hasattr(self, '_refresh_tray_icon'):
                self._refresh_tray_icon()
            self.on_rtss_change()

            lbl_autosave.config(text=_t("settings_autosave_saved", "✓ Değişiklik anında kaydedildi & uygulandı"), fg=THEME["accent_cyan"])
            top.after(1000, lambda: lbl_autosave.config(text=_t("settings_autosave_note", "⚡ Tüm ayarlar anında otomatik kaydedilir"), fg=THEME["accent_green"]) if top.winfo_exists() else None)

        for ent in list(entries.values()) + [ent_tray_warn, ent_tray_crit]:
            ent.bind("<KeyRelease>", auto_save)
            ent.bind("<FocusOut>", auto_save)

        for cb in (opt_theme, opt_tray, opt_font, opt_size, opt_bg, opt_fg, opt_osd_pos, opt_osd_hk):
            cb.bind("<<ComboboxSelected>>", auto_save)

        f_sys = tk.Frame(f_col_right, bg=THEME["card_bg"])
        f_sys.pack(fill="x", padx=6, pady=1)

        self.make_check(f_sys, _t("settings_autostart_chk", "Windows başlangıcında otomatik başlat"), autostart_var, auto_save,
                        fg=THEME["text_primary"], bold=True,
                        tooltip=_t("settings_autostart_tip", "Bilgisayar her açıldığında WattCost'u arka planda sistem tepsisinde otomatik başlatır")).pack(anchor="w", pady=1)

        self.make_check(f_sys, _t("settings_power_plan_sound_chk", "🔔 Güç planı değişiminde sesli uyarı çal"), power_sound_var, auto_save,
                        fg=THEME["text_primary"], bold=True,
                        tooltip=_t("settings_power_plan_sound_tip", "Sistem güç planı değiştirildiğinde sesli bildirim çalar")).pack(anchor="w", pady=1)

        self.make_check(f_sys, _t("settings_power_plan_toast_chk", "💬 Güç planı değişiminde Toast bildirim göster"), toast_notify_var, auto_save,
                        fg=THEME["text_primary"], bold=True,
                        tooltip=_t("settings_power_plan_toast_tip", "Güç planı değiştirildiğinde ekranın sağ altında açılan bilgi kutusunu gösterir")).pack(anchor="w", pady=1)

        self.make_check(f_sys, _t("smart_sound_lbl", "🔔 Akıllı geçişlerde (SmartSwitch) sesli uyarı"), smart_sound_var, auto_save,
                        fg=THEME["text_primary"], bold=True,
                        tooltip=_t("smart_sound_tip", "Otomasyon kademe değiştirdiğinde sesli bildirim çalar")).pack(anchor="w", pady=1)

        self.make_check(f_sys, _t("smart_toast_lbl", "💬 Akıllı geçişlerde Toast bildirim göster"), smart_toast_var, auto_save,
                        fg=THEME["text_primary"], bold=True,
                        tooltip=_t("smart_toast_tip", "Otomasyon güç planını veya Hz değerini değiştirdiğinde ekranın sağ altında açılan bilgi kutusunu gösterir")).pack(anchor="w", pady=1)

        self.make_check(f_sys, _t("settings_always_on_top_chk", "Pencereyi Her Zaman En Üstte Tut"), getattr(self, 'always_on_top_var', tk.BooleanVar(value=True)), lambda: self.toggle_always_on_top() if hasattr(self, 'toggle_always_on_top') else None,
                        fg=THEME["text_primary"], bold=True).pack(anchor="w", pady=1)

        self.make_check(f_sys, _t("settings_close_to_tray_chk", "Çarpı (X) ile kapatınca tepsiye gizle"), close_to_tray_var, auto_save,
                        tooltip=_t("settings_close_to_tray_tip", "Pencereyi (X) ile kapattığınızda program kapanmaz; arka planda güç ve maliyet takibini sürdürür")).pack(anchor="w", pady=1)
        tk.Label(f_sys, text="* " + _t("settings_close_to_tray_note", "İşaretsizse X'e basınca program tamamen kapanır ve izleme durur."),
                 font=(f_font, 7, "italic"), fg=THEME["text_muted"], bg=THEME["card_bg"],
                 wraplength=380, justify="left").pack(anchor="w", padx=20, pady=(0, 4))

        # CLI Komut Kılavuzu & Terminal Butonu
        tk.Frame(f_sys, bg=THEME["card_border"], height=1).pack(fill="x", pady=(6, 4))
        btn_cli = self.make_btn(
            f_sys,
            _t("settings_btn_cli_guide", "💻 CLI Komut Kılavuzu & Terminal"),
            self.open_cli_guide,
            bg=THEME["card_inner"],
            fg=THEME["accent_cyan"],
            bold=True,
            tooltip=_t("settings_btn_cli_guide_tip", "WattCost'u komut satırından (CMD / PowerShell / Kısayollar) yönetmek için tüm CLI komutlarını ve parametreleri görüntüler")
        )
        btn_cli.pack(fill="x", padx=4, pady=(2, 4), ipady=2)

    # --- CLI Komut Kılavuzu & Terminal Penceresi ---
    def open_cli_guide(self):
        f_font = THEME["font_family"]
        top = tk.Toplevel(self.root)
        self.apply_window_icon(top)
        top.title(_t("cli_modal_title", "💻 WattCost CLI Komut Kılavuzu & Terminal Rehberi"))

        screen_w = top.winfo_screenwidth()
        screen_h = top.winfo_screenheight()
        target_w = min(int(screen_w * 0.95), max(860, int(900 * UI_SCALE)))
        target_h = min(int(screen_h * 0.90), max(580, int(640 * UI_SCALE)))
        pos_x = max(10, (screen_w - target_w) // 2)
        pos_y = max(10, (screen_h - target_h) // 2)

        top.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
        top.minsize(int(780 * UI_SCALE), int(520 * UI_SCALE))
        top.configure(bg=THEME["card_bg"])
        top.transient(self.root)

        # Üst Başlık Barı
        f_top = tk.Frame(top, bg=THEME["card_bg"])
        f_top.pack(fill="x", padx=18, pady=(12, 6))

        tk.Label(f_top, text=_t("cli_guide_header", "WattCost HaYTooL • CLI Komut Arayüzü Kılavuzu"),
                 font=(f_font, 11, "bold"), fg=THEME["accent_cyan"], bg=THEME["card_bg"]).pack(anchor="w")
        tk.Label(f_top, text=_t("cli_guide_sub", "Uygulamayı CMD, PowerShell, Stream Deck, kısayollar veya betiklerle doğrudan komut satırından tam yetkiyle yönetebilirsiniz."),
                 font=(f_font, 8), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(anchor="w", pady=(2, 0))

        # Kaydırılabilir İçerik Alanı (Canvas + Scrollbar)
        f_container = tk.Frame(top, bg=THEME["card_bg"])
        f_container.pack(fill="both", expand=True, padx=14, pady=6)

        canvas = tk.Canvas(f_container, bg=THEME["card_bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(f_container, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg=THEME["card_bg"])

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(xscrollcommand=None, yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Fare tekerleği desteği
        def _on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        top.bind("<MouseWheel>", _on_mousewheel)

        # Komut Grupları Verisi
        cli_commands = [
            {
                "group": _t("cli_group_plans", "⚡ Güç Planları Yönetimi (-p, --plan)"),
                "items": [
                    ("WattCost. HaYTooL.exe --plan 1", _t("cli_desc_plan1", "Kademe 1: Ultra Güç Tasarrufu moduna anında geçer.")),
                    ("WattCost. HaYTooL.exe --plan 2", _t("cli_desc_plan2", "Kademe 2: Dengeli Güç Tasarrufu moduna anında geçer.")),
                    ("WattCost. HaYTooL.exe --plan 3", _t("cli_desc_plan3", "Kademe 3: Yüksek Performans moduna anında geçer.")),
                    ("WattCost. HaYTooL.exe --plan 4", _t("cli_desc_plan4", "Kademe 4: Maksimum Performans moduna anında geçer.")),
                    ('WattCost. HaYTooL.exe --plan "Dengeli"', _t("cli_desc_plan_name", "Plan adına göre kısmi eşleşmeyle güç planını uygular.")),
                    ("WattCost. HaYTooL.exe -p 7a1f0001-c001-4a11-b001-000000000001", _t("cli_desc_plan_guid", "Doğrudan Windows GUID numarası vererek güç planını uygular.")),
                ]
            },
            {
                "group": _t("cli_group_smart", "🤖 Akıllı Geçiş Otomasyonu (-s, --smart)"),
                "items": [
                    ("WattCost. HaYTooL.exe --smart on", _t("cli_desc_smart_on", "4 kademeli dinamik akıllı geçiş otomasyonunu aktif eder.")),
                    ("WattCost. HaYTooL.exe --smart off", _t("cli_desc_smart_off", "Akıllı geçiş otomasyonunu devre dışı bırakır.")),
                    ("WattCost. HaYTooL.exe --smart toggle", _t("cli_desc_smart_toggle", "Akıllı mod açıksa kapatır, kapalıysa açar.")),
                    ("WattCost. HaYTooL.exe --smart status", _t("cli_desc_smart_status", "Akıllı modun açık/kapalı durumunu konsola döker.")),
                ]
            },
            {
                "group": _t("cli_group_list", "📋 Güç Planlarını Listeleme (-l, --list-plans)"),
                "items": [
                    ("WattCost. HaYTooL.exe --list-plans", _t("cli_desc_list_plans", "Sistemdeki tüm kayıtlı güç planlarını, GUID'lerini ve aktif olanı renkli tabloda gösterir.")),
                ]
            },
            {
                "group": _t("cli_group_status", "📊 Canlı Güç & Maliyet Durumu (--status)"),
                "items": [
                    ("WattCost. HaYTooL.exe --status", _t("cli_desc_status", "Aktif güç planını, canlı priz gücünü (W), saatlik maliyeti (TL/sa) ve akıllı mod durumunu özetler.")),
                ]
            },
            {
                "group": _t("cli_group_osd", "🎮 RivaTuner RTSS OSD Göstergesi (--osd)"),
                "items": [
                    ("WattCost. HaYTooL.exe --osd toggle", _t("cli_desc_osd_toggle", "Oyun içi RivaTuner (RTSS) bilgi ekranını açar veya kapatır.")),
                ]
            },
            {
                "group": _t("cli_group_help", "❓ CLI Yardım Ekranı (-h, --help)"),
                "items": [
                    ("WattCost. HaYTooL.exe --help", _t("cli_desc_help", "Konsolda tüm CLI komutlarını ve seçeneklerini listeler.")),
                ]
            },
        ]

        # Komutları Çiz
        for grp in cli_commands:
            f_sec = tk.Frame(scroll_content, bg=THEME["card_bg"])
            f_sec.pack(fill="x", padx=4, pady=(6, 2))

            tk.Label(f_sec, text=grp["group"], font=(f_font, 9, "bold"),
                     fg=THEME["accent_amber"], bg=THEME["card_bg"]).pack(anchor="w", padx=2, pady=(0, 4))

            for cmd_str, desc_str in grp["items"]:
                row = tk.Frame(f_sec, bg=THEME["card_inner"], bd=1, relief="solid")
                row.pack(fill="x", padx=2, pady=2)

                f_left = tk.Frame(row, bg=THEME["card_inner"])
                f_left.pack(side="left", fill="both", expand=True, padx=8, pady=4)

                lbl_cmd = tk.Label(f_left, text=cmd_str, font=("Consolas", 9, "bold"),
                                   fg=THEME["accent_cyan"], bg=THEME["card_inner"])
                lbl_cmd.pack(anchor="w")

                lbl_desc = tk.Label(f_left, text=desc_str, font=(f_font, 8),
                                    fg=THEME["text_secondary"], bg=THEME["card_inner"])
                lbl_desc.pack(anchor="w", pady=(1, 0))

                def _make_copy_handler(c_str):
                    def _copy(btn_widget):
                        try:
                            self.root.clipboard_clear()
                            self.root.clipboard_append(c_str)
                            btn_widget.config(text=_t("cli_copied", "✓ Kopyalandı!"), fg=THEME["accent_green"])
                            top.after(1400, lambda: btn_widget.config(text=_t("cli_copy", "📋 Kopyala"), fg=THEME["text_primary"]) if top.winfo_exists() and btn_widget.winfo_exists() else None)
                        except Exception:
                            pass
                    return _copy

                btn_copy = tk.Button(row, text=_t("cli_copy", "📋 Kopyala"), font=(f_font, 8),
                                     fg=THEME["text_primary"], bg=THEME["card_bg"],
                                     activebackground=THEME["accent_cyan"], activeforeground="#ffffff",
                                     bd=0, padx=8, pady=2, cursor="hand2")
                handler = _make_copy_handler(cmd_str)
                btn_copy.config(command=lambda b=btn_copy, h=handler: h(b))
                btn_copy.pack(side="right", padx=8, pady=4)

        # Alt Buton Barı (Terminal Aç / Kapat)
        f_footer = tk.Frame(top, bg=THEME["card_bg"])
        f_footer.pack(fill="x", padx=18, pady=(8, 12))

        def _open_terminal(is_ps=False):
            try:
                work_dir = os.path.dirname(os.path.abspath(sys.argv[0])) if getattr(sys, 'frozen', False) else os.path.abspath(".")
                if is_ps:
                    subprocess.Popen(["powershell.exe", "-NoExit", "-Command", f"Write-Host '⚡ WattCost HaYTooL CLI Konsolu' -ForegroundColor Cyan; Write-Host 'Yardım için: .\\\"WattCost. HaYTooL.exe\\\" --help' -ForegroundColor Yellow; cd '{work_dir}'"], cwd=work_dir)
                else:
                    subprocess.Popen(f'cmd.exe /k "echo ======================================================== && echo  ⚡ WattCost HaYTooL CLI Konsoluna Hos Geldiniz! && echo ======================================================== && echo Yardim: WattCost. HaYTooL.exe --help && echo. && cd /d {work_dir}"', shell=True, cwd=work_dir)
            except Exception:
                pass

        btn_cmd = self.make_btn(
            f_footer,
            _t("cli_btn_open_cmd", "⚡ Terminali Aç (CMD)"),
            lambda: _open_terminal(False),
            bg=THEME["card_inner"],
            fg=THEME["accent_green"],
            bold=True,
            tooltip=_t("cli_btn_open_cmd_tip", "WattCost dizininde komut istemini (CMD) başlatır")
        )
        btn_cmd.pack(side="left", padx=(0, 6))

        btn_ps = self.make_btn(
            f_footer,
            _t("cli_btn_open_ps", "⚡ PowerShell Aç"),
            lambda: _open_terminal(True),
            bg=THEME["card_inner"],
            fg=THEME["accent_cyan"],
            bold=True,
            tooltip=_t("cli_btn_open_ps_tip", "WattCost dizininde Windows PowerShell konsolunu başlatır")
        )
        btn_ps.pack(side="left", padx=4)

        btn_close = self.make_btn(
            f_footer,
            _t("cli_btn_close", "Kapat"),
            top.destroy,
            bg=THEME["card_inner"],
            fg=THEME["text_secondary"]
        )
        btn_close.pack(side="right")
