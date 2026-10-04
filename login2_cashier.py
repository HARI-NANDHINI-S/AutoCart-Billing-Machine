import tkinter as tk
import os, subprocess, threading, time, random

# ─── CONFIG ───────────────────────────────────────────────────────────────────
PROJECT_PATH = r"C:\Users\ADMIN\Desktop\Module 1"
DOSBOX_PATH  = r"C:\Program Files (x86)\DOSBox-0.74-3\DOSBox.exe"
EMU_ASM_DIR  = PROJECT_PATH
RESULT_FILE  = os.path.join(EMU_ASM_DIR, "RESULT.TXT")
ASM_FILE     = os.path.join(EMU_ASM_DIR, "VALIDATE.ASM")

# ─── PALETTE ──────────────────────────────────────────────────────────────────
BG_DEEP    = "#02070f"
BG_PANEL   = "#060d1a"
BG_CARD    = "#0a1628"
BG_CARD2   = "#0d1f3c"
ACCENT_C   = "#00d4ff"
ACCENT_G   = "#00ff88"
ACCENT_Y   = "#ffd700"
ACCENT_R   = "#ff4444"
ACCENT_P   = "#a855f7"
TEXT_PRI   = "#e8f4ff"
TEXT_SEC   = "#7eb8d4"
TEXT_MUT   = "#3a5a7a"

FONT_HERO  = ("Consolas", 22, "bold")
FONT_MED   = ("Consolas", 16, "bold")
FONT_BODY  = ("Consolas", 12)
FONT_SMALL = ("Consolas", 10)

# ─── PARTICLE SYSTEM ──────────────────────────────────────────────────────────
class Particle:
    def __init__(self, canvas_w, canvas_h):
        self._w, self._h = canvas_w, canvas_h
        self.reset()

    def reset(self):
        self.x     = random.uniform(0, self._w)
        self.y     = random.uniform(0, self._h)
        self.vx    = random.uniform(-0.4, 0.4)
        self.vy    = random.uniform(-0.6, -0.1)
        self.life  = random.uniform(0.4, 1.0)
        self.decay = random.uniform(0.003, 0.008)
        self.size  = random.uniform(1, 2.5)
        self.color = random.choice([ACCENT_C, ACCENT_G, "#0088cc", "#00aaff", "#44ffbb"])

    def update(self):
        self.x    += self.vx
        self.y    += self.vy
        self.life -= self.decay
        if self.life <= 0 or self.y < 0:
            self.reset()
            self.y = self._h + 2

class GlowCanvas(tk.Canvas):
    def __init__(self, parent, w=1000, h=780, **kw):
        super().__init__(parent, bg=BG_DEEP, highlightthickness=0,
                         width=w, height=h, **kw)
        self._cw, self._ch = w, h
        self.running = True
        self.particles = [Particle(w, h) for _ in range(70)]
        for p in self.particles:
            p.y = random.uniform(0, h)
        self.after(50, self._draw)

    def _draw(self):
        if not self.running:
            return
        try:
            self.delete("particle")
            for p in self.particles:
                r = max(1, int(p.size))
                self.create_oval(p.x-r, p.y-r, p.x+r, p.y+r,
                                 fill=p.color, outline="", tags="particle")
                p.update()
            self.after(30, self._draw)
        except tk.TclError:
            pass

    def stop(self):
        self.running = False

# ─── NEON BUTTON ──────────────────────────────────────────────────────────────
def neon_btn(parent, text, color, command, width=28, pady_val=12, font=FONT_MED):
    bf = tk.Frame(parent, bg=color, padx=1, pady=1)
    inner = tk.Frame(bf, bg=BG_CARD)
    inner.pack(fill="both", expand=True)
    btn = tk.Button(inner, text=text, font=font, bg=BG_CARD, fg=color,
                    activebackground=color, activeforeground=BG_DEEP,
                    width=width, pady=pady_val, relief="flat", bd=0,
                    cursor="hand2", command=command)
    btn.pack(fill="both", expand=True)
    btn.bind("<Enter>", lambda e: (btn.config(bg=color, fg=BG_DEEP),
                                   bf.config(bg=color)))
    btn.bind("<Leave>", lambda e: btn.config(bg=BG_CARD, fg=color))
    return bf

# ─── EMU8086 / DOSBOX INTEGRATION ─────────────────────────────────────────────
def write_validate_asm(username, password):
    uname_bytes = username.encode('ascii', 'ignore')[:10].ljust(10, b'\0')
    pword_bytes = password.encode('ascii', 'ignore')[:10].ljust(10, b'\0')
    uname_hex = ''.join(f'{b:02X}h,' for b in uname_bytes)[:-1]
    pword_hex = ''.join(f'{b:02X}h,' for b in pword_bytes)[:-1]

    asm = (
        "; VALIDATE.ASM  -  Cashier Login Validator\n"
        "; Assemble:  NASM VALIDATE.ASM -f bin -o VALIDATE.COM\n"
        "ORG 100h\n"
        "\n"
        "section .text\n"
        "start:\n"
        "    ; Load username\n"
        "    MOV  SI, uname\n"
        "    MOV  DI, input_uname\n"
        "    MOV  CX, 10\n"
        "uname_loop:\n"
        "    LODSB\n"
        "    CMP  AL, [DI]\n"
        "    JNE  fail\n"
        "    INC  DI\n"
        "    LOOP uname_loop\n"
        "\n"
        "    ; Load password\n"
        "    MOV  SI, pword\n"
        "    MOV  DI, input_pword\n"
        "    MOV  CX, 10\n"
        "pword_loop:\n"
        "    LODSB\n"
        "    CMP  AL, [DI]\n"
        "    JNE  fail\n"
        "    INC  DI\n"
        "    LOOP pword_loop\n"
        "\n"
        "    ; Success: write '1' to RESULT.TXT\n"
        "    MOV  AH, 3Ch\n"
        "    MOV  CX, 0\n"
        "    MOV  DX, fname\n"
        "    INT  21h\n"
        "    JC   done\n"
        "    MOV  [handle], AX\n"
        "\n"
        "    MOV  AH, 40h\n"
        "    MOV  BX, [handle]\n"
        "    MOV  CX, 1\n"
        "    MOV  DX, success\n"
        "    INT  21h\n"
        "\n"
        "    MOV  AH, 3Eh\n"
        "    MOV  BX, [handle]\n"
        "    INT  21h\n"
        "    JMP  done\n"
        "\n"
        "fail:\n"
        "    ; Failure: write '0' to RESULT.TXT\n"
        "    MOV  AH, 3Ch\n"
        "    MOV  CX, 0\n"
        "    MOV  DX, fname\n"
        "    INT  21h\n"
        "    JC   done\n"
        "    MOV  [handle], AX\n"
        "\n"
        "    MOV  AH, 40h\n"
        "    MOV  BX, [handle]\n"
        "    MOV  CX, 1\n"
        "    MOV  DX, failure\n"
        "    INT  21h\n"
        "\n"
        "    MOV  AH, 3Eh\n"
        "    MOV  BX, [handle]\n"
        "    INT  21h\n"
        "\n"
        "done:\n"
        "    MOV  AH, 4Ch\n"
        "    XOR  AL, AL\n"
        "    INT  21h\n"
        "\n"
        "section .data\n"
        "fname       DB 'RESULT.TXT', 0\n"
        "handle      DW 0\n"
        "success     DB '1'\n"
        "failure     DB '0'\n"
        f"uname       DB {uname_hex}\n"
        f"pword       DB {pword_hex}\n"
        "input_uname DB 0,0,0,0,0,0,0,0,0,0\n"
        "input_pword DB 0,0,0,0,0,0,0,0,0,0\n"
    )
    os.makedirs(EMU_ASM_DIR, exist_ok=True)
    with open(ASM_FILE, "w") as f:
        f.write(asm)

def build_dosbox_conf(extra_cmds):
    conf_path = os.path.join(EMU_ASM_DIR, "bridge.conf")
    lines = [
        "[sdl]",
        "fullscreen=false",
        "autolock=false",
        "[dosbox]",
        "memsize=16",
        "[cpu]",
        "core=normal",
        "[autoexec]",
        f'MOUNT C "{PROJECT_PATH}"',
        "C:",
    ] + extra_cmds + ["EXIT"]
    with open(conf_path, "w") as f:
        f.write("\n".join(lines))
    return conf_path

def run_dosbox_sync(extra_cmds, timeout=30):
    if not os.path.isfile(DOSBOX_PATH):
        return False, f"DOSBox not found at: {DOSBOX_PATH}"
    conf = build_dosbox_conf(extra_cmds)
    try:
        proc = subprocess.Popen(
            [DOSBOX_PATH, "-conf", conf, "-noconsole"],
            cwd=PROJECT_PATH
        )
        proc.wait(timeout=timeout)
        return True, "OK"
    except subprocess.TimeoutExpired:
        proc.kill()
        return False, "DOSBox timed out"
    except Exception as e:
        return False, str(e)

def validate_user(username, password):
    write_validate_asm(username, password)
    if os.path.exists(RESULT_FILE):
        os.remove(RESULT_FILE)

    ok, msg = run_dosbox_sync([
        "NASM VALIDATE.ASM -f bin -o VALIDATE.COM",
        "VALIDATE",
    ], timeout=30)

    if not ok:
        return False, msg

    if not os.path.exists(RESULT_FILE):
        return False, "RESULT.TXT not created — ensure NASM.EXE is in C:\\"

    with open(RESULT_FILE, "r") as f:
        raw = f.read().strip()
    if raw == "1":
        return True, ""
    elif raw == "0":
        return False, "Invalid username or password"
    else:
        return False, f"Bad RESULT.TXT content: '{raw}'"

# ─── MAIN APP ─────────────────────────────────────────────────────────────────
class Login2Cashier(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CASHIER LOGIN  ·  HyperStore International")
        self.geometry("1000x780")
        self._center_window(1000, 780)
        self.resizable(False, False)
        self.configure(bg=BG_DEEP)

        self.bg_canvas = GlowCanvas(self, w=1000, h=780)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.stage = tk.Frame(self, bg=BG_DEEP)
        self.stage.place(x=0, y=0, relwidth=1, relheight=1)

        self._draw_header()
        self.content = tk.Frame(self.stage, bg=BG_DEEP)
        self.content.place(x=0, y=110, relwidth=1, height=610)
        self._draw_footer()
        self.show_login()

    def _center_window(self, width, height):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    # ── LAYOUT ────────────────────────────────────────────────────────────────
    def _draw_header(self):
        hdr = tk.Frame(self.stage, bg=BG_PANEL, height=100)
        hdr.place(x=0, y=0, relwidth=1)
        hdr.pack_propagate(False)
        logo_f = tk.Frame(hdr, bg=BG_PANEL)
        logo_f.place(x=24, y=28)
        tk.Label(logo_f, text="◈ CASHIER", font=("Consolas", 26, "bold"),
                 bg=BG_PANEL, fg=ACCENT_Y).pack(side="left")
        tk.Label(logo_f, text="LOGIN", font=("Consolas", 26, "bold"),
                 bg=BG_PANEL, fg=ACCENT_G).pack(side="left")
        tk.Label(logo_f, text=" v2.0", font=("Consolas", 11),
                 bg=BG_PANEL, fg=TEXT_MUT).pack(side="left", padx=4)
        tk.Frame(self.stage, bg=ACCENT_Y, height=2).place(x=0, y=100, relwidth=1)

    def _draw_footer(self):
        ft = tk.Frame(self.stage, bg=BG_PANEL, height=40)
        ft.place(x=0, y=740, relwidth=1)

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _section_title(self, text, color=ACCENT_Y):
        tk.Label(self.content, text=text, font=("Consolas", 13),
                 bg=BG_DEEP, fg=color).pack(pady=(8, 2))
        tk.Frame(self.content, bg=color, height=1).pack(
            fill="x", padx=80, pady=(0, 10))

    # ── LOGIN ──────────────────────────────────────────────────────────────────
    def show_login(self):
        self.clear_content()
        self._section_title("CASHIER AUTHENTICATION", ACCENT_Y)

        tk.Label(self.content, text="USERNAME", font=FONT_SMALL,
                 bg=BG_DEEP, fg=TEXT_SEC).pack(pady=(20, 2))
        self._uname_var = tk.StringVar()
        uname_e = tk.Entry(self.content, textvariable=self._uname_var,
                           font=("Consolas", 16, "bold"), bg=BG_CARD, fg=ACCENT_Y,
                           insertbackground=ACCENT_Y, relief="flat", bd=4,
                           width=24, justify="center")
        uname_e.pack(pady=(0, 8), ipady=6)
        uname_e.focus_set()

        tk.Label(self.content, text="PASSWORD", font=FONT_SMALL,
                 bg=BG_DEEP, fg=TEXT_SEC).pack(pady=(8, 2))
        self._pword_var = tk.StringVar()
        pword_e = tk.Entry(self.content, textvariable=self._pword_var,
                           font=("Consolas", 16, "bold"), bg=BG_CARD, fg=ACCENT_Y,
                           insertbackground=ACCENT_Y, relief="flat", bd=4,
                           width=24, justify="center", show="*")
        pword_e.pack(pady=(0, 8), ipady=6)

        self._login_err = tk.Label(self.content, text="",
                                   font=("Consolas", 10), bg=BG_DEEP, fg=ACCENT_R)
        self._login_err.pack(pady=(4, 0))

        tk.Frame(self.content, bg=TEXT_MUT, height=1
                 ).pack(fill="x", padx=100, pady=12)
        neon_btn(self.content, "🔐  LOGIN", ACCENT_Y,
                 self._attempt_login, width=24, pady_val=12).pack()

        tk.Label(self.content, text="Default: admin / admin123",
                 font=("Consolas", 9), bg=BG_DEEP, fg=TEXT_MUT).pack(pady=(6, 0))

    def _attempt_login(self):
        uname = self._uname_var.get().strip()
        pword = self._pword_var.get().strip()
        if not uname or not pword:
            self._login_err.config(text="⚠  Please enter both username and password")
            return
        self._login_err.config(text="Validating via EMU8086...")
        self.update()
        threading.Thread(target=self._validate_thread,
                         args=(uname, pword), daemon=True).start()

    def _validate_thread(self, uname, pword):
        ok, msg = validate_user(uname, pword)
        self.after(0, lambda: self._login_done(ok, msg))

    def _login_done(self, ok, msg):
        if ok:
            self._login_err.config(text="✔  Access granted", fg=ACCENT_G)
            self.after(500, self.start_session)
        else:
            self._login_err.config(text=f"✗  {msg}", fg=ACCENT_R)

    def start_session(self):
        self.destroy()
        from cashier_screen import CashierScreen
        CashierScreen().mainloop()

if __name__ == "__main__":
    Login2Cashier().mainloop()