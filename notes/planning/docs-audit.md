# Docs Audit

Temporary (2026-10-25): delete it once everything here is fixed or decided.

Every doc in `notes/` and the README, checked against the `.dig` files, `crom_programmer.py` and the assembler. Nothing was changed. Each item says what the doc says, what the circuit or the code does, and how it could be fixed. The kinds are:

- Wrong: it says something the circuit or the code doesn't do
- Outdated: it was true before a change
- Missing: something that should be there and isn't
- Unclear: it's not wrong, but it's easy to misread
- Cleanup: leftovers (broken links and such)

The last part is a table with the sections of `doc-template.md` that each module doc has.

## Summary

About 70 items: 13 wrong, 19 outdated, 19 missing, 16 unclear and 3 cleanups. Most are small. These are the ones worth fixing first, because they say something the CPU doesn't do:

- `program_counter.md`: `nPCL_OE`/`nPCH_OE` are described as loads from the data bus. They're outputs to it (that's how `CALL` pushes the PC), and the PC never loads from the data bus.
- `mar.md`: it says the MAR isn't programmer-visible (programs use it directly), lists a `JCC MAR` that doesn't exist, and has `nMARL_LD` twice in the signals table.
- `reset.md`: it says the registers aren't reset, but `RST` clears A-F.
- `stack_pointer.md`: the SP starts at `0x3FFF` (it's `0xBAFF` now), and the PUSH timing argument doesn't hold on real hardware: `MEM_WR` comes from the EPROMs and goes away after the SP has already changed, which is the `MEM_WR` gating that's already an open point.
- `alu.md`: ROR's bit 7 is `SHR_IN0` (a control bit), not the C flag, and the accumulator has 2 output buffers, not 3. The same wrong `SHR_IN0` description is in `crom_programmer.py`, so it's in `controlbits.md` too.
- `instructiondecoding.md`: the table still has the examples from before the redesign (`ADD R1, R2` with any destination, `INC R1`, `PUSH` with Rdst, 1-word `JZ 0x80`).

The outdated ones are mostly the old memory map (`0x3FFF`, the framebuffer chip select, 15 KB of ROM) in the README, `stack_pointer.md` and the comments of `crom_programmer.py`. The three cleanups are quick: two broken image links (`controlunit.md` line 15, `program_counter.md` line 13) and a link pasted in the middle of a word (`74191-loadsync.md` line 7).

Fine as they are: `isa.md` (the tests check the table), the two generated docs, `instregister.md`, `controlunit.md`, `address_buffers.md`, `address_decoder.md`, `memory_map.md`, `interrupts.md` and `instruction-set-redesign.md`. `st-zeropage.md` and `fetch-execute-overlap.md` only have a syntax detail each.

Verification is missing from every module doc, but that one's easy now: each module has a test file in `digital/tests/`.

## README.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Outdated | Highlights | 48 KB of RAM, 15 KB of ROM, a 1 KB framebuffer and 256 bytes of MMIO | `ADDR_DEC.dig`: RAM `0x0000-0xBEFF` (47.75 KB), MMIO `0xBF00-0xBFFF`, ROM `0xC000-0xFFFF` (16 KB). The framebuffer is plain RAM (`0xBB00-0xBEFF` by convention), it has no chip select | "47.75 KB of RAM (1 KB of it for the framebuffer), 16 KB of ROM and 256 bytes of MMIO" |
| Outdated | Highlights | I/O: keyboard, timer and an SPI port for an OLED | There's no timer yet (`to-do.md`). In the simulation the SPI port drives the MAX7219 model, and there are 8 LEDs | "keyboard, 8 LEDs, and an SPI port (MAX7219 now, OLED planned)" |
| Outdated | Highlights | 77 logic chips so far | The simulation has 80 74xx chips (whole chips per module, plus 7 generic gates). The real count, with gates shared between modules, will be lower | update the number, or say it's the simulation count |
| Outdated | Architecture | the Address Decoder enables the RAM, the ROM, the framebuffer or the MMIO | 3 chip selects, no framebuffer one | drop "the framebuffer" |
| Outdated | main modules list | Address Decoder and MMIO: select RAM, ROM, framebuffer or I/O | same | same |
| Unclear | main modules list | Stack Pointer grows down from the end of RAM | The hardware doesn't fix where it starts. The programs put it at `0xBAFF`, right below the framebuffer area, not at the end of RAM (`0xBEFF`) | "grows down from wherever the program puts it (`0xBAFF`, below the framebuffer)" |
| Unclear | Architecture | the data bus is shared by the register file, the ALU, memory, the flags and the halves of the PC, the MAR and the SP | Also the IR's low byte (immediates) drives it. The MAR only loads from it, it never outputs to it | add the IR, or say who drives and who loads |
| Outdated | Status | the whole datapath works in the simulation | The result of `SHR`/`ROR` never reaches the data bus (missing junction, `issues.md`) | "works except the shifter output (see issues)" until it's fixed |
| Outdated | Status checklist | [ ] Test every instruction | `programs/tests` tests every instruction, `digital/tests` every module and the whole CPU | tick it |

Checked and right: 32 opcodes and 66 instructions (the `isa.md` table), 41 control bits, up to 16 steps, most instructions in 2 cycles, the description of the fetch and the address bus sources, and the Running It steps (`gen_docs.py` does warn about `isa.md`, and the generated docs are up to date).

## Hardware Design

### address_buffers.md

Everything matches `addr_buffer.dig` (3 74245, the values, the enables, `AB_L` passing straight through).

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Missing | Control Signals | - | `nRST` and `nHBA_OE` must never be low at the same time: both buffers would drive the high byte (`0xC0` and `0x00`). In the CPU it can't happen, because during the reset the control ROMs are off and the pull-up keeps `nHBA_OE` high. In Digital, the module tests found that a short like that at start-up leaves the simulation stuck | add a line about it |

### address_decoder.md

Fixed today, it matches `ADDR_DEC.dig` (the 3 equations, gate 3 of the 7400 free). Missing only the template sections (see the table at the end).

### alu.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Wrong | Overview, last bullet | the accumulator goes to 3 buffers: normal output, shift right, and roll right through carry | There are 2 buffers from the accumulator: A itself (`A_OE`) and the shifter (`nSHR`). The third 74245 is the ALU result (`nALU_OE`). There's no separate ROR buffer | "2 buffers from A (normal and shifted right) and one for the ALU result" |
| Wrong | Datapath Routing, ROR row | Shift MUX (D7) driven to `C_FLAG` | Bit 7 of the shifter is `SHR_IN0`, a control bit (bit 29), not the C flag | "driven by `SHR_IN0`". A ROR through carry can still be done in microcode only: the microcode address has C, so ROR can set `SHR_IN0` only when C = 1. The shifted-out bit going into C would need hardware, though |
| Outdated | 74382 table | ADI, CPI, ANI | The ISA calls them `ADD A, Imm`, `CP A, Imm`, `AND A, Imm` (old mnemonics) | rename |
| Unclear | 74382 table | Cin = X for AND/OR/XOR | The microcode leaves `ALU_CIN` at 0. It doesn't change the result, but it does change the C and V that get loaded | "0" |
| Unclear | Datapath Routing, INC/DEC row | B-input source: force 0 | Nothing forces it: the IR puts its low byte on the data bus (`nIRD_OE`), and the assembler leaves it at `0x00` (`issues.md` has it as a limitation) | "the IR's low byte (0x00)" |
| Unclear | Datapath Routing | the output bus source of ALU operations is the 74382 outputs | The result goes into A through the 74257 mux (`A_SEL = 1`). `nALU_OE` (ALU result to the bus) is never used by the microcode | say the result goes back into A, not to the bus |
| Missing | Flags | - | After a subtraction (and CP), C = 1 means no borrow (A >= B unsigned), because the 74382 does A + NOT(B) + 1. That's what `JC`/`JNC` see | add it |
| Missing | Flags | - | AND/OR/XOR also load C and V (`issues.md`) | a line pointing to the issue |
| Missing | whole doc | - | The accumulator (two 74173, cleared by `RST`), the 74257 input mux (`A_SEL`), `A_LD`/`A_OE` being active low and coming from the register file's decoders, a pin table and a chip table | template sections 1, 3 and 6 |

### regfile.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Outdated | second paragraph | `[7:5]` goes to the source decoder | Since the `ST zp` change, a 74157 in front of the source decoder picks `[7:5]` or `[10:8]` with `SRC_SEL` | mention the mux (it's explained in `st-zeropage.md`) |
| Missing | XY | - | X and Y load asynchronously (74191), so their load is ORed with CLK (the 7432), like the MAR and SP (`74191-loadsync.md`) | add it |
| Missing | whole doc | - | `RST` clears B-F (the 74173 reset pins) but not X and Y. The two 74138 decoders with `REG_LD_EN`/`REG_OE_EN`, and the pins | template sections 1, 3, 4 and 6 |
| Unclear | ICs Logic | the 74191 pairs use 2 74245 | It's 2 per register: X and Y each have one 74245 to the data bus and one to the address bus (4 in total) | "two each" |

### controlunit.md

Everything matches `CTRLUNIT.dig` and the microcode (the address bits, the 74163 with its synchronous clear, `nMPC_RST` AND `nRST`, the ROMs off during reset with every line pulled to its inactive level, HALT through ENP/ENT).

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Cleanup | line 15 | `![](notes/Attachments/Pasted%20image%2020261023235737.png)` | That image doesn't exist (it's an Obsidian leftover), the `<img>` right below is the real one | delete the line |
| Outdated | Timing | gating `MEM_WR` with the clock is an open point | `MEM_RD` needs it too: in Digital the keyboard loses keys because `KB_EN` glitches when a fetch follows an MMIO write (`issues.md`, `verification.md`) | add `MEM_RD` |

### instregister.md

Everything matches `IR.dig` (2 74377, 2 74245, the fields and the signals). Missing only Verification.

### mar.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Wrong | Control Signals table | `nMARL_LD` twice | The second row is `nMARH_LD` | typo |
| Wrong | Operations | JCC MAR uses `nMAR_OE` | There's no `JCC MAR` (`issues.md`). `nMAR_OE` is used by `LD`/`ST MAR`, `JMP MAR`, `CALL MAR`, `MOV SP, MAR`, and the last step of the direct jumps, calls and `RET` | list those |
| Missing | Operations | - | The direct jumps and calls load MARH and MARL from the IR, `RET` loads them from the stack, and `MOV MAR, SP` from the SP, so the MAR is lost after them | add them |
| Wrong | Overview | the MAR isn't programmer-visible, the CPU uses it automatically, also for pseudoinstructions | Programs load and use it directly (`MOV MARL/MARH`, `LD`/`ST MAR`, `INC`/`DEC MAR`, `JMP`/`CALL MAR`). What's automatic is that the direct jumps, calls and `RET` overwrite it, and those are native instructions, not pseudoinstructions | rewrite that paragraph |
| Wrong | Timing | the outputs only change on the rising edge | That's true when it counts. The load is asynchronous (74191), ORed with CLK, so a load happens while CLK is low (`74191-loadsync.md`) | add the load |
| Missing | whole doc | - | The 2 generic OR gates of the load (a 7432 on the breadboard), and a chip table | template section 6 |

### program_counter.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Wrong | Control Signals | `nPCL_OE` / `nPCH_OE` enable a parallel load into PCL / PCH from the data bus | They put the PC's low / high byte on the data bus (74245 from the counters to the bus), that's how `CALL` pushes the return address. The PC never loads from the data bus | "outputs PCL / PCH to the data bus" |
| Unclear | Control Signals | `PC_OE`: drives the PC onto the address bus | `PC_OE` = 1 takes the PC off the address bus (it drives it by default), so the row says the opposite of what a 1 does, even with the note | "1 = the PC stops driving the address bus" |
| Missing | Operations | (empty heading) | - | fill it in or remove it |
| Cleanup | line 13 | `![](notes/Attachments/Pasted%20image%2020261023235822.png)` | That image doesn't exist, the `<img>` below is the real one | delete the line |
| Missing | whole doc | - | A chip table: 4 74161, 4 74245, and one gate each of a 7408 and a 7432 | template section 6 |

### stack_pointer.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Outdated | Initialization, PUSH | the SP starts at `0x3FFF`, the end of RAM | RAM ends at `0xBEFF` now, and the programs put the SP at `0xBAFF` (right below the framebuffer area, `memory_map.md`) | `0xBAFF` |
| Wrong | Timing | the 74191 only changes on the rising edge | That's the counting. The load (`MOV SP, MAR` / `MOV SP, XY`, from the address bus) is asynchronous, ORed with CLK, so it happens while CLK is low (`74191-loadsync.md`) | add the load |
| Wrong (real hardware) | PUSH | the RAM latches the data on the rising edge while the SP decrements, and the 74HC191's 31-38 ns keep the address stable until the write is done | `MEM_WR` comes straight from the EPROMs, so it only goes away an access time (100+ ns for a 27C1024) after the clock edge, and by then the SP has already changed. On real hardware the write would still be on while the address changes. In Digital it works because its RAM takes the address when `WE` goes up, at the start of the step. This is the `MEM_WR` gating that's already an open point | say it depends on gating `MEM_WR` with the clock |
| Unclear | PUSH (1 cycle), POP (2 cycles) | 1 and 2 cycles | Those are the steps after the fetch. With the fetch, like `isa.md` counts them, it's 2 and 3 | say "steps", or 2 and 3 cycles |
| Outdated | Downward Growth | the low addresses have the zero page, dynamic vectors, etc. | There are no vectors since the interrupts were removed | drop "dynamic vectors" |
| Missing | whole doc | - | A chip table (4 74191, 4 74245, and the generic OR of the load, a 7432 on the breadboard) | template section 6 |

### statreg.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Unclear | Hardware | the data bus supplies the saved flags during `POPF` | In the module, yes. In `CPU.dig`, `STATUS_REG`'s `D IN` isn't on the data bus (the missing junction in `issues.md`), so even with `FL_SEL` set, `POPF` wouldn't work yet | point to the issue |
| Missing | Overview | the flags take the lower 4 bits of the pushed byte | The order: bit 0 Z, bit 1 C, bit 2 N, bit 3 V (the same order as the microcode address bits 12-15) | add it |
| Missing | Hardware | - | The 74173's reset is grounded, so the flags have no reset (they power up random), and the `nRST` pin of the module isn't connected to anything inside | add it |
| Missing | whole doc | - | A chip table (74157, 74173, 74245) | template section 6 |

### reset.md

Everything else matches: the 7474 synchronizer (the module test checks the press, the hold, the release and a short press), the PC gates, the control unit, and the table of inactive EPROM words (`0xF3FA`, `0xD428`, `0x017A` are exactly `active_low_mask`).

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Wrong | Overview | the registers aren't reset | `RST` clears A-F: it goes to the reset pins of the 74173 in `ALU.dig` (A) and `RFILE.dig` (B-F). X, Y, the flags, the SP and the MAR really aren't reset | "A-F are cleared, X, Y, the flags, the SP and the MAR aren't" |
| Missing | Overview, the table of parts | 4 parts | The ALU (A) and the register file (B-F) also take `RST` | add them |
| Missing | Idea: Power-on Reset | the power-on reset is only an idea | In `CPU.dig` the button is ANDed with Digital's Reset component, which keeps `RST_IN` low while the simulation starts, so the simulation already resets itself at power-on | say the simulation already does it, and the RC + 74HC14 would be the same thing on the breadboard |

### memory_map.md

Rewritten today, it matches `ADDR_DEC.dig`, `MMIO.dig` and how the programs use the RAM.

## Instruction Set

### isa.md

The table is checked by `programs/tests/test_microcode.py`: every opcode slot is there, and the opcodes, subOps and cycles match the microcode and the assembler. The notes and the pseudo-instructions are right too.

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Missing | Known Issues | - | `SHR` and `ROR` don't work in `CPU.dig` yet: their result never reaches the data bus (the missing junction in `issues.md`). The `POPF` fix needs that junction too | add a line |

### instructiondecoding.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Outdated | table, Conditional Jump | `JZ 0x80`, Imm = target address | Since the redesign the direct jumps are 2 words: word 1 has the high byte of the target in `[7:0]`, word 2 the low byte (`jumps.md`). There's also `JCC XY`, with no immediate | update the row, and add `JCC XY` |
| Wrong | table, Dual Register | `ADD R1, R2`, Rdst = target | The ALU operations always write A: the assembler puts 0 in `[10:8]`, and `A_SEL` only changes A's input. The dual-register instruction with a free destination is `MOV R1, R2` | `MOV R1, R2`, and `ADD A, R2` with Rdst = A |
| Wrong | table, Single-Register | `INC R1`, `PUSH R2`, Rdst = target | `INC` only exists for A, XY, MAR and SP. `PUSH` takes its register from `[7:5]` (Rsrc), `POP` from `[10:8]` (Rdst) | `POP R1` (Rdst) and `PUSH R2` (Rsrc) |
| Unclear | table, No-operand | `NOP`, `HALT` use the 8-bit opcode | `NOP` is a pseudo-instruction (`MOV A, A`, opcode `0x01`) | use `HALT` and `RET` |
| Missing | bit encoding | - | `ST Imm, REG` takes its register from `[10:8]` (through the `SRC_SEL` mux), because `[7:5]` are part of the zero-page address. And the zero-page instructions use `[7:0]` as the address | add a zero-page row (`LD REG, Imm` / `ST Imm, REG`) |
| Missing | first paragraphs | IRLB outputs to the data bus | It can also go to the address bus (`nIRA_OE`, zero page) | add it |

### controlbits.md

Generated, and up to date (`gen_docs.py` makes the same file, with no warnings). But it takes the descriptions from the comments in `crom_programmer.py`, and some of those are off:

| Kind | Bit | It says | The circuit | Fix (in `crom_programmer.py`, then `gen_docs.py`) |
| ---- | --- | ------- | ----------- | --- |
| Wrong | `SHR_IN0` (29) | bit 0 of the shr buffer; 0 = SHR, 1 = ROR | It goes into bit 7 of the shifted value (the last input of the shifter's 74245). A 1 there just sets bit 7, it doesn't make a rotate through carry | "bit 7 of the shifted value (0 for SHR)" |
| Outdated | `MEM_RD` (10), `MEM_WR` (11) | ROM/RAM/FB/MMIO | There's no framebuffer chip select anymore | drop FB |
| Outdated | `FL_SEL` (32) | (only first 4 flags) | There are only 4 flags since I and B were removed | drop it |

### instructionset_extended.md

Generated, and up to date.

## Design Decisions

`instruction-set-redesign.md`, `interrupts.md` and `st-zeropage.md` match the circuits and the microcode (the `ST zp` microcode table is exactly what `crom_programmer.py` does, and `SRC_SEL` is bit 39). The rest:

### 74191-loadsync.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Outdated | second paragraph | the 74191 is used in two places, XY and the SP | Also the MAR (four 74191, with the same OR gates on the loads) | add the MAR |
| Cleanup | line 7 | "that load signal com[mar](notes/hardware-design/mar.md)es from" | A link got pasted in the middle of "comes" | "comes from" |
| Unclear | the solution | it loads on the falling edge of the clock | With the OR, the load is on during the whole low half of the cycle: the register follows its input from the falling edge, and keeps what was there at the next rising edge. The module tests show it: if the data changes while the load is on, the register follows | "it loads while CLK is low, and keeps the value it had at the rising edge" |

### jumps.md

The cycles, opcodes and conditions match the microcode.

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Outdated | The Problem (third point), The Solution | an interrupt in the middle of the 3-instruction jump would lose the MAR | It's still a good reason for the time, but the interrupts were removed since | a short note pointing to `interrupts.md` |
| Unclear | The Solution | "since it's treated as two instructions, the microsteps are less", and later "since it is treated as 1 instruction" | It's one instruction made of two words | "one instruction in two words" |

### fetch-execute-overlap.md

Everything matches (step 1 always has `PC_INC`, the exceptions, the cycles).

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Unclear | comparison table | `LD reg, [XY]` | The assembler syntax is `LD REG, XY` (with brackets it doesn't assemble) | `LD reg, XY` |

### st-zeropage.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Unclear | The Problem, The Solution Now | `LD Imm, REG` | The syntax is `LD REG, Imm` (destination first), like in `isa.md` | swap them |

## Planning

### to-do.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Outdated | line 5 | make pseudoinstructions: NOP, SHL, ROL | The assembler already has them (`expand_pseudoinstructions`), and `isa.md` lists them | keep only "more complex ones" |
| Unclear | line 3 | fix the 'and' row of the table alu core | The AND row in `alu.md` now says S = 110, which is what the microcode does. If it was about something else, ignore this | check if it's still needed |

### issues.md

| Kind | Where | It says | The circuit / code | Fix |
| ---- | ----- | ------- | ------------------ | --- |
| Outdated | Missing, generic gates | `CPU.dig`, `MAR.dig`, `SP.dig` and `MMIO.dig` have 8 generic gates | 7 now, and none in `MMIO.dig` (it uses a 7400 and a 7404): `CPU.dig` has 3 AND and 1 OR (the clock select and the reset button), `MAR.dig` 2 OR and `SP.dig` 1 OR (the load gating) | update the list |
| Unclear | Limitations, the MAR | the MAR is lost after `JCC label` | Only when the jump is taken: a jump that isn't taken never touches the MAR | "after a taken `JCC label`" |

### ideas.md

The free slots it proposes (`0x03` sub-ops 2-7, `0x1F` sub-op 0, `0x02` sub-ops 6-7) are really free. One thing to add to the ISA bullet: fixing `ROR` (and the shifts) also needs the missing junction in `CPU.dig`.

`sources.md` and `doc-template.md`: nothing to check.

### verification.md

Written today, it matches the tools.

## Template Sections per Module

The 6 sections of `doc-template.md`: overview and pinouts, architecture, control signals, timing, verification, physical TTL mapping. "Yes" means it's there, "part" that it's there but incomplete or with errors (see above), "no" that it's missing.

| Module doc | Overview | Pinouts | Architecture | Control | Timing | Verification | TTL mapping |
| ---------- | :------: | :-----: | :----------: | :-----: | :----: | :----------: | :---------: |
| `program_counter.md` | yes | no | yes | part | yes | no | no |
| `stack_pointer.md` | yes | no | yes | yes | part | no | no |
| `mar.md` | yes | no | yes | part | part | no | no |
| `statreg.md` | yes | no | yes | yes | yes | no | no |
| `alu.md` | yes | no | yes | part | no | no | part |
| `regfile.md` | part | no | part | no | no | no | part |
| `address_decoder.md` | yes | part | yes | - | no | no | part |
| `address_buffers.md` | yes | yes | yes | yes | no | no | yes |
| `instregister.md` | yes | part | yes | yes | yes | no | yes |
| `controlunit.md` | yes | yes | yes | yes | yes | no | yes |
| `reset.md` | yes | yes | yes | yes | yes | no | yes |
| MMIO | no doc yet | | | | | | |

Verification is missing everywhere, but now it's an easy one: every module has its test file in `digital/tests/` (`MODULE_tests.txt`, all passing), so each doc can point to it and to `verification.md`. Most docs also lack a pin table, which `digital/tests/` can help with too: the header line of each test file lists every pin of the module.
