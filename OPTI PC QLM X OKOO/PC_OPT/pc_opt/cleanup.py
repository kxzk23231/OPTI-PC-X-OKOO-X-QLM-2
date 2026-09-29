"""Nettoyage prudent du dossier TEMP de l'utilisateur uniquement (fichiers > 24 h)."""
import logging, os, time
from pathlib import Path

log = logging.getLogger("pc_opt.cleanup")

def _reparse(p):
    try:
        return bool(os.lstat(p).st_file_attributes & 0x400)  # lien / jonction : jamais suivi
    except OSError:
        return True

def clean_user_temp(min_age_h=24):
    root = Path(os.environ.get("TEMP", "")).resolve()
    home = Path.home().resolve()
    if not str(root).lower().startswith(str(home).lower() + os.sep) or root == home:
        raise RuntimeError(f"Dossier TEMP inattendu, nettoyage annulé : {root}")
    cutoff = time.time() - min_age_h * 3600
    files = size = 0
    dirs = []
    for cur, dnames, fnames in os.walk(root, topdown=True):
        dnames[:] = [d for d in dnames if not d.startswith("_MEI") and not _reparse(os.path.join(cur, d))]
        dirs += [os.path.join(cur, d) for d in dnames]
        for f in fnames:
            p = os.path.join(cur, f)
            try:
                if _reparse(p) or os.path.getmtime(p) > cutoff:
                    continue
                s = os.path.getsize(p)
                os.remove(p)
                files += 1
                size += s
            except OSError:
                pass  # fichier utilisé : ignoré
    for d in reversed(dirs):
        try:
            os.rmdir(d)  # ne supprime que les dossiers vides
        except OSError:
            pass
    log.info("Nettoyage TEMP : %d fichiers, %d octets", files, size)
    return files, size
