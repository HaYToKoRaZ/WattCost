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
from config_manager import THEME, UI_SCALE, fs, get_asset_path, APP_VERSION, apply_dark_titlebar
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

        # Plan Adı (varsa Hz bilgisiyle birlikte)
        disp_plan_name = plan_name
        if hz and int(hz) > 0 and f"{int(hz)} Hz" not in str(plan_name):
            disp_plan_name = f"{plan_name} • {int(hz)} Hz"
        lbl_name = tk.Label(pill, text=disp_plan_name, font=(f_font, fs(9), "bold"),
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
            track_color = THEME["accent_cyan"] if val else THEME["card_inner"]
            border_color = THEME["accent_cyan"] if val else THEME["card_border"]
            thumb_color = "#FFFFFF" if val else THEME["text_muted"]

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
            self.btn_test_screen.config(text=_t("test_screen_active_btn", "✓ Test Ekranı Açık"), bg=THEME["btn_active"])

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
        top.withdraw()
        self.apply_window_icon(top)
        top.title(_t("settings_title", "⚙ TARİFE VE SİSTEM AYARLARI"))
        # Geniş Yatay Dikdörtgen (Dashboard Oranı) - 2 Kolonlu Yayvan Düzen
        screen_w = top.winfo_screenwidth()
        screen_h = top.winfo_screenheight()
        target_w = min(int(screen_w * 0.96), max(920, int(980 * UI_SCALE)))
        target_h = min(int(screen_h * 0.94), max(640, int(680 * UI_SCALE)))
        pos_x = max(10, (screen_w - target_w) // 2)
        pos_y = max(10, (screen_h - target_h) // 2)

        top.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
        top.minsize(int(860 * UI_SCALE), int(580 * UI_SCALE))
        top.configure(bg=THEME["bg"])
        top.resizable(True, True)
        top.transient(self.root)
        apply_dark_titlebar(top)

        # Sabit Üst Başlık Barı (Başlık, Otomatik Kayıt & Tek CLI Rehberi Butonu)
        f_top_header = tk.Frame(top, bg=THEME["bg"])
        f_top_header.pack(fill="x", padx=16, pady=(10, 6))

        f_header_left = tk.Frame(f_top_header, bg=THEME["bg"])
        f_header_left.pack(side="left", fill="y")

        tk.Label(f_header_left, text=f"{_t('settings_title', '⚙ TARİFE VE SİSTEM AYARLARI')} (v{APP_VERSION})", font=(f_font, fs(10), "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["bg"]).pack(anchor="w")
        lbl_autosave = tk.Label(f_header_left, text=_t("settings_autosave_note", "⚡ Tüm ayarlar anında otomatik kaydedilir"), font=(f_font, fs(7), "italic"),
                                fg=THEME["accent_green"], bg=THEME["bg"])
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

        # 2 Eşit Sütunlu Kart Düzeni
        f_body = tk.Frame(top, bg=THEME["bg"])
        f_body.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        f_body.columnconfigure(0, weight=1, uniform="set_col")
        f_body.columnconfigure(1, weight=1, uniform="set_col")
        f_body.rowconfigure(0, weight=1)

        f_col_left = tk.Frame(f_body, bg=THEME["bg"])
        f_col_left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        f_col_right = tk.Frame(f_body, bg=THEME["bg"])
        f_col_right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        entries = {}

        # ========================================================
        # SOL KOLON: 1) TARİFE, 2) HARİCİ CİHAZLAR, 3) SİSTEM DAVRANIŞI
        # ========================================================

        # --- KART 1: ELEKTRİK TARİFESİ KADEMESİ ---
        card_tariff = self.create_card(f_col_left, pady=(0, 6))
        self.make_card_title(card_tariff, _t("settings_tariff_tier_title", "⚡ ELEKTRİK TARİFESİ KADEMESİ:"), THEME["accent_cyan"])

        f_tier = tk.Frame(card_tariff, bg=THEME["card_bg"])
        f_tier.pack(fill="x", padx=12, pady=(0, 8))

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

        f_form = tk.Frame(card_tariff, bg=THEME["card_bg"])
        f_form.pack(fill="x", padx=12, pady=(0, 8))

        f_price_row = tk.Frame(f_form, bg=THEME["card_bg"])
        f_price_row.pack(fill="x", pady=1)
        tk.Label(f_price_row, text=_t("settings_price_label", "Elektrik Birim Fiyatı (TL / kWh):"), font=(f_font, fs(8)), fg=THEME["text_secondary"],
                 bg=THEME["card_bg"]).pack(side="left", padx=(0, 8))
        ent_price = tk.Entry(f_price_row, font=(f_font, fs(9), "bold"), bg=THEME["card_inner"], fg=THEME["accent_cyan"],
                             insertbackground=THEME["text_primary"], relief="flat", width=10, justify="center",
                             highlightbackground=THEME["card_border"], highlightcolor=THEME["accent_cyan"],
                             highlightthickness=1)
        ent_price.insert(0, str(self.config.get("kwh_price_tl", 4.86)))
        ent_price.pack(side="right", ipady=2)
        self.add_tooltip(ent_price, _t("settings_price_tooltip", "1 kWh elektrik enerjisinin KDV ve dağıtım dahil güncel TL birim fiyatı"))
        entries["kwh_price_tl"] = ent_price

        # --- KART 2: PRİZDEN ÇEKİLEN HARİCİ CİHAZLAR & ÇEVRE BİRİMLERİ ---
        card_devices = self.create_card(f_col_left, pady=(0, 6))
        self.make_card_title(card_devices, _t("settings_devices_title", "🔌 PRİZDEN ÇEKİLEN HARİCİ CİHAZLAR:"), THEME["accent_amber"])

        f_devices_sec = tk.Frame(card_devices, bg=THEME["card_bg"])
        f_devices_sec.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(f_devices_sec, text=_t("settings_devices_desc", "Cihaz adını ve Watt değerini değiştirebilir, istemediklerinizi kapatabilir veya yeni cihaz ekleyebilirsiniz."),
                 font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["card_bg"], wraplength=int(420 * UI_SCALE), justify="left").pack(anchor="w", pady=(0, 4))

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
        # SAĞ KOLON: 4) GÖRÜNÜM & TRAY, 5) RTSS OSD & DONANIM
        # ========================================================
        card_appearance = self.create_card(f_col_right, pady=(0, 6))
        self.make_card_title(card_appearance, _t("settings_sec_appearance_tray", "🎨 GÖRÜNÜM VE SİSTEM TEPSİSİ (TRAY)"), THEME["accent_cyan"])

        from config_manager import AVAILABLE_THEMES
        f_theme_sec = tk.Frame(card_appearance, bg=THEME["card_bg"])
        f_theme_sec.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(f_theme_sec, text=_t("settings_theme_title", "🎨 Arayüz Teması:"), font=(f_font, fs(8), "bold"),
                 fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(anchor="w")

        is_tr = (self.lang_mgr.active_language_code == "tr") if hasattr(self, 'lang_mgr') else True
        theme_names = {}
        for k, v in AVAILABLE_THEMES.items():
            theme_names[k] = v["name_tr"] if is_tr else v["name_en"]
        from config_manager import AVAILABLE_THEMES, resolve_theme_key
        rev_theme_map = {}
        theme_names = {}
        for k, v in AVAILABLE_THEMES.items():
            theme_names[k] = v["name_tr"] if is_tr else v["name_en"]
        rev_theme_map = {v: k for k, v in theme_names.items()}
        cur_th_key = resolve_theme_key(self.config.get("theme", "auto"))
        cur_th_name = theme_names.get(cur_th_key, theme_names.get("dark"))

        opt_theme = ttk.Combobox(f_theme_sec, values=list(theme_names.values()), state="readonly", font=(f_font, fs(8)))
        opt_theme.set(cur_th_name)
        opt_theme.pack(fill="x", pady=(1, 0))
        self.add_tooltip(opt_theme, _t("settings_theme_tip", "Uygulama pencereleri ve sağ tuş menüsü için Açık, Koyu veya Matrix temasını seçin"))

        def _on_theme_change(event=None):
            sel_name = opt_theme.get()
            th_code = rev_theme_map.get(sel_name, "dark")
            auto_save()
            if hasattr(self, 'apply_theme_to_ui'):
                self.apply_theme_to_ui(th_code)
            else:
                from config_manager import set_active_theme
                set_active_theme(th_code)
                self.config["theme"] = th_code
                self.save_config()
            if top.winfo_exists():
                top.destroy()
            self.root.after(20, self.open_settings)

        opt_theme.bind("<<ComboboxSelected>>", _on_theme_change)

        # --- SİSTEM TEPSİSİ (TRAY) AYARLARI ---
        f_tray_mode = tk.Frame(card_appearance, bg=THEME["card_bg"])
        f_tray_mode.pack(fill="x", padx=12, pady=(4, 2))
        tk.Label(f_tray_mode, text=_t("settings_tray_display_title", "📌 Saatteki Simge Göstergesi (Tray):"), font=(f_font, fs(8), "bold"),
                 fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(anchor="w")

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

        opt_tray = ttk.Combobox(f_tray_mode, values=list(tray_mode_map.values()), state="readonly", font=(f_font, fs(8)))
        opt_tray.set(current_display_name)
        opt_tray.pack(fill="x", pady=(1, 0))
        self.add_tooltip(opt_tray, _t("settings_tray_mode_tip", "Windows görev çubuğu saat yanında simge olarak hangi canlı değerin gösterileceğini seçin"))

        # Yan yana kompakt Kutu Rengi ve Yazı Rengi seçimi
        f_tray_colors = tk.Frame(card_appearance, bg=THEME["card_bg"])
        f_tray_colors.pack(fill="x", padx=12, pady=2)

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
        f_tray_font = tk.Frame(card_appearance, bg=THEME["card_bg"])
        f_tray_font.pack(fill="x", padx=12, pady=2)
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
        f_tray_extra = tk.Frame(card_appearance, bg=THEME["card_bg"])
        f_tray_extra.pack(fill="x", padx=12, pady=(2, 8))

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

        # --- KART 5: OYUN İÇİ GÖSTERGE (RTSS) VE DONANIM (ZALMAN + KULAKLIK) ---
        card_osd_hw = self.create_card(f_col_right, pady=(0, 0))
        self.make_card_title(card_osd_hw, _t("settings_sec_osd_hw", "🎮 OYUN İÇİ GÖSTERGE (RTSS) VE DONANIM"), THEME["accent_purple"])

        pos_settings_map = {
            "top_right": _t("osd_pos_top_right", "↗ Sağ Üst (Varsayılan)"),
            "top_left": _t("osd_pos_top_left", "↖ Sol Üst"),
            "bottom_left": _t("osd_pos_bottom_left", "↙ Sol Alt"),
            "bottom_right": _t("osd_pos_bottom_right", "↘ Sağ Alt")
        }
        rev_pos_settings_map = {v: k for k, v in pos_settings_map.items()}

        f_rtss_row = tk.Frame(card_osd_hw, bg=THEME["card_bg"])
        f_rtss_row.pack(fill="x", padx=12, pady=(0, 6))

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

        # --- AKILLI KADEME KISAYOL TUŞLARI (Varsayılan: Kapalı) ---
        from hotkey_manager import TIER_HOTKEY_OPTIONS
        none_hk_lbl = _t("smart_hotkey_none", "Yok (Kapalı)")
        tier_hk_disp_map = {c: (none_hk_lbl if c == "none" else d) for c, d in TIER_HOTKEY_OPTIONS}
        rev_tier_hk_map = {v: k for k, v in tier_hk_disp_map.items()}
        tier_hotkeys_en_var = tk.BooleanVar(value=bool(self.config.get("smart_switch_hotkeys_enabled", False)))

        f_tier_hk_sec = tk.Frame(card_osd_hw, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_tier_hk_sec.pack(fill="x", padx=12, pady=(2, 6))

        def _on_tier_hk_toggle():
            self.config["smart_switch_hotkeys_enabled"] = bool(tier_hotkeys_en_var.get())
            auto_save()

        self.make_check(
            f_tier_hk_sec,
            _t("settings_tier_hotkeys_enable", "⌨️ Akıllı Kademe Kısayollarını Aktif Et"),
            tier_hotkeys_en_var,
            _on_tier_hk_toggle,
            fg=THEME["accent_cyan"], bold=True, bg=THEME["card_inner"],
            tooltip=_t("settings_tier_hotkeys_tip", "Açıkken Kademe 1-4 için atanan global klavye kısayolları (varsayılan Ctrl+Alt+1..4) dinlenir")
        ).pack(anchor="w", padx=8, pady=(5, 2))

        f_tier_hk_grid = tk.Frame(f_tier_hk_sec, bg=THEME["card_inner"])
        f_tier_hk_grid.pack(fill="x", padx=8, pady=(0, 6))
        f_tier_hk_grid.columnconfigure(1, weight=1, uniform="thk")
        f_tier_hk_grid.columnconfigure(3, weight=1, uniform="thk")

        tier_hk_combos = {}
        for idx, t_num in enumerate((1, 2, 3, 4)):
            r_pos, c_pos = divmod(idx, 2)
            tk.Label(f_tier_hk_grid, text=f"K{t_num}:", font=(f_font, fs(7), "bold"),
                     fg=THEME["text_secondary"], bg=THEME["card_inner"]).grid(row=r_pos, column=c_pos * 2, sticky="w", padx=(0 if c_pos == 0 else 8, 4), pady=2)
            cb_thk = ttk.Combobox(f_tier_hk_grid, values=list(tier_hk_disp_map.values()), state="readonly", font=(f_font, fs(7)))
            cur_t_code = str(self.config.get(f"smart_switch_t{t_num}_hotkey", f"Ctrl+Alt+{t_num}") or "none")
            cb_thk.set(tier_hk_disp_map.get(cur_t_code, cur_t_code))
            cb_thk.grid(row=r_pos, column=c_pos * 2 + 1, sticky="ew", pady=2)
            tier_hk_combos[t_num] = cb_thk

        # --- ZALMAN ALPHA2 LCD POMPA & KULAKLIK BATARYASI ---
        f_hw_box = tk.Frame(card_osd_hw, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_hw_box.pack(fill="x", padx=12, pady=(2, 10))

        zalman_on_var = tk.BooleanVar(value=bool(self.config.get("zalman_active", True)))
        headset_usb_var = tk.BooleanVar(value=bool(self.config.get("headset_usb_active", True)))
        headset_bt_var = tk.BooleanVar(value=bool(self.config.get("headset_bt_active", True)))

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

        def on_headset_usb_toggle():
            if hasattr(self, 'apply_headset_enabled'):
                self.apply_headset_enabled("usb", headset_usb_var.get())
            auto_save()

        def on_headset_bt_toggle():
            if hasattr(self, 'apply_headset_enabled'):
                self.apply_headset_enabled("bt", headset_bt_var.get())
            auto_save()

        self.make_check(f_hw_box, _t("settings_zalman_enable", "Zalman Alpha2 LCD Pompa Desteğini Aktif Et"), zalman_on_var,
                        on_zalman_setting_toggle, fg=THEME["text_primary"], bold=True, bg=THEME["card_inner"],
                        tooltip=_t("zalman_chk_tooltip", "Zalman Alpha2 sıvı soğutma LCD pompasıyla USB üzerinden haberleşmeyi ve ekran kartını kontrol eder")).pack(anchor="w", padx=8, pady=(6, 2))
        tk.Label(f_hw_box, text=_t("settings_zalman_note", "* Kapatıldığında Zalman pompası ile USB iletişimi kesilir ve ana ekrandaki kart gizlenir."),
                 font=(f_font, fs(6), "italic"), fg=THEME["text_muted"], bg=THEME["card_inner"],
                 wraplength=int(390 * UI_SCALE), justify="left").pack(anchor="w", padx=32, pady=(0, 4))

        tk.Frame(f_hw_box, bg=THEME["card_border"], height=1).pack(fill="x", padx=8, pady=2)

        self.make_check(f_hw_box, _t("settings_headset_usb", "SteelSeries USB kulaklık (HID)"),
                        headset_usb_var, on_headset_usb_toggle, fg=THEME["text_primary"], bold=True, bg=THEME["card_inner"],
                        tooltip=_t("settings_headset_usb_tip", "SteelSeries Arctis 7 / Pro bataryasını USB HID üzerinden okur; harici araç gerekmez")).pack(anchor="w", padx=8, pady=(4, 2))

        self.make_check(f_hw_box, _t("settings_headset_bt", "Bluetooth kulaklık (Windows HFP)"),
                        headset_bt_var, on_headset_bt_toggle, fg=THEME["text_primary"], bold=True, bg=THEME["card_inner"],
                        tooltip=_t("settings_headset_bt_tip", "Bağlı Bluetooth kulaklığın bataryasını Windows'un HFP cihaz özelliğinden okur")).pack(anchor="w", padx=8, pady=2)

        tk.Label(f_hw_box, text=_t("settings_headset_note_dual", "* İki kaynak bağımsızdır: yalnızca sahip olduğunuz türü açık bırakın. İkisi de kapalıysa hiç okuma yapılmaz."),
                 font=(f_font, fs(6), "italic"), fg=THEME["text_muted"], bg=THEME["card_inner"],
                 wraplength=int(390 * UI_SCALE), justify="left").pack(anchor="w", padx=32, pady=(0, 6))

        # --- KART 3 (SOL KOLON ALTI): SİSTEM DAVRANIŞI VE BİLDİRİMLER ---
        card_system = self.create_card(f_col_left, pady=(0, 0))
        self.make_card_title(card_system, _t("settings_sec_system", "⚙️ SİSTEM DAVRANIŞI VE BİLDİRİMLER"), THEME["accent_green"])

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

            if "kwh_price_tl" in self.config:
                p_now = float(self.config.get("kwh_price_tl", 4.86))
                if abs(p_now - 3.24) < 0.01:
                    tariff_var.set("low")
                elif abs(p_now - 4.86) < 0.01:
                    tariff_var.set("high")
                else:
                    tariff_var.set("custom")

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

            if hasattr(self, 'on_top_var'):
                self.config["always_on_top"] = bool(self.on_top_var.get())
                self.apply_always_on_top()

            self.config["close_to_tray"] = close_to_tray_var.get()
            self.config["power_plan_toast"] = toast_notify_var.get()
            self.config["power_plan_sound"] = power_sound_var.get()
            self.config["smart_switch_sound"] = smart_sound_var.get()
            self.config["smart_switch_toast"] = smart_toast_var.get()
            if hasattr(self, 'smart_switch_sound_var'):
                self.smart_switch_sound_var.set(smart_sound_var.get())
            if hasattr(self, 'smart_switch_toast_var'):
                self.smart_switch_toast_var.set(smart_toast_var.get())

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
                if getattr(self.hotkey_mgr, "vk", None) is not None:
                    self.config["rtss_hotkey_vk"] = int(self.hotkey_mgr.vk)
                if getattr(self.hotkey_mgr, "mod", None) is not None:
                    self.config["rtss_hotkey_mod"] = int(self.hotkey_mgr.mod)

            self.config["smart_switch_hotkeys_enabled"] = bool(tier_hotkeys_en_var.get())
            for t_num, cb_thk in tier_hk_combos.items():
                sel_t_code = rev_tier_hk_map.get(cb_thk.get(), f"Ctrl+Alt+{t_num}")
                self.config[f"smart_switch_t{t_num}_hotkey"] = sel_t_code
                t_var = getattr(self, f"smart_t{t_num}_hotkey_var", None)
                if t_var is not None:
                    t_var.set(none_hk_lbl if sel_t_code == "none" else f"⌨️ {cb_thk.get()}")
            if hasattr(self, "register_all_hotkeys"):
                self.register_all_hotkeys()

            self.save_config()
            WindowsAutoStart.set_enabled(autostart_var.get())
            if hasattr(self, 'refresh_devices_ui'):
                self.refresh_devices_ui()
            if hasattr(self, '_refresh_tray_icon'):
                self._refresh_tray_icon()
            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    self.tray_icon.update_menu()
                except Exception:
                    pass
            self.on_rtss_change()

            lbl_autosave.config(text=_t("settings_autosave_saved", "✓ Değişiklik anında kaydedildi & uygulandı"), fg=THEME["accent_cyan"])
            top.after(1000, lambda: lbl_autosave.config(text=_t("settings_autosave_note", "⚡ Tüm ayarlar anında otomatik kaydedilir"), fg=THEME["accent_green"]) if top.winfo_exists() else None)

            # Bağlı GitHub token varsa 5 sn debounce ile Gist yedeğini arka planda güncelle
            _tok_auto = str(self.config.get("github_gist_token", "") or "").strip()
            if _tok_auto and getattr(self, "_github_profile_cache", {}).get("token") == _tok_auto:
                prev_tid = getattr(self, "_gist_auto_backup_after", None)
                if prev_tid is not None:
                    try:
                        self.root.after_cancel(prev_tid)
                    except Exception:
                        pass
                def _run_bg_gist():
                    self._gist_auto_backup_after = None
                    t_now = str(self.config.get("github_gist_token", "") or "").strip()
                    g_now = str(self.config.get("github_gist_id", "") or "").strip()
                    if not t_now:
                        return
                    def _bg():
                        try:
                            from config_manager import backup_settings_to_gist
                            ok_b, new_id_b, _ = backup_settings_to_gist(t_now, g_now)
                            if ok_b and new_id_b and new_id_b != g_now:
                                self.root.after(0, lambda: (self.config.__setitem__("github_gist_id", new_id_b), self.save_config()))
                        except Exception:
                            pass
                    threading.Thread(target=_bg, daemon=True).start()
                self._gist_auto_backup_after = self.root.after(5000, _run_bg_gist)

        for ent in list(entries.values()) + [ent_tray_warn, ent_tray_crit]:
            ent.bind("<KeyRelease>", auto_save)
            ent.bind("<FocusOut>", auto_save)

        for cb in [opt_tray, opt_font, opt_size, opt_bg, opt_fg, opt_osd_pos, opt_osd_hk] + list(tier_hk_combos.values()):
            cb.bind("<<ComboboxSelected>>", auto_save)

        f_sys = tk.Frame(card_system, bg=THEME["card_bg"])
        f_sys.pack(fill="x", padx=12, pady=(0, 8))

        self.make_check(f_sys, _t("settings_autostart_chk", "Windows başlangıcında otomatik başlat"), autostart_var, auto_save,
                        fg=THEME["text_primary"], bold=True,
                        tooltip=_t("settings_autostart_tip", "Bilgisayar her açıldığında WattCost'u arka planda sistem tepsisinde otomatik başlatır")).pack(anchor="w", pady=2)

        self.make_check(f_sys, _t("settings_power_plan_sound_chk", "🔔 Güç planı değişiminde sesli uyarı çal"), power_sound_var, auto_save,
                        fg=THEME["text_primary"], bold=True,
                        tooltip=_t("settings_power_plan_sound_tip", "Sistem güç planı değiştirildiğinde sesli bildirim çalar")).pack(anchor="w", pady=2)

        self.make_check(f_sys, _t("settings_power_plan_toast_chk", "💬 Güç planı değişiminde Toast bildirim göster"), toast_notify_var, auto_save,
                        fg=THEME["text_primary"], bold=True,
                        tooltip=_t("settings_power_plan_toast_tip", "Güç planı değiştirildiğinde ekranın sağ altında açılan bilgi kutusunu gösterir")).pack(anchor="w", pady=2)

        self.make_check(f_sys, _t("smart_sound_lbl", "🔔 Akıllı geçişlerde (SmartSwitch) sesli uyarı"), smart_sound_var, auto_save,
                        fg=THEME["text_primary"], bold=True,
                        tooltip=_t("smart_sound_tip", "Otomasyon kademe değiştirdiğinde sesli bildirim çalar")).pack(anchor="w", pady=2)

        self.make_check(f_sys, _t("smart_toast_lbl", "💬 Akıllı geçişlerde Toast bildirim göster"), smart_toast_var, auto_save,
                        fg=THEME["text_primary"], bold=True,
                        tooltip=_t("smart_toast_tip", "Otomasyon güç planını veya Hz değerini değiştirdiğinde ekranın sağ altında açılan bilgi kutusunu gösterir")).pack(anchor="w", pady=2)

        if not hasattr(self, 'on_top_var'):
            self.on_top_var = tk.BooleanVar(value=bool(self.config.get("always_on_top", False)))
        self.make_check(f_sys, _t("settings_always_on_top_chk", "Pencereyi Her Zaman En Üstte Tut"), self.on_top_var, auto_save,
                        fg=THEME["text_primary"], bold=True).pack(anchor="w", pady=2)

        self.make_check(f_sys, _t("settings_close_to_tray_chk", "Çarpı (X) ile kapatınca tepsiye gizle"), close_to_tray_var, auto_save,
                        tooltip=_t("settings_close_to_tray_tip", "Pencereyi (X) ile kapattığınızda program kapanmaz; arka planda güç ve maliyet takibini sürdürür")).pack(anchor="w", pady=2)
        tk.Label(f_sys, text="* " + _t("settings_close_to_tray_note", "İşaretsizse X'e basınca program tamamen kapanır ve izleme durur."),
                 font=(f_font, fs(6), "italic"), fg=THEME["text_muted"], bg=THEME["card_bg"],
                 wraplength=int(400 * UI_SCALE), justify="left").pack(anchor="w", padx=24, pady=(0, 2))

        # --- KART 6 (SAĞ KOLON ALTI): GITHUB GİST AYAR YEDEĞİ ---
        card_gist = self.create_card(f_col_right, pady=(6, 0))
        self.make_card_title(card_gist, _t("settings_sec_gist", "☁️ GITHUB GİST AYAR YEDEĞİ"), THEME["accent_cyan"])

        f_gist = tk.Frame(card_gist, bg=THEME["card_bg"])
        f_gist.pack(fill="x", padx=12, pady=(0, 8))

        f_gist_tok = tk.Frame(f_gist, bg=THEME["card_bg"])
        f_gist_tok.pack(fill="x", pady=(0, 4))
        tk.Label(f_gist_tok, text=_t("settings_gist_token_lbl", "GitHub Token (gist):"), font=(f_font, fs(7), "bold"),
                 fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")
        def _open_gist_token_page():
            import urllib.parse
            desc = urllib.parse.quote_plus(f"WattCost HaYTooL ({time.strftime('%Y-%m-%d')})")
            url = f"https://github.com/settings/tokens/new?scopes=gist&description={desc}"
            try:
                os.startfile(url)
            except Exception:
                import webbrowser
                webbrowser.open(url)

        self.make_btn(
            f_gist_tok, _t("settings_gist_get_token", "🔑 Token Al"),
            _open_gist_token_page,
            fg=THEME["accent_cyan"], bg=THEME["card_inner"], padx=int(6 * UI_SCALE), pady=1,
            tooltip=_t("settings_gist_get_token_tip", "GitHub'da yalnızca 'gist' izinli yeni token oluşturma sayfasını açar")
        ).pack(side="right")

        ent_gist_token = tk.Entry(
            f_gist, show="*", font=("Consolas", fs(8)),
            bg=THEME["card_inner"], fg=THEME["text_primary"], insertbackground=THEME["accent_cyan"],
            relief="flat", bd=0, highlightbackground=THEME["card_border"], highlightthickness=1
        )
        ent_gist_token.insert(0, str(self.config.get("github_gist_token", "") or ""))
        ent_gist_token.pack(fill="x", ipady=3, pady=(0, 6))
        self.add_tooltip(ent_gist_token, _t("settings_gist_token_tip", "Yalnızca 'gist' yetkili Personal Access Token. Token yedek dosyasına ASLA yazılmaz."))

        # Profil resmi + kullanıcı adı + otomatik Gist eşleşme satırı
        f_gist_profile = tk.Frame(f_gist, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_gist_profile.pack(fill="x", pady=(0, 6))

        lbl_gist_avatar = tk.Label(f_gist_profile, text="🐙", font=(f_font, fs(11)),
                                   fg=THEME["text_muted"], bg=THEME["card_inner"], width=3)
        lbl_gist_avatar.pack(side="left", padx=(6, 4), pady=4)

        lbl_gist_user = tk.Label(
            f_gist_profile,
            text=_t("settings_gist_not_connected", "GitHub hesabı bağlı değil (Token yapıştırın)"),
            font=(f_font, fs(7), "bold"), fg=THEME["text_muted"], bg=THEME["card_inner"], anchor="w"
        )
        lbl_gist_user.pack(side="left", fill="x", expand=True, padx=(0, 4), pady=4)

        def _set_token_inputs_visible(visible: bool):
            if visible:
                if not f_gist_tok.winfo_ismapped():
                    f_gist_tok.pack(fill="x", pady=(0, 4), before=f_gist_profile)
                if not ent_gist_token.winfo_ismapped():
                    ent_gist_token.pack(fill="x", ipady=3, pady=(0, 6), before=f_gist_profile)
                try:
                    btn_gist_clear.pack_forget()
                except Exception:
                    pass
            else:
                try:
                    f_gist_tok.pack_forget()
                    ent_gist_token.pack_forget()
                except Exception:
                    pass
                if not btn_gist_clear.winfo_ismapped():
                    btn_gist_clear.pack(side="right", padx=(0, 6), pady=4)

        def _clear_gist_token():
            ent_gist_token.delete(0, tk.END)
            self.config["github_gist_token"] = ""
            self.config["github_gist_id"] = ""
            self.save_config()
            self._github_profile_cache = {}
            if hasattr(self, "refresh_header_github_avatar"):
                self.refresh_header_github_avatar()
            _last_synced_tok[0] = ""
            _set_token_inputs_visible(True)
            lbl_gist_avatar.config(image="", text="🐙", width=3)
            lbl_gist_user.config(text=_t("settings_gist_not_connected", "GitHub hesabı bağlı değil (Token yapıştırın)"), fg=THEME["text_muted"])
            lbl_gist_status.config(text=_t("settings_gist_cleared", "✓ GitHub Token silindi ve bağlantı kesildi"), fg=THEME["accent_amber"])

        btn_gist_clear = self.make_btn(
            f_gist_profile, _t("settings_gist_clear_btn", "🗑️ Token Sil"),
            _clear_gist_token,
            fg=THEME["accent_rose"], bg=THEME["card_bg"], padx=int(6 * UI_SCALE), pady=1,
            tooltip=_t("settings_gist_clear_tip", "Kayıtlı GitHub Token'ını uygulamadan kaldırır ve bağlantıyı keser")
        )

        lbl_gist_status = tk.Label(f_gist, text="", font=(f_font, fs(7), "bold"),
                                   fg=THEME["text_muted"], bg=THEME["card_bg"], anchor="w")

        _gist_sync_after = [None]
        _last_synced_tok = [None]

        def _render_avatar(av_bytes: bytes):
            if not av_bytes or not top.winfo_exists():
                return
            photo = self.make_circular_avatar(av_bytes, int(26 * UI_SCALE)) if hasattr(self, "make_circular_avatar") else None
            if photo is not None:
                lbl_gist_avatar.config(image=photo, text="", width=0)
                lbl_gist_avatar.image = photo

        def _sync_github_profile(force=False):
            tok = ent_gist_token.get().strip()
            self.config["github_gist_token"] = tok
            self.save_config()
            if not tok:
                _last_synced_tok[0] = ""
                self._github_profile_cache = {}
                if hasattr(self, "refresh_header_github_avatar"):
                    self.refresh_header_github_avatar()
                lbl_gist_avatar.config(image="", text="🐙", width=3)
                lbl_gist_user.config(text=_t("settings_gist_not_connected", "GitHub hesabı bağlı değil (Token yapıştırın)"), fg=THEME["text_muted"])
                return
            if not force and tok == _last_synced_tok[0]:
                return
            if len(tok) < 20:
                return
            _last_synced_tok[0] = tok
            lbl_gist_user.config(text=_t("settings_gist_checking", "⏳ GitHub hesabı ve yedek Gist kontrol ediliyor..."), fg=THEME["accent_cyan"])

            def _worker():
                try:
                    from config_manager import fetch_github_user_and_backup_gist
                    ok, info, err = fetch_github_user_and_backup_gist(tok)
                except Exception as exc:
                    ok, info, err = False, {}, str(exc)
                def _done():
                    if not top.winfo_exists() or ent_gist_token.get().strip() != tok:
                        return
                    if ok:
                        login = info.get("login", "")
                        found_gid = info.get("gist_id", "")
                        if found_gid:
                            self.config["github_gist_id"] = found_gid
                            self.save_config()
                            lbl_gist_user.config(
                                text=_t("settings_gist_connected_found", "✓ @{user} • Mevcut ayar yedeği otomatik bulundu").format(user=login),
                                fg=THEME["accent_green"]
                            )
                        else:
                            lbl_gist_user.config(
                                text=_t("settings_gist_connected_new", "✓ @{user} • Bağlandı (ilk yedeklemeye hazır)").format(user=login),
                                fg=THEME["accent_cyan"]
                            )
                        _render_avatar(info.get("avatar_bytes", b""))
                        _set_token_inputs_visible(False)
                        self._github_profile_cache = {
                            "token": tok,
                            "login": login,
                            "avatar_bytes": info.get("avatar_bytes", b""),
                        }
                        if hasattr(self, "refresh_header_github_avatar"):
                            self.refresh_header_github_avatar()
                    else:
                        _set_token_inputs_visible(True)
                        self._github_profile_cache = {}
                        if hasattr(self, "refresh_header_github_avatar"):
                            self.refresh_header_github_avatar()
                        lbl_gist_avatar.config(image="", text="🐙", width=3)
                        lbl_gist_user.config(text=_t("settings_gist_err_fail", "✗ Gist hatası: {err}").format(err=err), fg=THEME["accent_rose"])
                try:
                    self.root.after(0, _done)
                except Exception:
                    pass

            threading.Thread(target=_worker, daemon=True).start()

        def _on_token_change(e=None):
            self.config["github_gist_token"] = ent_gist_token.get().strip()
            self.save_config()
            if _gist_sync_after[0] is not None:
                try:
                    top.after_cancel(_gist_sync_after[0])
                except Exception:
                    pass
            _gist_sync_after[0] = top.after(450, _sync_github_profile)

        ent_gist_token.bind("<KeyRelease>", _on_token_change)
        ent_gist_token.bind("<<Paste>>", lambda e: top.after(30, _on_token_change))
        ent_gist_token.bind("<FocusOut>", lambda e: _sync_github_profile())
        if str(self.config.get("github_gist_token", "") or "").strip():
            top.after(50, lambda: _sync_github_profile(force=True))

        def _do_gist_backup():
            tok = ent_gist_token.get().strip()
            gid = str(self.config.get("github_gist_id", "") or "").strip()
            if not tok:
                lbl_gist_status.config(text=_t("settings_gist_err_no_token", "⚠ Yedekleme için önce GitHub Token girin!"), fg=THEME["accent_amber"])
                return
            self.config["github_gist_token"] = tok
            self.save_config()
            lbl_gist_status.config(text=_t("settings_gist_working", "⏳ GitHub Gist ile iletişim kuruluyor..."), fg=THEME["accent_cyan"])

            def _worker():
                from config_manager import backup_settings_to_gist
                ok, new_id, msg = backup_settings_to_gist(tok, gid)
                def _done():
                    if not top.winfo_exists():
                        return
                    if ok:
                        self.config["github_gist_id"] = new_id
                        self.save_config()
                        txt = _t("settings_gist_backup_ok", "✓ Ayarlar Gizli Gist'e yedeklendi ({id})").format(id=new_id[:10] + "...")
                        lbl_gist_status.config(text=txt, fg=THEME["accent_green"])
                        if hasattr(self, "show_toast"):
                            self.show_toast("WattCost", txt, THEME["accent_green"])
                    else:
                        lbl_gist_status.config(text=_t("settings_gist_err_fail", "✗ Gist hatası: {err}").format(err=msg), fg=THEME["accent_rose"])
                self.root.after(0, _done)

            threading.Thread(target=_worker, daemon=True).start()

        def _do_gist_restore():
            tok = ent_gist_token.get().strip()
            gid = str(self.config.get("github_gist_id", "") or "").strip()
            if not tok and not gid:
                lbl_gist_status.config(text=_t("settings_gist_err_no_token", "⚠ Yedekleme için önce GitHub Token girin!"), fg=THEME["accent_amber"])
                return
            self.config["github_gist_token"] = tok
            self.save_config()
            lbl_gist_status.config(text=_t("settings_gist_working", "⏳ GitHub Gist ile iletişim kuruluyor..."), fg=THEME["accent_cyan"])

            def _worker():
                from config_manager import restore_settings_from_gist
                ok, msg = restore_settings_from_gist(gid, tok)
                def _done():
                    if ok:
                        self.load_config()
                        self.config["github_gist_token"] = tok
                        self.config["github_gist_id"] = msg
                        self.save_config()
                        if hasattr(self, "apply_theme_to_ui"):
                            self.apply_theme_to_ui(self.config.get("theme", "auto"))
                        if hasattr(self, "register_all_hotkeys"):
                            self.register_all_hotkeys()
                        if hasattr(self, "show_toast"):
                            self.show_toast("WattCost", _t("settings_gist_restore_ok", "✓ Ayarlar Gist'ten geri yüklendi ve uygulandı!"), THEME["accent_green"])
                        if top.winfo_exists():
                            top.destroy()
                        self.root.after(20, self.open_settings)
                    elif top.winfo_exists():
                        lbl_gist_status.config(text=_t("settings_gist_err_fail", "✗ Gist hatası: {err}").format(err=msg), fg=THEME["accent_rose"])
                self.root.after(0, _done)

            threading.Thread(target=_worker, daemon=True).start()

        def _do_gist_preview():
            tok = str(self.config.get("github_gist_token", "") or ent_gist_token.get()).strip()
            gid = str(self.config.get("github_gist_id", "") or "").strip()
            if not tok and not gid:
                lbl_gist_status.config(text=_t("settings_gist_err_no_token", "⚠ Yedekleme için önce GitHub Token girin!"), fg=THEME["accent_amber"])
                return
            lbl_gist_status.config(text=_t("settings_gist_working", "⏳ GitHub Gist ile iletişim kuruluyor..."), fg=THEME["accent_cyan"])

            def _worker():
                try:
                    from config_manager import fetch_gist_ini_preview
                    ok, content, updated_at = fetch_gist_ini_preview(gid, tok)
                except Exception as exc:
                    ok, content, updated_at = False, str(exc), ""

                def _done():
                    if not top.winfo_exists():
                        return
                    if not ok:
                        lbl_gist_status.config(text=_t("settings_gist_err_fail", "✗ Gist hatası: {err}").format(err=content), fg=THEME["accent_rose"])
                        return
                    lbl_gist_status.config(text="", fg=THEME["text_muted"])

                    pv = tk.Toplevel(top)
                    self.apply_window_icon(pv)
                    pv.title(_t("settings_gist_preview_title", "☁️ GitHub Gist'teki Kayıtlı Ayarlar"))
                    pv.configure(bg=THEME["bg"])
                    apply_dark_titlebar(pv)
                    pw, ph = int(560 * UI_SCALE), int(440 * UI_SCALE)
                    px = max(10, (pv.winfo_screenwidth() - pw) // 2)
                    py = max(10, (pv.winfo_screenheight() - ph) // 2)
                    pv.geometry(f"{pw}x{ph}+{px}+{py}")

                    f_pv_hdr = tk.Frame(pv, bg=THEME["bg"])
                    f_pv_hdr.pack(fill="x", padx=12, pady=(10, 6))
                    tk.Label(f_pv_hdr, text=_t("settings_gist_preview_title", "☁️ GitHub Gist'teki Kayıtlı Ayarlar"),
                             font=(f_font, fs(10), "bold"), fg=THEME["accent_cyan"], bg=THEME["bg"]).pack(side="left")
                    if updated_at:
                        tk.Label(f_pv_hdr, text=_t("settings_gist_preview_updated", "Son yedekleme: {dt}").format(dt=updated_at.replace("T", " ").replace("Z", " UTC")),
                                 font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["bg"]).pack(side="right")

                    f_pv_txt = tk.Frame(pv, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
                    f_pv_txt.pack(fill="both", expand=True, padx=12, pady=(0, 8))
                    sb = ttk.Scrollbar(f_pv_txt, orient="vertical")
                    txt = tk.Text(f_pv_txt, font=("Consolas", fs(8)), bg=THEME["card_bg"], fg=THEME["text_primary"],
                                  relief="flat", bd=6, wrap="none", yscrollcommand=sb.set)
                    sb.config(command=txt.yview)
                    sb.pack(side="right", fill="y")
                    txt.pack(side="left", fill="both", expand=True)
                    txt.insert("1.0", content)
                    txt.config(state="disabled")

                    f_pv_act = tk.Frame(pv, bg=THEME["bg"])
                    f_pv_act.pack(fill="x", padx=12, pady=(0, 10))
                    self.make_btn(f_pv_act, _t("settings_gist_restore_btn", "📥 Gist'ten Yükle"),
                                  lambda: (pv.destroy(), _do_gist_restore()),
                                  fg=THEME["accent_green"], bg=THEME["card_inner"]).pack(side="right")
                    pv.grab_set()

                try:
                    self.root.after(0, _done)
                except Exception:
                    pass

            threading.Thread(target=_worker, daemon=True).start()

        f_gist_btns = tk.Frame(f_gist, bg=THEME["card_bg"])
        f_gist_btns.pack(fill="x", pady=(0, 4))
        self.make_btn(f_gist_btns, _t("settings_gist_backup_btn", "☁️ Gist'e Yedekle"), _do_gist_backup,
                      fg=THEME["accent_cyan"], bg=THEME["card_inner"]).pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.make_btn(f_gist_btns, _t("settings_gist_preview_btn", "👁️ Yedeği Gör"), _do_gist_preview,
                      fg=THEME["text_primary"], bg=THEME["card_inner"],
                      tooltip=_t("settings_gist_preview_tip", "GitHub Gist'te kayıtlı eski ayarlarınızı önizler")).pack(side="left", fill="x", expand=True, padx=2)
        self.make_btn(f_gist_btns, _t("settings_gist_restore_btn", "📥 Gist'ten Yükle"), _do_gist_restore,
                      fg=THEME["accent_green"], bg=THEME["card_inner"]).pack(side="left", fill="x", expand=True, padx=(2, 0))
        lbl_gist_status.pack(fill="x")
        tk.Label(f_gist, text=_t("settings_gist_auto_note", "💡 Yedekleme: 'Gist'e Yedekle'ye bastığınızda veya ayar değiştirdiğinizde otomatik güncellenir."),
                 font=(f_font, fs(6), "italic"), fg=THEME["text_muted"], bg=THEME["card_bg"],
                 wraplength=int(410 * UI_SCALE), justify="left").pack(anchor="w", pady=(2, 0))

        top.update_idletasks()
        top.deiconify()
        top.grab_set()

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
                "group": _t("cli_group_hz", "🖥️ Monitör Yenileme Hızı (--hz)"),
                "items": [
                    ("WattCost. HaYTooL.exe --hz 144", _t("cli_desc_hz", "Birincil monitörün yenileme hızını doğrudan ayarlar (örn. 60, 144).")),
                ]
            },
            {
                "group": _t("cli_group_tab", "🗂️ Sekme Açma (--tab)"),
                "items": [
                    ("WattCost. HaYTooL.exe --tab smart", _t("cli_desc_tab", "Açık pencereyi öne getirip belirtilen sekmeye geçer (cost, powerplan, smart, compare).")),
                ]
            },
            {
                "group": _t("cli_group_hide", "🕵️ Tam Gizli Çoklu-Kullanıcı Modu (hide / --hide)"),
                "items": [
                    ('"WattCost. HaYTooL.exe" hide', _t("cli_desc_hide", "Pencere ve saat yanı tepsi simgesi açmadan yalnızca tüketim kaydı + Zalman pompa için arka planda başlar (yeni INI oluşturmaz).")),
                    ('"WattCost. HaYTooL.exe" hide1', _t("cli_desc_hide1", "Gizli modda başlar ve Akıllı Geçiş Kademe 1 (Ultra Tasarruf) güç planı + monitör Hz ayarlarını aktif eder.")),
                    ('"WattCost. HaYTooL.exe" hide3', _t("cli_desc_hide3", "Gizli modda başlar ve Akıllı Geçiş Kademe 3 (Yüksek Performans) güç planı + monitör Hz ayarlarını aktif eder.")),
                    ('"WattCost. HaYTooL.exe" hideauto', _t("cli_desc_hideauto", "Gizli modda başlar ve 4 kademeli Akıllı Geçiş (güç planı + Hz) otomasyonunu arka planda dinamik çalıştırır.")),
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
