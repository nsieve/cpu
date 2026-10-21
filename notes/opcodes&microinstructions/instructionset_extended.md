# Instruction Set

Cycles represent the "steps" in the micro-program counter. They start at 0 and can go up to 7, but most instructions only take 2 cycles.

Cycle 0 is exactly the same in every single instruction, since it only fetches the data from the ROM (MEM_RD) and latches it in the instruction register (nIR_LD) safely.
###  $00 --> MOV reg, imm

| Cycle | Control bits                       |
| ----- | ---------------------------------- |
| 0     | MEM_RD, nIR_LD                     |
| 1     | PC_INC, nIRDB_OE, REG_LD, nMPC_RST |
### $01 --> MOV reg, reg

Works with the accumulator implicitely.

| Cycle | Control bits                     |
| ----- | -------------------------------- |
| 0     | MEM_RD, nIR_LD                   |
| 1     | PC_INC, REG_LD, REG_OE, nMPC_RST |
### $02 --> MOV MARL/MARH, imm

When programming, the assembler will read the format, if it's MARL, the bit 8 of the instruction register which points to the selector of the MAR will be a 0. If it's MARH, the bit will be 1.

| Cycle | Control bits                        |
| ----- | ----------------------------------- |
| 0     | MEM_RD, nIR_LD                      |
| 1     | PC_INC, nIRDB_OE, nMAR_LD, nMPC_RST |
### $03 --> MOV MARL/MARH, reg

When programming, the assembler will read the format, if it's MARL, the bit 8 of the instruction register which points to the selector of the MAR will be a 0. If it's MARH, the bit will be 1.

| Cycle | Control bits                      |
| ----- | --------------------------------- |
| 0     | MEM_RD, nIR_LD                    |
| 1     | PC_INC, REG_OE, nMAR_LD, nMPC_RST |
### $04 --> LD reg, imm

Load the data from the zero-page RAM address range to a register

| Cycle | Control bits                                              |
| ----- | --------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                            |
| 1     | PC_INC, PC_OE, nIRA_OE, nHBA_OE, MEM_RD, REG_LD, nMPC_RST |
### $05 --> LD reg, MAR

Load the data of address (MAR) of RAM into a register

| Cycle | Control bits                                     |
| ----- | ------------------------------------------------ |
| 0     | MEM_RD, nIR_LD                                   |
| 1     | PC_INC, PC_OE, nMAR_OE, MEM_RD, REG_LD, nMPC_RST |
### $06 --> LD reg, XY

Load the data of address (XY registers) of RAM into a register

| Cycle | Control bits                                     |
| ----- | ------------------------------------------------ |
| 0     | MEM_RD, nIR_LD                                   |
| 1     | PC_INC, PC_OE, nXYA_OE, MEM_RD, REG_LD, nMPC_RST |
### $07 --> ST imm, reg

Store the data of a register in the zero-page address range of RAM

| Cycle | Control bits                                              |
| ----- | --------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                            |
| 1     | PC_INC, PC_OE, nIRA_OE, nHBA_OE, MEM_WR, REG_OE, nMPC_RST |
### $08 --> ST MAR, reg

Store the data of a register in address (MAR) of the RAM

| Cycle | Control bits                                     |
| ----- | ------------------------------------------------ |
| 0     | MEM_RD, nIR_LD                                   |
| 1     | PC_INC, PC_OE, nMAR_OE, MEM_WR, REG_OE, nMPC_RST |
### $09 --> ST XY, reg

Store the data of a register in address (XY) of the RAM

| Cycle | Control bits                                     |
| ----- | ------------------------------------------------ |
| 0     | MEM_RD, nIR_LD                                   |
| 1     | PC_INC, PC_OE, nXYA_OE, MEM_WR, REG_OE, nMPC_RST |
### $10 --> PUSH reg (NOT DONE)

Push the data contents of a register onto the stack. 

| Cycle | Control bits                                     |
| ----- | ------------------------------------------------ |
| 0     | MEM_RD, nIR_LD                                   |
| 1     | PC_INC, PC_OE, nXYA_OE, MEM_WR, REG_OE, nMPC_RST |
### $11 --> POP reg (NOT DONE)

Pop the data contents of a register from the stack to its destination. (document properly)

| Cycle | Control bits                                     |
| ----- | ------------------------------------------------ |
| 0     | MEM_RD, nIR_LD                                   |
| 1     | PC_INC, PC_OE, nXYA_OE, MEM_WR, REG_OE, nMPC_RST |
### $12 --> ADD A, reg

Add the data of the accumulator with the data of another register and store into the accumulator.

| Cycle | Control bits                                                    |
| ----- | --------------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                                  |
| 1     | PC_INC, ALU_S0, ALU_S1, REG_OE, REG_LD, A_SEL, nFL_LD, nMPC_RST |
### $13 --> ADD A, imm

Add the data of the accumulator with an immediate and store into the accumulator.

| Cycle | Control bits                                                     |
| ----- | ---------------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                                   |
| 1     | PC_INC, ALU_S0, ALU_S1, nIRD_OE, REG_LD, A_SEL, nFL_LD, nMPC_RST |
### $14 --> ADC A, reg (NOT DONE (works with flags))

Add the data of the accumulator with the data of another register and store into the accumulator.

| Cycle | Control bits                                                    |
| ----- | --------------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                                  |
| 1     | PC_INC, ALU_S0, ALU_S1, REG_OE, REG_LD, A_SEL, nFL_LD, nMPC_RST |
### $15 --> SUB A, reg

Substract the data of the accumulator with the data of another register and store into the accumulator.

| Cycle | Control bits                                                     |
| ----- | ---------------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                                   |
| 1     | PC_INC, ALU_S1, ALU_CIN, REG_OE, REG_LD, A_SEL, nFL_LD, nMPC_RST |
### $16 --> SBC A, reg (NOT DONE (works with flags))

Add the data of the accumulator with the data of another register and store into the accumulator.

| Cycle | Control bits                                                    |
| ----- | --------------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                                  |
| 1     | PC_INC, ALU_S0, ALU_S1, REG_OE, REG_LD, A_SEL, nFL_LD, nMPC_RST |
### $17 --> AND A, reg

Performs a logical AND with the accumulator and a register, and stores it in the accumulator.

| Cycle | Control bits                                                    |
| ----- | --------------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                                  |
| 1     | PC_INC, ALU_S1, ALU_S2, REG_OE, REG_LD, A_SEL, nFL_LD, nMPC_RST |
### $18 --> AND A, imm

Performs a logical AND with the accumulator and an immediate, and stores it in the accumulator. Instruction explicitely made for masks.

| Cycle | Control bits                                                     |
| ----- | ---------------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                                   |
| 1     | PC_INC, ALU_S1, ALU_S2, nIRD_OE, REG_LD, A_SEL, nFL_LD, nMPC_RST |
### $19 --> OR A, reg

Performs a logical OR with the accumulator and a register, and stores it in the accumulator.

| Cycle | Control bits                                                    |
| ----- | --------------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                                  |
| 1     | PC_INC, ALU_S0, ALU_S2, REG_OE, REG_LD, A_SEL, nFL_LD, nMPC_RST |
### $20 --> XOR A, reg

Performs a logical XOR with the accumulator and a register, and stores it in the accumulator.

| Cycle | Control bits                                            |
| ----- | ------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                          |
| 1     | PC_INC, ALU_S2, REG_OE, REG_LD, A_SEL, nFL_LD, nMPC_RST |
### $21 --> INC A

Increments A. In reality, its doing A + 0 (from immediate) + Carry

| Cycle | Control bits                                                              |
| ----- | ------------------------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                                            |
| 1     | PC_INC, ALU_S0, ALU_S1, ALU_CIN, nIRD_OE, REG_LD, A_SEL, nFL_LD, nMPC_RST |
### $22 --> DEC A

Decrements A. In reality, its doing A - 0 (from immediate)

| Cycle | Control bits                                             |
| ----- | -------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                           |
| 1     | PC_INC, ALU_S1, nIRD_OE, REG_LD, A_SEL, nFL_LD, nMPC_RST |
### $23 --> INC/DEC XY

Increments or Decrements the XY register pair. Bit 8 selects which instruction is made. 0 = INC, 1 = DEC. This instruction can be done because it doesn't need a source register, because now the accumulator is not the one performing arithmetic, meaning bits `[10:8]` are free to use. Since in this case, deciding between incrementing or decrementing is only a matter of changing the pin 5 (nU/D) of the 74191.

| Cycle | Control bits              |
| ----- | ------------------------- |
| 0     | MEM_RD, nIR_LD            |
| 1     | PC_INC, nXY_INC, nMPC_RST |


### $24 --> ROR A

Rotate right through carry

1
7 st zp(8), reg
8 st mar(16), reg
9 st XY, reg
10 push reg
11 pop reg
12 add A, reg
13 adi A, imm
14 adc A, reg
15 sub A, reg
16 sbc A, reg
17 and A, reg
18 ani A, imm
19 or A, reg
20 xor A, reg
21 inc A
22 dec A
23 inc/dec XY
25 ror A (must add rol A as a pseudoinstruction ADC A, A)
24 shr A(must add shl as a pseudoinstruction ADD A, A)
26 cp A, reg
27 cpi A, imm
28 jcc mar
29 jcc xy (jmp will be 111 decode condition)
30 call mar/xy

## $31 --> Zero-Operand Instructions

This operations only rely on using the opcode and do not need to use any registers or immediate data from the instruction. For this, with 1 instruction opcode, 8 sub-opcodes are fetched from the 3 lowest bits of the IRHB:
### · 1 --> BRK

| Cycle | Control bits     |
| ----- | ---------------- |
| 0     | MEM_RD, nIR_LD   |
| 1     | PC_INC, nMPC_RST |
### · 2 --> PUSHF

### · 3 --> POPF

### · 4 --> RET
### · 5 --> RTI
### · 6 --> CLI
### · 7 --> SEI

### · 8 --> HALT
