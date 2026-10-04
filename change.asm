; CHANGE.ASM  -  NeonPay 8086 Change Calculator
; Assemble:  NASM CHANGE.ASM -f bin -o CHANGE.COM
ORG 100h

section .text
start:
    MOV  AX, 200000    ; AX = tendered paise
    MOV  BX, 190006         ; BX = amount due paise
    SUB  AX, BX                   ; AX = change paise

    ; Convert AX to decimal string
    MOV  CX, 0
    MOV  BX, 10
div_loop:
    XOR  DX, DX
    DIV  BX
    PUSH DX
    INC  CX
    CMP  AX, 0
    JNE  div_loop

    MOV  DI, buf
pop_loop:
    POP  AX
    ADD  AL, '0'
    MOV  [DI], AL
    INC  DI
    LOOP pop_loop
    MOV  BYTE [DI], 0Dh
    INC  DI
    MOV  BYTE [DI], 0Ah
    INC  DI

    ; Create RESULT.TXT
    MOV  AH, 3Ch
    MOV  CX, 0
    MOV  DX, fname
    INT  21h
    JC   done
    MOV  [handle], AX

    ; Write to file
    MOV  AH, 40h
    MOV  BX, [handle]
    MOV  CX, DI
    SUB  CX, buf
    MOV  DX, buf
    INT  21h

    ; Close file
    MOV  AH, 3Eh
    MOV  BX, [handle]
    INT  21h

done:
    MOV  AH, 4Ch
    XOR  AL, AL
    INT  21h

section .data
fname   DB 'RESULT.TXT', 0
handle  DW 0
buf     TIMES 20 DB 0
