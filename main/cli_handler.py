"""
WattCost HaYTooL - CLI (Command Line Interface) Komut Yöneticisi
Uygulama konsoldan argümanlarla çağrıldığında komutları ayrıştırır,
arka planda açık olan GUI örneğine soketle bildirir (Toast tetikler)
veya bağımsız (headless) olarak doğrudan Windows API üzerinden işletir.
"""

import sys
import os
import argparse
import difflib

# Windows Terminal UTF-8 Çıktı Desteği
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from config_manager import send_instance_command, load_config_dict, save_config_dict, CONFIG_FILE_NAME
from power_manager import PowerManagerService, DisplayManagerService
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
    title = _t("cli_banner_title", "⚡ WattCost HaYTooL • CLI Güç & Donanım Komut Arayüzü")
    banner = f"""
{CLR_CYAN}{CLR_BOLD}========================================================================
 {title}
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


VALID_CLI_FLAGS = [
    "-h", "--help",
    "-l", "--list-plans",
    "-p", "--plan",
    "-s", "--smart",
    "--hz",
    "--status",
    "--osd",
    "--tab",
    "--tray",
    "--exit", "exit", "--quit", "quit",
    "--hide", "hide",
    "--hide1", "hide1",
    "--hide2", "hide2",
    "--hide3", "hide3",
    "--hide4", "hide4",
    "--hide-auto", "hideauto",
]


def _suggest_matches(word: str, candidates: list, n: int = 3, cutoff: float = 0.5) -> list:
    """Verilen hatalı girişe en yakın geçerli komut/parametre önerilerini döner."""
    if not word or not candidates:
        return []
    return difflib.get_close_matches(word.strip().lower(), candidates, n=n, cutoff=cutoff)


def _print_suggestion(word: str, candidates: list):
    matches = _suggest_matches(word, candidates)
    if matches:
        sugg = ", ".join(f"{CLR_CYAN}{m}{CLR_RESET}" for m in matches)
        print(f" {CLR_YELLOW}{_t('cli_did_you_mean', 'Bunu mu demek istediniz:')}{CLR_RESET} {sugg}")


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
            err_msg = _t("cli_err_plan_not_found", "'{spec}' ile eşleşen bir güç planı bulunamadı!").format(spec=specifier)
            print(f"{CLR_RED}[HATA] {err_msg}{CLR_RESET}")
            plans = PowerManagerService.get_power_plans()
            if plans:
                _print_suggestion(specifier, [p.name.lower() for p in plans])
            print(f" {_t('cli_hint_help', 'Tüm geçerli komutları görmek için: WattCost. HaYTooL.exe --help')}")
            print(f" {CLR_CYAN}WattCost. HaYTooL.exe --list-plans{CLR_RESET}")
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
        err_msg = _t("cli_err_invalid_param", "Geçersiz parametre: '{val}'").format(val=action)
        print(f"{CLR_RED}[HATA] {err_msg}{CLR_RESET}")
        _print_suggestion(act, ["on", "off", "toggle", "status"])
        print(f"Kullanım: {CLR_CYAN}WattCost. HaYTooL.exe --smart <on | off | toggle | status>{CLR_RESET}")
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
    """Birincil monitörün yenileme hızını (Hz) doğrular ve ayarlar."""
    print_banner()
    supported = DisplayManagerService.get_supported_refresh_rates()
    if supported and hz_val not in supported:
        print(f"{CLR_RED}[HATA] {_t('cli_err_hz_unsupported', '{hz} Hz değeri mevcut monitör tarafından desteklenmiyor!').format(hz=hz_val)}{CLR_RESET}")
        rates_str = ", ".join(f"{r} Hz" for r in supported)
        print(f" {CLR_CYAN}{_t('cli_hz_supported_list', 'Desteklenen değerler: {rates}').format(rates=rates_str)}{CLR_RESET}")
        return

    is_gui_running, resp = send_instance_command(f"CMD:set_hz {hz_val}")
    if is_gui_running and resp.startswith("OK"):
        print(f"{CLR_GREEN}{CLR_BOLD}[BAŞARILI]{CLR_RESET} {_t('cli_ok_hz_set', 'Monitör yenileme hızı {hz} Hz olarak ayarlandı.').format(hz=hz_val)}")
        return

    ok = DisplayManagerService.set_refresh_rate(hz_val)
    actual = DisplayManagerService.get_current_refresh_rate()
    if ok or int(actual) == int(hz_val):
        print(f"{CLR_GREEN}{CLR_BOLD}[BAŞARILI]{CLR_RESET} {_t('cli_ok_hz_set', 'Monitör yenileme hızı {hz} Hz olarak ayarlandı.').format(hz=actual)}")
    else:
        print(f"{CLR_RED}[HATA] {_t('cli_err_hz_failed', 'Monitör yenileme hızı {hz} Hz olarak ayarlanamadı (şu an {actual} Hz).').format(hz=hz_val, actual=actual)}{CLR_RESET}")


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
    if act not in ("on", "off", "toggle", "1", "0", "true", "false"):
        err_msg = _t("cli_err_invalid_param", "Geçersiz parametre: '{val}'").format(val=action)
        print(f"{CLR_RED}[HATA] {err_msg}{CLR_RESET}")
        _print_suggestion(act, ["on", "off", "toggle"])
        print(f"Kullanım: {CLR_CYAN}WattCost. HaYTooL.exe --osd <on | off | toggle>{CLR_RESET}")
        return
    if act in ("1", "true"):
        act = "on"
    elif act in ("0", "false"):
        act = "off"

    is_gui_running, resp = send_instance_command(f"CMD:osd {act}")
    if is_gui_running and resp.startswith("OK"):
        print(f"{CLR_GREEN}{CLR_BOLD}[BAŞARILI]{CLR_RESET} RivaTuner OSD güncellendi:")
        print(f"  • {resp.replace('OK:', '').strip()}")
    else:
        print(f"{CLR_YELLOW}[BİLGİ] OSD yönetimi için WattCost uygulamasının arka planda çalışıyor olması gerekir.{CLR_RESET}")


def cmd_tab(tab_name: str) -> bool:
    """WattCost penceresini öne getirir ve belirtilen sekmeye geçirir."""
    target = tab_name.strip().lower()
    valid_tabs = ["cost", "powerplan", "smart", "compare"]
    if target not in valid_tabs:
        print_banner()
        err_msg = _t("cli_err_invalid_param", "Geçersiz parametre: '{val}'").format(val=tab_name)
        print(f"{CLR_RED}[HATA] {err_msg}{CLR_RESET}")
        _print_suggestion(target, valid_tabs)
        print(f"Kullanım: {CLR_CYAN}WattCost. HaYTooL.exe --tab <cost | powerplan | smart | compare>{CLR_RESET}")
        return True

    is_gui_running, resp = send_instance_command(f"CMD:tab {target}")
    if is_gui_running and resp.startswith("OK"):
        print_banner()
        ok_msg = _t("cli_ok_tab_switched", "Pencere öne getirildi ve '{tab}' sekmesi açıldı.").format(tab=target)
        print(f"{CLR_GREEN}{CLR_BOLD}[BAŞARILI]{CLR_RESET} {ok_msg}")
        return True
    print_banner()
    print(f"{CLR_YELLOW}[BİLGİ] {_t('cli_err_tab_gui_closed', 'Sekme geçişi için WattCost uygulaması arka planda çalışıyor olmalıdır.')}{CLR_RESET}")
    return True


def cmd_exit():
    """Çalışan GUI veya gizli (--hide) WattCost örneğini verileri kaydederek kapatır."""
    print_banner()
    closed_any = False

    ok, res = send_instance_command("CLI:exit")
    if ok and str(res).startswith("OK:"):
        closed_any = True

    try:
        import ctypes
        h_evt = ctypes.windll.kernel32.OpenEventW(0x0002, False, "Local\\WattCostHiddenStop")
        if h_evt:
            ctypes.windll.kernel32.SetEvent(h_evt)
            ctypes.windll.kernel32.CloseHandle(h_evt)
            closed_any = True
    except Exception:
        pass

    if closed_any:
        print(f"{CLR_GREEN}[OK] {_t('cli_ok_exit', 'WattCost kapatma sinyali gönderildi (veriler kaydedildi).')}{CLR_RESET}\n")
    else:
        print(f"{CLR_YELLOW}[!] {_t('cli_err_not_running', 'Arka planda çalışan bir WattCost örneği bulunamadı.')}{CLR_RESET}\n")


def handle_cli_args() -> bool:
    """
    Komut satırı argümanlarını inceler.
    Eğer bir CLI komutu çalıştırıldıysa işlemi yapar ve True döner (böylece GUI açılmaz).
    Eğer hiçbir CLI argümanı verilmediyse False döner (normal GUI başlatılır).
    """
    if len(sys.argv) <= 1:
        return False

    # --watch ve --hide/hide/hide1..4/hideauto parametreleri arka plan izleyicileridir, CLI olarak kesme
    if sys.argv[1].lower().lstrip("-") in ("watch", "hide", "hide1", "hide2", "hide3", "hide4", "hideauto", "hide-auto"):
        return False

    # Uygulama ayarlarındaki dili CLI çıktıları için de başlat (TR / EN uyumu)
    try:
        from language_manager import LanguageManager
        LanguageManager.get_instance().init_language(load_config_dict().get("language", "auto"))
    except Exception:
        pass

    # Çıplak 'exit' / 'quit' argümanlarını '--exit' olarak kabul et
    if sys.argv[1].lower() in ("exit", "quit"):
        cmd_exit()
        return True

    parser = argparse.ArgumentParser(
        prog="WattCost. HaYTooL.exe",
        description="WattCost HaYTooL CLI",
        add_help=False,
        exit_on_error=False
    )

    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-l", "--list-plans", action="store_true")
    parser.add_argument("-p", "--plan", type=str)
    parser.add_argument("-s", "--smart", type=str)
    parser.add_argument("--hz", type=int)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--osd", type=str)
    parser.add_argument("--tab", type=str)
    parser.add_argument("--exit", "--quit", action="store_true")

    try:
        args, unknown = parser.parse_known_args()
    except (argparse.ArgumentError, SystemExit, Exception) as e:
        print_banner()
        err_lbl = _t("cli_err_prefix", "HATA")
        print(f"{CLR_RED}[{err_lbl}] {_t('cli_err_parse', 'Komut satırı argüman hatası: {err}').format(err=e)}{CLR_RESET}")
        if len(sys.argv) > 1:
            _print_suggestion(sys.argv[1], VALID_CLI_FLAGS)
        print(f" {_t('cli_hint_help', 'Tüm geçerli komutları görmek için: WattCost. HaYTooL.exe --help')}")
        return True

    if unknown:
        print_banner()
        bad_arg = unknown[0]
        err_lbl = _t("cli_err_prefix", "HATA")
        err_msg = _t("cli_err_unknown_arg", "Bilinmeyen veya hatalı komut: '{arg}'").format(arg=bad_arg)
        print(f"{CLR_RED}[{err_lbl}] {err_msg}{CLR_RESET}")
        _print_suggestion(bad_arg, VALID_CLI_FLAGS)
        print(f" {_t('cli_hint_help', 'Tüm geçerli komutları görmek için: WattCost. HaYTooL.exe --help')}")
        return True

    # Yardım Göster
    if args.help:
        print_banner()
        print(f"""
{CLR_BOLD}{_t('cli_help_title', 'KULLANIM:')}{CLR_RESET}
  WattCost. HaYTooL.exe [OPTIONS]

{CLR_BOLD}{_t('cli_help_cmds', 'KOMUTLAR VE SEÇENEKLER:')}{CLR_RESET}
  {CLR_CYAN}-p, --plan <1-4 | GUID | name>{CLR_RESET}
      {_t('cli_desc_plan_name', 'Plan adına göre kısmi eşleşmeyle güç planını uygular.')}

  {CLR_CYAN}-s, --smart <on | off | toggle | status>{CLR_RESET}
      {_t('cli_desc_smart_on', '4 kademeli dinamik akıllı geçiş otomasyonunu aktif eder.')}

  {CLR_CYAN}--hz <Hz>{CLR_RESET}
      {_t('cli_desc_hz', 'Birincil monitörün yenileme hızını doğrudan ayarlar (örn. 60, 144).')}

  {CLR_CYAN}-l, --list-plans{CLR_RESET}
      {_t('cli_desc_list_plans', 'Sistemdeki tüm kayıtlı güç planlarını listeler.')}

  {CLR_CYAN}--status{CLR_RESET}
      {_t('cli_desc_status', 'Aktif güç planını, canlı priz gücünü (W) ve akıllı mod durumunu özetler.')}

  {CLR_CYAN}--osd <on | off | toggle>{CLR_RESET}
      {_t('cli_desc_osd_toggle', 'Oyun içi RivaTuner (RTSS) bilgi ekranını açar veya kapatır.')}

  {CLR_CYAN}--tab <cost | powerplan | smart | compare>{CLR_RESET}
      {_t('cli_desc_tab', 'Açık pencereyi öne getirip belirtilen sekmeye geçer (cost, powerplan, smart, compare).')}

  {CLR_CYAN}hide, --hide | hide1..hide4 | hideauto{CLR_RESET}
      {_t('cli_desc_hide', 'Pencere ve saat yanı tepsi simgesi açmadan arka planda başlar (yeni INI oluşturmaz).')}

  {CLR_CYAN}exit, --exit, --quit{CLR_RESET}
      {_t('cli_desc_exit', 'Çalışan WattCost penceresini veya gizli arka plan (hide) sürecini verileri kaydederek güvenle kapatır.')}

  {CLR_CYAN}-h, --help{CLR_RESET}
      {_t('cli_desc_help', 'Konsolda tüm CLI komutlarını ve seçeneklerini listeler.')}
""")
        return True

    if args.exit:
        cmd_exit()
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

    if args.hz is not None:
        cmd_set_hz(args.hz)
        return True

    if args.status:
        cmd_status()
        return True

    if args.osd:
        cmd_osd(args.osd)
        return True

    if args.tab:
        return cmd_tab(args.tab)

    return False
