ORG 100h
MOV AX,149
CMP AX,20
JA ok
MOV DX,0
JMP end
ok:
MOV DX,1
end:
; write DX to RESULT.TXT
MOV BX,DX
MOV CX,1
MOV SI,0
MOV DI,out
ADD DL,'0'
MOV [DI],DL
MOV DI, out+1
MOV BYTE [DI], 0Dh
MOV DI, out+2
MOV BYTE [DI], 0Ah
MOV AH,3Ch
MOV CX,0
MOV DX,fname
INT 21h
MOV [h],AX
MOV AH,40h
MOV BX,[h]
MOV CX,4
MOV DX,out
INT 21h
MOV AH,3Eh
MOV BX,[h]
INT 21h
MOV AH,4Ch
INT 21h
section .data
fname db 'RESULT.TXT',0
h dw 0
out db '0000'
