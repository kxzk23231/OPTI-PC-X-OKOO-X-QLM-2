import ctypes, sys
from pc_opt.common import setup_logging
from pc_opt.gui import App

def main():
    log = setup_logging()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    try:
        App().mainloop()
    except Exception:
        log.exception("Erreur fatale")
        raise

if __name__ == "__main__":
    sys.exit(main())
