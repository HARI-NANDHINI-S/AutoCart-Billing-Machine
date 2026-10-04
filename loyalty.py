"""
loyalty.py — Loyalty Points System for HyperMarket Pro
EMU 8086-powered points calculation with persistent JSON storage.

Points Rules:
  - 1 point per ₹10 spent
  - Member session type → 2× multiplier
  - 100 points = ₹10 redemption value
"""

import os
import json
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LOYALTY_FILE = os.path.join(HERE, "loyalty_data.json")

# ─── EMU 8086 Points Calculation ──────────────────────────────────────────────

def _calculate_points_asm(total_paise, multiplier=1):
    """
    Use EMU 8086 assembly (via DOSBox) to compute loyalty points.
    Points = (total_paise / 1000) * multiplier
    (i.e. 1 point per ₹10 = per 1000 paise)

    Falls back to Python if DOSBox is unavailable.
    """
    try:
        from asm_utils import _write_asm_and_run
        asm = f"""ORG 100h
MOV AX, {total_paise & 0xFFFF}
MOV DX, {(total_paise >> 16) & 0xFFFF}
MOV BX, 1000
CMP DX, 0
JNE big_div
DIV BX
XOR DX, DX
JMP apply_mul
big_div:
PUSH AX
MOV AX, DX
XOR DX, DX
DIV BX
MOV CX, AX
POP AX
DIV BX
MOV DX, CX
apply_mul:
MOV BX, {multiplier}
MUL BX
; AX = points, write to RESULT.TXT
MOV SI, AX
MOV DI, buf
MOV BX, 10
MOV CX, 0
CMP AX, 0
JNE pts_loop
MOV BYTE [DI], '0'
INC DI
INC CX
JMP pts_write
pts_loop:
CMP AX, 0
JE pts_rev
XOR DX, DX
DIV BX
PUSH DX
INC CX
JMP pts_loop
pts_rev:
CMP CX, 0
JE pts_write
POP DX
ADD DL, '0'
MOV [DI], DL
INC DI
DEC CX
JMP pts_rev
pts_write:
MOV BYTE [DI], 0Dh
INC DI
MOV BYTE [DI], 0Ah
INC DI
MOV AH, 3Ch
MOV CX, 0
MOV DX, fname
INT 21h
JC done
MOV [h], AX
MOV AH, 40h
MOV BX, [h]
MOV CX, DI
SUB CX, buf
MOV DX, buf
INT 21h
MOV AH, 3Eh
MOV BX, [h]
INT 21h
done:
MOV AH, 4Ch
INT 21h
section .data
fname db 'RESULT.TXT',0
h dw 0
buf times 20 db 0
"""
        ok, out = _write_asm_and_run(asm)
        if ok:
            return max(0, int(out.strip()))
    except Exception:
        pass

    # Python fallback: total_paise / 1000 * multiplier
    return max(0, int(total_paise // 1000) * multiplier)


# ─── Loyalty Manager ─────────────────────────────────────────────────────────

class LoyaltyManager:
    """Manages customer loyalty points with persistent JSON storage."""

    def __init__(self, filepath=None):
        self.filepath = filepath or LOYALTY_FILE
        self._data = self._load()

    def _load(self):
        if os.path.isfile(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Loyalty] Save error: {e}")

    def _ensure_member(self, phone):
        phone = str(phone).strip()
        if phone not in self._data:
            self._data[phone] = {
                "name": "",
                "points": 0,
                "total_spent": 0,
                "tier": "Bronze",
                "history": [],
                "joined": datetime.now().isoformat(),
            }
        return phone

    def get_balance(self, phone):
        """Get current points balance for a customer."""
        phone = str(phone).strip()
        if phone in self._data:
            return self._data[phone].get("points", 0)
        return 0

    def get_tier(self, phone):
        """Get loyalty tier based on total spent."""
        phone = str(phone).strip()
        if phone not in self._data:
            return "Bronze"
        total = self._data[phone].get("total_spent", 0)
        if total >= 50000:
            return "Platinum"
        elif total >= 20000:
            return "Gold"
        elif total >= 5000:
            return "Silver"
        return "Bronze"

    def get_member_info(self, phone):
        """Return full member info dict."""
        phone = str(phone).strip()
        if phone in self._data:
            info = self._data[phone].copy()
            info["tier"] = self.get_tier(phone)
            return info
        return None

    def set_name(self, phone, name):
        """Set or update customer name."""
        phone = self._ensure_member(phone)
        self._data[phone]["name"] = name
        self._save()

    def add_points(self, phone, total_paise, multiplier=1):
        """
        Award loyalty points for a purchase.
        Returns the number of points awarded.
        """
        phone = self._ensure_member(phone)
        pts = _calculate_points_asm(total_paise, multiplier)
        self._data[phone]["points"] += pts
        self._data[phone]["total_spent"] += total_paise / 100.0
        self._data[phone]["tier"] = self.get_tier(phone)
        self._data[phone]["history"].append({
            "type": "earn",
            "points": pts,
            "amount_rs": total_paise / 100.0,
            "date": datetime.now().isoformat(),
        })
        self._save()
        return pts

    def redeem_points(self, phone, points_to_redeem):
        """
        Redeem loyalty points. 100 points = ₹10 discount.
        Returns (success: bool, discount_rs: float, remaining_points: int).
        """
        phone = str(phone).strip()
        if phone not in self._data:
            return False, 0.0, 0
        balance = self._data[phone].get("points", 0)
        if points_to_redeem > balance:
            return False, 0.0, balance
        if points_to_redeem <= 0:
            return False, 0.0, balance

        discount_rs = (points_to_redeem / 100.0) * 10.0  # 100 pts = ₹10
        self._data[phone]["points"] -= points_to_redeem
        self._data[phone]["history"].append({
            "type": "redeem",
            "points": -points_to_redeem,
            "discount_rs": discount_rs,
            "date": datetime.now().isoformat(),
        })
        self._save()
        return True, discount_rs, self._data[phone]["points"]

    def get_redemption_value(self, points):
        """Calculate rupee value of given points. 100 pts = ₹10."""
        return max(0, (points / 100.0) * 10.0)


# ─── Singleton Instance ──────────────────────────────────────────────────────
_manager = None

def get_loyalty_manager():
    global _manager
    if _manager is None:
        _manager = LoyaltyManager()
    return _manager


# ─── Test / Demo ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mgr = LoyaltyManager()
    print("=== Loyalty System Test ===")

    phone = "9876543210"
    mgr.set_name(phone, "Test Customer")

    # Simulate ₹1500 purchase (150000 paise) → should get 150 points
    pts = mgr.add_points(phone, 150000, multiplier=1)
    print(f"Points earned for ₹1500: {pts}")
    print(f"Balance: {mgr.get_balance(phone)}")
    print(f"Tier: {mgr.get_tier(phone)}")

    # Member multiplier
    pts2 = mgr.add_points(phone, 100000, multiplier=2)
    print(f"Points earned for ₹1000 (2x member): {pts2}")
    print(f"Balance: {mgr.get_balance(phone)}")

    # Redeem
    ok, disc, rem = mgr.redeem_points(phone, 100)
    print(f"Redeemed 100 pts: discount=₹{disc}, remaining={rem}")

    print(f"Member info: {mgr.get_member_info(phone)}")
    print("=== Test Complete ===")
