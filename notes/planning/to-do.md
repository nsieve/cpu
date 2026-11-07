# To-Do

Everything left before the SFD-8 is done for now, so that the only things left are the VHDL port (which I do in parallel) and the breadboard build. When something gets done, delete it from here (git keeps the history).

## Decisions

These can still change the hardware, so they go first.

- the real keyboard interface (PS/2?). In Digital it's Digital's own keyboard component
- SPI: the hardware shifter (74HC165 + 74HC161 + some gates) or keep bit-banging
- the timer the programs can poll through the MMIO, and what the stop button does (or drop them)
- power-on reset (RC + 74HC14) or not, see `reset.md`
- the OLED level shifter (74LVC125 or 74LVC245 at 3.3 V)
- the final RAM and ROM chips (AS6C1008 and two AT28C256 for now)
- whether the real MAX7219 module goes on the breadboard

## Hardware

In Digital.

- map the 7 generic gates in `CPU.dig`, `MAR.dig` and `SP.dig` to real chips
- shift into carry: a 74157 in `ALU.dig` that gives C = A[0] and V = 0 while `nSHR_OE` is active, so `SHR` and `ROR` put the bit they shift out into C
- the jump latch: holds the high byte of a direct jump's target, so `JMP`, `JCC` and `CALL label` don't go through the MAR anymore (and take 4 cycles instead of 5 when they jump)
- add whatever the decisions add (keyboard, SPI shifter, timer)
- draw the clock (the three 555s) as a schematic

## Software

- binary files for a real programmer: one per EPROM for the microcode, and the program split into a high-byte and a low-byte file for the two AT28C256 (right now everything is in Digital's hex format)
- update the microcode, assembler, emulator and tests for any other new instructions or I/O
- more complex pseudoinstructions (maybe split into single-instruction and multi-instruction ones)

## Docs

- the items left in `docs-audit.md`
- a design-decisions doc for the new instructions: the ALU with memory (and the brackets), the auto-increments, `CALLcc` / `RETcc`, and why `POP XY` is only a pseudo-instruction
- the template sections the module docs are missing: pinouts, verification (pointing to `digital/tests/`) and physical TTL mapping. The table at the end of `docs-audit.md` says which doc lacks what
- finish the program counter doc
- rewrite the instruction decoding to make it easier to understand
- check the AND row of the ALU core table (it says S = 110 now, which is what the microcode does)
- a block diagram of the register file (if possible)
- new docs: the MMIO, the clock, and whatever the decisions add
- `instregister.md` and `statreg.md` with the split loads (and in `statreg.md`, the pushed byte is now `0000VCNZ`, C and N swapped compared to the microcode address), and a design-decisions doc for `LDT` and the split IR load (why the opcode can't change in the middle of an instruction)
- design-decisions docs for past changes:
	- the memory map: RAM first (for the zero page) instead of ROM first, and the address decoder redesign
	- the power-on race conditions
	- the old PC and SP versions in `digital/discarded/` (less important)
- README: the SFD-8 isn't my thesis anymore, the chip count (80 in the simulation), the block diagram (from my drawing) and the status list
- fill in the placeholders in `picking-back-up.md`

## Cleanup

- delete `docs-audit.md` once everything in it is fixed
- `issues.md` with only the limitations left
- every test passing (`programs/tests`, `digital/tests/run_module_tests.py`, `digital/tests/check_cpu.py`)
- (once most documentation is finished) change the folder system to have each module its own folder with the notes, images and its real hardware implementation, datasheets, etc.
