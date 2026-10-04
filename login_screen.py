import tkinter as tk
from tkinter import messagebox
import uuid
import subprocess
import os

from pos_screen import POSScreen

PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))
DOSBOX_PATH = r"C:\Program Files (x86)\DOSBox-0.74-3\DOSBox.exe"

if not os.path.exists(PROJECT_PATH):
    os.makedirs(PROJECT_PATH)

BG_DARK = "#0a0b14"
CARD_BG = "#161b2c"
ACCENT_PURPLE = "#6366f1"
TEXT_GRAY = "#94a3b8"
INPUT_BG = "#1e293b"

def on_entry_click(event, entry, placeholder):
    if entry.get() == placeholder:
        entry.delete(0, "end")
        entry.config(fg='white')

def on_focusout(event, entry, placeholder):
    if entry.get() == '':
        entry.insert(0, placeholder)
        entry.config(fg=TEXT_GRAY)

def find_dosbox():
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

def run_validate_exe(dosbox_path):
    validate_exe = os.path.join(PROJECT_PATH, "validate.exe")
    if not os.path.isfile(validate_exe):
        return False, "Missing validate.exe in project directory."
    if not dosbox_path:
        return False, "DOSBox not found."

    input_file = os.path.join(PROJECT_PATH, "input.txt")
    result_file = os.path.join(PROJECT_PATH, "result.txt")

    # Remove old result
    if os.path.exists(result_file):
        os.remove(result_file)

    cmd = [
        dosbox_path,
        "-noconsole",
        "-c", f"mount c \"{PROJECT_PATH}\"",
        "-c", "c:",
        "-c", "validate.exe",
        "-c", "exit",
    ]

    try:
        subprocess.run(cmd, cwd=PROJECT_PATH, timeout=20, check=True)
        return True, "OK"
    except subprocess.CalledProcessError as e:
        return False, f"validate.exe failed: {e}"
    except subprocess.TimeoutExpired:
        return False, "DOSBox timed out while running validate.exe."
    except Exception as e:
        return False, str(e)

class LoginScreen(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HyperMarket Pro | Self Checkout - Login")
        self.geometry("700x560")
        self._center_window(700, 560)
        self.configure(bg=BG_DARK)
        self.resizable(False, False)

        self.logged_in = False
        self.session_id = None

        self._build_ui()

    def _center_window(self, width, height):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        main_container = tk.Frame(self, bg=BG_DARK)
        main_container.place(relx=0.5, rely=0.5, anchor="center")

        card = tk.Frame(main_container, bg=CARD_BG, padx=50, pady=40,
                        highlightbackground="#2e3750", highlightthickness=1)
        card.pack()

        #tk.Label(card, text="< BACK TO MODE SELECT", font=("Arial", 9, "bold"), fg=TEXT_GRAY, bg=CARD_BG).pack(anchor="w", pady=(0, 20))

        tk.Label(card, text="Customer\nOnboarding", font=("Impact", 32), fg="white", bg=CARD_BG, justify="left").pack(anchor="w")

        tk.Label(card, text="Enter customer details to initialize billing session", font=("Arial", 10), fg=TEXT_GRAY, bg=CARD_BG).pack(anchor="w", pady=(5, 30))

        # Name
        tk.Label(card, text="CUSTOMER NAME", font=("Arial", 8, "bold"), fg=TEXT_GRAY, bg=CARD_BG).pack(anchor="w", pady=(10, 5))

        self.entry_name = tk.Entry(card, font=("Arial", 12), fg=TEXT_GRAY, bg=INPUT_BG, relief="flat", insertbackground='white')
        self.entry_name.insert(0, "Full name")
        self.entry_name.bind('<FocusIn>', lambda x: on_entry_click(x, self.entry_name, "Full name"))
        self.entry_name.bind('<FocusOut>', lambda x: on_focusout(x, self.entry_name, "Full name"))
        self.entry_name.pack(fill="x", ipady=8)

        # Phone
        tk.Label(card, text="PHONE / MEMBERSHIP ID", font=("Arial", 8, "bold"), fg=TEXT_GRAY, bg=CARD_BG).pack(anchor="w", pady=(10, 5))

        self.entry_phone = tk.Entry(card, font=("Arial", 12), fg=TEXT_GRAY, bg=INPUT_BG, relief="flat", insertbackground='white')
        self.entry_phone.insert(0, "+91 00000 00000")
        self.entry_phone.bind('<FocusIn>', lambda x: on_entry_click(x, self.entry_phone, "+91 00000 00000"))
        self.entry_phone.bind('<FocusOut>', lambda x: on_focusout(x, self.entry_phone, "+91 00000 00000"))
        self.entry_phone.pack(fill="x", ipady=8)

        # Validate
        self.validate_btn = tk.Button(card, text="Validate Details", font=("Arial", 10, "bold"), bg="#16a34a", fg="white", relief="flat", cursor="hand2", command=self.validate_user)
        self.validate_btn.pack(fill="x", pady=(30, 10), ipady=10)

        self.start_btn = tk.Button(card, text="Initialize Session →", font=("Arial", 12, "bold"), bg="#16a34a", fg="white", relief="flat",  cursor="hand2", command=self.start_session)
        self.start_btn.pack(fill="x", ipady=12)

        self.session_label = tk.Label(main_container, text="", font=("Arial", 10, "bold"), fg=ACCENT_PURPLE, bg=BG_DARK)
        self.session_label.pack(pady=20)

    def validate_user(self):
        name = self.entry_name.get()
        phone = self.entry_phone.get()

        if name == "" or name == "Full name" or phone == "" or phone == "+91 00000 00000":
            messagebox.showerror("Error", "Please fill all fields")
            return

        input_file = os.path.join(PROJECT_PATH, "input.txt")
        result_file = os.path.join(PROJECT_PATH, "result.txt")

        try:
            with open(input_file, "w") as f:
                f.write(name + "\n")
                f.write(phone)
        except Exception as e:
            messagebox.showerror("Error", f"Could not write input file: {e}")
            return

        self.validate_btn.config(state="disabled", text="Validating...")
        dosbox = find_dosbox()
        ok, msg = run_validate_exe(dosbox)
        if not ok:
            messagebox.showerror("Error", f"Validation failed: {msg}")
            self.validate_btn.config(state="normal", text="Validate Details")
            return

        self.after(1000, self.check_result)

    def check_result(self):
        result_file = os.path.join(PROJECT_PATH, "result.txt")

        if not os.path.exists(result_file):
            messagebox.showerror("Error", "Result file not created. Validation failed.")
            self.validate_btn.config(state="normal", text="Validate Details")
            return

        try:
            with open(result_file, "r") as f:
                result = f.read().strip()

            if result == "1":
                messagebox.showinfo("Success", "Validation Successful")
                self.start_btn.config(state="normal")
                self.validate_btn.config(state="normal", text="Validate Details")
            else:
                messagebox.showerror("Error", "Invalid Name or Phone")
                self.start_btn.config(state="disabled")
                self.validate_btn.config(state="normal", text="Validate Details")
        except Exception as e:
            messagebox.showerror("Error", f"Error reading result: {e}")
            self.validate_btn.config(state="normal", text="Validate Details")

    def start_session(self):
        name = self.entry_name.get()
        self.session_id = str(uuid.uuid4())[:8]

        messagebox.showinfo("Session Started", f"Welcome {name}\nSession ID: {self.session_id}")
        self.session_label.config(text=f"ACTIVE SESSION : {self.session_id}")

        self.destroy()
        POSScreen().mainloop()

if __name__ == "__main__":
    LoginScreen().mainloop()
