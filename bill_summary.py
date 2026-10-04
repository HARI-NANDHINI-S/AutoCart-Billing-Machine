
import tkinter as tk
from tkinter import font as tkfont, messagebox, filedialog
import os, subprocess, time, threading, tempfile

try:
    from loyalty import get_loyalty_manager
    LOYALTY_AVAILABLE = True
except ImportError:
    LOYALTY_AVAILABLE = False

try:
    from transaction_history import get_transaction_logger
    TXN_LOG_AVAILABLE = True
except ImportError:
    TXN_LOG_AVAILABLE = False

# =============================================================================
# DOSBox + EMU 8086 bridge
# =============================================================================

def _find_dosbox():
    """Return path to DOSBox.exe or None."""
    candidates = [
        os.environ.get("DOSBOX_EXE", ""),
        r"C:\Program Files (x86)\DOSBox-0.74-3\DOSBox.exe",
        r"C:\Program Files (x86)\DOSBox-0.74\DOSBox.exe",
        r"C:\Program Files\DOSBox-0.74-3\DOSBox.exe",
        r"C:\Program Files\DOSBox-0.74\DOSBox.exe",
        r"C:\DOSBox\DOSBox.exe",
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


def run_asm_calc(folder, subtotal_paise, disc_pct, gst_pct, coupon_paise):
    """
    Write INPUT.TXT into `folder`, run calc.exe via DOSBox (same folder),
    read OUTPUT.TXT from `folder`.

    folder       = same directory as hypermarket_pos.py and calc.exe
    Returns dict: subtotal, discount, gst, coupon, grand  (all in paise)
                  source = "EMU8086/DOSBox" or "Python(fallback)"
    """
    calc_exe = os.path.join(folder, "calc.exe")
    dosbox   = _find_dosbox()

    if dosbox and os.path.isfile(calc_exe):
        try:
            input_file  = os.path.join(folder, "INPUT.TXT")
            output_file = os.path.join(folder, "OUTPUT.TXT")

            # write input
            with open(input_file, "w") as f:
                f.write(f"{subtotal_paise}\n{disc_pct}\n{gst_pct}\n{coupon_paise}\n")

            # remove stale output
            if os.path.exists(output_file):
                os.remove(output_file)

            # DOSBox autoexec config
            # Mount the FOLDER as C: so calc.exe, INPUT.TXT, OUTPUT.TXT
            # are all on the same virtual C: drive
            conf = (
                "[sdl]\n"
                "fullscreen=false\n"
                "[dosbox]\n"
                "machine=svga_s3\n"
                "[autoexec]\n"
                f"MOUNT C \"{folder}\"\n"
                "C:\\\n"
                "calc.exe\n"
                "exit\n"
            )
            conf_path = os.path.join(tempfile.gettempdir(), "hyperpos_dosbox.conf")
            with open(conf_path, "w") as f:
                f.write(conf)

            subprocess.run(
                [dosbox, "-conf", conf_path, "-noconsole"],
                timeout=20,
                creationflags=0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
            )

            # read output
            if os.path.isfile(output_file):
                with open(output_file) as f:
                    lines = [ln.strip() for ln in f.readlines() if ln.strip()]
                if len(lines) >= 5:
                    return {
                        "subtotal": int(lines[0]),
                        "discount": int(lines[1]),
                        "gst":      int(lines[2]),
                        "coupon":   int(lines[3]),
                        "grand":    int(lines[4]),
                        "source":   "EMU8086 / DOSBox",
                    }
        except Exception as ex:
            print(f"[DOSBox] error: {ex}")

    # Python fallback
    disc  = (subtotal_paise * disc_pct) // 100
    after = subtotal_paise - disc
    gst   = (after * gst_pct) // 100
    grand = max(0, after + gst - coupon_paise)
    return {
        "subtotal": subtotal_paise,
        "discount": disc,
        "gst":      gst,
        "coupon":   coupon_paise,
        "grand":    grand,
        "source":   "Python (fallback — calc.exe/DOSBox not found)",
    }


def rs(paise):
    return paise / 100.0

# =============================================================================
# Palette
# =============================================================================
BG_DARK    = "#0b0f19"
BG_PANEL   = "#111827"
BG_CARD    = "#1a2235"
BG_INPUT   = "#0d1424"
ACCENT     = "#4f8ef7"
ACCENT_DIM = "#2d5da6"
GREEN      = "#22c55e"
RED        = "#ef4444"
YELLOW     = "#f59e0b"
CYAN       = "#06b6d4"
TW         = "#f1f5f9"
TM         = "#64748b"
TPRICE     = "#4f8ef7"
TGREEN     = "#22c55e"
TRED       = "#ef4444"
BORDER     = "#1e2d45"
BORDERL    = "#253550"

def mf(size, weight="normal", family="Segoe UI"):
    return tkfont.Font(family=family, size=size, weight=weight)

def mono(size, weight="normal"):
    return tkfont.Font(family="Courier New", size=size, weight=weight)

# =============================================================================
# Order Summary Window
# =============================================================================
class OrderSummaryWindow(tk.Toplevel):
    def __init__(self, parent, cart, product_map, disc_pct, coupon_rs, folder,
                 manual_discount=0.0, session_id=None, is_cashier=True):
        super().__init__(parent)
        self.cart        = cart
        self.product_map = product_map
        self.disc_pct    = disc_pct
        self.coupon_rs   = coupon_rs
        self.folder      = folder
        self.manual_discount = manual_discount
        self.session_id  = session_id
        self.is_cashier  = is_cashier
        self._results    = {}
        self._gst_used   = 18

        self.title("HyperMarket Pro  |  Order Summary")
        self.configure(bg=BG_DARK)
        self.resizable(False, False)
        self.grab_set()

        parent.update_idletasks()
        pw = parent.winfo_width(); ph = parent.winfo_height()
        px = parent.winfo_x();    py = parent.winfo_y()
        self.geometry(f"440x790+{px+pw//2-220}+{py+ph//2-395}")

        self._build_ui()
        self._compute_async()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Normalize cart keys to strings to match PRODUCT_MAP
        self.cart = {str(k): v for k, v in self.cart.items()}
        
        items = len(self.cart)
        # Handle both simple {pid: qty} and complex {pid: {"qty": q, "price": p}}
        units = 0
        subtotal_rs = 0.0
        for pid, val in self.cart.items():
            if pid not in self.product_map: continue
            if isinstance(val, dict):
                q = val.get("qty", 0)
                p = val.get("price", self.product_map[pid]["price"])
            else:
                q = val
                p = self.product_map[pid]["price"]
            units += q
            subtotal_rs += p * q
        avg = subtotal_rs / items if items else 0

        # Stats boxes
        stats = tk.Frame(self, bg=BG_DARK)
        stats.pack(fill="x", padx=14, pady=(14,8))
        for col, (val, lbl) in enumerate([(str(items),"ITEMS"),
                                           (str(units),"UNITS"),
                                           (f"₹{avg:.0f}","AVG/ITEM")]):
            box = tk.Frame(stats, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
            box.grid(row=0, column=col, padx=4, sticky="ew")
            stats.columnconfigure(col, weight=1)
            tk.Label(box, text=val, font=mf(20,"bold"), bg=BG_CARD, fg=TW).pack(pady=(10,0))
            tk.Label(box, text=lbl, font=mf(7,"bold"),  bg=BG_CARD, fg=TM).pack(pady=(0,10))

        # Coupon
        cf = tk.Frame(self, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        cf.pack(fill="x", padx=14, pady=6)
        tk.Label(cf, text="✏  COUPON / PROMO", font=mf(8,"bold"),
                 bg=BG_CARD, fg=TM).pack(anchor="w", padx=12, pady=(10,4))
        cr = tk.Frame(cf, bg=BG_CARD)
        cr.pack(fill="x", padx=10, pady=(0,12))
        cr.columnconfigure(0, weight=1)
        self.coupon_var = tk.StringVar()
        ce = tk.Entry(cr, textvariable=self.coupon_var, font=mf(10),
                      bg=BG_INPUT, fg=TM, insertbackground=TW, relief="flat",
                      highlightbackground=BORDERL, highlightthickness=1)
        ce.insert(0, "Enter code...")
        ce.grid(row=0, column=0, sticky="ew", ipady=8, padx=(0,8))
        ce.bind("<FocusIn>", lambda e: (ce.delete(0,"end"), ce.config(fg=TW)))
        ab = tk.Label(cr, text="Apply", font=mf(9,"bold"),
                      bg=ACCENT, fg=TW, padx=18, pady=8, cursor="hand2")
        ab.grid(row=0, column=1)
        ab.bind("<Button-1>", lambda e: self._apply_coupon(ce))
        ab.bind("<Enter>",    lambda e: ab.config(bg="#6aa3ff"))
        ab.bind("<Leave>",    lambda e: ab.config(bg=ACCENT))

        # Order summary card
        sf = tk.Frame(self, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        sf.pack(fill="x", padx=14, pady=6)
        tk.Label(sf, text="🧾  ORDER SUMMARY", font=mf(8,"bold"),
                 bg=BG_CARD, fg=TM).pack(anchor="w", padx=12, pady=(10,6))

        def srow(label, attr, color=TW, badge=None):
            r = tk.Frame(sf, bg=BG_CARD); r.pack(fill="x", padx=14, pady=4)
            lf = tk.Frame(r, bg=BG_CARD); lf.pack(side="left")
            tk.Label(lf, text=label, font=mf(10), bg=BG_CARD, fg=TM).pack(side="left")
            if badge:
                tk.Label(lf, text=badge, font=mf(7,"bold"),
                         bg=YELLOW, fg="#000", padx=4).pack(side="left", padx=6)
            lbl = tk.Label(r, text="₹0.00", font=mf(10,"bold"), bg=BG_CARD, fg=color)
            lbl.pack(side="right")
            setattr(self, attr, lbl)

        srow("Subtotal",       "lbl_sub")
        srow("Discount",       "lbl_dis", color=TRED,   badge=f"{self.disc_pct}%")
        srow("GST",            "lbl_gst", color=TGREEN)
        srow("Coupon Savings", "lbl_cpn", color=YELLOW)
        tk.Frame(sf, bg=BORDERL, height=1).pack(fill="x", padx=10, pady=6)

        # Grand total
        gt = tk.Frame(self, bg="#0e1a32", highlightbackground=ACCENT_DIM, highlightthickness=1)
        gt.pack(fill="x", padx=14, pady=6)
        tk.Label(gt, text="GRAND TOTAL", font=mf(8,"bold"),
                 bg="#0e1a32", fg=TM).pack(anchor="w", padx=14, pady=(10,0))
        br = tk.Frame(gt, bg="#0e1a32"); br.pack(fill="x", padx=14, pady=(0,10))
        self.lbl_grand = tk.Label(br, text="₹0.00", font=mf(32,"bold"),
                                   bg="#0e1a32", fg=CYAN)
        self.lbl_grand.pack(side="left")
        bf = tk.Frame(br, bg="#0e1a32"); bf.pack(side="right")
        tk.Label(bf, text=f"{sum(self.cart.values())} items",
                 font=mf(8,"bold"), bg=BG_CARD, fg=TW, padx=8, pady=4).pack()
        tk.Label(bf, text="INCL. ALL TAXES", font=mf(7), bg="#0e1a32", fg=TM).pack(pady=(4,0))

        # Source label
        self.lbl_src = tk.Label(self, text="⏳  Sending to EMU 8086 via DOSBox...",
                                 font=mf(7), bg=BG_DARK, fg=TM)
        self.lbl_src.pack(pady=2)

        # ── Loyalty Points Section ────────────────────────────────────────────
        if LOYALTY_AVAILABLE:
            lp_frame = tk.Frame(self, bg=BG_CARD, highlightbackground=BORDERL, highlightthickness=1)
            lp_frame.pack(fill="x", padx=14, pady=4)
            tk.Label(lp_frame, text="🏆  LOYALTY POINTS", font=mf(8,"bold"),
                     bg=BG_CARD, fg="#ffd700").pack(anchor="w", padx=12, pady=(8,2))

            # Points to be earned
            subtotal_p = int(subtotal_rs * 100)
            est_points = max(0, subtotal_p // 1000)
            pe_row = tk.Frame(lp_frame, bg=BG_CARD)
            pe_row.pack(fill="x", padx=14, pady=2)
            tk.Label(pe_row, text="Points to earn:", font=mf(9), bg=BG_CARD, fg=TM).pack(side="left")
            self.lbl_pts_earn = tk.Label(pe_row, text=f"+{est_points} pts", font=mf(9,"bold"),
                                         bg=BG_CARD, fg="#ffd700")
            self.lbl_pts_earn.pack(side="right")

            # Redeem button
            self._loyalty_discount = 0.0
            rd_row = tk.Frame(lp_frame, bg=BG_CARD)
            rd_row.pack(fill="x", padx=14, pady=(2,8))
            self.redeem_var = tk.StringVar(value="0")
            tk.Label(rd_row, text="Redeem pts:", font=mf(8), bg=BG_CARD, fg=TM).pack(side="left")
            tk.Entry(rd_row, textvariable=self.redeem_var, font=mf(9),
                     bg=BG_INPUT, fg=TW, insertbackground=TW, relief="flat",
                     width=8, highlightbackground=BORDERL, highlightthickness=1).pack(side="left", padx=4)
            rb = tk.Label(rd_row, text="Redeem", font=mf(8,"bold"),
                          bg="#ffd700", fg="#000", padx=10, pady=4, cursor="hand2")
            rb.pack(side="left", padx=4)
            rb.bind("<Button-1>", lambda e: self._redeem_loyalty())

        # Generate Bill button
        gb = tk.Label(self, text="🧾   Generate Bill",
                      font=mf(13,"bold"), bg=GREEN, fg=TW, pady=14, cursor="hand2")
        gb.pack(fill="x", padx=14, pady=(6,14))
        gb.bind("<Button-1>", lambda e: self._open_bill())
        gb.bind("<Enter>",    lambda e: gb.config(bg="#16a34a"))
        gb.bind("<Leave>",    lambda e: gb.config(bg=GREEN))

    # ── async compute ─────────────────────────────────────────────────────────
    def _compute_async(self):
        def run():
            # Calculate input values for EMU 8086
            subtotal_p = 0
            total_gst_paise = 0.0
            
            for pid, val in self.cart.items():
                if pid not in self.product_map: continue
                if isinstance(val, dict):
                    q = val.get("qty", 0)
                    p = val.get("price", self.product_map[pid]["price"])
                else:
                    q = val
                    p = self.product_map[pid]["price"]
                
                item_sub_p = int(p * q * 100)
                subtotal_p += item_sub_p
                
                # GST for this item
                gst_pct = self.product_map[pid].get("gst", 18)
                total_gst_paise += (item_sub_p * gst_pct / 100.0)

            # Apply manual discount to subtotal
            subtotal_p = max(0, subtotal_p - int(self.manual_discount * 100))
            
            # Weighted average GST
            avg_gst = int(round(total_gst_paise / (subtotal_p / 100.0))) if subtotal_p > 0 else 18
            self._gst_used = avg_gst

            result = run_asm_calc(
                self.folder, subtotal_p,
                self.disc_pct, avg_gst,
                int(self.coupon_rs * 100)
            )
            self._results = result
            self.after(0, self._update_labels)
        threading.Thread(target=run, daemon=True).start()

    def _update_labels(self):
        r = self._results
        def fmt(p): return f"₹{rs(p):.2f}"
        self.lbl_sub.config(text=fmt(r["subtotal"]))
        self.lbl_dis.config(text=f"-{fmt(r['discount'])}")
        self.lbl_gst.config(text=f"+{fmt(r['gst'])}")
        self.lbl_cpn.config(text=fmt(r["coupon"]))
        self.lbl_grand.config(text=fmt(r["grand"]))
        src = r.get("source","?")
        col = TGREEN if "DOSBox" in src else YELLOW
       # self.lbl_src.config(text=f"✓  Computed by: {src}", fg=col)

    def _redeem_loyalty(self):
        """Redeem loyalty points as discount."""
        if not LOYALTY_AVAILABLE:
            return
        try:
            pts = int(self.redeem_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid", "Enter a valid number of points", parent=self)
            return
        if pts <= 0:
            return
        # Apply discount: 100 pts = Rs 10
        self._loyalty_discount = (pts / 100.0) * 10.0
        self.manual_discount += self._loyalty_discount
        self._compute_async()
        messagebox.showinfo("Loyalty", f"Redeemed {pts} pts for \u20b9{self._loyalty_discount:.2f} discount", parent=self)

    def _apply_coupon(self, entry):
        codes = {"SAVE50":50.0,"HYPER20":20.0,"FLAT100":100.0}
        code  = self.coupon_var.get().strip().upper()
        if code in codes:
            self.coupon_rs = codes[code]; entry.config(fg=TGREEN)
        else:
            self.coupon_rs = 0.0; entry.config(fg=TRED)
        self._compute_async()

    def _open_bill(self):
        if not self._results:
            messagebox.showinfo("Wait", "Calculation running, please try again.")
            return

        # Log transaction
        if TXN_LOG_AVAILABLE:
            try:
                logger = get_transaction_logger()
                logger.log_transaction(
                    self.cart, self.product_map, self._results,
                    self.disc_pct, self._gst_used,
                    self.manual_discount, self.session_id
                )
            except Exception as e:
                print(f"[TxnLog] Error: {e}")

        # Award loyalty points
        loyalty_earned = 0
        if LOYALTY_AVAILABLE:
            try:
                mgr = get_loyalty_manager()
                total_paise = self._results.get("grand", 0)
                loyalty_earned = mgr.add_points("customer", total_paise, multiplier=1)
            except Exception:
                pass

        BillWindow(self, self.cart, self.product_map,
                   self._results, self.disc_pct, self._gst_used,
                   self.manual_discount, self.session_id, loyalty_earned, self.is_cashier)

# =============================================================================
# Thermal Receipt Bill Window
# =============================================================================
class BillWindow(tk.Toplevel):
    def __init__(self, parent, cart, product_map, results, disc_pct, gst_pct,
                 manual_discount=0.0, session_id=None, loyalty_earned=0, is_cashier=True):
        super().__init__(parent)
        self.cart        = cart
        self.product_map = product_map
        self.results     = results
        self.disc_pct    = disc_pct
        self.gst_pct     = gst_pct
        self.manual_discount = manual_discount
        self.session_id  = session_id
        self.loyalty_earned = loyalty_earned
        self.is_cashier = is_cashier
        self._bill_no    = int(time.time()) % 100000
        self._plain_text = ""

        self.title("HyperMarket Pro  |  Tax Invoice")
        self.configure(bg="#1a1a2e")
        self.resizable(False, True)
        self.grab_set()

        parent.update_idletasks()
        px = parent.winfo_x(); py = parent.winfo_y()
        pw = parent.winfo_width(); ph = parent.winfo_height()
        self.geometry(f"520x820+{px+pw//2-260}+{py+10}")

        self._build_receipt()
        self._build_actions()

    def _build_receipt(self):
        shadow = tk.Frame(self, bg="#0a0a14")
        shadow.pack(fill="both", expand=True, padx=20, pady=(16,4))
        receipt = tk.Frame(shadow, bg="#f8f8f2")
        receipt.pack(fill="both", expand=True, padx=3, pady=3)

        canvas = tk.Canvas(receipt, bg="#f8f8f2", highlightthickness=0)
        vsb    = tk.Scrollbar(receipt, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg="#f8f8f2")
        canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        C = "#f8f8f2"; BLK = "#111"; GRY = "#555"

        def dashed(color="#bbb"):
            tk.Label(inner, text="- "*28, font=mono(7), bg=C, fg=color).pack(fill="x", padx=4)

        def ctr(text, size=10, bold=False, color=BLK):
            tk.Label(inner, text=text,
                     font=mono(size,"bold" if bold else "normal"),
                     bg=C, fg=color).pack()

        def lr(left, right, lsize=9, lcolor=BLK, rcolor=BLK, bold=False):
            w = "bold" if bold else "normal"
            r = tk.Frame(inner, bg=C); r.pack(fill="x", padx=14, pady=1)
            tk.Label(r, text=left,  font=mono(lsize,w), bg=C, fg=lcolor, anchor="w").pack(side="left")
            tk.Label(r, text=right, font=mono(lsize,w), bg=C, fg=rcolor, anchor="e").pack(side="right")

        # Header
        tk.Label(inner, text="", bg=C).pack(pady=8)
        ctr("*  HyperMarket Pro  *", 13, bold=True, color="#1a1a8c")
        ctr("Enterprise Supermarket POS", 8, color=GRY)
        ctr("GSTIN: 33ABCDE1234F1Z5", 7, color=GRY)
        ctr("Ph: 044-2345-6789  |  www.hypermarket.in", 7, color=GRY)
        tk.Label(inner, text="", bg=C).pack(pady=2)
        dashed()
        ctr("TAX INVOICE", 10, bold=True, color="#1a1a8c")
        dashed()
        lr(f"Bill #: {self._bill_no:05d}", f"Date: {time.strftime('%d/%m/%Y')}")
        lr(f"Time : {time.strftime('%I:%M %p')}", "Mode: RETAIL")
        lr("Cashier: VAAV", "Counter: #84")
        lr("Powered by: EMU 8086 + Python", "DOSBox Integration")
        dashed()

        # Column header
        r = tk.Frame(inner, bg=C); r.pack(fill="x", padx=14)
        for txt, w, anch in [("ITEM",20,"w"),("QTY",4,"e"),("RATE",7,"e"),("AMT",9,"e")]:
            tk.Label(r, text=txt, font=mono(8,"bold"), bg=C, fg=GRY,
                     width=w, anchor=anch).pack(side="left")
        dashed(color="#ccc")

        # Line items
        lines = []
        for pid, qty in self.cart.items():
            p = self.product_map.get(pid)
            if not p: continue
            amt  = p["price"] * qty
            name = p["name"][:18].ljust(18)
            lines.append((name, qty, p["price"], amt, p.get("gst",18)))
            row_f = tk.Frame(inner, bg=C); row_f.pack(fill="x", padx=14, pady=1)
            tk.Label(row_f, text=name, font=mono(8), bg=C, fg=BLK, width=20, anchor="w").pack(side="left")
            tk.Label(row_f, text=str(qty), font=mono(8), bg=C, fg=GRY, width=4, anchor="e").pack(side="left")
            tk.Label(row_f, text=f"{p['price']:.0f}", font=mono(8), bg=C, fg=GRY, width=7, anchor="e").pack(side="left")
            tk.Label(row_f, text=f"Rs.{amt:.2f}", font=mono(8,"bold"), bg=C,
                     fg="#1a1a8c", width=9, anchor="e").pack(side="left")

        dashed()

        # Totals
        R = self.results
        def frs(p): return f"Rs.{rs(p):>8.2f}"
        lr("Sub-Total",                    frs(R["subtotal"]),     lcolor=GRY)
        lr(f"Discount ({self.disc_pct}%)", f"-{frs(R['discount'])}", lcolor=GRY, rcolor="#c0392b")
        lr(f"GST ({self.gst_pct}%)",       f"+{frs(R['gst'])}",     lcolor=GRY, rcolor="#27ae60")
        if R["coupon"]:
            lr("Coupon Savings",           f"-{frs(R['coupon'])}", lcolor=GRY, rcolor="#e67e22")
        dashed()

        # Grand total
        gr = tk.Frame(inner, bg=C); gr.pack(fill="x", padx=14, pady=4)
        tk.Label(gr, text="GRAND TOTAL", font=mono(11,"bold"), bg=C, fg="#1a1a8c").pack(side="left")
        tk.Label(gr, text=f"Rs.{rs(R['grand']):.2f}", font=mono(13,"bold"),
                 bg=C, fg="#1a1a8c").pack(side="right")
        dashed()

        # Savings banner
        savings = rs(R["discount"] + R["coupon"])
        if savings > 0:
            tk.Label(inner, text=f"  ** YOU SAVED  Rs.{savings:.2f} TODAY **  ",
                     font=mono(9,"bold"), bg="#fff3cd", fg="#856404").pack(fill="x",padx=20,pady=4)
            dashed()

        # Loyalty points earned
        if self.loyalty_earned > 0:
            tk.Label(inner, text=f"  🏆 LOYALTY POINTS EARNED: +{self.loyalty_earned} pts  ",
                     font=mono(9,"bold"), bg="#e8f5e9", fg="#2e7d32").pack(fill="x",padx=20,pady=4)
            dashed()

        ctr("Thank you for shopping!", 9, bold=True, color="#1a1a8c")
        ctr("Visit again soon :)", 8, color=GRY)
        tk.Label(inner, text="", bg=C).pack(pady=8)

        self._build_plain_text(lines, R)

    def _build_plain_text(self, lines, R):
        sep  = "-" * 44
        dsep = "=" * 44
        out  = [dsep, "       HyperMarket Pro  --  TAX INVOICE", dsep,
                f"Bill #: {self._bill_no:05d}    Date: {time.strftime('%d %b %Y  %I:%M %p')}",
                sep, f"{'ITEM':<20} {'QTY':>4} {'RATE':>7} {'AMT':>9}", sep]
        for name, qty, rate, amt, _ in lines:
            out.append(f"{name:<20} {qty:>4} {rate:>7.0f} {amt:>9.2f}")
        out += [sep,
                f"{'Sub-Total':<30} {rs(R['subtotal']):>9.2f}"]
        if self.manual_discount > 0:
            out.append(f"{'Manual Discount':<30}-{self.manual_discount:>9.2f}")
        out += [f"{'Discount ('+str(self.disc_pct)+'%)':<30}-{rs(R['discount']):>9.2f}",
                f"{'GST':<30}+{rs(R['gst']):>9.2f}"]
        if R["coupon"]:
            out.append(f"{'Coupon Savings':<30}-{rs(R['coupon']):>9.2f}")
        out += [dsep, f"{'GRAND TOTAL':<30} {rs(R['grand']):>9.2f}", dsep,
                "     Thank you for shopping at HyperMarket Pro!", dsep]
        self._plain_text = "\n".join(out)

    def _build_actions(self):
        bf = tk.Frame(self, bg="#1a1a2e")
        bf.pack(fill="x", padx=20, pady=(4,16))
        bf.columnconfigure((0,1,2,3,4), weight=1)
        for col,(txt,bg,hov,cmd) in enumerate([
            ("X  Cancel", RED,    "#b91c1c", self.destroy),
            ("Save",      ACCENT, "#2563eb", self._save),
            ("Print",     "#7c3aed","#6d28d9",self._print),
            ("Share",     YELLOW, "#b45309", self._share),
            ("Pay Now",   "#10b981", "#059669", self._pay_now),
        ]):
            b = tk.Label(bf, text=txt, font=mf(10,"bold"),
                         bg=bg, fg=TW, pady=12, cursor="hand2")
            b.grid(row=0, column=col, padx=3, sticky="ew")
            b.bind("<Button-1>", lambda e,c=cmd: c())
            b.bind("<Enter>",    lambda e,h=hov,w=b: w.config(bg=h))
            b.bind("<Leave>",    lambda e,og=bg,w=b: w.config(bg=og))

    def _save(self):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        default_name = f"HyperMarket_Bill_{self._bill_no}.txt"
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text","*.txt"),("All","*.*")],
            initialdir=desktop,
            initialfile=default_name,
            title="Save Bill to Desktop")
        if path:
            with open(path,"w",encoding="utf-8") as f: f.write(self._plain_text)
            messagebox.showinfo("Saved", f"Receipt saved to Desktop:\n{os.path.basename(path)}")
        else:
            # If user cancels, still save to Desktop with default name
            default_path = os.path.join(desktop, default_name)
            with open(default_path,"w",encoding="utf-8") as f: f.write(self._plain_text)
            messagebox.showinfo("Saved", f"Receipt saved to Desktop:\n{default_name}")

    def _print(self):
        tmp = os.path.join(tempfile.gettempdir(), f"HM_Bill_{self._bill_no}.txt")
        with open(tmp,"w",encoding="utf-8") as f: f.write(self._plain_text)
        try:
            if os.name == "nt": os.startfile(tmp, "print")
            else: subprocess.Popen(["lp", tmp])
            messagebox.showinfo("Print", "Bill sent to printer.")
        except Exception as ex:
            messagebox.showerror("Print Error", str(ex))

    def _share(self):
        self.clipboard_clear()
        self.clipboard_append(self._plain_text)
        messagebox.showinfo("Shared", "Bill text copied to clipboard!\nPaste in WhatsApp / Email.")

    def _pay_now(self):
        """Open payment kiosk (cash/card/upi) for current grand total."""
        if not hasattr(self, 'results') or not self.results:
            messagebox.showinfo("Payment", "Price data not available yet.", parent=self)
            return
        total_paise = self.results.get('grand', 0)
        if total_paise <= 0:
            messagebox.showinfo("Payment", "Total amount is zero; nothing to pay.", parent=self)
            return

        import traceback
        try:
            from payment_screen import PaymentScreen
            pay_window = PaymentScreen(self, grand_paise=total_paise, is_cashier=self.is_cashier)
            self.wait_window(pay_window)
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Payment Module Error:\n{error_trace}")
            messagebox.showerror("Payment Error", 
                                f"The payment module failed to open.\n\nError: {e}\n\nPlease ensure 'Pillow' (PIL) and 'qrcode' are installed: \n'pip install Pillow qrcode'")
        finally:
            try:
                self.deiconify()
            except:
                pass

# =============================================================================
# Public entry point
# =============================================================================
def open_bill_summary(parent, cart, product_map,
                      discount_pct=10, coupon_discount=0.0, folder=None,
                      manual_discount=0.0, session_id=None, is_cashier=True):
    if not cart:
        messagebox.showinfo("Empty Cart", "Add items to cart first.", parent=parent)
        return
    if folder is None:
        folder = os.path.dirname(os.path.abspath(__file__))
    OrderSummaryWindow(parent, cart, product_map, discount_pct, coupon_discount, folder,
                       manual_discount, session_id, is_cashier)


# =============================================================================
# Standalone test / integration entrypoint
# =============================================================================
if __name__ == "__main__":
    try:
        from main_hypermarket import main
        main()
    except Exception:
        # Fallback test mode shows bill summary if main path unavailable.
        SAMPLE = [
            {"id":101,"name":"Amul Butter 500g","price":255.0,"cat":"Dairy","emoji":"🧈","gst":5},
            {"id":102,"name":"Coke 2L Combo",   "price": 95.0,"cat":"Drinks","emoji":"🥤","gst":12},
            {"id":104,"name":"Basmati Rice 5kg","price":750.0,"cat":"Grains","emoji":"🌾","gst":5},
            {"id":108,"name":"Surf Excel 1kg",  "price":220.0,"cat":"Care","emoji":"🧹","gst":18},
        ]
        PM   = {p["id"]:p for p in SAMPLE}
        CART = {101:2, 102:3, 104:1, 108:1}
        root = tk.Tk(); root.withdraw()
        open_bill_summary(root, CART, PM)
        root.mainloop()
