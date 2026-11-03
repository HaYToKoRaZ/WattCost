"""
WattCost HaYTooL - Global Kısayol Tuşu (Hotkey) Yöneticisi
Windows API RegisterHotKey ve UnregisterHotKey kullanarak oyun içindeyken OSD açma/kapatma tuşunu yakalar.
"""
import ctypes
from ctypes import wintypes
import threading

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

HOTKEY_DEFINITIONS = {
    "none": (0, 0, "Yok (Devre Dışı)"),
    "Alt+Shift+R": (MOD_ALT | MOD_SHIFT, ord('R'), "Alt + Shift + R (Varsayılan)"),
    "Ctrl+Alt+R": (MOD_CONTROL | MOD_ALT, ord('R'), "Ctrl + Alt + R"),
    "F9": (0, 0x78, "F9"),
    "F10": (0, 0x79, "F10"),
    "F11": (0, 0x7A, "F11"),
    "F12": (0, 0x7B, "F12"),
    "ScrollLock": (0, 0x91, "Scroll Lock"),
    "Pause": (0, 0x13, "Pause / Break"),
    "Insert": (0, 0x2D, "Insert"),
    "Home": (0, 0x24, "Home"),
    "F8": (0, 0x77, "F8"),
    "F7": (0, 0x76, "F7"),
    "Ctrl+Shift+O": (MOD_CONTROL | MOD_SHIFT, ord('O'), "Ctrl + Shift + O"),
    "Alt+O": (MOD_ALT, ord('O'), "Alt + O"),
    "Ctrl+Alt+O": (MOD_CONTROL | MOD_ALT, ord('O'), "Ctrl + Alt + O"),
}

HOTKEY_OPTIONS = [
    ("Alt+Shift+R", "Alt + Shift + R (Varsayılan)"),
    ("Ctrl+Alt+R", "Ctrl + Alt + R"),
    ("F9", "F9"),
    ("F10", "F10"),
    ("F11", "F11"),
    ("F12", "F12"),
    ("ScrollLock", "Scroll Lock"),
    ("Pause", "Pause / Break"),
    ("Insert", "Insert"),
    ("Home", "Home"),
    ("F8", "F8"),
    ("F7", "F7"),
    ("Ctrl+Shift+O", "Ctrl + Shift + O"),
    ("Alt+O", "Alt + O"),
    ("Ctrl+Alt+O", "Ctrl + Alt + O"),
    ("none", "Yok (Devre Dışı)"),
]

class GlobalHotkeyManager:
    """Windows global RegisterHotKey dinleyicisi (Oyun oynarken OSD aç/kapat)."""
    def __init__(self, on_trigger):
        self.on_trigger = on_trigger
        self.thread = None
        self.thread_id = None
        self.is_registered = False

    def start(self, key_name, vk=None, mod=0):
        self.stop()
        if not key_name or key_name == "none":
            return
        target_vk = vk
        target_mod = mod
        if target_vk is None:
            if key_name in HOTKEY_DEFINITIONS:
                target_mod, target_vk, _ = HOTKEY_DEFINITIONS[key_name]
            else:
                target_mod, target_vk = 0, 0x78  # F9 varsayılan

        def _loop():
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            self.thread_id = kernel32.GetCurrentThreadId()
            HOTKEY_ID = 1
            ok = user32.RegisterHotKey(None, HOTKEY_ID, target_mod | MOD_NOREPEAT, target_vk)
            if not ok:
                ok = user32.RegisterHotKey(None, HOTKEY_ID, target_mod, target_vk)
            self.is_registered = bool(ok)

            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    if self.on_trigger:
                        self.on_trigger()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

            if self.is_registered:
                user32.UnregisterHotKey(None, HOTKEY_ID)
                self.is_registered = False

        self.thread = threading.Thread(target=_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
            self.thread_id = None
        self.is_registered = False
