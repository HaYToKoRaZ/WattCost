"""
WattCost HaYTooL - CLI (Command Line Interface) Komut Yöneticisi
Uygulama konsoldan argümanlarla çağrıldığında komutları ayrıştırır,
arka planda açık olan GUI örneğine soketle bildirir (Toast tetikler)
veya bağımsız (headless) olarak doğrudan Windows API üzerinden işletir.
"""

import sys
import os
import argparse

# Windows Terminal UTF-8 Çıktı Desteği
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from config_manager import send_instance_command, load_config_dict, save_config_dict, CONFIG_FILE_NAME
from power_manager import PowerManagerService
from language_manager import _t


# --- Renkli Konsol Çıktısı Yardımcıları ---
CLR_RESET   = "\033[0m"
CLR_CYAN    = "\033[96m"
CLR_GREEN   = "\033[92m"
CLR_YELLOW  = "\033[93m"
CLR_RED     = "\033[91m"
CLR_BOLD    = "\033[1m"
CLR_DIM     = "\033[2m"

def _enable_vt_mode():
    """Windows cmd / powershell için konsola bağlanır (AttachConsole) ve sanal terminal renklerini (ANSI) aktif eder."""
    if os.name == 'nt':
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # Çağıran ebeveyn konsola bağlan (ATTACH_PARENT_PROCESS = -1)
        if kernel32.AttachConsole(-1):
            try:
                # Standart akışları konsola bağla
                sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
                sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
                sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
            except Exception:
                pass
        h_out = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(h_out, ctypes.byref(mode)):
            kernel32.SetConsoleMode(h_out, mode.value | 0x0004)

_enable_vt_mode()

def print_banner():
    banner = f"""
{CLR_CYAN}{CLR_BOLD}========================================================================
 ⚡ WattCost HaYTooL • CLI Güç & Donanım Komut Arayüzü
========================================================================{CLR_RESET}"""
    print(banner)


# Standart 4 Kademe WattCost Plan İsimleri ve Eşleşmeleri
TIER_PLAN_KEYWORDS = {
    1: ["maximum power saver", "ultra saver", "boşta", "tasarruf", "kademe 1", "tier 1"],
    2: ["balanced power saver", "günlük", "medya", "kademe 2", "tier 2"],
    3: ["high performance", "çoklu görev", "orta yük", "kademe 3", "tier 3"],
    4: ["maximum performance", "max power", "oyun", "kademe 4", "tier 4"],
}


def find_plan_by_specifier(specifier: str):
    """
    Kullanıcının girdiği '1', '2', '3', '4', GUID veya kısmi plan adını sistemdeki
    kayıtlı güç planlarıyla eşleştirir ve (PowerPlanItem, tier_number) döner.
    """
    spec = specifier.strip().lower()
    plans = PowerManagerService.get_power_plans()
    if not plans:
        return None, None

    # 1. Sayısal Kademe Girişi (1, 2, 3, 4)
    if spec in ("1", "2", "3", "4"):
        t_num = int(spec)
        keywords = TIER_PLAN_KEYWORDS.get(t_num, [])
        for p in plans:
            p_lower = p.name.lower()
            if "wattcost" in p_lower and any(kw in p_lower for kw in keywords):
                return p, t_num
        # WattCost bulunamadıysa sistemin genel planlarından en uygun olanı bul
        if t_num == 1:
            fallback_kws = ["güç tasarrufu", "power saver"]
        elif t_num == 2:
            fallback_kws = ["dengeli", "balanced"]
        elif t_num in (3, 4):
            fallback_kws = ["nihai", "ultimate", "yüksek", "high performance"]
        for p in plans:
            p_lower = p.name.lower()
            if any(kw in p_lower for kw in fallback_kws):
                return p, t_num

    # 2. Doğrudan GUID eşleşmesi
    for p in plans:
        if p.guid.lower() == spec:
            return p, None

    # 3. Plan Adı ile Kısmi Eşleşme
    for p in plans:
        if spec in p.name.lower():
            return p, None

    return None, None


def cmd_list_plans():
    """Sistemdeki tüm güç planlarını GUID ve aktiflik durumuyla listeler."""
    print_banner()
    plans = PowerManagerService.get_power_plans()
    if not plans:
        print(f"{CLR_RED}[HATA] Sistemdeki güç planları listelenemedi.{CLR_RESET}")
        return

    print(f" {CLR_BOLD}Sistemde Kayıtlı Güç Planları:{CLR_RESET}\n")
    print(f" {'DURUM':<8} | {'KADEME':<8} | {'PLAN ADI':<36} | {'GUID'}")
    print(f" " + "-" * 75)

    for p in plans:
        # Kademe tespit et
        t_label = "-"
        p_lower = p.name.lower()
        if "maximum power saver" in p_lower:
            t_label = "Kademe 1"
        elif "balanced power saver" in p_lower:
            t_label = "Kademe 2"
        elif "high performance" in p_lower and "wattcost" in p_lower:
            t_label = "Kademe 3"
        elif "maximum performance" in p_lower and "wattcost" in p_lower:
            t_label = "Kademe 4"

        if p.is_active:
            status_tag = f"{CLR_GREEN}{CLR_BOLD}* AKTİF{CLR_RESET}"
            name_tag = f"{CLR_GREEN}{CLR_BOLD}{p.name}{CLR_RESET}"
        else:
            status_tag = f"{CLR_DIM}  Pasif{CLR_RESET}"
            name_tag = f"{CLR_CYAN}{p.name}{CLR_RESET}"

        print(f" {status_tag:<17} | {t_label:<8} | {name_tag:<45} | {CLR_DIM}{p.guid}{CLR_RESET}")

    print(f" " + "-" * 75)
    print(f"\n {CLR_YELLOW}💡 İpucu: Plan değiştirmek için:{CLR_RESET} WattCost.exe --plan <1-4|GUID|isim>\n")


def cmd_set_plan(specifier: str):
    """Güç planını değiştirir. Açık GUI varsa socket ile bildirir, yoksa doğrudan uygular."""
    print_banner()
    plan, tier = find_plan_by_specifier(specifier)
    if not plan:
        # Eğer WattCost planları henüz eklenmemişse ve 1-4 girildiyse, otomatik ekleyip tekrar dene
        if specifier in ("1", "2", "3", "4"):
            print(f"{CLR_YELLOW}[i] WattCost planları sistemde bulunamadı, otomatik ekleniyor...{CLR_RESET}")
            PowerManagerService.add_wattcost_max_saver()
            PowerManagerService.add_wattcost_bal_saver()
            PowerManagerService.add_wattcost_high_perf()
            PowerManagerService.add_wattcost_max_perf()
            plan, tier = find_plan_by_specifier(specifier)

        if not plan:
            print(f"{CLR_RED}[HATA] '{specifier}' ile eşleşen bir güç planı bulunamadı!{CLR_RESET}")
            print(f"Sistemdeki planları görmek için: {CLR_CYAN}WattCost.exe --list-plans{CLR_RESET}")
            return

    # Önce açık GUI uygulamasına komut iletmeyi dene
    is_gui_running, resp = send_instance_command(f"CMD:set_plan {plan.guid}")
    if is_gui_running and resp.startswith("OK"):
        print(f"{CLR_GREEN}{CLR_BOLD}[BAŞARILI]{CLR_RESET} Güç planı aktif GUI üzerinden değiştirildi:")
        print(f"  • Plan:   {CLR_CYAN}{plan.name}{CLR_RESET}")
        print(f"  • GUID:   {CLR_DIM}{plan.guid}{CLR_RESET}")
        print(f"  • Bildirim: Ekranın sağ altında Toast bildirimi gösterildi.")
        return

    # GUI açık değilse bağımsız (headless) Windows API ile uygula
    ok = PowerManagerService.set_active_plan(plan.guid)
    if ok:
        print(f"{CLR_GREEN}{CLR_BOLD}[BAŞARILI]{CLR_RESET} Windows güç planı başarıyla değiştirildi (Headless):")
        print(f"  • Plan:   {CLR_CYAN}{plan.name}{CLR_RESET}")
        print(f"  • GUID:   {CLR_DIM}{plan.guid}{CLR_RESET}")
    else:
        print(f"{CLR_RED}[HATA] Güç planı uygulanamadı.{CLR_RESET}")


def cmd_smart_switch(action: str):
    """Akıllı güç modunu (SmartSwitch) açar, kapatır, toggle yapar veya durumunu sorgular."""
    print_banner()
    act = action.strip().lower()

    if act not in ("on", "off", "toggle", "status", "1", "0", "true", "false"):
        print(f"{CLR_RED}[HATA] Geçersiz parametre: '{action}'{CLR_RESET}")
        print(f"Kullanım: {CLR_CYAN}WattCost.exe --smart <on | off | toggle | status>{CLR_RESET}")
        return

    # Normalizasyon
    if act in ("1", "true"):
        act = "on"
    elif act in ("0", "false"):
        act = "off"

    # Açık GUI'ye ilet
    is_gui_running, resp = send_instance_command(f"CMD:smart {act}")
    if is_gui_running and resp.startswith("OK"):
        status_info = resp.replace("OK:", "").strip()
        print(f"{CLR_GREEN}{CLR_BOLD}[BAŞARILI]{CLR_RESET} Akıllı Güç Modu (GUI Üzerinden Güncellendi):")
        print(f"  • Durum: {CLR_CYAN}{status_info}{CLR_RESET}")
        return

    # GUI açık değilse doğrudan INI dosyasını güncelle
    cfg = load_config_dict()
    cur_state = bool(cfg.get("smart_switch_enabled", False))

    if act == "status":
        st_text = f"{CLR_GREEN}AKTİF (Açık){CLR_RESET}" if cur_state else f"{CLR_DIM}DEVRE DIŞI (Kapalı){CLR_RESET}"
        print(f" Akıllı Güç Modu Durumu: {st_text}")
        return

    if act == "on":
        new_state = True
    elif act == "off":
        new_state = False
    elif act == "toggle":
        new_state = not cur_state
    else:
        new_state = cur_state

    cfg["smart_switch_enabled"] = new_state
    save_config_dict(cfg)

    st_text = f"{CLR_GREEN}{CLR_BOLD}AÇIK (Aktif){CLR_RESET}" if new_state else f"{CLR_RED}{CLR_BOLD}KAPALI (Devre Dışı){CLR_RESET}"
    print(f"{CLR_GREEN}{CLR_BOLD}[BAŞARILI]{CLR_RESET} Akıllı Güç Modu (SmartSwitch) ayarlandı:")
    print(f"  • Yeni Durum: {st_text}")
    print(f"  • Ayar dosyasına kaydedildi ({CONFIG_FILE_NAME}).")


def cmd_set_hz(hz_val: int):
    """Monitörün yenileme hızı komutunu bilgilendirir."""
    print_banner()
    print(f"{CLR_YELLOW}[BİLGİ] Monitör Hz yönetimi Windows 11 kararlılığı ve standart kullanıcı kısıtlamaları nedeniyle devre dışı bırakılmıştır.{CLR_RESET}")


def cmd_status():
    """Uygulama ve sistem güç durumunu özetler."""
    print_banner()
    # 1. Aktif Plan
    active_guid = PowerManagerService.get_active_guid_fast()
    plans = PowerManagerService.get_power_plans()
    active_name = "Bilinmeyen Plan"
    for p in plans:
        if p.guid.lower() == active_guid.lower():
            active_name = p.name
            break

    # 2. Akıllı Geçiş Durumu
    is_gui_running, resp = send_instance_command("CMD:status")
    if is_gui_running and resp.startswith("OK"):
        print(f" {CLR_BOLD}WattCost Durumu (Canlı GUI):{CLR_RESET}")
        lines = resp.replace("OK:", "").strip().split(";")
        for line in lines:
            if line.strip():
                print(f"  • {line.strip()}")
        return

    # Headless Durum
    cfg = load_config_dict()
    smart_on = bool(cfg.get("smart_switch_enabled", False))

    print(f" {CLR_BOLD}Sistem & Güç Durumu (Headless):{CLR_RESET}")
    print(f"  • Aktif Güç Planı:   {CLR_GREEN}{CLR_BOLD}{active_name}{CLR_RESET}")
    print(f"  • Plan GUID:         {CLR_DIM}{active_guid}{CLR_RESET}")
    print(f"  • Akıllı Güç Modu:   {CLR_CYAN}{'AÇIK' if smart_on else 'KAPALI'}{CLR_RESET}")
    print(f"  • Uygulama Durumu:   {CLR_DIM}Arka planda açık değil{CLR_RESET}")


def cmd_osd(action: str):
    """RivaTuner (RTSS) OSD açma/kapatma/toggle işlemi."""
    print_banner()
    act = action.strip().lower()
    is_gui_running, resp = send_instance_command(f"CMD:osd {act}")
    if is_gui_running and resp.startswith("OK"):
        print(f"{CLR_GREEN}{CLR_BOLD}[BAŞARILI]{CLR_RESET} RivaTuner OSD güncellendi:")
        print(f"  • {resp.replace('OK:', '').strip()}")
    else:
        print(f"{CLR_YELLOW}[BİLGİ] OSD yönetimi için WattCost uygulamasının arka planda çalışıyor olması gerekir.{CLR_RESET}")


def cmd_tab(tab_name: str) -> bool:
    """WattCost penceresini öne getirir ve belirtilen sekmeye geçirir."""
    target = tab_name.strip().lower()
    is_gui_running, resp = send_instance_command(f"CMD:tab {target}")
    if is_gui_running and resp.startswith("OK"):
        return True
    return False


def handle_cli_args() -> bool:
    """
    Komut satırı argümanlarını inceler.
    Eğer bir CLI komutu çalıştırıldıysa işlemi yapar ve True döner (böylece GUI açılmaz).
    Eğer hiçbir CLI argümanı verilmediyse False döner (normal GUI başlatılır).
    """
    if len(sys.argv) <= 1:
        return False

    # --watch parametresi rtss_overlay dahili izleyicisidir, onu es geç
    if sys.argv[1] == "--watch":
        return False

    parser = argparse.ArgumentParser(
        prog="WattCost. HaYTooL.exe",
        description="WattCost HaYTooL • PC Güç Planları, Akıllı Otomasyon ve Donanım CLI Yöneticisi",
        add_help=False
    )

    parser.add_argument("-h", "--help", action="store_true", help="Bu yardım kılavuzunu görüntüler.")
    parser.add_argument("-l", "--list-plans", action="store_true", help="Sistemdeki tüm güç planlarını listeler.")
    parser.add_argument("-p", "--plan", type=str, metavar="<1-4|GUID|ad>", help="Güç planını değiştirir (1: Boşta, 2: Günlük, 3: Yüksek, 4: Maksimum).")
    parser.add_argument("-s", "--smart", type=str, metavar="<on|off|toggle|status>", help="Akıllı Güç Modunu (SmartSwitch) açar, kapatır veya sorgular.")
    parser.add_argument("--hz", type=int, metavar="<Hz>", help="Birincil monitörün yenileme hızını doğrudan ayarlar (örn. 60, 144, 165, 240).")
    parser.add_argument("--status", action="store_true", help="Mevcut aktif güç planını ve otomasyon durumunu özetler.")
    parser.add_argument("--osd", type=str, metavar="<on|off|toggle>", help="RivaTuner (RTSS) oyun içi göstergesini açar/kapatır.")
    parser.add_argument("--tab", type=str, metavar="<cost|powerplan|smart|compare>", help=_t("cli_tab_help", "WattCost penceresini öne getirip belirtilen sekmeyi açar."))

    try:
        args, unknown = parser.parse_known_args()
    except Exception as e:
        print(f"{CLR_RED}[HATA] Argüman ayrıştırma hatası: {e}{CLR_RESET}")
        return True

    # Yardım Göster
    if args.help:
        print_banner()
        print(f"""
{CLR_BOLD}KULLANIM:{CLR_RESET}
  WattCost. HaYTooL.exe [SEÇENEKLER]

{CLR_BOLD}KOMUTLAR VE SEÇENEKLER:{CLR_RESET}
  {CLR_CYAN}-p, --plan <1-4 | GUID | ad>{CLR_RESET}
      Güç planını anında değiştirir.
      Örnekler:
        WattCost.exe --plan 1         (Kademe 1: Ultra Tasarruf)
        WattCost.exe --plan 4         (Kademe 4: Maksimum Performans)
        WattCost.exe --plan "Dengeli"
        WattCost.exe -p a8d8...-guid

  {CLR_CYAN}-s, --smart <on | off | toggle | status>{CLR_RESET}
      4 Kademeli Akıllı Güç Modunu (SmartSwitch) yönetir.
      Örnekler:
        WattCost.exe --smart on       (Otomasyonu aktif eder)
        WattCost.exe --smart off      (Devre dışı bırakır)
        WattCost.exe --smart toggle   (Açıksa kapatır, kapalıysa açar)
        WattCost.exe --smart status   (Mevcut durumu sorgular)

  {CLR_CYAN}--hz <Hz Değeri>{CLR_RESET}
      Monitör yenileme hızını ayarlar.
      Örnekler:
        WattCost.exe --hz 60
        WattCost.exe --hz 165
        WattCost.exe --hz 240

  {CLR_CYAN}-l, --list-plans{CLR_RESET}
      Sistemde kayıtlı olan tüm güç planlarını listeler ve aktif olanı gösterir.

  {CLR_CYAN}--status{CLR_RESET}
      Aktif güç planı, SmartSwitch, Hz ve priz gücü durumunu özetler.

  {CLR_CYAN}--osd <on | off | toggle>{CLR_RESET}
      RivaTuner (RTSS) oyun içi OSD göstergesini açar / kapatır.

  {CLR_CYAN}-h, --help{CLR_RESET}
      Bu yardım ekranını görüntüler.
""")
        return True

    if args.list_plans:
        cmd_list_plans()
        return True

    if args.plan:
        cmd_set_plan(args.plan)
        return True

    if args.smart:
        cmd_smart_switch(args.smart)
        return True

    if args.hz:
        cmd_set_hz(args.hz)
        return True

    if args.status:
        cmd_status()
        return True

    if args.osd:
        cmd_osd(args.osd)
        return True

    if args.tab:
        handled = cmd_tab(args.tab)
        if handled:
            return True
        return False

    return False
