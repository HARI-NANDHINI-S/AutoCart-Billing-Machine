import tkinter as tk
from tkinter import ttk
import os, time, math, random, threading, subprocess, tempfile

try:
    import qrcode
    from PIL import ImageTk, Image
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

# ─── CONFIG ───────────────────────────────────────────────────────────────────
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
DOSBOX_PATH  = r"C:\Program Files (x86)\DOSBox-0.74-3\DOSBox.exe"
EMU_ASM_DIR  = PROJECT_PATH
RESULT_FILE  = os.path.join(EMU_ASM_DIR, "RESULT.TXT")
ASM_FILE     = os.path.join(EMU_ASM_DIR, "CHANGE.ASM")

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
def write_asm(tendered_paise, due_paise):
    """
    Write CHANGE.ASM — a NASM COM program (ORG 100h) that:
      MOV AX, <tendered>
      MOV BX, <due>
      SUB AX, BX          ; change in paise
    Then converts AX to decimal ASCII and writes it to RESULT.TXT via INT 21h.
    """
    asm = (
        "; CHANGE.ASM  -  NeonPay 8086 Change Calculator\n"
        "; Assemble:  NASM CHANGE.ASM -f bin -o CHANGE.COM\n"
        "ORG 100h\n"
        "\n"
        "section .text\n"
        "start:\n"
        f"    MOV  AX, {tendered_paise}    ; AX = tendered paise\n"
        f"    MOV  BX, {due_paise}         ; BX = amount due paise\n"
        "    SUB  AX, BX                   ; AX = change paise\n"
        "\n"
        "    ; Convert AX to decimal string\n"
        "    MOV  CX, 0\n"
        "    MOV  BX, 10\n"
        "div_loop:\n"
        "    XOR  DX, DX\n"
        "    DIV  BX\n"
        "    PUSH DX\n"
        "    INC  CX\n"
        "    CMP  AX, 0\n"
        "    JNE  div_loop\n"
        "\n"
        "    MOV  DI, buf\n"
        "pop_loop:\n"
        "    POP  AX\n"
        "    ADD  AL, '0'\n"
        "    MOV  [DI], AL\n"
        "    INC  DI\n"
        "    LOOP pop_loop\n"
        "    MOV  BYTE [DI], 0Dh\n"
        "    INC  DI\n"
        "    MOV  BYTE [DI], 0Ah\n"
        "    INC  DI\n"
        "\n"
        "    ; Create RESULT.TXT\n"
        "    MOV  AH, 3Ch\n"
        "    MOV  CX, 0\n"
        "    MOV  DX, fname\n"
        "    INT  21h\n"
        "    JC   done\n"
        "    MOV  [handle], AX\n"
        "\n"
        "    ; Write to file\n"
        "    MOV  AH, 40h\n"
        "    MOV  BX, [handle]\n"
        "    MOV  CX, DI\n"
        "    SUB  CX, buf\n"
        "    MOV  DX, buf\n"
        "    INT  21h\n"
        "\n"
        "    ; Close file\n"
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
        "fname   DB 'RESULT.TXT', 0\n"
        "handle  DW 0\n"
        "buf     TIMES 20 DB 0\n"
    )
    os.makedirs(EMU_ASM_DIR, exist_ok=True)
    with open(ASM_FILE, "w") as f:
        f.write(asm)


def build_dosbox_conf(extra_cmds):
    conf_path = os.path.join(EMU_ASM_DIR, "neonpay.conf")
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


def assemble_and_run_change(tendered_paise, due_paise):
    """
    1. Write CHANGE.ASM
    2. DOSBox: NASM assemble → run CHANGE.COM → writes RESULT.TXT
    3. Read RESULT.TXT → return (change_paise, asm_trace, error)
    """
    write_asm(tendered_paise, due_paise)
    if os.path.exists(RESULT_FILE):
        os.remove(RESULT_FILE)

    ok, msg = run_dosbox_sync([
        "NASM CHANGE.ASM -f bin -o CHANGE.COM",
        "CHANGE",
    ], timeout=30)

    if not ok:
        return None, "", msg

    if not os.path.exists(RESULT_FILE):
        return None, "", "RESULT.TXT not created — ensure NASM.EXE is in C:\\"

    with open(RESULT_FILE, "r") as f:
        raw = f.read().strip()
    try:
        change_paise = int(raw)
    except ValueError:
        return None, "", f"Bad RESULT.TXT content: '{raw}'"

    trace = (
        f"  MOV AX, {tendered_paise:04X}h  ; tendered = {tendered_paise} paise\n"
        f"  MOV BX, {due_paise:04X}h  ; due     = {due_paise} paise\n"
        f"  SUB AX, BX\n"
        f"  ; AX = {change_paise} paise  CF={'0'}  ZF={'1' if change_paise==0 else '0'}\n"
        f"  ; RESULT.TXT written via INT 21h  ✔"
    )
    return change_paise, trace, ""


# ─── MAIN APP ─────────────────────────────────────────────────────────────────
class NeonPayKiosk(tk.Tk):
    def __init__(self, grand_paise):
        super().__init__()
        self.grand_paise = grand_paise
        self.current_pin = ""
        self._anim_id    = None

        self.title("NEON-PAY v4.0  ·  HyperStore International")
        self.geometry("1000x780")
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
        self.show_main_menu()

    # ── LAYOUT ────────────────────────────────────────────────────────────────
    def _draw_header(self):
        hdr = tk.Frame(self.stage, bg=BG_PANEL, height=100)
        hdr.place(x=0, y=0, relwidth=1)
        hdr.pack_propagate(False)
        logo_f = tk.Frame(hdr, bg=BG_PANEL)
        logo_f.place(x=24, y=28)
        tk.Label(logo_f, text="◈ PAYMENT", font=("Consolas", 26, "bold"),
                 bg=BG_PANEL, fg=ACCENT_C).pack(side="left")
        #tk.Label(logo_f, text="PAY\", font=("Consolas", 26, "bold"),
               #  bg=BG_PANEL, fg=ACCENT_G).pack(side="left")
        tk.Label(logo_f, text=" v4.0", font=("Consolas", 11),
                 bg=BG_PANEL, fg=TEXT_MUT).pack(side="left", padx=4)
        # REMOVED: subtitle "HyperStore International · Secure Checkout"
        amt_f = tk.Frame(hdr, bg=BG_CARD2, padx=18, pady=8)
        amt_f.place(x=690, y=14, width=290)
        tk.Label(amt_f, text="AMOUNT DUE", font=FONT_SMALL,
                 bg=BG_CARD2, fg=TEXT_SEC).pack(anchor="e")
        tk.Label(amt_f, text=f"₹ {self.grand_paise/100:,.2f}",
                 font=("Consolas", 28, "bold"), bg=BG_CARD2,
                 fg=ACCENT_Y).pack(anchor="e")
        tk.Frame(self.stage, bg=ACCENT_C, height=2).place(x=0, y=100, relwidth=1)

    def _draw_footer(self):
        ft = tk.Frame(self.stage, bg=BG_PANEL, height=40)
        ft.place(x=0, y=740, relwidth=1)
        # REMOVED: "🔒  256-bit TLS  ·  PCI-DSS Compliant  ·  Secure Transaction"

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None

    def _add_back_btn(self):
        tk.Button(self.content, text="◀  BACK",
                  font=("Consolas", 10, "bold"), bg=BG_DEEP, fg=ACCENT_R,
                  activebackground=ACCENT_R, activeforeground=BG_DEEP,
                  relief="flat", bd=0, cursor="hand2",
                  command=self.show_main_menu).place(x=20, y=10)

    def _section_title(self, text, color=ACCENT_C):
        tk.Label(self.content, text=text, font=("Consolas", 13),
                 bg=BG_DEEP, fg=color).pack(pady=(8, 2))
        tk.Frame(self.content, bg=color, height=1).pack(
            fill="x", padx=80, pady=(0, 10))

    # ── MAIN MENU ─────────────────────────────────────────────────────────────
    def show_main_menu(self):
        self.clear_content()
        tk.Label(self.content, text="SELECT PAYMENT METHOD",
                 font=("Consolas", 13), bg=BG_DEEP, fg=TEXT_SEC
                 ).pack(pady=(28, 4))
        tk.Frame(self.content, bg=TEXT_MUT, height=1
                 ).pack(fill="x", padx=120, pady=(0, 20))
        for title, color, cmd in [
            ("⚡  UPI / QR CODE",       ACCENT_C, self.show_upi),
            ("💳  DEBIT / CREDIT CARD", ACCENT_P, self.show_card),
            ("💵  CASH PAYMENT",         ACCENT_Y, self.show_cash),
        ]:
            neon_btn(self.content, title, color, cmd,
                     width=32, pady_val=13).pack(pady=8)
        # REMOVED: "All transactions are encrypted end-to-end."

    # ── UPI ───────────────────────────────────────────────────────────────────
    def show_upi(self):
        self.clear_content()
        self._add_back_btn()
        self._section_title("UPI / QR PAYMENT", ACCENT_C)
        amount_rs = self.grand_paise / 100
        upi_str = (f"upi://pay?pa=hyperstore@ybl&pn=HyperStore"
                   f"&am={amount_rs:.2f}&cu=INR")
        if QR_AVAILABLE:
            try:
                qr = qrcode.make(upi_str).resize((220, 220), Image.LANCZOS)
                self._qr_img = ImageTk.PhotoImage(qr)
                qf = tk.Frame(self.content, bg="white", padx=10, pady=10)
                qf.pack(pady=8)
                tk.Label(qf, image=self._qr_img, bg="white").pack()
            except Exception as e:
                tk.Label(self.content, text=f"QR Error: {e}",
                         font=FONT_BODY, bg=BG_DEEP, fg=ACCENT_R).pack(pady=20)
        else:
            tk.Label(self.content, text="[ qrcode / Pillow not installed ]",
                     font=FONT_BODY, bg=BG_DEEP, fg=ACCENT_R).pack(pady=8)
            uf = tk.Frame(self.content, bg=BG_CARD2, padx=20, pady=10)
            uf.pack(pady=6)
            tk.Label(uf, text="UPI ID", font=FONT_SMALL,
                     bg=BG_CARD2, fg=TEXT_SEC).pack()
            tk.Label(uf, text="hyperstore@ybl",
                     font=("Consolas", 16, "bold"),
                     bg=BG_CARD2, fg=ACCENT_C).pack()
        tk.Label(self.content, text="SCAN WITH ANY UPI APP",
                 font=FONT_MED, bg=BG_DEEP, fg=ACCENT_C).pack(pady=(6, 2))
        tk.Label(self.content, text=f"₹ {amount_rs:,.2f}  ·  hyperstore@ybl",
                 font=FONT_BODY, bg=BG_DEEP, fg=TEXT_SEC).pack()
        tk.Frame(self.content, bg=TEXT_MUT, height=1
                 ).pack(fill="x", padx=100, pady=12)
        neon_btn(self.content, "✅  I HAVE PAID", ACCENT_G,
                 lambda: self.show_processing("UPI", 0, 0, 0),
                 width=28, pady_val=10).pack(pady=4)

    # ── CARD ──────────────────────────────────────────────────────────────────
    def show_card(self):
        self.clear_content()
        self._add_back_btn()
        self._section_title("CARD PAYMENT", ACCENT_P)
        # REMOVED: "TAP, INSERT, OR SWIPE YOUR CARD" label
        # REMOVED: "Visa · Mastercard · RuPay · Amex" label
        # REMOVED: horizontal separator
        # REMOVED: "Or click above to proceed to PIN entry." hint
        tk.Frame(self.content, height=60, bg=BG_DEEP).pack()  # spacer
        neon_btn(self.content, "CARD DETECTED  —  ENTER PIN  ▶", ACCENT_P,
                 self.show_card_pin, width=34, pady_val=13).pack(pady=4)

    # ── PIN PAD ───────────────────────────────────────────────────────────────
    def show_card_pin(self):
        self.clear_content()
        self._add_back_btn()
        self._section_title("ENTER PIN", ACCENT_P)
        self.current_pin = ""
        self._pin_var = tk.StringVar(value="")
        tk.Label(self.content, text="Enter your 4-digit card PIN",
                 font=FONT_BODY, bg=BG_DEEP, fg=TEXT_SEC).pack(pady=(0, 8))
        tk.Label(self.content, textvariable=self._pin_var,
                 font=("Consolas", 30, "bold"), bg=BG_CARD2,
                 fg=ACCENT_P, width=10, pady=10).pack(pady=4)
        self._pin_err = tk.Label(self.content, text="",
                                 font=("Consolas", 10), bg=BG_DEEP, fg=ACCENT_R)
        self._pin_err.pack()
        pad = tk.Frame(self.content, bg=BG_DEEP)
        pad.pack(pady=6)

        def press(v):
            if len(self.current_pin) < 4:
                self.current_pin += v
                self._pin_var.set("●" * len(self.current_pin))

        def bksp():
            self.current_pin = self.current_pin[:-1]
            self._pin_var.set("●" * len(self.current_pin))

        def confirm():
            if len(self.current_pin) != 4:
                self._pin_err.config(text="⚠  PIN must be exactly 4 digits")
                return
            self.show_processing("Card", 0, 0, 0)

        for row_keys in [["1","2","3"],["4","5","6"],["7","8","9"],["⌫","0","✔"]]:
            row = tk.Frame(pad, bg=BG_DEEP)
            row.pack(pady=3)
            for k in row_keys:
                if k == "✔":   c, cmd = ACCENT_G, confirm
                elif k == "⌫": c, cmd = ACCENT_R, bksp
                else:           c, cmd = ACCENT_P, lambda v=k: press(v)
                tk.Button(row, text=k, font=("Consolas", 16, "bold"),
                          bg=BG_CARD, fg=c, activebackground=c,
                          activeforeground=BG_DEEP, width=4, pady=8,
                          relief="flat", bd=0, cursor="hand2",
                          command=cmd).pack(side="left", padx=5)

    # ── CASH ──────────────────────────────────────────────────────────────────
    def show_cash(self):
        self.clear_content()
        self._add_back_btn()
        self._section_title("CASH PAYMENT", ACCENT_Y)
        amount_rs = self.grand_paise / 100

        inf = tk.Frame(self.content, bg=BG_CARD2, padx=30, pady=14)
        inf.pack(pady=(0, 8))
        tk.Label(inf, text="AMOUNT TO PAY", font=FONT_SMALL,
                 bg=BG_CARD2, fg=TEXT_SEC).pack()
        tk.Label(inf, text=f"₹ {amount_rs:,.2f}",
                 font=("Consolas", 32, "bold"), bg=BG_CARD2, fg=ACCENT_Y).pack()

        ef = tk.Frame(self.content, bg=BG_DEEP)
        ef.pack(pady=4)
        tk.Label(ef, text="CASH TENDERED  ₹",
                 font=("Consolas", 13, "bold"), bg=BG_DEEP,
                 fg=TEXT_SEC).pack(side="left")
        self._cash_var = tk.StringVar()
        ce = tk.Entry(ef, textvariable=self._cash_var,
                      font=("Consolas", 20, "bold"), bg=BG_CARD, fg=ACCENT_Y,
                      insertbackground=ACCENT_Y, relief="flat", bd=4,
                      width=10, justify="right")
        ce.pack(side="left", ipady=6, padx=(6, 0))
        ce.focus_set()

        # EMU badge
        eb = tk.Frame(self.content, bg=BG_DEEP)
        eb.pack(pady=(3, 0))
        tk.Label(eb, text="⚙  EMU8086 via DOSBox",
                 font=("Consolas", 9, "bold"), bg=BG_DEEP,
                 fg=ACCENT_P).pack(side="left")
        tk.Label(eb, text="  — NASM · SUB AX,BX · INT 21h",
                 font=("Consolas", 9), bg=BG_DEEP,
                 fg=TEXT_MUT).pack(side="left")

        # Change display
        self._cf = tk.Frame(self.content, bg=BG_CARD2, padx=24, pady=10)
        self._cf.pack(pady=6, padx=120, fill="x")
        self._balance_lbl = tk.Label(self._cf,
                                     text="Enter cash amount above",
                                     font=("Consolas", 11), bg=BG_CARD2,
                                     fg=TEXT_MUT)
        self._balance_lbl.pack()
        self._change_lbl = tk.Label(self._cf, text="",
                                    font=("Consolas", 22, "bold"),
                                    bg=BG_CARD2, fg=ACCENT_G)
        self._change_lbl.pack()
        self._asm_lbl = tk.Label(self._cf, text="",
                                 font=("Courier New", 9), bg=BG_CARD2,
                                 fg=TEXT_MUT, justify="left", anchor="w")
        self._asm_lbl.pack(fill="x", pady=(4, 0))

        # REMOVED: "Accepted: ₹10  ₹20  ₹50  ₹100  ₹200  ₹500"

        self._cash_err = tk.Label(self.content, text="",
                                  font=("Consolas", 10), bg=BG_DEEP,
                                  fg=ACCENT_R)
        self._cash_err.pack()

        self._cash_var.trace_add(
            "write", lambda *_: self._live_preview(amount_rs))

        tk.Frame(self.content, bg=TEXT_MUT, height=1
                 ).pack(fill="x", padx=100, pady=6)
        neon_btn(self.content, "✅  CASH INSERTED — CONFIRM", ACCENT_Y,
                 lambda: self._confirm_cash(amount_rs),
                 width=30, pady_val=10).pack()

    def _live_preview(self, amount_rs):
        """Instant Python preview while typing (DOSBox runs on Confirm)."""
        raw = self._cash_var.get().strip()
        try:
            tendered = float(raw)
        except ValueError:
            self._balance_lbl.config(
                text="Enter cash amount above", fg=TEXT_MUT)
            self._change_lbl.config(text="")
            self._asm_lbl.config(text="")
            return

        tp = int(round(tendered * 100))
        dp = self.grand_paise
        cp = tp - dp

        if cp < 0:
            self._balance_lbl.config(
                text=f"STILL NEEDED:  ₹ {abs(cp)/100:,.2f}", fg=ACCENT_R)
            self._change_lbl.config(text="")
            self._asm_lbl.config(
                text=f"  MOV AX, {tp}  ; tendered\n"
                     f"  MOV BX, {dp}  ; due\n"
                     f"  SUB AX, BX  → CF=1 (short)")
        elif cp == 0:
            self._balance_lbl.config(text="EXACT AMOUNT  ✔", fg=ACCENT_G)
            self._change_lbl.config(text="")
            self._asm_lbl.config(
                text=f"  MOV AX, {tp}  ; tendered\n"
                     f"  MOV BX, {dp}  ; due\n"
                     f"  SUB AX, BX  → ZF=1 (exact)")
        else:
            self._balance_lbl.config(text="CHANGE TO RETURN:", fg=TEXT_SEC)
            self._change_lbl.config(text=f"₹ {cp/100:,.2f}", fg=ACCENT_G)
            self._asm_lbl.config(
                text=f"  MOV AX, {tp}  ; tendered\n"
                     f"  MOV BX, {dp}  ; due\n"
                     f"  SUB AX, BX  → AX={cp}  (DOSBox verifies on CONFIRM)")

    def _confirm_cash(self, amount_rs):
        raw = self._cash_var.get().strip()
        try:
            tendered = float(raw)
        except ValueError:
            self._cash_err.config(text="⚠  Please enter a valid cash amount")
            return
        if tendered < amount_rs:
            self._cash_err.config(
                text=f"⚠  Insufficient — short by ₹ {amount_rs-tendered:,.2f}")
            return
        self._cash_err.config(text="")
        tp = int(round(tendered * 100))
        self.show_processing("Cash", tp, self.grand_paise, tp)

    # ── PROCESSING  (DOSBox-integrated) ───────────────────────────────────────
    def show_processing(self, method, tendered_paise, due_paise, _unused):
        self.clear_content()

        tk.Label(self.content, text="PROCESSING PAYMENT",
                 font=FONT_HERO, bg=BG_DEEP, fg=ACCENT_C).pack(pady=(46, 14))

        self._prog_var = tk.DoubleVar(value=0)
        ttk.Progressbar(self.content, variable=self._prog_var,
                        maximum=100, length=440,
                        mode="determinate").pack(pady=8)

        self._proc_lbl = tk.Label(self.content, text="Initialising...",
                                  font=FONT_BODY, bg=BG_DEEP, fg=TEXT_SEC)
        self._proc_lbl.pack(pady=4)

        self._status_box = tk.Frame(self.content, bg=BG_CARD2, padx=20, pady=10)
        self._status_box.pack(pady=8, padx=130, fill="x")
        self._status_lbl = tk.Label(self._status_box, text="",
                                    font=("Courier New", 9), bg=BG_CARD2,
                                    fg=ACCENT_P, justify="left", anchor="w")
        self._status_lbl.pack(fill="x")

        # State
        self._proc_method         = method
        self._proc_tendered_paise = tendered_paise
        self._proc_due_paise      = due_paise
        self._dosbox_change_paise = None
        self._dosbox_asm_trace    = ""

        is_cash = (method == "Cash")
        if is_cash:
            self._proc_steps = [
                (10,  "Writing CHANGE.ASM for emu8086..."),
                (25,  "Launching DOSBox + NASM assembler..."),
                (55,  "Running CHANGE.COM  (SUB AX, BX)..."),
                (75,  "Reading RESULT.TXT from DOSBox..."),
                (90,  "Verifying transaction with bank..."),
                (100, "Payment authorised!"),
            ]
        else:
            self._proc_steps = [
                (20,  "Verifying credentials..."),
                (45,  "Authorizing transaction..."),
                (70,  "Contacting issuing bank..."),
                (90,  "Confirming payment..."),
                (100, "Transaction complete!"),
            ]

        self._proc_idx = 0
        self._run_step()

    def _run_step(self):
        if self._proc_idx >= len(self._proc_steps):
            cp = self._dosbox_change_paise
            change_rs = (cp / 100) if cp is not None else 0.0
            self.after(500, lambda: self.show_success(
                self._proc_method, change_rs,
                asm_trace=self._dosbox_asm_trace,
                tendered_paise=self._proc_tendered_paise))
            return

        pct, msg = self._proc_steps[self._proc_idx]
        self._prog_var.set(pct)
        self._proc_lbl.config(text=msg)
        self._proc_idx += 1

        # At step index 3 for Cash ("Running CHANGE.COM") → launch DOSBox thread
        if self._proc_method == "Cash" and self._proc_idx == 3:
            self._status_lbl.config(
                text="DOSBox window launched...\n"
                     "Assembling & running CHANGE.COM\n"
                     "Window closes automatically when done.")
            threading.Thread(target=self._dosbox_thread, daemon=True).start()
            return  # thread calls _dosbox_done when finished

        self._anim_id = self.after(700, self._run_step)

    def _dosbox_thread(self):
        tp = self._proc_tendered_paise
        dp = self._proc_due_paise
        cp, trace, err = assemble_and_run_change(tp, dp)
        self.after(0, lambda: self._dosbox_done(cp, trace, err))

    def _dosbox_done(self, cp, trace, err):
        if cp is None:
            cp = (self._proc_tendered_paise or 0) - (self._proc_due_paise or 0)
            trace = (f"  [DOSBox error — Python fallback used]\n"
                     f"  {err[:72]}\n"
                     f"  Result: {cp} paise")
            self._status_lbl.config(
                text=f"⚠ DOSBox unavailable — fallback:\n{err[:70]}",
                fg=ACCENT_R)
        else:
            self._status_lbl.config(
                text=f"✔ DOSBox result: {cp} paise = ₹{cp/100:.2f}\n"
                     f"RESULT.TXT read OK", fg=ACCENT_G)

        self._dosbox_change_paise = cp
        self._dosbox_asm_trace    = trace
        self._anim_id = self.after(900, self._run_step)

    # ── SUCCESS ───────────────────────────────────────────────────────────────
    def show_success(self, method, change_rs=0.0,
                     asm_trace="", tendered_paise=None):
        self.clear_content()
        import datetime
        now       = datetime.datetime.now()
        amount_rs = self.grand_paise / 100

        tk.Label(self.content, text="✔",
                 font=("Consolas", 52, "bold"),
                 bg=BG_DEEP, fg=ACCENT_G).pack(pady=(10, 2))
        tk.Label(self.content, text="PAYMENT SUCCESSFUL",
                 font=("Consolas", 20, "bold"),
                 bg=BG_DEEP, fg=ACCENT_G).pack()

        # ── Receipt card ─────────────────────────────────────────────────
        rcpt = tk.Frame(self.content, bg=BG_CARD2, padx=30, pady=12)
        rcpt.pack(pady=8, padx=90, fill="x")

        def row(k, v, vc=TEXT_PRI):
            r = tk.Frame(rcpt, bg=BG_CARD2)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=k, font=("Consolas", 10),
                     bg=BG_CARD2, fg=TEXT_SEC, anchor="w",
                     width=20).pack(side="left")
            tk.Label(r, text=v, font=("Consolas", 10, "bold"),
                     bg=BG_CARD2, fg=vc, anchor="e").pack(side="right")

        row("AMOUNT PAID",  f"₹ {amount_rs:,.2f}", ACCENT_Y)
        if method == "Cash" and tendered_paise:
            row("CASH TENDERED", f"₹ {tendered_paise/100:,.2f}", TEXT_PRI)
            row("CHANGE DUE",
                f"₹ {change_rs:,.2f}" if change_rs > 0 else "₹ 0.00  (exact)",
                ACCENT_G if change_rs > 0 else TEXT_SEC)
            row("CALC ENGINE", "EMU8086 · DOSBox · NASM", ACCENT_P)
        row("METHOD",      method.upper(),                   ACCENT_C)
        row("DATE & TIME", now.strftime("%d %b %Y  %H:%M:%S"))
        row("MERCHANT",    "HyperStore International")
        row("TXN ID",      f"NPAY{random.randint(100000000,999999999)}")
        row("STATUS",      "APPROVED ✔",                     ACCENT_G)

        # ── Assembly trace (cash only) ────────────────────────────────────
        if method == "Cash" and asm_trace:
            af = tk.Frame(self.content, bg=BG_CARD, padx=16, pady=8)
            af.pack(pady=(4, 0), padx=90, fill="x")
            tk.Label(af, text="⚙  8086 Assembly Trace  (via DOSBox)",
                     font=("Consolas", 9, "bold"),
                     bg=BG_CARD, fg=ACCENT_P).pack(anchor="w")
            tk.Label(af, text=asm_trace,
                     font=("Courier New", 9), bg=BG_CARD,
                     fg=TEXT_MUT, justify="left",
                     anchor="w").pack(fill="x")

        # REMOVED: "Thank you for shopping at HyperStore!"

        neon_btn(self.content, "🏠  NEW TRANSACTION", ACCENT_C,
                 self.show_main_menu, width=26, pady_val=11).pack(pady=8)


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = NeonPayKiosk(grand_paise=144000)   # ₹1,440.00
    app.mainloop()
