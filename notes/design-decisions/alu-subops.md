# ALU Operations as Sub-Opcodes (Direct A Load)

### The Problem

Only `ADD`, `AND` and `CP` had an immediate version. Subtracting a constant took two instructions (`MOV B, Imm` + `SUB A, B`), and there was no `OR` or `XOR` with an immediate, which is exactly what I need to set and clear single bits, in the MMIO registers and in the framebuffer.

The obvious place for the missing ones was the free sub-opcodes, but that can't work with microcode alone. Every instruction that writes a register uses `REG_LD`, which enables the register file's load decoder (a 74138), and that decoder always reads the register number from `[10:8]`. A is register 0, so its load line (`A_LD`) is output 0 of the decoder. An ALU operation writes A, so `[10:8]` had to be 0. If I put, for example, `OR A, Imm` in sub-op 5, `REG_LD` would load register 5 (F) instead of A.

That's why every ALU operation needed its own whole opcode: the only bits left to say which operation it was were the ones of the base opcode `[15:11]`. The ALU used 11 of the 32 opcodes, and there was no room for the other 5 immediates.

### Options I Had

- Leave it as it was.
- Free whole opcodes by moving the instructions that don't write A (like `CP` and `MOV MARL/MARH, REG`) into free sub-op slots, so their opcodes could hold new ALU immediates. No hardware, but it only gets about 3 of the 5, and the opcode table ends up scrambled.
- Give A a second way to load that doesn't go through the decoder. Then `[10:8]` isn't needed as the destination in the ALU operations, and it can be the operation itself.

### The Solution Now: A Direct Load for A

A new control bit, `nA_LD` (bit 23, D7 of the second EPROM), loads A directly. A's load enable now comes from two places, the decoder output (`A_LD`) and `nA_LD`, joined with an AND gate. Both are active-low, so if either of them goes low, A loads:

| Decoder `A_LD` | `nA_LD` | A's load enable | A loads? |
| :------------: | :-----: | :-------------: | :------: |
| 1              | 1       | 1               | no       |
| 0              | 1       | 0               | yes (MOV, LD and POP into A, INC A, DEC A, SHR, ROR) |
| 1              | 0       | 0               | yes (the ALU operations) |

It's the same trick as the `nACC_OE` I had in the first version of `ST zp` (see `st-zeropage.md`), but for loading A instead of outputting it.

The ALU operations set `nA_LD` instead of `REG_LD`. `REG_LD` stays at 0, so the decoder is off and no other register loads, whatever is in `[10:8]`. And since the EPROMs are addressed with the whole 8-bit opcode `[15:8]`, they already see the base opcode and the sub-op together, so the microcode can output different ALU select lines for each sub-op.

The ALU now uses 2 opcodes, one for each kind of operand, and the sub-op is the operation:

| Sub-op | Operation | `0x0C`: ALU A, REG | `0x0D`: ALU A, Imm | Flags   |
| ------ | --------- | ------------------ | ------------------ | ------- |
| 0      | ADD       | `ADD A, REG`       | `ADD A, Imm`       | Z,C,N,V |
| 1      | ADC       | `ADC A, REG`       | `ADC A, Imm`       | Z,C,N,V |
| 2      | SUB       | `SUB A, REG`       | `SUB A, Imm`       | Z,C,N,V |
| 3      | SBC       | `SBC A, REG`       | `SBC A, Imm`       | Z,C,N,V |
| 4      | AND       | `AND A, REG`       | `AND A, Imm`       | Z,N     |
| 5      | OR        | `OR A, REG`        | `OR A, Imm`        | Z,N     |
| 6      | XOR       | `XOR A, REG`       | `XOR A, Imm`       | Z,N     |
| 7      | CP        | `CP A, REG`        | `CP A, Imm`        | Z,C,N,V |

In `0x0C` the register still comes from `[7:5]`, and in `0x0D` the immediate is `[7:0]`. `CP` is the same as `SUB` without `nA_LD`, so only the flags change, and the logic operations only load Z and N (`nFLZN_LD`), so C and V keep their value.

For example, `SUB A, 5` is `0x6A05`:

| Bits    | Value   | Meaning                        |
| ------- | ------- | ------------------------------ |
| `[15:11]` | `01101` | base opcode `0x0D` (ALU A, Imm) |
| `[10:8]`  | `010`   | sub-op 2 (SUB)                 |
| `[7:0]`   | `0x05`  | the immediate                  |

| Cycle | Control bits                                                                         |
| ----- | ------------------------------------------------------------------------------------ |
| 0     | MEM_RD, nIRH_LD, nIRL_LD                                                             |
| 1     | PC_INC, nIRD_OE, ALU_S1, ALU_CIN, A_SEL, nA_LD, nFLZN_LD, nFLCV_LD, nMPC_RST         |

With `OR A, 5` (sub-op 5), cycle 1 has `ALU_S0` and `ALU_S2` instead, and only `nFLZN_LD`.

### The Rule for `[10:8]`

The instruction format didn't change: `[15:11]` is the base opcode, `[10:8]` the destination register or the sub-op, `[7:5]` the source register and `[7:0]` the immediate. What changed is when `[10:8]` can be a sub-op.

The rule is that `[10:8]` can be a sub-op in any instruction that doesn't use `REG_LD`, because `REG_LD` always reads it as the destination. The conditional jumps (the condition), the jumps and calls, and the SP and MAR instructions could already use it that way because none of them write a register. The ALU operations were the exception because they write A, and `nA_LD` removes that exception. The instructions that write any register (`MOV`, `LD`, `POP`) still use `REG_LD` with the destination in `[10:8]`, exactly as before.

### What Changed in the Opcodes

| Instruction  | Before        | Now               |
| ------------ | ------------- | ----------------- |
| `ADD A, REG` | `0x0C`        | `0x0C` sub-op 0   |
| `ADD A, Imm` | `0x0D`        | `0x0D` sub-op 0   |
| `ADC A, REG` | `0x0E`        | `0x0C` sub-op 1   |
| `SUB A, REG` | `0x0F`        | `0x0C` sub-op 2   |
| `SBC A, REG` | `0x10`        | `0x0C` sub-op 3   |
| `AND A, REG` | `0x11`        | `0x0C` sub-op 4   |
| `AND A, Imm` | `0x12`        | `0x0D` sub-op 4   |
| `OR A, REG`  | `0x13`        | `0x0C` sub-op 5   |
| `XOR A, REG` | `0x14`        | `0x0C` sub-op 6   |
| `CP A, REG`  | `0x19`        | `0x0C` sub-op 7   |
| `CP A, Imm`  | `0x1A`        | `0x0D` sub-op 7   |
| `ADC`, `SUB`, `SBC`, `OR`, `XOR A, Imm` | didn't exist | `0x0D` sub-ops 1, 2, 3, 5, 6 |

`ADD` kept its opcodes. The 9 opcodes `0x0E-0x14`, `0x19` and `0x1A` are completely free now, and the CPU has 72 instructions in the other 23. The assembly syntax is the same, so the programs only had to be assembled again.

`INC A`, `DEC A`, `SHR A` and `ROR A` stayed in their own opcodes, with `REG_LD` and `[10:8]` = 0. `INC A` and `DEC A` give exactly the same result and flags as `ADD A, 1` and `SUB A, 1`, so they could become pseudo-instructions some day and free 2 more opcodes.

### What It Costs

One control bit and one AND gate in front of A's load enable. The gate adds around 10-20 ns on that path, but the EPROMs before it already take more than 100 ns, and the 74173 only looks at its load enable on the clock edge, so it doesn't matter.

The ALU result doesn't go to the data bus at all. The 74245 that could put it there (with `nALU_OE`) was never used by the microcode, and it couldn't be: the ALU's B input reads the data bus, so putting the result on it makes a loop. Removing it saved a chip and a control bit, so the CPU still has 43 control bits in total.
