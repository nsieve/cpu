# Instruction Set Architecture

## Instructions Table

Cycles count every microstep, including the fetch (step 0).

| Mnemonic      | Opcode | subOp |                Pseudocode                |  Flags  | Cycles |
| :------------ | :----: | :---: | :--------------------------------------: | :-----: | :----: |
| MOV REG, Imm  |  0x00  |   -   |                Rd <-- Imm                |    -    |   2    |
| MOV REG, REG  |  0x01  |   -   |                Rd <-- Rs                 |    -    |   2    |
| MOV MARL, Imm |  0x02  |  0x0  |               MARL <-- Imm               |    -    |   2    |
| MOV MARH, Imm |  0x02  |  0x1  |               MARH <-- Imm               |    -    |   2    |
| INC MAR       |  0x02  |  0x2  |             MAR <-- MAR + 1              |    -    |   2    |
| DEC MAR       |  0x02  |  0x3  |             MAR <-- MAR - 1              |    -    |   2    |
| INC XY        |  0x02  |  0x4  |              XY <-- XY + 1               |    -    |   2    |
| DEC XY        |  0x02  |  0x5  |              XY <-- XY - 1               |    -    |   2    |
| ST XY+, REG   |  0x02  |  0x6  |     Mem[XY] <-- Rs<br>XY <-- XY + 1      |    -    |   2    |
| ST MAR+, REG  |  0x02  |  0x7  |    Mem[MAR] <-- Rs<br>MAR <-- MAR + 1    |    -    |   2    |
| MOV MARL, REG |  0x03  |  0x0  |               MARL <-- Rs                |    -    |   2    |
| MOV MARH, REG |  0x03  |  0x1  |               MARH <-- Rs                |    -    |   2    |
| LD REG, Imm   |  0x04  |   -   |           Rd <-- Mem[0x00:Imm]           |    -    |   2    |
| LD REG, MAR   |  0x05  |   -   |             Rd <-- Mem[MAR]              |    -    |   2    |
| LD REG, XY    |  0x06  |   -   |              Rd <-- Mem[XY]              |    -    |   2    |
| ST Imm, REG   |  0x07  |   -   |           Mem[0x00:Imm] <-- Rs           |    -    |   2    |
| ST MAR, REG   |  0x08  |   -   |             Mem[MAR] <-- Rs              |    -    |   2    |
| ST XY, REG    |  0x09  |   -   |              Mem[XY] <-- Rs              |    -    |   2    |
| PUSH REG      |  0x0A  |   -   |     Mem[SP] <-- Rs<br>SP <-- SP - 1      |    -    |   2    |
| POP REG       |  0x0B  |   -   |     SP <-- SP + 1<br>Rd <-- Mem[SP]      |    -    |   3    |
| ADD A, REG    |  0x0C  |  0x0  |               A <-- A + Rs               | Z,C,N,V |   2    |
| ADC A, REG    |  0x0C  |  0x1  |             A <-- A + Rs + C             | Z,C,N,V |   2    |
| SUB A, REG    |  0x0C  |  0x2  |               A <-- A - Rs               | Z,C,N,V |   2    |
| SBC A, REG    |  0x0C  |  0x3  |           A <-- A - Rs - 1 + C           | Z,C,N,V |   2    |
| AND A, REG    |  0x0C  |  0x4  |               A <-- A & Rs               |   Z,N   |   2    |
| OR A, REG     |  0x0C  |  0x5  |              A <-- A \| Rs               |   Z,N   |   2    |
| XOR A, REG    |  0x0C  |  0x6  |              A <-- A (+) Rs              |   Z,N   |   2    |
| CP A, REG     |  0x0C  |  0x7  |                  A - Rs                  | Z,C,N,V |   2    |
| ADD A, Imm    |  0x0D  |  0x0  |              A <-- A + Imm               | Z,C,N,V |   2    |
| ADC A, Imm    |  0x0D  |  0x1  |            A <-- A + Imm + C             | Z,C,N,V |   2    |
| SUB A, Imm    |  0x0D  |  0x2  |              A <-- A - Imm               | Z,C,N,V |   2    |
| SBC A, Imm    |  0x0D  |  0x3  |          A <-- A - Imm - 1 + C           | Z,C,N,V |   2    |
| AND A, Imm    |  0x0D  |  0x4  |              A <-- A & Imm               |   Z,N   |   2    |
| OR A, Imm     |  0x0D  |  0x5  |              A <-- A \| Imm              |   Z,N   |   2    |
| XOR A, Imm    |  0x0D  |  0x6  |             A <-- A (+) Imm              |   Z,N   |   2    |
| CP A, Imm     |  0x0D  |  0x7  |                 A - Imm                  | Z,C,N,V |   2    |
| ADD A, [Imm]  |  0x0E  |  0x0  |         A <-- A + Mem[0x00:Imm]          | Z,C,N,V |   2    |
| ADC A, [Imm]  |  0x0E  |  0x1  |       A <-- A + Mem[0x00:Imm] + C        | Z,C,N,V |   2    |
| SUB A, [Imm]  |  0x0E  |  0x2  |         A <-- A - Mem[0x00:Imm]          | Z,C,N,V |   2    |
| SBC A, [Imm]  |  0x0E  |  0x3  |     A <-- A - Mem[0x00:Imm] - 1 + C      | Z,C,N,V |   2    |
| AND A, [Imm]  |  0x0E  |  0x4  |         A <-- A & Mem[0x00:Imm]          |   Z,N   |   2    |
| OR A, [Imm]   |  0x0E  |  0x5  |         A <-- A \| Mem[0x00:Imm]         |   Z,N   |   2    |
| XOR A, [Imm]  |  0x0E  |  0x6  |        A <-- A (+) Mem[0x00:Imm]         |   Z,N   |   2    |
| CP A, [Imm]   |  0x0E  |  0x7  |            A - Mem[0x00:Imm]             | Z,C,N,V |   2    |
| ADD A, [XY]   |  0x0F  |  0x0  |            A <-- A + Mem[XY]             | Z,C,N,V |   2    |
| ADC A, [XY]   |  0x0F  |  0x1  |          A <-- A + Mem[XY] + C           | Z,C,N,V |   2    |
| SUB A, [XY]   |  0x0F  |  0x2  |            A <-- A - Mem[XY]             | Z,C,N,V |   2    |
| SBC A, [XY]   |  0x0F  |  0x3  |        A <-- A - Mem[XY] - 1 + C         | Z,C,N,V |   2    |
| AND A, [XY]   |  0x0F  |  0x4  |            A <-- A & Mem[XY]             |   Z,N   |   2    |
| OR A, [XY]    |  0x0F  |  0x5  |            A <-- A \| Mem[XY]            |   Z,N   |   2    |
| XOR A, [XY]   |  0x0F  |  0x6  |           A <-- A (+) Mem[XY]            |   Z,N   |   2    |
| CP A, [XY]    |  0x0F  |  0x7  |               A - Mem[XY]                | Z,C,N,V |   2    |
| LD REG, XY+   |  0x10  |   -   |     Rd <-- Mem[XY]<br>XY <-- XY + 1      |    -    |   2    |
| LD REG, MAR+  |  0x11  |   -   |    Rd <-- Mem[MAR]<br>MAR <-- MAR + 1    |    -    |   2    |
| INC A         |  0x15  |   -   |               A <-- A + 1                | Z,C,N,V |   2    |
| DEC A         |  0x16  |   -   |               A <-- A - 1                | Z,C,N,V |   2    |
| SHR A         |  0x17  |   -   |      A <-- {0, A[7:1]}<br>C <-- A[0]     |   C,V   |   2    |
| ROR A         |  0x18  |   -   |      A <-- {C, A[7:1]}<br>C <-- A[0]     |   C,V   |   2    |
| RETC          |  0x19  |  0x0  | if (C == 1):<br>SP + 2<br>PC <-- Mem[SP] |    -    | 5 / 2  |
| RETNC         |  0x19  |  0x1  | if (C == 0):<br>SP + 2<br>PC <-- Mem[SP] |    -    | 5 / 2  |
| RETZ          |  0x19  |  0x2  | if (Z == 1):<br>SP + 2<br>PC <-- Mem[SP] |    -    | 5 / 2  |
| RETNZ         |  0x19  |  0x3  | if (Z == 0):<br>SP + 2<br>PC <-- Mem[SP] |    -    | 5 / 2  |
| RETN          |  0x19  |  0x4  | if (N == 1):<br>SP + 2<br>PC <-- Mem[SP] |    -    | 5 / 2  |
| RETNN         |  0x19  |  0x5  | if (N == 0):<br>SP + 2<br>PC <-- Mem[SP] |    -    | 5 / 2  |
| RETV          |  0x19  |  0x6  | if (V == 1):<br>SP + 2<br>PC <-- Mem[SP] |    -    | 5 / 2  |
| RETNV         |  0x19  |  0x7  | if (V == 0):<br>SP + 2<br>PC <-- Mem[SP] |    -    | 5 / 2  |
| CALLC label   |  0x1A  |  0x0  | if (C == 1):<br>Mem[SP] <-- PC<br>SP - 2<br>PC <-- imm16 |    -    | 7 / 3  |
| CALLNC label  |  0x1A  |  0x1  | if (C == 0):<br>Mem[SP] <-- PC<br>SP - 2<br>PC <-- imm16 |    -    | 7 / 3  |
| CALLZ label   |  0x1A  |  0x2  | if (Z == 1):<br>Mem[SP] <-- PC<br>SP - 2<br>PC <-- imm16 |    -    | 7 / 3  |
| CALLNZ label  |  0x1A  |  0x3  | if (Z == 0):<br>Mem[SP] <-- PC<br>SP - 2<br>PC <-- imm16 |    -    | 7 / 3  |
| CALLN label   |  0x1A  |  0x4  | if (N == 1):<br>Mem[SP] <-- PC<br>SP - 2<br>PC <-- imm16 |    -    | 7 / 3  |
| CALLNN label  |  0x1A  |  0x5  | if (N == 0):<br>Mem[SP] <-- PC<br>SP - 2<br>PC <-- imm16 |    -    | 7 / 3  |
| CALLV label   |  0x1A  |  0x6  | if (V == 1):<br>Mem[SP] <-- PC<br>SP - 2<br>PC <-- imm16 |    -    | 7 / 3  |
| CALLNV label  |  0x1A  |  0x7  | if (V == 0):<br>Mem[SP] <-- PC<br>SP - 2<br>PC <-- imm16 |    -    | 7 / 3  |
| JC label      |  0x1B  |  0x0  |       if (C == 1):<br>PC <-- imm16       |    -    | 5 / 3  |
| JNC label     |  0x1B  |  0x1  |       if (C == 0):<br>PC <-- imm16       |    -    | 5 / 3  |
| JZ label      |  0x1B  |  0x2  |       if (Z == 1):<br>PC <-- imm16       |    -    | 5 / 3  |
| JNZ label     |  0x1B  |  0x3  |       if (Z == 0):<br>PC <-- imm16       |    -    | 5 / 3  |
| JN label      |  0x1B  |  0x4  |       if (N == 1):<br>PC <-- imm16       |    -    | 5 / 3  |
| JNN label     |  0x1B  |  0x5  |       if (N == 0):<br>PC <-- imm16       |    -    | 5 / 3  |
| JV label      |  0x1B  |  0x6  |       if (V == 1):<br>PC <-- imm16       |    -    | 5 / 3  |
| JNV label     |  0x1B  |  0x7  |       if (V == 0):<br>PC <-- imm16       |    -    | 5 / 3  |
| JC XY         |  0x1C  |  0x0  |        if (C == 1):<br>PC <-- XY         |    -    |   2    |
| JNC XY        |  0x1C  |  0x1  |        if (C == 0):<br>PC <-- XY         |    -    |   2    |
| JZ XY         |  0x1C  |  0x2  |        if (Z == 1):<br>PC <-- XY         |    -    |   2    |
| JNZ XY        |  0x1C  |  0x3  |        if (Z == 0):<br>PC <-- XY         |    -    |   2    |
| JN XY         |  0x1C  |  0x4  |        if (N == 1):<br>PC <-- XY         |    -    |   2    |
| JNN XY        |  0x1C  |  0x5  |        if (N == 0):<br>PC <-- XY         |    -    |   2    |
| JV XY         |  0x1C  |  0x6  |        if (V == 1):<br>PC <-- XY         |    -    |   2    |
| JNV XY        |  0x1C  |  0x7  |        if (V == 0):<br>PC <-- XY         |    -    |   2    |
| JMP label     |  0x1D  |  0x0  |               PC <-- imm16               |    -    |   5    |
| CALL label    |  0x1D  |  0x1  | Mem[SP] <-- PC<br>SP - 2<br>PC <-- imm16 |    -    |   7    |
| JMP MAR       |  0x1D  |  0x2  |                PC <-- MAR                |    -    |   2    |
| JMP XY        |  0x1D  |  0x3  |                PC <-- XY                 |    -    |   2    |
| CALL MAR      |  0x1D  |  0x4  |  Mem[SP] <-- PC<br>SP - 2<br>PC <-- MAR  |    -    |   5    |
| CALL XY       |  0x1D  |  0x5  |  Mem[SP] <-- PC<br>SP - 2<br>PC <-- XY   |    -    |   5    |
| MOV SP, MAR   |  0x1E  |  0x0  |                SP <-- MAR                |    -    |   2    |
| MOV MAR, SP   |  0x1E  |  0x1  |                MAR <-- SP                |    -    |   3    |
| MOV SP, XY    |  0x1E  |  0x2  |                SP <-- XY                 |    -    |   2    |
| INC SP        |  0x1E  |  0x3  |              SP <-- SP + 1               |    -    |   2    |
| DEC SP        |  0x1E  |  0x4  |              SP <-- SP - 1               |    -    |   2    |
| MOV X, SPH    |  0x1E  |  0x6  |                X <-- SPH                 |    -    |   2    |
| MOV Y, SPL    |  0x1E  |  0x7  |                Y <-- SPL                 |    -    |   2    |
| LDT A, XY     |  0x1F  |  0x0  |           A <-- ROM[XY][7:0]             |    -    |   3    |
| RET           |  0x1F  |  0x1  |         SP + 2<br>PC <-- Mem[SP]         |    -    |   5    |
| LDT A, XY+    |  0x1F  |  0x2  |   A <-- ROM[XY][7:0]<br>XY <-- XY + 1    |    -    |   3    |
| PUSHF         |  0x1F  |  0x5  |     Mem[SP] <-- FR<br>SP <-- SP - 1      |    -    |   2    |
| POPF          |  0x1F  |  0x6  |     SP <-- SP + 1<br>FR <-- Mem[SP]      | Z,C,N,V |   3    |
| HALT          |  0x1F  |  0x7  |           freeze the micro-PC            |    -    |   3    |

`5 / 3` on the conditional jumps means 5 cycles if the jump is taken and 3 if it isn't (it just skips the second word). The conditional calls (`7 / 3`) and returns (`5 / 2`) work the same way.

### Notes

- Condition codes (subOp of 0x19, 0x1A, 0x1B and 0x1C): 0 = C, 1 = NC, 2 = Z, 3 = NZ, 4 = N, 5 = NN, 6 = V, 7 = NV. There is no `JCC MAR`, only `JCC XY` and `JCC label`, and the conditional calls only exist with a label (`CALLZ label`).
- Direct jumps and calls (`JMP label`, `JCC label`, `CALL label`, `CALLcc label`) are 2-word instructions: word 1 has the opcode + the high byte of the target, word 2 has the opcode + the low byte. The CPU uses the MAR to hold the target before loading it into the PC, so whatever was in the MAR is lost after a direct jump or call (and after `RET` and `RETcc` too, which also go through the MAR). For the conditional ones, only when they're taken. More about this in `design-decisions/jumps.md`.
- CALL pushes PCH first and then PCL, so `RET` pops PCL first and then PCH. The pushed PC is always the address of the instruction right after the CALL.
- ST Imm and LD Imm keep the register in bits `[10:8]`, because the whole lower byte is the zero-page address. For the store, the control bit `SRC_SEL` makes the source decoder read the register from `[10:8]` instead of `[7:5]`. More about this in `design-decisions/st-zeropage.md`.
- CP does the same as SUB, but only updates the flags, A is not written.
- HALT freezes the micro-PC in step 2 with `nHALT`, after the PC already points to the next instruction. The CPU stays there until a reset. More about this in `hardware-design/controlunit.md`.
- ALU operations: 0x0C is the ALU with a register (Rs in `[7:5]`), 0x0D with an immediate, 0x0E with a byte of the zero page (`SUB A, [var]` is A - Mem[0x00:var]) and 0x0F with the byte at XY (`SUB A, [XY]`, or just `SUB A, XY`), and the subOp is the operation: 0 ADD, 1 ADC, 2 SUB, 3 SBC, 4 AND, 5 OR, 6 XOR, 7 CP. The result goes into A with `nA_LD`, which loads A without the register file's decoder, so `[10:8]` can be the subOp (with `REG_LD` it would load the register numbered in `[10:8]`).
- The brackets only mean memory in the ALU instructions, where `SUB A, 0x20` already means the number 0x20. LD and ST don't change: `LD A, 0x20` reads the zero page, like before.
- AND / OR / XOR only load Z and N (`nFLZN_LD`), so C and V keep the value they had.
- PUSHF / POPF: the flags byte on the stack is `0000VCNZ` (Z in bit 0, N in bit 1, C in bit 2, V in bit 3).
- INC A / DEC A don't use the carry, they force the carry-in: INC A is A + 0 + 1, and DEC A is A - 0 - 1.
- Free slots: the whole opcodes 0x12-0x14 (old ALU opcodes, from before the ALU was grouped in 0x0C and 0x0D), 0x03 subOp 2-7, 0x1D subOp 6-7, 0x1E subOp 5 and 0x1F subOp 3, 4 (these were interrupt instructions). If one gets executed, it works as a NOP: 2 cycles, and nothing changes except the PC.

- SHR A / ROR A: the bit shifted out (A[0]) goes into C, and V is cleared. While `nSHR_OE` is on, a 74157 in the ALU puts A[0] and 0 on the ALU's C and V outputs, and the shifts load them with `nFLCV_LD`. Z and N don't change.
- ROR A: the old C goes into bit 7 (the microcode sets `SHR_IN0` only when C = 1), so it's a rotate through the carry. `SHR` on the high byte and then `ROR` on the low byte shift 16 bits right.
- LDT A, XY: reads a table from the ROM. In step 1 only the IR's low byte loads from the ROM word at XY, so the opcode the control unit sees stays LDT's, and in step 2 that byte goes to A. XY must point into the ROM (0xC000-0xFFFF). The assembler's `.TABLE` directive writes one byte per word, with LDT's opcode (0xF8) in the high byte.
- LDT A, XY+ does the same and then XY + 1, to read a table byte after byte. Its subOp is 2, so in step 2 A loads with `nA_LD` (`REG_LD` would load C, register 2).
- Auto-increment (`ST XY+`, `ST MAR+`, `LD REG, XY+`, `LD REG, MAR+`, `LDT A, XY+`): the access uses the address from before, and the register counts on the clock edge at the end of the step, so the increment doesn't cost a cycle. `LD REG, XY+` only works with A-F, because X and Y can't load while XY counts (the assembler rejects `LD X, XY+` and `LD Y, XY+`). `ST XY+, X` and `ST XY+, Y` store the value from before the increment.

Open problems are in `planning/issues.md`.

## Pseudo-Instructions Table

These don't exist in hardware, the assembler just translates them into one or two real instructions.

| Pseudo-instruction | Assembled as | Cycles |
| :----------------- | :----------- | :----: |
| NOP                | MOV A, A     |   2    |
| SHL A              | ADD A, A     |   2    |
| ROL A              | ADC A, A     |   2    |
| PUSH XY            | PUSH X<br>PUSH Y |   4    |
| POP XY             | POP Y<br>POP X   |   6    |

Direct jumps (`JMP label`, `JCC label`, `CALL label`, `CALLcc label`) are NOT pseudo-instructions, they are native 2-word instructions.

`POP XY` can't be one instruction: the register file's decoder only loads the register numbered in `[10:8]`, so one instruction can't load both X and Y.
