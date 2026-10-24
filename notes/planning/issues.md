# Issues

Everything that doesn't work, is missing, or should change. The to-do list says what I'm going to do, this file says what's wrong. When something gets fixed, delete it from here (git keeps the history).

## Bugs

Things that exist but don't work as intended.

| Issue | Where | Notes |
| ----- | ----- | ----- |
| `ROR` does the same as `SHR` | microcode | `SHR_IN0` is never set, and the bit shifted out doesn't go into C. |
| `POPF` loads the flags from the ALU | microcode | Step 2 doesn't set `FL_SEL`. It also needs the junction below, because `STATUS_REG`'s `D IN` isn't on the data bus either. |
| `AND`/`OR`/`XOR` load garbage into C and V | hardware | The 4 ALU flags are loaded together, so C and V get whatever the 74382 outputs on a logic operation. Only Z and N are meaningful. |
| The result of `SHR`/`ROR` never reaches the data bus | `CPU.dig` | The wire from the ALU's `ALU` output to `STATUS_REG`'s `D IN` ((940,300) to (1040,300)) crosses the data bus wire from `A_R OUT` at (960,300) without a junction, so A loads a floating bus. Found by `digital/tests/check_cpu.py`, see `verification.md`. |
| The keyboard loses keys | `CPU.dig`, MMIO | When a fetch comes right after an MMIO write (every `ST XY` to `SPI_OUT`), `MEM_RD` turns on before the address bus settles, so `KB_EN` glitches and the keyboard drops a key each time. Keys typed while the program waits for one are fine. `MEM_RD` needs to be gated with the clock, like `MEM_WR`. See `verification.md`. |

## Missing

Things that should exist but don't yet.

| What | Notes |
| ---- | ----- |
| Generic gates mapped to real chips | `CPU.dig`, `MAR.dig`, `SP.dig` and `MMIO.dig` still use 8 generic And/Or/Not gates instead of 74HC parts. |

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

Nothing right now.
