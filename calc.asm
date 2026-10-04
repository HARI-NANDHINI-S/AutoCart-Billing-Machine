; ============================================================
; HyperMarket Pro - Bill Calculator
; EMU 8086 COMPATIBLE - FULLY DEBUGGED
; ============================================================
; Rules followed:
;  - No 32-bit registers (EAX etc)
;  - No XCHG with memory ([SP] not supported in EMU8086)
;  - No MUL/DIV with immediate values
;  - No PUSH with immediate values
;  - All memory temps used instead of clever stack tricks
;  - PROC declared as NEAR
;  - All labels unique
;
; INPUT  : C:\HYPERPOS\INPUT.TXT
;  Line1: SUBTOTAL paise   e.g. 93500
;  Line2: DISCOUNT percent e.g. 10
;  Line3: GST      percent e.g. 18
;  Line4: COUPON   paise   e.g. 5000
;
; OUTPUT : C:\HYPERPOS\OUTPUT.TXT
;  Line1: SUBTOTAL
;  Line2: DISCOUNT
;  Line3: GST_AMOUNT
;  Line4: COUPON
;  Line5: GRAND_TOTAL
; ============================================================

.MODEL SMALL
.STACK 200h

.DATA
    fname_in   DB 'C:\HYPERPOS\INPUT.TXT',0
    fname_out  DB 'C:\HYPERPOS\OUTPUT.TXT',0
    hdl_in     DW 0
    hdl_out    DW 0
    rbuf       DB 128 DUP(0)
    wbuf       DB 16  DUP(0)
    crlf       DB 13,10

    ; 32-bit values stored as lo+hi word pairs
    sub_lo     DW 0
    sub_hi     DW 0
    dpc        DW 0
    gpc        DW 0
    cpn_lo     DW 0
    cpn_hi     DW 0
    dis_lo     DW 0
    dis_hi     DW 0
    gst_lo     DW 0
    gst_hi     DW 0
    gnd_lo     DW 0
    gnd_hi     DW 0
    aft_lo     DW 0
    aft_hi     DW 0

    ; general purpose temps (avoids register conflicts)
    t1         DW 0
    t2         DW 0
    t3         DW 0
    tmpq       DW 0
    dcount     DW 0
    TEN        DW 10
    HUNDRED    DW 100

.CODE

; =============================================================================
MAIN PROC
    MOV  AX, @DATA
    MOV  DS, AX

    ; open INPUT.TXT
    MOV  AH, 3Dh
    MOV  AL, 0
    LEA  DX, fname_in
    INT  21h
    JC   QUIT
    MOV  hdl_in, AX

    ; read
    MOV  AH, 3Fh
    MOV  BX, hdl_in
    MOV  CX, 127
    LEA  DX, rbuf
    INT  21h
    PUSHF
    MOV  AH, 3Eh
    MOV  BX, hdl_in
    INT  21h
    POPF
    JC   QUIT
    MOV  BX, AX
    MOV  BYTE PTR rbuf[BX], 0

    ; parse
    LEA  SI, rbuf
    CALL PNUM
    MOV  sub_lo, AX
    MOV  sub_hi, DX
    CALL SNL

    CALL PNUM
    MOV  dpc, AX
    CALL SNL

    CALL PNUM
    MOV  gpc, AX
    CALL SNL

    CALL PNUM
    MOV  cpn_lo, AX
    MOV  cpn_hi, DX

    ; DISCOUNT = sub * dpc / 100
    MOV  AX, sub_lo
    MOV  DX, sub_hi
    MOV  BX, dpc
    CALL MUL32
    MOV  BX, HUNDRED
    CALL DIV32
    MOV  dis_lo, AX
    MOV  dis_hi, DX

    ; AFTER = sub - discount
    MOV  AX, sub_lo
    MOV  DX, sub_hi
    SUB  AX, dis_lo
    SBB  DX, dis_hi
    MOV  aft_lo, AX
    MOV  aft_hi, DX

    ; GST = after * gpc / 100
    MOV  AX, aft_lo
    MOV  DX, aft_hi
    MOV  BX, gpc
    CALL MUL32
    MOV  BX, HUNDRED
    CALL DIV32
    MOV  gst_lo, AX
    MOV  gst_hi, DX

    ; GRAND = after + gst - coupon
    MOV  AX, aft_lo
    MOV  DX, aft_hi
    ADD  AX, gst_lo
    ADC  DX, gst_hi
    SUB  AX, cpn_lo
    SBB  DX, cpn_hi
    MOV  gnd_lo, AX
    MOV  gnd_hi, DX

    ; create OUTPUT.TXT
    MOV  AH, 3Ch
    MOV  CX, 0
    LEA  DX, fname_out
    INT  21h
    JC   QUIT
    MOV  hdl_out, AX

    ; write 5 lines
    MOV  AX, sub_lo
    MOV  DX, sub_hi
    CALL WLINE

    MOV  AX, dis_lo
    MOV  DX, dis_hi
    CALL WLINE

    MOV  AX, gst_lo
    MOV  DX, gst_hi
    CALL WLINE

    MOV  AX, cpn_lo
    MOV  DX, cpn_hi
    CALL WLINE

    MOV  AX, gnd_lo
    MOV  DX, gnd_hi
    CALL WLINE

    ; close output
    MOV  AH, 3Eh
    MOV  BX, hdl_out
    INT  21h

QUIT:
    MOV  AX, 4C00h
    INT  21h
MAIN ENDP

; =============================================================================
; PNUM: parse decimal ASCII at DS:SI -> DX:AX
;   Uses memory temps t1,t2,t3 -- NO XCHG, NO stack tricks
; =============================================================================
PNUM PROC NEAR
    XOR  AX, AX
    XOR  DX, DX

PN_LP:
    MOV  BL, BYTE PTR [SI]
    CMP  BL, '0'
    JB   PN_RT
    CMP  BL, '9'
    JA   PN_RT

    ; multiply accumulator DX:AX by 10 using memory temps
    ; save current values
    MOV  t1, AX              ; t1 = current lo
    MOV  t2, DX              ; t2 = current hi

    ; compute lo * 10
    MOV  AX, t1
    MUL  TEN                 ; DX:AX = t1 * 10
    MOV  t3, AX              ; t3 = lo product
    MOV  t1, DX              ; t1 = carry from lo multiply

    ; compute hi * 10
    MOV  AX, t2
    MUL  TEN                 ; DX:AX = t2 * 10 (ignore DX)
    ADD  AX, t1              ; new hi = (t2*10) + carry
    MOV  DX, AX              ; DX = new hi word
    MOV  AX, t3              ; AX = new lo word

    ; add digit
    SUB  BL, '0'
    XOR  BH, BH
    ADD  AX, BX
    ADC  DX, 0

    INC  SI
    JMP  PN_LP

PN_RT:
    RET
PNUM ENDP

; =============================================================================
; SNL: skip CR/LF at DS:SI, stop at null or other char
; =============================================================================
SNL PROC NEAR
SN_LP:
    MOV  AL, BYTE PTR [SI]
    CMP  AL, 0
    JE   SN_RT
    CMP  AL, 13
    JE   SN_SK
    CMP  AL, 10
    JE   SN_SK
    JMP  SN_RT
SN_SK:
    INC  SI
    JMP  SN_LP
SN_RT:
    RET
SNL ENDP

; =============================================================================
; MUL32: DX:AX * BX -> DX:AX  (32x16 multiply)
;   Uses memory temps t1,t2,t3 -- NO XCHG with memory
; =============================================================================
MUL32 PROC NEAR
    MOV  t1, AX              ; t1 = lo word of multiplicand
    MOV  t2, DX              ; t2 = hi word of multiplicand

    ; lo * BX
    MOV  AX, t1
    MUL  BX                  ; DX:AX = lo * BX
    MOV  t3, AX              ; t3 = lo product
    MOV  t1, DX              ; t1 = carry from lo

    ; hi * BX
    MOV  AX, t2
    MUL  BX                  ; DX:AX = hi * BX (ignore DX)
    ADD  AX, t1              ; new hi = (hi*BX) + carry
    MOV  DX, AX              ; DX = result hi word
    MOV  AX, t3              ; AX = result lo word
    RET
MUL32 ENDP

; =============================================================================
; DIV32: DX:AX / BX -> DX:AX quotient
;   Uses tmpq for hi quotient -- NO XCHG with memory
; =============================================================================
DIV32 PROC NEAR
    CMP  DX, 0
    JNE  D32_BIG

    ; fast path: DX=0, simple 16-bit divide
    DIV  BX
    XOR  DX, DX
    RET

D32_BIG:
    ; full 32-bit / 16-bit
    MOV  t1, AX              ; save lo dividend
    MOV  AX, DX
    XOR  DX, DX
    DIV  BX                  ; hi / BX -> AX=hi_quot, DX=hi_rem
    MOV  tmpq, AX            ; save hi quotient to memory
    MOV  AX, t1              ; restore lo dividend
    ; DX = hi_rem (feeds as upper word)
    DIV  BX                  ; DX:AX / BX -> AX=lo_quot, DX=remainder
    MOV  DX, tmpq            ; DX:AX = full quotient
    RET
DIV32 ENDP

; =============================================================================
; WLINE: write DX:AX as decimal + CRLF to hdl_out
;   Extracts digits by dividing by 10, stores in wbuf, writes via INT 21h
;   Uses dcount (memory) for byte count -- NO MOV CX,CX bug
;   No PUSH DS around INT 21h -- would corrupt segment register
; =============================================================================
WLINE PROC NEAR
    MOV  dcount, 0

    ; check if zero
    MOV  CX, DX
    OR   CX, AX
    JNZ  WL_LOOP

    ; value is zero
    MOV  BYTE PTR wbuf, '0'
    MOV  dcount, 1
    JMP  WL_WRITE

WL_LOOP:
    ; quit when DX:AX = 0
    MOV  CX, DX
    OR   CX, AX
    JZ   WL_REVERSE

    CMP  DX, 0
    JNE  WL_BIG

    ; 16-bit path
    MOV  CX, 10
    DIV  CX                  ; AX=quot DX=remainder
    MOV  BX, dcount
    ADD  DL, '0'
    MOV  BYTE PTR wbuf[BX], DL
    INC  dcount
    XOR  DX, DX
    JMP  WL_LOOP

WL_BIG:
    ; 32-bit divide by 10
    MOV  t1, AX              ; save lo dividend
    MOV  AX, DX
    XOR  DX, DX
    MOV  CX, 10
    DIV  CX                  ; hi/10 -> AX=hi_quot DX=hi_rem
    MOV  tmpq, AX            ; save hi quot
    MOV  AX, t1              ; restore lo dividend
    DIV  CX                  ; DX:AX/10 -> AX=lo_quot DX=digit
    MOV  BX, dcount
    ADD  DL, '0'
    MOV  BYTE PTR wbuf[BX], DL
    INC  dcount
    MOV  DX, tmpq            ; restore hi quot
    JMP  WL_LOOP

WL_REVERSE:
    ; digits in wbuf are in reverse order (LSB first), reverse them
    MOV  CX, dcount
    MOV  SI, 0               ; start index
    MOV  DI, dcount
    DEC  DI                  ; end index

WL_REV_LP:
    CMP  SI, DI
    JGE  WL_WRITE

    ; swap wbuf[SI] and wbuf[DI]
    MOV  AL, BYTE PTR wbuf[SI]
    MOV  BL, BYTE PTR wbuf[DI]
    MOV  BYTE PTR wbuf[SI], BL
    MOV  BYTE PTR wbuf[DI], AL
    INC  SI
    DEC  DI
    JMP  WL_REV_LP

WL_WRITE:
    ; write digit bytes
    MOV  AH, 40h
    MOV  BX, hdl_out
    MOV  CX, dcount          ; byte count from memory var -- FIXED
    LEA  DX, wbuf
    INT  21h

    ; write CRLF
    MOV  AH, 40h
    MOV  BX, hdl_out
    MOV  CX, 2
    LEA  DX, crlf
    INT  21h

    ; clear wbuf for next call
    MOV  CX, 16
    LEA  DI, wbuf
WL_CLR:
    MOV  BYTE PTR [DI], 0
    INC  DI
    LOOP WL_CLR

    RET
WLINE ENDP

END MAIN