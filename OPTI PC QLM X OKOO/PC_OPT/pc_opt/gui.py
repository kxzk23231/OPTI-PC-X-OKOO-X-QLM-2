import queue, threading, tkinter as tk
from tkinter import ttk, messagebox
from . import engine
from .common import is_admin, LOG_PATH

BG, CARD, FG, MUTED = "#0f141b", "#18202b", "#e8edf3", "#8fa1b5"
COL = {"ok": "#3ddc84", "err": "#ff5c5c", "info": "#8fb8ff"}

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PC OPT")
        self.geometry("780x620")
        self.minsize(700, 540)
        self.configure(bg=BG)
        self.q = queue.Queue()
        self.busy = False
        self.admin = is_admin()

        tk.Label(self, text="PC OPT", font=("Segoe UI", 24, "bold"), bg=BG, fg=FG).pack(anchor="w", padx=24, pady=(18, 0))
        tk.Label(self, text="Optimisation douce et réversible pour PC peu puissants",
                 font=("Segoe UI", 10), bg=BG, fg=MUTED).pack(anchor="w", padx=24)
        if not self.admin:
            tk.Label(self, text="⚠ Lancez PC OPT en administrateur (clic droit → Exécuter en tant qu'administrateur).",
                     font=("Segoe UI", 10, "bold"), bg="#4a2a12", fg="#ffd9a8", padx=10, pady=6
                     ).pack(fill="x", padx=24, pady=(10, 0))

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=24, pady=16)
        self.btns = [
            self._btn(bar, "🚀 Optimiser mon PC", self.on_optimize, "#2f80ed"),
            self._btn(bar, "↩ Restaurer les réglages", self.on_restore, "#3a4657"),
            self._btn(bar, "🔄 Créer un point de restauration", self.on_point, "#3a4657"),
        ]
        for b in self.btns:
            b.pack(side="left", padx=(0, 10), ipady=8, ipadx=8)

        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("pc.Horizontal.TProgressbar", troughcolor=CARD, background="#2f80ed", bordercolor=CARD,
                     lightcolor="#2f80ed", darkcolor="#2f80ed")
        self.pb = ttk.Progressbar(self, style="pc.Horizontal.TProgressbar", maximum=100)
        self.pb.pack(fill="x", padx=24)

        tk.Label(self, text="Journal", font=("Segoe UI", 10, "bold"), bg=BG, fg=MUTED).pack(anchor="w", padx=24, pady=(14, 4))
        self.txt = tk.Text(self, bg=CARD, fg=FG, relief="flat", font=("Consolas", 10), wrap="word",
                           state="disabled", padx=10, pady=8)
        self.txt.pack(fill="both", expand=True, padx=24, pady=(0, 6))
        for k, c in COL.items():
            self.txt.tag_config(k, foreground=c)
        tk.Label(self, text=f"Journal détaillé : {LOG_PATH}", font=("Segoe UI", 8), bg=BG, fg=MUTED).pack(anchor="w", padx=24, pady=(0, 10))
        self.say("info", "Prêt. Un point de restauration est créé avant toute modification.")
        self.after(100, self.poll)

    def _btn(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, command=cmd, bg=color, fg="white", activebackground="#5a9bff",
                         activeforeground="white", relief="flat", bd=0, font=("Segoe UI", 10, "bold"), cursor="hand2")

    def say(self, level, text):
        self.txt.configure(state="normal")
        self.txt.insert("end", {"ok": "✔ ", "err": "✖ ", "info": "• "}[level] + text + "\n", level)
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def run(self, fn, done_title):
        if self.busy:
            return
        self.busy = True
        for b in self.btns:
            b.configure(state="disabled")
        self.pb["value"] = 0
        def work():
            try:
                ok, msg = fn(lambda l, t: self.q.put(("log", l, t)), lambda v: self.q.put(("pg", v)))
            except Exception as e:
                ok, msg = False, f"Erreur inattendue : {e}"
                self.q.put(("log", "err", msg))
            self.q.put(("done", done_title, ok, msg))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                m = self.q.get_nowait()
                if m[0] == "log":
                    self.say(m[1], m[2])
                elif m[0] == "pg":
                    self.pb["value"] = m[1]
                else:
                    self.busy = False
                    for b in self.btns:
                        b.configure(state="normal")
                    (messagebox.showinfo if m[2] else messagebox.showerror)(m[1], m[3])
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def on_optimize(self):
        if messagebox.askyesno("Confirmation",
                "PC OPT va :\n\n1. Créer un point de restauration\n2. Désactiver animations, transparence et ombres\n"
                "3. Supprimer les fichiers temporaires (> 24 h) de votre profil\n\nAucun antivirus, pare-feu ni service "
                "n'est modifié. Les réglages sont réversibles ; les fichiers temporaires supprimés ne le sont pas.\n\nContinuer ?"):
            self.run(engine.optimize, "Optimisation")

    def on_restore(self):
        if messagebox.askyesno("Confirmation", "Restaurer les réglages modifiés par PC OPT ?"):
            self.run(engine.restore, "Restauration")

    def on_point(self):
        self.run(engine.make_restore_point, "Point de restauration")
