; ==============================================================================
; Test Program: every instruction at least once (except SHR and ROR)
; ==============================================================================
; It doesn't check itself: digital/tests/check_cpu.py runs it on CPU.dig and on
; the emulator and compares them cycle by cycle. Results also go to RAM, so a
; wrong value shows up in the final RAM too. If a conditional jump goes the wrong
; way it ends in BAD (A = 0xEE). The shifts are in shifts.asm, because CPU.dig
; doesn't do them right yet.

.ORG 0xC000

START:
    ; ---- moves ----
    MOV A, 0x11
    MOV B, 0x22
    MOV C, 0x33
    MOV D, 0x44
    MOV E, 0x55
    MOV F, 0x66
    MOV X, 0x77
    MOV Y, 0x88
    MOV A, Y
    MOV B, X
    MOV C, A
    MOV X, F
    MOV Y, E
    MOV D, D
    MOV E, B
    MOV F, C

    ; ---- zero page: store every register, load into every register ----
    ST 0x20, A
    ST 0x41, B
    ST 0x62, C
    ST 0x83, D
    ST 0xA4, E
    ST 0xC5, F
    ST 0xE6, X
    ST 0x07, Y
    LD A, 0x07
    LD B, 0xE6
    LD C, 0xC5
    LD D, 0xA4
    LD E, 0x83
    LD F, 0x62
    LD X, 0x41
    LD Y, 0x20

    ; ---- stack pointer ----
    MOV X, 0xBA
    MOV Y, 0xFF
    MOV SP, XY
    MOV MAR, SP
    INC MAR
    MOV SP, MAR
    DEC SP
    DEC SP
    INC SP
    MOV X, SPH
    MOV Y, SPL
    ST 0x08, X
    ST 0x09, Y

    ; ---- MAR ----
    MOV MARH, 0x10
    MOV MARL, 0xFF
    INC MAR                 ; 0x1100
    ST MAR, A
    DEC MAR                 ; 0x10FF
    ST MAR, B
    LD C, MAR
    MOV D, 0x34
    MOV E, 0x12
    MOV MARL, D
    MOV MARH, E             ; 0x1234
    ST MAR, C
    ST MAR, X
    LD F, MAR

    ; ---- XY ----
    MOV X, 0x20
    MOV Y, 0xFF
    INC XY                  ; 0x2100
    ST XY, A
    DEC XY                  ; 0x20FF
    ST XY, X
    LD D, XY
    ST XY, Y
    LD E, XY

    ; ---- push / pop ----
    MOV A, 0xA1
    MOV B, 0xB2
    MOV X, 0xC3
    MOV Y, 0xD4
    PUSH A
    PUSH B
    PUSH X
    PUSH Y
    POP C
    POP D
    POP E
    POP F
    PUSH C
    POP A

    ; ---- ALU with registers (PUSHF keeps every result's flags) ----
    MOV A, 0x7F
    MOV B, 0x01
    ADD A, B                ; 0x80, N V
    PUSHF
    ADC A, B                ; C = 0
    PUSHF
    MOV A, 0xFF
    ADD A, B                ; 0x00, Z C
    PUSHF
    ADC A, B                ; C = 1
    PUSHF
    MOV C, 0x90
    SUB A, C
    PUSHF
    SBC A, C
    PUSHF
    SBC A, B
    PUSHF
    MOV D, 0xF0
    MOV E, 0x3C
    MOV A, D
    AND A, E
    PUSHF
    OR A, D
    PUSHF
    XOR A, E
    PUSHF
    CP A, E
    PUSHF
    MOV X, 0x55
    MOV Y, 0xAA
    ADD A, X
    ADD A, Y
    SUB A, X
    AND A, Y
    OR A, X
    XOR A, Y
    ADD A, A
    ADC A, A
    CP A, A
    PUSHF
    ST 0x30, A

    ; ---- ALU with immediates ----
    MOV A, 0x10
    ADD A, 0xF5
    PUSHF
    AND A, 0x0F
    PUSHF
    CP A, 0x05
    PUSHF
    CP A, 0x06
    PUSHF
    ST 0x31, A

    ; ---- INC / DEC ----
    MOV A, 0x7F
    INC A                   ; 0x80, V
    PUSHF
    MOV A, 0xFF
    INC A                   ; 0x00, Z C
    PUSHF
    DEC A                   ; 0xFF, borrow
    PUSHF
    MOV A, 0x80
    DEC A                   ; 0x7F, V
    PUSHF
    ST 0x32, A

    ; ---- flags ----
    MOV A, 0x05
    CP A, 0x06              ; 0xFF: N, borrow
    PUSHF
    POP B
    ST 0x35, B
    MOV A, 0x0B             ; Z C N V all set
    PUSH A
    POPF
    PUSHF
    POP C
    ST 0x36, C

    ; ---- conditional jumps, each one taken and not taken ----
    MOV A, 0x05
    CP A, 0x05              ; Z C
    JNZ BAD
    JZ J1
    JMP BAD
J1:
    JNC BAD
    JC J2
    JMP BAD
J2:
    CP A, 0x06              ; N, no carry
    JNN BAD
    JN J3
    JMP BAD
J3:
    JC BAD
    JNC J4
    JMP BAD
J4:
    JZ BAD
    JNZ J5
    JMP BAD
J5:
    MOV A, 0x80
    CP A, 0x01              ; 0x7F, V
    JNV BAD
    JV J6
    JMP BAD
J6:
    CP A, 0x80              ; 0x00, no V
    JV BAD
    JNV J7
    JMP BAD
J7:

    ; ---- conditional jumps to XY ----
    MOV X, HIGH:J8
    MOV Y, LOW:J8
    JNZ XY                  ; Z = 1 from the last CP: not taken
    JZ XY
    JMP BAD
J8:
    MOV X, HIGH:J9
    MOV Y, LOW:J9
    JNC XY                  ; C = 1: not taken
    JC XY
    JMP BAD
J9:
    MOV X, HIGH:J10
    MOV Y, LOW:J10
    JN XY                   ; N = 0: not taken
    JNN XY
    JMP BAD
J10:
    MOV X, HIGH:J11
    MOV Y, LOW:J11
    JV XY                   ; V = 0: not taken
    JNV XY
    JMP BAD
J11:

    ; ---- jumps and calls ----
    MOV MARH, HIGH:K1
    MOV MARL, LOW:K1
    JMP MAR
    JMP BAD
K1:
    MOV X, HIGH:K2
    MOV Y, LOW:K2
    JMP XY
    JMP BAD
K2:
    MOV A, 0
    CALL SUB1
    MOV MARH, HIGH:SUB1
    MOV MARL, LOW:SUB1
    CALL MAR
    MOV X, HIGH:SUB1
    MOV Y, LOW:SUB1
    CALL XY
    ST 0x37, A              ; 3 if the 3 calls came back

    ; ---- free slots, they work as NOPs ----
    .RAW 0x1600
    .RAW 0x1A00
    .RAW 0xEE00
    .RAW 0xF500
    .RAW 0xF800

    ; ---- MMIO ----
    MOV X, 0xBF
    MOV Y, 0x03
    MOV A, 0x5A
    ST XY, A                ; LEDs
    MOV Y, 0x02
    MOV A, 0x18
    ST XY, A                ; SPI_OUT, both CS high
    MOV Y, 0x01
    LD B, XY                ; keyboard status
    MOV Y, 0x00
    LD C, XY                ; keyboard data
    ST 0x38, B
    ST 0x39, C

DONE:
    HALT
    JMP DONE

SUB1:
    INC A
    RET

BAD:
    MOV A, 0xEE
    HALT
    JMP BAD
