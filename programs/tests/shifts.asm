; ==============================================================================
; Test Program: SHR and ROR
; ==============================================================================
; digital/tests/check_cpu.py runs it on CPU.dig and on the emulator. It's apart
; from all_instructions.asm because in CPU.dig the shifter's output doesn't reach
; the data bus yet (see planning/issues.md), so these are known to be different.

.ORG 0xC000

START:
    MOV A, 0x81
    SHR A
    ST 0x20, A
    MOV A, 0x81
    CP A, 0x00              ; C = 1
    ROR A
    ST 0x21, A
    MOV A, 0x06
    SHR A
    SHR A
    ST 0x22, A

DONE:
    HALT
    JMP DONE
