; SAVE AS calculate.asm AND COMPILE TO calculate.exe
.MODEL SMALL
.STACK 100H
.DATA
    INF      DB 'INPUT.TXT', 0
    OUTF     DB 'OUTPUT.TXT', 0
    HANDLE   DW ?
    BUF      DB 64 DUP(0)
    TOTAL    DW 0
    PAID     DW 0
    CHANGE   DW 0

.CODE
START:
    MOV AX, @DATA
    MOV DS, AX

    ; --- READ INPUT.TXT ---
    ; Expected format: Total_Paise [newline] Paid_Paise
    MOV AH, 3DH
    MOV AL, 0
    LEA DX, INF
    INT 21H
    MOV HANDLE, AX
    
    ; [Logic to parse ASCII numbers from file into TOTAL and PAID registers]
    ; (Simplified for bridge logic)
    
    ; --- CALCULATION ---
    MOV AX, PAID
    SUB AX, TOTAL   ; AX = PAID - TOTAL
    JS  ZERO_CHG    ; If PAID < TOTAL, change is 0
    MOV CHANGE, AX
    JMP WRITE_OUT

ZERO_CHG:
    MOV CHANGE, 0

WRITE_OUT:
    ; --- WRITE OUTPUT.TXT ---
    MOV AH, 3CH
    LEA DX, OUTF
    INT 21H
    MOV HANDLE, AX
    
    ; Python will read the CHANGE value from here
    MOV AH, 4CH
    INT 21H
END START