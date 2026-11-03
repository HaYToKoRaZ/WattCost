r"""
WattCost HaYTooL - Kulaklik Batarya Okuyucusu

Iki ayri kaynaktan beslenir, ikisi de harici arac gerektirmez:

1) USB kulaklik (SteelSeries Arctis 7 / 7+ / Pro) - HID protokolu
   VID 0x1038; PID 0x1260 / 0x12AD / 0x1252 / 0x1280
   Istek: report 0x06 + komut 0x18 (31 bayt) -> yanit 8 bayt, [2] = yuzde
   Kalan sure cihazdan gelmez: HeadsetControl ile ayni sekilde
   yuzde x 720 dk / 100 (tam doluda ~12 saat) tahmin edilir.

2) Bluetooth kulaklik (HFP) - Windows cihaz ozelligi
   Windows, HFP (Hands-Free) uzerinden gelen batarya bildirimini cihazin
   PnP ozelligine isler:
       DEVPKEY {104EA319-6EE2-4701-BD47-8DDBF425BBE5} PID 2  (DEVPROP_TYPE_BYTE)
   Ayarlar uygulamasinin gosterdigi degerin aynisi. SetupAPI (ctypes) ile
   okunur; ek kutuphane veya arac gerekmez. Cihaz dugumu:
       BTHENUM\{0000111E-...}  (Handsfree Audio Gateway)

Istege bagli yedek: INI'de headset_exe doluysa ve USB cihazi bulunamazsa
`headsetcontrol -b -o json` cagrisi kullanilir. Varsayilan olarak kapalidir.

snapshot() cikti sozlesmesi:
    {
        "usb": {"state": "ok"|"no_device"|"error", "name":..., "level": 83,
                "status_key": "headset_status_available", "time_to_empty_min": 597},
        "bt":  {"state": "ok"|"no_device"|"error", "name": "QCY H3 PRO", "level": 100, ...}
    }
"""

import ctypes
import json
import os
import subprocess
import threading
from ctypes import wintypes

try:
    import hid
except ImportError:  # hidapi yoksa USB yolu devre disi kalir
    hid = None

# --- SteelSeries USB -------------------------------------------------------
STEELSERIES_DEVICES = {
    0x1260: "SteelSeries Arctis 7",
    0x12AD: "SteelSeries Arctis 7 (2019)",
    0x1252: "SteelSeries Arctis Pro (2019)",
    0x1280: "SteelSeries Arctis Pro GameDAC",
}
STEELSERIES_VID = 0x1038
VENDOR_USAGE_PAGE = 0xFF43
VENDOR_USAGE = 514
BATTERY_INTERFACE = 5

REQUEST_REPORT_ID = 0x06
REQUEST_COMMAND = 0x18
PACKET_SIZE = 31
READ_TIMEOUT_MS = 1500
FULL_CHARGE_MINUTES = 720  # tam doluda tahmini kullanim suresi (dk)

# --- Windows Bluetooth HFP ------------------------------------------------
DIGCF_PRESENT = 0x00000002
DIGCF_ALLCLASSES = 0x00000004
SPDRP_FRIENDLYNAME = 0x0000000C
DEVPROP_TYPE_BYTE = 0x00000003

# PKEY_Devices_BatteryLevel: {104EA319-6EE2-4701-BD47-8DDBF425BBE5} PID 2
_BATTERY_FMTID = (0x104EA319, 0x6EE2, 0x4701, (0xBD, 0x47, 0x8D, 0xDB, 0xF4, 0x25, 0xBB, 0xE5))
_BATTERY_PID = 2


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _DEVPROPKEY(ctypes.Structure):
    _fields_ = [("fmtid", _GUID), ("pid", wintypes.DWORD)]


class _SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("ClassGuid", _GUID),
        ("DevInst", wintypes.DWORD),
        ("Reserved", ctypes.c_void_p),
    ]


def _clean_bt_name(name: str) -> str:
    """Windows'un ekledigi profil eklerini ('Hands-Free AG' vb.) temizler."""
    for suffix in (" Hands-Free AG", " Hands-Free", " Avrcp Transport", " A2DP Source", " AG"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.strip()


def _connected_bt_addresses():
    """Windows'un su anda bagli saydigi Bluetooth cihazlarinin MAC adreslerini dondurur.

    None -> sorgu yapilamadi (filtre uygulanmaz), set() -> bagli cihaz yok.
    """
    if os.name != "nt":
        return None
    try:
        bth = ctypes.WinDLL("bthprops.cpl", use_last_error=True)
    except OSError:
        return None

    class _BT_ADDRESS(ctypes.Union):
        _fields_ = [("ullLong", ctypes.c_ulonglong), ("rgBytes", ctypes.c_ubyte * 6)]

    class _SYSTEMTIME(ctypes.Structure):
        _fields_ = [
            ("wYear", wintypes.WORD), ("wMonth", wintypes.WORD), ("wDayOfWeek", wintypes.WORD),
            ("wDay", wintypes.WORD), ("wHour", wintypes.WORD), ("wMinute", wintypes.WORD),
            ("wSecond", wintypes.WORD), ("wMilliseconds", wintypes.WORD),
        ]

    class _BT_DEVICE_INFO(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("Address", _BT_ADDRESS),
            ("ulClassofDevice", wintypes.ULONG), ("fConnected", wintypes.BOOL),
            ("fRemembered", wintypes.BOOL), ("fAuthenticated", wintypes.BOOL),
            ("stLastSeen", _SYSTEMTIME), ("stLastUsed", _SYSTEMTIME),
            ("szName", wintypes.WCHAR * 248),
        ]

    class _FIND_RADIO_PARAMS(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD)]

    class _SEARCH_PARAMS(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("fReturnAuthenticated", wintypes.BOOL),
            ("fReturnRemembered", wintypes.BOOL), ("fReturnUnknown", wintypes.BOOL),
            ("fReturnConnected", wintypes.BOOL), ("fIssueInquiry", wintypes.BOOL),
            ("cTimeoutMultiplier", ctypes.c_ubyte), ("hRadio", wintypes.HANDLE),
        ]

    try:
        bth.BluetoothFindFirstRadio.argtypes = [ctypes.POINTER(_FIND_RADIO_PARAMS), ctypes.POINTER(wintypes.HANDLE)]
        bth.BluetoothFindFirstRadio.restype = wintypes.HANDLE
        bth.BluetoothFindRadioClose.argtypes = [wintypes.HANDLE]
        bth.BluetoothFindFirstDevice.argtypes = [ctypes.POINTER(_SEARCH_PARAMS), ctypes.POINTER(_BT_DEVICE_INFO)]
        bth.BluetoothFindFirstDevice.restype = wintypes.HANDLE
        bth.BluetoothFindNextDevice.argtypes = [wintypes.HANDLE, ctypes.POINTER(_BT_DEVICE_INFO)]
        bth.BluetoothFindDeviceClose.argtypes = [wintypes.HANDLE]

        radio_params = _FIND_RADIO_PARAMS(ctypes.sizeof(_FIND_RADIO_PARAMS))
        h_radio = wintypes.HANDLE()
        h_find_radio = bth.BluetoothFindFirstRadio(ctypes.byref(radio_params), ctypes.byref(h_radio))
        if not h_find_radio:
            return None

        addresses = {}
        try:
            search = _SEARCH_PARAMS()
            search.dwSize = ctypes.sizeof(_SEARCH_PARAMS)
            search.fReturnAuthenticated = True
            search.fReturnRemembered = True
            search.fReturnUnknown = False
            search.fReturnConnected = True
            search.fIssueInquiry = False
            search.cTimeoutMultiplier = 1
            search.hRadio = h_radio

            info = _BT_DEVICE_INFO()
            info.dwSize = ctypes.sizeof(_BT_DEVICE_INFO)
            h_find = bth.BluetoothFindFirstDevice(ctypes.byref(search), ctypes.byref(info))
            if not h_find:
                return addresses
            try:
                while True:
                    if info.fConnected:
                        mac = "".join(f"{b:02X}" for b in reversed(list(info.Address.rgBytes)))
                        seen = info.stLastSeen
                        addresses[mac] = (seen.wYear, seen.wMonth, seen.wDay,
                                          seen.wHour, seen.wMinute, seen.wSecond)
                    if not bth.BluetoothFindNextDevice(h_find, ctypes.byref(info)):
                        break
            finally:
                bth.BluetoothFindDeviceClose(h_find)
        finally:
            bth.BluetoothFindRadioClose(h_find_radio)
        return addresses
    except Exception:
        return None


def _collect_battery_nodes():
    """Pil ozelligi tasiyan BTHENUM dugumlerini toplar (bagli olanlarla sinirli).

    None -> numaralandirma hatasi, [] -> uygun cihaz yok.
    """
    if os.name != "nt":
        return []

    connected = _connected_bt_addresses()

    try:
        setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
    except OSError:
        return []

    setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE
    setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]
    setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
    setupapi.SetupDiEnumDeviceInfo.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(_SP_DEVINFO_DATA)]
    setupapi.SetupDiGetDeviceInstanceIdW.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_SP_DEVINFO_DATA),
        wintypes.LPWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
    ]
    setupapi.SetupDiGetDevicePropertyW.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_SP_DEVINFO_DATA), ctypes.POINTER(_DEVPROPKEY),
        ctypes.POINTER(wintypes.ULONG), ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), wintypes.DWORD,
    ]
    setupapi.SetupDiGetDeviceRegistryPropertyW.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_SP_DEVINFO_DATA), wintypes.DWORD,
        ctypes.POINTER(wintypes.ULONG), ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]

    key = _DEVPROPKEY()
    key.fmtid = _GUID(*_BATTERY_FMTID)
    key.pid = _BATTERY_PID

    handle = setupapi.SetupDiGetClassDevsW(None, None, None, DIGCF_ALLCLASSES | DIGCF_PRESENT)
    if not handle:
        return []

    try:
        info = _SP_DEVINFO_DATA()
        info.cbSize = ctypes.sizeof(_SP_DEVINFO_DATA)
        buf = ctypes.create_string_buffer(64)
        index = 0
        candidates = []

        while setupapi.SetupDiEnumDeviceInfo(handle, index, ctypes.byref(info)):
            index += 1

            inst = ctypes.create_unicode_buffer(512)
            need = wintypes.DWORD()
            if not setupapi.SetupDiGetDeviceInstanceIdW(handle, ctypes.byref(info), inst, 512, ctypes.byref(need)):
                continue
            instance_id = inst.value or ""
            if "BTHENUM" not in instance_id:
                continue

            # Cihaz kapatildiginda Windows eski yuzdeyi dugumde birakiyor:
            # yalnizca o an bagli olan MAC adreslerini kabul et.
            seen_key = ()
            if connected is not None:
                upper_id = instance_id.upper()
                matched = next((mac for mac in connected if mac in upper_id), None)
                if matched is None:
                    continue
                seen_key = connected.get(matched, ())

            prop_type = wintypes.ULONG()
            size = wintypes.DWORD()
            ok = setupapi.SetupDiGetDevicePropertyW(
                handle, ctypes.byref(info), ctypes.byref(key), ctypes.byref(prop_type),
                buf, ctypes.sizeof(buf), ctypes.byref(size), 0,
            )
            if not ok or prop_type.value != DEVPROP_TYPE_BYTE or size.value < 1:
                continue

            level = ctypes.c_ubyte.from_buffer_copy(buf.raw[:1]).value
            if level < 0 or level > 100:
                continue

            # Görünen ad (ör. "QCY H3 PRO Hands-Free AG" -> "QCY H3 PRO")
            name = ""
            name_type = wintypes.ULONG()
            name_size = wintypes.DWORD()
            name_buf = ctypes.create_unicode_buffer(256)
            if setupapi.SetupDiGetDeviceRegistryPropertyW(
                handle, ctypes.byref(info), SPDRP_FRIENDLYNAME, ctypes.byref(name_type),
                name_buf, ctypes.sizeof(name_buf), ctypes.byref(name_size),
            ):
                name = name_buf.value or ""
            name = _clean_bt_name(name) or "Bluetooth Kulaklik"

            candidates.append({
                "mac": matched or "",
                "name": name,
                "level": level,
                "seen": seen_key,
            })
    except Exception:
        return None
    finally:
        try:
            setupapi.SetupDiDestroyDeviceInfoList(handle)
        except Exception:
            pass

    return candidates


def read_bluetooth_batteries():
    """Bagli tum Bluetooth cihazlarinin bataryalarini dondurur (liste)."""
    if os.name != "nt":
        return []
    nodes = _collect_battery_nodes()
    if not nodes:
        return []

    devices = []
    for node in nodes:
        if not node.get("mac"):
            continue
        devices.append({
            "key": "bt:" + node["mac"],
            "name": node["name"],
            "level": node["level"],
            "status_key": "headset_status_available",
            # Windows sadece yuzde verir; USB tarafiyla ayni tahmin kullanilir
            "time_to_empty_min": int(node["level"] * FULL_CHARGE_MINUTES / 100),
            "mac": node["mac"],
        })
    devices.sort(key=lambda d: d["name"].lower())
    return devices


class HeadsetBatteryReader:
    """USB ve Bluetooth kulaklik bataryalarini arka planda okuyup onbellege alir."""

    POLL_INTERVAL = 30.0

    def __init__(self, exe_path: str = "", poll_interval: float = POLL_INTERVAL,
                 autostart: bool = False, usb_enabled: bool = True, bt_enabled: bool = True):
        self.exe_path = (exe_path or "").strip()
        self.poll_interval = max(10.0, float(poll_interval))
        self.usb_enabled = bool(usb_enabled)
        self.bt_enabled = bool(bt_enabled)
        self._lock = threading.Lock()
        self._state = {"devices": [], "usb_state": "starting", "bt_state": "starting"}
        self._device_path = ""
        self._device_pid = 0
        self._running = False
        self._stop_event = threading.Event()
        self._thread = None
        if autostart:
            self.start()

    # --------------------------------------------------------------- kaynaklar
    def any_enabled(self) -> bool:
        """En az bir kulaklik kaynagi acik mi?"""
        return self.usb_enabled or self.bt_enabled

    def set_sources(self, usb=None, bt=None):
        """USB / Bluetooth kaynaklarini tek tek acip kapatir."""
        with self._lock:
            if usb is not None:
                self.usb_enabled = bool(usb)
                if not self.usb_enabled:
                    self._state["usb_state"] = "disabled"
            if bt is not None:
                self.bt_enabled = bool(bt)
                if not self.bt_enabled:
                    self._state["bt_state"] = "disabled"
                    self._state["devices"] = [d for d in self._state["devices"] if not d["key"].startswith("bt:")]

    # ------------------------------------------------------------------ USB
    @property
    def is_available(self) -> bool:
        """hidapi modulu yuklu mu?"""
        return hid is not None

    def find_device(self) -> dict:
        """Bagli SteelSeries kulakligin HID yolunu ve urun kimligini bulur."""
        if hid is None:
            return {}
        for pid, name in STEELSERIES_DEVICES.items():
            try:
                candidates = hid.enumerate(STEELSERIES_VID, pid)
            except Exception:
                continue
            if not candidates:
                continue

            chosen = None
            for info in candidates:
                if info.get("usage_page") == VENDOR_USAGE_PAGE and info.get("usage") == VENDOR_USAGE:
                    chosen = info
                    break
            if chosen is None:
                for info in candidates:
                    if info.get("interface_number") == BATTERY_INTERFACE:
                        chosen = info
                        break
            if chosen is None:
                chosen = candidates[0]

            return {"path": chosen.get("path", b""), "pid": pid, "name": name}
        return {}

    def _read_hid(self) -> dict:
        """USB kulakliga batarya istegi gonderir."""
        if hid is None:
            return {"state": "no_device"}

        device = None
        try:
            device = hid.device()
            device.open_path(self._device_path)
            device.set_nonblocking(0)

            packet = bytes([REQUEST_REPORT_ID, REQUEST_COMMAND] + [0x00] * (PACKET_SIZE - 2))
            device.write(packet)
            response = device.read(64, READ_TIMEOUT_MS)
        except Exception:
            self._device_path = ""
            return {"state": "error"}
        finally:
            if device is not None:
                try:
                    device.close()
                except Exception:
                    pass

        if not response or len(response) < 3:
            return {"state": "error"}

        level = int(response[2])
        if level < 0 or level > 100:
            return {"state": "error"}

        return {
            "state": "ok",
            "name": STEELSERIES_DEVICES.get(self._device_pid, "SteelSeries"),
            "status": "BATTERY_AVAILABLE",
            "status_key": "headset_status_available",
            "level": level,
            "time_to_empty_min": int(level * FULL_CHARGE_MINUTES / 100),
        }

    # --------------------------------------------------------- istege bagli CLI
    def _read_cli(self) -> dict:
        """headset_exe tanimliysa HeadsetControl ciktisindan okur (USB icin yedek)."""
        exe = os.path.expandvars(os.path.expanduser(self.exe_path.strip('"')))
        if not exe or not os.path.isfile(exe):
            return {"state": "no_device"}

        creationflags = 0
        startupinfo = None
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            proc = subprocess.run(
                [exe, "-b", "-o", "json"],
                capture_output=True, text=True, encoding="utf-8", errors="ignore",
                timeout=20, creationflags=creationflags, startupinfo=startupinfo,
            )
        except (OSError, subprocess.SubprocessError):
            return {"state": "error"}

        raw = (proc.stdout or "").strip()
        brace = raw.find("{")
        if brace < 0:
            return {"state": "error"}
        try:
            payload = json.loads(raw[brace:])
        except ValueError:
            return {"state": "error"}

        devices = payload.get("devices") or []
        if not devices:
            return {"state": "no_device"}

        device = devices[0]
        battery = device.get("battery") or {}
        level = battery.get("level")
        try:
            level = int(level) if level is not None else None
        except (TypeError, ValueError):
            level = None
        if level is None:
            return {"state": "no_device"}

        status = str(battery.get("status") or "BATTERY_AVAILABLE")
        return {
            "state": "ok",
            "name": str(device.get("product") or device.get("device") or "Headset").strip(),
            "status": status,
            "status_key": {
                "BATTERY_AVAILABLE": "headset_status_available",
                "BATTERY_CHARGING": "headset_status_charging",
                "BATTERY_FULL": "headset_status_full",
            }.get(status, "headset_status_unknown"),
            "level": max(0, min(100, level)),
            "time_to_empty_min": int(level * FULL_CHARGE_MINUTES / 100),
        }

    # ------------------------------------------------------------------ dongu
    def refresh(self) -> dict:
        """Tek seferlik okuma yapar, onbellegi gunceller ve guncel durumu dondurur."""
        usb = {"state": "disabled"}
        if self.usb_enabled and hid is not None:
            if not self._device_path:
                found = self.find_device()
                if found:
                    self._device_path = found["path"]
                    self._device_pid = found["pid"]
            if self._device_path:
                usb = self._read_hid()

            if usb.get("state") != "ok" and self.exe_path:
                cli = self._read_cli()
                if cli.get("state") == "ok":
                    usb = cli

        devices = []
        if usb.get("state") == "ok":
            devices.append({
                "key": "usb",
                "name": usb.get("name") or "USB Kulaklik",
                "level": usb.get("level"),
                "status_key": usb.get("status_key") or "headset_status_available",
                "time_to_empty_min": usb.get("time_to_empty_min"),
            })

        if self.bt_enabled:
            bt_devices = read_bluetooth_batteries()
            bt_state = "ok" if bt_devices else "no_device"
            devices.extend(bt_devices)
        else:
            bt_state = "disabled"

        with self._lock:
            self._state = {
                "devices": devices,
                "usb_state": usb.get("state"),
                "bt_state": bt_state,
            }
        return self._state

    def start(self):
        """Arka plan okuma dongusunu baslatir (ilk okuma hemen yapilir)."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="HeadsetBatteryThread", daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                self.refresh()
            except Exception:
                with self._lock:
                    self._state = {"devices": [], "usb_state": "error", "bt_state": "error"}
            self._stop_event.wait(self.poll_interval)

    def stop(self):
        """Arka plan dongusunu durdurur."""
        self._running = False
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            try:
                thread.join(timeout=1.0)
            except Exception:
                pass
        self._thread = None
        self._device_path = ""

    # ------------------------------------------------------------- snapshot
    def snapshot(self) -> dict:
        """UI'in okuyacagi son durumun kopyasini dondurur."""
        with self._lock:
            return {
                "devices": [dict(d) for d in self._state.get("devices", [])],
                "usb_state": self._state.get("usb_state"),
                "bt_state": self._state.get("bt_state"),
            }

    def set_poll_interval(self, seconds: float):
        with self._lock:
            self.poll_interval = max(10.0, float(seconds))
