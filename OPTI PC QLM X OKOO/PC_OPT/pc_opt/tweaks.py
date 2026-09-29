"""Réglages visuels (API SystemParametersInfo + clés HKCU). Chaque valeur d'origine est sauvegardée."""
import ctypes, json, logging, os, winreg
from ctypes import wintypes
from .common import APP_DIR

log = logging.getLogger("pc_opt.tweaks")
BACKUP = APP_DIR / "backup_reglages.json"
HKCU = winreg.HKEY_CURRENT_USER
user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
user32.SystemParametersInfoW.restype = wintypes.BOOL
SPIF = 0x03  # UPDATEINIFILE | SENDCHANGE

class Tweak:
    def __init__(self, id, label, read, write, target):
        self.id, self.label, self.read, self.write, self.target = id, label, read, write, target

def _spi(cond):
    if not cond:
        raise ctypes.WinError(ctypes.get_last_error())

def _spi_bool(id, label, get, set_):
    def read():
        v = wintypes.BOOL()
        _spi(user32.SystemParametersInfoW(get, 0, ctypes.byref(v), 0))
        return bool(v.value)
    def write(val):
        _spi(user32.SystemParametersInfoW(set_, 0, 1 if val else 0, SPIF))
    return Tweak(id, label, read, write, False)

class _AnimInfo(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("iMinAnimate", ctypes.c_int)]

def _anim():
    def read():
        i = _AnimInfo(ctypes.sizeof(_AnimInfo), 0)
        _spi(user32.SystemParametersInfoW(0x48, i.cbSize, ctypes.byref(i), 0))
        return int(i.iMinAnimate)
    def write(val):
        i = _AnimInfo(ctypes.sizeof(_AnimInfo), int(val))
        _spi(user32.SystemParametersInfoW(0x49, i.cbSize, ctypes.byref(i), SPIF))
    return Tweak("anim_minmax", "Animation réduire/agrandir les fenêtres", read, write, 0)

def _reg(id, label, path, name):
    def read():
        try:
            with winreg.OpenKey(HKCU, path, 0, winreg.KEY_READ) as k:
                v, t = winreg.QueryValueEx(k, name)
                return [v, t]
        except FileNotFoundError:
            return None
    def write(val):
        if val is None:  # la valeur n'existait pas à l'origine : on la supprime
            try:
                with winreg.OpenKey(HKCU, path, 0, winreg.KEY_SET_VALUE) as k:
                    winreg.DeleteValue(k, name)
            except FileNotFoundError:
                pass
        else:
            with winreg.CreateKeyEx(HKCU, path, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, name, 0, val[1], val[0])
    return Tweak(id, label, read, write, [0, winreg.REG_DWORD])

ADV = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
TWEAKS = [
    _anim(),
    _spi_bool("anim_client", "Animations des contrôles et éléments", 0x1042, 0x1043),
    _spi_bool("anim_menu", "Animation des menus", 0x1002, 0x1003),
    _spi_bool("anim_combo", "Animation des listes déroulantes", 0x1004, 0x1005),
    _spi_bool("smooth_list", "Défilement animé des listes", 0x1006, 0x1007),
    _spi_bool("fade_select", "Fondu de la sélection", 0x1014, 0x1015),
    _spi_bool("anim_tooltip", "Animation des info-bulles", 0x1016, 0x1017),
    _spi_bool("shadow_cursor", "Ombre du curseur", 0x101A, 0x101B),
    _spi_bool("shadow_menu", "Ombres sous les menus", 0x1024, 0x1025),
    _reg("taskbar_anim", "Animations de la barre des tâches", ADV, "TaskbarAnimations"),
    _reg("icon_shadow", "Ombres des noms d'icônes du bureau", ADV, "ListviewShadow"),
    _reg("transparency", "Transparence de Windows",
         r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency"),
    _reg("aero_peek", "Aperçu du bureau (Peek)", r"Software\Microsoft\Windows\DWM", "EnableAeroPeek"),
]

# --- sauvegarde des valeurs d'origine ---
def load_backup():
    if not BACKUP.exists():
        return {}
    return json.loads(BACKUP.read_text(encoding="utf-8"))

def save_backup(store):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = BACKUP.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, indent=1), encoding="utf-8")
    os.replace(tmp, BACKUP)

def broadcast():
    user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                           wintypes.LPCWSTR, wintypes.UINT, wintypes.UINT, ctypes.c_void_p]
    user32.SendMessageTimeoutW(0xFFFF, 0x1A, 0, "ImmersiveColorSet", 0x2, 2000, None)

def apply_tweak(t, store):
    """Sauvegarde l'original (une seule fois) PUIS modifie. Retourne True si modifié."""
    cur = t.read()
    if t.id not in store:
        store[t.id] = cur
        save_backup(store)  # écrit sur disque avant toute modification
    if cur == t.target:
        return False
    t.write(t.target)
    return True

def restore_all(log_cb):
    """Restaure uniquement ce qui figure dans la sauvegarde. Retourne (restaurés, échecs)."""
    store = load_backup()
    ok = fail = 0
    for t in TWEAKS:
        if t.id not in store:
            continue
        try:
            t.write(store[t.id])
            del store[t.id]
            save_backup(store)
            ok += 1
            log_cb("ok", f"Restauré : {t.label}")
        except Exception as e:
            fail += 1
            log.exception("Restauration échouée : %s", t.id)
            log_cb("err", f"Échec restauration « {t.label} » : {e}")
    broadcast()
    if not store and BACKUP.exists():
        BACKUP.unlink()
    return ok, fail
