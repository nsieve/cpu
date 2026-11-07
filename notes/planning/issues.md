# Issues

Everything that doesn't work, is missing, or should change. The to-do list says what I'm going to do, this file says what's wrong. When something gets fixed, delete it from here (git keeps the history).

## Bugs

Things that exist but don't work as intended.

Nothing right now.

## Missing

Things that should exist but don't yet.

| What | Notes |
| ---- | ----- |
| Generic gates mapped to real chips | `CPU.dig`, `MAR.dig` and `SP.dig` still use 7 generic gates instead of 74HC parts: 3 AND and 1 OR in `CPU.dig` (the clock select and the reset button), 2 OR in `MAR.dig` and 1 OR in `SP.dig` (the load gating). |

## Limitations (by Design)

Not bugs, these are on purpose (or the price of something else), but they're easy to forget when programming.

| Limitation | Why |
| ---------- | --- |
| The MAR is lost after `JMP label`, `JCC label`, `CALL label`, `CALLcc label`, `RET` and `RETcc` | They use it to hold the target address. See `design-decisions/jumps.md`. |
| No `JCC MAR` | Only `JCC XY` and `JCC label`. |
| Shifts don't update Z and N | `SHR`/`ROR` use their own buffer, not the ALU, so they only load C (the bit shifted out) and V (cleared). (`SHL` and `ROL` are really `ADD A, A` and `ADC A, A`, so they update all four.) |
| `INC A` / `DEC A` need the immediate to be `0x00` | They add the IR's low byte. The assembler always leaves it at 0. |
| `MOV X, SPH` / `MOV Y, SPL` | The subOp (6 and 7) doubles as the destination register, that's why they only work with X and Y. |
| No `LD X, XY+` / `LD Y, XY+` | X and Y can't load while XY counts. |
| No `POP XY` instruction | The register file's decoder only loads the register in `[10:8]`, so one instruction can't load both. `PUSH XY` / `POP XY` are pseudo-instructions. |

## Cleanup

Leftovers that should be removed or updated.

Nothing right now.
