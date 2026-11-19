"""
WattCost HaYTooL - Tüketim Geçmişi ve Otomatik Başlatma Modülü
Günlük, haftalık, aylık ve yıllık enerji/harcama takibi, taşınabilir JSON veritabanı ve analiz raporu.
"""
import datetime
import json
import os
import shutil
import time
import winreg
from config_manager import THEME, UI_SCALE, fs, get_app_data_path, get_config_path, apply_dark_titlebar
from language_manager import _t


def _calc_avg_watt(wh: float, active_seconds: int) -> float:
    if active_seconds <= 0 or wh <= 0:
        return 0.0
    return (wh * 3600.0) / active_seconds


def _format_duration_compact(active_seconds: int) -> str:
    sec = max(0, int(active_seconds or 0))
    hrs = sec // 3600
    mins = (sec % 3600) // 60
    h_u = _t("unit_hours_short", "s")
    m_u = _t("unit_mins_short", "d")
    if hrs > 0:
        return f"{hrs}{h_u} {mins:02d}{m_u}"
    return f"{mins}{m_u}"


class HistoryManager:
    HISTORY_FILE = "WattCost. HaYTooL.json"
    _history_cache = None
    _last_save_time = 0.0
    _dirty = False
    _pending_deltas = {}
    _cached_prior_key = None
    _cached_prior_tl = 0.0
    _cached_prior_kwh = 0.0

    @classmethod
    def get_history_file_path(cls) -> str:
        """Tüketim veritabanını her zaman EXE / proje kök dizinine sabitler."""
        return get_app_data_path(cls.HISTORY_FILE)

    @classmethod
    def _read_json_dict(cls, path: str):
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return None

    @classmethod
    def load_history(cls):
        if cls._history_cache is not None:
            return cls._history_cache

        target_file = cls.get_history_file_path()
        # 1. Doğrudan EXE/kök yanındaki dosyayı veya .bak yedeğini oku
        data = cls._read_json_dict(target_file)
        if data is not None:
            cls._history_cache = data
            return cls._history_cache

        bak_data = cls._read_json_dict(target_file + ".bak")
        if bak_data is not None:
            cls._history_cache = bak_data
            return cls._history_cache

        # 2. Eski isimlerden veya çalışma dizininden verileri EXE yanına taşı
        for legacy_name in (cls.HISTORY_FILE, "consumption_history.json", "tuketim_gecmisi.json"):
            cand = get_config_path(legacy_name)
            if os.path.abspath(cand) == os.path.abspath(target_file):
                continue
            legacy_data = cls._read_json_dict(cand)
            if legacy_data is not None:
                cls._history_cache = legacy_data
                cls._dirty = True
                cls.flush_history()
                return cls._history_cache

        cls._history_cache = {}
        return cls._history_cache

    @classmethod
    def flush_history(cls):
        """Çoklu oturum farklarını diskle birleştirip atomik (.tmp + .bak) olarak diske yazar."""
        if cls._history_cache is None or not cls._dirty:
            return
        target_file = cls.get_history_file_path()
        try:
            os.makedirs(os.path.dirname(os.path.abspath(target_file)), exist_ok=True)
            disk_data = cls._read_json_dict(target_file)
            if disk_data is not None and cls._pending_deltas:
                merged = {k: dict(v) for k, v in disk_data.items() if isinstance(v, dict)}
                for day_key, delta in cls._pending_deltas.items():
                    base = merged.setdefault(day_key, {"wh": 0.0, "kwh": 0.0, "cost_tl": 0.0, "active_seconds": 0})
                    base["wh"] = float(base.get("wh", 0.0)) + float(delta.get("wh", 0.0))
                    base["kwh"] = base["wh"] / 1000.0
                    base["cost_tl"] = float(base.get("cost_tl", 0.0)) + float(delta.get("cost_tl", 0.0))
                    base["active_seconds"] = int(base.get("active_seconds", 0)) + int(delta.get("active_seconds", 0))
                cls._history_cache = merged
                cls._cached_prior_key = None

            if os.path.exists(target_file):
                try:
                    shutil.copy2(target_file, target_file + ".bak")
                except Exception:
                    pass

            tmp_file = target_file + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(cls._history_cache, f, indent=4, ensure_ascii=False)
            os.replace(tmp_file, target_file)
            cls._pending_deltas.clear()
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

        cost_delta = (wh / 1000.0) * price_per_kwh
        history[today]["wh"] = float(history[today].get("wh", 0.0)) + wh
        history[today]["kwh"] = history[today]["wh"] / 1000.0
        history[today]["cost_tl"] = float(history[today].get("cost_tl", 0.0)) + cost_delta
        history[today]["active_seconds"] = int(history[today].get("active_seconds", 0)) + 1

        d_delta = cls._pending_deltas.setdefault(today, {"wh": 0.0, "cost_tl": 0.0, "active_seconds": 0})
        d_delta["wh"] += wh
        d_delta["cost_tl"] += cost_delta
        d_delta["active_seconds"] += 1

        cls._dirty = True

        # Her 60 saniyede bir diske yaz (1 Hz disk I/O darboğazını ortadan kaldırır)
        now = time.time()
        if now - cls._last_save_time >= 60.0:
            cls.flush_history()

    @classmethod
    def get_summary(cls):
        history = cls.load_history()
        today = time.strftime("%Y-%m-%d")
        current_month = today[:7]

        today_entry = history.get(today, {})
        today_tl = today_entry.get("cost_tl", 0.0)
        today_kwh = today_entry.get("kwh", 0.0)

        cache_key = (id(history), today, len(history))
        if cls._cached_prior_key != cache_key:
            prior_tl = 0.0
            prior_kwh = 0.0
            for date_str, data in history.items():
                if date_str != today and date_str.startswith(current_month):
                    prior_tl += data.get("cost_tl", 0.0)
                    prior_kwh += data.get("kwh", 0.0)
            cls._cached_prior_key = cache_key
            cls._cached_prior_tl = prior_tl
            cls._cached_prior_kwh = prior_kwh

        return {
            "today_tl": today_tl,
            "today_kwh": today_kwh,
            "month_tl": cls._cached_prior_tl + today_tl,
            "month_kwh": cls._cached_prior_kwh + today_kwh,
            "history": history
        }

    @classmethod
    def _aggregate_dates(cls, history: dict, date_pred) -> dict:
        wh = 0.0
        kwh = 0.0
        tl = 0.0
        secs = 0
        days = 0
        for d_str, d_obj in history.items():
            if not isinstance(d_obj, dict):
                continue
            if date_pred(d_str):
                wh += float(d_obj.get("wh", 0.0) or 0.0)
                kwh += float(d_obj.get("kwh", 0.0) or 0.0)
                tl += float(d_obj.get("cost_tl", 0.0) or 0.0)
                secs += int(d_obj.get("active_seconds", 0) or 0)
                if d_obj.get("active_seconds", 0) or d_obj.get("wh", 0):
                    days += 1
        return {
            "wh": wh,
            "kwh": kwh,
            "tl": tl,
            "active_seconds": secs,
            "avg_watt": _calc_avg_watt(wh, secs),
            "days_count": days,
        }

    @classmethod
    def get_extended_summary(cls) -> dict:
        """Bugün, Bu Hafta, Geçen Hafta, Bu Ay, Bu Yıl ve Tüm Zamanlar özetlerini döner."""
        history = cls.load_history()
        today_dt = datetime.date.today()
        today_str = today_dt.strftime("%Y-%m-%d")
        this_week_mon = today_dt - datetime.timedelta(days=today_dt.weekday())
        this_week_sun = this_week_mon + datetime.timedelta(days=6)
        last_week_mon = this_week_mon - datetime.timedelta(days=7)
        last_week_sun = this_week_mon - datetime.timedelta(days=1)

        tw_start, tw_end = this_week_mon.strftime("%Y-%m-%d"), this_week_sun.strftime("%Y-%m-%d")
        lw_start, lw_end = last_week_mon.strftime("%Y-%m-%d"), last_week_sun.strftime("%Y-%m-%d")
        cur_month = today_str[:7]
        cur_year = today_str[:4]

        months = sorted({d[:7] for d in history.keys() if len(d) >= 7}, reverse=True)
        if cur_month not in months:
            months.insert(0, cur_month)
        years = sorted({d[:4] for d in history.keys() if len(d) >= 4}, reverse=True)
        if cur_year not in years:
            years.insert(0, cur_year)

        return {
            "today": cls._aggregate_dates(history, lambda d: d == today_str),
            "this_week": cls._aggregate_dates(history, lambda d: tw_start <= d <= tw_end),
            "last_week": cls._aggregate_dates(history, lambda d: lw_start <= d <= lw_end),
            "this_month": cls._aggregate_dates(history, lambda d: d.startswith(cur_month)),
            "this_year": cls._aggregate_dates(history, lambda d: d.startswith(cur_year)),
            "all_time": cls._aggregate_dates(history, lambda _d: True),
            "months": months,
            "years": years,
            "history": history,
        }

    @classmethod
    def get_period_rows(cls, mode: str, filter_val: str = "") -> tuple:
        """Seçili dönem için (satır listesi, toplam dict) döner."""
        history = cls.load_history()
        today_dt = datetime.date.today()
        rows = []

        def _make_day_row(d_str: str) -> dict:
            d_obj = history.get(d_str, {}) if isinstance(history.get(d_str), dict) else {}
            wh = float(d_obj.get("wh", 0.0) or 0.0)
            kwh = float(d_obj.get("kwh", 0.0) or 0.0)
            tl = float(d_obj.get("cost_tl", 0.0) or 0.0)
            secs = int(d_obj.get("active_seconds", 0) or 0)
            try:
                dt_obj = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
                wday = dt_obj.weekday()
            except Exception:
                wday = -1
            return {
                "key": d_str,
                "kind": "day",
                "weekday": wday,
                "wh": wh,
                "kwh": kwh,
                "tl": tl,
                "active_seconds": secs,
                "avg_watt": _calc_avg_watt(wh, secs),
            }

        if mode in ("this_week", "last_week"):
            mon = today_dt - datetime.timedelta(days=today_dt.weekday())
            if mode == "last_week":
                mon = mon - datetime.timedelta(days=7)
            for offset in range(7):
                d_str = (mon + datetime.timedelta(days=offset)).strftime("%Y-%m-%d")
                rows.append(_make_day_row(d_str))
        elif mode == "monthly":
            target_m = filter_val or today_dt.strftime("%Y-%m")
            for d_str in sorted((k for k in history.keys() if k.startswith(target_m)), reverse=True):
                rows.append(_make_day_row(d_str))
        elif mode == "yearly":
            target_y = filter_val or today_dt.strftime("%Y")
            for m_idx in range(1, 13):
                m_key = f"{target_y}-{m_idx:02d}"
                agg = cls._aggregate_dates(history, lambda d, mk=m_key: d.startswith(mk))
                if agg["active_seconds"] > 0 or agg["wh"] > 0 or m_key <= today_dt.strftime("%Y-%m"):
                    rows.append({
                        "key": m_key,
                        "kind": "month",
                        "month_idx": m_idx - 1,
                        "wh": agg["wh"],
                        "kwh": agg["kwh"],
                        "tl": agg["tl"],
                        "active_seconds": agg["active_seconds"],
                        "avg_watt": agg["avg_watt"],
                        "days_count": agg["days_count"],
                    })
        else:
            for d_str in sorted(history.keys(), reverse=True):
                rows.append(_make_day_row(d_str))

        tot_wh = sum(r["wh"] for r in rows)
        tot_kwh = sum(r["kwh"] for r in rows)
        tot_tl = sum(r["tl"] for r in rows)
        tot_secs = sum(r["active_seconds"] for r in rows)
        totals = {
            "wh": tot_wh,
            "kwh": tot_kwh,
            "tl": tot_tl,
            "active_seconds": tot_secs,
            "avg_watt": _calc_avg_watt(tot_wh, tot_secs),
        }
        return rows, totals


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
    """Haftalık, aylık, yıllık ve gün bazlı tüketim & ücretlendirme rapor penceresi."""

    def open_history_report(self):
        import subprocess
        import tkinter as tk
        from tkinter import ttk

        HistoryManager.flush_history()
        f_font = THEME["font_family"]
        top = tk.Toplevel(self.root)
        self.apply_window_icon(top)
        top.title(_t("history_title", "Elektrik Tüketim Raporu"))
        w_win = min(top.winfo_screenwidth() - 40, int(760 * UI_SCALE))
        h_win = min(top.winfo_screenheight() - 60, int(580 * UI_SCALE))
        px = max(10, (top.winfo_screenwidth() - w_win) // 2)
        py = max(10, (top.winfo_screenheight() - h_win) // 2)
        top.geometry(f"{w_win}x{h_win}+{px}+{py}")
        top.configure(bg=THEME["bg"])
        apply_dark_titlebar(top)
        top.transient(self.root)
        top.grab_set()

        ext = HistoryManager.get_extended_summary()

        # Üst Başlık
        f_hdr = tk.Frame(top, bg=THEME["bg"])
        f_hdr.pack(fill="x", padx=14, pady=(12, 8))
        tk.Label(f_hdr, text=_t("history_header", "📊 ENERJİ TÜKETİM RAPORU"),
                 font=(f_font, fs(11), "bold"), fg=THEME["accent_cyan"], bg=THEME["bg"]).pack(side="left")
        self.make_btn(f_hdr, "✕", top.destroy, fg=THEME["text_muted"], bg=THEME["bg"], padx=6).pack(side="right")

        # 4 Özet Kart (Bugün | Bu Hafta | Bu Ay | Bu Yıl)
        f_cards = tk.Frame(top, bg=THEME["bg"])
        f_cards.pack(fill="x", padx=14, pady=(0, 8))
        for idx, (lbl_key, lbl_def, bucket, accent) in enumerate([
            ("hero_daily", "BUGÜN", ext["today"], THEME["accent_green"]),
            ("history_week_total", "BU HAFTA", ext["this_week"], THEME["accent_cyan"]),
            ("history_month_total", "BU AY", ext["this_month"], THEME["accent_amber"]),
            ("history_year_total", "BU YIL", ext["this_year"], THEME["accent_purple"]),
        ]):
            title_txt = _t(lbl_key, lbl_def).replace(":", "").replace("(FATURA)", "").strip()
            if lbl_key == "hero_daily" and self.lang_mgr.active_language_code == "tr":
                title_txt = _t("history_today_total", "BUGÜNKÜ TOPLAM:").replace(":", "")
            c = tk.Frame(f_cards, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
            c.pack(side="left", fill="both", expand=True, padx=(0 if idx == 0 else 4, 4 if idx < 3 else 0))
            tk.Frame(c, bg=accent, height=2).pack(fill="x")
            tk.Label(c, text=title_txt, font=(f_font, fs(7), "bold"), fg=THEME["text_muted"], bg=THEME["card_bg"]).pack(anchor="w", padx=8, pady=(5, 1))
            tk.Label(c, text=self.format_currency(bucket["tl"], 2), font=(f_font, fs(12), "bold"), fg=accent, bg=THEME["card_bg"]).pack(anchor="w", padx=8)
            sub_txt = f"{bucket['kwh']:.2f} kWh • {_format_duration_compact(bucket['active_seconds'])}"
            tk.Label(c, text=sub_txt, font=(f_font, fs(7)), fg=THEME["text_secondary"], bg=THEME["card_bg"]).pack(anchor="w", padx=8, pady=(0, 6))

        # Dönem Seçim Çubuğu
        f_filters = tk.Frame(top, bg=THEME["bg"])
        f_filters.pack(fill="x", padx=14, pady=(0, 6))

        active_mode = ["last_week"] if ext["last_week"]["active_seconds"] > 0 else ["this_week"]
        mode_btns = {}

        cb_sub = ttk.Combobox(f_filters, values=[], state="readonly", width=12, font=(f_font, fs(8)))

        # Tablo Başlık Satırı
        f_tbl_wrap = tk.Frame(top, bg=THEME["card_bg"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_tbl_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 6))

        f_thead = tk.Frame(f_tbl_wrap, bg=THEME["card_inner"])
        f_thead.pack(fill="x")
        for col_txt, col_w, anch in [
            (_t("history_col_date", "Tarih / Dönem"), 24, "w"),
            ("", 14, "w"),
            (_t("history_col_duration", "Süre"), 10, "e"),
            (_t("history_col_avg_w", "Ort. Güç"), 10, "e"),
            (_t("history_col_kwh", "Tüketim"), 11, "e"),
            (_t("history_col_cost", "Ücret"), 12, "e"),
        ]:
            tk.Label(f_thead, text=col_txt, width=col_w, anchor=anch,
                     font=(f_font, fs(7), "bold"), fg=THEME["accent_cyan"], bg=THEME["card_inner"], padx=6, pady=5).pack(side="left")

        canvas = tk.Canvas(f_tbl_wrap, bg=THEME["card_bg"], highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(f_tbl_wrap, orient="vertical", command=canvas.yview)
        f_rows = tk.Frame(canvas, bg=THEME["card_bg"])
        f_rows_id = canvas.create_window((0, 0), window=f_rows, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        def _on_rows_cfg(e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        f_rows.bind("<Configure>", _on_rows_cfg)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(f_rows_id, width=e.width))

        def _on_mousewheel(e):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)

        # Dönem Toplam Bandı
        f_total_bar = tk.Frame(top, bg=THEME["card_inner"], highlightbackground=THEME["card_border"], highlightthickness=1)
        f_total_bar.pack(fill="x", padx=14, pady=(0, 6))
        lbl_period_tot = tk.Label(f_total_bar, text="", font=(f_font, fs(8), "bold"), fg=THEME["accent_cyan"], bg=THEME["card_inner"])
        lbl_period_tot.pack(side="left", padx=10, pady=5)
        lbl_period_vals = tk.Label(f_total_bar, text="", font=(f_font, fs(9), "bold"), fg=THEME["accent_green"], bg=THEME["card_inner"])
        lbl_period_vals.pack(side="right", padx=10, pady=5)

        weekday_names = _t("history_weekdays", "Pazartesi,Salı,Çarşamba,Perşembe,Cuma,Cumartesi,Pazar").split(",")
        month_names = _t("history_months", "Ocak,Şubat,Mart,Nisan,Mayıs,Haziran,Temmuz,Ağustos,Eylül,Ekim,Kasım,Aralık").split(",")

        def _format_row_label(r: dict) -> str:
            if r["kind"] == "month":
                m_idx = r.get("month_idx", 0)
                m_name = month_names[m_idx] if 0 <= m_idx < len(month_names) else r["key"]
                d_cnt = r.get("days_count", 0)
                return f"{m_name} {r['key'][:4]} ({_t('history_days_active', '{n} gün').format(n=d_cnt)})"
            d_str = r["key"]
            try:
                parts = d_str.split("-")
                pretty = f"{parts[2]}.{parts[1]}.{parts[0]}"
            except Exception:
                pretty = d_str
            wd = r.get("weekday", -1)
            wname = weekday_names[wd] if 0 <= wd < len(weekday_names) else ""
            return f"{pretty} • {wname}" if wname else pretty

        def _render_table():
            for w in f_rows.winfo_children():
                w.destroy()

            mode = active_mode[0]
            for m_id, btn in mode_btns.items():
                is_act = (m_id == mode)
                btn.config(bg=THEME["accent_cyan"] if is_act else THEME["btn_bg"],
                           fg=THEME["bg"] if is_act else THEME["text_primary"])

            f_val = cb_sub.get() if cb_sub.winfo_ismapped() else ""
            rows, totals = HistoryManager.get_period_rows(mode, f_val)

            if not rows:
                tk.Label(f_rows, text=_t("history_no_records", "Henüz kayıtlı geçmiş bulunmuyor."),
                         font=(f_font, fs(8)), fg=THEME["text_muted"], bg=THEME["card_bg"]).pack(pady=24)
                lbl_period_tot.config(text=_t("history_period_total", "Seçili Dönem Toplamı:"))
                lbl_period_vals.config(text=f"{self.format_currency(0.0, 2)}  •  0.000 kWh")
                return

            max_kwh = max((r["kwh"] for r in rows), default=0.0) or 1.0
            for idx, r in enumerate(rows):
                row_bg = THEME["card_bg"] if idx % 2 == 0 else THEME["bg"]
                is_empty = (r["active_seconds"] == 0 and r["wh"] <= 0.0)
                rf = tk.Frame(f_rows, bg=row_bg)
                rf.pack(fill="x")

                fg_main = THEME["text_muted"] if is_empty else THEME["text_primary"]
                fg_cost = THEME["text_muted"] if is_empty else THEME["accent_green"]

                tk.Label(rf, text=_format_row_label(r), width=24, anchor="w",
                         font=(f_font, fs(8), "normal" if is_empty else "bold"),
                         fg=fg_main, bg=row_bg, padx=6, pady=4).pack(side="left")

                # Orantılı Görsel Tüketim Çubuğu
                bar_w = int(95 * UI_SCALE)
                bar_c = tk.Canvas(rf, width=bar_w, height=int(14 * UI_SCALE), bg=row_bg, highlightthickness=0, bd=0)
                bar_c.pack(side="left", padx=4)
                bar_c.create_rectangle(0, int(4 * UI_SCALE), bar_w, int(10 * UI_SCALE), fill=THEME["card_inner"], outline="")
                if not is_empty:
                    fill_w = max(3, int(bar_w * (r["kwh"] / max_kwh)))
                    bar_c.create_rectangle(0, int(4 * UI_SCALE), fill_w, int(10 * UI_SCALE), fill=THEME["accent_cyan"], outline="")

                tk.Label(rf, text=_format_duration_compact(r["active_seconds"]), width=10, anchor="e",
                         font=(f_font, fs(8)), fg=THEME["text_secondary"], bg=row_bg, padx=6).pack(side="left")
                tk.Label(rf, text=f"{r['avg_watt']:.0f} W" if r["avg_watt"] > 0 else "-", width=10, anchor="e",
                         font=(f_font, fs(8)), fg=THEME["text_secondary"], bg=row_bg, padx=6).pack(side="left")
                tk.Label(rf, text=f"{r['kwh']:.3f} kWh", width=11, anchor="e",
                         font=(f_font, fs(8)), fg=fg_main, bg=row_bg, padx=6).pack(side="left")
                tk.Label(rf, text=self.format_currency(r["tl"], 2), width=12, anchor="e",
                         font=(f_font, fs(8), "bold"), fg=fg_cost, bg=row_bg, padx=6).pack(side="left")

            lbl_period_tot.config(text=_t("history_period_total", "Seçili Dönem Toplamı:"))
            lbl_period_vals.config(
                text=f"{self.format_currency(totals['tl'], 2)}   •   {totals['kwh']:.3f} kWh   •   "
                     f"{_format_duration_compact(totals['active_seconds'])}   •   {totals['avg_watt']:.0f} W"
            )
            canvas.yview_moveto(0)

        def _select_mode(m_id: str):
            active_mode[0] = m_id
            if m_id == "monthly":
                cb_sub.config(values=ext["months"])
                if ext["months"]:
                    cb_sub.set(ext["months"][0])
                cb_sub.pack(side="right", padx=(4, 0))
            elif m_id == "yearly":
                cb_sub.config(values=ext["years"])
                if ext["years"]:
                    cb_sub.set(ext["years"][0])
                cb_sub.pack(side="right", padx=(4, 0))
            else:
                cb_sub.pack_forget()
            _render_table()

        cb_sub.bind("<<ComboboxSelected>>", lambda e: _render_table())

        for m_id, m_key, m_def in [
            ("this_week", "history_tab_this_week", "📅 Bu Hafta"),
            ("last_week", "history_tab_last_week", "📆 Geçen Hafta"),
            ("monthly", "history_tab_monthly", "🗓️ Aylık"),
            ("yearly", "history_tab_yearly", "📈 Yıllık"),
            ("all", "history_tab_all", "📋 Tüm Günler"),
        ]:
            b = self.make_btn(f_filters, _t(m_key, m_def), lambda mid=m_id: _select_mode(mid),
                              fg=THEME["text_primary"], bg=THEME["btn_bg"], padx=int(8 * UI_SCALE), pady=int(3 * UI_SCALE))
            b.pack(side="left", padx=(0, 4))
            mode_btns[m_id] = b

        # Alt Bilgi Bandı (Taşınabilir Format Dosyası + Klasörü Aç)
        db_path = HistoryManager.get_history_file_path()
        f_foot = tk.Frame(top, bg=THEME["bg"])
        f_foot.pack(fill="x", padx=14, pady=(0, 10))
        tk.Label(f_foot, text=_t("history_db_path", "📁 Taşınabilir Veri (Formatta koruyun): {path}").format(path=db_path),
                 font=(f_font, fs(7)), fg=THEME["text_muted"], bg=THEME["bg"]).pack(side="left")
        self.make_btn(
            f_foot, _t("history_open_folder", "📂 Klasörü Aç"),
            lambda: subprocess.Popen(["explorer", "/select,", os.path.abspath(db_path)]) if os.path.exists(db_path) else os.startfile(os.path.dirname(os.path.abspath(db_path))),
            fg=THEME["accent_cyan"], bg=THEME["card_inner"], padx=int(8 * UI_SCALE), pady=2
        ).pack(side="right")

        _select_mode(active_mode[0])
