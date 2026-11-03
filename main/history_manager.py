"""
WattCost HaYTooL - Tüketim Geçmişi ve Otomatik Başlatma Modülü
Günlük ve aylık enerji/harcama takibi, JSON veritabanı ve geçmiş rapor penceresi.
"""
import os
import json
import time
import winreg
import tkinter as tk
from config_manager import THEME, fs, get_config_path
from language_manager import _t

class HistoryManager:
    HISTORY_FILE = "WattCost. HaYTooL.json"
    _history_cache = None
    _last_save_time = 0.0
    _dirty = False

    @classmethod
    def load_history(cls):
        if cls._history_cache is not None:
            return cls._history_cache

        target_file = get_config_path(cls.HISTORY_FILE)
        # 1. Güncel dosya adını kontrol et
        if os.path.exists(target_file):
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    cls._history_cache = json.load(f)
                    return cls._history_cache
            except Exception:
                pass

        # 2. Eski isimlerden (consumption_history.json veya tuketim_gecmisi.json) verileri kaybetmeden taşı
        for old_file in ["consumption_history.json", "tuketim_gecmisi.json"]:
            old_path = get_config_path(old_file)
            if os.path.exists(old_path):
                try:
                    with open(old_path, "r", encoding="utf-8") as f:
                        old_data = json.load(f)
                    with open(target_file, "w", encoding="utf-8") as f:
                        json.dump(old_data, f, indent=4, ensure_ascii=False)
                    cls._history_cache = old_data
                    return cls._history_cache
                except Exception:
                    pass
        cls._history_cache = {}
        return cls._history_cache

    @classmethod
    def flush_history(cls):
        """Bellekteki geçmiş verisini diske kaydeder."""
        if cls._history_cache is not None and cls._dirty:
            try:
                target_file = get_config_path(cls.HISTORY_FILE)
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(cls._history_cache, f, indent=4, ensure_ascii=False)
                cls._dirty = False
                cls._last_save_time = time.time()
            except Exception:
                pass

    @classmethod
    def add_energy(cls, wh, price_per_kwh):
        today = time.strftime("%Y-%m-%d")
        history = cls.load_history()
        
        if today not in history:
            history[today] = {
                "wh": 0.0,
                "kwh": 0.0,
                "cost_tl": 0.0,
                "active_seconds": 0
            }
            
        history[today]["wh"] += wh
        history[today]["kwh"] = history[today]["wh"] / 1000.0
        history[today]["cost_tl"] = history[today]["kwh"] * price_per_kwh
        history[today]["active_seconds"] += 1
        cls._dirty = True

        # Her 60 saniyede bir diske yaz (1 Hz disk I/O darboğazını ortadan kaldırır)
        now = time.time()
        if now - cls._last_save_time >= 60.0:
            cls.flush_history()

    @classmethod
    def get_summary(cls):
        history = cls.load_history()
        today = time.strftime("%Y-%m-%d")
        current_month = time.strftime("%Y-%m")
        
        today_entry = history.get(today, {})
        today_tl = today_entry.get("cost_tl", 0.0)
        today_kwh = today_entry.get("kwh", 0.0)
        
        month_tl = 0.0
        month_kwh = 0.0
        for date_str, data in history.items():
            if date_str.startswith(current_month):
                month_tl += data.get("cost_tl", 0.0)
                month_kwh += data.get("kwh", 0.0)
                
        return {
            "today_tl": today_tl,
            "today_kwh": today_kwh,
            "month_tl": month_tl,
            "month_kwh": month_kwh,
            "history": history
        }

class WindowsAutoStart:
    REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "WattCostHaYTooL"

    @classmethod
    def is_enabled(cls):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, cls.APP_NAME)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    @classmethod
    def ensure_tray_flag(cls):
        """Eski otomatik baslatma kaydinda --tray yoksa komutu gunceller (acilista tepside baslar)."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE)
            try:
                val, _ = winreg.QueryValueEx(key, cls.APP_NAME)
                if "--tray" not in val:
                    winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, val.rstrip() + " --tray")
            finally:
                winreg.CloseKey(key)
        except FileNotFoundError:
            pass
        except Exception:
            pass

    @classmethod
    def set_enabled(cls, enable=True):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY, 0, winreg.KEY_SET_VALUE)
            if enable:
                import sys
                if getattr(sys, 'frozen', False):
                    target_exe = sys.executable
                else:
                    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    cand_dist = os.path.join(base_dir, "dist", "WattCost. HaYTooL.exe")
                    cand_local = os.path.join(os.getcwd(), "dist", "WattCost. HaYTooL.exe")
                    cand_root = os.path.join(base_dir, "WattCost. HaYTooL.exe")
                    if os.path.isfile(cand_dist):
                        target_exe = cand_dist
                    elif os.path.isfile(cand_local):
                        target_exe = cand_local
                    elif os.path.isfile(cand_root):
                        target_exe = cand_root
                    else:
                        target_exe = sys.executable
                cmd = f'"{target_exe}" --tray'
                winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, cls.APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

class HistoryReportMixin:
    """Tüketim geçmişi rapor penceresini açan metotları barındıran mixin."""

    def open_history_report(self):
        f_font = THEME["font_family"]
        top = tk.Toplevel(self.root)
        self.apply_window_icon(top)
        top.title(_t("history_title", "Elektrik Tüketim Raporu"))
        top.geometry("450x420")
        top.configure(bg=THEME["bg"])
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        summary = HistoryManager.get_summary()

        # Başlık
        f_hdr = tk.Frame(top, bg=THEME["bg"])
        f_hdr.pack(fill="x", padx=16, pady=(14, 10))
        tk.Label(f_hdr, text=_t("history_header", "📊 ENERJİ TÜKETİM RAPORU"), font=(f_font, 10, "bold"),
                 fg=THEME["accent_cyan"], bg=THEME["bg"]).pack(side="left")
        self.make_btn(f_hdr, "✕", top.destroy, fg=THEME["text_muted"], bg=THEME["bg"], padx=6).pack(side="right")

        # Bugün & Bu Ay Özet Kartı
        card_sum = self.create_card(top, pady=(0, 10))
        
        f_row_today = tk.Frame(card_sum, bg=THEME["card_bg"])
        f_row_today.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(f_row_today, text=_t("history_today_total", "BUGÜNKÜ TOPLAM:"), font=(f_font, 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")
        h_unit = _t("unit_hours_short", "s")
        m_unit = _t("unit_mins_short", "d")
        tk.Label(f_row_today, text=f"{self.format_currency(summary['today_tl'])}  ({summary['today_kwh']:.2f} kWh)",
                 font=(f_font, 9, "bold"), fg=THEME["accent_green"], bg=THEME["card_bg"]).pack(side="right")

        tk.Frame(card_sum, bg=THEME["card_border"], height=1).pack(fill="x", padx=12, pady=2)

        f_row_month = tk.Frame(card_sum, bg=THEME["card_bg"])
        f_row_month.pack(fill="x", padx=12, pady=6)
        tk.Label(f_row_month, text=_t("history_month_total", "BU AYKİ TOPLAM (FATURA):"), font=(f_font, 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")
        tk.Label(f_row_month, text=f"{self.format_currency(summary['month_tl'])}  ({summary['month_kwh']:.2f} kWh)",
                 font=(f_font, 9, "bold"), fg=THEME["accent_amber"], bg=THEME["card_bg"]).pack(side="right")

        # Geçmiş Günler Başlığı
        tk.Label(top, text=_t("history_recent_days", "SON GÜNLERİN TÜKETİM GEÇMİŞİ"), font=(f_font, 7, "bold"),
                 fg=THEME["text_muted"], bg=THEME["bg"]).pack(anchor="w", padx=16, pady=(10, 4))

        # Liste Kutusu (Frame + Scroll)
        f_list = tk.Frame(top, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_list.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # Gün gün ters kronolojik sırala
        history_items = sorted(summary["history"].items(), key=lambda x: x[0], reverse=True)
        if not history_items:
            tk.Label(f_list, text=_t("history_no_records", "Henüz kayıtlı geçmiş bulunmuyor."), font=(f_font, 8), fg=THEME["text_muted"], bg=THEME["card_bg"]).pack(pady=20)
        else:
            for d_str, d_data in history_items[:8]:
                r = tk.Frame(f_list, bg=THEME["card_bg"])
                r.pack(fill="x", padx=10, pady=3)
                
                secs = d_data.get("active_seconds", 0)
                dur_str = f"{secs//3600:02d}{h_unit} {((secs%3600)//60):02d}{m_unit}"
                
                tk.Label(r, text=f"{d_str} ({dur_str})", font=(f_font, 8), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(side="left")
                tk.Label(r, text=f"{self.format_currency(d_data.get('cost_tl', 0.0))}", font=(f_font, 8, "bold"), fg=THEME["text_primary"], bg=THEME["card_bg"]).pack(side="right")
                tk.Label(r, text=f"{d_data.get('kwh', 0.0):.2f} kWh", font=(f_font, 7), fg=THEME["text_muted"], bg=THEME["card_bg"]).pack(side="right", padx=6)
