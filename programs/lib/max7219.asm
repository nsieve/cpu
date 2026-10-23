; ==============================================================================
; MAX7219 library: 8-digit 7-segment display over SPI (bit-banged on SPI_OUT)
; ==============================================================================
; Use it with  .INCLUDE "lib/max7219.asm"  at the end of the program (after the
; main code, so the CPU never runs into it), and set up the stack before calling
; anything.
;
;   MAX_INIT    configures the MAX7219. Call it once at the start
;   SHOW_DEC    shows NUM_H:NUM_L (0-65535) in decimal on digits 1-5
;   SEND16      sends one raw frame: B = register (1-8 = digits), A = value
;   SHOW_LEDS   shows A on the 8 DISPLAY LEDs
;
; Every routine can change every register (A-F, X, Y), so keep your own values
; in the zero page. The library uses 0x10-0x1F, the program can use 0x20 and up.
;
; SPI_OUT bits: 0 = SCLK, 1 = MOSI, 2 = D/C (OLED), 3 = CS (OLED), 4 = CS (MAX7219)

.EQU SPI         0xBF02     ; SPI_OUT register
.EQU LEDS        0xBF03     ; DISPLAY register (8 LEDs)

.EQU SPI_IDLE    0x18       ; both CS high, SCLK low
.EQU MAX_SEL     0x08       ; MAX7219 CS low, OLED CS high
.EQU M0_CLK0     0x08       ; MAX selected, MOSI = 0, SCLK = 0
.EQU M0_CLK1     0x09       ; MAX selected, MOSI = 0, SCLK = 1
.EQU M1_CLK0     0x0A       ; MAX selected, MOSI = 1, SCLK = 0
.EQU M1_CLK1     0x0B       ; MAX selected, MOSI = 1, SCLK = 1

; zero page used by the library
.EQU VAL         0x10       ; value byte of the frame being sent
.EQU DATA        0x11       ; byte being shifted out
.EQU COUNT       0x12       ; bits left in the byte
.EQU NUM_L       0x13       ; number for SHOW_DEC (low byte)
.EQU NUM_H       0x14       ; number for SHOW_DEC (high byte)
.EQU POW_L       0x15       ; power of 10 being counted (low byte)
.EQU POW_H       0x16       ; power of 10 being counted (high byte)
.EQU TMP_L       0x17       ; NUM - POW (low byte)
.EQU DIGIT       0x18       ; decimal digit being counted

; ------------------------------------------------------------------------------
; MAX_INIT: deselects every SPI device and configures the MAX7219
; (the model in Digital ignores the configuration, the real chip needs it)
; ------------------------------------------------------------------------------
MAX_INIT:
    MOV X, HIGH:SPI
    MOV Y, LOW:SPI
    MOV A, SPI_IDLE         ; SPI_OUT powers on with random values
    ST XY, A
    MOV B, 0x0F             ; display test: off
    MOV A, 0x00
    CALL SEND16
    MOV B, 0x09             ; decode mode: Code B on every digit (it takes 0-9 directly)
    MOV A, 0xFF
    CALL SEND16
    MOV B, 0x0A             ; intensity: about half
    MOV A, 0x08
    CALL SEND16
    MOV B, 0x0B             ; scan limit: digits 1-5
    MOV A, 0x04
    CALL SEND16
    MOV B, 0x0C             ; shutdown: normal operation
    MOV A, 0x01
    CALL SEND16
    RET

; ------------------------------------------------------------------------------
; SHOW_DEC: shows NUM_H:NUM_L in decimal, with leading zeros (00042)
; For each power of 10, it counts how many times it fits in the number by
; subtracting it (there's no division). The rest is the units digit.
; NUM_H:NUM_L is destroyed.
; ------------------------------------------------------------------------------
SHOW_DEC:
    MOV A, LOW:10000
    ST POW_L, A
    MOV A, HIGH:10000
    ST POW_H, A
    CALL DEC_DIGIT
    MOV B, 5
    CALL SEND16

    MOV A, LOW:1000
    ST POW_L, A
    MOV A, HIGH:1000
    ST POW_H, A
    CALL DEC_DIGIT
    MOV B, 4
    CALL SEND16

    MOV A, 100
    ST POW_L, A
    MOV A, 0
    ST POW_H, A
    CALL DEC_DIGIT
    MOV B, 3
    CALL SEND16

    MOV A, 10
    ST POW_L, A
    MOV A, 0
    ST POW_H, A
    CALL DEC_DIGIT
    MOV B, 2
    CALL SEND16

    LD A, NUM_L             ; what's left is the units
    MOV B, 1
    CALL SEND16
    RET

; DEC_DIGIT: A = how many times POW fits in NUM, and NUM = what's left
DEC_DIGIT:
    MOV A, 0
    ST DIGIT, A
DEC_LOOP:
    LD A, NUM_L             ; NUM - POW, 16 bits
    LD B, POW_L
    SUB A, B
    ST TMP_L, A
    LD A, NUM_H
    LD B, POW_H
    SBC A, B                ; LD and ST don't change the flags, so C is still the borrow of the SUB
    JNC DEC_END             ; C = 0: it borrowed, so NUM < POW and this digit is done
    ST NUM_H, A             ; NUM = NUM - POW
    LD A, TMP_L
    ST NUM_L, A
    LD A, DIGIT
    INC A
    ST DIGIT, A
    JMP DEC_LOOP
DEC_END:
    LD A, DIGIT
    RET

; ------------------------------------------------------------------------------
; SHOW_LEDS: shows A on the DISPLAY LEDs
; ------------------------------------------------------------------------------
SHOW_LEDS:
    MOV X, HIGH:LEDS
    MOV Y, LOW:LEDS
    ST XY, A
    RET

; ------------------------------------------------------------------------------
; SEND16: sends one 16-bit frame to the MAX7219, MSB first
;   in: B = register (1-8 = digits), A = value
; ------------------------------------------------------------------------------
SEND16:
    ST VAL, A               ; keep the value while the register byte goes out
    MOV X, HIGH:SPI         ; XY points to SPI_OUT (not the MAR: JMP/JCC/CALL label and RET overwrite it)
    MOV Y, LOW:SPI
    MOV C, M0_CLK0          ; the 4 values SEND8 writes, so each bit is just 2 writes
    MOV D, M0_CLK1
    MOV E, M1_CLK0
    MOV F, M1_CLK1
    MOV A, MAX_SEL          ; CS low: the frame starts
    ST XY, A
    MOV A, B
    CALL SEND8              ; bits 15-8: register
    LD A, VAL
    CALL SEND8              ; bits 7-0: value
    MOV A, SPI_IDLE         ; CS high: the MAX7219 takes the 16 bits on this edge
    ST XY, A
    RET

; SEND8: shifts out A, MSB first. Each bit: MOSI with SCLK low, then SCLK high
; (the MAX7219 reads MOSI on the rising edge)
SEND8:
    ST DATA, A
    MOV A, 8
    ST COUNT, A
SEND8_BIT:
    LD A, DATA
    ADD A, A                ; the next bit (bit 7) goes into the carry
    ST DATA, A
    JC SEND8_ONE
    ST XY, C                ; MOSI = 0, SCLK = 0
    ST XY, D                ; SCLK = 1: the MAX7219 reads a 0
    JMP SEND8_NEXT
SEND8_ONE:
    ST XY, E                ; MOSI = 1, SCLK = 0
    ST XY, F                ; SCLK = 1: the MAX7219 reads a 1
SEND8_NEXT:
    LD A, COUNT
    DEC A
    ST COUNT, A
    JNZ SEND8_BIT
    RET
