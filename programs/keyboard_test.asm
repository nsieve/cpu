; ==============================================================================
; Test Program: keyboard polling
; ==============================================================================
; Waits for a key, reads it, and shows its code on the LEDs (binary) and on the
; 7-segment display (decimal). For example 'A' = 65, 'a' = 97, '0' = 48.
; It loops forever, one key at a time.
;
; 0xBF01 (status): bit 7 = 1 when there's a key waiting (the Keyboard's av)
; 0xBF00 (data):   the key. Reading it also removes it from the keyboard's buffer

.EQU KB_DATA     0xBF00
.EQU KB_STATUS   0xBF01
.EQU KEY         0x20       ; last key read

.ORG 0xC000

START:
    MOV X, 0xBA             ; stack right below the framebuffer
    MOV Y, 0xFF
    MOV SP, XY
    CALL MAX_INIT

WAIT_KEY:
    MOV X, HIGH:KB_STATUS
    MOV Y, LOW:KB_STATUS
    LD A, XY
    ADD A, A                ; bit 7 (key available) goes into the carry
    JNC WAIT_KEY            ; no key yet

    MOV Y, LOW:KB_DATA      ; read the key (X is the same, 0xBF)
    LD A, XY
    ST KEY, A

    CALL SHOW_LEDS          ; binary on the LEDs
    LD A, KEY               ; decimal on the display
    ST NUM_L, A
    MOV A, 0
    ST NUM_H, A
    CALL SHOW_DEC
    JMP WAIT_KEY

.INCLUDE "lib/max7219.asm"
