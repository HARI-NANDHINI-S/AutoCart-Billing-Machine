"""
HyperMarket Pro — Self Checkout POS
Integrated with EMU 8086 calc.asm / calc.exe via DOSBox
All files in SAME folder.
"""

import tkinter as tk
from tkinter import font, messagebox
import time
import os
import sys
import json
import subprocess
from bill_summary import open_bill_summary
from scan import decode_product_id
from asm_utils import calculate_weight_price, inventory_threshold_alert
from products import PRODUCTS, PRODUCT_MAP
HERE = os.path.dirname(os.path.abspath(__file__))

CATEGORIES    = ["All", "Dairy", "Drinks", "Grains", "Care", "Snacks"]
DISCOUNT_PCT  = 10
GST_DEFAULT   = 18

BG_DARK      = "#0b0f19"
BG_PANEL     = "#111827"
BG_CARD      = "#1a2235"
BG_CARD_HOV  = "#1e2a40"
BG_INPUT     = "#0d1424"
BG_SCANNER   = "#0d1b2a"
ACCENT       = "#4f8ef7"
ACCENT_HOV   = "#6aa3ff"
ACCENT_DIM   = "#2d5da6"
GREEN        = "#22c55e"
RED          = "#ef4444"
YELLOW       = "#f59e0b"
CYAN         = "#06b6d4"
TEXT_WHITE   = "#f1f5f9"
TEXT_MUTED   = "#64748b"
TEXT_PRICE   = "#4f8ef7"
TEXT_GREEN   = "#22c55e"
TEXT_RED     = "#ef4444"
BORDER       = "#1e2d45"
BORDER_LT    = "#253550"
TAG_BG       = "#1e2d45"
BTN_MINUS    = "#1e2d45"
BTN_PLUS_BG  = "#14532d"
SCAN_BORDER  = "#164e63"
ACCENT2      = "#7c3aed"

def _mf(family, size, weight="normal"):
    return font.Font(family=family, size=size, weight=weight)

class POSScreen(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HyperMarket Pro | Self Checkout POS")
        self.geometry("1100x860")
        self._center_window(1100, 860)
        self.minsize(900, 700)
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        self.cart             = {}
        self.coupon_discount  = 0.0
        self.active_cat       = tk.StringVar(value="All")
        self.search_var       = tk.StringVar()
        self.pid_var          = tk.StringVar()
        self.coupon_var       = tk.StringVar()
        self._scan_buffer     = ""
        self._scan_timer      = None
        self._pid_placeholder = True
        self._cat_placeholder = True

        self._build_fonts()
        self._build_layout()
        self._refresh_catalog()
        self.bind("<Key>", self._on_key)
        self._tick_clock()

    def _center_window(self, width, height):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - width) // 2
        y = (sh - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_fonts(self):
        F = "Segoe UI"
        E = "Segoe UI Emoji"
        self.fn_h1      = _mf(F, 18, "bold")
        self.fn_h2      = _mf(F, 13, "bold")
        self.fn_h3      = _mf(F, 11, "bold")
        self.fn_body    = _mf(F, 10)
        self.fn_small   = _mf(F, 8)
        self.fn_price   = _mf(F, 11, "bold")
        self.fn_btn     = _mf(F, 12, "bold")
        self.fn_emoji   = _mf(E, 22)
        self.fn_emoji_s = _mf(E, 16)
        self.fn_mono    = _mf("Consolas", 10)
        self.fn_scan    = _mf("Consolas", 9)
        self.fn_cat     = _mf(F, 8,  "bold")

    def _build_layout(self):
        self._build_header()
        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        body.columnconfigure(0, weight=4, minsize=320)
        body.columnconfigure(1, weight=6, minsize=460)
        body.rowconfigure(0, weight=1)
        left   = tk.Frame(body, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        center = tk.Frame(body, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        left.grid(  row=0, column=0, sticky="nsew", padx=(0, 4))
        center.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        self._build_left(left)
        self._build_center(center)

    def _build_header(self):
        hdr = tk.Frame(self, bg="#0d1424", highlightbackground=BORDER, highlightthickness=1)
        hdr.pack(fill="x", padx=8, pady=(8, 4))
        logo_f = tk.Frame(hdr, bg="#0d1424")
        logo_f.pack(side="left", padx=(12, 20), pady=6)
        tk.Label(logo_f, text="🛒", font=self.fn_emoji, bg="#0d1424", fg=ACCENT).pack(side="left")
        lname = tk.Frame(logo_f, bg="#0d1424")
        lname.pack(side="left", padx=6)
        tk.Label(lname, text="HyperMarket Pro", font=_mf("Segoe UI", 15, "bold"),
                 bg="#0d1424", fg=TEXT_WHITE).pack(anchor="w")
        tk.Label(lname, text="SELF CHECKOUT  #84", font=self.fn_small,
                 bg="#0d1424", fg=TEXT_MUTED).pack(anchor="w")
        for txt, col in [("● ONLINE", GREEN), ("⚡ VAAV", YELLOW), ("🏪 RETAIL", CYAN)]:
            tk.Label(hdr, text=txt, font=self.fn_cat, bg=TAG_BG, fg=col,
                     padx=10, pady=4).pack(side="left", padx=4)
        self.lbl_clock = tk.Label(hdr, text="", font=self.fn_h3,
                                   bg="#0d1424", fg=TEXT_WHITE)
        self.lbl_clock.pack(side="right", padx=(0, 12))
        tk.Label(hdr, text="End Session", font=self.fn_cat, bg=RED, fg=TEXT_WHITE,
                 padx=12, pady=5, cursor="hand2").pack(side="right", padx=8)
        tk.Label(hdr, text="V  Valued", font=self.fn_cat, bg=ACCENT_DIM, fg=TEXT_WHITE,
                 padx=10, pady=5).pack(side="right", padx=4)

    def _tick_clock(self):
        self.lbl_clock.config(text=time.strftime("%I:%M:%S %p").lower())
        self.after(1000, self._tick_clock)

    def _build_left(self, parent):
        parent.rowconfigure(0, weight=0)
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)
        self._build_pid_section(parent)
        self._build_catalog_section(parent)

    def _build_pid_section(self, parent):
        sec = tk.Frame(parent, bg=BG_PANEL)
        sec.grid(row=0, column=0, sticky="ew", padx=10, pady=4)
        _sec_header(sec, "▦  MANUAL SCAN OVERRIDE", BG_PANEL)
        row = tk.Frame(sec, bg=BG_PANEL)
        row.pack(fill="x", pady=4)
        row.columnconfigure(0, weight=1)
        entry = tk.Entry(row, textvariable=self.pid_var,
                         font=self.fn_mono, bg=BG_INPUT, fg=TEXT_MUTED,
                         insertbackground=TEXT_WHITE, relief="flat",
                         highlightbackground=BORDER_LT, highlightthickness=1)
        entry.insert(0, "Enter Product ID...")
        entry.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 6))
        entry.bind("<FocusIn>",  lambda e: self._pid_focus_in(entry))
        entry.bind("<FocusOut>", lambda e: self._pid_focus_out(entry))
        entry.bind("<Return>",   lambda e: self._pid_scan())
        self._pid_entry = entry
        scan_btn = tk.Label(row, text="SCAN", font=self.fn_cat, bg=ACCENT, fg=TEXT_WHITE,
                            padx=14, pady=8, cursor="hand2")
        scan_btn.grid(row=0, column=1)
        scan_btn.bind("<Button-1>", lambda e: self._pid_scan())
        scan_btn.bind("<Enter>", lambda e: scan_btn.config(bg=ACCENT_HOV))
        scan_btn.bind("<Leave>", lambda e: scan_btn.config(bg=ACCENT))

        # Scan1 integration buttons
        bridge_frame = tk.Frame(sec, bg=BG_PANEL)
        bridge_frame.pack(fill="x", pady=(4,0))

        scan_btn2 = tk.Button(bridge_frame, text="📷 SCAN PRODUCT", font=self.fn_small,
                  bg=ACCENT2, fg=TEXT_WHITE, relief="flat", bd=0,
                  cursor="hand2", command=self._mode_scan)
        scan_btn2.pack(side="left", padx=2)
        tk.Button(bridge_frame, text="🔄 SYNC SCANNED", font=self.fn_small,
                  bg=ACCENT, fg=TEXT_WHITE, relief="flat", bd=0,
                  cursor="hand2", command=self._sync_scan1_cart).pack(side="left", padx=2)

    def _pid_focus_in(self, e):
        if self._pid_placeholder:
            e.delete(0, "end"); e.config(fg=TEXT_WHITE)
            self._pid_placeholder = False

    def _pid_focus_out(self, e):
        if not self.pid_var.get().strip():
            e.insert(0, "Enter Product ID..."); e.config(fg=TEXT_MUTED)
            self._pid_placeholder = True

    def _pid_scan(self):
        raw = "" if self._pid_placeholder else self.pid_var.get().strip()
        if not raw: return
        self._add_to_cart(raw, 1)
        self.pid_var.set("")
        self._pid_entry.delete(0, "end")
        self._pid_entry.insert(0, "Enter Product ID...")
        self._pid_entry.config(fg=TEXT_MUTED)
        self._pid_placeholder = True

    def _mode_scan(self):
        """Launch scanner and wait for it to finish, then auto-sync."""
        self._launch_scan1()

    def _launch_scan1(self):
        scan1_path = os.path.join(os.path.dirname(__file__), "scan1.py")
        if not os.path.isfile(scan1_path):
            messagebox.showerror("scan1 Missing", "scan1.py not found in project folder")
            return
        proc = subprocess.Popen([sys.executable, scan1_path], cwd=os.path.dirname(__file__))
        self._wait_for_scan1(proc)

    def _wait_for_scan1(self, proc):
        """Poll until scan1 process exits, then auto-sync cart."""
        if proc.poll() is None:
            self.after(500, lambda: self._wait_for_scan1(proc))
        else:
            self._sync_scan1_cart()

    def _sync_scan1_cart(self):
        scan_file = os.path.join(os.path.dirname(__file__), "scan1_output.json")
        if not os.path.isfile(scan_file):
            messagebox.showinfo("Sync scan1", "No scan1 output found. Run scan1 and scan items first.")
            return
        try:
            with open(scan_file, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception as ex:
            messagebox.showerror("Sync scan1", f"Failed to read scan1 output: {ex}")
            return
        imported = 0
        for item in items:
            try:
                pid_str = str(item.get("code", item.get("id", "0")))
                qty = int(item.get("qty", 1))
            except Exception:
                continue
            if pid_str in PRODUCT_MAP:
                self.cart[pid_str] = self.cart.get(pid_str, 0) + qty
                imported += qty
        if imported:
            self._refresh_cart_ui()
            messagebox.showinfo("Sync scan1", f"Imported {imported} items from scan1.")
        else:
            messagebox.showinfo("Sync scan1", "No matching products found in current catalog.")

    def _build_catalog_section(self, parent):
        sec = tk.Frame(parent, bg=BG_PANEL)
        sec.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))
        sec.rowconfigure(0, weight=1)
        sec.columnconfigure(0, weight=1)
        inner = tk.Frame(sec, bg=BG_PANEL)
        inner.grid(row=0, column=0, sticky="nsew")
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(3, weight=1)
        _sec_header(inner, "🛍️  PRODUCT CATALOG", BG_PANEL)
        sf = tk.Frame(inner, bg=BG_INPUT, highlightbackground=BORDER_LT, highlightthickness=1)
        sf.pack(fill="x", pady=(4, 6))
        tk.Label(sf, text="🔍", bg=BG_INPUT, fg=TEXT_MUTED, font=self.fn_body).pack(side="left", padx=(6,2))
        self.cat_search = tk.Entry(sf, textvariable=self.search_var, font=self.fn_body,
                                    bg=BG_INPUT, fg=TEXT_MUTED, insertbackground=TEXT_WHITE,
                                    relief="flat", bd=0)
        self.cat_search.insert(0, "Search products...")
        self.cat_search.pack(fill="x", padx=2, pady=5)
        self.cat_search.bind("<FocusIn>",  self._cat_search_in)
        self.cat_search.bind("<FocusOut>", self._cat_search_out)
        self.search_var.trace_add("write", lambda *_: self._refresh_catalog())
        cf = tk.Frame(inner, bg=BG_PANEL)
        cf.pack(fill="x", pady=(0, 4))
        cat_icons = {"All":"","Dairy":"🥛","Drinks":"🥤","Grains":"🌾","Care":"💊","Snacks":"🍪"}
        self.cat_btns = {}
        for i, cat in enumerate(CATEGORIES):
            icon = cat_icons.get(cat, "")
            lbl  = f"{icon} {cat}".strip()
            b = tk.Label(cf, text=lbl, font=self.fn_cat,
                         bg=ACCENT if cat=="All" else TAG_BG, fg=TEXT_WHITE,
                         padx=8, pady=3, cursor="hand2")
            b.grid(row=i//3, column=i%3, padx=2, pady=2, sticky="ew")
            b.bind("<Button-1>", lambda e, c=cat: self._set_cat(c))
            self.cat_btns[cat] = b
        for col in range(3): cf.columnconfigure(col, weight=1)
        outer = tk.Frame(inner, bg=BG_PANEL)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(0, weight=1); outer.columnconfigure(0, weight=1)
        canvas = tk.Canvas(outer, bg=BG_PANEL, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        canvas.grid(row=0, column=0, sticky="nsew")
        self.cat_grid = tk.Frame(canvas, bg=BG_PANEL)
        self._cat_win = canvas.create_window((0,0), window=self.cat_grid, anchor="nw")
        self.cat_grid.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self._cat_win, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self._cat_canvas = canvas

    def _cat_search_in(self, e):
        if self._cat_placeholder:
            self.cat_search.delete(0, "end"); self.cat_search.config(fg=TEXT_WHITE)
            self._cat_placeholder = False

    def _cat_search_out(self, e):
        if not self.search_var.get().strip():
            self.cat_search.insert(0, "Search products..."); self.cat_search.config(fg=TEXT_MUTED)
            self._cat_placeholder = True

    def _set_cat(self, cat):
        self.active_cat.set(cat)
        for c, b in self.cat_btns.items():
            b.config(bg=ACCENT if c==cat else TAG_BG)
        self._refresh_catalog()

    def _filtered(self):
        cat   = self.active_cat.get()
        query = "" if self._cat_placeholder else self.search_var.get().strip().lower()
        return [p for p in PRODUCTS
                if (cat=="All" or p["cat"]==cat)
                and (not query or query in p["name"].lower() or query in str(p["id"]))]

    def _refresh_catalog(self):
        for w in self.cat_grid.winfo_children():
            w.destroy()
        cols = 2
        for i, prod in enumerate(self._filtered()):
            r, c = divmod(i, cols)
            card = self._mini_card(prod)
            card.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
        for c in range(cols):
            self.cat_grid.columnconfigure(c, weight=1, uniform="mc")

    def _mini_card(self, prod):
        pid = prod["id"]
        card = tk.Frame(self.cat_grid, bg=BG_CARD,
                        highlightbackground=BORDER, highlightthickness=1, cursor="hand2")
        tk.Label(card, text=prod["emoji"], font=self.fn_emoji_s, bg=BG_CARD).pack(pady=(8,2))
        name = prod["name"][:18] + ("…" if len(prod["name"])>18 else "")
        tk.Label(card, text=name, font=_mf("Segoe UI",8,"bold"),
                 bg=BG_CARD, fg=TEXT_WHITE, wraplength=110).pack(padx=4)
        tk.Label(card, text=f"₹{prod['price']:.0f}", font=_mf("Segoe UI",9,"bold"),
                 bg=BG_CARD, fg=TEXT_PRICE).pack()
        tk.Label(card, text=f"PID: {pid}", font=self.fn_small,
                 bg=BG_CARD, fg=TEXT_MUTED).pack(pady=(0,6))
        def click(e=None): self._open_qty_dialog(prod)
        def hin(e):  card.config(bg=BG_CARD_HOV, highlightbackground=ACCENT)
        def hout(e): card.config(bg=BG_CARD,     highlightbackground=BORDER)
        for w in card.winfo_children() + [card]:
            w.bind("<Button-1>", click)
            w.bind("<Enter>", hin)
            w.bind("<Leave>", hout)

        qt = tk.Button(card, text="QTY", font=self.fn_small,
                       bg=ACCENT2, fg="white", relief="flat", bd=0,
                       cursor="hand2", command=lambda p=prod: self._open_qty_dialog(p))
        qt.pack(pady=(4, 6))
        qt.bind("<Enter>", lambda e: qt.config(bg="#1f6d96"))
        qt.bind("<Leave>", lambda e: qt.config(bg=ACCENT2))
        return card

    def _build_center(self, parent):
        parent.rowconfigure(2, weight=1)
        parent.columnconfigure(0, weight=1)
        hdr = tk.Frame(parent, bg=BG_PANEL)
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        tk.Label(hdr, text="📋  LIVE CART BUFFER", font=self.fn_h2,
                 bg=BG_PANEL, fg=TEXT_WHITE).pack(side="left")
        self.lbl_item_count = tk.Label(hdr, text="0", font=self.fn_small,
                                        bg=ACCENT, fg=TEXT_WHITE, padx=6, pady=2)
        self.lbl_item_count.pack(side="left", padx=6)
        clear_btn = tk.Label(hdr, text="Clear All", font=self.fn_cat,
                             bg=RED, fg=TEXT_WHITE, padx=10, pady=4, cursor="hand2")
        clear_btn.pack(side="right")
        clear_btn.bind("<Button-1>", lambda e: self._clear_cart())
        tk.Frame(parent, bg=BORDER, height=1).grid(row=1, column=0, sticky="ew", padx=12)
        outer = tk.Frame(parent, bg=BG_PANEL)
        outer.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
        outer.rowconfigure(0, weight=1); outer.columnconfigure(0, weight=1)
        canvas = tk.Canvas(outer, bg=BG_PANEL, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        canvas.grid(row=0, column=0, sticky="nsew")
        self.cart_frame = tk.Frame(canvas, bg=BG_PANEL)
        self._cart_win  = canvas.create_window((0,0), window=self.cart_frame, anchor="nw")
        self.cart_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self._cart_win, width=e.width))
        self._cart_canvas = canvas

        bill_btn = tk.Label(parent, text="🧾   Generate Bill",
                            font=_mf("Segoe UI", 13, "bold"),
                            bg=GREEN, fg="#ffffff", pady=14, cursor="hand2")
        bill_btn.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))
        bill_btn.bind("<Button-1>", lambda e: self._generate_bill())
        bill_btn.bind("<Enter>", lambda e: bill_btn.config(bg="#16a34a"))
        bill_btn.bind("<Leave>", lambda e: bill_btn.config(bg=GREEN))

    def _generate_bill(self):
        """Invoke the bill summary window for self-checkout."""
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Add items to cart first")
            return
        # Ensure imports are present in the function scope or file scope
        from bill_summary import open_bill_summary
        open_bill_summary(self, self.cart, PRODUCT_MAP,
                          DISCOUNT_PCT, self.coupon_discount, HERE,
                          is_cashier=False)

    def _refresh_cart_ui(self):
        for w in self.cart_frame.winfo_children():
            w.destroy()
        if not self.cart:
            tk.Label(self.cart_frame,
                     text="Cart is empty\nScan or select a product to begin",
                     font=self.fn_body, bg=BG_PANEL, fg=TEXT_MUTED,
                     justify="center").pack(pady=60)
        else:
            for pid, qty in list(self.cart.items()):
                p = PRODUCT_MAP.get(pid)
                if p: self._cart_item_row(p, qty)
        self._cart_canvas.configure(scrollregion=self._cart_canvas.bbox("all"))
        self.lbl_item_count.config(text=str(sum(self.cart.values())))

    def _cart_item_row(self, prod, qty):
        pid = prod["id"]
        row = tk.Frame(self.cart_frame, bg=BG_CARD,
                       highlightbackground=BORDER, highlightthickness=1)
        row.pack(fill="x", padx=8, pady=4)
        row.columnconfigure(1, weight=1)
        tk.Label(row, text=prod["emoji"], font=self.fn_emoji_s,
                 bg=BG_CARD, width=4).grid(row=0, column=0, rowspan=2, padx=8, pady=8)
        tk.Label(row, text=prod["name"], font=self.fn_h3,
                 bg=BG_CARD, fg=TEXT_WHITE, anchor="w").grid(row=0, column=1, sticky="w", padx=4)
        tk.Label(row, text=f"PID: {pid}  ·  ₹{prod['price']:.2f}/unit",
                 font=self.fn_small, bg=BG_CARD, fg=TEXT_MUTED,
                 anchor="w").grid(row=1, column=1, sticky="w", padx=4)
        ctrl = tk.Frame(row, bg=BG_CARD)
        ctrl.grid(row=0, column=2, rowspan=2, padx=8, pady=6)
        minus = tk.Label(ctrl, text="−", font=self.fn_btn, bg=BTN_MINUS,
                          fg=TEXT_WHITE, width=3, pady=3, cursor="hand2")
        minus.pack(side="left")
        tk.Label(ctrl, text=str(qty), font=self.fn_h2,
                 bg=BG_CARD, fg=TEXT_WHITE, width=3).pack(side="left", padx=6)
        plus = tk.Label(ctrl, text="+", font=self.fn_btn, bg=BTN_PLUS_BG,
                         fg=TEXT_WHITE, width=3, pady=3, cursor="hand2")
        plus.pack(side="left")
        def on_minus(e=None):
            new = self.cart.get(pid, 1) - 1
            if new <= 0: self.cart.pop(pid, None)
            else: self.cart[pid] = new
            self._refresh_cart_ui()
        def on_plus(e=None):
            self.cart[pid] = self.cart.get(pid, 0) + 1
            self._refresh_cart_ui()
        minus.bind("<Button-1>", on_minus)
        plus.bind("<Button-1>",  on_plus)
        tk.Label(row, text=f"₹{prod['price']*qty:.2f}", font=self.fn_price,
                 bg=BG_CARD, fg=TEXT_PRICE).grid(row=0, column=3, rowspan=2, padx=12)
        del_btn = tk.Label(row, text="🗑", font=self.fn_body, bg=BG_CARD,
                            fg=TEXT_MUTED, cursor="hand2")
        del_btn.grid(row=0, column=4, rowspan=2, padx=(0, 10))
        del_btn.bind("<Button-1>", lambda e: (self.cart.pop(pid, None), self._refresh_cart_ui()))

    def _add_to_cart(self, pid, qty=1):
        pid = str(pid)
        if pid not in PRODUCT_MAP:
            self._flash_error(f"PID {pid} not found"); return

        prod = PRODUCT_MAP[pid]
        stock = prod.get("stock", 9999)
        if stock <= 0:
            messagebox.showwarning("Out of Stock", f"{prod['name']} is out of stock")
            return

        next_qty = self.cart.get(pid, 0) + qty
        if next_qty > stock:
            messagebox.showwarning("Stock limit", f"Only {stock} units available for {prod['name']}")
            return

        self.cart[pid] = next_qty
        prod["stock"] = stock - qty

        if inventory_threshold_alert(pid, prod["stock"], prod.get("reorder_threshold", 10)):
            messagebox.showinfo("Reorder Alert",
                                f"{prod['name']} stock is low ({prod['stock']} units).\n"
                                f"Auto reorder {prod.get('reorder_qty', 30)} units triggered.")
            prod["stock"] += prod.get("reorder_qty", 30)

        self._refresh_cart_ui()

    def _clear_cart(self):
        if self.cart and messagebox.askyesno("Clear Cart", "Remove all items?"):
            self.cart.clear(); self.coupon_discount = 0
            self._refresh_cart_ui()

    def _generate_bill(self):
        """Validate cart and open bill summary."""
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Add items to cart first.")
            return
        open_bill_summary(
            self, self.cart, PRODUCT_MAP,
            DISCOUNT_PCT, self.coupon_discount, HERE,
            0.0, None)

    def _open_qty_dialog(self, prod):
        pid     = prod["id"]
        current = self.cart.get(pid, 0)
        dlg = tk.Toplevel(self)
        dlg.title(f"Set Quantity — {prod['name']}")
        dlg.configure(bg=BG_DARK)
        dlg.resizable(False, False)
        dlg.grab_set()
        self.update_idletasks()
        x = self.winfo_x() + self.winfo_width()  // 2 - 175
        y = self.winfo_y() + self.winfo_height() // 2 - 140
        dlg.geometry(f"360x280+{x}+{y}")
        frm = tk.Frame(dlg, bg=BG_CARD, highlightbackground=ACCENT, highlightthickness=1)
        frm.pack(fill="both", expand=True, padx=18, pady=18)
        tk.Label(frm, text=prod["emoji"], font=self.fn_emoji, bg=BG_CARD).pack(pady=(14,2))
        tk.Label(frm, text=prod["name"],  font=self.fn_h2, bg=BG_CARD, fg=TEXT_WHITE).pack()
        tk.Label(frm, text=f"₹{prod['price']:.2f} / unit  ·  PID {pid}",
                 font=self.fn_small, bg=BG_CARD, fg=TEXT_PRICE).pack(pady=(2,12))
        val  = tk.IntVar(value=max(1, current))
        ctrl = tk.Frame(frm, bg=BG_CARD); ctrl.pack()
        tk.Label(ctrl, text="−", font=self.fn_btn, bg=BTN_MINUS,
                 fg=TEXT_WHITE, width=4, pady=6, cursor="hand2").grid(row=0,column=0,padx=4)
        ctrl.winfo_children()[-1].bind("<Button-1>", lambda e: val.set(max(0, val.get()-1)))
        tk.Spinbox(ctrl, textvariable=val, from_=0, to=9999, width=5,
                   font=self.fn_h2, justify="center", bg=BG_INPUT, fg=TEXT_WHITE,
                   buttonbackground=TAG_BG, insertbackground=TEXT_WHITE, relief="flat",
                   highlightbackground=BORDER_LT, highlightthickness=1).grid(row=0,column=1,padx=8,ipady=4)
        tk.Label(ctrl, text="+", font=self.fn_btn, bg=BTN_PLUS_BG,
                 fg=TEXT_WHITE, width=4, pady=6, cursor="hand2").grid(row=0,column=2,padx=4)
        ctrl.winfo_children()[-1].bind("<Button-1>", lambda e: val.set(val.get()+1))
        def confirm():
            try:    q = max(0, int(val.get()))
            except: q = 0
            pid_str = str(pid)
            if q > 0: self.cart[pid_str] = q
            else: self.cart.pop(pid_str, None)
            self._refresh_cart_ui(); dlg.destroy()
        tk.Label(frm, text="Add to Cart", font=self.fn_cat, bg=ACCENT,
                 fg=TEXT_WHITE, pady=10, cursor="hand2").pack(fill="x", padx=20, pady=(16,14))
        frm.winfo_children()[-1].bind("<Button-1>", lambda e: confirm())
        dlg.bind("<Return>", lambda e: confirm())

    def _on_key(self, event):
        ch = event.char
        if not ch or not ch.isprintable(): return
        if self.focus_get() in (self._pid_entry, self.cat_search): return
        if event.keysym == "Return":
            buf = self._scan_buffer.strip()
            self._scan_buffer = ""
            if self._scan_timer: self.after_cancel(self._scan_timer)
            if buf.isdigit(): self._add_to_cart(int(buf))
        else:
            self._scan_buffer += ch
            if self._scan_timer: self.after_cancel(self._scan_timer)
            self._scan_timer = self.after(500, self._clear_scan_buffer)

    def _clear_scan_buffer(self):
        self._scan_buffer = ""

    def _flash_error(self, msg):
        self.after(2500, lambda: None)

def _sec_header(parent, text, bg):
    tk.Label(parent, text=text, font=_mf("Segoe UI", 8, "bold"),
             bg=bg, fg="#64748b").pack(anchor="w", pady=(4,2))

if __name__ == "__main__":
    POSScreen().mainloop()