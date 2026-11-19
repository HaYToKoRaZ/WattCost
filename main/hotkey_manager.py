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
    "Ctrl+Alt+1": (MOD_CONTROL | MOD_ALT, ord('1'), "Ctrl + Alt + 1"),
    "Ctrl+Alt+2": (MOD_CONTROL | MOD_ALT, ord('2'), "Ctrl + Alt + 2"),
    "Ctrl+Alt+3": (MOD_CONTROL | MOD_ALT, ord('3'), "Ctrl + Alt + 3"),
    "Ctrl+Alt+4": (MOD_CONTROL | MOD_ALT, ord('4'), "Ctrl + Alt + 4"),
    "Alt+Shift+1": (MOD_ALT | MOD_SHIFT, ord('1'), "Alt + Shift + 1"),
    "Alt+Shift+2": (MOD_ALT | MOD_SHIFT, ord('2'), "Alt + Shift + 2"),
    "Alt+Shift+3": (MOD_ALT | MOD_SHIFT, ord('3'), "Alt + Shift + 3"),
    "Alt+Shift+4": (MOD_ALT | MOD_SHIFT, ord('4'), "Alt + Shift + 4"),
    "Ctrl+Shift+1": (MOD_CONTROL | MOD_SHIFT, ord('1'), "Ctrl + Shift + 1"),
    "Ctrl+Shift+2": (MOD_CONTROL | MOD_SHIFT, ord('2'), "Ctrl + Shift + 2"),
    "Ctrl+Shift+3": (MOD_CONTROL | MOD_SHIFT, ord('3'), "Ctrl + Shift + 3"),
    "Ctrl+Shift+4": (MOD_CONTROL | MOD_SHIFT, ord('4'), "Ctrl + Shift + 4"),
    "F1": (0, 0x70, "F1"),
    "F2": (0, 0x71, "F2"),
    "F3": (0, 0x72, "F3"),
    "F4": (0, 0x73, "F4"),
}

TIER_HOTKEY_OPTIONS = [
    ("Ctrl+Alt+1", "Ctrl + Alt + 1"),
    ("Ctrl+Alt+2", "Ctrl + Alt + 2"),
    ("Ctrl+Alt+3", "Ctrl + Alt + 3"),
    ("Ctrl+Alt+4", "Ctrl + Alt + 4"),
    ("Alt+Shift+1", "Alt + Shift + 1"),
    ("Alt+Shift+2", "Alt + Shift + 2"),
    ("Alt+Shift+3", "Alt + Shift + 3"),
    ("Alt+Shift+4", "Alt + Shift + 4"),
    ("Ctrl+Shift+1", "Ctrl + Shift + 1"),
    ("Ctrl+Shift+2", "Ctrl + Shift + 2"),
    ("Ctrl+Shift+3", "Ctrl + Shift + 3"),
    ("Ctrl+Shift+4", "Ctrl + Shift + 4"),
    ("F1", "F1"),
    ("F2", "F2"),
    ("F3", "F3"),
    ("F4", "F4"),
    ("none", "Yok (Kapalı)"),
]

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
    """Windows global RegisterHotKey dinleyicisi (OSD ve Akıllı Kademe kısayolları)."""
    def __init__(self, on_trigger=None):
        self.on_trigger = on_trigger
        self.thread = None
        self.thread_id = None
        self.is_registered = False
        self.registered_ids = []
        self._stop_done = None
        self.vk = None
        self.mod = 0
        self._extra_bindings = {}

    @staticmethod
    def resolve_key(key_name, vk=None, mod=0):
        """Anahtar adından (mod, vk) çifti çözer; geçersiz/none ise None döner."""
        if not key_name or str(key_name).lower() == "none":
            return None
        if key_name in HOTKEY_DEFINITIONS:
            t_mod, t_vk, _ = HOTKEY_DEFINITIONS[key_name]
            return (t_mod, t_vk)
        if vk is not None:
            return (int(mod or 0), int(vk))
        return None

    def register_hotkeys(self, bindings: dict):
        """Birden fazla global kısayolu tek Win32 mesaj döngüsünde dinler.

        bindings: { action_key: (key_name, callback[, vk, mod]) }
        """
        self.stop()
        parsed = []
        next_id = 1
        for action_key, spec in bindings.items():
            if not spec:
                continue
            key_name = spec[0]
            cb = spec[1]
            vk = spec[2] if len(spec) > 2 else None
            mod = spec[3] if len(spec) > 3 else 0
            resolved = self.resolve_key(key_name, vk=vk, mod=mod)
            if resolved and cb:
                t_mod, t_vk = resolved
                if action_key == "rtss":
                    self.vk = t_vk
                    self.mod = t_mod
                parsed.append((next_id, t_mod, t_vk, cb, action_key))
                next_id += 1

        if not parsed:
            return

        stop_evt = threading.Event()
        self._stop_done = stop_evt

        def _loop():
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            self.thread_id = kernel32.GetCurrentThreadId()
            callbacks = {}
            reg_ids = []
            for hk_id, t_mod, t_vk, cb, _ in parsed:
                ok = user32.RegisterHotKey(None, hk_id, t_mod | MOD_NOREPEAT, t_vk)
                if not ok:
                    ok = user32.RegisterHotKey(None, hk_id, t_mod, t_vk)
                if ok:
                    reg_ids.append(hk_id)
                    callbacks[hk_id] = cb
            self.registered_ids = reg_ids
            self.is_registered = bool(reg_ids)

            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY and msg.wParam in callbacks:
                    try:
                        callbacks[msg.wParam]()
                    except Exception:
                        pass
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

            for hk_id in reg_ids:
                try:
                    user32.UnregisterHotKey(None, hk_id)
                except Exception:
                    pass
            self.registered_ids = []
            self.is_registered = False
            self.thread_id = None
            stop_evt.set()

        self.thread = threading.Thread(target=_loop, daemon=True)
        self.thread.start()

    def start(self, key_name, vk=None, mod=0):
        """Geriye dönük uyumluluk: yalnızca RTSS kısayolunu günceller, kayıtlı kademe kısayollarını korur."""
        if not key_name or key_name == "none":
            self.vk = None
            self.mod = 0
            bindings = dict(self._extra_bindings)
        else:
            resolved = self.resolve_key(key_name, vk=vk, mod=mod)
            if not resolved:
                resolved = (0, 0x78)
            self.mod, self.vk = resolved
            bindings = {"rtss": (key_name, self.on_trigger, self.vk, self.mod)}
            bindings.update(self._extra_bindings)
        self.register_hotkeys(bindings)

    def stop(self):
        if self.thread_id:
            evt = self._stop_done
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
            if evt and self.thread and self.thread is not threading.current_thread():
                evt.wait(timeout=0.5)
            self.thread_id = None
            self.thread_id = None
        self.is_registered = False
