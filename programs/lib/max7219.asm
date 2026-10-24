; ==============================================================================
; MAX7219 library: 8-digit 7-segment display over SPI (bit-banged on SPI_OUT)
; ==============================================================================
; Use it with  .INCLUDE "lib/max7219.asm"  at the end of the program (after the
; main code, so the CPU never runs into it), and set up the stack before calling
; anything.
;
;   MAX_INIT    configures the MAX7219 and sets the 8 digits to 0. Call it once
;   SHOW_DEC    shows NUM_H:NUM_L (16 bits, 0-65535)
;   SHOW_DEC32  shows NUM3:NUM2:NUM1:NUM0 (32 bits, 0-99,999,999)
;   SEND16      sends one raw frame: B = register (1-8 = digits), A = value
;   SHOW_LEDS   shows A on the 8 DISPLAY LEDs
;
; Digit 1 is the rightmost one. Numbers are shown with leading zeros.
; SHOW_DEC and SHOW_DEC32 calculate all 8 digits first and then send only the
; ones that changed, one right after the other, so the number changes as much
; at once as possible.
;
; Every routine can change every register (A-F, X, Y), so keep your own values
; in the zero page. The library uses 0x10-0x3F, the program can use 0x40 and up.
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

; zero page used by the library (0x10-0x3F)
.EQU VAL         0x10       ; value byte of the frame being sent
.EQU NUM0        0x11       ; number to show, least significant byte first
.EQU NUM1        0x12
.EQU NUM2        0x13
.EQU NUM3        0x14
.EQU POW0        0x15       ; power of 10 being counted, least significant byte first
.EQU POW1        0x16
.EQU POW2        0x17
.EQU POW3        0x18
.EQU TMP0        0x19       ; NUM - POW, bytes 0-2 (byte 3 stays in A)
.EQU TMP1        0x1A
.EQU TMP2        0x1B
.EQU DIGIT       0x1C       ; decimal digit being counted
.EQU DREG        0x1D       ; digit position (1-8) it belongs to
.EQU IDX         0x1E       ; digit position being sent
.EQU DBUF        0x20       ; new digits: digit d is at DBUF + d (0x21-0x28)
.EQU SHOWN       0x30       ; what each digit shows now: SHOWN + d (0x31-0x38)

.EQU NUM_L       NUM0       ; names for 16-bit numbers (SHOW_DEC)
.EQU NUM_H       NUM1

; ------------------------------------------------------------------------------
; MAX_INIT: deselects every SPI device, configures the MAX7219 and sets the
; 8 digits to 0 (the model in Digital ignores the configuration, the real chip
; needs it)
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
    MOV B, 0x0B             ; scan limit: all 8 digits
    MOV A, 0x07
    CALL SEND16
    MOV B, 0x0C             ; shutdown: normal operation
    MOV A, 0x01
    CALL SEND16

    MOV A, 0xFF             ; "shows nothing valid", so the first number sends all 8 digits
    ST SHOWN+1, A
    ST SHOWN+2, A
    ST SHOWN+3, A
    ST SHOWN+4, A
    ST SHOWN+5, A
    ST SHOWN+6, A
    ST SHOWN+7, A
    ST SHOWN+8, A
    MOV A, 0                ; show 00000000
    ST NUM0, A
    ST NUM1, A
    ST NUM2, A
    ST NUM3, A
    CALL SHOW_DEC32
    RET

; ------------------------------------------------------------------------------
; SHOW_DEC: shows NUM_H:NUM_L (16 bits) in decimal
; ------------------------------------------------------------------------------
SHOW_DEC:
    MOV A, 0
    ST NUM2, A
    ST NUM3, A              ; and continues into SHOW_DEC32

; ------------------------------------------------------------------------------
; SHOW_DEC32: shows NUM3:NUM2:NUM1:NUM0 in decimal on the 8 digits
; For each power of 10, it counts how many times it fits in the number by
; subtracting it (there's no division). What's left at the end is the units.
; Only up to 99,999,999 fits in 8 digits. The number is destroyed.
; ------------------------------------------------------------------------------
SHOW_DEC32:
    MOV B, 0x00             ; 10,000,000 = 0x00989680 -> digit 8
    MOV C, 0x98
    MOV D, 0x96
    MOV E, 0x80
    MOV F, 8
    CALL POW_DIGIT
    MOV B, 0x00             ; 1,000,000 = 0x000F4240 -> digit 7
    MOV C, 0x0F
    MOV D, 0x42
    MOV E, 0x40
    MOV F, 7
    CALL POW_DIGIT
    MOV B, 0x00             ; 100,000 = 0x000186A0 -> digit 6
    MOV C, 0x01
    MOV D, 0x86
    MOV E, 0xA0
    MOV F, 6
    CALL POW_DIGIT
    MOV B, 0x00             ; 10,000 = 0x00002710 -> digit 5
    MOV C, 0x00
    MOV D, 0x27
    MOV E, 0x10
    MOV F, 5
    CALL POW_DIGIT
    MOV B, 0x00             ; 1,000 = 0x000003E8 -> digit 4
    MOV C, 0x00
    MOV D, 0x03
    MOV E, 0xE8
    MOV F, 4
    CALL POW_DIGIT
    MOV B, 0x00             ; 100 -> digit 3
    MOV C, 0x00
    MOV D, 0x00
    MOV E, 100
    MOV F, 3
    CALL POW_DIGIT
    MOV B, 0x00             ; 10 -> digit 2
    MOV C, 0x00
    MOV D, 0x00
    MOV E, 10
    MOV F, 2
    CALL POW_DIGIT
    LD A, NUM0              ; what's left is the units
    ST DBUF+1, A
    CALL SEND_CHANGED       ; now send them all, one right after the other
    RET

; POW_DIGIT: counts how many times the power in B:C:D:E (B = most significant)
; fits in NUM, takes it out of NUM, and stores that digit at DBUF + F
POW_DIGIT:
    ST POW3, B
    ST POW2, C
    ST POW1, D
    ST POW0, E
    ST DREG, F
    MOV A, 0
    ST DIGIT, A
POW_LOOP:
    LD A, NUM0              ; NUM - POW, 32 bits. LD and ST don't change the flags,
    LD B, POW0              ; so each SBC gets the borrow of the byte before it
    SUB A, B
    ST TMP0, A
    LD A, NUM1
    LD B, POW1
    SBC A, B
    ST TMP1, A
    LD A, NUM2
    LD B, POW2
    SBC A, B
    ST TMP2, A
    LD A, NUM3
    LD B, POW3
    SBC A, B
    JNC POW_END             ; C = 0: it borrowed, so NUM < POW and this digit is done
    ST NUM3, A              ; NUM = NUM - POW
    LD A, TMP2
    ST NUM2, A
    LD A, TMP1
    ST NUM1, A
    LD A, TMP0
    ST NUM0, A
    LD A, DIGIT
    INC A
    ST DIGIT, A
    JMP POW_LOOP
POW_END:
    LD A, DREG              ; XY = 0x00:(DBUF + position), in the zero page
    ADD A, DBUF
    MOV Y, A
    MOV X, 0
    LD A, DIGIT
    ST XY, A
    RET

; SEND_CHANGED: sends the digits whose DBUF value is different from SHOWN,
; from digit 8 down to digit 1
SEND_CHANGED:
    MOV A, 8
    ST IDX, A
SC_LOOP:
    LD A, IDX               ; B = new digit (DBUF + d)
    ADD A, DBUF
    MOV Y, A
    MOV X, 0
    LD B, XY
    MOV A, Y                ; A = what it shows now (SHOWN + d)
    ADD A, 0x10             ; SHOWN - DBUF
    MOV Y, A
    LD A, XY
    CP A, B
    JZ SC_NEXT              ; same digit, nothing to send
    ST XY, B                ; it will show the new one
    MOV A, B
    LD B, IDX
    CALL SEND16
SC_NEXT:
    LD A, IDX
    DEC A
    ST IDX, A
    JNZ SC_LOOP
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
; (the MAX7219 reads MOSI on the rising edge). The same code is repeated for the
; 8 bits instead of a loop, so it doesn't need a counter and A keeps the byte.
SEND8:
    ADD A, A                ; bit 7 into the carry
    JC S8_ONE7
    ST XY, C                ; MOSI = 0, SCLK = 0
    ST XY, D                ; SCLK = 1: the MAX7219 reads a 0
    JMP S8_BIT6
S8_ONE7:
    ST XY, E                ; MOSI = 1, SCLK = 0
    ST XY, F                ; SCLK = 1: the MAX7219 reads a 1
S8_BIT6:
    ADD A, A
    JC S8_ONE6
    ST XY, C
    ST XY, D
    JMP S8_BIT5
S8_ONE6:
    ST XY, E
    ST XY, F
S8_BIT5:
    ADD A, A
    JC S8_ONE5
    ST XY, C
    ST XY, D
    JMP S8_BIT4
S8_ONE5:
    ST XY, E
    ST XY, F
S8_BIT4:
    ADD A, A
    JC S8_ONE4
    ST XY, C
    ST XY, D
    JMP S8_BIT3
S8_ONE4:
    ST XY, E
    ST XY, F
S8_BIT3:
    ADD A, A
    JC S8_ONE3
    ST XY, C
    ST XY, D
    JMP S8_BIT2
S8_ONE3:
    ST XY, E
    ST XY, F
S8_BIT2:
    ADD A, A
    JC S8_ONE2
    ST XY, C
    ST XY, D
    JMP S8_BIT1
S8_ONE2:
    ST XY, E
    ST XY, F
S8_BIT1:
    ADD A, A
    JC S8_ONE1
    ST XY, C
    ST XY, D
    JMP S8_BIT0
S8_ONE1:
    ST XY, E
    ST XY, F
S8_BIT0:
    ADD A, A
    JC S8_ONE0
    ST XY, C
    ST XY, D
    RET
S8_ONE0:
    ST XY, E
    ST XY, F
    RET
