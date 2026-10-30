# Gating the Memory Strobes with the Clock

### The Problem

The EPROMs of the control unit aren't latched. On every rising clock edge, a lot of things start changing at the same time:

- The micro-PC, the IR and the flags change, so the EPROMs get a new address. Until their access time is over (100-150 ns), their outputs still show the bits of the old step, or glitch on the way to the new ones.
- The registers that drive the address bus change (the PC increments, the MAR or the SP loads), and the address decoder needs some time to settle after them.

So in the first part of every step, the control bits and the address can both be wrong, and not even wrong at the same moments.

For everything edge-triggered (registers, counters, the IR) this doesn't matter: they only look at their inputs on the next clock edge, when everything has settled. That's why most of the CPU works without caring about it. But some things react to levels, not edges:

- A real SRAM writes for as long as `/WE` and `/CE` are low. If `MEM_WR` from the step before is still on while the address changes, the write lands on the wrong address and corrupts a byte (or worse, writes to the MMIO).
- Some reads have side effects. Reading the keyboard data takes the key out of its buffer, so a glitch that looks like a read is a real read.
- Plain RAM and ROM reads don't really care, because whatever they read only gets loaded at the clock edge. But for a moment the memory could drive the data bus at the same time as the register that was driving it before, and two chips driving the same bus is a short.

### How It Showed Up

In the simulation the keyboard was losing keys (`digital/tests/check_cpu.py` found it, see `verification.md`). In a fetch that comes right after a write to the MMIO (every `ST XY` to `SPI_OUT`), `MEM_RD` turned on while the address bus was still pointing to the MMIO. For an instant, that decoded as "read the keyboard", `KB_EN` pulsed, and a key was gone. Keys typed while the program was waiting for one were fine, which is why it took a while to notice.

### Why Not Just Make Them Active-Low

The first thing that comes to mind is making `MEM_RD` and `MEM_WR` active-low in the microcode, since the real RAM and EPROM pins (`/OE`, `/WE`) are active-low anyway. But that changes nothing: the problem was never the polarity, it's when the signal is valid. Flipping the polarity only changes which level means "on", and the EPROM outputs are still unsettled at the start of every step.

### Options I Had

- Gate the strobes with the clock, so they can only be on in the second half of the step, when everything has settled. One 7400 for the whole CPU.
- Latch the EPROM outputs with a register (a pipeline register, like a few 74HC574). That removes the glitches, but the write would still last until the clock edge, the same moment the address changes, so I'd still need a strobe shorter than the step.
- Spread every memory access over more steps: set the address, then read or write, then hold the address. No hardware, but every memory access gets slower, and it costs microcode steps.

The clock is the only signal in the CPU that says when everything has settled, so I went with the first option. Real CPUs do the same thing: on the 6502 every memory access is qualified by the PHI2 clock phase, and the Z80 times its `/RD`, `/WR` and `/MREQ` with its own clock.

### The Solution Now

The `nMEM` module (`nMEM.dig`) sits between the control unit and the memory, and uses 3 of the 4 gates of a 7400 (the 4th one has its inputs tied to ground):

| Output    | Logic                     |
| --------- | ------------------------- |
| `nCLK`    | `NAND(CLK, CLK)`          |
| `nMEM_RD` | `NAND(MEM_RD, nCLK)`      |
| `nMEM_WR` | `NAND(MEM_WR, nCLK)`      |

Every register loads on the rising edge, so the second half of every step is when `CLK` is low. `nMEM_RD` and `nMEM_WR` only go low when their control bit is on and the clock is low:

```
          step N                  step N+1
CLK     ‾‾‾‾‾‾‾‾‾‾‾\___________/‾‾‾‾‾‾‾‾‾‾‾\___________/
bits    XX settle XX=== stable ===XX settle XX=== stable
nMEM_RD ‾‾‾‾‾‾‾‾‾‾‾‾\__________/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
                    ^ only here: the address and the bits are stable
```

The strobes stay active-low all the way to the chips:

- The RAM's `OE` and `WE` and the EEPROM's `OE` are inverted inputs (in Digital, the same way `CS` already was). On the breadboard, `nMEM_RD` and `nMEM_WR` go straight to the `/OE` and `/WE` pins.
- In the MMIO, the 74138 outputs and `nMMIO_CS` are active-low too, so "both active" is an OR (low only when both inputs are low). A 7432 does the three gates: `OR(nMMIO_CS, nMEM_WR)` is the clock of the two 74377 (`SPI_OUT` and `DISPLAY`), and `OR(nMEM_RD, Y0)` and `OR(nMEM_RD, Y1)` enable the keyboard data and status buffers. Before, the MMIO had a 7400 and a 7404 to make active-high copies of those signals for the NANDs, so it lost a chip, and in total the change doesn't cost any.

### What It Costs

The memory only gets half a cycle to answer: the EPROM access time plus the address decoding has to fit in half a clock period. At breadboard speeds that's easy.

There's one thing to check on the breadboard. A write now ends exactly on the rising edge, the same moment the address and the data start changing for the next step. It's a race between the delay of the 7400 (about 10 ns), which turns `nMEM_WR` off, and the delay of the registers that change the address (about 30 ns for a 74HC191), so the write should end first. The same goes for the 74377 in the MMIO, which latch their data when their clock goes back up, at the end of the write, with the 7432 adding a few more ns. SRAMs usually need 0 ns of address hold time, so it should work, but it's worth checking against the datasheets of the chips I actually use. Before the gating it was worse: the write ended an EPROM access time after the edge, when the address had already changed.

### Idea: Active-Low Control Bits

If `MEM_RD` and `MEM_WR` came out of the EPROMs already active-low, the gate would be `OR(nMEM_x, CLK)` (low only when the bit is on and the clock is low). That's 2 gates of a 7432 and no inverter for the clock, so it saves one gate. It would mean changing `crom_programmer.py`, the emulator and the tests, and swapping the pull resistors of those two lines, so it's not worth it for now, but it's there if I'm ever one gate short.
