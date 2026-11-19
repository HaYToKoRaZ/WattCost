"""
WattCost HaYTooL - Core Automated Unit Test Suite
Tests language parity, dataclass slots, HistoryManager O(1) cache,
Windows DPAPI token encryption, save_config dirty-check, Gist sanitization,
and --watch early-exit import isolation.
"""
import json
import os
import sys
import time
import unittest
from unittest import mock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_DIR = os.path.join(ROOT_DIR, "main")
if MAIN_DIR not in sys.path:
    sys.path.insert(0, MAIN_DIR)

import config_manager as cm
from history_manager import HistoryManager
from power_manager import PowerPlanItem, PowerPlanSettings


class WattCostCoreTests(unittest.TestCase):
    def test_language_key_parity(self):
        with open(os.path.join(MAIN_DIR, "languages", "tr.json"), encoding="utf-8") as f:
            tr = json.load(f)
        with open(os.path.join(MAIN_DIR, "languages", "en.json"), encoding="utf-8") as f:
            en = json.load(f)
        self.assertEqual(set(tr.keys()), set(en.keys()))

    def test_dataclass_slots(self):
        item = PowerPlanItem(guid="1234", name="High Performance", is_active=True)
        settings = PowerPlanSettings(guid="1234", name="High Performance")
        self.assertTrue(hasattr(PowerPlanItem, "__slots__"))
        self.assertTrue(hasattr(PowerPlanSettings, "__slots__"))
        self.assertFalse(hasattr(item, "__dict__"))
        self.assertFalse(hasattr(settings, "__dict__"))

    def test_history_manager_o1_summary_cache(self):
        today = time.strftime("%Y-%m-%d")
        month_prefix = today[:7]
        prior_day = f"{month_prefix}-01" if today != f"{month_prefix}-01" else f"{month_prefix}-02"
        orig_cache = HistoryManager._history_cache
        try:
            HistoryManager._history_cache = {
                prior_day: {"wh": 1000.0, "kwh": 1.0, "cost_tl": 5.0, "active_seconds": 3600},
                today: {"wh": 500.0, "kwh": 0.5, "cost_tl": 2.5, "active_seconds": 1800},
            }
            HistoryManager._cached_prior_key = None
            s1 = HistoryManager.get_summary()
            self.assertAlmostEqual(s1["today_tl"], 2.5)
            self.assertAlmostEqual(s1["month_tl"], 7.5)
            self.assertIsNotNone(HistoryManager._cached_prior_key)

            # Updating today's entry reuses O(1) prior-days cache accurately
            HistoryManager._history_cache[today]["cost_tl"] = 4.0
            s2 = HistoryManager.get_summary()
            self.assertAlmostEqual(s2["today_tl"], 4.0)
            self.assertAlmostEqual(s2["month_tl"], 9.0)
        finally:
            HistoryManager._history_cache = orig_cache
            HistoryManager._cached_prior_key = None

    def test_dpapi_encryption_and_dirty_check(self):
        secret = "ghp_TestSecretToken987654321"
        enc1 = cm.encrypt_dpapi(secret)
        enc2 = cm.encrypt_dpapi(secret)
        self.assertTrue(enc1.startswith("dpapi:"))
        self.assertEqual(enc1, enc2)
        self.assertEqual(cm.decrypt_dpapi(enc1), secret)
        # Backward compatibility for plaintext tokens
        self.assertEqual(cm.decrypt_dpapi(secret), secret)

    def test_gist_token_sanitization_and_preview(self):
        captured = {}

        def fake_urlopen(req, timeout=15):
            if req.data:
                captured["content"] = json.loads(req.data.decode("utf-8"))["files"][cm.CONFIG_FILE_NAME]["content"]

            class Resp:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    pass

                def read(self):
                    if req.get_method() in ("POST", "PATCH"):
                        return json.dumps({"id": "g999", "html_url": "https://gist.github.com/g999"}).encode("utf-8")
                    return json.dumps({
                        "id": "g999",
                        "updated_at": "2026-11-19T11:00:00Z",
                        "files": {cm.CONFIG_FILE_NAME: {"content": "[Genel_Ayarlar]\ntheme = dark\n"}},
                    }).encode("utf-8")

            return Resp()

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            ok, gid, _ = cm.backup_settings_to_gist("ghp_TOPSECRET999", "g999")
            self.assertTrue(ok)
            self.assertEqual(gid, "g999")
            self.assertNotIn("ghp_TOPSECRET999", captured["content"])

            ok_p, ini_p, dt_p = cm.fetch_gist_ini_preview("g999", "ghp_TOPSECRET999")
            self.assertTrue(ok_p)
            self.assertIn("theme = dark", ini_p)
            self.assertEqual(dt_p, "2026-11-19T11:00:00Z")

    def test_watch_and_hide_early_exit_before_tkinter_import(self):
        with open(os.path.join(MAIN_DIR, "app.py"), encoding="utf-8") as f:
            src = f.read()
        pos_watch = src.find('sys.argv[1] == "--watch"')
        pos_hide = src.find('run_hidden_daemon()')
        pos_tk = src.find("import tkinter as tk")
        self.assertGreater(pos_watch, 0)
        self.assertGreater(pos_hide, pos_watch)
        self.assertGreater(pos_tk, pos_hide)

    def test_wall_power_formula_helper(self):
        cfg = {"case_base_w": 46.7}
        devs = [{"active": True, "enabled": True, "watt": 16.5}, {"active": True, "enabled": True, "watt": 10.0}]
        total = cm.calculate_wall_power_w(50.0, 100.0, cfg, devs)
        expected = 46.7 + (1.632 * 50.0) + (1.170 * 100.0) + 26.5
        self.assertAlmostEqual(total, expected, places=2)

    def test_history_extended_summary_and_delta_merge(self):
        import datetime
        import tempfile
        today_dt = datetime.date.today()
        last_tue = (today_dt - datetime.timedelta(days=today_dt.weekday() + 7)) + datetime.timedelta(days=1)
        lt_str = last_tue.strftime("%Y-%m-%d")

        orig_cache = HistoryManager._history_cache
        orig_deltas = HistoryManager._pending_deltas
        orig_dirty = HistoryManager._dirty
        orig_get_path = HistoryManager.get_history_file_path
        try:
            with tempfile.TemporaryDirectory() as td:
                db_path = os.path.join(td, "WattCost. HaYTooL.json")
                with open(db_path, "w", encoding="utf-8") as f:
                    json.dump({lt_str: {"wh": 1000.0, "kwh": 1.0, "cost_tl": 5.0, "active_seconds": 3600}}, f)

                HistoryManager.get_history_file_path = classmethod(lambda cls: db_path)
                HistoryManager._history_cache = None
                HistoryManager._pending_deltas = {}
                HistoryManager._dirty = False

                ext = HistoryManager.get_extended_summary()
                self.assertAlmostEqual(ext["last_week"]["kwh"], 1.0)
                rows, tot = HistoryManager.get_period_rows("last_week")
                self.assertEqual(len(rows), 7)
                self.assertEqual(rows[1]["key"], lt_str)
                self.assertAlmostEqual(rows[1]["tl"], 5.0)
                self.assertAlmostEqual(tot["kwh"], 1.0)

                # Simulate another session adding to disk before our flush
                with open(db_path, "w", encoding="utf-8") as f:
                    json.dump({lt_str: {"wh": 1500.0, "kwh": 1.5, "cost_tl": 7.5, "active_seconds": 5400}}, f)
                HistoryManager.add_energy(250.0, 5.0)
                HistoryManager.flush_history()

                self.assertTrue(os.path.exists(db_path + ".bak"))
                with open(db_path, encoding="utf-8") as f:
                    merged = json.load(f)
                self.assertAlmostEqual(merged[lt_str]["wh"], 1500.0)
                today_key = time.strftime("%Y-%m-%d")
                self.assertAlmostEqual(merged[today_key]["wh"], 250.0)
        finally:
            HistoryManager.get_history_file_path = orig_get_path
            HistoryManager._history_cache = orig_cache
            HistoryManager._pending_deltas = orig_deltas
            HistoryManager._dirty = orig_dirty


if __name__ == "__main__":
    unittest.main()
