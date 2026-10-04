import tkinter as tk
from tkinter import ttk, messagebox
import os, json, uuid, random, time, sys, subprocess, threading
from datetime import datetime
from asm_utils import calculate_weight_price, inventory_threshold_alert
from products import PRODUCTS, PRODUCT_MAP
# ─── CONFIG ───────────────────────────────────────────────────────────────────
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
# Config
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

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
ACCENT    = ACCENT_C
ACCENT2   = ACCENT_P
TEXT_PRI   = "#e8f4ff"
TEXT_SEC   = "#7eb8d4"
TEXT_MUT   = "#3a5a7a"

FONT_HERO  = ("Consolas", 22, "bold")
FONT_MED   = ("Consolas", 16, "bold")
FONT_BODY  = ("Consolas", 12)
FONT_SMALL = ("Consolas", 10)

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

# ─── MAIN APP ─────────────────────────────────────────────────────────────────
class CashierScreen(tk.Tk):
    def __init__(self, cashier_name="Cashier"):
        super().__init__()
        self.title("CASHIER POS  ·  HyperStore International")
        self.geometry("1200x800")
        self._center_window(1200, 800)
        self.resizable(False, False)
        self.configure(bg=BG_DEEP)

        self.session_id = str(uuid.uuid4())[:8]
        self.cashier_name = cashier_name
        self.cart = {}
        self.discount_pct = 0.0
        self.manual_discount = 0.0
        self.override_id_var = tk.StringVar()
        self.override_price_var = tk.StringVar()
        self.discount_var = tk.StringVar()
        self.fixed_discount_var = tk.StringVar()

        self._build_layout()
        self._refresh_catalog()

    def _center_window(self, width, height):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_layout(self):
        # Header
        hdr = tk.Frame(self, bg=BG_PANEL, height=80)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="◈ CASHIER POS", font=("Consolas", 28, "bold"),
                 bg=BG_PANEL, fg=ACCENT_Y).pack(side="left", padx=20, pady=20)
        tk.Label(hdr, text=f"Session: {self.session_id}",
                 font=("Consolas", 12), bg=BG_PANEL, fg=TEXT_MUT).pack(side="right", padx=20)

        # Sales Dashboard button
        dash_btn = tk.Button(hdr, text="📊 SALES DASHBOARD", font=("Consolas", 10, "bold"),
                             bg=ACCENT_C, fg=BG_DEEP, relief="flat", bd=0,
                             cursor="hand2", command=self._open_dashboard)
        dash_btn.pack(side="right", padx=10, pady=20)
        dash_btn.bind("<Enter>", lambda e: dash_btn.config(bg="#00a8cc"))
        dash_btn.bind("<Leave>", lambda e: dash_btn.config(bg=ACCENT_C))

        # ─── INPUT OPTIONS ────────────────────────────────────────────────────
        opt_frame = tk.Frame(self, bg=BG_CARD2, height=70)
        opt_frame.pack(fill="x", padx=10, pady=8)
        opt_frame.pack_propagate(False)

        tk.Label(opt_frame, text="ADD PRODUCTS:", font=("Consolas", 10, "bold"),
                 bg=BG_CARD2, fg=TEXT_SEC).pack(side="left", padx=12, pady=10)

        # Scan button
        btn1 = tk.Button(opt_frame, text="📱 SCAN PRODUCT", font=FONT_SMALL,
                         bg=ACCENT_P, fg=BG_DEEP, relief="flat", bd=0,
                         cursor="hand2", command=self._mode_scan)
        btn1.pack(side="left", padx=4)
        btn1.bind("<Enter>", lambda e: btn1.config(bg="#8b5cf6"))
        btn1.bind("<Leave>", lambda e: btn1.config(bg=ACCENT_P))

        # Enter ID button
        btn2 = tk.Button(opt_frame, text="⌨ ENTER PRODUCT ID", font=FONT_SMALL,
                         bg=ACCENT_C, fg=BG_DEEP, relief="flat", bd=0,
                         cursor="hand2", command=self._mode_enter_id)
        btn2.pack(side="left", padx=4)
        btn2.bind("<Enter>", lambda e: btn2.config(bg="#00a8cc"))
        btn2.bind("<Leave>", lambda e: btn2.config(bg=ACCENT_C))

        # Browse Catalog button
        btn3 = tk.Button(opt_frame, text="📦 BROWSE CATALOG", font=FONT_SMALL,
                         bg=ACCENT_G, fg=BG_DEEP, relief="flat", bd=0,
                         cursor="hand2", command=self._mode_browse)
        btn3.pack(side="left", padx=4)
        btn3.bind("<Enter>", lambda e: btn3.config(bg="#00dd55"))
        btn3.bind("<Leave>", lambda e: btn3.config(bg=ACCENT_G))

        # Main content
        main = tk.Frame(self, bg=BG_DEEP)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: Input/Catalog area
        left = tk.Frame(main, bg=BG_DEEP, width=600)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        left.pack_propagate(False)

        # Search + Catalog section
        search_bar = tk.Frame(left, bg=BG_CARD2, padx=12, pady=10)
        search_bar.pack(fill="x", pady=(0, 10))
        tk.Label(search_bar, text="Search catalog:", font=FONT_BODY,
                 bg=BG_CARD2, fg=TEXT_MUT).pack(anchor="w")
        self.search_var = tk.StringVar()
        self._search_entry = tk.Entry(search_bar, textvariable=self.search_var,
                                     font=("Consolas", 12), bg=BG_CARD, fg=TEXT_PRI,
                                     insertbackground=TEXT_PRI, relief="flat", bd=2)
        self._search_entry.pack(fill="x", pady=(8, 0), ipady=8)
        self.search_var.trace_add("write", lambda *_: self._refresh_catalog())

        tk.Label(left, text="PRODUCT CATALOG", font=FONT_MED,
                 bg=BG_DEEP, fg=ACCENT_C).pack(pady=(0, 10))
        catalog_outer = tk.Frame(left, bg=BG_CARD, padx=10, pady=10)
        catalog_outer.pack(fill="both", expand=True)
        catalog_outer.grid_rowconfigure(0, weight=1)
        catalog_outer.grid_columnconfigure(0, weight=1)

        self.catalog_canvas = tk.Canvas(catalog_outer, bg=BG_CARD, highlightthickness=0)
        self.catalog_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(catalog_outer, orient="vertical", command=self.catalog_canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.catalog_canvas.configure(yscrollcommand=scrollbar.set)

        self.catalog_inner = tk.Frame(self.catalog_canvas, bg=BG_CARD)
        self.catalog_canvas.create_window((0, 0), window=self.catalog_inner, anchor="nw")
        self.catalog_inner.bind(
            "<Configure>",
            lambda e: self.catalog_canvas.configure(scrollregion=self.catalog_canvas.bbox("all"))
        )

        # Right: Cart and controls
        right = tk.Frame(main, bg=BG_DEEP, width=550)
        right.pack(side="right", fill="both", expand=True)
        right.pack_propagate(False)

        # Cart
        cart_hdr = tk.Frame(right, bg=BG_PANEL, height=40)
        cart_hdr.pack(fill="x")
        tk.Label(cart_hdr, text="🛒 SHOPPING CART", font=FONT_MED,
                 bg=BG_PANEL, fg=ACCENT_G).pack(side="left", padx=10)
        tk.Button(cart_hdr, text="🗑 CLEAR", font=FONT_SMALL, bg=BG_PANEL, fg=ACCENT_R,
                  activebackground=ACCENT_R, activeforeground=BG_DEEP,
                  relief="flat", bd=0, cursor="hand2",
                  command=self._clear_cart).pack(side="right", padx=10)

        self.cart_frame = tk.Frame(right, bg=BG_CARD, padx=10, pady=10)
        self.cart_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Controls
        ctrl = tk.Frame(right, bg=BG_DEEP)
        ctrl.pack(fill="x")

        # ── Price Override ──
        ovr_frame = tk.Frame(ctrl, bg=BG_CARD2, padx=8, pady=6)
        ovr_frame.pack(fill="x", pady=(4, 0))
        tk.Label(ovr_frame, text="PRICE OVERRIDE", font=FONT_SMALL,
                 bg=BG_CARD2, fg=TEXT_SEC).pack(anchor="w")
        ovr_row = tk.Frame(ovr_frame, bg=BG_CARD2)
        ovr_row.pack(fill="x", pady=2)
        tk.Entry(ovr_row, textvariable=self.override_id_var,
                 font=("Consolas", 10), bg=BG_CARD, fg=TEXT_PRI,
                 insertbackground=TEXT_PRI, relief="flat", width=8).pack(side="left", padx=(0, 4))
        tk.Entry(ovr_row, textvariable=self.override_price_var,
                 font=("Consolas", 10), bg=BG_CARD, fg=TEXT_PRI,
                 insertbackground=TEXT_PRI, relief="flat", width=8).pack(side="left", padx=(0, 4))
        tk.Button(ovr_row, text="SET", font=("Consolas", 9, "bold"),
                  bg=ACCENT_P, fg=BG_DEEP, relief="flat", bd=0,
                  cursor="hand2", command=self._apply_override).pack(side="left")

        # ── Discount Controls ──
        disc_frame = tk.Frame(ctrl, bg=BG_CARD2, padx=8, pady=6)
        disc_frame.pack(fill="x", pady=(4, 0))
        tk.Label(disc_frame, text="DISCOUNTS", font=FONT_SMALL,
                 bg=BG_CARD2, fg=TEXT_SEC).pack(anchor="w")
        disc_row = tk.Frame(disc_frame, bg=BG_CARD2)
        disc_row.pack(fill="x", pady=2)
        tk.Entry(disc_row, textvariable=self.discount_var,
                 font=("Consolas", 10), bg=BG_CARD, fg=TEXT_PRI,
                 insertbackground=TEXT_PRI, relief="flat", width=6).pack(side="left", padx=(0, 2))
        tk.Button(disc_row, text="% OFF", font=("Consolas", 9, "bold"),
                  bg=ACCENT_C, fg=BG_DEEP, relief="flat", bd=0,
                  cursor="hand2", command=self._apply_discount_pct).pack(side="left", padx=(0, 6))
        tk.Entry(disc_row, textvariable=self.fixed_discount_var,
                 font=("Consolas", 10), bg=BG_CARD, fg=TEXT_PRI,
                 insertbackground=TEXT_PRI, relief="flat", width=6).pack(side="left", padx=(0, 2))
        tk.Button(disc_row, text="₹ OFF", font=("Consolas", 9, "bold"),
                  bg=ACCENT_Y, fg=BG_DEEP, relief="flat", bd=0,
                  cursor="hand2", command=self._apply_fixed_discount).pack(side="left")

        # Bill button
        neon_btn(ctrl, "📄  GENERATE BILL", ACCENT_G,
                 self._generate_bill, width=28, pady_val=10).pack(pady=(8, 0), fill="x")

    def _mode_scan(self):
        """Launch scanner and auto-sync scanned items to main cart on close."""
        self._launch_scan1()

    def _launch_scan1(self):
        scan1_path = os.path.join(os.path.dirname(__file__), "scan1.py")
        if not os.path.isfile(scan1_path):
            messagebox.showerror("Scanner Missing", "scan1.py not found in project folder")
            return
        # Use simpler threading logic for cashier screen
        proc = subprocess.Popen([sys.executable, scan1_path], cwd=os.path.dirname(__file__))
        def poll():
            if proc.poll() is None:
                self.after(500, poll)
            else:
                self._sync_scan1_cart()
        self.after(500, poll)

    def _sync_scan1_cart(self):
        """Read scan1_output.json and merge into main cashier cart."""
        scan_file = os.path.join(os.path.dirname(__file__), "scan1_output.json")
        if not os.path.isfile(scan_file):
            return
        try:
            with open(scan_file, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            return
        imported = 0
        for item in items:
            try:
                # Support both 'code' and 'id' fields from scan1_output.json
                pid_raw = item.get("code", item.get("id"))
                if pid_raw is None: continue
                pid = str(pid_raw).strip()
                qty = int(item.get("qty", 1))
            except Exception:
                continue
            if pid in PRODUCT_MAP:
                self._add_to_cart(pid, qty)
                imported += qty
        if imported:
            self._refresh_cart()
            messagebox.showinfo("Scanner Sync", f"✔ Imported {imported} item(s) from scanner into cart")
        else:
            messagebox.showwarning("Scanner Sync", "No matching products found in current catalog. Please check your scan data.")
        # Clean up the scan file
        try:
            os.remove(scan_file)
        except Exception:
            pass

    def _add_to_cart(self, pid, qty=1):
        if pid not in PRODUCT_MAP:
            messagebox.showerror("Add item", "Product code not held in catalog")
            return
        prod = PRODUCT_MAP[pid]
        stock = prod.get("stock", 999)
        if stock <= 0:
            messagebox.showwarning("Out of stock", f"{prod['name']} is unavailable")
            return
        self.cart.setdefault(pid, {"qty": 0, "price": prod["price"]})
        self.cart[pid]["qty"] += qty
        prod["stock"] = max(0, stock - qty)
        if inventory_threshold_alert(pid, prod["stock"], prod.get("reorder_threshold", 10)):
            messagebox.showinfo("Reorder Alert",
                                f"{prod['name']} stock is low ({prod['stock']} left). Auto-reordering {prod.get('reorder_qty', 20)} units.")
            prod["stock"] += prod.get("reorder_qty", 20)
        self._refresh_cart()

    def _add_by_id(self, pid):
        if pid not in PRODUCT_MAP:
            messagebox.showerror("Invalid ID", f"Product ID '{pid}' not found in catalog")
            return
        self._add_to_cart(pid)


    def _refresh_catalog(self):
        for w in self.catalog_inner.winfo_children():
            w.destroy()
        query = self.search_var.get().strip().lower() if hasattr(self, 'search_var') else ""
        for pid, prod in PRODUCT_MAP.items():
            if query and query not in prod['name'].lower() and query not in str(pid):
                continue
            pf = tk.Frame(self.catalog_inner, bg=BG_CARD, padx=8, pady=8)
            pf.pack(fill="x", pady=2)
            info = tk.Frame(pf, bg=BG_CARD)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=f"{pid}", font=("Consolas", 10, "bold"),
                     bg=BG_CARD, fg=ACCENT_C).pack(anchor="w")
            tk.Label(info, text=prod['name'], font=FONT_BODY,
                     bg=BG_CARD, fg=TEXT_PRI, wraplength=340, justify="left").pack(anchor="w")
            tk.Label(info, text=f"₹{prod['price']:.2f}", font=FONT_BODY,
                     bg=BG_CARD, fg=ACCENT_Y).pack(anchor="w", pady=(4, 0))
            actions = tk.Frame(pf, bg=BG_CARD)
            actions.pack(side="right")
            tk.Button(actions, text="QTY", font=("Consolas", 10, "bold"),
                      bg=ACCENT2, fg=BG_DEEP, width=6,
                      relief="flat", bd=0, cursor="hand2",
                      command=lambda p=pid: self._open_qty_dialog(p)).pack(side="right", padx=(0, 8))
            tk.Button(actions, text="+", font=("Consolas", 14, "bold"),
                      bg=ACCENT_C, fg=BG_DEEP, width=3,
                      relief="flat", bd=0, cursor="hand2",
                      command=lambda p=pid: self._add_to_cart(p)).pack(side="right")

    def _open_qty_dialog(self, pid):
        if pid not in PRODUCT_MAP:
            messagebox.showerror("Quantity", "Unknown product")
            return
        prod = PRODUCT_MAP[pid]
        dlg = tk.Toplevel(self)
        dlg.title(f"QTY — {prod['name']}")
        dlg.configure(bg=BG_CARD)
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.geometry("380x280")

        self.update_idletasks()
        dlg.geometry(f"+{self.winfo_x() + self.winfo_width() // 2 - 190}"
                     f"+{self.winfo_y() + self.winfo_height() // 2 - 140}")

        tk.Label(dlg, text=f"{prod['name']}", font=FONT_MED,
                 bg=BG_CARD, fg=TEXT_PRI).pack(pady=(18, 2))
        tk.Label(dlg, text=f"₹{prod['price']:.2f} each", font=FONT_BODY,
                 bg=BG_CARD, fg=ACCENT_Y).pack(pady=(0, 14))

        tk.Label(dlg, text="SELECT QUANTITY", font=(FONT_SMALL[0], 9, "bold"),
                 bg=BG_CARD, fg=ACCENT_C).pack()

        qty_var = tk.IntVar(value=1)
        row = tk.Frame(dlg, bg=BG_CARD)
        row.pack(pady=10)

        def dec():
            if qty_var.get() > 1: qty_var.set(qty_var.get() - 1)
            update_total()
        def inc():
            if qty_var.get() < 99: qty_var.set(qty_var.get() + 1)
            update_total()

        tk.Button(row, text=" − ", font=("Consolas", 18, "bold"), bg=BG_PANEL, fg=ACCENT_R,
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
                  command=dec).pack(side="left", padx=6)
        tk.Label(row, textvariable=qty_var, font=("Consolas", 24, "bold"),
                 bg=BG_PANEL, fg=TEXT_PRI, width=4, anchor="center",
                 padx=8, pady=4).pack(side="left", padx=4)
        tk.Button(row, text=" + ", font=("Consolas", 18, "bold"), bg=BG_PANEL, fg=ACCENT_G,
                  relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
                  command=inc).pack(side="left", padx=6)

        total_lbl = tk.Label(dlg, text=f"Total: ₹{prod['price']:.2f}",
                             font=("Consolas", 12, "bold"), bg=BG_CARD, fg=ACCENT_G)
        total_lbl.pack()

        def update_total():
            total_lbl.config(text=f"Total: ₹{prod['price'] * qty_var.get():.2f}")

        def confirm():
            self._add_to_cart(pid, qty_var.get())
            dlg.destroy()

        tk.Button(dlg, text="  ADD TO CART  ✔", font=("Consolas", 12, "bold"),
                  bg=ACCENT_G, fg=BG_DEEP, relief="flat", bd=0,
                  padx=18, pady=10, cursor="hand2",
                  command=confirm).pack(pady=(12, 0))

    def _refresh_cart(self):
        for w in self.cart_frame.winfo_children():
            w.destroy()
        total = 0
        for pid, item in self.cart.items():
            if item["qty"] == 0:
                continue
            cf = tk.Frame(self.cart_frame, bg=BG_CARD, padx=8, pady=4)
            cf.pack(fill="x", pady=1)
            tk.Label(cf, text=f"{PRODUCT_MAP[pid]['name']} (x{item['qty']})",
                     font=FONT_BODY, bg=BG_CARD, fg=TEXT_PRI).pack(side="left")
            price = item["price"] * item["qty"]
            tk.Label(cf, text=f"₹{price}",
                     font=FONT_BODY, bg=BG_CARD, fg=ACCENT_Y).pack(side="right")
            tk.Button(cf, text="−", font=("Consolas", 12, "bold"),
                      bg=ACCENT_R, fg=BG_DEEP, width=2,
                      relief="flat", bd=0, cursor="hand2",
                      command=lambda p=pid: self._remove_from_cart(p)).pack(side="right", padx=(5, 0))
            total += price
        # Discounts
        if self.discount_pct > 0:
            disc_amt = total * (self.discount_pct / 100)
            total -= disc_amt
            df = tk.Frame(self.cart_frame, bg=BG_CARD2, padx=8, pady=4)
            df.pack(fill="x", pady=1)
            tk.Label(df, text=f"Discount ({self.discount_pct}%)",
                     font=FONT_BODY, bg=BG_CARD2, fg=ACCENT_R).pack(side="left")
            tk.Label(df, text=f"-₹{disc_amt:.2f}",
                     font=FONT_BODY, bg=BG_CARD2, fg=ACCENT_R).pack(side="right")
        if self.manual_discount > 0:
            total -= self.manual_discount
            mf = tk.Frame(self.cart_frame, bg=BG_CARD2, padx=8, pady=4)
            mf.pack(fill="x", pady=1)
            tk.Label(mf, text="Manual Discount",
                     font=FONT_BODY, bg=BG_CARD2, fg=ACCENT_R).pack(side="left")
            tk.Label(mf, text=f"-₹{self.manual_discount:.2f}",
                     font=FONT_BODY, bg=BG_CARD2, fg=ACCENT_R).pack(side="right")
        # Total
        tf = tk.Frame(self.cart_frame, bg=BG_PANEL, padx=8, pady=6)
        tf.pack(fill="x", pady=(5, 0))
        tk.Label(tf, text="TOTAL", font=FONT_MED,
                 bg=BG_PANEL, fg=ACCENT_G).pack(side="left")
        tk.Label(tf, text=f"₹{total:.2f}",
                 font=FONT_MED, bg=BG_PANEL, fg=ACCENT_G).pack(side="right")

        # ─── GENERATE BILL / PAY BUTTON ───
        gb_btn = tk.Button(self.cart_frame, text="🧾   GENERATE BILL / PAY",
                           font=("Consolas", 13, "bold"),
                           bg=ACCENT_G, fg=BG_DEEP, relief="flat", bd=0,
                           pady=15, cursor="hand2", command=self._generate_bill)
        gb_btn.pack(fill="x", pady=(15, 5))
        gb_btn.bind("<Enter>", lambda e: gb_btn.config(bg="#00dd55"))
        gb_btn.bind("<Leave>", lambda e: gb_btn.config(bg=ACCENT_G))

    def _remove_from_cart(self, pid):
        if pid in self.cart and self.cart[pid]["qty"] > 0:
            self.cart[pid]["qty"] -= 1
            if self.cart[pid]["qty"] == 0:
                del self.cart[pid]
        self._refresh_cart()

    def _clear_cart(self):
        self.cart = {}
        self.discount_pct = 0.0
        self.manual_discount = 0.0
        self._refresh_cart()

    def _apply_override(self):
        pid = self.override_id_var.get().strip()
        try:
            new_price = float(self.override_price_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid price")
            return
        if pid not in PRODUCT_MAP:
            messagebox.showerror("Error", "Product ID not found")
            return
        if pid in self.cart:
            self.cart[pid]["price"] = new_price
        self.override_id_var.set("")
        self.override_price_var.set("")
        self._refresh_cart()
        messagebox.showinfo("Success", f"Price for {PRODUCT_MAP[pid]['name']} overridden to ₹{new_price}")

    def _apply_discount_pct(self):
        try:
            pct = float(self.discount_var.get().strip())
            if pct < 0 or pct > 100:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid discount percentage (0-100)")
            return
        self.discount_pct = pct
        self.discount_var.set("")
        self._refresh_cart()

    def _apply_fixed_discount(self):
        try:
            amt = float(self.fixed_discount_var.get().strip())
            if amt < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid fixed discount amount")
            return
        self.manual_discount = amt
        self.fixed_discount_var.set("")
        self._refresh_cart()

    def _open_dashboard(self):
        """Open the Sales Analytics Dashboard."""
        from transaction_history import SalesDashboard
        SalesDashboard(self)

    def _generate_bill(self):
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Add items to cart first")
            return
        cart_snapshot = {pid: item["qty"] for pid, item in self.cart.items()}
        from bill_summary import open_bill_summary
        folder = os.path.dirname(os.path.abspath(__file__))
        open_bill_summary(self, cart_snapshot, PRODUCT_MAP, self.discount_pct, 0.0, folder,
                          self.manual_discount, self.session_id, is_cashier=True)

    def _mode_enter_id(self):
        """Allow manual ID entry in a popup dialog."""
        dlg = tk.Toplevel(self)
        dlg.title("Enter Product ID")
        dlg.geometry("320x180")
        dlg.configure(bg=BG_CARD)
        dlg.grab_set()
        dlg.resizable(False, False)
        
        self.update_idletasks()
        dlg.geometry(f"+{self.winfo_x() + self.winfo_width()//2 - 160}+{self.winfo_y() + self.winfo_height()//2 - 90}")

        tk.Label(dlg, text="ID ENTRY", font=FONT_SMALL, bg=BG_CARD, fg=ACCENT_C).pack(pady=(20, 10))
        entry = tk.Entry(dlg, font=FONT_MED, bg=BG_DEEP, fg=TEXT_PRI, insertbackground=TEXT_PRI, relief="flat", justify="center")
        entry.pack(padx=20, pady=5, ipady=5, fill="x")
        entry.focus_set()

        def confirm(e=None):
            pid = entry.get().strip()
            if pid in PRODUCT_MAP:
                self._add_to_cart(pid)
                dlg.destroy()
            else:
                messagebox.showerror("Error", f"Product ID '{pid}' not found", parent=dlg)

        tk.Button(dlg, text="ADD TO CART", font=FONT_SMALL, bg=ACCENT_G, fg=BG_DEEP, relief="flat", command=confirm).pack(pady=15)
        entry.bind("<Return>", confirm)

    def _mode_browse(self):
        """Focus the search bar for browsing."""
        if hasattr(self, '_search_entry'):
            self._search_entry.focus_set()
            self.search_var.set("") # Clear search
        else:
            # If reference not saved, just keep it as is
            pass

if __name__ == "__main__":
    CashierScreen().mainloop()