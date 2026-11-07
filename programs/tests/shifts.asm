; ==============================================================================
; Test Program: SHR and ROR
; ==============================================================================
; digital/tests/check_cpu.py runs it on CPU.dig and on the emulator. ROR runs
; with C = 1, so bit 7 of the result comes from the carry. Both shifts put the
; bit they shift out into C and clear V, and PUSHF keeps the flags of each one.

.ORG 0xC000

START:
    MOV X, 0xBA
    MOV Y, 0xFF
    MOV SP, XY
    MOV A, 0x81
    SHR A                   ; 0x40, C = 1
    PUSHF
    ST 0x20, A
    MOV A, 0x81
    CP A, 0x00              ; C = 1
    ROR A                   ; 0xC0, C = 1
    PUSHF
    ST 0x21, A
    MOV A, 0x06
    SHR A                   ; 0x03, C = 0
    PUSHF
    SHR A                   ; 0x01, C = 1
    PUSHF
    ST 0x22, A
    MOV A, 0x80
    CP A, 0x01              ; 0x7F: C and V
    ROR A                   ; 0xC0, C = 0 and V = 0
    PUSHF
    ST 0x23, A

    ; a 16-bit shift right: 0xA5A5 >> 1 = 0x52D2, the bit in between goes through C
    MOV X, 0xA5
    MOV Y, 0xA5
    MOV A, X
    SHR A
    MOV X, A
    MOV A, Y
    ROR A
    MOV Y, A
    PUSHF
    ST 0x24, X
    ST 0x25, Y

DONE:
    HALT
    JMP DONE
