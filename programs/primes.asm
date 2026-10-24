; ==============================================================================
; Prime numbers: the Sieve of Eratosthenes, shown on the 7-segment display
; ==============================================================================
; The sieve is one byte of RAM per number, starting at SIEVE (0 = still possibly
; prime, 1 = crossed out). 2 is shown first, and then it goes through the odd
; numbers from 3 up:
;   - if a number isn't crossed out, it's prime: show it, and cross out its odd
;     multiples (3n, 5n, 7n ...) by adding 2n to a pointer, so no multiplication.
;     The even numbers are never checked, so their bytes are never used
;   - if it is crossed out, skip it
; The LEDs show the pages being cleared at the start, and then how many primes
; have been found (low byte).
;
; LIMIT sets how far it goes. Up to 5000 there are 669 primes. It can go up to
; 47,000 (the sieve has to fit in the RAM below the stack), but in Digital that
; takes very long: the small primes have thousands of multiples to cross out.

.EQU LIMIT   5000           ; last number checked (47,000 at most: the sieve has to fit below the stack)
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

    ; 2 is the only even prime: show it first, then check only the odd numbers
    MOV A, 2
    ST NUM_L, A
    MOV A, 0
    ST NUM_H, A
    CALL SHOW_DEC
    MOV A, 1
    ST FOUND, A
    CALL SHOW_LEDS
    MOV A, 3                ; n = 3
    ST N_L, A
    MOV A, 0
    ST N_H, A

NEXT_N:
    LD A, N_H               ; XY = SIEVE + n (SIEVE's low byte is 0, so only X changes)
    MOV B, HIGH:SIEVE
    ADD A, B
    MOV X, A
    LD A, N_L
    MOV Y, A
    MOV B, LOW:SV_END       ; XY - SV_END, only to look at the borrow
    SUB A, B
    MOV A, X
    MOV B, HIGH:SV_END
    SBC A, B
    JC DONE                 ; no borrow: XY >= SV_END, so n > LIMIT
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

    ; cross out its odd multiples (3n, 5n, 7n ...): the even ones are never checked.
    ; XY = SIEVE + n, then add 2n each time
    LD A, N_H
    MOV B, HIGH:SIEVE
    ADD A, B
    MOV X, A
    LD A, N_L
    MOV Y, A
    LD A, N_L               ; C:D = 2n (D = high byte)
    ADD A, A
    MOV C, A
    LD A, N_H               ; LD and MOV don't change the flags, so the ADC gets the carry
    ADC A, A
    MOV D, A
    JC SKIP                 ; 2n doesn't fit in 16 bits (n > 32767): 3n is past any sieve, nothing to cross out
MARK:
    MOV A, Y                ; XY = XY + 2n
    ADD A, C
    MOV Y, A
    MOV A, X
    ADC A, D
    MOV X, A
    JC SKIP                 ; XY + 2n went past 0xFFFF (MOV doesn't change the flags), so it's past the end too
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
    LD A, N_L               ; n = n + 2
    ADD A, 2
    ST N_L, A
    LD A, N_H
    MOV B, 0
    ADC A, B
    ST N_H, A
    JMP NEXT_N

DONE:
    HALT
    JMP DONE                ; only reached if HALT doesn't stop the CPU

.INCLUDE "lib/max7219.asm"
