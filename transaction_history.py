"""
transaction_history.py — Transaction Logger & Sales Dashboard
Persistent transaction log with analytics for HyperMarket Pro.
"""

import os
import json
import csv
import time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

HERE = os.path.dirname(os.path.abspath(__file__))
TRANSACTIONS_FILE = os.path.join(HERE, "transactions.json")

# ─── PALETTE ──────────────────────────────────────────────────────────────────
BG_DEEP   = "#02070f"
BG_PANEL  = "#060d1a"
BG_CARD   = "#0a1628"
BG_CARD2  = "#0d1f3c"
ACCENT_C  = "#00d4ff"
ACCENT_G  = "#00ff88"
ACCENT_Y  = "#ffd700"
ACCENT_R  = "#ff4444"
ACCENT_P  = "#a855f7"
TEXT_PRI  = "#e8f4ff"
TEXT_SEC  = "#7eb8d4"
TEXT_MUT  = "#3a5a7a"
BORDER    = "#1e3a5f"

FONT_HERO  = ("Consolas", 22, "bold")
FONT_MED   = ("Consolas", 16, "bold")
FONT_BODY  = ("Consolas", 12)
FONT_SMALL = ("Consolas", 10)
FONT_TINY  = ("Consolas", 8)


# ═══════════════════════════════════════════════════════════════════════════════
#  Transaction Logger
# ═══════════════════════════════════════════════════════════════════════════════
class TransactionLogger:
    """Logs every completed transaction to a JSON file."""

    def __init__(self, filepath=None):
        self.filepath = filepath or TRANSACTIONS_FILE
        self._transactions = self._load()

    def _load(self):
        if os.path.isfile(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._transactions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[TxnLog] Save error: {e}")

    def log_transaction(self, cart, product_map, results, disc_pct, gst_pct,
                         manual_discount=0.0, session_id=None, payment_method=None,
                         loyalty_points_earned=0, loyalty_points_redeemed=0):
        """Log a completed transaction with full details."""
        items = []
        for pid, qty in cart.items():
            p = product_map.get(pid)
            if not p:
                continue
            items.append({
                "pid": pid if isinstance(pid, int) else str(pid),
                "name": p.get("name", "Unknown"),
                "price": p.get("price", 0),
                "qty": qty,
                "subtotal": p.get("price", 0) * qty,
                "gst_pct": p.get("gst", 18),
                "category": p.get("cat", "Other"),
            })

        txn = {
            "txn_id": f"TXN{int(time.time())}",
            "session_id": session_id or "N/A",
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "items": items,
            "item_count": len(items),
            "unit_count": sum(i["qty"] for i in items),
            "subtotal_paise": results.get("subtotal", 0),
            "discount_paise": results.get("discount", 0),
            "gst_paise": results.get("gst", 0),
            "coupon_paise": results.get("coupon", 0),
            "grand_total_paise": results.get("grand", 0),
            "discount_pct": disc_pct,
            "gst_pct_avg": gst_pct,
            "manual_discount": manual_discount,
            "payment_method": payment_method or "Unknown",
            "loyalty_points_earned": loyalty_points_earned,
            "loyalty_points_redeemed": loyalty_points_redeemed,
            "source": results.get("source", "Python"),
        }

        self._transactions.append(txn)
        self._save()
        return txn["txn_id"]

    def get_all(self):
        return self._transactions

    def get_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return [t for t in self._transactions if t.get("date") == today]

    def get_by_date(self, date_str):
        """date_str in YYYY-MM-DD format."""
        return [t for t in self._transactions if t.get("date") == date_str]

    def get_stats(self, transactions=None):
        """Compute aggregate statistics from a list of transactions."""
        txns = transactions if transactions is not None else self._transactions
        if not txns:
            return {
                "total_revenue": 0, "total_items": 0, "total_units": 0,
                "avg_bill": 0, "total_gst": 0, "total_discount": 0,
                "top_products": [], "category_breakdown": {},
                "hourly_sales": {}, "txn_count": 0,
            }

        total_revenue = sum(t.get("grand_total_paise", 0) for t in txns) / 100.0
        total_items = sum(t.get("item_count", 0) for t in txns)
        total_units = sum(t.get("unit_count", 0) for t in txns)
        total_gst = sum(t.get("gst_paise", 0) for t in txns) / 100.0
        total_discount = sum(t.get("discount_paise", 0) for t in txns) / 100.0
        avg_bill = total_revenue / len(txns) if txns else 0

        # Top products
        prod_count = {}
        cat_count = {}
        for t in txns:
            for item in t.get("items", []):
                name = item.get("name", "Unknown")
                prod_count[name] = prod_count.get(name, 0) + item.get("qty", 0)
                cat = item.get("category", "Other")
                cat_count[cat] = cat_count.get(cat, 0) + item.get("subtotal", 0)

        top_products = sorted(prod_count.items(), key=lambda x: x[1], reverse=True)[:5]

        # Hourly sales
        hourly = {}
        for t in txns:
            hour = t.get("time", "00:00:00")[:2]
            hourly[hour] = hourly.get(hour, 0) + t.get("grand_total_paise", 0) / 100.0

        return {
            "total_revenue": total_revenue,
            "total_items": total_items,
            "total_units": total_units,
            "avg_bill": avg_bill,
            "total_gst": total_gst,
            "total_discount": total_discount,
            "top_products": top_products,
            "category_breakdown": cat_count,
            "hourly_sales": hourly,
            "txn_count": len(txns),
        }

    def export_csv(self, filepath):
        """Export all transactions to a CSV file."""
        if not self._transactions:
            return False
        fields = ["txn_id", "date", "time", "item_count", "unit_count",
                  "subtotal_paise", "discount_paise", "gst_paise", "coupon_paise",
                  "grand_total_paise", "payment_method", "session_id"]
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                for t in self._transactions:
                    writer.writerow(t)
            return True
        except Exception as e:
            print(f"[TxnLog] CSV export error: {e}")
            return False


# ─── Singleton ────────────────────────────────────────────────────────────────
_logger = None

def get_transaction_logger():
    global _logger
    if _logger is None:
        _logger = TransactionLogger()
    return _logger


# ═══════════════════════════════════════════════════════════════════════════════
#  Sales Dashboard Window
# ═══════════════════════════════════════════════════════════════════════════════
class SalesDashboard(tk.Toplevel):
    """Enterprise Sales Analytics Dashboard."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("📊 Sales Dashboard  ·  HyperMarket Pro")
        self.geometry("950x720")
        self._center_window(950, 720)
        self.configure(bg=BG_DEEP)
        self.resizable(False, False)
        self.grab_set()

        self.logger = get_transaction_logger()
        self._view_mode = "today"  # "today" or "all"

        self._build_ui()
        self._refresh_data()

    def _center_window(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # ─── Header ───
        hdr = tk.Frame(self, bg=BG_PANEL, height=70)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="📊 SALES DASHBOARD", font=FONT_HERO,
                 bg=BG_PANEL, fg=ACCENT_C).pack(side="left", padx=20, pady=14)

        # View toggles
        btn_frame = tk.Frame(hdr, bg=BG_PANEL)
        btn_frame.pack(side="right", padx=20)

        self.btn_today = tk.Button(btn_frame, text="TODAY", font=FONT_TINY,
                                    bg=ACCENT_C, fg=BG_DEEP, relief="flat",
                                    cursor="hand2", command=lambda: self._set_view("today"))
        self.btn_today.pack(side="left", padx=2)

        self.btn_all = tk.Button(btn_frame, text="ALL TIME", font=FONT_TINY,
                                  bg=BG_CARD, fg=TEXT_SEC, relief="flat",
                                  cursor="hand2", command=lambda: self._set_view("all"))
        self.btn_all.pack(side="left", padx=2)

        tk.Button(btn_frame, text="📤 EXPORT CSV", font=FONT_TINY,
                  bg=ACCENT_Y, fg=BG_DEEP, relief="flat",
                  cursor="hand2", command=self._export_csv).pack(side="left", padx=(10, 0))

        tk.Frame(self, bg=ACCENT_C, height=2).pack(fill="x")

        # ─── Content ───
        self.content = tk.Frame(self, bg=BG_DEEP)
        self.content.pack(fill="both", expand=True, padx=16, pady=12)

    def _set_view(self, mode):
        self._view_mode = mode
        if mode == "today":
            self.btn_today.config(bg=ACCENT_C, fg=BG_DEEP)
            self.btn_all.config(bg=BG_CARD, fg=TEXT_SEC)
        else:
            self.btn_today.config(bg=BG_CARD, fg=TEXT_SEC)
            self.btn_all.config(bg=ACCENT_C, fg=BG_DEEP)
        self._refresh_data()

    def _refresh_data(self):
        for w in self.content.winfo_children():
            w.destroy()

        if self._view_mode == "today":
            txns = self.logger.get_today()
            period_label = f"Today · {datetime.now().strftime('%d %b %Y')}"
        else:
            txns = self.logger.get_all()
            period_label = "All Time"

        stats = self.logger.get_stats(txns)

        # ─── Stats Cards Row ───
        stats_row = tk.Frame(self.content, bg=BG_DEEP)
        stats_row.pack(fill="x", pady=(0, 12))
        for i in range(5):
            stats_row.columnconfigure(i, weight=1)

        cards_data = [
            ("TRANSACTIONS", str(stats["txn_count"]), ACCENT_C),
            ("REVENUE", f"₹{stats['total_revenue']:,.0f}", ACCENT_G),
            ("AVG BILL", f"₹{stats['avg_bill']:,.0f}", ACCENT_Y),
            ("GST COLLECTED", f"₹{stats['total_gst']:,.0f}", ACCENT_P),
            ("DISCOUNTS", f"₹{stats['total_discount']:,.0f}", ACCENT_R),
        ]

        for i, (label, value, color) in enumerate(cards_data):
            card = tk.Frame(stats_row, bg=BG_CARD, highlightbackground=color,
                           highlightthickness=1, padx=12, pady=10)
            card.grid(row=0, column=i, padx=4, sticky="nsew")
            tk.Label(card, text=value, font=("Consolas", 18, "bold"),
                     bg=BG_CARD, fg=color).pack()
            tk.Label(card, text=label, font=FONT_TINY,
                     bg=BG_CARD, fg=TEXT_MUT).pack()

        # ─── Period Label ───
        tk.Label(self.content, text=f"📅 {period_label}  ·  {stats['total_units']} units sold",
                 font=FONT_SMALL, bg=BG_DEEP, fg=TEXT_SEC).pack(anchor="w", pady=(0, 8))

        # ─── Two columns: Top Products + Category Breakdown ───
        mid = tk.Frame(self.content, bg=BG_DEEP)
        mid.pack(fill="x", pady=(0, 12))
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)

        # Top Products
        tp_frame = tk.Frame(mid, bg=BG_CARD, highlightbackground=BORDER,
                            highlightthickness=1, padx=14, pady=10)
        tp_frame.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        tk.Label(tp_frame, text="🏆 TOP 5 PRODUCTS", font=("Consolas", 10, "bold"),
                 bg=BG_CARD, fg=ACCENT_Y).pack(anchor="w", pady=(0, 8))

        if stats["top_products"]:
            max_qty = max(q for _, q in stats["top_products"]) if stats["top_products"] else 1
            for rank, (name, qty) in enumerate(stats["top_products"], 1):
                row_f = tk.Frame(tp_frame, bg=BG_CARD)
                row_f.pack(fill="x", pady=2)
                tk.Label(row_f, text=f"#{rank}", font=("Consolas", 9, "bold"),
                         bg=BG_CARD, fg=ACCENT_C, width=3).pack(side="left")
                tk.Label(row_f, text=name[:20], font=("Consolas", 9),
                         bg=BG_CARD, fg=TEXT_PRI, anchor="w", width=20).pack(side="left", padx=(4, 8))

                # Progress bar visual
                bar_frame = tk.Frame(row_f, bg=BG_DEEP, height=14)
                bar_frame.pack(side="left", fill="x", expand=True, padx=(0, 4))
                bar_width = max(10, int((qty / max_qty) * 150))
                bar = tk.Frame(bar_frame, bg=ACCENT_G, height=12, width=bar_width)
                bar.place(x=0, y=1, height=12)
                bar_frame.config(width=160, height=14)

                tk.Label(row_f, text=f"{qty}", font=("Consolas", 9, "bold"),
                         bg=BG_CARD, fg=ACCENT_G, width=5).pack(side="right")
        else:
            tk.Label(tp_frame, text="No sales data yet", font=FONT_SMALL,
                     bg=BG_CARD, fg=TEXT_MUT).pack(pady=20)

        # Category Breakdown
        cat_frame = tk.Frame(mid, bg=BG_CARD, highlightbackground=BORDER,
                             highlightthickness=1, padx=14, pady=10)
        cat_frame.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

        tk.Label(cat_frame, text="📦 CATEGORY REVENUE", font=("Consolas", 10, "bold"),
                 bg=BG_CARD, fg=ACCENT_P).pack(anchor="w", pady=(0, 8))

        cat_colors = {"Dairy": "#4fc3f7", "Drinks": "#81c784", "Grains": "#ffb74d",
                      "Care": "#ce93d8", "Snacks": "#ff8a65", "Other": "#90a4ae"}

        if stats["category_breakdown"]:
            total_cat = sum(stats["category_breakdown"].values()) or 1
            for cat, amount in sorted(stats["category_breakdown"].items(),
                                       key=lambda x: x[1], reverse=True):
                pct = (amount / total_cat) * 100
                row_f = tk.Frame(cat_frame, bg=BG_CARD)
                row_f.pack(fill="x", pady=2)
                color = cat_colors.get(cat, "#90a4ae")
                tk.Label(row_f, text="●", font=("Consolas", 10),
                         bg=BG_CARD, fg=color).pack(side="left")
                tk.Label(row_f, text=f"{cat}", font=("Consolas", 9),
                         bg=BG_CARD, fg=TEXT_PRI, width=10, anchor="w").pack(side="left", padx=4)
                tk.Label(row_f, text=f"₹{amount:,.0f}", font=("Consolas", 9, "bold"),
                         bg=BG_CARD, fg=color, width=10).pack(side="left")
                tk.Label(row_f, text=f"({pct:.0f}%)", font=("Consolas", 8),
                         bg=BG_CARD, fg=TEXT_MUT).pack(side="left", padx=4)
        else:
            tk.Label(cat_frame, text="No sales data yet", font=FONT_SMALL,
                     bg=BG_CARD, fg=TEXT_MUT).pack(pady=20)

        # ─── Hourly Sales Chart ───
        hour_frame = tk.Frame(self.content, bg=BG_CARD, highlightbackground=BORDER,
                              highlightthickness=1, padx=14, pady=10)
        hour_frame.pack(fill="x", pady=(0, 12))

        tk.Label(hour_frame, text="📈 HOURLY SALES", font=("Consolas", 10, "bold"),
                 bg=BG_CARD, fg=ACCENT_C).pack(anchor="w", pady=(0, 6))

        chart_canvas = tk.Canvas(hour_frame, bg=BG_CARD, height=80, highlightthickness=0)
        chart_canvas.pack(fill="x")

        hourly = stats["hourly_sales"]
        if hourly:
            max_val = max(hourly.values()) or 1
            bar_w = 30
            gap = 6
            total_w = len(hourly) * (bar_w + gap)
            start_x = 10
            for i, (hour, val) in enumerate(sorted(hourly.items())):
                x = start_x + i * (bar_w + gap)
                bar_h = max(4, int((val / max_val) * 55))
                y = 65 - bar_h
                chart_canvas.create_rectangle(x, y, x + bar_w, 65,
                                               fill=ACCENT_C, outline="")
                chart_canvas.create_text(x + bar_w // 2, 74, text=f"{hour}h",
                                         fill=TEXT_MUT, font=("Consolas", 7))
                chart_canvas.create_text(x + bar_w // 2, y - 8,
                                         text=f"₹{val:.0f}",
                                         fill=ACCENT_G, font=("Consolas", 7))
        else:
            chart_canvas.create_text(400, 40, text="No hourly data available",
                                     fill=TEXT_MUT, font=FONT_SMALL)

        # ─── Recent Transactions Table ───
        txn_frame = tk.Frame(self.content, bg=BG_CARD, highlightbackground=BORDER,
                             highlightthickness=1, padx=10, pady=8)
        txn_frame.pack(fill="both", expand=True)

        tk.Label(txn_frame, text="🧾 RECENT TRANSACTIONS", font=("Consolas", 10, "bold"),
                 bg=BG_CARD, fg=ACCENT_G).pack(anchor="w", pady=(0, 6))

        cols = ("TXN ID", "TIME", "ITEMS", "TOTAL", "METHOD")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dash.Treeview",
                        background=BG_CARD, foreground=TEXT_PRI,
                        rowheight=28, fieldbackground=BG_CARD,
                        font=("Consolas", 9), borderwidth=0)
        style.configure("Dash.Treeview.Heading",
                        background=BG_PANEL, foreground=ACCENT_C,
                        font=("Consolas", 9, "bold"), relief="flat")
        style.map("Dash.Treeview",
                  background=[("selected", ACCENT_P)],
                  foreground=[("selected", "white")])

        tree = ttk.Treeview(txn_frame, columns=cols, show="headings",
                            style="Dash.Treeview", height=6)
        widths = {"TXN ID": 140, "TIME": 100, "ITEMS": 80, "TOTAL": 120, "METHOD": 100}
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="center", width=widths.get(c, 100))

        scrollbar = ttk.Scrollbar(txn_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Populate (most recent first)
        for t in reversed(txns[-50:]):
            tree.insert("", "end", values=(
                t.get("txn_id", ""),
                t.get("time", ""),
                t.get("unit_count", 0),
                f"₹{t.get('grand_total_paise', 0) / 100:,.2f}",
                t.get("payment_method", "N/A"),
            ))

    def _export_csv(self):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
            initialdir=desktop,
            initialfile=f"HyperMarket_Sales_{datetime.now().strftime('%Y%m%d')}.csv",
            title="Export Sales Data")
        if filepath:
            ok = self.logger.export_csv(filepath)
            if ok:
                messagebox.showinfo("Export", f"Sales data exported to:\n{os.path.basename(filepath)}")
            else:
                messagebox.showerror("Export", "No transaction data to export.")


# ─── Test / Demo ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Demo: create sample transactions and show dashboard
    logger = get_transaction_logger()

    # Sample data
    SAMPLE_MAP = {
        101: {"name": "Amul Butter 500g", "price": 255.0, "cat": "Dairy", "gst": 5},
        102: {"name": "Coke 2L Combo Pack", "price": 95.0, "cat": "Drinks", "gst": 12},
        104: {"name": "Basmati Rice 5kg", "price": 750.0, "cat": "Grains", "gst": 5},
        108: {"name": "Surf Excel 1kg", "price": 220.0, "cat": "Care", "gst": 18},
        130: {"name": "Maggi Noodles 4-Pack", "price": 60.0, "cat": "Snacks", "gst": 12},
    }
    sample_cart = {101: 2, 102: 3, 104: 1, 130: 4}
    sample_results = {"subtotal": 103500, "discount": 10350, "gst": 16767,
                      "coupon": 0, "grand": 109917, "source": "Python"}

    logger.log_transaction(sample_cart, SAMPLE_MAP, sample_results,
                           10, 18, payment_method="Cash")

    root = tk.Tk()
    root.withdraw()
    SalesDashboard(root)
    root.mainloop()
