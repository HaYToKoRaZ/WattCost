"""
WattCost HaYTooL - Windows G Ynetimi & Karlatrma Servisi (PowerManager)
Eski 'Powers / PowerGridHaYTooL' C# kodlarndan tam kapasiteyle Python'a tanmtr.
"""
import subprocess
import re
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple
from language_manager import _t
try:
    import win32api
    import win32con
except ImportError:
    win32api = None
    win32con = None

# Sabit Resmi & Özel GUID Tanımları
GUID_ULTIMATE_PERF        = "e9a42b02-d5df-448d-aa00-03f14749eb00"
GUID_AMD_BALANCED         = "9897998c-92de-4669-853f-b7cd3ecb2790"
GUID_AMD_HIGH_PERF        = "9897998c-92de-4669-853f-b7cd3ecb2791"

# 4 Kademeli Sabit WattCost Güç Planları GUID'leri (1: Max Tasarruf -> 4: Max Performans)
GUID_WATTCOST_MAX_SAVER   = "7a1f0001-c001-4a11-b001-000000000001"
GUID_WATTCOST_BAL_SAVER   = "7a1f0002-c002-4a11-b002-000000000002"
GUID_WATTCOST_HIGH_PERF   = "7a1f0003-c003-4a11-b003-000000000003"
GUID_WATTCOST_MAX_PERF    = "7a1f0004-c004-4a11-b004-000000000004"

BASE_BALANCED             = "381b4222-f694-41f0-9685-ff5bb260df2e"
BASE_HIGH_PERF            = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
BASE_POWER_SAVER          = "a1841308-3541-4fab-bc81-f71556f20b4a"
BASE_ULTIMATE             = "e9a42b02-d5df-448d-aa00-03f14749eb61"

# Windows G Alt Gruplar (Subgroups)
SUB_VIDEO      = "7516b95f-f776-4464-8c53-06167f40cc99"
SUB_SLEEP      = "238c9fa8-0aad-41ed-83f4-97be242c8f20"
SUB_DISK       = "0012ee47-9041-4b5d-9b77-535fba8b1442"
SUB_PROCESSOR  = "54533251-82be-4824-96c1-47b60b740d00"
SUB_PCIEXPRESS = "501a4d13-42af-4429-9fd1-a8218c268e20"
SUB_USB        = "2a737441-1930-4402-8d77-b2bebba308a3"
SUB_WIFI       = "19cbb8fa-5279-450e-9fac-8a3d5fedd0c1"
SUB_BUTTONS    = "4f971e89-eebd-4455-a8de-9e59040e7347"

# Windows G Ayar GUID'leri
VIDEOIDLE       = "3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e"
STANDBYIDLE     = "29f6c1db-86da-48c5-9fdb-f2b67b1f44da"
DISKIDLE        = "6738e2c4-e8a5-4a42-b16a-e040e769756e"
HIBERNATEIDLE   = "9d7815a6-7ee4-497e-8888-515a05f02364"
PROCTHROTTLEMIN = "893dee8e-2bef-41e0-89c6-b55d0929964c"
PROCTHROTTLEMAX = "bc5038f7-23e0-4960-96da-33abaf5935ec"
PROCMAXFREQ     = "75b0ae3f-bce0-45a7-8c89-c9611c25e100"
SYSCOOLPOL      = "94d3a615-a899-4ac5-ae2b-e4d8f634367f"
PERFBOOSTMODE   = "be337238-0d82-4146-a960-4f3749d470c7"
CPMINCORES      = "0cc5b647-c1df-4637-891a-dec35c318583"
CPMAXCORES      = "ea062031-0e34-4ff1-9b6d-eb1059334028"
PERFEPP         = "36687f9e-e3a5-4dbf-b1dc-15eb381c6863"
ASPM            = "ee12f906-d277-404b-b6da-e5fa1a576df5"
USBSELECT       = "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"
WIFISAVING      = "12bbebe6-58d6-4636-95bb-3217ef867c1a"
HYBRIDSLEEP     = "94ac6d29-73ce-41a6-809f-6363ba21b47e"
WAKETIMERS      = "bd3b718a-0680-4d9d-8ab2-e1d2b4ac806d"
POWERBUTTON     = "7648efa3-dd9c-4e3e-b566-50f929386280"
SLEEPBUTTON     = "96996bc0-ad50-47ec-923b-6f41874dd9eb"

# Windows Gelişmiş Gizli Güç Ayarları Çiftleri (SUBGROUP, SETTING)
HIDDEN_POWER_SETTING_PAIRS = [
    # SUB_PROCESSOR (54533251-82be-4824-96c1-47b60b740d00)
    ("54533251-82be-4824-96c1-47b60b740d00", "893dee8e-2bef-41e0-89c6-b55d0929964c"), # En Düşük İşlemci Durumu (PROCTHROTTLEMIN)
    ("54533251-82be-4824-96c1-47b60b740d00", "bc5038f7-23e0-4960-96da-33abaf5935ec"), # En Yüksek İşlemci Durumu (PROCTHROTTLEMAX)
    ("54533251-82be-4824-96c1-47b60b740d00", "75b0ae3f-bce0-45a7-8c89-c9611c25e100"), # Maksimum İşlemci Frekansı (PROCMAXFREQ)
    ("54533251-82be-4824-96c1-47b60b740d00", "94d3a615-a899-4ac5-ae2b-e4d8f634367f"), # Sistem Soğutma İlkesi (SYSCOOLPOL)
    ("54533251-82be-4824-96c1-47b60b740d00", "be337238-0d82-4146-a960-4f3749d470c7"), # Turbo Boost Modu (PERFBOOSTMODE)
    ("54533251-82be-4824-96c1-47b60b740d00", "0cc5b647-c1df-4637-891a-dec35c318583"), # Core Parking Min (CPMINCORES)
    ("54533251-82be-4824-96c1-47b60b740d00", "ea062031-0e34-4ff1-9b6d-eb1059334028"), # Core Parking Max (CPMAXCORES)
    ("54533251-82be-4824-96c1-47b60b740d00", "36687f9e-e3a5-4dbf-b1dc-15eb381c6863"), # EPP Enerji Tercihi (PERFEPP)
    # SUB_PCIEXPRESS (501a4d13-42af-4429-9fd1-a8218c268e20)
    ("501a4d13-42af-4429-9fd1-a8218c268e20", "ee12f906-d277-404b-b6da-e5fa1a576df5"), # ASPM Güç Tasarrufu
    # SUB_USB (2a737441-1930-4402-8d77-b2bebba308a3)
    ("2a737441-1930-4402-8d77-b2bebba308a3", "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"), # USB Seçici Askıya Alma
    # SUB_WIFI (19cbb8fa-5279-450e-9fac-8a3d5fedd0c1)
    ("19cbb8fa-5279-450e-9fac-8a3d5fedd0c1", "12bbebe6-58d6-4636-95bb-3217ef867c1a"), # Kablosuz Güç Tasarrufu
    # SUB_SLEEP (238c9fa8-0aad-41ed-83f4-97be242c8f20)
    ("238c9fa8-0aad-41ed-83f4-97be242c8f20", "bd3b718a-0680-4d9d-8ab2-e1d2b4ac806d"), # Uyandırma Zamanlayıcıları
    ("238c9fa8-0aad-41ed-83f4-97be242c8f20", "9d7815a6-7ee4-497e-8888-515a05f02364"), # Hazırda Bekleme Süresi
    ("238c9fa8-0aad-41ed-83f4-97be242c8f20", "94ac6d29-73ce-41a6-809f-6363ba21b47e"), # Karma (Hibrit) Uyku
    # SUB_DISK (0012ee47-9041-4b5d-9b77-535fba8b1442)
    ("0012ee47-9041-4b5d-9b77-535fba8b1442", "6738e2c4-e8a5-4a42-b16a-e040e769756e"), # Sabit Diski Kapatma
    # SUB_BUTTONS (4f971e89-eebd-4455-a8de-9e59040e7347)
    ("4f971e89-eebd-4455-a8de-9e59040e7347", "7648efa3-dd9c-4e3e-b566-50f929386280"), # Güç Düğmesi Eylemi
    ("4f971e89-eebd-4455-a8de-9e59040e7347", "96996bc0-ad50-47ec-923b-6f41874dd9eb"), # Uyku Düğmesi Eylemi
]

@dataclass
class PowerPlanItem:
    guid: str
    name: str
    is_active: bool = False

    @property
    def badge_icon(self) -> str:
        nl = self.name.lower()
        if "ryzen" in nl or "amd" in nl:
            return "🔴"
        if "maximum performance" in nl or "max performance" in nl or "maksimum performans" in nl or "ultra" in nl or "apex" in nl or "ultimate" in nl or "nihai" in nl:
            return "⚡"
        if "high performance" in nl or "high" in nl or "yüksek" in nl or "yksek" in nl or "oyun" in nl or "game" in nl:
            return "🔥"
        if "balanced" in nl or "dengeli" in nl:
            return "⚖️"
        if "power saver" in nl or "saver" in nl or "tasarruf" in nl or "eco" in nl or "stealth" in nl:
            return "🌱"
        return "⚖️"

@dataclass
class PowerPlanSettings:
    guid: str = ""
    name: str = ""
    video_timeout_ac: int = 0      # dakika
    sleep_timeout_ac: int = 0      # dakika
    disk_timeout_ac: int = 0       # dakika
    hibernate_timeout_ac: int = 0  # dakika
    cpu_min_ac: int = 5            # %
    cpu_max_ac: int = 100          # %
    cpu_max_freq_ac: int = 0       # MHz (0: Sınırsız)
    cooling_policy_ac: int = 1     # 1: Etkin, 0: Edilgin
    boost_mode_ac: int = 2         # 0: Kapalı, 1: Etkin, 2: Agresif, 3: Verimli Etkin, 4: Verimli Agresif
    core_parking_min_ac: int = 100 # % (100: Park yok, düşük: Park etkin)
    core_parking_max_ac: int = 100 # % (100: Tümü park edilebilir)
    energy_perf_pref_ac: int = 0   # 0: Max Performans, 50: Dengeli, 100: Tasarruf
    pcie_aspm_ac: int = 0          # 0: Kapalı (Max Hız), 1: Orta, 2: Maksimum Tasarruf
    usb_suspend_ac: int = 0        # 0: Devre dışı, 1: Etkin
    allow_wake_timers_ac: int = 1  # 1: Etkin, 0: Devre dışı, 2: Yalnızca Önemli
    hybrid_sleep_ac: int = 0       # 0: Kapalı, 1: Açık
    wifi_power_saving_ac: int = 0  # 0: En Yüksek Performans, 1: Düşük, 2: Orta, 3: Maksimum Tasarruf
    power_button_ac: int = 3       # 0: Hiçbiri, 1: Uyku, 2: Hazırda Beklet, 3: Kapat, 4: Ekranı Kapat
    sleep_button_ac: int = 1       # 0: Hiçbiri, 1: Uyku, 2: Hazırda Beklet, 3: Kapat, 4: Ekranı Kapat

def run_powercfg(args: List[str]) -> Tuple[int, str, str]:
    """powercfg komutunu pencere amadan sessizce altrr ve kty dner."""
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        res = subprocess.run(
            ["powercfg"] + args,
            capture_output=True,
            startupinfo=startupinfo,
            creationflags=0x08000000
        )
        out = ""
        for enc in ['cp857', 'cp1254', 'utf-8', 'latin1']:
            try:
                out = res.stdout.decode(enc)
                break
            except Exception:
                continue
        if not out:
            out = res.stdout.decode('latin1', errors='ignore')

        err = ""
        for enc in ['cp857', 'cp1254', 'utf-8', 'latin1']:
            try:
                err = res.stderr.decode(enc)
                break
            except Exception:
                continue
        return res.returncode, out, err
    except Exception as e:
        return -1, "", str(e)

class PowerManagerService:
    """Windows g dzenlerini ynetme, deitirme, sorgulama ve retme servisi."""

    @staticmethod
    def get_power_plans() -> List[PowerPlanItem]:
        code, out, _ = run_powercfg(["/list"])
        plans: List[PowerPlanItem] = []
        if code != 0 or not out:
            return plans

        pattern = re.compile(r"GUID:\s*([a-fA-F0-9\-]+)\s*\((.*?)\)(\s*\*?)", re.IGNORECASE)
        for m in pattern.finditer(out):
            guid = m.group(1).strip()
            name = m.group(2).strip()
            is_active = "*" in m.group(3)
            plans.append(PowerPlanItem(guid=guid, name=name, is_active=is_active))
        return plans

    @staticmethod
    def get_active_plan() -> Optional[PowerPlanItem]:
        plans = PowerManagerService.get_power_plans()
        for p in plans:
            if p.is_active:
                return p
        return plans[0] if plans else None

    @staticmethod
    def get_active_guid_fast() -> str:
        """Kayıt defterinden milisaniyeler içinde aktif güç planı GUID'ini okur."""
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes") as k:
                val, _ = winreg.QueryValueEx(k, "ActivePowerScheme")
                return str(val).strip().lower()
        except Exception:
            p = PowerManagerService.get_active_plan()
            return p.guid.lower() if p else ""

    @staticmethod
    def set_active_plan(guid: str) -> bool:
        code, _, _ = run_powercfg(["/setactive", guid])
        return code == 0

    @staticmethod
    def delete_plan(guid: str) -> bool:
        code, _, _ = run_powercfg(["/delete", guid])
        return code == 0

    @staticmethod
    def is_plan_existing(guid: str) -> bool:
        """Verilen GUID değerine sahip bir güç planının sistemde kayıtlı olup olmadığını kontrol eder."""
        if not guid:
            return False
        g_clean = guid.strip().lower()
        plans = PowerManagerService.get_power_plans()
        return any(p.guid.lower() == g_clean for p in plans)

    @staticmethod
    def is_plan_name_existing(name: str) -> bool:
        """Verilen ada sahip bir güç planının sistemde kayıtlı olup olmadığını kontrol eder."""
        if not name:
            return False
        n_clean = name.strip().lower()
        plans = PowerManagerService.get_power_plans()
        return any(p.name.strip().lower() == n_clean for p in plans)

    @staticmethod
    def are_hidden_settings_unlocked() -> bool:
        """Windows Denetim Masasında gelişmiş güç ayarlarının görünür/açık (Attributes == 2) olup olmadığını kontrol eder."""
        try:
            import winreg
            key_path = r"SYSTEM\CurrentControlSet\Control\Power\PowerSettings\54533251-82be-4824-96c1-47b60b740d00\be337238-0d82-4146-a960-4f3749d470c7"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
                val, _ = winreg.QueryValueEx(k, "Attributes")
                return val == 2
        except Exception:
            return False

    @staticmethod
    def unlock_all_hidden_settings(make_visible: bool = True) -> bool:
        """
        Windows Denetim Masasında varsayılan olarak gizli tutulan gelişmiş güç ayarlarının
        kilidini açar (Attributes=2) veya tekrar gizler (Attributes=1).
        """
        import tempfile
        import time
        attr_val = 2 if make_visible else 1
        flag = "-ATTRIB_HIDE" if make_visible else "+ATTRIB_HIDE"

        # 1. Önce doğrudan kayıt defterine yazmayı dene (Eğer yönetici olarak çalışıyorsa)
        try:
            import winreg
            for sub, setting in HIDDEN_POWER_SETTING_PAIRS:
                kp = rf"SYSTEM\CurrentControlSet\Control\Power\PowerSettings\{sub}\{setting}"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, kp, 0, winreg.KEY_SET_VALUE) as k:
                    winreg.SetValueEx(k, "Attributes", 0, winreg.REG_DWORD, attr_val)
                run_powercfg(["-attributes", sub, setting, flag])
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Power\PowerSettings\54533251-82be-4824-96c1-47b60b740d00", 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "Attributes", 0, winreg.REG_DWORD, attr_val)
            return True
        except Exception:
            pass

        # 2. Yönetici yetkisi yoksa, tek bir UAC onay penceresiyle çalışacak geçici betik oluştur ve PowerShell 'RunAs' ile çalıştır
        temp_script = os.path.join(tempfile.gettempdir(), f"haytool_unlock_{int(time.time() * 1000)}.cmd")
        try:
            lines = [
                "@echo off",
                "chcp 65001 >nul",
                rf'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Power\PowerSettings\54533251-82be-4824-96c1-47b60b740d00" /v Attributes /t REG_DWORD /d {attr_val} /f >nul 2>&1'
            ]
            for sub, setting in HIDDEN_POWER_SETTING_PAIRS:
                lines.append(rf'reg add "HKLM\SYSTEM\CurrentControlSet\Control\Power\PowerSettings\{sub}\{setting}" /v Attributes /t REG_DWORD /d {attr_val} /f >nul 2>&1')
                lines.append(rf'powercfg -attributes {sub} {setting} {flag} >nul 2>&1')

            with open(temp_script, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            ps_cmd = f'Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"{temp_script}`"" -Verb RunAs -WindowStyle Hidden -Wait'
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                startupinfo=startupinfo,
                creationflags=0x08000000,
                check=False
            )
            time.sleep(0.5)
            return PowerManagerService.are_hidden_settings_unlocked() == make_visible
        except Exception:
            return False
        finally:
            if os.path.exists(temp_script):
                try:
                    os.remove(temp_script)
                except Exception:
                    pass

    @staticmethod
    def duplicate_plan(guid: str, new_name: str = "New Power Plan", target_guid: str = "") -> Optional[str]:
        # 1. Sabit hedef GUID sistemde zaten varsa KESİNLİKLE tekrar ekleme
        if target_guid and PowerManagerService.is_plan_existing(target_guid):
            return None

        # 2. Aynı ada sahip plan zaten varsa çift kopya üretmeyi engelle
        if PowerManagerService.is_plan_name_existing(new_name):
            return None

        existing_plans = PowerManagerService.get_power_plans()
        existing_guids = [p.guid.lower() for p in existing_plans]

        base_guid = guid
        if base_guid.lower() not in existing_guids and existing_plans:
            active = PowerManagerService.get_active_plan()
            base_guid = active.guid if active else existing_plans[0].guid

        args = ["/duplicatescheme", base_guid]
        if target_guid:
            args.append(target_guid)
        code, out, _ = run_powercfg(args)

        # Hedef GUID belirtilmişse ve başarısız olduysa ASLA rastgele GUID ile mükerrer plan üretme!
        if code != 0:
            if not target_guid:
                code, out, _ = run_powercfg(["/duplicatescheme", base_guid])
            else:
                return None

        if code == 0:
            m = re.search(r"GUID:\s*([a-fA-F0-9\-]+)", out, re.IGNORECASE)
            created_guid = m.group(1).strip() if m else target_guid
            if created_guid:
                PowerManagerService.rename_plan(created_guid, new_name)
                return created_guid
        return None

    @staticmethod
    def rename_plan(guid: str, new_name: str) -> bool:
        code, _, _ = run_powercfg(["/changename", guid, new_name])
        return code == 0

    @staticmethod
    def restore_defaults() -> bool:
        """Tüm güç planlarını Windows varsayılanlarına döndürür."""
        code, _, _ = run_powercfg(["/restoredefaultschemes"])
        return code == 0

    @staticmethod
    def save_plan_settings(s: PowerPlanSettings) -> bool:
        """Bir güç planına ait tüm işlemci, soğutma, boost ve uyku ayarlarını yazar."""
        g = s.guid
        if not g:
            return False

        run_powercfg(["/setacvalueindex", g, SUB_VIDEO, VIDEOIDLE, str(s.video_timeout_ac * 60)])
        run_powercfg(["/setdcvalueindex", g, SUB_VIDEO, VIDEOIDLE, str(s.video_timeout_ac * 60)])

        run_powercfg(["/setacvalueindex", g, SUB_SLEEP, STANDBYIDLE, str(s.sleep_timeout_ac * 60)])
        run_powercfg(["/setdcvalueindex", g, SUB_SLEEP, STANDBYIDLE, str(s.sleep_timeout_ac * 60)])

        run_powercfg(["/setacvalueindex", g, SUB_DISK, DISKIDLE, str(s.disk_timeout_ac * 60)])
        run_powercfg(["/setdcvalueindex", g, SUB_DISK, DISKIDLE, str(s.disk_timeout_ac * 60)])

        run_powercfg(["/setacvalueindex", g, SUB_PROCESSOR, PROCTHROTTLEMIN, str(s.cpu_min_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_PROCESSOR, PROCTHROTTLEMIN, str(s.cpu_min_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_PROCESSOR, PROCTHROTTLEMAX, str(s.cpu_max_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_PROCESSOR, PROCTHROTTLEMAX, str(s.cpu_max_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_PROCESSOR, SYSCOOLPOL, str(s.cooling_policy_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_PROCESSOR, SYSCOOLPOL, str(s.cooling_policy_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_PROCESSOR, PERFBOOSTMODE, str(s.boost_mode_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_PROCESSOR, PERFBOOSTMODE, str(s.boost_mode_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_PROCESSOR, CPMINCORES, str(s.core_parking_min_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_PROCESSOR, CPMINCORES, str(s.core_parking_min_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_PROCESSOR, PERFEPP, str(s.energy_perf_pref_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_PROCESSOR, PERFEPP, str(s.energy_perf_pref_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_PCIEXPRESS, ASPM, str(s.pcie_aspm_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_PCIEXPRESS, ASPM, str(s.pcie_aspm_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_USB, USBSELECT, str(s.usb_suspend_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_USB, USBSELECT, str(s.usb_suspend_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_PROCESSOR, CPMAXCORES, str(s.core_parking_max_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_PROCESSOR, CPMAXCORES, str(s.core_parking_max_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_PROCESSOR, PROCMAXFREQ, str(s.cpu_max_freq_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_PROCESSOR, PROCMAXFREQ, str(s.cpu_max_freq_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_SLEEP, HIBERNATEIDLE, str(s.hibernate_timeout_ac * 60)])
        run_powercfg(["/setdcvalueindex", g, SUB_SLEEP, HIBERNATEIDLE, str(s.hibernate_timeout_ac * 60)])

        run_powercfg(["/setacvalueindex", g, SUB_SLEEP, HYBRIDSLEEP, str(s.hybrid_sleep_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_SLEEP, HYBRIDSLEEP, str(s.hybrid_sleep_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_SLEEP, WAKETIMERS, str(s.allow_wake_timers_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_SLEEP, WAKETIMERS, str(s.allow_wake_timers_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_WIFI, WIFISAVING, str(s.wifi_power_saving_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_WIFI, WIFISAVING, str(s.wifi_power_saving_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_BUTTONS, POWERBUTTON, str(s.power_button_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_BUTTONS, POWERBUTTON, str(s.power_button_ac)])

        run_powercfg(["/setacvalueindex", g, SUB_BUTTONS, SLEEPBUTTON, str(s.sleep_button_ac)])
        run_powercfg(["/setdcvalueindex", g, SUB_BUTTONS, SLEEPBUTTON, str(s.sleep_button_ac)])

        # Eğer düzen aktifse Değişiklikleri Windows çekirdeğine uygula
        active = PowerManagerService.get_active_plan()
        if active and active.guid.lower() == g.lower():
            run_powercfg(["/setactive", g])
        return True

    @staticmethod
    def update_plan_setting(guid: str, key: str, value: int) -> bool:
        """Belirli bir güç planındaki tek bir ayarı anında günceller."""
        if not guid:
            return False
        val_str = str(value)
        mapping = {
            "video_timeout_ac": (SUB_VIDEO, VIDEOIDLE, str(value * 60)),
            "sleep_timeout_ac": (SUB_SLEEP, STANDBYIDLE, str(value * 60)),
            "disk_timeout_ac": (SUB_DISK, DISKIDLE, str(value * 60)),
            "hibernate_timeout_ac": (SUB_SLEEP, HIBERNATEIDLE, str(value * 60)),
            "cpu_min_ac": (SUB_PROCESSOR, PROCTHROTTLEMIN, val_str),
            "cpu_max_ac": (SUB_PROCESSOR, PROCTHROTTLEMAX, val_str),
            "cpu_max_freq_ac": (SUB_PROCESSOR, PROCMAXFREQ, val_str),
            "cooling_policy_ac": (SUB_PROCESSOR, SYSCOOLPOL, val_str),
            "boost_mode_ac": (SUB_PROCESSOR, PERFBOOSTMODE, val_str),
            "core_parking_min_ac": (SUB_PROCESSOR, CPMINCORES, val_str),
            "core_parking_max_ac": (SUB_PROCESSOR, CPMAXCORES, val_str),
            "energy_perf_pref_ac": (SUB_PROCESSOR, PERFEPP, val_str),
            "pcie_aspm_ac": (SUB_PCIEXPRESS, ASPM, val_str),
            "usb_suspend_ac": (SUB_USB, USBSELECT, val_str),
            "wifi_power_saving_ac": (SUB_WIFI, WIFISAVING, val_str),
            "hybrid_sleep_ac": (SUB_SLEEP, HYBRIDSLEEP, val_str),
            "allow_wake_timers_ac": (SUB_SLEEP, WAKETIMERS, val_str),
            "power_button_ac": (SUB_BUTTONS, POWERBUTTON, val_str),
            "sleep_button_ac": (SUB_BUTTONS, SLEEPBUTTON, val_str),
        }
        if key not in mapping:
            return False
        sub, sett, v = mapping[key]
        run_powercfg(["/setacvalueindex", guid, sub, sett, v])
        run_powercfg(["/setdcvalueindex", guid, sub, sett, v])
        active = PowerManagerService.get_active_plan()
        if active and active.guid.lower() == guid.lower():
            run_powercfg(["/setactive", guid])
        return True

    @staticmethod
    def get_plan_settings(guid: str, name: str = "") -> PowerPlanSettings:
        s = PowerPlanSettings(guid=guid, name=name)
        code, out, _ = run_powercfg(["/query", guid])
        if code != 0 or not out:
            return s

        regex = re.compile(
            r"Power Setting GUID:\s*([a-fA-F0-9\-]+)[\s\S]*?"
            r"Current AC Power Setting Index:\s*0x([0-9a-fA-F]+)",
            re.IGNORECASE
        )

        for m in regex.finditer(out):
            s_guid = m.group(1).lower().strip()
            try:
                ac_val = int(m.group(2), 16)
            except ValueError:
                continue

            if s_guid == "3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e":
                s.video_timeout_ac = ac_val // 60
            elif s_guid == "29f6c1db-86da-48c5-9fdb-f2b67b1f44da":
                s.sleep_timeout_ac = ac_val // 60
            elif s_guid in ["6738e2c4-e8a5-4a42-b16a-e040e769756e", "6738e2c4-e8a5-4424-a1ff-8097d77b2d08"]:
                s.disk_timeout_ac = ac_val // 60
            elif s_guid == "9d7815a6-7ee4-497e-8888-515a05f02364":
                s.hibernate_timeout_ac = ac_val // 60
            elif s_guid == "893dee8e-2bef-41e0-89c6-b55d0929964c":
                s.cpu_min_ac = ac_val
            elif s_guid == "bc5038f7-23e0-4960-96da-33abaf5935ec":
                s.cpu_max_ac = ac_val
            elif s_guid in ["75b0ae3f-bce0-45a7-8c89-c9611c25e100", "75b0ae3f-bce0-45a7-8c89-c9611c25e101"]:
                s.cpu_max_freq_ac = ac_val
            elif s_guid in ["94d3a615-a899-4ac5-ae2b-e4d8f634367f", "94d3a615-a899-4ac5-ae2b-e4d8f6343b57"]:
                s.cooling_policy_ac = ac_val
            elif s_guid == "be337238-0d82-4146-a960-4f3749d470c7":
                s.boost_mode_ac = ac_val
            elif s_guid in ["0cc5b647-c1df-4637-891a-dec35c318583", "0cc5b647-c1df-4637-891a-dec35c318584"]:
                s.core_parking_min_ac = ac_val
            elif s_guid in ["ea062031-0e34-4ff1-9b6d-eb1059334028", "ea062031-0e34-4ff1-9b6d-eb1059334029"]:
                s.core_parking_max_ac = ac_val
            elif s_guid in ["36687f9e-e3a5-4dbf-b1dc-15eb381c6863", "36687f9e-e376-4512-a778-dd514d66bb38"]:
                s.energy_perf_pref_ac = ac_val
            elif s_guid in ["ee12f906-d277-404b-b6da-e5fa1a576df5", "ee12f906-d277-47ba-b601-1e445653d4b6"]:
                s.pcie_aspm_ac = ac_val
            elif s_guid == "48e6b7a6-50f5-4782-a5d4-53bb8f07e226":
                s.usb_suspend_ac = ac_val
            elif s_guid == "12bbebe6-58d6-4636-95bb-3217ef867c1a":
                s.wifi_power_saving_ac = ac_val
            elif s_guid == "94ac6d29-73ce-41a6-809f-6363ba21b47e":
                s.hybrid_sleep_ac = ac_val
            elif s_guid == "bd3b718a-0680-4d9d-8ab2-e1d2b4ac806d":
                s.allow_wake_timers_ac = ac_val
            elif s_guid == "7648efa3-dd9c-4e3e-b566-50f929386280":
                s.power_button_ac = ac_val
            elif s_guid == "96996bc0-ad50-47ec-923b-6f41874dd9eb":
                s.sleep_button_ac = ac_val

        return s

    # --- ÖZEL GÜÇ PLANLARI ÜRETME METOTLARI ---

    @staticmethod
    def add_ultimate_performance(name: str = "Ultimate Performance") -> Tuple[bool, str]:
        if PowerManagerService.is_plan_existing(GUID_ULTIMATE_PERF):
            return False, "Ultimate Performance plan already exists in system."
        if PowerManagerService.is_plan_name_existing(name):
            return False, f"'{name}' plan already exists."

        guid = PowerManagerService.duplicate_plan(BASE_ULTIMATE, name, GUID_ULTIMATE_PERF)
        if not guid:
            guid = PowerManagerService.duplicate_plan(BASE_HIGH_PERF, name, GUID_ULTIMATE_PERF)
        if not guid:
            guid = PowerManagerService.duplicate_plan(BASE_BALANCED, name, GUID_ULTIMATE_PERF)
        if not guid:
            return False, "Ultimate Performance could not be created or already exists."

        s = PowerManagerService.get_plan_settings(guid, name)
        s.guid = guid
        s.name = name
        s.cpu_min_ac = 100
        s.cpu_max_ac = 100
        s.cooling_policy_ac = 1
        s.boost_mode_ac = 2
        s.core_parking_min_ac = 100
        s.energy_perf_pref_ac = 0
        s.pcie_aspm_ac = 0
        s.usb_suspend_ac = 0
        s.video_timeout_ac = 0
        s.sleep_timeout_ac = 0
        s.disk_timeout_ac = 0
        ok = PowerManagerService.save_plan_settings(s)
        return ok, "Ultimate Performance plan added successfully." if ok else "Settings could not be saved."

    # --- 4 KADEMELİ ÖZEL WATTCOST GÜÇ PLANLARI (Sabit GUID Mimarisi) ---

    @staticmethod
    def _create_or_update_wattcost_plan(guid: str, base_guids: List[str], name: str, settings: dict) -> Tuple[bool, str]:
        is_new = False
        if not PowerManagerService.is_plan_existing(guid):
            for bg in base_guids:
                if PowerManagerService.duplicate_plan(bg, name, guid):
                    is_new = True
                    break
            if not is_new:
                return False, f"'{name}' oluşturulamadı."
        else:
            PowerManagerService.rename_plan(guid, name)

        s = PowerManagerService.get_plan_settings(guid, name)
        s.guid = guid
        s.name = name
        for k, v in settings.items():
            setattr(s, k, v)
        PowerManagerService.save_plan_settings(s)
        return is_new, f"'{name}' başarıyla {'eklendi' if is_new else 'güncellendi'}."

    @staticmethod
    def add_wattcost_max_saver(name: str = "WattCost Maximum Power Saver") -> Tuple[bool, str]:
        """Plan 1: Maximum Power Saver (No boost, 2000MHz frequency ceiling, deep core parking, lowest idle/load power draw)."""
        return PowerManagerService._create_or_update_wattcost_plan(
            GUID_WATTCOST_MAX_SAVER, [BASE_POWER_SAVER, BASE_BALANCED], name, {
                "cpu_min_ac": 5, "cpu_max_ac": 100, "cpu_max_freq_ac": 2000, "energy_perf_pref_ac": 100,
                "boost_mode_ac": 0, "cooling_policy_ac": 0, "core_parking_min_ac": 0, "core_parking_max_ac": 100,
                "pcie_aspm_ac": 2, "usb_suspend_ac": 1, "wifi_power_saving_ac": 3, "video_timeout_ac": 5,
                "sleep_timeout_ac": 15, "hybrid_sleep_ac": 1, "hibernate_timeout_ac": 60, "allow_wake_timers_ac": 0,
                "power_button_ac": 3, "sleep_button_ac": 1, "disk_timeout_ac": 10
            }
        )

    @staticmethod
    def add_wattcost_bal_saver(name: str = "WattCost Balanced Power Saver") -> Tuple[bool, str]:
        """Plan 2: Balanced Power Saver (Daily usage, 3000MHz frequency ceiling, intelligent dynamic scaling, efficient boost)."""
        return PowerManagerService._create_or_update_wattcost_plan(
            GUID_WATTCOST_BAL_SAVER, [BASE_BALANCED], name, {
                "cpu_min_ac": 5, "cpu_max_ac": 100, "cpu_max_freq_ac": 3000, "energy_perf_pref_ac": 50,
                "boost_mode_ac": 3, "cooling_policy_ac": 1, "core_parking_min_ac": 50, "core_parking_max_ac": 100,
                "pcie_aspm_ac": 1, "usb_suspend_ac": 1, "wifi_power_saving_ac": 1, "video_timeout_ac": 10,
                "sleep_timeout_ac": 30, "hybrid_sleep_ac": 1, "hibernate_timeout_ac": 120, "allow_wake_timers_ac": 2,
                "power_button_ac": 3, "sleep_button_ac": 1, "disk_timeout_ac": 20
            }
        )

    @staticmethod
    def add_wattcost_high_perf(name: str = "WattCost High Performance") -> Tuple[bool, str]:
        """Plan 3: High Performance (Gaming & heavy loads, aggressive boost, screen never sleeps, 30min disk timeout)."""
        return PowerManagerService._create_or_update_wattcost_plan(
            GUID_WATTCOST_HIGH_PERF, [BASE_HIGH_PERF, BASE_BALANCED], name, {
                "cpu_min_ac": 50, "cpu_max_ac": 100, "cpu_max_freq_ac": 0, "energy_perf_pref_ac": 20,
                "boost_mode_ac": 2, "cooling_policy_ac": 1, "core_parking_min_ac": 100, "core_parking_max_ac": 100,
                "pcie_aspm_ac": 0, "usb_suspend_ac": 0, "wifi_power_saving_ac": 0, "video_timeout_ac": 0,
                "sleep_timeout_ac": 60, "hybrid_sleep_ac": 0, "hibernate_timeout_ac": 0, "allow_wake_timers_ac": 1,
                "power_button_ac": 3, "sleep_button_ac": 1, "disk_timeout_ac": 30
            }
        )

    @staticmethod
    def add_wattcost_max_perf(name: str = "WattCost Maximum Performance") -> Tuple[bool, str]:
        """Plan 4: Maximum Performance (Locked ceiling clocks, EPP=0 zero latency, screen & sleep never, 30min disk timeout)."""
        return PowerManagerService._create_or_update_wattcost_plan(
            GUID_WATTCOST_MAX_PERF, [BASE_ULTIMATE, BASE_HIGH_PERF, BASE_BALANCED], name, {
                "cpu_min_ac": 100, "cpu_max_ac": 100, "cpu_max_freq_ac": 0, "energy_perf_pref_ac": 0,
                "boost_mode_ac": 2, "cooling_policy_ac": 1, "core_parking_min_ac": 100, "core_parking_max_ac": 0,
                "pcie_aspm_ac": 0, "usb_suspend_ac": 0, "wifi_power_saving_ac": 0, "video_timeout_ac": 0,
                "sleep_timeout_ac": 0, "hybrid_sleep_ac": 0, "hibernate_timeout_ac": 0, "allow_wake_timers_ac": 1,
                "power_button_ac": 3, "sleep_button_ac": 1, "disk_timeout_ac": 30
            }
        )

    @staticmethod
    def add_amd_ryzen_balanced(name: str = "AMD Ryzen Balanced") -> Tuple[bool, str]:
        if PowerManagerService.is_plan_existing(GUID_AMD_BALANCED):
            return False, "AMD Ryzen Balanced plan already exists in system."
        if PowerManagerService.is_plan_name_existing(name):
            return False, f"'{name}' plan already exists."

        guid = PowerManagerService.duplicate_plan(BASE_BALANCED, name, GUID_AMD_BALANCED)
        if not guid:
            return False, "AMD Ryzen Balanced could not be created or already exists."

        s = PowerManagerService.get_plan_settings(guid, name)
        s.guid = guid
        s.name = name
        # AMD Resmi Yonga Seti Spesifikasyonu:
        s.cpu_min_ac = 90  # Zen mimarisinde saat geçiş gecikmesini sıfırlar
        s.cpu_max_ac = 100
        s.cooling_policy_ac = 1
        s.boost_mode_ac = 2
        s.core_parking_min_ac = 100  # AMD CCX/CCD geçiş gecikmesini önlemek için park yok
        s.energy_perf_pref_ac = 25
        s.pcie_aspm_ac = 1
        s.usb_suspend_ac = 0  # AMD USB kopmalarını önler
        s.video_timeout_ac = 10
        s.sleep_timeout_ac = 20
        ok = PowerManagerService.save_plan_settings(s)
        return ok, "AMD Ryzen Balanced plan added successfully." if ok else "Settings could not be saved."

    @staticmethod
    def add_amd_ryzen_high_performance(name: str = "AMD Ryzen High Performance") -> Tuple[bool, str]:
        if PowerManagerService.is_plan_existing(GUID_AMD_HIGH_PERF):
            return False, "AMD Ryzen High Performance plan already exists in system."
        if PowerManagerService.is_plan_name_existing(name):
            return False, f"'{name}' plan already exists."

        guid = PowerManagerService.duplicate_plan(BASE_HIGH_PERF, name, GUID_AMD_HIGH_PERF)
        if not guid:
            guid = PowerManagerService.duplicate_plan(BASE_BALANCED, name, GUID_AMD_HIGH_PERF)
        if not guid:
            return False, "AMD Ryzen High Performance could not be created or already exists."

        s = PowerManagerService.get_plan_settings(guid, name)
        s.guid = guid
        s.name = name
        s.cpu_min_ac = 100
        s.cpu_max_ac = 100
        s.cooling_policy_ac = 1
        s.boost_mode_ac = 2
        s.core_parking_min_ac = 100
        s.energy_perf_pref_ac = 0
        s.pcie_aspm_ac = 0
        s.usb_suspend_ac = 0
        s.video_timeout_ac = 0
        s.sleep_timeout_ac = 0
        ok = PowerManagerService.save_plan_settings(s)
        return ok, "AMD Ryzen High Performance plan added successfully." if ok else "Settings could not be saved."


class DisplayManagerService:
    """Windows monitör yenileme hızı (Hz) okuma, algılama ve değiştirme servisi."""

    @staticmethod
    def get_monitors() -> list:
        """Bağlı tüm monitörleri (birincil önce) listeler.

        Her kayıt: device_name, name, resolution, current_hz, is_primary
        """
        monitors = []
        if not win32api or not win32con:
            return []

        try:
            index = 0
            while True:
                try:
                    dev = win32api.EnumDisplayDevices(None, index, 0)
                except Exception:
                    break
                index += 1
                if not dev:
                    break
                if not (dev.StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP):
                    continue

                device_name = dev.DeviceName
                name = (dev.DeviceString or device_name).strip()

                # Monitörün gerçek donanım adı (ör. "ASUS VP249")
                try:
                    mon = win32api.EnumDisplayDevices(device_name, 0, 0)
                    if mon and mon.DeviceString and mon.DeviceString.strip():
                        name = mon.DeviceString.strip()
                except Exception:
                    pass

                resolution = "-"
                current_hz = 60
                try:
                    mode = win32api.EnumDisplaySettings(device_name, win32con.ENUM_CURRENT_SETTINGS)
                    if mode:
                        resolution = f"{mode.PelsWidth}x{mode.PelsHeight}"
                        current_hz = int(getattr(mode, 'DisplayFrequency', 60))
                except Exception:
                    pass

                monitors.append({
                    "device_name": device_name,
                    "name": name,
                    "resolution": resolution,
                    "current_hz": current_hz,
                    "is_primary": bool(dev.StateFlags & win32con.DISPLAY_DEVICE_PRIMARY_DEVICE),
                })
        except Exception:
            pass

        monitors.sort(key=lambda m: (not m.get("is_primary"), m.get("device_name") or ""))
        return monitors

    @staticmethod
    def get_current_refresh_rate_for(device_name=None) -> int:
        """Belirtilen monitörün (None = birincil) mevcut yenileme hızını döndürür."""
        if not win32api or not win32con:
            return 60
        try:
            mode = win32api.EnumDisplaySettings(device_name, win32con.ENUM_CURRENT_SETTINGS)
            return int(getattr(mode, 'DisplayFrequency', 60))
        except Exception:
            return DisplayManagerService.get_current_refresh_rate()

    @staticmethod
    def get_supported_rates_for(device_name=None) -> list:
        """Belirtilen monitörün mevcut çözünürlükte desteklediği Hz değerleri."""
        rates = set()
        if not win32api or not win32con:
            return [60]

        try:
            cur = win32api.EnumDisplaySettings(device_name, win32con.ENUM_CURRENT_SETTINGS)
            cur_w, cur_h = cur.PelsWidth, cur.PelsHeight
            index = 0
            while True:
                try:
                    mode = win32api.EnumDisplaySettings(device_name, index)
                except Exception:
                    break
                index += 1
                if not mode:
                    break
                hz = int(getattr(mode, 'DisplayFrequency', 0))
                if hz > 0 and mode.PelsWidth == cur_w and mode.PelsHeight == cur_h:
                    rates.add(hz)
        except Exception:
            pass

        if not rates:
            rates.add(DisplayManagerService.get_current_refresh_rate_for(device_name))
        return sorted(rates)

    @staticmethod
    def set_refresh_rate_for(device_name, target_hz: int) -> bool:
        """Belirtilen monitöre hedef Hz'i uygular."""
        if target_hz <= 0 or not win32api or not win32con:
            return False
        try:
            cur = win32api.EnumDisplaySettings(device_name, win32con.ENUM_CURRENT_SETTINGS)
            if int(getattr(cur, 'DisplayFrequency', 0)) == int(target_hz):
                return True

            target_mode = None
            index = 0
            while True:
                try:
                    mode = win32api.EnumDisplaySettings(device_name, index)
                except Exception:
                    break
                index += 1
                if not mode:
                    break
                if (mode.PelsWidth == cur.PelsWidth and mode.PelsHeight == cur.PelsHeight
                        and int(getattr(mode, 'DisplayFrequency', 0)) == int(target_hz)):
                    target_mode = mode
                    break

            if target_mode is None:
                # Eşleşen mod bulunamadı: DEVMODE'u elle kurcalamak yerine vazgeç
                # (yanlış alanlarla yazmak monitörün kayıtlı modunu bozabiliyor)
                return False

            try:
                ret = win32api.ChangeDisplaySettingsEx(device_name, target_mode, win32con.CDS_UPDATEREGISTRY)
            except Exception:
                ret = win32api.ChangeDisplaySettings(target_mode, win32con.CDS_UPDATEREGISTRY)
            return ret == win32con.DISP_CHANGE_SUCCESSFUL
        except Exception:
            return False

    @staticmethod
    def set_refresh_rate_all(target_hz: int) -> list:
        """Hedef Hz'i tüm bağlı monitörlere uygular (desteklemeyenleri atlar).

        Dönüş: [{'device_name', 'name', 'ok', 'skipped', 'actual'}]
        """
        results = []
        monitors = DisplayManagerService.get_monitors()
        if not monitors:
            ok = DisplayManagerService.set_refresh_rate(target_hz)
            results.append({
                "device_name": "", "name": "Birincil",
                "ok": bool(ok), "skipped": False,
                "actual": DisplayManagerService.get_current_refresh_rate(),
            })
            return results

        for mon in monitors:
            device_name = mon.get("device_name")
            rates = DisplayManagerService.get_supported_rates_for(device_name)
            if target_hz not in rates:
                results.append({
                    "device_name": device_name, "name": mon.get("name", ""),
                    "ok": False, "skipped": True, "actual": mon.get("current_hz", 0),
                })
                continue

            DisplayManagerService.set_refresh_rate_for(device_name, target_hz)
            actual = DisplayManagerService.get_current_refresh_rate_for(device_name)
            results.append({
                "device_name": device_name, "name": mon.get("name", ""),
                "ok": int(actual) == int(target_hz), "skipped": False, "actual": actual,
            })
        return results

    @staticmethod
    def get_monitor_info() -> dict:
        """Kullanıcının bağlı ana ekran monitör adını, çözünürlüğünü ve mevcut Hz değerini döndürür."""
        info = {
            "name": "Standart Monitör",
            "resolution": "1920x1080",
            "current_hz": 60,
            "device_name": r"\\.\DISPLAY1"
        }
        if not win32api or not win32con:
            return info

        try:
            # 1. Ana masaüstü ekran cihazını bul
            i = 0
            primary_dev_name = None
            while True:
                try:
                    d = win32api.EnumDisplayDevices(None, i, 0)
                    if d.StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
                        if (d.StateFlags & win32con.DISPLAY_DEVICE_PRIMARY_DEVICE) or primary_dev_name is None:
                            primary_dev_name = d.DeviceName
                            if d.StateFlags & win32con.DISPLAY_DEVICE_PRIMARY_DEVICE:
                                break
                    i += 1
                except Exception:
                    break

            if primary_dev_name:
                info["device_name"] = primary_dev_name
                # Monitör donanım adını oku
                try:
                    m_dev = win32api.EnumDisplayDevices(primary_dev_name, 0, 0)
                    if m_dev.DeviceString and m_dev.DeviceString.strip():
                        info["name"] = m_dev.DeviceString.strip()
                except Exception:
                    pass

            # Mevcut çözünürlük ve Hz oku
            dev = win32api.EnumDisplaySettings(primary_dev_name, win32con.ENUM_CURRENT_SETTINGS)
            if dev:
                w = getattr(dev, 'PelsWidth', 0)
                h = getattr(dev, 'PelsHeight', 0)
                hz = int(getattr(dev, 'DisplayFrequency', 60))
                if w > 0 and h > 0:
                    info["resolution"] = f"{w}x{h}"
                if hz > 0:
                    info["current_hz"] = hz
        except Exception:
            pass

        return info

    @staticmethod
    def get_supported_refresh_rates() -> list:
        """Kullanıcının mevcut ekran çözünürlüğünde monitörün desteklediği tüm Hz değerlerini döndürür."""
        rates = set()

        info = DisplayManagerService.get_monitor_info()
        cur_hz = int(info.get("current_hz", 60))
        if cur_hz > 0:
            rates.add(cur_hz)

        cur_w = 0
        cur_h = 0
        res_str = info.get("resolution", "")
        if "x" in res_str:
            try:
                parts = res_str.split("x")
                cur_w = int(parts[0])
                cur_h = int(parts[1])
            except Exception:
                pass

        dev_name = info.get("device_name", None)
        targets = [dev_name] if dev_name else []
        if None not in targets:
            targets.append(None)

        # 1. win32api üzerinden EnumDisplaySettingsEx ve EnumDisplaySettings ile tarama
        if win32api and win32con:
            for target in targets:
                # RAWMODE ve standart modları dene
                flags_list = [0x00000002, 0] if hasattr(win32api, 'EnumDisplaySettingsEx') else [0]
                for flg in flags_list:
                    i = 0
                    while True:
                        try:
                            if flg != 0 and hasattr(win32api, 'EnumDisplaySettingsEx'):
                                m = win32api.EnumDisplaySettingsEx(target, i, flg)
                            else:
                                m = win32api.EnumDisplaySettings(target, i)
                            if not m:
                                break
                            w = getattr(m, 'PelsWidth', 0)
                            h = getattr(m, 'PelsHeight', 0)
                            hz = int(getattr(m, 'DisplayFrequency', 0))
                            if hz > 0:
                                if cur_w > 0 and cur_h > 0:
                                    if w == cur_w and h == cur_h:
                                        rates.add(hz)
                                else:
                                    rates.add(hz)
                            i += 1
                        except Exception:
                            break

        # 2. Ctypes Fallback (win32api eksikse veya çözünürlük filtresi boş kaldıysa)
        if len(rates) <= 1:
            try:
                import ctypes
                from ctypes import wintypes
                class _DEVMODEW(ctypes.Structure):
                    _fields_ = [
                        ('dmDeviceName', wintypes.WCHAR * 32),
                        ('dmSpecVersion', wintypes.WORD),
                        ('dmDriverVersion', wintypes.WORD),
                        ('dmSize', wintypes.WORD),
                        ('dmDriverExtra', wintypes.WORD),
                        ('dmFields', wintypes.DWORD),
                        ('dmOrientation', ctypes.c_short),
                        ('dmPaperSize', ctypes.c_short),
                        ('dmPaperLength', ctypes.c_short),
                        ('dmPaperWidth', ctypes.c_short),
                        ('dmScale', ctypes.c_short),
                        ('dmCopies', ctypes.c_short),
                        ('dmDefaultSource', ctypes.c_short),
                        ('dmPrintQuality', ctypes.c_short),
                        ('dmColor', ctypes.c_short),
                        ('dmDuplex', ctypes.c_short),
                        ('dmYResolution', ctypes.c_short),
                        ('dmTTOption', ctypes.c_short),
                        ('dmCollate', ctypes.c_short),
                        ('dmFormName', wintypes.WCHAR * 32),
                        ('dmLogPixels', wintypes.WORD),
                        ('dmBitsPerPel', wintypes.DWORD),
                        ('dmPelsWidth', wintypes.DWORD),
                        ('dmPelsHeight', wintypes.DWORD),
                        ('dmDisplayFlags', wintypes.DWORD),
                        ('dmDisplayFrequency', wintypes.DWORD),
                    ]
                dm = _DEVMODEW()
                dm.dmSize = ctypes.sizeof(_DEVMODEW)
                i = 0
                while ctypes.windll.user32.EnumDisplaySettingsW(None, i, ctypes.byref(dm)):
                    hz = int(dm.dmDisplayFrequency)
                    w = int(dm.dmPelsWidth)
                    h = int(dm.dmPelsHeight)
                    if hz > 0:
                        if cur_w > 0 and cur_h > 0:
                            if w == cur_w and h == cur_h:
                                rates.add(hz)
                        else:
                            rates.add(hz)
                    i += 1
            except Exception:
                pass

        # 3. Son Fallback: Eğer çözünürlük filtresiyle hiç Hz bulunamadıysa tüm modlardan al
        if not rates:
            if cur_hz > 0:
                rates.add(cur_hz)
            else:
                rates.add(60)

        valid_rates = sorted([r for r in rates if r > 0])
        return valid_rates if valid_rates else [60]

    @staticmethod
    def get_current_refresh_rate() -> int:
        """Mevcut monitör yenileme hızını (Hz) döndürür."""
        if not win32api or not win32con:
            return 60
        try:
            m = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            return int(getattr(m, 'DisplayFrequency', 60))
        except Exception:
            return 60

    @staticmethod
    def set_refresh_rate(target_hz: int) -> bool:
        """Hedef monitör yenileme hızını uygular."""
        if target_hz <= 0:
            return False
        try:
            cur_hz = DisplayManagerService.get_current_refresh_rate()
            if cur_hz == target_hz:
                return True

            cur_dev = win32api.EnumDisplaySettings(None, win32con.ENUM_CURRENT_SETTINGS)
            cur_w = cur_dev.PelsWidth
            cur_h = cur_dev.PelsHeight
            cur_bpp = cur_dev.BitsPerPel

            # 1. En uygun tam eşleşen DEVMODE yapısını ara
            target_mode = None
            i = 0
            while True:
                try:
                    m = win32api.EnumDisplaySettings(None, i)
                    if (m.PelsWidth == cur_w and m.PelsHeight == cur_h and
                            m.BitsPerPel == cur_bpp and m.DisplayFrequency == target_hz):
                        target_mode = m
                        break
                    i += 1
                except Exception:
                    break

            if target_mode is None:
                # Eşleşen çözünürlükte sadece Hz uyan herhangi bir modu dene
                i = 0
                while True:
                    try:
                        m = win32api.EnumDisplaySettings(None, i)
                        if m.PelsWidth == cur_w and m.PelsHeight == cur_h and m.DisplayFrequency == target_hz:
                            target_mode = m
                            break
                        i += 1
                    except Exception:
                        break

            if target_mode is not None:
                ret = win32api.ChangeDisplaySettings(target_mode, win32con.CDS_UPDATEREGISTRY)
                if ret == win32con.DISP_CHANGE_SUCCESSFUL:
                    return True
                # Dinamik geçici deneme
                ret = win32api.ChangeDisplaySettings(target_mode, 0)
                if ret == win32con.DISP_CHANGE_SUCCESSFUL:
                    return True

            # 2. Eşleşen mod yoksa zorlamak yerine vazgeç (kayıtlı mod bozulmasın)
            return False
        except Exception:
            return False


class SmartAutoSwitcher:
    """
    4 Kademeli Akıllı Otomatik Güç Planı ve Monitör Hz Yöneticisi:
    Kademe 1 (Boşta / Ultra Tasarruf): tier1_plan_guid + tier1_hz
    Kademe 2 (Düşük / Günlük & Medya): tier2_plan_guid + tier2_hz (GPU/CPU Eşik 2)
    Kademe 3 (Orta / Ağır İş & Multitask): tier3_plan_guid + tier3_hz (GPU/CPU Eşik 3)
    Kademe 4 (Maksimum / Oyun & Render): tier4_plan_guid + tier4_hz (GPU/CPU Eşik 4 | RTSS | Watt)
    """
    def __init__(self, on_plan_switched=None):
        self.enabled = False

        # 4 Kademeli Güç Planı GUID'leri
        self.tier1_plan_guid = ""  # Kademe 1: Boşta / Ultra Tasarruf
        self.tier2_plan_guid = ""  # Kademe 2: Düşük / Günlük & Medya
        self.tier3_plan_guid = ""  # Kademe 3: Orta / Multitask & Kod
        self.tier4_plan_guid = ""  # Kademe 4: Maksimum / Oyun & Render

        # 4 Kademeli Monitör Yenileme Hızı (Hz) Hedefleri (0 = Değiştirme / Pasif)
        self.tier1_hz = 0
        self.tier2_hz = 0
        self.tier3_hz = 0
        self.tier4_hz = 0

        # İkinci monitör için ayrı Hz hedefleri
        self.tier1_hz2 = 0
        self.tier2_hz2 = 0
        self.tier3_hz2 = 0
        self.tier4_hz2 = 0

        # Kullanıcı Tanımlı GPU Kullanım Eşikleri (%)
        self.tier2_gpu_pct = 15.0  # Kademe 2 tetikleme GPU %
        self.tier3_gpu_pct = 40.0  # Kademe 3 tetikleme GPU %
        self.tier4_gpu_pct = 70.0  # Kademe 4 tetikleme GPU %

        # Kullanıcı Tanımlı CPU Kullanım Eşikleri (%)
        self.tier2_cpu_pct = 20.0  # Kademe 2 tetikleme CPU %
        self.tier3_cpu_pct = 45.0  # Kademe 3 tetikleme CPU %
        self.tier4_cpu_pct = 75.0  # Kademe 4 tetikleme CPU %

        # Diğer Tetikleyiciler
        self.watt_threshold = 260.0   # 260W üzeri doğrudan Kademe 4
        self.use_rtss_trigger = True  # 3D Oyun algılandığında doğrudan Kademe 4
        self.use_gpu_trigger = True   # GPU eşiklerini kullan
        self.use_cpu_trigger = True   # CPU eşiklerini kullan
        self.use_watt_trigger = True  # Priz watt eşiğini kullan

        # Gecikme Süreleri (Kararlılık / Titremeyi Önleme)
        self.trigger_seconds = 2  # Yüksek kademeye geçiş gecikmesi
        self.revert_seconds = 5   # Düşük kademeye dönüş gecikmesi

        self.on_plan_switched = on_plan_switched

        self.current_tier = "tier1"   # "tier1" | "tier2" | "tier3" | "tier4"
        self._candidate_tier = "tier1"
        self._streak_count = 0

        # Kademe sayısı (2, 3 veya 4) - kullanıcı seçer
        self.tier_count = 4

        # Monitör Hz otomasyonu açık mı? (kapalıyken kademe Hz hedefleri uygulanmaz)
        self.hz_enabled = True

        # Teşhis / canlı gösterim için son karar bilgisi
        self.last_target_tier = "tier1"
        self.last_reason_text = ""
        self.last_gpu = 0.0
        self.last_cpu = 0.0

    # ------------------------------------------------------------- kademe yardımcıları
    @staticmethod
    def _tier_rank(tier) -> int:
        """'tier3' -> 3"""
        try:
            return int(str(tier).replace("tier", ""))
        except (TypeError, ValueError):
            return 1

    def set_tier_count(self, count):
        """Kademe sayısını 2-4 aralığına sınırlar ve aktif kademeyi buna uyarlar."""
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 4
        self.tier_count = max(2, min(4, count))

        if self._tier_rank(self.current_tier) > self.tier_count:
            self.current_tier = f"tier{self.tier_count}"
        if self._tier_rank(self._candidate_tier) > self.tier_count:
            self._candidate_tier = self.current_tier
        self._streak_count = 0

    def _tier_gpu_thr(self, rank: int) -> float:
        return float(getattr(self, f"tier{rank}_gpu_pct", 100.0))

    def _tier_cpu_thr(self, rank: int) -> float:
        return float(getattr(self, f"tier{rank}_cpu_pct", 100.0))

    def evaluate(self, is_rtss_active: bool, gpu_uti: float, cpu_uti: float, total_watt: float):
        """Her 1 saniyelik güncelleme döngüsünde donanım sensörleri ile çağrılır."""
        if not self.enabled:
            return

        top_rank = self.tier_count
        top_tier = f"tier{top_rank}"

        # Hangi kademe eşikleri aşıldı? (2..en üst)
        hit_ranks = [
            rank for rank in range(2, top_rank + 1)
            if (self.use_gpu_trigger and gpu_uti >= self._tier_gpu_thr(rank))
            or (self.use_cpu_trigger and cpu_uti >= self._tier_cpu_thr(rank))
        ]

        # 1. EN ÜST KADEME (Maksimum) ŞARTLARI
        is_top = False
        reason = ""
        if self.use_rtss_trigger and is_rtss_active:
            is_top = True
            reason = _t("smart_reason_rtss_game", "RTSS 3D Oyun Algılandı")
        elif self.use_watt_trigger and total_watt >= self.watt_threshold:
            is_top = True
            reason = _t("smart_reason_wall_watt", "Priz Gücü {thresh:.0f}W Eşiğini Aştı ({watt:.0f}W)").format(thresh=self.watt_threshold, watt=total_watt)

        # 2. KADEME BELİRLEME HİYERARŞİSİ
        if is_top:
            target_tier = top_tier
        elif hit_ranks:
            top_hit = max(hit_ranks)
            target_tier = f"tier{top_hit}"
            if top_hit >= top_rank:
                reason = _t("smart_reason_heavy_load", "Ağır Donanım Yükü (GPU: %{gpu:.0f} | CPU: %{cpu:.0f})").format(gpu=gpu_uti, cpu=cpu_uti)
            elif top_rank >= 4 and top_hit >= 3:
                reason = _t("smart_reason_mid_load", "Orta-Ağır İş Yükü (GPU: %{gpu:.0f} | CPU: %{cpu:.0f})").format(gpu=gpu_uti, cpu=cpu_uti)
            else:
                reason = _t("smart_reason_daily_load", "Günlük & Medya Yükü (GPU: %{gpu:.0f} | CPU: %{cpu:.0f})").format(gpu=gpu_uti, cpu=cpu_uti)
        else:
            target_tier = "tier1"
            reason = _t("smart_reason_idle", "Sistem Boşta / Ultra Tasarruf")

        # 3. KARARLILIK / GECİKME FİLTRESİ
        target_rank = self._tier_rank(target_tier)
        current_rank = self._tier_rank(self.current_tier)

        # Canlı gösterim için son hedef/neden
        self.last_target_tier = target_tier
        self.last_reason_text = reason
        self.last_gpu = gpu_uti
        self.last_cpu = cpu_uti

        req_streak = self.trigger_seconds if target_rank > current_rank else self.revert_seconds

        if target_tier != self.current_tier:
            if target_tier == self._candidate_tier:
                self._streak_count += 1
                if self._streak_count >= req_streak:
                    self._apply_tier(target_tier, reason)
            else:
                self._candidate_tier = target_tier
                self._streak_count = 1
        else:
            self._candidate_tier = self.current_tier
            self._streak_count = 0

    def _apply_hz_targets(self, rank: int):
        """Verilen kademenin 1. ve 2. monitör Hz hedeflerini uygular ve geri okuyarak doğrular."""
        hz1 = int(getattr(self, f"tier{rank}_hz", 0) or 0)
        hz2 = int(getattr(self, f"tier{rank}_hz2", 0) or 0)
        self.last_hz_results = []

        if not self.hz_enabled or (hz1 <= 0 and hz2 <= 0):
            return None, None

        try:
            monitors = DisplayManagerService.get_monitors()
            if not monitors:
                monitors = [{"device_name": "", "name": "Birincil", "current_hz": 0}]

            for idx, mon in enumerate(monitors[:2]):
                want = hz1 if idx == 0 else hz2
                if want <= 0:
                    continue
                dev = mon.get("device_name")
                rates = DisplayManagerService.get_supported_rates_for(dev)
                skipped = want not in rates
                if not skipped:
                    DisplayManagerService.set_refresh_rate_for(dev, want)
                actual = DisplayManagerService.get_current_refresh_rate_for(dev)
                self.last_hz_results.append({
                    "device_name": dev,
                    "name": mon.get("name", ""),
                    "target": want,
                    "ok": (not skipped) and int(actual) == int(want),
                    "skipped": skipped,
                    "actual": actual,
                })

            applied = [r for r in self.last_hz_results if not r.get("skipped")]
            hz_ok = (bool(applied) and all(r.get("ok") for r in applied)) if self.last_hz_results else None
            return DisplayManagerService.get_current_refresh_rate(), hz_ok
        except Exception:
            return None, False

    def apply_current_hz(self):
        """Aktif kademenin Hz hedeflerini yeniden uygular (açılışta / anahtar açılınca)."""
        return self._apply_hz_targets(self._tier_rank(self.current_tier))

    def force_apply_current(self, reason: str = ""):
        """Aktif kademeyi (güç planı + monitör Hz) hemen uygular.

        Açılışta ve otomasyon elle açıldığında kullanılır; aksi halde
        current_tier 'tier1' görünse bile o kademenin ayarları uygulanmaz.
        """
        if not self.enabled:
            return False

        rank = self._tier_rank(self.current_tier)
        if rank > self.tier_count:
            self.current_tier = f"tier{self.tier_count}"

        self._apply_tier(
            self.current_tier,
            reason or _t("smart_reason_startup", "Otomasyon başlatıldı")
        )
        return True

    def _apply_tier(self, tier: str, reason: str = ""):
        rank = self._tier_rank(tier)

        # İlgili kademenin güç planını belirle (istenen kademeden başlayan fallback zinciri)
        target_guid = ""
        order = [rank] + [r for r in range(self.tier_count, 0, -1) if r != rank]
        candidates = []
        for r in order:
            guid = str(getattr(self, f"tier{r}_plan_guid", "") or "")
            if guid and guid not in candidates:
                candidates.append(guid)

        # Sistemde gerçekten var olan ilk planı seç (silinmiş GUID'lere takılmayalım)
        for guid in candidates:
            try:
                if PowerManagerService.is_plan_existing(guid):
                    target_guid = guid
                    break
            except Exception:
                target_guid = guid
                break

        if not target_guid and candidates:
            target_guid = candidates[0]

        if not target_guid:
            return

        # Kademenin monitör bazlı Hz hedefleri (1. ve 2. monitör ayrı seçilir)
        target_hz = int(getattr(self, f"tier{rank}_hz", 0) or 0)
        target_hz2 = int(getattr(self, f"tier{rank}_hz2", 0) or 0)

        hz_actual = None
        hz_ok = None
        self.last_hz_results = []
        if self.hz_enabled and (target_hz > 0 or target_hz2 > 0):
            hz_actual, hz_ok = self._apply_hz_targets(rank)

        ok = PowerManagerService.set_active_plan(target_guid)
        if ok or target_hz > 0 or target_hz2 > 0:
            self.current_tier = tier
            self._streak_count = 0

            if self.on_plan_switched:
                self.on_plan_switched(tier, target_guid, target_hz, reason, hz_actual, hz_ok)
