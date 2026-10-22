# SFD-8

(new name pending)

An 8-bit CPU designed from scratch and built entirely from 74HC logic chips.

(the block diagram goes here once it's drawn, and later a photo of the breadboards. For now, the Digital screenshot:)

<img src="notes/Attachments/cpu.png" alt="SFD-8 in Digital" width="900" />

## Highlights

- 8-bit data bus, 16-bit address bus (64 KB of memory)
- Von Neumann, accumulator-based architecture
- 32 opcodes that expand to 66 instructions using sub-opcodes
- Microprogrammed control unit: 40 control bits on three 16-bit EPROMs, up to 16 microsteps per instruction
- Most instructions take 2 cycles, because the fetch of the next instruction overlaps with the execution of the current one
- 48 KB of RAM, 15 KB of ROM, a 1 KB framebuffer and 256 bytes of memory-mapped I/O
- I/O: keyboard, timer and an SPI port for an OLED display
- 77 logic chips so far (plus RAM, ROM and the three EPROMs)
- Designed and simulated in [Digital](https://github.com/hneemann/Digital), and being built on breadboards

## About the Project

This isn't a textbook design, and it isn't necessarily how a professional would do it. It's how I managed to think about a CPU coming from an electronics background, under real constraints: chip count, breadboard size, available parts, keeping it easy to program, and making it reliable enough to actually build. Many decisions here come from mistakes I made along the way, and the docs explain the why behind them.

The SFD-8 is also my Bachelor's Thesis. This repository holds everything: the simulation, the documentation of every module, and the software to program it.

## Architecture

Every instruction is a 16-bit word stored in the ROM. In the first cycle, the Program Counter puts its address on the address bus and the word is loaded into the Instruction Register. The upper byte of the instruction (the opcode), the step of the Micro-Program Counter and the four flags together form the address of the three EPROMs of the Control Unit, and the bits they output are the control signals for that step. In the second cycle the PC is incremented while the instruction executes, and most instructions finish right there.

Data moves over an 8-bit data bus, shared by the register file, the ALU, memory, the flags and the 8-bit halves of the PC, the MAR and the Stack Pointer. Addresses go over a 16-bit address bus, which can be driven by the PC, the MAR, the XY register pair, the Stack Pointer, or the lower byte of the instruction (with the upper byte forced to `0x00` for the zero page). The Address Decoder looks at the address and enables the RAM, the ROM, the framebuffer or the MMIO.

The ALU always works with the accumulator: one operand is A, the other one is a register or an immediate, and the result goes back into A.

The main modules are:

- Clock: three 555 timers for manual and automatic clock (only on the breadboard)
- Program Counter: 16-bit, addresses the whole 64 KB
- Instruction Register: 16-bit, loaded straight from the program ROM
- Micro-Program Counter: 4-bit counter that steps through each microinstruction
- Control Unit: three EPROMs holding the microcode
- ALU: 8-bit, does ADD, ADC, SUB, SBC, AND, OR, XOR and shifts, with registers and immediates
- Register File: the accumulator plus 7 registers, 2 of which (X and Y) work together as a 16-bit pointer
- Status Register: holds the Z, C, N and V flags
- Stack Pointer: 16-bit, grows down from the end of RAM
- Memory Address Register: 16-bit up/down counter used to address memory
- Address Decoder and MMIO: select RAM, ROM, framebuffer or I/O depending on the address

## Documentation

| Module                                                         | Description                                               | Status  |
| -------------------------------------------------------------- | --------------------------------------------------------- | :-----: |
| [Program Counter](notes/hardware-design/program_counter.md)    | 16-bit PC and its reset circuit                           |  Done   |
| [Stack Pointer](notes/hardware-design/stack_pointer.md)        | 16-bit SP, push and pop                                   |  Done   |
| [Memory Address Register](notes/hardware-design/mar.md)        | 16-bit up/down counter                                    |  Done   |
| [Status Register](notes/hardware-design/statreg.md)            | Z, C, N and V flags                                       |  Done   |
| [ALU](notes/hardware-design/alu.md)                            | 8-bit ALU with two 74382                                  | Partial |
| [Register File](notes/hardware-design/regfile.md)              | Accumulator, 7 registers and the XY pair                  | Partial |
| [Address Decoder](notes/hardware-design/address_decoder.md)    | Chip selects for each memory region                       | Partial |
| [Reset Buffer](notes/hardware-design/rstbuffer.md)             | Reset vector logic                                        | Partial |
| [Instruction Register](notes/hardware-design/instregister.md)  | 16-bit IR                                                 |  To do  |
| [Control Unit](notes/hardware-design/controlunit.md)           | Microcode EPROMs                                          |  To do  |
| [Address High Buffer](notes/hardware-design/addrhighbuffer.md) | Forces the high byte of the address to `0x00` (zero page) |  To do  |
| Micro-Program Counter                                          | 4-bit microstep counter                                   |  To do  |
| MMIO                                                           | Memory-mapped I/O registers                               |  To do  |

Instruction set:

- [Instruction Set Architecture](notes/opcodes%26microinstructions/isa.md): every instruction, its opcode, cycles and flags
- [Instruction Decoding](notes/opcodes%26microinstructions/instructiondecoding.md): how the 16-bit instruction word is split
- [Control Bits](notes/opcodes%26microinstructions/controlbits.md): what each of the 40 control bits does (not written yet)
- [Memory Map](notes/hardware-design/memory_map.md)

Design decisions:

- [ST Zero-Page Source Register](notes/design-decisions/st-zeropage.md)
- [Fetch-Execute Overlap](notes/design-decisions/fetch-execute-overlap.md)
- [Direct Jumps](notes/design-decisions/jumps.md)
- [74191 Load Synchronization](notes/design-decisions/74191-loadsync.md)
- [Interrupts (and Why I Removed Them)](notes/design-decisions/interrupts.md)

## Repository Structure

```
digital/                  Digital simulation, one .dig file per module (CPU.dig is the top level)
  discarded/              old versions of modules I replaced
notes/
  hardware-design/        one doc per module
  opcodes&microinstructions/
                          instruction set, decoding and control bits
  design-decisions/       problems I ran into and why I solved them the way I did
  planning/               to-do list, known issues, ideas and sources
  Attachments/            images used in the docs
programs/
  assembler.py            assembler for SFD-8 programs
  crom_programmer.py      generates the microcode for the control unit EPROMs
  main.asm                current test program
```

## Running It

You need [Digital](https://github.com/hneemann/Digital) and Python 3.

1. Generate the microcode: running `python crom_programmer.py` inside `programs/` creates `eprom1.hex`, `eprom2.hex` and `eprom3.hex`.
2. Assemble a program: `python assembler.py main.asm` creates `main.hex`.
3. Load the files into the ROMs. Digital keeps the contents inside the `.dig` files, so this is only needed after changing the microcode or the program: in `CTRLUNIT.dig`, load `eprom1.hex`, `eprom2.hex` and `eprom3.hex` into `1ROM`, `2ROM` and `3ROM`, and in `CPU.dig`, load `main.hex` into the program EEPROM (right-click the component, edit its data and load the file).
4. Open `digital/CPU.dig` and start the simulation. `CLK_SEL` switches between the automatic clock and the manual one.

## Status

The whole datapath works in the simulation, and every instruction has its microcode. What's left is mostly fixing and testing, not building.

- [x] All datapath modules built in Digital
- [x] Microcode for every instruction
- [x] Assembler
- [ ] Fix the known bugs (see [issues](notes/planning/issues.md))
- [ ] Test every instruction
- [ ] Document every module
- [ ] Map the remaining generic gates to real chips
- [ ] Build it on breadboards (started)
- [ ] Make the whole design in VHDL

## Use of AI

The CPU's architecture, circuits, instruction set and microcode are my own design. I used AI (Claude) as a tool for the parts outside the project's focus: writing and maintaining the assembler and other software tooling, helping track down bugs, and turning my explanations of each module into cleaner, better-structured documentation. Commits where AI was involved are marked as co-authored.

## Acknowledgments

I want to start by thanking [mattbatwings](https://github.com/mattbatwings), who gave me the inspiration to attempt building my first computer in Minecraft. After that, [Ben Eater](https://github.com/beneater) was the one that showed me how these computers can be brought to life in breadboards.

I also want to mention [Fadil](https://github.com/Fadil-1), from whom I got the idea to use an SPI OLED, and whose CPU showed me that it is possible to build an actual potent computer in breadboards.

## License

[MIT](LICENSE.md)
