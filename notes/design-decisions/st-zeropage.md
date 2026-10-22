# ST Zero-Page Source Register

### The Problem

`ST Imm, REG` was supposed to store any register into the zero page (`0x0000-0x00FF`), but at first it couldn't work that way.

The register file always decodes the source register from bits `[7:5]` of the instruction (the destination comes from `[10:8]`). The problem is that in a zero-page store, the whole lower byte `[7:0]` is the address, so bits `[7:5]` are part of the address, not a register. The assembler was putting the register in `[10:8]`, but that field was only used for loading, not for outputting. So, for example, `ST 0x45, B` would actually output register `010` (from the address `0x45` = `0100 0101`), which is C, and not B.

This doesn't happen with the loads (`LD Imm, REG`) because those use the destination field `[10:8]`, which is free.

The microcode alone can't fix this, because the bits that go into the decoder come straight from the instruction register, so there is no way to change which bits it reads without new hardware.

### Options I Had

- Multiplex the decoder input between `[7:5]` and `[10:8]` with a 74157 and a new control bit. It works with every register, but I didn't like adding a mux on the path of the register file.
- Remove `ST Imm` and always store through the MAR (`MOV MARH`, `MOV MARL`, `ST MAR, REG`). No hardware, but it's 3 instructions instead of 1.
- Make the zero page 32 bytes and use `[4:0]` as the address. It doesn't really work, because the IR puts the whole lower byte on the address bus, so the register bits would end up inside the address.
- Make it accumulator-only (`ST Imm, A`).

### First Solution: Accumulator Only

At first I chose the last option. There was a control bit, `nACC_OE`, which enabled the output of the accumulator directly, without going through the source decoder. The accumulator's output enable came from two places, the decoder output (`A_OE`) or `nACC_OE`, joined with an AND gate (both are active-low, so if either of them went low, the accumulator drove the data bus). The assembler only accepted `ST Imm, A`.

It worked, but storing any other register meant doing `MOV A, REG` first, which overwrites A. Since A is the register I use the most, in practice this often meant saving it first (`PUSH A`, `MOV A, REG`, `ST`, `POP A`), so 4 instructions instead of 1.

### Why I Changed It

The hardware cost is small (1 extra chip, and the control bit was already there from the first solution), and in exchange I don't have to remember, every time I program, that ST in the zero page only works with the accumulator. I could've made a pseudo-instruction that does it in two instructions, but it wasn't worth it: it costs extra cycles, and it makes the accumulator even more volatile, since one more instruction would be overwriting its contents. And last but not least, it makes LD and ST symmetric, something I value a lot and try to keep as much as I can in the entire CPU.

### The Solution Now: A Mux on the Source Decoder

In the end I went with the first option. A 74157 sits in front of the source decoder of the register file, and selects where the source register number comes from:

| `SRC_SEL` | Source register bits |
| --------- | -------------------- |
| 0         | `[7:5]` (normal)     |
| 1         | `[10:8]` (ST zp)     |

`SRC_SEL` took the place of `nACC_OE` (it's bit 39 now, on the third EPROM), and the AND gate is gone, so the change doesn't cost any extra control bits. It's active-high, so every other instruction leaves it at 0 and behaves exactly as before.

In `ST Imm, REG`, the microcode activates `REG_OE` together with `SRC_SEL`, so the decoder enables the register written in `[10:8]`:

| Cycle | Control bits                                                        |
| ----- | ------------------------------------------------------------------- |
| 0     | MEM_RD, nIR_LD                                                      |
| 1     | PC_INC, PC_OE, nIRA_OE, nHBA_OE, MEM_WR, REG_OE, SRC_SEL, nMPC_RST  |

Now `LD Imm, REG` and `ST Imm, REG` have the same encoding: the register in `[10:8]` and the address in `[7:0]`.

The mux adds some delay on the path of the register file (around 15-25 ns for a 74HC157), but the EPROMs before it already take more than 100 ns, and on the breadboard the clock period will be much longer than that, so it doesn't matter.
