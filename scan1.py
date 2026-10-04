import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import pytesseract
import re
import time
import math
import os
import json

SCAN1_OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "scan1_output.json")

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─── Product database (matches cashier_screen PRODUCT_MAP keys) ───────────────
product_database = {
    "101": ("Amul Butter 500g", 255), "102": ("Coke 2L Combo Pack", 95),
    "103": ("Tide Detergent 2kg", 440), "104": ("Basmati Rice 5kg", 750),
    "105": ("Britannia Biscuits 400g", 60), "106": ("Amul Milk 1L", 58),
    "107": ("Parle-G 800g", 45), "108": ("Surf Excel 1kg", 220),
    "109": ("Chakki Atta 5kg", 280), "110": ("Frooti 1L Pack", 80),
    "111": ("Paneer 200g", 120), "112": ("Lays Classic 100g", 30),
    "113": ("Amul Dahi 500g", 55), "114": ("Thums Up 2L", 95),
    "115": ("Colgate Total 150g", 99), "116": ("Toor Dal 1kg", 140),
    "117": ("Kurkure Masala 90g", 25), "118": ("Nescafe Classic 100g", 280),
    "119": ("Dove Soap 100g", 55), "120": ("Moong Dal 500g", 70),
    "121": ("Hide & Seek 100g", 40), "122": ("Real Juice Orange 1L", 120),
    "123": ("Head & Shoulders 340ml", 350), "124": ("Poha 500g", 45),
    "125": ("Good Day Cashew 120g", 35), "126": ("Amul Ghee 500ml", 295),
    "127": ("Sprite 750ml", 45), "128": ("Dettol Handwash 250ml", 85),
    "129": ("Chana Dal 1kg", 125), "130": ("Maggi Noodles 4-Pack", 60),
    "131": ("Amul Cheese Slices 200g", 155), "132": ("Maaza Mango 600ml", 45),
    "133": ("Lifebuoy Soap 4-Pack", 88), "134": ("Rajma Red 500g", 95),
    "135": ("Bingo Mad Angles 130g", 35), "136": ("Amul Lassi 200ml", 25),
    "137": ("Red Bull 250ml", 125), "138": ("Ariel Pods 12-Pack", 320),
    "139": ("Quinoa 500g", 280), "140": ("Oreo Original 300g", 90),
}

# ─── PALETTE ──────────────────────────────────────────────────────────────────
BG           = "#0b0f1a"
BG_CARD      = "#111827"
BG_PANEL     = "#0d1526"
ACCENT       = "#00c6ff"
ACCENT2      = "#7c3aed"
GREEN        = "#00e676"
RED          = "#ff4d6d"
ORANGE       = "#ff9f43"
YELLOW       = "#ffd93d"
TXT          = "#e2e8f0"
TXT_MUTED    = "#475569"
BORDER       = "#1e3a5f"

cap            = None
camera_running = False
frame          = None
scanned_items  = []  # list of dicts: {code, name, price, qty}


def export_cart_to_json():
    """Export scanned items to JSON for cashier sync."""
    try:
        with open(SCAN1_OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(scanned_items, f, indent=2)
    except Exception:
        pass


def start_camera():
    global cap, camera_running
    cap = cv2.VideoCapture(0)
    camera_running = True
    set_status("LIVE  ·  Hold product code inside the scan frame", GREEN)
    start_btn.config(state="disabled", bg=BG_PANEL, fg=TXT_MUTED)
    stop_btn.config(state="normal",   bg=ACCENT,   fg=BG)
    show_camera()


def show_camera():
    global frame
    if not camera_running:
        return
    ret, frame = cap.read()
    if not ret:
        window.after(10, show_camera)
        return

    h, w, _ = frame.shape
    bw, bh = 320, 160
    sx = (w - bw) // 2;  sy = (h - bh) // 2
    ex = sx + bw;        ey = sy + bh

    # dark overlay outside scan box
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.rectangle(overlay, (sx, sy), (ex, ey), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.42, frame, 0.58, 0, frame)

    # animated scan line
    bar_y = sy + int(bh * ((time.time() % 1.4) / 1.4))
    cv2.line(frame, (sx + 6, bar_y), (ex - 6, bar_y), (0, 198, 255), 1)

    # corner brackets
    col = (0, 198, 255); ln, th = 34, 4
    for ox, oy, dx, dy in [(sx, sy, 1, 1), (ex, sy, -1, 1), (sx, ey, 1, -1), (ex, ey, -1, -1)]:
        cv2.line(frame, (ox, oy), (ox + dx * ln, oy), col, th)
        cv2.line(frame, (ox, oy), (ox, oy + dy * ln), col, th)

    cv2.rectangle(frame, (sx, sy), (ex, ey), (255, 255, 255), 1)
    cv2.putText(frame, "SCAN CODE HERE", (sx, sy - 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 198, 255), 2)

    rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img   = Image.fromarray(rgb)
    imgtk = ImageTk.PhotoImage(img)
    cam_label.imgtk = imgtk
    cam_label.configure(image=imgtk)
    window.after(10, show_camera)


def stop_camera():
    global cap, camera_running
    camera_running = False
    if cap:
        cap.release(); cap = None
    start_btn.config(state="normal",   bg=ACCENT2, fg="white")
    stop_btn.config(state="disabled",  bg=BG_PANEL, fg=TXT_MUTED)
    set_status("Processing captured frame…", ACCENT)
    detect_and_add(frame)


def detect_and_add(image):
    if image is None:
        set_status("No frame captured — try again", RED)
        return

    h, w, _ = image.shape
    bw, bh = 320, 160
    sx = (w - bw) // 2; sy = (h - bh) // 2
    roi  = image[sy:sy + bh, sx:sx + bw]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    txt  = pytesseract.image_to_string(gray, config='--psm 6')
    nums = re.findall(r'\d+', txt)

    if nums:
        code = nums[0]
        if code in product_database:
            name, price = product_database[code]
            set_status(f"✔  Detected: {name} (Code: {code})", GREEN)
            ask_quantity_and_add(code, name, price)
        else:
            set_status(f"Code '{code}' not found in database", RED)
    else:
        set_status("No code detected — adjust lighting and try again", RED)


# ═══════════════════════════════════════════════════════════════════════════════
#  QUANTITY DIALOG — asks qty, adds to scanned items, updates log
# ═══════════════════════════════════════════════════════════════════════════════
def ask_quantity_and_add(code, name, price):
    """Pop up quantity dialog, then add to scanned_items list."""
    dlg = tk.Toplevel(window)
    dlg.title("")
    dlg.resizable(False, False)
    dlg.configure(bg=BG_CARD)
    dlg.grab_set()
    dlg.geometry("420x320")
    window.update_idletasks()
    dlg.geometry(f"+{window.winfo_x() + window.winfo_width() // 2 - 210}"
                 f"+{window.winfo_y() + window.winfo_height() // 2 - 160}")

    tk.Frame(dlg, bg=ACCENT, height=3).pack(fill="x")

    tk.Label(dlg, text="PRODUCT DETECTED ✔",
             font=("Consolas", 14, "bold"), bg=BG_CARD, fg=GREEN).pack(pady=(18, 4))
    tk.Label(dlg, text=f"{name}  (Code: {code})  —  ₹{price}",
             font=("Consolas", 10), bg=BG_CARD, fg=TXT_MUTED).pack(pady=(0, 16))

    tk.Label(dlg, text="SELECT QUANTITY",
             font=("Consolas", 12, "bold"), bg=BG_CARD, fg=ACCENT).pack(pady=(0, 8))

    qty_var = tk.IntVar(value=1)
    row = tk.Frame(dlg, bg=BG_CARD)
    row.pack()

    def dec():
        if qty_var.get() > 1:
            qty_var.set(qty_var.get() - 1)

    def inc():
        if qty_var.get() < 99:
            qty_var.set(qty_var.get() + 1)

    tk.Button(row, text=" − ", font=("Consolas", 18, "bold"), bg=BG_PANEL, fg=RED,
              relief="flat", bd=0, padx=16, pady=8, cursor="hand2",
              activebackground=BG_PANEL, activeforeground=RED,
              highlightthickness=1, highlightbackground=BORDER,
              command=dec).grid(row=0, column=0, padx=8)

    tk.Label(row, textvariable=qty_var, font=("Consolas", 26, "bold"),
             bg=BG_PANEL, fg=TXT, width=4, anchor="center",
             highlightthickness=1, highlightbackground=BORDER,
             padx=8, pady=6).grid(row=0, column=1, padx=4)

    tk.Button(row, text=" + ", font=("Consolas", 18, "bold"), bg=BG_PANEL, fg=GREEN,
              relief="flat", bd=0, padx=16, pady=8, cursor="hand2",
              activebackground=BG_PANEL, activeforeground=GREEN,
              highlightthickness=1, highlightbackground=BORDER,
              command=inc).grid(row=0, column=2, padx=8)

    tk.Frame(dlg, bg=BORDER, height=1).pack(fill="x", padx=30, pady=16)

    def confirm():
        qty = qty_var.get()
        # Check if already in scanned_items
        found = False
        for item in scanned_items:
            if item["code"] == code:
                item["qty"] += qty
                found = True
                break
        if not found:
            scanned_items.append({"code": code, "name": name, "price": price, "qty": qty})

        export_cart_to_json()
        refresh_scanned_log()
        dlg.destroy()
        set_status(f"✔  Added {qty} × {name} to cart", GREEN)
        prompt_scan_more()

    tk.Button(dlg, text="  ADD TO CART  ✔",
              font=("Consolas", 12, "bold"), bg=GREEN, fg=BG,
              relief="flat", bd=0, padx=18, pady=10, cursor="hand2",
              activebackground="#00c853", activeforeground=BG,
              command=confirm).pack()


def prompt_scan_more():
    """Ask if user wants to scan another product or finish."""
    dlg = tk.Toplevel(window)
    dlg.title("")
    dlg.resizable(False, False)
    dlg.configure(bg=BG_CARD)
    dlg.grab_set()
    dlg.geometry("440x220")
    window.update_idletasks()
    dlg.geometry(f"+{window.winfo_x() + window.winfo_width() // 2 - 220}"
                 f"+{window.winfo_y() + window.winfo_height() // 2 - 110}")

    tk.Frame(dlg, bg=GREEN, height=3).pack(fill="x")

    tk.Label(dlg, text="✔  ITEM ADDED TO CART",
             font=("Consolas", 14, "bold"), bg=BG_CARD, fg=GREEN).pack(pady=(20, 4))

    total = sum(i["price"] * i["qty"] for i in scanned_items)
    count = sum(i["qty"] for i in scanned_items)
    tk.Label(dlg, text=f"{count} item(s) scanned  ·  ₹{total}",
             font=("Consolas", 10), bg=BG_CARD, fg=TXT_MUTED).pack(pady=(0, 14))

    tk.Label(dlg, text="Scan another product?",
             font=("Consolas", 12, "bold"), bg=BG_CARD, fg=TXT).pack(pady=(0, 12))

    bf = tk.Frame(dlg, bg=BG_CARD)
    bf.pack()

    def on_yes():
        dlg.destroy()
        cam_label.configure(bg=BG)
        start_camera()

    def on_done():
        dlg.destroy()
        set_status(f"Scanning complete — {count} item(s) ready for cashier", ACCENT)

    tk.Button(bf, text="  📷  SCAN MORE  ", font=("Consolas", 11, "bold"),
              bg=ACCENT2, fg="white", relief="flat", bd=0,
              activebackground="#6d28d9", padx=16, pady=10,
              cursor="hand2", command=on_yes).grid(row=0, column=0, padx=12)

    tk.Button(bf, text="  ✔  DONE  ", font=("Consolas", 11, "bold"),
              bg=GREEN, fg=BG, relief="flat", bd=0,
              activebackground="#00c853", padx=16, pady=10,
              cursor="hand2", command=on_done).grid(row=0, column=1, padx=12)


def refresh_scanned_log():
    """Update the scanned items log display."""
    for w in log_frame.winfo_children():
        w.destroy()
    if not scanned_items:
        tk.Label(log_frame, text="No items scanned yet",
                 font=("Consolas", 9), bg=BG_CARD, fg=TXT_MUTED).pack(pady=4)
        return
    for item in scanned_items:
        row = tk.Frame(log_frame, bg=BG_CARD)
        row.pack(fill="x", padx=6, pady=1)
        tk.Label(row, text=f"  {item['code']}", font=("Consolas", 9, "bold"),
                 bg=BG_CARD, fg=ACCENT, width=5, anchor="w").pack(side="left")
        tk.Label(row, text=item["name"][:22], font=("Consolas", 9),
                 bg=BG_CARD, fg=TXT, anchor="w").pack(side="left", padx=(4, 0))
        tk.Label(row, text=f"×{item['qty']}", font=("Consolas", 9, "bold"),
                 bg=BG_CARD, fg=YELLOW).pack(side="right", padx=(4, 6))
        tk.Label(row, text=f"₹{item['price'] * item['qty']}", font=("Consolas", 9),
                 bg=BG_CARD, fg=GREEN).pack(side="right")


def clear_scanned():
    global scanned_items
    scanned_items = []
    export_cart_to_json()
    refresh_scanned_log()
    set_status("Scanned items cleared", TXT_MUTED)


def set_status(msg, color=TXT_MUTED):
    status_lbl.config(text=f"  {msg}", fg=color)


# ═══════════════════════════════════════════════════════════════════════════════
#  BUILD WINDOW — Simplified: Camera + Status + Scanned Log (no right sidebar)
# ═══════════════════════════════════════════════════════════════════════════════
W, H = 760, 680
window = tk.Tk()
window.title("SmartCart Scanner")
window.geometry(f"{W}x{H}")
window.resizable(False, False)
window.configure(bg=BG)

# ─── Top accent bar ───
tk.Frame(window, bg=ACCENT, height=3).place(x=0, y=0, width=W)

# ─── Header ───
hdr = tk.Frame(window, bg=BG_CARD, height=56)
hdr.place(x=0, y=3, width=W)
tk.Label(hdr, text="◈  SMARTCART SCANNER",
         font=("Consolas", 18, "bold"), bg=BG_CARD, fg=ACCENT).place(x=20, y=12)

clock_lbl = tk.Label(hdr, font=("Consolas", 9), bg=BG_CARD, fg=TXT_MUTED)
clock_lbl.place(x=W - 200, y=18)

def tick():
    clock_lbl.config(text=time.strftime("  %H:%M:%S   %d %b %Y"))
    window.after(1000, tick)
tick()

tk.Frame(window, bg=BORDER, height=1).place(x=0, y=59, width=W)

# ─── Camera Area ───
cam_frame = tk.Frame(window, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
cam_frame.place(x=14, y=68, width=W - 28, height=370)

tk.Label(cam_frame, text="  LIVE SCANNER",
         font=("Consolas", 9, "bold"), bg=BG_CARD, fg=TXT_MUTED).place(x=0, y=0, width=W - 28, height=24)
tk.Frame(cam_frame, bg=BORDER, height=1).place(x=0, y=24, width=W - 28)

cam_label = tk.Label(cam_frame, bg=BG, cursor="crosshair")
cam_label.place(x=6, y=30, width=W - 42, height=300)

# ─── Status bar ───
status_lbl = tk.Label(cam_frame, text="  Ready — press  ▶ START  to begin",
                       font=("Consolas", 10), bg=BG_PANEL, fg=TXT_MUTED, anchor="w")
status_lbl.place(x=0, y=334, width=W - 28, height=30)

# ─── On close: ensure export ───
def on_close():
    global cap
    export_cart_to_json()
    if cap:
        cap.release()
    window.destroy()

# ─── Buttons ───
btn_y = 446
start_btn = tk.Button(window, text="▶   START CAMERA",
                      font=("Consolas", 11, "bold"),
                      bg=ACCENT2, fg="white", relief="flat", bd=0,
                      activebackground="#6d28d9", activeforeground="white",
                      cursor="hand2", command=start_camera)
start_btn.place(x=14, y=btn_y, width=230, height=40)

stop_btn = tk.Button(window, text="📷   CAPTURE & SCAN",
                      font=("Consolas", 11, "bold"),
                      bg=BG_PANEL, fg=TXT_MUTED, relief="flat", bd=0,
                      activebackground=ACCENT, activeforeground=BG,
                      cursor="hand2", command=stop_camera, state="disabled",
                      highlightthickness=1, highlightbackground=BORDER)
stop_btn.place(x=258, y=btn_y, width=240, height=40)

clear_btn = tk.Button(window, text="🗑  CLEAR ALL",
                      font=("Consolas", 11, "bold"),
                      bg=BG_PANEL, fg=ORANGE, relief="flat", bd=0,
                      activebackground="#1e293b", activeforeground=ORANGE,
                      cursor="hand2", command=clear_scanned,
                      highlightthickness=1, highlightbackground=BORDER)
clear_btn.place(x=512, y=btn_y, width=120, height=40)

proceed_btn = tk.Button(window, text="✅  PROCEED",
                        font=("Consolas", 11, "bold"),
                        bg=GREEN, fg=BG, relief="flat", bd=0,
                        activebackground="#00c853", activeforeground=BG,
                        cursor="hand2", command=on_close)
proceed_btn.place(x=637, y=btn_y, width=109, height=40)

# ─── Scanned Items Log (compact, replaces the old right sidebar) ───
log_outer = tk.Frame(window, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
log_outer.place(x=14, y=496, width=W - 28, height=140)

log_header = tk.Frame(log_outer, bg=BG_CARD)
log_header.pack(fill="x")
tk.Label(log_header, text="  📋  SCANNED ITEMS", font=("Consolas", 9, "bold"),
         bg=BG_CARD, fg=ACCENT).pack(side="left", padx=6, pady=4)

log_total_lbl = tk.Label(log_header, text="", font=("Consolas", 9, "bold"),
                          bg=BG_CARD, fg=GREEN)
log_total_lbl.pack(side="right", padx=10, pady=4)

tk.Frame(log_outer, bg=BORDER, height=1).pack(fill="x")

log_canvas = tk.Canvas(log_outer, bg=BG_CARD, highlightthickness=0)
log_canvas.pack(fill="both", expand=True)
log_frame = tk.Frame(log_canvas, bg=BG_CARD)
log_canvas.create_window((0, 0), window=log_frame, anchor="nw")
log_frame.bind("<Configure>", lambda e: log_canvas.configure(scrollregion=log_canvas.bbox("all")))

refresh_scanned_log()

# ─── Footer ───
tk.Frame(window, bg=ACCENT2, height=3).place(x=0, y=H - 24, width=W)
tk.Label(window, text="SmartCart v2.0  ·  OCR-powered by Tesseract  ·  Items sync to Cashier POS on close",
         font=("Consolas", 8), bg=BG, fg=TXT_MUTED).place(x=W // 2 - 280, y=H - 20)

window.protocol("WM_DELETE_WINDOW", on_close)

window.mainloop()
if cap:
    cap.release()
cv2.destroyAllWindows()
