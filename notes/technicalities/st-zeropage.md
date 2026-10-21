# ST Zero-Page Only with the Accumulator

### The Problem

`ST Imm, REG` was supposed to store any register into the zero page (`0x0000-0x00FF`), but it can't work that way.

The register file always decodes the source register from bits `[7:5]` of the instruction (the destination comes from `[10:8]`). The problem is that in a zero-page store, the whole lower byte `[7:0]` is the address, so bits `[7:5]` are part of the address, not a register. The assembler was putting the register in `[10:8]`, but that field is only used for loading, not for outputting. So, for example, `ST 0x45, B` would actually output register `010` (from the address `0x45` = `0100 0101`), which is C, and not B.

This doesn't happen with the loads (`LD Imm, REG`) because those use the destination field `[10:8]`, which is free.

The microcode can't fix this, because the bits that go into the decoder come straight from the instruction register, there is no way to change which bits it reads.

### Options I Had

- Multiplex the decoder input between `[7:5]` and `[10:8]` with a 74157 and a new control bit. It works with every register, but I didn't like adding a mux on the path of the register file.
- Remove `ST Imm` and always store through the MAR (`MOV MARH`, `MOV MARL`, `ST MAR, REG`). No hardware, but it's 3 instructions instead of 1.
- Make the zero page 32 bytes and use `[4:0]` as the address. It doesn't really work, because the IR puts the whole lower byte on the address bus, so the register bits would end up inside the address.
- Make it accumulator-only (`ST Imm, A`), which is the one I chose.

### The Solution

There is a new control bit, `nACC_OE` (bit 45, on the third EPROM), which enables the output of the accumulator directly, without going through the source decoder.

The accumulator's output enable now comes from two places: the decoder output (`A_OE`, which comes from the register file) or `nACC_OE`. Since both are active-low, a single AND gate (7408) between them does the job: if either of them goes low, the accumulator outputs to the data bus.

In `ST Imm, A`, the microcode activates `nACC_OE` instead of `REG_OE`. Since `REG_OE` is not active, the decoder stays disabled and no other register drives the bus, so there is no conflict.

| Cycle | Control bits                                                 |
| ----- | ------------------------------------------------------------ |
| 0     | MEM_RD, nIR_LD                                               |
| 1     | PC_INC, PC_OE, nIRA_OE, nHBA_OE, MEM_WR, nACC_OE, nMPC_RST   |

The cost is that, to store another register in the zero page, I first need `MOV A, REG`, which is 1 extra instruction. This is pretty common in accumulator-based CPUs anyway (for example, the 6502 also has `STA` for the zero page).

The assembler only accepts `ST Imm, A` and gives an error for any other register.
