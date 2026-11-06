# To-Do

Everything left before the SFD-8 is done for now, so that the only things left are the VHDL port (which I do in parallel) and the breadboard build. When something gets done, delete it from here (git keeps the history).

## Decisions

These can still change the hardware, so they go first.

- reading constants from the ROM (fonts, images, the QR code): right now the ROM only goes to the IR. The `LDT A, XY` idea in `ideas.md` does it with no new hardware. Decide before the instruction set is frozen
- the other ISA ideas in `ideas.md`: ALU operations with an immediate, and `ST XY+, REG`
- the real keyboard interface (PS/2?). In Digital it's Digital's own keyboard component
- SPI: the hardware shifter (74HC165 + 74HC161 + some gates) or keep bit-banging
- the timer the programs can poll through the MMIO, and what the stop button does (or drop them)
- power-on reset (RC + 74HC14) or not, see `reset.md`
- the OLED level shifter (74LVC125 or 74LVC245 at 3.3 V)
- the final RAM and ROM chips (AS6C1008 and two AT28C256 for now)
- whether the real MAX7219 module goes on the breadboard

## Hardware

In Digital.

- fix `ROR` (it does the same as `SHR`) and the C and V flags that `AND`/`OR`/`XOR` load (see `issues.md`)
- map the 7 generic gates in `CPU.dig`, `MAR.dig` and `SP.dig` to real chips
- add whatever the decisions add (keyboard, SPI shifter, timer)
- draw the clock (the three 555s) as a schematic

## Software

- binary files for a real programmer: one per EPROM for the microcode, and the program split into a high-byte and a low-byte file for the two AT28C256 (right now everything is in Digital's hex format)
- update the microcode, assembler, emulator and tests for any new instructions or I/O
- more complex pseudoinstructions (maybe split into single-instruction and multi-instruction ones)

## Docs

- the items left in `docs-audit.md`
- the template sections the module docs are missing: pinouts, verification (pointing to `digital/tests/`) and physical TTL mapping. The table at the end of `docs-audit.md` says which doc lacks what
- finish the program counter doc
- rewrite the instruction decoding to make it easier to understand
- check the AND row of the ALU core table (it says S = 110 now, which is what the microcode does)
- a block diagram of the register file (if possible)
- new docs: the MMIO, the clock, and whatever the decisions add
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
