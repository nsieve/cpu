; ==============================================================================
; Fibonacci: 0, 1, 1, 2, 3, 5, 8 ... up to 46368 on the 7-segment display
; ==============================================================================
; 16-bit numbers, so the sum uses ADD for the low byte and ADC for the high one.
; It stops at the last number that fits in 16 bits (the next one, 75025, doesn't).
; The LEDs show how many numbers have been shown.

.EQU FA_L    0x20           ; current number (low byte)
.EQU FA_H    0x21
.EQU FB_L    0x22           ; next number
.EQU FB_H    0x23
.EQU N       0x24           ; count of numbers shown

.ORG 0xC000

START:
    MOV X, 0xBA             ; stack right below the framebuffer
    MOV Y, 0xFF
    MOV SP, XY
    CALL MAX_INIT

    MOV A, 0                ; a = 0, b = 1
    ST FA_L, A
    ST FA_H, A
    ST FB_H, A
    ST N, A
    MOV A, 1
    ST FB_L, A

LOOP:
    LD A, FA_L              ; show a
    ST NUM_L, A
    LD A, FA_H
    ST NUM_H, A
    CALL SHOW_DEC

    LD A, N                 ; count it on the LEDs
    INC A
    ST N, A
    CALL SHOW_LEDS

    LD A, FA_L              ; next = a + b (the carry goes from the low to the high byte)
    LD B, FB_L
    ADD A, B
    ST FA_L, A              ; a now holds the low byte of next, b still holds the old b
    LD A, FA_H
    LD B, FB_H
    ADC A, B
    JC DONE                 ; carry out of the high byte: next doesn't fit in 16 bits

    ST FA_H, A              ; swap: a = old b, b = next
    LD B, FB_H
    ST FB_H, A
    MOV A, B
    ST FA_H, A
    LD A, FA_L
    LD B, FB_L
    ST FB_L, A
    MOV A, B
    ST FA_L, A
    JMP LOOP

DONE:
    LD A, FB_L              ; b is the last number that fits, show it too
    ST NUM_L, A
    LD A, FB_H
    ST NUM_H, A
    CALL SHOW_DEC
    LD A, N
    INC A
    CALL SHOW_LEDS
END:
    HALT
    JMP END                 ; only reached if HALT doesn't stop the CPU

.INCLUDE "lib/max7219.asm"
