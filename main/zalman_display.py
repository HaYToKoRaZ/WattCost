"""
Zalman Alpha2 LCD Display Kontrolcüsü (WattCost HaYTooL Modülü)
Zalman Alpha2 A24 / A36 AIO sıvı soğutma pompa LCD göstergesine USB HID üzerinden
canlı sıcaklık (CPU / GPU) aktarımını yönetir.

Protokol:
- USB VID: 0x1C57, PID: 0x3ED1
- Windows HID Unnumbered Report ID kuralı: 65 Bayt (Bayt 0 = 0x00, Bayt 1 = 0x02, Bayt 2 = Temp)
- Gönderim Sıklığı: 0.25 sn (4 Hz - donanımsal yumuşatma/interpolasyon için ideal)
"""

import time
import threading

try:
    import hid
except ImportError:
    hid = None


class ZalmanDisplay:
    VID = 0x1C57
    PID = 0x3ED1

    def __init__(self, update_interval: float = 0.25):
        self.update_interval = max(0.1, min(1.0, update_interval))
        self._device = None
        self._current_temp = 0.0
        self._enabled = True
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._is_connected = False
        self._is_blank = False
        self._last_error_time = 0.0

    @property
    def is_available(self) -> bool:
        """Sistemde hidapi modülünün yüklü olup olmadığını döner."""
        return hid is not None

    @property
    def is_connected(self) -> bool:
        """Aygıta şu anda bağlı olunup olunmadığını döner."""
        return self._is_connected and self._device is not None

    def connect(self) -> bool:
        """Zalman Alpha2 USB HID aygıtına bağlanmayı dener."""
        if not self.is_available:
            self._is_connected = False
            return False

        try:
            if self._device is not None:
                try:
                    self._device.close()
                except Exception:
                    pass
                self._device = None

            dev = hid.device()
            dev.open(self.VID, self.PID)
            dev.set_nonblocking(1)
            self._device = dev
            self._is_connected = True
            return True
        except Exception:
            self._device = None
            self._is_connected = False
            return False

    def disconnect(self):
        """USB HID aygıt bağlantısını güvenle sonlandırır."""
        self._is_connected = False
        if self._device is not None:
            try:
                self._device.close()
            except Exception:
                pass
            self._device = None

    def set_enabled(self, enabled: bool):
        """Pompa ekranına veri gönderimini aktif/pasif yapar."""
        with self._lock:
            self._enabled = bool(enabled)
            if not self._enabled:
                self.disconnect()

    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def set_blank(self, blank: bool):
        """
        Ekranı geçici olarak karartmak için veri gönderimini askıya alır.
        Zalman donanımı 1 saniyeden uzun süre USB paketi almadığında ekranı otomatik kapatır.
        """
        with self._lock:
            self._is_blank = bool(blank)

    def is_blank(self) -> bool:
        with self._lock:
            return self._is_blank

    def set_temperature(self, temp: float):
        """Arka plan döngüsünün ekrana basacağı anlık sıcaklığı günceller."""
        with self._lock:
            try:
                self._current_temp = float(temp)
            except (ValueError, TypeError):
                self._current_temp = 0.0

    def send_immediate(self, temp: float) -> bool:
        """
        Zalman ekranına tek seferlik 65 baytlık Windows HID paketini gönderir.
        """
        if self._device is None:
            if not self.connect():
                return False

        temp_int = max(0, min(127, int(round(temp))))

        # Windows HID 65 Baytlık Protokol:
        # Bayt 0: 0x00 (Report ID 0)
        # Bayt 1: 0x02 (Sıcaklık Komut Kodu)
        # Bayt 2: Değer (0 - 99 °C veya 101: A1, 122: c2 gibi özel kodlar)
        # Bayt 3..64: 0x00 (Padding)
        report = bytearray(65)
        report[0] = 0x00
        report[1] = 0x02
        report[2] = temp_int

        try:
            written = self._device.write(report)
            if written < 0:
                self.disconnect()
                return False
            self._is_connected = True
            return True
        except Exception:
            self.disconnect()
            return False

    def start_background_loop(self):
        """Sıcaklığı 0.25 sn periyotla USB'ye basan arka plan thread'ini başlatır."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._loop, name="ZalmanDisplayThread", daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            with self._lock:
                enabled = self._enabled
                temp = self._current_temp
                is_blank = self._is_blank

            if enabled and not is_blank:
                now = time.time()
                # Bağlantı yoksa ve son hatadan bu yana 2 sn geçmişse yeniden bağlanmayı dene
                if not self.is_connected:
                    if (now - self._last_error_time) >= 2.0:
                        if not self.connect():
                            self._last_error_time = now

                if self.is_connected:
                    success = self.send_immediate(temp)
                    if not success:
                        self._last_error_time = now

            time.sleep(self.update_interval)

    def stop_background_loop(self):
        """Arka plan thread'ini durdurur ve aygıtı kapatır."""
        self._running = False
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=1.0)
            except Exception:
                pass
            self._thread = None
        self.disconnect()

    def __enter__(self):
        self.start_background_loop()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_background_loop()
