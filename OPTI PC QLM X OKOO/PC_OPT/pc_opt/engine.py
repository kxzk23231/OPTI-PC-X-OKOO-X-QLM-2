import logging
from .common import is_admin
from .restore_point import create_restore_point, RestorePointError
from . import tweaks, cleanup

log = logging.getLogger("pc_opt.engine")

def _fmt(n):
    return f"{n/1048576:.1f} Mo"

def make_restore_point(say, progress):
    if not is_admin():
        return False, "Droits administrateur requis. Relancez PC OPT en administrateur."
    say("info", "Création du point de restauration…")
    progress(30)
    try:
        create_restore_point()
    except (RestorePointError, Exception) as e:
        log.exception("Point de restauration")
        say("err", f"Point de restauration impossible : {e}")
        return False, f"Le point de restauration n'a pas pu être créé.\n\n{e}"
    progress(100)
    say("ok", "Point de restauration « PC OPT - Avant optimisation » créé et vérifié.")
    return True, "Point de restauration créé avec succès."

def optimize(say, progress):
    say("info", "Vérification des droits administrateur…")
    if not is_admin():
        say("err", "Application non lancée en administrateur. Aucune modification effectuée.")
        return False, "Droits administrateur requis. Aucune modification n'a été effectuée."
    say("info", "Création du point de restauration (avant toute modification)…")
    progress(5)
    try:
        create_restore_point()
    except Exception as e:
        log.exception("Point de restauration")
        say("err", f"Point de restauration impossible : {e}")
        say("err", "AUCUNE modification n'a été effectuée.")
        return False, f"Le point de restauration n'a pas pu être créé.\nAucune modification n'a été effectuée.\n\n{e}"
    say("ok", "Point de restauration « PC OPT - Avant optimisation » créé et vérifié.")
    progress(25)

    store = tweaks.load_backup()
    changed, same, failed = [], [], []
    total = len(tweaks.TWEAKS)
    for i, t in enumerate(tweaks.TWEAKS, 1):
        try:
            if tweaks.apply_tweak(t, store):
                changed.append(t.label)
                say("ok", f"Désactivé : {t.label} (valeur d'origine sauvegardée)")
            else:
                same.append(t.label)
                say("info", f"Déjà optimisé : {t.label}")
        except Exception as e:
            log.exception("Réglage %s", t.id)
            failed.append(t.label)
            say("err", f"Échec « {t.label} » : {e}")
        progress(25 + int(50 * i / total))
    tweaks.broadcast()

    say("info", "Nettoyage des fichiers temporaires de l'utilisateur…")
    n = size = 0
    try:
        n, size = cleanup.clean_user_temp()
        say("ok", f"{n} fichier(s) temporaire(s) supprimé(s) ({_fmt(size)})")
    except Exception as e:
        log.exception("Nettoyage")
        say("err", f"Nettoyage impossible : {e}")
    progress(100)

    msg = (f"Optimisation terminée.\n\n• {len(changed)} réglage(s) visuel(s) modifié(s)\n"
           f"• {len(same)} déjà optimisé(s)\n• {n} fichier(s) temporaire(s) supprimé(s) ({_fmt(size)})\n")
    if failed:
        msg += f"• {len(failed)} échec(s) : voir le journal\n"
    msg += ("\nLes réglages peuvent être annulés avec « Restaurer les réglages ».\n"
            "Le nettoyage des fichiers temporaires n'est pas restaurable.\n"
            "Déconnectez/reconnectez votre session pour appliquer tous les effets.")
    return not failed, msg

def restore(say, progress):
    progress(10)
    store = tweaks.load_backup()
    if not store:
        say("info", "Aucun réglage sauvegardé : rien à restaurer.")
        progress(100)
        return True, "Aucune sauvegarde de réglages trouvée : rien à restaurer."
    ok, fail = tweaks.restore_all(say)
    progress(100)
    msg = f"{ok} réglage(s) restauré(s)."
    if fail:
        msg += f"\n{fail} échec(s) : voir le journal."
    msg += "\nLes fichiers temporaires supprimés ne peuvent pas être restaurés."
    return fail == 0, msg
