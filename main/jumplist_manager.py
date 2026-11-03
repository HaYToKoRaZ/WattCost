"""
WattCost HaYTooL - Windows Görev Çubuğu Atlama Listesi (Jump List) Yöneticisi
Kullanıcı görev çubuğundaki simgeye sağ tıkladığında sekmeleri (Maliyet, Güç Planı,
Akıllı Geçiş, Karşılaştırma) ve sistemdeki dinamik güç planlarını hızlı görev olarak sunar.
"""
import os
import sys
import ctypes

APP_USER_MODEL_ID = "HaYTooL.WattCost"

def init_app_user_model_id():
    """Windows'a uygulamanın açık AppUserModelID'sini bildirir."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass

def setup_jump_list(power_plans=None):
    """
    Görev çubuğu sağ tık menüsüne (Jump List Tasks) dinamik görevleri ekler:
    - Uygulama Sekmeleri (Maliyet, Güç Planı, Akıllı Geçiş, Karşılaştırma)
    - Sistemdeki Güncel Güç Düzenleri (Dinamik - ekleme/silme ile senkronize)
    - Hızlı Kısayollar (Akıllı Mod, RivaTuner OSD)
    """
    if os.name != 'nt':
        return False

    try:
        import pythoncom
        from win32com.shell import shell
        from win32com.propsys import propsys, pscon
        from language_manager import _t
        from config_manager import _app_dir
        from power_manager import PowerManagerService

        try:
            pythoncom.CoInitialize()
        except Exception:
            pass

        # 1. Hedef EXE Yolunu Belirle
        if getattr(sys, 'frozen', False):
            target_exe = sys.executable
        else:
            cand_exe = os.path.join(_app_dir, "dist", "WattCost. HaYTooL.exe")
            if os.path.exists(cand_exe):
                target_exe = cand_exe
            else:
                target_exe = sys.executable

        # 2. ICustomDestinationList oluştur
        cdl = pythoncom.CoCreateInstance(
            shell.CLSID_DestinationList,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_ICustomDestinationList
        )
        cdl.SetAppID(APP_USER_MODEL_ID)

        # Listeyi başlat
        slots, removed = cdl.BeginList()

        # 3. Görevler koleksiyonunu oluştur
        collection = pythoncom.CoCreateInstance(
            shell.CLSID_EnumerableObjectCollection,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IObjectCollection
        )

        def _add_task(title: str, args: str):
            try:
                link = pythoncom.CoCreateInstance(
                    shell.CLSID_ShellLink,
                    None,
                    pythoncom.CLSCTX_INPROC_SERVER,
                    shell.IID_IShellLink
                )
                link.SetPath(target_exe)
                link.SetArguments(args)
                link.SetIconLocation(target_exe, 0)

                ps = link.QueryInterface(propsys.IID_IPropertyStore)
                ps.SetValue(pscon.PKEY_Title, propsys.PROPVARIANTType(title))
                ps.Commit()

                collection.AddObject(link)
            except Exception:
                pass

        def _add_separator():
            try:
                sep = pythoncom.CoCreateInstance(
                    shell.CLSID_ShellLink,
                    None,
                    pythoncom.CLSCTX_INPROC_SERVER,
                    shell.IID_IShellLink
                )
                ps = sep.QueryInterface(propsys.IID_IPropertyStore)
                pkey_sep = propsys.PSGetPropertyKeyFromName("System.AppUserModel.IsDestListSeparator")
                ps.SetValue(pkey_sep, propsys.PROPVARIANTType(True))
                ps.Commit()
                collection.AddObject(sep)
            except Exception:
                pass

        # BÖLÜM 1: Sekmeler
        _add_task("⚡ " + _t("jumplist_tab_cost", "Maliyet & Tüketim"), "--tab cost")
        _add_task("⚙️ " + _t("jumplist_tab_powerplan", "Güç Planı Yöneticisi"), "--tab powerplan")
        _add_task("🤖 " + _t("jumplist_tab_smart", "4 Kademeli Akıllı Otomasyon"), "--tab smart")
        _add_task("⚖️ " + _t("jumplist_tab_compare", "Plan Karşılaştırma Matrisi"), "--tab compare")

        _add_separator()

        # BÖLÜM 2: Sistemdeki Dinamik Güç Planları
        if power_plans is None:
            power_plans = PowerManagerService.get_power_plans()

        if power_plans:
            # Aktif planı en başa al, ardından diğer planları ekle (en fazla 6 plan)
            sorted_plans = sorted(power_plans, key=lambda p: (not p.is_active, p.name))
            for p in sorted_plans[:6]:
                active_str = f" ({_t('jumplist_active_marker', '● Aktif')})" if p.is_active else ""
                icon = getattr(p, 'badge_icon', '⚡')
                _add_task(f"{icon} {p.name}{active_str}", f"--plan {p.guid}")

        _add_separator()

        # BÖLÜM 3: Hızlı Kısayollar
        _add_task("🤖 " + _t("jumplist_task_smart", "Akıllı Modu Değiştir"), "--smart toggle")
        _add_task("📊 " + _t("jumplist_task_osd", "RivaTuner (RTSS) OSD"), "--osd toggle")

        # Görevleri listeye ekle ve kaydet
        cdl.AddUserTasks(collection)
        cdl.CommitList()
        return True
    except Exception:
        return False
