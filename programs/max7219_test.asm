; ==============================================================================
; Test Program: the MAX7219 model and the library
; ==============================================================================
; The LEDs show the progress: 0x01 = configured, 0x03 = 12345 shown,
; 0x07 = 54321 shown, then the CPU halts.

.ORG 0xC000

START:
    MOV X, 0xBA             ; stack right below the framebuffer
    MOV Y, 0xFF
    MOV SP, XY
    CALL MAX_INIT
    MOV A, 0x01
    CALL SHOW_LEDS

    MOV A, LOW:12345
    ST NUM_L, A
    MOV A, HIGH:12345
    ST NUM_H, A
    CALL SHOW_DEC
    MOV A, 0x03
    CALL SHOW_LEDS

    MOV A, LOW:54321
    ST NUM_L, A
    MOV A, HIGH:54321
    ST NUM_H, A
    CALL SHOW_DEC
    MOV A, 0x07
    CALL SHOW_LEDS

DONE:
    HALT
    JMP DONE                ; only reached if HALT doesn't stop the CPU

.INCLUDE "lib/max7219.asm"
