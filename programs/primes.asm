; ==============================================================================
; Prime numbers: the Sieve of Eratosthenes, shown on the 7-segment display
; ==============================================================================
; The sieve is one byte of RAM per number, starting at SIEVE (0 = still possibly
; prime, 1 = crossed out). It goes through the numbers from 2 up:
;   - if a number isn't crossed out, it's prime: show it, and cross out all its
;     multiples (2n, 3n, 4n ...) by adding n to a pointer, so no multiplication
;   - if it is crossed out, skip it
; The LEDs show how many primes have been found (low byte).
;
; LIMIT sets how far it goes. Up to 1000 there are 168 primes, which takes a few
; minutes in Digital at 5 kHz. On the real CPU it can go up to about 47,000
; (the sieve has to fit in the RAM below the stack).

.EQU LIMIT   47000          ; last number checked (47,000 at most: the sieve has to fit below the stack)
.EQU SIEVE   0x0200         ; sieve start (must start at a page, xx00)
.EQU SV_END  SIEVE+LIMIT+1  ; the first byte after the sieve
.EQU CLR_END SV_END+256      ; its high byte is the page after the last one to clear

.EQU N_L     0x40           ; number being checked
.EQU N_H     0x41
.EQU FOUND   0x42           ; primes found

.ORG 0xC000

START:
    MOV X, 0xBA             ; stack right below the framebuffer
    MOV Y, 0xFF
    MOV SP, XY
    CALL MAX_INIT

    ; clear the sieve (RAM starts with random values on real hardware).
    ; It clears whole pages, 8 bytes per loop, and shows the page on the LEDs
    MOV X, HIGH:SIEVE
    MOV Y, LOW:SIEVE
CLEAR_PAGE:
    MOV A, X
    CALL SHOW_LEDS          ; it changes XY, so put it back
    MOV X, A
    MOV Y, 0
    MOV B, 0
CLEAR:
    ST XY, B
    INC XY
    ST XY, B
    INC XY
    ST XY, B
    INC XY
    ST XY, B
    INC XY
    ST XY, B
    INC XY
    ST XY, B
    INC XY
    ST XY, B
    INC XY
    ST XY, B
    INC XY
    MOV A, Y                ; Y = 0 again: the page is done
    CP A, 0
    JNZ CLEAR
    MOV A, X                ; stop after the page where the sieve ends
    CP A, HIGH:CLR_END
    JNZ CLEAR_PAGE

    MOV A, 2                ; n = 2
    ST N_L, A
    MOV A, 0
    ST N_H, A
    ST FOUND, A

NEXT_N:
    LD A, N_H               ; XY = SIEVE + n (SIEVE's low byte is 0, so only X changes)
    MOV B, HIGH:SIEVE
    ADD A, B
    MOV X, A
    LD A, N_L
    MOV Y, A
    MOV A, Y                ; stop when SIEVE + n = SV_END, which means n = LIMIT + 1
    CP A, LOW:SV_END
    JNZ NOT_END
    MOV A, X
    CP A, HIGH:SV_END
    JZ DONE
NOT_END:
    LD A, XY                ; crossed out?
    CP A, 0
    JNZ SKIP

    LD A, N_L               ; it's prime: show it
    ST NUM_L, A
    LD A, N_H
    ST NUM_H, A
    CALL SHOW_DEC
    LD A, FOUND
    INC A
    ST FOUND, A
    CALL SHOW_LEDS

    LD A, N_H               ; cross out its multiples: XY = SIEVE + n, then add n each time
    MOV B, HIGH:SIEVE
    ADD A, B
    MOV X, A
    LD A, N_L
    MOV Y, A
    LD C, N_L               ; C:D = n (D = high byte)
    LD D, N_H
MARK:
    MOV A, Y                ; XY = XY + n
    ADD A, C
    MOV Y, A
    MOV A, X
    ADC A, D
    MOV X, A
    JC SKIP                 ; XY + n went past 0xFFFF (MOV doesn't change the flags), so it's past the end too
    MOV A, Y                ; XY - SV_END, only to look at the borrow
    MOV B, LOW:SV_END
    SUB A, B
    MOV A, X
    MOV B, HIGH:SV_END
    SBC A, B
    JC SKIP                 ; no borrow: XY >= SV_END, past the end of the sieve
    MOV A, 1
    ST XY, A                ; cross it out
    JMP MARK

SKIP:
    LD A, N_L               ; n = n + 1
    INC A
    ST N_L, A
    JNZ NEXT_N              ; the low byte didn't wrap around
    LD A, N_H
    INC A
    ST N_H, A
    JMP NEXT_N

DONE:
    HALT
    JMP DONE                ; only reached if HALT doesn't stop the CPU

.INCLUDE "lib/max7219.asm"
