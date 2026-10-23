# Instruction Set Redesign

### The Problem

The instruction set is the most volatile part of the whole CPU. I had a first plan of what it was going to look like, but I couldn't figure it all out in my head beforehand, so it kept changing as the hardware progressed. What I was looking for was a balance between three things: having enough instructions to program comfortably, having enough general-purpose registers, and not needing a huge amount of hardware (or a huge amount of microcode to write by hand).

Every instruction is 16 bits, and the lower byte `[7:0]` is almost always the 8-bit immediate. That leaves the upper byte `[15:8]` for the opcode and the register, so every bit I give to the opcode is a bit the register field loses:

| Approach         | Opcode bits | Register bits | Registers I can name                |
| ---------------- | ----------- | ------------- | ----------------------------------- |
| 256 instructions | 8           | 0             | the register goes inside the opcode |
| 64 instructions  | 6           | 2             | 4                                   |
| 32 instructions  | 5           | 3             | 8                                   |

I went through these three approaches.

### First Approach: 256 Instructions

The first idea was to use the whole upper byte as the opcode, so 256 different instructions, with the register written into the opcode itself. For example, `MOV A, imm` and `MOV B, imm` would be two different opcodes.

It wasn't a bad idea, and it's simple to decode, since the microcode knows everything just from the opcode. The problem is that I'd have to program almost every instruction by hand, once per register (and per register pair for things like `MOV REG, REG`), so 200+ instructions. Now that I use AI to help with the software it would've been easier, but at the time it just looked like a pain in the ass. This one stayed on paper.

### Second Approach: 64 Instructions

The second approach was a 6-bit opcode (64 instructions) with a 2-bit register field, which goes straight from the instruction register to the register file and is decoded in hardware, like it's done now. This one actually existed, my CPUv2 and CPUv3 both worked like this (in CPUv3 the 2 bits selected B, C, X or Y, and A was implicit).

It's also not a bad approach, and it saves ICs. The register file would be a lot smaller (4 GPRs + the accumulator, instead of 7 + the accumulator), and I wouldn't need the special cases that the sub-opcodes need now, like the extra wires or the 74157 mux for `ST Imm, REG`. The problem is that when I actually thought about it, 4 GPRs felt very limited.

### The Solution Now: 32 Instructions + Sub-Opcodes

The SFD-8 uses a 5-bit base opcode, so 32 instructions:

| Bits      | What they are                                       |
| --------- | --------------------------------------------------- |
| `[15:11]` | base opcode                                         |
| `[10:8]`  | destination register, sub-opcode or jump condition  |
| `[7:5]`   | source register                                     |
| `[7:0]`   | 8-bit immediate (or zero-page address)              |

With 3 bits for the register I get 8 registers (7 GPRs + the accumulator), and 32 instructions are enough to do most of the things I want.

The sub-opcodes weren't planned from the start. When the 32 slots started to run out, they were the only option I had if I wanted to keep the 5-bit opcode and still have a good amount of instructions, so programming stays easy. The trick is that the microcode EPROMs don't only see the base opcode, they see the whole upper byte `[15:8]`. So the same 3 bits `[10:8]` can mean two different things depending on the instruction:

- In instructions like `MOV REG, Imm` or `LD REG, MAR`, they are the destination register. The register file decodes them in hardware, and the microcode is the same for all 8 values.
- In instructions that don't need a register, they're a sub-opcode, and the microcode does something different for each value. For example, `0x02` is `MOV MARL, Imm`, `MOV MARH, Imm`, `INC MAR`, `DEC MAR`, `INC XY` or `DEC XY` depending on the sub-opcode, and `0x1B` uses them as the condition of the jump (C, NC, Z, NZ, ...).

The sub-opcodes don't need any extra decoding hardware, since the EPROM address already includes those bits. Thanks to this, the 32 base opcodes hold 66 instructions, and there are still free slots left. The full list is in `opcodes&microinstructions/isa.md`.

### The Downside

The decoding isn't uniform. Every instruction is a bit special depending on which bits it uses and for what: some read the register from `[10:8]`, some from `[7:5]`, some use `[10:8]` as a sub-opcode, and `ST Imm, REG` needs a mux to read its register from a different field than usual (more about this in `design-decisions/st-zeropage.md`). This makes the instructions harder to explain than in the other two approaches.

It's not the most "aesthetically pleasing" system, but I think it's a good way to show how I fit as many instructions as I could without a huge amount of hardware, while keeping them fast (most of them take only 2 cycles).
