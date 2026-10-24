; ==============================================================================
; Fibonacci: 0, 1, 1, 2, 3, 5, 8 ... up to 63,245,986 on the 8-digit display
; ==============================================================================
; 32-bit numbers (4 bytes, least significant first), so the sum is one ADD for
; the lowest byte and an ADC for each of the other 3, which adds the carry of the
; byte before. It stops at the last number that fits in 8 digits (the next one,
; 102,334,155, doesn't). The LEDs count how many numbers have been shown (40).

.EQU FA0     0x40           ; a: number being shown
.EQU FA1     0x41
.EQU FA2     0x42
.EQU FA3     0x43
.EQU FB0     0x44           ; b: the next one
.EQU FB1     0x45
.EQU FB2     0x46
.EQU FB3     0x47
.EQU NX0     0x48           ; a + b
.EQU NX1     0x49
.EQU NX2     0x4A
.EQU NX3     0x4B
.EQU N       0x4C           ; count of numbers shown

.ORG 0xC000

START:
    MOV X, 0xBA             ; stack right below the framebuffer
    MOV Y, 0xFF
    MOV SP, XY
    CALL MAX_INIT

    MOV A, 0                ; a = 0, b = 1
    ST FA0, A
    ST FA1, A
    ST FA2, A
    ST FA3, A
    ST FB1, A
    ST FB2, A
    ST FB3, A
    ST N, A
    MOV A, 1
    ST FB0, A

LOOP:
    LD A, FA0               ; show a
    ST NUM0, A
    LD A, FA1
    ST NUM1, A
    LD A, FA2
    ST NUM2, A
    LD A, FA3
    ST NUM3, A
    CALL SHOW_DEC32

    LD A, N                 ; count it on the LEDs
    INC A
    ST N, A
    CALL SHOW_LEDS

    LD A, FA0               ; next = a + b, 32 bits. LD and ST don't change the flags,
    LD B, FB0               ; so each ADC gets the carry of the byte before it
    ADD A, B
    ST NX0, A
    LD A, FA1
    LD B, FB1
    ADC A, B
    ST NX1, A
    LD A, FA2
    LD B, FB2
    ADC A, B
    ST NX2, A
    LD A, FA3
    LD B, FB3
    ADC A, B
    ST NX3, A

    LD A, NX0               ; next - 100,000,000 (0x05F5E100), only to look at the borrow
    MOV B, 0x00             ; (MOV doesn't change the flags either)
    SUB A, B
    LD A, NX1
    MOV B, 0xE1
    SBC A, B
    LD A, NX2
    MOV B, 0xF5
    SBC A, B
    LD A, NX3
    MOV B, 0x05
    SBC A, B
    JC DONE                 ; no borrow: next >= 100,000,000, it doesn't fit in 8 digits

    LD A, FB0               ; a = b
    ST FA0, A
    LD A, FB1
    ST FA1, A
    LD A, FB2
    ST FA2, A
    LD A, FB3
    ST FA3, A
    LD A, NX0               ; b = next
    ST FB0, A
    LD A, NX1
    ST FB1, A
    LD A, NX2
    ST FB2, A
    LD A, NX3
    ST FB3, A
    JMP LOOP

DONE:
    LD A, FB0               ; b is the last number that fits, show it too
    ST NUM0, A
    LD A, FB1
    ST NUM1, A
    LD A, FB2
    ST NUM2, A
    LD A, FB3
    ST NUM3, A
    CALL SHOW_DEC32
    LD A, N
    INC A
    CALL SHOW_LEDS
END:
    HALT
    JMP END                 ; only reached if HALT doesn't stop the CPU

.INCLUDE "lib/max7219.asm"
