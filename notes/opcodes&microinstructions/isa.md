# Instruction Set Architecture

## Instructions Table

Cycles count every microstep, including the fetch (step 0).

| Mnemonic      | Opcode | subOp |               Pseudocode                |  Flags   |  Cycles   |
| :------------ | :----: | :---: | :-------------------------------------: | :------: | :-------: |
| MOV REG, Imm  |  0x00  |   -   |               Rd <-- Imm                |    -     |     2     |
| MOV REG, REG  |  0x01  |   -   |                Rd <-- Rs                |    -     |     2     |
| MOV MARL, Imm |  0x02  |  0x0  |              MARL <-- Imm               |    -     |     2     |
| MOV MARH, Imm |  0x02  |  0x1  |              MARH <-- Imm               |    -     |     2     |
| INC MAR       |  0x02  |  0x2  |             MAR <-- MAR + 1             |    -     |     2     |
| DEC MAR       |  0x02  |  0x3  |             MAR <-- MAR - 1             |    -     |     2     |
| INC XY        |  0x02  |  0x4  |              XY <-- XY + 1              |    -     |     2     |
| DEC XY        |  0x02  |  0x5  |              XY <-- XY - 1              |    -     |     2     |
| MOV MARL, REG |  0x03  |  0x0  |               MARL <-- Rs               |    -     |     2     |
| MOV MARH, REG |  0x03  |  0x1  |               MARH <-- Rs               |    -     |     2     |
| LD REG, Imm   |  0x04  |   -   |          Rd <-- Mem[0x00:Imm]           |    -     |     2     |
| LD REG, MAR   |  0x05  |   -   |             Rd <-- Mem[MAR]             |    -     |     2     |
| LD REG, XY    |  0x06  |   -   |             Rd <-- Mem[XY]              |    -     |     2     |
| ST Imm, REG   |  0x07  |   -   |          Mem[0x00:Imm] <-- Rs           |    -     |     2     |
| ST MAR, REG   |  0x08  |   -   |             Mem[MAR] <-- Rs             |    -     |     2     |
| ST XY, REG    |  0x09  |   -   |             Mem[XY] <-- Rs              |    -     |     2     |
| PUSH REG      |  0x0A  |   -   |     Mem[SP] <-- Rs<br>SP <-- SP - 1     |    -     |     2     |
| POP REG       |  0x0B  |   -   |     SP <-- SP + 1<br>Rd <-- Mem[SP]     |    -     |     3     |
| ADD A, REG    |  0x0C  |   -   |              A <-- A + Rs               | Z,C,N,V  |     2     |
| ADD A, Imm    |  0x0D  |   -   |              A <-- A + Imm              | Z,C,N,V  |     2     |
| ADC A, REG    |  0x0E  |   -   |            A <-- A + Rs + C             | Z,C,N,V  |     2     |
| SUB A, REG    |  0x0F  |   -   |              A <-- A - Rs               | Z,C,N,V  |     2     |
| SBC A, REG    |  0x10  |   -   |          A <-- A - Rs - 1 + C           | Z,C,N,V  |     2     |
| AND A, REG    |  0x11  |   -   |              A <-- A & Rs               |   Z,N*   |     2     |
| AND A, Imm    |  0x12  |   -   |              A <-- A & Imm              |   Z,N*   |     2     |
| OR A, REG     |  0x13  |   -   |              A <-- A \| Rs              |   Z,N*   |     2     |
| XOR A, REG    |  0x14  |   -   |             A <-- A (+) Rs              |   Z,N*   |     2     |
| INC A         |  0x15  |   -   |               A <-- A + 1               | Z,C,N,V  |     2     |
| DEC A         |  0x16  |   -   |               A <-- A - 1               | Z,C,N,V  |     2     |
| SHR A         |  0x17  |   -   |          A <-- {0, A[7:1]}              |    -     |     2     |
| ROR A         |  0x18  |   -   |            A <-- {C, A[7:1]}            |    -     |    2*     |
| CP A, REG     |  0x19  |   -   |                 A - Rs                  | Z,C,N,V  |     2     |
| CP A, Imm     |  0x1A  |   -   |                 A - Imm                 | Z,C,N,V  |     2     |
| JC label      |  0x1B  |  0x0  |       if (C == 1):<br>PC <-- imm16       |    -     | 5 / 3     |
| JNC label     |  0x1B  |  0x1  |       if (C == 0):<br>PC <-- imm16       |    -     | 5 / 3     |
| JZ label      |  0x1B  |  0x2  |       if (Z == 1):<br>PC <-- imm16       |    -     | 5 / 3     |
| JNZ label     |  0x1B  |  0x3  |       if (Z == 0):<br>PC <-- imm16       |    -     | 5 / 3     |
| JN label      |  0x1B  |  0x4  |       if (N == 1):<br>PC <-- imm16       |    -     | 5 / 3     |
| JNN label     |  0x1B  |  0x5  |       if (N == 0):<br>PC <-- imm16       |    -     | 5 / 3     |
| JV label      |  0x1B  |  0x6  |       if (V == 1):<br>PC <-- imm16       |    -     | 5 / 3     |
| JNV label     |  0x1B  |  0x7  |       if (V == 0):<br>PC <-- imm16       |    -     | 5 / 3     |
| JC XY         |  0x1C  |  0x0  |        if (C == 1):<br>PC <-- XY         |    -     |     2     |
| JNC XY        |  0x1C  |  0x1  |        if (C == 0):<br>PC <-- XY         |    -     |     2     |
| JZ XY         |  0x1C  |  0x2  |        if (Z == 1):<br>PC <-- XY         |    -     |     2     |
| JNZ XY        |  0x1C  |  0x3  |        if (Z == 0):<br>PC <-- XY         |    -     |     2     |
| JN XY         |  0x1C  |  0x4  |        if (N == 1):<br>PC <-- XY         |    -     |     2     |
| JNN XY        |  0x1C  |  0x5  |        if (N == 0):<br>PC <-- XY         |    -     |     2     |
| JV XY         |  0x1C  |  0x6  |        if (V == 1):<br>PC <-- XY         |    -     |     2     |
| JNV XY        |  0x1C  |  0x7  |        if (V == 0):<br>PC <-- XY         |    -     |     2     |
| JMP label     |  0x1D  |  0x0  |              PC <-- imm16               |    -     |     5     |
| CALL label    |  0x1D  |  0x1  | Mem[SP] <-- PC<br>SP - 2<br>PC <-- imm16 |    -     |     7     |
| JMP MAR       |  0x1D  |  0x2  |               PC <-- MAR                |    -     |     2     |
| JMP XY        |  0x1D  |  0x3  |                PC <-- XY                |    -     |     2     |
| CALL MAR      |  0x1D  |  0x4  |  Mem[SP] <-- PC<br>SP - 2<br>PC <-- MAR  |    -     |     5     |
| CALL XY       |  0x1D  |  0x5  |  Mem[SP] <-- PC<br>SP - 2<br>PC <-- XY   |    -     |     5     |
| MOV SP, MAR   |  0x1E  |  0x0  |               SP <-- MAR                |    -     |     2     |
| MOV MAR, SP   |  0x1E  |  0x1  |               MAR <-- SP                |    -     |     3     |
| MOV SP, XY    |  0x1E  |  0x2  |                SP <-- XY                |    -     |     2     |
| INC SP        |  0x1E  |  0x3  |              SP <-- SP + 1              |    -     |     2     |
| DEC SP        |  0x1E  |  0x4  |              SP <-- SP - 1              |    -     |     2     |
| MOV X, SPH    |  0x1E  |  0x6  |                X <-- SPH                |    -     |     2     |
| MOV Y, SPL    |  0x1E  |  0x7  |                Y <-- SPL                |    -     |     2     |
| RET           |  0x1F  |  0x1  |          SP + 2<br>PC <-- Mem[SP]         |    -     |     5     |
| PUSHF         |  0x1F  |  0x5  |     Mem[SP] <-- FR<br>SP <-- SP - 1     |    -     |     2     |
| POPF          |  0x1F  |  0x6  |     SP <-- SP + 1<br>FR <-- Mem[SP]     |  Z,C,N,V |    3*     |
| HALT          |  0x1F  |  0x7  |           freeze the micro-PC           |    -     |     3     |

`5 / 3` on the conditional jumps means 5 cycles if the jump is taken and 3 if it isn't (it just skips the second word).

### Notes

- Condition codes (subOp of 0x1B and 0x1C): 0 = C, 1 = NC, 2 = Z, 3 = NZ, 4 = N, 5 = NN, 6 = V, 7 = NV. There is no `JCC MAR`, only `JCC XY` and `JCC label`.
- Direct jumps and calls (`JMP label`, `JCC label`, `CALL label`) are 2-word instructions: word 1 has the opcode + the high byte of the target, word 2 has the opcode + the low byte. The CPU uses the MAR to hold the target before loading it into the PC, so whatever was in the MAR is lost after a direct jump or call (and after `RET` too, which also goes through the MAR). More about this in `design-decisions/jumps.md`.
- CALL pushes PCH first and then PCL, so `RET` pops PCL first and then PCH. The pushed PC is always the address of the instruction right after the CALL.
- ST Imm and LD Imm keep the register in bits `[10:8]`, because the whole lower byte is the zero-page address. For the store, the control bit `SRC_SEL` makes the source decoder read the register from `[10:8]` instead of `[7:5]`. More about this in `design-decisions/st-zeropage.md`.
- CP does the same as SUB, but only updates the flags, A is not written.
- HALT freezes the micro-PC in step 2 with `nHALT`, after the PC already points to the next instruction. The CPU stays there until a reset. More about this in `hardware-design/controlunit.md`.
- INC A / DEC A don't use the carry, they force the carry-in: INC A is A + 0 + 1, and DEC A is A - 0 - 1.
- Free slots: 0x02 subOp 6-7, 0x03 subOp 2-7, 0x1D subOp 6-7, 0x1E subOp 5 and 0x1F subOp 0, 2, 3, 4 (these last four were the interrupt instructions). If one gets executed, it works as a NOP: 2 cycles, and nothing changes except the PC.

### Known Issues (*)

- AND / OR / XOR: the 4 ALU flags are loaded together, so C and V also get loaded with whatever the 74382 outputs on a logic operation. Only Z and N are meaningful.
- ROR: right now its microcode is exactly the same as SHR (`SHR_IN0` is never set), and shifts don't update the flags, so the bit shifted out doesn't go into C.
- POPF: step 2 loads the flag register but doesn't set `FL_SEL`, so the flags get loaded from the ALU instead of from the data bus.

The full list of open problems is in `planning/issues.md`.

## Pseudo-Instructions Table

These don't exist in hardware, the assembler just translates them into a real instruction.

| Pseudo-instruction | Assembled as | Cycles |
| :----------------- | :----------- | :----: |
| NOP                | MOV A, A     |   2    |
| SHL A              | ADD A, A     |   2    |
| ROL A              | ADC A, A     |   2    |

Direct jumps (`JMP label`, `JCC label`, `CALL label`) are NOT pseudo-instructions, they are native 2-word instructions.
