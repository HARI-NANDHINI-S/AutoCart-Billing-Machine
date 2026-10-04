import tkinter as tk
from tkinter import messagebox
import os

# Import screens
from login_screen import LoginScreen
from cashier_screen import CashierScreen

class ModeSelect(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HyperMarket Pro | Mode Selection")
        self.geometry("600x400")
        self._center_window(600, 400)
        self.configure(bg="#0a0b14")
        self.resizable(False, False)

        self._build_ui()

    def _center_window(self, width, height):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        frame = tk.Frame(self, bg="#1a2235", padx=40, pady=40)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="Smart Billing Machine", font=("Impact", 32), fg="white", bg="#1a2235").pack(pady=(0, 20))

        tk.Label(frame, text="Select Checkout Mode", font=("Arial", 16), fg="#94a3b8", bg="#1a2235").pack(pady=(0, 30))

        btn_self = tk.Button(frame, text="Self Checkout", font=("Arial", 14, "bold"), bg="#6366f1", fg="white", relief="flat", cursor="hand2", command=self._self_checkout)
        btn_self.pack(fill="x", pady=(0, 10), ipady=10)

        btn_cashier = tk.Button(frame, text="Cashier Checkout", font=("Arial", 14, "bold"), bg="#16a34a", fg="white", relief="flat", cursor="hand2", command=self._cashier_checkout)
        btn_cashier.pack(fill="x", pady=(0, 10), ipady=10)

      #  tk.Label(frame, text="Powered by EMU 8086 + Python", font=("Arial", 10), fg="#64748b", bg="#1a2235").pack(pady=(20, 0))

    def _self_checkout(self):
        self.destroy()
        LoginScreen().mainloop()

    def _cashier_checkout(self):
        """Show cashier authentication dialog before opening CashierScreen."""
        VALID_CREDENTIALS = {
            "CASHIER01": "1234",
            "ADMIN": "0000",
            "MANAGER": "9999",
        }

        dlg = tk.Toplevel(self)
        dlg.title("Cashier Authentication")
        dlg.geometry("420x340")
        dlg.configure(bg="#0a0b14")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self)

        self.update_idletasks()
        x = self.winfo_x() + self.winfo_width() // 2 - 210
        y = self.winfo_y() + self.winfo_height() // 2 - 170
        dlg.geometry(f"420x340+{x}+{y}")

        card = tk.Frame(dlg, bg="#1a2235", padx=30, pady=24,
                        highlightbackground="#2e3750", highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="🔐 Cashier Login", font=("Impact", 24), fg="white", bg="#1a2235").pack(pady=(0, 14))

        tk.Label(card, text="EMPLOYEE ID", font=("Arial", 8, "bold"), fg="#94a3b8", bg="#1a2235").pack(anchor="w")
        emp_entry = tk.Entry(card, font=("Arial", 12), bg="#1e293b", fg="white",
                             insertbackground="white", relief="flat")
        emp_entry.pack(fill="x", ipady=6, pady=(0, 8))
        emp_entry.focus_set()

        tk.Label(card, text="PIN", font=("Arial", 8, "bold"), fg="#94a3b8", bg="#1a2235").pack(anchor="w")
        pin_entry = tk.Entry(card, font=("Arial", 12), bg="#1e293b", fg="white",
                             insertbackground="white", relief="flat", show="●")
        pin_entry.pack(fill="x", ipady=6, pady=(0, 8))

        status_lbl = tk.Label(card, text="", font=("Arial", 9), fg="#ef4444", bg="#1a2235")
        status_lbl.pack(pady=(0, 6))

        def attempt_login(event=None):
            emp_id = emp_entry.get().strip().upper()
            pin = pin_entry.get().strip()
            if emp_id in VALID_CREDENTIALS and VALID_CREDENTIALS[emp_id] == pin:
                dlg.destroy()
                self.destroy()
                CashierScreen(cashier_name=emp_id).mainloop()
            else:
                status_lbl.config(text="❌ Invalid Employee ID or PIN")
                pin_entry.delete(0, "end")

        tk.Button(card, text="Authenticate →", font=("Arial", 12, "bold"),
                  bg="#16a34a", fg="white", relief="flat", cursor="hand2",
                  command=attempt_login).pack(fill="x", ipady=8)
        pin_entry.bind("<Return>", attempt_login)

if __name__ == "__main__":
    ModeSelect().mainloop()
