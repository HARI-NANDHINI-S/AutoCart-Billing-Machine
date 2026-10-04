import tkinter as tk
from tkinter import messagebox
import uuid
import subprocess
import os



PROJECT_PATH = r"C:\Users\ADMIN\Desktop\Module 1"
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


def validate_user():
    name = entry_name.get()
    phone = entry_phone.get()

    if name == "" or name == "Full name" or phone == "" or phone == "+91 00000 00000":
        messagebox.showerror("Error", "Please fill all fields")
        return

    input_file = os.path.join(PROJECT_PATH, "input.txt")
    result_file = os.path.join(PROJECT_PATH, "result.txt")

    # remove old result
    if os.path.exists(result_file):
        os.remove(result_file)

    # write input file
    try:
        with open(input_file, "w") as f:
            f.write(name + "\n")
            f.write(phone)
    except Exception as e:
        messagebox.showerror("Error", f"Could not write input file: {e}")
        return

    try:
        subprocess.run([
            DOSBOX_PATH,
            "-c", "mount c \"C:\\Users\\ADMIN\\Desktop\\Module 1\"",
            "-c", "c:",
            "-c", "validate.exe",
            "-c", "exit"
        ], check=True)

        root.after(1000, check_result)

    except Exception as e:
        messagebox.showerror("Error", f"DOSBox or validate.exe error: {e}")


def check_result():
    result_file = os.path.join(PROJECT_PATH, "result.txt")

    if not os.path.exists(result_file):
        messagebox.showerror("Error", "Result file not created. Validation failed.")
        return

    try:
        with open(result_file, "r") as f:
            result = f.read().strip()

        if result == "1":
            messagebox.showinfo("Success", "Validation Successful")
            start_btn.config(state="normal")
        else:
            messagebox.showerror("Error", "Invalid Name or Phone")
            start_btn.config(state="disabled")
    except Exception as e:
        messagebox.showerror("Error", f"Error reading result: {e}")

# ---------- START SESSION ----------

def start_session():
    name = entry_name.get()
    session_id = str(uuid.uuid4())[:8]

    messagebox.showinfo("Session Started", f"Welcome {name}\nSession ID: {session_id}")
    session_label.config(text=f"ACTIVE SESSION : {session_id}")

root = tk.Tk()
root.title("HyperMarket Pro | Enterprise POS")
root.geometry("900x700")
root.configure(bg=BG_DARK)

main_container = tk.Frame(root, bg=BG_DARK)
main_container.place(relx=0.5, rely=0.5, anchor="center")


card = tk.Frame(main_container, bg=CARD_BG, padx=50, pady=40,
                highlightbackground="#2e3750", highlightthickness=1)
card.pack()

tk.Label(card,
         text="< BACK TO HOME",
         font=("Arial", 9, "bold"),
         fg=TEXT_GRAY,
         bg=CARD_BG).pack(anchor="w", pady=(0, 20))

tk.Label(card,
         text="Customer\nOnboarding",
         font=("Impact", 32),
         fg="white",
         bg=CARD_BG,
         justify="left").pack(anchor="w")

tk.Label(card,
         text="Enter customer details to initialize billing session",
         font=("Arial", 10),
         fg=TEXT_GRAY,
         bg=CARD_BG).pack(anchor="w", pady=(5, 30))

# ---------- NAME ----------

tk.Label(card,
         text="CUSTOMER NAME",
         font=("Arial", 8, "bold"),
         fg=TEXT_GRAY,
         bg=CARD_BG).pack(anchor="w", pady=(10, 5))

entry_name = tk.Entry(card,
                      font=("Arial", 12),
                      fg=TEXT_GRAY,
                      bg=INPUT_BG,
                      relief="flat",
                      insertbackground='white') # Caret color

entry_name.insert(0, "Full name")
entry_name.bind('<FocusIn>', lambda x: on_entry_click(x, entry_name, "Full name"))
entry_name.bind('<FocusOut>', lambda x: on_focusout(x, entry_name, "Full name"))
entry_name.pack(fill="x", ipady=8)

# ---------- PHONE ----------

tk.Label(card,
         text="PHONE / MEMBERSHIP ID",
         font=("Arial", 8, "bold"),
         fg=TEXT_GRAY,
         bg=CARD_BG).pack(anchor="w", pady=(10, 5))

entry_phone = tk.Entry(card,
                       font=("Arial", 12),
                       fg=TEXT_GRAY,
                       bg=INPUT_BG,
                       relief="flat",
                       insertbackground='white')

entry_phone.insert(0, "+91 00000 00000")
entry_phone.bind('<FocusIn>', lambda x: on_entry_click(x, entry_phone, "+91 00000 00000"))
entry_phone.bind('<FocusOut>', lambda x: on_focusout(x, entry_phone, "+91 00000 00000"))
entry_phone.pack(fill="x", ipady=8)


# ---------- VALIDATE ----------

validate_btn = tk.Button(card,
                         text="Validate Details",
                         font=("Arial", 10, "bold"),
                         bg="#16a34a",
                         fg="white",
                         relief="flat",
                         cursor="hand2",
                         command=validate_user)

validate_btn.pack(fill="x", pady=(30, 10), ipady=10)


start_btn = tk.Button(card,
                      text="Initialize Session →",
                      font=("Arial", 12, "bold"),
                      bg="#16a34a",
                      fg="white",
                      relief="flat",
                      state="disabled",
                      cursor="hand2",
                      command=start_session)

start_btn.pack(fill="x", ipady=12)



session_label = tk.Label(main_container,
                         text="",
                         font=("Arial", 10, "bold"),
                         fg=ACCENT_PURPLE,
                         bg=BG_DARK)

session_label.pack(pady=20)

root.mainloop()
      
     
