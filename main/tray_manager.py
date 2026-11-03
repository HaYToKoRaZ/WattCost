"""
WattCost HaYTooL - System Tray Modülü
Windows saat yanındaki sistem tepsisi simgesi, dinamik sayaç çizimi, sağ tık menüsü ve arka plan yönetimini sağlar.
"""
import os
import threading
import pystray
from PIL import Image, ImageDraw, ImageFont
from config_manager import get_asset_path, apply_dark_titlebar
from language_manager import _t
from power_manager import PowerManagerService, DisplayManagerService
from history_manager import WindowsAutoStart


class TrayManagerMixin:
    """Windows Sistem Tepsisi (Tray) simge ve menü yöneticisi."""

    def _get_tray_font(self, size):
        font_choice = self.config.get("tray_font", "bahnschrift")
        cache_key = (font_choice, size)
        if not hasattr(self, '_font_cache'):
            self._font_cache = {}
        if cache_key not in self._font_cache:
            font_map = {
                "segoe": ["segoeuib.ttf", "segoeui.ttf", "arialbd.ttf"],
                "bahnschrift": ["bahnschrift.ttf", "segoeuib.ttf"],
                "arial": ["arialbd.ttf", "ariblk.ttf", "arial.ttf"],
                "consola": ["consolab.ttf", "consola.ttf"],
                "impact": ["impact.ttf", "ariblk.ttf", "arialbd.ttf"],
            }
            cand_files = font_map.get(font_choice, ["bahnschrift.ttf", "segoeuib.ttf"])
            windir = os.environ.get('WINDIR', 'C:\\Windows')
            font_path = None
            for fname in cand_files:
                p = os.path.join(windir, 'Fonts', fname)
                if os.path.exists(p):
                    font_path = p
                    break
            try:
                if font_path:
                    self._font_cache[cache_key] = ImageFont.truetype(font_path, size)
                else:
                    self._font_cache[cache_key] = ImageFont.load_default()
            except Exception:
                self._font_cache[cache_key] = ImageFont.load_default()
        return self._font_cache[cache_key]

    def _get_optimal_font_size(self, val_str, max_w, max_h, font_choice):
        """Metin uzunluğuna ve kullanıcı boyut ölçeğine göre optimal font boyutunu döndürür."""
        length = len(val_str)
        size_mode = self.config.get("tray_font_size", "normal")

        # 1-2 Haneli Değerler (Sıcaklık 55°C, Kullanım vb.)
        if length <= 2:
            sz_map = {
                "small":  32,
                "normal": 44,   # 1.45x Tabanı (Varsayılan)
                "large":  50,   # 1.75x
                "xlarge": 56,   # 2.10x
                "max":    62    # 2.50x
            }
            best_sz = sz_map.get(size_mode, 44)
        elif length == 3:
            # 3 Haneli Değerler (Watt: 250W)
            sz_map = {
                "small":  28,
                "normal": 38,   # 1.45x Tabanı (Varsayılan - tam kutu genişliği)
                "large":  46,   # 1.75x
                "xlarge": 52,   # 2.10x
                "max":    58    # 2.50x
            }
            best_sz = sz_map.get(size_mode, 38)
        elif length == 4:
            sz_map = {
                "small":  22,
                "normal": 30,
                "large":  36,
                "xlarge": 42,
                "max":    48
            }
            best_sz = sz_map.get(size_mode, 30)
        else:
            best_sz = 20

        limit_w = 63 if max_w >= 56 else max_w
        limit_h = 63 if max_h >= 56 else max_h

        font = self._get_tray_font(best_sz)
        dummy_img = Image.new('RGBA', (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), val_str, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        # Eğer doğrudan çizimde genişlik aşarsa (ve özel stretch modunda değilsek) küçült
        if length <= 2 or size_mode in ("small", "normal"):
            while (tw > limit_w or th > limit_h) and best_sz > 10:
                best_sz -= 1
                font = self._get_tray_font(best_sz)
                bbox = draw.textbbox((0, 0), val_str, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

        return best_sz, bbox

    def _draw_tray_badge(self, val_str, alert_color):
        bg_mode = self.config.get("tray_bg", "transparent")
        fg_mode = self.config.get("tray_fg", "auto")
        font_choice = self.config.get("tray_font", "bahnschrift")
        size_mode = self.config.get("tray_font_size", "normal")

        badge_cache_key = (val_str, alert_color, bg_mode, fg_mode, font_choice, size_mode)
        if not hasattr(self, '_badge_cache'):
            self._badge_cache = {}
        if badge_cache_key in self._badge_cache:
            return self._badge_cache[badge_cache_key]

        img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 1. Yazı Rengi
        if fg_mode == "auto":
            text_color = alert_color
        elif fg_mode == "cyan":
            text_color = (0, 255, 255, 255)
        elif fg_mode == "green":
            text_color = (16, 255, 129, 255)
        elif fg_mode == "amber":
            text_color = (251, 191, 36, 255)
        elif fg_mode == "rose":
            text_color = (244, 63, 94, 255)
        elif fg_mode == "white":
            text_color = (255, 255, 255, 255)
        elif fg_mode == "black":
            text_color = (8, 11, 20, 255)
        elif fg_mode == "purple":
            text_color = (192, 132, 252, 255)
        else:
            text_color = alert_color

        # 2. Arka Plan Çizimi
        if bg_mode == "dark":
            draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(8, 11, 20, 255), outline=alert_color, width=2)
        elif bg_mode == "cyan":
            draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(0, 229, 255, 255))
            if fg_mode == "auto":
                text_color = (8, 11, 20, 255)
        elif bg_mode == "green":
            draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(16, 185, 129, 255))
            if fg_mode == "auto":
                text_color = (8, 11, 20, 255)
        elif bg_mode == "rose":
            draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(244, 63, 94, 255))
            if fg_mode == "auto":
                text_color = (255, 255, 255, 255)
        elif bg_mode == "amber":
            draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(245, 158, 11, 255))
            if fg_mode == "auto":
                text_color = (8, 11, 20, 255)
        elif bg_mode == "white":
            draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(255, 255, 255, 255))
            if fg_mode == "auto":
                text_color = (8, 11, 20, 255)

        max_w = 56 if bg_mode != "transparent" else 63
        max_h = 56 if bg_mode != "transparent" else 63

        best_sz, best_bbox = self._get_optimal_font_size(val_str, max_w, max_h, font_choice)
        font = self._get_tray_font(best_sz)

        length = len(val_str)
        # 3+ haneli sayılarda 'large', 'xlarge', 'max' seçildiğinde dikey yüksekliği koruyup tam dolgunluk sağla
        if length >= 3 and size_mode in ("large", "xlarge", "max"):
            stretch_cfg = {
                "large":  (34, 56 if bg_mode != "transparent" else 62),
                "xlarge": (40, 56 if bg_mode != "transparent" else 63),
                "max":    (46, 56 if bg_mode != "transparent" else 64)
            }
            target_h, target_w = stretch_cfg.get(size_mode, (34, 62))
            dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
            raw_bbox = dummy_draw.textbbox((0, 0), val_str, font=font)
            raw_w = raw_bbox[2] - raw_bbox[0]
            raw_h = raw_bbox[3] - raw_bbox[1]

            tmp_img = Image.new('RGBA', (raw_w + 4, raw_h + 4), (0, 0, 0, 0))
            ImageDraw.Draw(tmp_img).text((-raw_bbox[0] + 2, -raw_bbox[1] + 2), val_str, fill=text_color, font=font)
            scaled = tmp_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            x = int((64 - target_w) / 2)
            y = int((64 - target_h) / 2)
            img.paste(scaled, (x, y), scaled)
        else:
            tw = best_bbox[2] - best_bbox[0]
            th = best_bbox[3] - best_bbox[1]
            x = (64 - tw) / 2 - best_bbox[0]
            y = (64 - th) / 2 - best_bbox[1]
            draw.text((x, y), val_str, fill=text_color, font=font)

        # LRU benzeri sınır (max 32 simge)
        if len(self._badge_cache) > 32:
            self._badge_cache.clear()
        self._badge_cache[badge_cache_key] = img
        return img

    def _clear_tray_caches(self):
        """Ayar değişikliklerinde simge ve font önbelleklerini temizler."""
        if hasattr(self, '_font_cache'):
            self._font_cache.clear()
        if hasattr(self, '_font_sz_cache'):
            self._font_sz_cache.clear()
        if hasattr(self, '_badge_cache'):
            self._badge_cache.clear()
        if hasattr(self, '_dual_badge_cache'):
            self._dual_badge_cache.clear()
        self._cached_logo_img = None
        self._last_assigned_tray_icon = None

    def set_tray_mode(self, mode):
        self.config["tray_mode"] = mode
        self._clear_tray_caches()
        self.save_config()
        self._refresh_tray_icon()

    def set_tray_bg(self, bg_mode):
        self.config["tray_bg"] = bg_mode
        self._clear_tray_caches()
        self.save_config()
        self._refresh_tray_icon()

    def set_tray_fg(self, fg_mode):
        self.config["tray_fg"] = fg_mode
        self._clear_tray_caches()
        self.save_config()
        self._refresh_tray_icon()

    def set_tray_font(self, font_name):
        self.config["tray_font"] = font_name
        self._clear_tray_caches()
        self.save_config()
        self._refresh_tray_icon()

    def _refresh_tray_icon(self):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            hw = getattr(self, "_last_hw", {})
            img = self.create_tray_image(
                watt=getattr(self, "_last_watt", 0),
                cpu_temp=hw.get("cpu_temp", 0),
                gpu_temp=hw.get("gpu_temp", 0),
                cpu_uti=hw.get("cpu_uti", 0),
                gpu_uti=hw.get("gpu_uti", 0),
                hourly_tl=getattr(self, "_last_hourly", 0.0)
            )
            self._last_assigned_tray_icon = img
            try:
                self.tray_icon.icon = img
            except Exception:
                pass

    def create_tray_image(self, watt=0, cpu_temp=0, gpu_temp=0, cpu_uti=0, gpu_uti=0, hourly_tl=0.0):
        mode = self.config.get("tray_mode", "power_w")

        if mode == "logo":
            cached = getattr(self, '_cached_logo_img', None)
            if cached is not None:
                return cached
            cand_p = get_asset_path("app_icon.png")
            if os.path.exists(cand_p):
                try:
                    self._cached_logo_img = Image.open(cand_p).convert('RGBA').resize((64, 64), Image.Resampling.LANCZOS)
                    return self._cached_logo_img
                except Exception:
                    pass

        if mode == "power_w":
            w_int = int(round(watt))
            val_str = f"{w_int}" if w_int < 1000 else f"{watt/1000.0:.1f}k"

            # Kullanıcı Tanımlı Watt Renk Eşikleri (Varsayılan: 250W Sarı/Orta, 450W Kırmızı/Yüksek)
            th_warn = float(self.config.get("tray_watt_warn", 250.0))
            th_crit = float(self.config.get("tray_watt_crit", 450.0))

            if watt >= th_crit:
                col = (244, 63, 94, 255)  # Kırmızı (Yüksek Yük)
            elif watt >= th_warn:
                col = (251, 191, 36, 255)  # Sarı / Amber (Orta Yük)
            else:
                col = (0, 255, 255, 255)   # Cyan / Yeşil (Düşük Yük / Normal)
            return self._draw_tray_badge(val_str, col)

        elif mode == "cpu_temp":
            val_str = f"{int(round(cpu_temp))}"
            col = (244, 63, 94, 255) if cpu_temp >= 80 else ((245, 158, 11, 255) if cpu_temp >= 70 else (192, 132, 252, 255))
            return self._draw_tray_badge(val_str, col)

        elif mode == "gpu_temp":
            val_str = f"{int(round(gpu_temp))}"
            col = (244, 63, 94, 255) if gpu_temp >= 80 else ((245, 158, 11, 255) if gpu_temp >= 70 else (0, 255, 255, 255))
            return self._draw_tray_badge(val_str, col)

        elif mode == "cpu_uti":
            val_str = f"{int(round(cpu_uti))}"
            col = (244, 63, 94, 255) if cpu_uti >= 80 else ((245, 158, 11, 255) if cpu_uti >= 50 else (252, 211, 77, 255))
            return self._draw_tray_badge(val_str, col)

        elif mode == "gpu_uti":
            val_str = f"{int(round(gpu_uti))}"
            col = (244, 63, 94, 255) if gpu_uti >= 80 else ((245, 158, 11, 255) if gpu_uti >= 50 else (0, 255, 255, 255))
            return self._draw_tray_badge(val_str, col)

        elif mode == "hourly_tl":
            val_str = f"{hourly_tl:.1f}"
            col = (16, 255, 129, 255)
            return self._draw_tray_badge(val_str, col)

        else: # "dual_temp" veya fallback
            col_box = (244, 63, 94, 255) if (cpu_temp >= 80 or gpu_temp >= 80) else (16, 185, 129, 255)
            bg_mode = self.config.get("tray_bg", "transparent")
            fg_mode = self.config.get("tray_fg", "auto")
            font_choice = self.config.get("tray_font", "bahnschrift")
            size_mode = self.config.get("tray_font_size", "normal")
            c_text = f"C{int(round(cpu_temp))}"
            g_text = f"G{int(round(gpu_temp))}"

            dual_cache_key = (c_text, g_text, col_box, bg_mode, fg_mode, font_choice, size_mode)
            if not hasattr(self, '_dual_badge_cache'):
                self._dual_badge_cache = {}
            if dual_cache_key in self._dual_badge_cache:
                return self._dual_badge_cache[dual_cache_key]

            img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            if bg_mode == "dark":
                draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(8, 11, 20, 255), outline=col_box, width=2)
            elif bg_mode == "cyan":
                draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(0, 229, 255, 255))
            elif bg_mode == "green":
                draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(16, 185, 129, 255))
            elif bg_mode == "rose":
                draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(244, 63, 94, 255))
            elif bg_mode == "amber":
                draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(245, 158, 11, 255))
            elif bg_mode == "white":
                draw.rounded_rectangle([0, 0, 63, 63], radius=10, fill=(255, 255, 255, 255))

            dual_sz_map = {
                "small": 20,
                "normal": 28,   # 1.45x Normal varsayılanı
                "large": 33,
                "xlarge": 38,
                "max": 43
            }
            dual_sz = dual_sz_map.get(size_mode, 28)
            f_dual = self._get_tray_font(dual_sz)
            
            if fg_mode == "auto":
                col_c = (245, 158, 11, 255) if bg_mode in ("transparent", "dark") else (8, 11, 20, 255)
                col_g = (0, 255, 255, 255) if bg_mode in ("transparent", "dark") else (8, 11, 20, 255)
            elif fg_mode == "cyan":
                col_c = col_g = (0, 255, 255, 255)
            elif fg_mode == "green":
                col_c = col_g = (16, 255, 129, 255)
            elif fg_mode == "amber":
                col_c = col_g = (251, 191, 36, 255)
            elif fg_mode == "rose":
                col_c = col_g = (244, 63, 94, 255)
            elif fg_mode == "white":
                col_c = col_g = (255, 255, 255, 255)
            elif fg_mode == "black":
                col_c = col_g = (8, 11, 20, 255)
            elif fg_mode == "purple":
                col_c = col_g = (192, 132, 252, 255)
            else:
                col_c, col_g = (245, 158, 11, 255), (0, 255, 255, 255)

            bbox_c = draw.textbbox((0, 0), c_text, font=f_dual)
            tw_c = bbox_c[2] - bbox_c[0]
            th_c = bbox_c[3] - bbox_c[1]
            y_c = max(0, 16 - (th_c / 2)) - bbox_c[1]
            draw.text(((64 - tw_c) / 2 - bbox_c[0], y_c), c_text, fill=col_c, font=f_dual)
            
            line_col = (40, 50, 75, 255) if bg_mode in ("transparent", "dark") else (180, 180, 180, 255)
            draw.line([(4, 32), (60, 32)], fill=line_col, width=1)
            
            bbox_g = draw.textbbox((0, 0), g_text, font=f_dual)
            tw_g = bbox_g[2] - bbox_g[0]
            th_g = bbox_g[3] - bbox_g[1]
            y_g = max(33, 48 - (th_g / 2)) - bbox_g[1]
            draw.text(((64 - tw_g) / 2 - bbox_g[0], y_g), g_text, fill=col_g, font=f_dual)

            if len(self._dual_badge_cache) > 32:
                self._dual_badge_cache.clear()
            self._dual_badge_cache[dual_cache_key] = img
            return img

    def set_monitor_hz_from_tray(self, device_name: str, hz: int, mon_title: str = "Monitör"):
        """Sistem tepsisinden seçilen monitörün Hz değerini ayarlar."""
        def _apply():
            try:
                ok = False
                if device_name:
                    ok = DisplayManagerService.set_refresh_rate_for(device_name, hz)
                else:
                    ok = DisplayManagerService.set_refresh_rate(hz)
                if ok:
                    msg = _t("toast_hz_applied", "Monitör yenileme hızı {hz} Hz olarak ayarlandı").format(hz=hz)
                    if hasattr(self, 'show_power_plan_toast'):
                        self.show_power_plan_toast(
                            plan_name=f"{mon_title} • {hz} Hz",
                            icon="🖥️",
                            subtitle=msg
                        )
                if hasattr(self, 'tray_icon') and self.tray_icon:
                    try:
                        self.tray_icon.update_menu()
                    except Exception:
                        pass
            except Exception:
                pass
        self.root.after(0, _apply)

    def set_smart_tier_from_tray(self, tier_num: int):
        """Sistem tepsisinden Akıllı Geçiş kademesini manuel olarak uygular."""
        def _apply():
            try:
                sw = getattr(self, 'smart_switcher', None)
                if sw:
                    sw._apply_tier(f"Tier {tier_num}", reason="Tray Manual")
                    tier_names = {
                        1: _t("tray_tier_1", "1. Boşta / Ultra Eko"),
                        2: _t("tray_tier_2", "2. Düşük / Günlük & Medya"),
                        3: _t("tray_tier_3", "3. Orta / İş & Multitask"),
                        4: _t("tray_tier_4", "4. Maksimum / Oyun & Render")
                    }
                    if hasattr(self, 'show_power_plan_toast') and self.config.get("smart_switch_toast", True):
                        self.show_power_plan_toast(
                            plan_name=tier_names.get(tier_num, f"Kademe {tier_num}"),
                            icon="🤖",
                            subtitle=_t("toast_tier_applied", "Akıllı Geçiş: Kademe {tier} uygulandı").format(tier=tier_num)
                        )
                if hasattr(self, 'tray_icon') and self.tray_icon:
                    try:
                        self.tray_icon.update_menu()
                    except Exception:
                        pass
            except Exception:
                pass
        self.root.after(0, _apply)

    def toggle_rtss_from_tray(self, icon=None, item=None):
        self.root.after(0, self.toggle_rtss)
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.update_menu()
            except Exception:
                pass

    def activate_power_plan_from_tray(self, guid):
        guid_str = str(guid).strip()
        self.root.after(0, lambda: self.activate_power_plan(guid_str))

    def toggle_smart_switch_from_tray(self, icon=None, item=None):
        cur = bool(getattr(self.smart_switcher, 'enabled', False))
        new_val = not cur
        if hasattr(self, 'smart_switcher') and self.smart_switcher:
            self.smart_switcher.enabled = new_val
        self.config["smart_switch_enabled"] = new_val
        self.save_config()
        if hasattr(self, 'smart_switch_var'):
            self.root.after(0, lambda: self.smart_switch_var.set(new_val))
        if hasattr(self, 'on_smart_switch_toggled'):
            self.root.after(0, self.on_smart_switch_toggled)
        if hasattr(self, 'show_power_plan_toast') and self.config.get("smart_switch_toast", True):
            st = _t("smart_status_active", "Aktif Edildi") if new_val else _t("smart_status_disabled", "Devre Dışı")
            self.root.after(0, lambda: self.show_power_plan_toast(
                plan_name=_t("tab_smartswitch", "Akıllı Geçiş"),
                icon="🤖",
                subtitle=f"{_t('smart_switch_title', 'Akıllı Otomasyon')} {st}"
            ))
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.update_menu()
            except Exception:
                pass

    def toggle_autostart_from_tray(self, icon=None, item=None):
        cur = WindowsAutoStart.is_enabled()
        new_val = not cur
        WindowsAutoStart.set_enabled(new_val)
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.update_menu()
            except Exception:
                pass

    def build_tray_menu(self):
        def _get_hz_items_for_monitor(device_name, mon_idx=1, mon_title="Monitör 1"):
            try:
                if device_name:
                    rates = sorted(list(DisplayManagerService.get_supported_rates_for(device_name)))
                    cur_hz = DisplayManagerService.get_current_refresh_rate_for(device_name)
                else:
                    rates = sorted(list(DisplayManagerService.get_supported_refresh_rates()))
                    cur_hz = DisplayManagerService.get_current_refresh_rate()
            except Exception:
                rates = []
                cur_hz = 60

            if not rates:
                yield pystray.MenuItem("Hz Okunamadı", lambda icon=None, item=None: None, enabled=False)
                return

            def _make_hz_action(target_hz):
                return lambda icon=None, item=None: self.set_monitor_hz_from_tray(device_name, target_hz, mon_title)

            def _make_hz_checked(target_hz):
                def _chk(item):
                    try:
                        if device_name:
                            now_hz = DisplayManagerService.get_current_refresh_rate_for(device_name)
                        else:
                            now_hz = DisplayManagerService.get_current_refresh_rate()
                        return now_hz == target_hz
                    except Exception:
                        return False
                return _chk

            for r in rates:
                yield pystray.MenuItem(
                    f"{r} Hz",
                    _make_hz_action(r),
                    checked=_make_hz_checked(r)
                )

        def _get_monitor_menu_items():
            try:
                monitors = DisplayManagerService.get_monitors()
            except Exception:
                monitors = []

            if not monitors:
                monitors = [{"device_name": "", "name": "Monitör 1"}]

            mon1 = monitors[0]
            dev1 = mon1.get("device_name", "")
            title1 = _t("tray_menu_monitor_hz", "🖥️ Monitör Yenileme Hızı (Hz)")

            # Monitör 1'in desteklediği frekansları doğrudan yield et
            for item in _get_hz_items_for_monitor(dev1, 1, title1):
                yield item

            # Eğer 2. monitör bağlıysa, onun için bir alt menü ekle
            if len(monitors) > 1:
                mon2 = monitors[1]
                dev2 = mon2.get("device_name", "")
                title2 = _t("tray_menu_second_monitor_hz", "🖥️ 2. Monitör Hz")
                yield pystray.Menu.SEPARATOR
                yield pystray.MenuItem(
                    title2,
                    pystray.Menu(lambda: _get_hz_items_for_monitor(dev2, 2, title2))
                )

        def _get_smart_tier_items():
            sw = getattr(self, 'smart_switcher', None)
            tier_defs = [
                (1, _t("tray_tier_1", "1. Boşta / Ultra Eko")),
                (2, _t("tray_tier_2", "2. Düşük / Günlük & Medya")),
                (3, _t("tray_tier_3", "3. Orta / İş & Multitask")),
                (4, _t("tray_tier_4", "4. Maksimum / Oyun & Render")),
            ]

            def _make_tier_action(t_num):
                return lambda icon=None, item=None: self.set_smart_tier_from_tray(t_num)

            def _make_tier_checked(t_num):
                def _chk(item):
                    if not sw:
                        return False
                    c_tier = str(getattr(sw, 'current_tier', '')).lower()
                    return f"tier {t_num}" in c_tier or f"tier{t_num}" in c_tier
                return _chk

            for t_num, t_label in tier_defs:
                yield pystray.MenuItem(
                    t_label,
                    _make_tier_action(t_num),
                    checked=_make_tier_checked(t_num)
                )

        def _get_power_plan_items():
            try:
                plans = PowerManagerService.get_power_plans()
            except Exception:
                plans = []

            if not plans:
                yield pystray.MenuItem(_t("tray_no_plans", "Güç Planı Bulunamadı"), lambda icon=None, item=None: None, enabled=False)
                return

            def _make_action(target_guid):
                return lambda icon=None, item=None: self.activate_power_plan_from_tray(target_guid)

            def _make_checked(target_guid):
                return lambda item: (PowerManagerService.get_active_guid_fast().lower() == str(target_guid).lower())

            for p in plans:
                display_name = f"{getattr(p, 'badge_icon', '⚡')} {p.name}"
                yield pystray.MenuItem(
                    display_name,
                    _make_action(p.guid),
                    checked=_make_checked(p.guid)
                )

        return pystray.Menu(
            pystray.MenuItem(_t("tray_menu_toggle_win", "👁️ Pencereyi Göster / Gizle"), self.toggle_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                _t("tray_menu_monitor_hz", "🖥️ Monitör Yenileme Hızı (Hz)"),
                pystray.Menu(_get_monitor_menu_items)
            ),
            pystray.MenuItem(
                _t("tray_menu_smart_tiers", "🤖 Akıllı Kademeler"),
                pystray.Menu(_get_smart_tier_items)
            ),
            pystray.MenuItem(
                _t("tray_menu_power_plans", "⚡ Güç Planları"),
                pystray.Menu(_get_power_plan_items)
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                _t("tray_menu_rtss", "🎮 RivaTuner (RTSS) OSD"),
                self.toggle_rtss_from_tray,
                checked=lambda item: bool(self.config.get("rtss_enabled", True))
            ),
            pystray.MenuItem(
                _t("tray_menu_smart_switch", "🤖 Akıllı Geçiş Otomasyonu"),
                self.toggle_smart_switch_from_tray,
                checked=lambda item: bool(getattr(self.smart_switcher, 'enabled', False))
            ),
            pystray.MenuItem(
                _t("tray_menu_autostart", "🚀 Windows Başlangıcında Çalıştır"),
                self.toggle_autostart_from_tray,
                checked=lambda item: WindowsAutoStart.is_enabled()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(_t("tray_menu_exit", "✕ Uygulamayı Kapat"), self.quit_app)
        )

    def init_tray_icon(self):
        icon_img = self.create_tray_image(0, 0, 0)
        menu = self.build_tray_menu()
        self.tray_icon = pystray.Icon("wattcost_haytool", icon_img, _t("tray_app_tooltip", "WattCost HaYTooL"), menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def toggle_always_on_top_from_tray(self, icon=None, item=None):
        self.root.after(0, self.toggle_always_on_top)

    def on_window_close_clicked(self):
        if self.config.get("close_to_tray", True):
            self.hide_to_tray()
        else:
            self.quit_app()

    def hide_to_tray(self):
        if hasattr(self, '_save_window_geometry'):
            try:
                self._save_window_geometry()
            except Exception:
                pass
        self.root.withdraw()

    def show_from_tray(self):
        try:
            apply_dark_titlebar(self.root)
            self.root.deiconify()
            self.root.update_idletasks()
            self.root.lift()
            self.root.focus_force()
            if hasattr(self, 'apply_always_on_top'):
                self.apply_always_on_top()
        except Exception:
            pass

    def toggle_window(self):
        if self.root.winfo_viewable():
            self.root.after(0, self.hide_to_tray)
        else:
            self.root.after(0, self.show_from_tray)

    def quit_app(self):
        if hasattr(self, '_save_window_geometry'):
            try:
                self._save_window_geometry()
            except Exception:
                pass
        try:
            HistoryManager.flush_history()
        except Exception:
            pass
        if hasattr(self, 'zalman') and self.zalman:
            try:
                self.zalman.stop_background_loop()
            except Exception:
                pass
        if hasattr(self, 'hotkey_mgr') and self.hotkey_mgr:
            try:
                self.hotkey_mgr.stop()
            except Exception:
                pass
        if hasattr(self, 'headset') and self.headset:
            try:
                self.headset.stop()
            except Exception:
                pass
        try:
            if hasattr(self, 'rtss') and self.rtss:
                self.rtss.release_osd()
        except Exception:
            pass
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)
