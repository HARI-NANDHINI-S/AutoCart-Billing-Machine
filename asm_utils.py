import os, subprocess, tempfile, time

# The EMU 8086 bridge for additional logic modules
DOSBOX_PATH = r"C:\Program Files (x86)\DOSBox-0.74-3\DOSBox.exe"
PROJECT_PATH = os.path.dirname(__file__)
RESULT_FILE = os.path.join(PROJECT_PATH, "RESULT.TXT")


def _write_asm_and_run(asm_text):
    asm_path = os.path.join(PROJECT_PATH, "TMP_EMU.ASM")
    with open(asm_path, "w", encoding="utf-8") as f:
        f.write(asm_text)

    if os.path.exists(RESULT_FILE):
        os.remove(RESULT_FILE)

    conf_path = os.path.join(tempfile.gettempdir(), "asm_utils_dosbox.conf")
    with open(conf_path, "w", encoding="utf-8") as f:
        f.write("""[sdl]\nfullscreen=false\nautolock=false\n[dosbox]\nmemsize=16\n[cpu]\ncore=normal\n[autoexec]\n""")
        f.write(f"MOUNT C \"{PROJECT_PATH}\"\n")
        f.write("C:\\\n")
        f.write("NASM TMP_EMU.ASM -f bin -o TMP_EMU.COM\n")
        f.write("TMP_EMU\n")
        f.write("EXIT\n")

    if not os.path.isfile(DOSBOX_PATH):
        return False, "DOSBox not found"

    try:
        subprocess.run([DOSBOX_PATH, "-conf", conf_path, "-noconsole"],
                       cwd=PROJECT_PATH, timeout=30)
    except subprocess.TimeoutExpired:
        return False, "DOSBox timed out"
    except Exception as e:
        return False, str(e)

    if not os.path.isfile(RESULT_FILE):
        return False, "RESULT.TXT not generated"

    with open(RESULT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        return True, f.read().strip()


def calculate_weight_price(base_rate, weight_kg):
    # base_rate in rupees per kg, weight_kg float
    paise = int(round(base_rate * 100))
    quantity = int(round(weight_kg * 1000))  # grams
    # return in paise using 8086: total_paise = paise * quantity / 1000
    asm = f"""ORG 100h\nMOV AX, {paise}\nMOV BX, {quantity}\nIMUL BX\nMOV CX, 1000\nXOR DX, DX\nDIV CX\n; AX has total paise\nMOV SI, AX\n; write decimal to file\nMOV DI, buf\nMOV BX, 10\nMOV CX, 0\ncmp_loop:\nXOR DX, DX\nDIV BX\nPUSH DX\nINC CX\nCMP AX, 0\nJNE cmp_loop\nPOP2:\nPOP DX\nADD DL, '0'\nMOV [DI], DL\nINC DI\nLOOP POP2\nMOV BYTE [DI], 0Dh\nINC DI\nMOV BYTE [DI], 0Ah\nINC DI\nMOV AH, 3Ch\nMOV CX, 0\nMOV DX, fname\nINT 21h\nMOV [h], AX\nMOV AH, 40h\nMOV BX, [h]\nMOV CX, DI\nSUB CX, buf\nMOV DX, buf\nINT 21h\nMOV AH, 3Eh\nMOV BX, [h]\nINT 21h\nMOV AH, 4Ch\nINT 21h\nsection .data\nfname db 'RESULT.TXT',0\nh dw 0\nbuf times 20 db 0\n"""
    ok, out = _write_asm_and_run(asm)
    if not ok:
        # fallback Python compute
        return int(round(base_rate * weight_kg * 100))
    try:
        return int(out.strip())
    except Exception:
        return int(round(base_rate * weight_kg * 100))


def inventory_threshold_alert(code, stock, threshold):
    asm = f"""ORG 100h\nMOV AX,{stock}\nCMP AX,{threshold}\nJA ok\nMOV DX,0\nJMP end\nok:\nMOV DX,1\nend:\n; write DX to RESULT.TXT\nMOV BX,DX\nMOV CX,1\nMOV SI,0\nMOV DI,out\nADD DL,'0'\nMOV [DI],DL\nMOV DI, out+1\nMOV BYTE [DI], 0Dh\nMOV DI, out+2\nMOV BYTE [DI], 0Ah\nMOV AH,3Ch\nMOV CX,0\nMOV DX,fname\nINT 21h\nMOV [h],AX\nMOV AH,40h\nMOV BX,[h]\nMOV CX,4\nMOV DX,out\nINT 21h\nMOV AH,3Eh\nMOV BX,[h]\nINT 21h\nMOV AH,4Ch\nINT 21h\nsection .data\nfname db 'RESULT.TXT',0\nh dw 0\nout db '0000'\n"""
    ok, out = _write_asm_and_run(asm)
    if not ok:
        return stock <= threshold
    return out.strip().startswith("0")
