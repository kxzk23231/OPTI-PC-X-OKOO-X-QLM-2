"""Création du point de restauration (API officielle : Checkpoint-Computer)."""
import json, logging, os, subprocess, winreg

log = logging.getLogger("pc_opt.restore")
NAME = "PC OPT - Avant optimisation"
PS = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                  r"System32\WindowsPowerShell\v1.0\powershell.exe")
# Valeur documentée par Microsoft (limite d'un point / 24 h). Sauvegardée puis remise à l'identique.
FREQ_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore"
FREQ_VAL = "SystemRestorePointCreationFrequency"

class RestorePointError(Exception):
    pass

def _ps(script, timeout=300):
    full = "[Console]::OutputEncoding=[Text.Encoding]::UTF8; $ErrorActionPreference='Stop'; " + script
    try:
        p = subprocess.run([PS, "-NoProfile", "-NonInteractive", "-Command", full],
                           capture_output=True, timeout=timeout, creationflags=0x08000000)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RestorePointError(f"PowerShell indisponible ou trop lent : {e}")
    out = p.stdout.decode("utf-8", "replace").strip()
    err = p.stderr.decode("utf-8", "replace").strip()
    if p.returncode != 0:
        raise RestorePointError(err or out or f"PowerShell a renvoyé le code {p.returncode}")
    return out

def _list_points():
    out = _ps("ConvertTo-Json -Compress -InputObject @(Get-ComputerRestorePoint | "
              "Select-Object SequenceNumber,Description)")
    return json.loads(out) if out else []

def _get_freq():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, FREQ_KEY, 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            return winreg.QueryValueEx(k, FREQ_VAL)[0]
    except FileNotFoundError:
        return None

def _set_freq(value):
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, FREQ_KEY, 0,
                        winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
        if value is None:
            try:
                winreg.DeleteValue(k, FREQ_VAL)
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(k, FREQ_VAL, 0, winreg.REG_DWORD, value)

def create_restore_point(name=NAME):
    """Crée et VÉRIFIE le point. Lève RestorePointError en cas d'échec."""
    drive = os.environ.get("SystemDrive", "C:") + "\\"
    log.info("Activation de la protection du système sur %s", drive)
    _ps(f"Enable-ComputerRestore -Drive '{drive}'")
    before = max((p["SequenceNumber"] for p in _list_points()), default=0)
    old = _get_freq()
    try:
        _set_freq(0)  # sinon Windows ignore la création si un point a < 24 h
        _ps(f"Checkpoint-Computer -Description '{name}' -RestorePointType MODIFY_SETTINGS")
    finally:
        try:
            _set_freq(old)
        except OSError:
            log.exception("Impossible de remettre la fréquence d'origine")
    found = [p for p in _list_points() if p["SequenceNumber"] > before and p["Description"] == name]
    if not found:
        raise RestorePointError("Windows n'a pas confirmé la création du point de restauration.")
    log.info("Point de restauration créé (n° %s)", found[-1]["SequenceNumber"])
    return found[-1]["SequenceNumber"]
