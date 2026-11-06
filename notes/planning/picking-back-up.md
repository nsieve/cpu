# Picking It Back Up

The SFD-8 is parked right before the breadboard build. The design is finished in Digital, but the breadboards are barely started. This page is what I read first when I come back: where everything stands, how to get the tools running again, and what's still missing before I can build and test it for real.

## Where Things Stand

- Design: complete in Digital (`digital/CPU.dig` is the top level). Every instruction has its microcode, and the programs (primes, Fibonacci, the keyboard test and the self-checking `main.asm`) run both in Digital and on the emulator.
- VHDL version: (fill in when it's done: which board, what runs on it, where the code is)
- Breadboards: about 5% wired. Every chip on them right now is a 74LS, which I bought by mistake: the design is for 74HC. They have the same size and pinout, so I'm using them as placeholders to wire around, and they all get swapped for the HC ones before testing anything. Nothing on the breadboards has been tested yet.
- What's wired so far: (fill in: which modules, which breadboards)
- Known bugs and limitations: in [issues.md](issues.md).

## Getting the Tools Running Again

- [Digital](https://github.com/hneemann/Digital) v0.31 is the version the `.dig` files were made with. A newer one should open them, but if something looks broken, go back to that one.
- Python 3, for the assembler, the microcode generator, the emulator and the tests.
- Java, for the circuit tests in `digital/tests/`. They look for `Digital.jar` in `~/Applications/Digital/`, or wherever `DIGITAL_JAR` points.

If these three pass, the repo is in the state I left it:

```
python3 -m unittest discover -s programs/tests      every instruction, the microcode files and the programs
python3 digital/tests/run_module_tests.py           every module in Digital against its test file
python3 digital/tests/check_cpu.py                  CPU.dig against the emulator, cycle by cycle
```

More about them in [verification.md](../verification.md).

## Reading Order

To get the whole design back in my head before touching a wire:

1. The [README](../../README.md), for the big picture.
2. [isa.md](../opcodes%26microinstructions/isa.md) and [instructiondecoding.md](../opcodes%26microinstructions/instructiondecoding.md), for what the 16-bit instruction word looks like.
3. [controlunit.md](../hardware-design/controlunit.md) and [fetch-execute-overlap.md](../design-decisions/fetch-execute-overlap.md), for how an instruction actually runs. `python3 programs/emulator.py --microcode "ADD A, B"` shows what every microstep of an instruction does, which helps a lot here.
4. [memory_map.md](../hardware-design/memory_map.md) and [address_decoder.md](../hardware-design/address_decoder.md).
5. The doc of each module in `hardware-design/` right before building it.
6. [memory-strobes.md](../design-decisions/memory-strobes.md) before wiring the memory and the MMIO, because that's where the timing matters.

## Parts

### Logic Chips

What the simulation uses, module by module. Digital uses whole gate chips in every module, even when only one gate is used, so on the breadboard the gate chips (7400, 7402, 7404, 7408, 7421, 7430, 7432) get shared between modules and the real number is lower.

| Chip  | What it is                             | Count | Where                                                    |
| ----- | -------------------------------------- | :---: | -------------------------------------------------------- |
| 74245 | Octal bus transceiver                  |  25   | PC 4, SP 4, RFILE 4, ALU 3, addr_buffer 3, IR 2, MAR 2, MMIO 2, STATUS_REG 1 |
| 74173 | 4-bit register, tri-state              |  13   | RFILE 10, ALU 2, STATUS_REG 1                            |
| 74191 | 4-bit up/down counter                  |  12   | RFILE 4, MAR 4, SP 4                                     |
| 74161 | 4-bit counter                          |   4   | PC                                                       |
| 74163 | 4-bit counter, synchronous clear       |   1   | CTRLUNIT (micro-PC)                                      |
| 74377 | 8-bit register with enable             |   4   | IR 2, MMIO 2                                             |
| 74382 | 4-bit ALU                              |   2   | ALU                                                      |
| 74257 | Quad 2-to-1 mux, tri-state             |   2   | ALU                                                      |
| 74157 | Quad 2-to-1 mux                        |   2   | RFILE, STATUS_REG                                        |
| 74138 | 3-to-8 decoder                         |   3   | RFILE 2, MMIO 1                                          |
| 7400  | Quad NAND                              |   2   | ADDR_DEC, nMEM                                           |
| 7402  | Quad NOR                               |   1   | ALU                                                      |
| 7404  | Hex inverter                           |   1   | RFILE                                                    |
| 7408  | Quad AND                               |   2   | CTRLUNIT, PC                                             |
| 7421  | Dual 4-input AND                       |   1   | ALU                                                      |
| 7430  | 8-input NAND                           |   1   | ADDR_DEC                                                 |
| 7432  | Quad OR                                |   3   | MMIO, PC, RFILE                                          |
| 7474  | Dual D flip-flop                       |   1   | RST_HARDWARE                                             |

That's 80 in the simulation, plus the 7 generic gates that aren't mapped to chips yet (see below).

### Everything Else

| Part                    | Count | For                                  | Status                       |
| ----------------------- | :---: | ------------------------------------ | ---------------------------- |
| 27C1024 (64K x 16 EPROM) |  3   | Microcode                            | Chosen                       |
| AS6C1008 (128K x 8 SRAM) |  1   | RAM (only 48 KB of it is used)       | From my notes, not final     |
| AT28C256 (32K x 8 EEPROM) |  2  | Program ROM, one per byte of the 16-bit word | From my notes, not final |
| 555                     |   3   | Clock (manual and automatic)         |                              |
| SSD1306 128x64 SPI OLED |   1   | Screen                               | Not bought                   |
| 74LVC125 or 74LVC245 at 3.3 V | 1 | Level shifter for the OLED lines (the OLED is 3.3 V) | Not decided |
| MAX7219 8-digit module  |   1   | 7-segment display on the SPI port    | Maybe                        |

To program the memory chips I also need a programmer that supports the 27C1024 and the AT28C256, and a UV eraser if the EPROMs are the windowed (erasable) kind.

## What's Missing Before Building

### Hardware

- The generic gates: `CPU.dig` (3 AND and 1 OR, for the clock select and the reset button), `MAR.dig` (2 OR) and `SP.dig` (1 OR) still use Digital's generic gates instead of real chips.
- The clock: three 555s, but it's only on the breadboard. It's not in Digital and it has no doc.
- The keyboard: in Digital it's Digital's own keyboard component, which stands in for the real thing. The real keyboard interface isn't designed yet.
- The SPI shifter: I chose a hardware shifter (74HC165 + 74HC161 + some gates, one bit per CPU clock) over bit-banging, but it isn't in Digital yet. For now `SPI_OUT` is bit-banged by the programs.
- The OLED level shifter (see the parts table).
- The timer the programs can poll through the MMIO, and what the stop button does.
- Power-on reset: only an idea for now, in [reset.md](../hardware-design/reset.md).

### Software

- Files for the real chips: `crom_programmer.py` and the assembler only write Digital's hex format. A programmer wants binary files: one per EPROM for the microcode, and the program split into a high-byte file and a low-byte file for the two AT28C256.

### Docs

- The MMIO doesn't have its own doc yet (the registers are in [memory_map.md](../hardware-design/memory_map.md)).
- The clock (see above).

## Building It

Every module has a test file in `digital/tests/` (`MODULE_tests.txt`) with its inputs and the outputs it should give, which is what Digital checks it against. When a module is wired, a few of those cases, done by hand with the manual clock, tell me if it works before I connect it to the bus.

The ideas I didn't get to (ISA improvements, demos, the UART) are in [ideas.md](ideas.md).
