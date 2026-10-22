; ==============================================================================
; Test Program: ST zp with every register & free opcode slots
; ==============================================================================
; If everything works, the CPU ends up looping on PASS.
; If something fails, it loops on FAIL, and X holds the number of the check
; that failed (1-8: ST zp of A, B, C, D, E, F, X, Y. 9-10: free slots).
;
; The zero-page addresses are picked so that bits [7:5] never match the
; register being stored (with the old ST zp, A-only design, those bits would
; select the wrong register).

.ORG 0xC000

START:
    ; 1. store every register in a different zero-page address
    MOV A, 0x11
    MOV B, 0x22
    MOV C, 0x33
    MOV D, 0x44
    MOV E, 0x55
    MOV F, 0x66
    MOV X, 0x77
    MOV Y, 0x88

    ST 0x25, A
    ST 0x4A, B
    ST 0x6F, C
    ST 0x93, D
    ST 0xB6, E
    ST 0xDC, F
    ST 0xFF, X
    ST 0x00, Y

    ; 2. read them back and check them
    MOV X, 1
    LD A, 0x25
    CP A, 0x11
    JNZ FAIL

    MOV X, 2
    LD A, 0x4A
    CP A, 0x22
    JNZ FAIL

    MOV X, 3
    LD A, 0x6F
    CP A, 0x33
    JNZ FAIL

    MOV X, 4
    LD A, 0x93
    CP A, 0x44
    JNZ FAIL

    MOV X, 5
    LD A, 0xB6
    CP A, 0x55
    JNZ FAIL

    MOV X, 6
    LD A, 0xDC
    CP A, 0x66
    JNZ FAIL

    MOV X, 7
    LD A, 0xFF
    CP A, 0x77
    JNZ FAIL

    MOV X, 8
    LD B, 0x00          ; this one loads into B, to also check LD zp into another register
    MOV A, B
    CP A, 0x88
    JNZ FAIL

    ; 3. free slots: they should do nothing and take 2 cycles each
    ;    (watch the step counter: it should go 0, 1, 0 on each one)
    MOV A, 0x5A
    MOV B, 0xA5
    .RAW 0x1600         ; opcode 2,  subOp 6
    .RAW 0x1A00         ; opcode 3,  subOp 2
    .RAW 0xEE00         ; opcode 29, subOp 6
    .RAW 0xF500         ; opcode 30, subOp 5
    .RAW 0xF800         ; opcode 31, subOp 0 (was BRK)
    .RAW 0xFA00         ; opcode 31, subOp 2 (was RTI)
    .RAW 0xFB00         ; opcode 31, subOp 3 (was SEI)
    .RAW 0xFC00         ; opcode 31, subOp 4 (was CLI)

    MOV X, 9
    CP A, 0x5A
    JNZ FAIL

    MOV X, 10
    MOV A, B
    CP A, 0xA5
    JNZ FAIL

PASS:
    JMP PASS

FAIL:
    JMP FAIL
