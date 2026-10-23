# Issues

Everything that doesn't work, is missing, or should change. The to-do list says what I'm going to do, this file says what's wrong. When something gets fixed, delete it from here (git keeps the history).

## Bugs

Things that exist but don't work as intended.

| Issue | Where | Notes |
| ----- | ----- | ----- |
| `ROR` does the same as `SHR` | microcode | `SHR_IN0` is never set, and the bit shifted out doesn't go into C. |
| `HALT` behaves like a `NOP` | microcode + hardware | It only resets the micro-PC, and step 1 still does `PC_INC`. It needs hardware that actually stops the clock. |
| `POPF` loads the flags from the ALU | microcode | Step 2 doesn't set `FL_SEL`. |
| `AND`/`OR`/`XOR` load garbage into C and V | hardware | The 4 ALU flags are loaded together, so C and V get whatever the 74382 outputs on a logic operation. Only Z and N are meaningful. |
| MMIO and framebuffer decoding don't work as intended | `ADDR_DEC.dig` | From the old to-do list, check if it's still true. |
| Reset needs a manual sequence | `RST Buffer.dig` | The reset address (`0xC000`) is hardwired into two 74245 that I have to open by hand after a reset. It should happen by itself. |

## Missing

Things that should exist but don't yet.

| What | Notes |
| ---- | ----- |
| Test cases | There are no Digital test cases, and the only test program (`main.asm`) checks jumps, `ST zp` and the free slots. Most instructions have never been tested on purpose. |
| HALT hardware | See the bug above. |
| Generic gates mapped to real chips | `CPU.dig`, `MAR.dig`, `SP.dig` and `MMIO.dig` still use 8 generic And/Or/Not gates instead of 74HC parts. |
| Docs for some modules | `controlunit.md` and `addrhighbuffer.md` are empty, and `instregister.md` only has a title. |

## Limitations (by Design)

Not bugs, these are on purpose (or the price of something else), but they're easy to forget when programming.

| Limitation | Why |
| ---------- | --- |
| The MAR is lost after `JMP label`, `JCC label`, `CALL label` and `RET` | They use it to hold the target address. See `design-decisions/jumps.md`. |
| Only `ADD` and `AND` (and `CP`) have an immediate version | No opcodes left for the others. |
| No `JCC MAR` | Only `JCC XY` and `JCC label`. |
| Shifts don't update the flags | `SHR`/`ROR` use their own buffer, not the ALU. (`SHL` and `ROL` are really `ADD A, A` and `ADC A, A`, so they do.) |
| `INC A` / `DEC A` need the immediate to be `0x00` | They add the IR's low byte. The assembler always leaves it at 0. |
| `MOV X, SPH` / `MOV Y, SPL` | The subOp (6 and 7) doubles as the destination register, that's why they only work with X and Y. |

## Cleanup

Leftovers that should be removed or updated.

- `notes/Attachments/Pasted image 20260911215024.png` needs a real name.
