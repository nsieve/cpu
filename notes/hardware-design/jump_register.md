# Jump Register

## Overview

The jump register (`J_REG`) holds the high byte of a direct jump's target while the CPU fetches the second word of the instruction. `JMP label`, `JCC label`, `CALL label` and `CALLcc label` use it.

The PC loads from the address bus, so the whole target has to be on the bus at once, but it comes in two words: the high byte in word 1 and the low byte in word 2. The IR only holds one word, so the high byte has to wait somewhere while word 2 is fetched, and that's `J_REG`. In the last step it drives the high byte of the address bus, the IR drives the low byte (with `nIRA_OE`, like in the zero-page instructions), and the PC loads the address.

Before `J_REG`, the direct jumps used the MAR for this, so they overwrote it, and they took one more cycle (see `design-decisions/jumps.md`).

## Hardware Architecture

| Pin      | Direction | Function                                       |
| -------- | --------- | ---------------------------------------------- |
| `D_BUS`  | in        | the data bus (8 bits), what gets loaded        |
| `nJ_LD`  | in        | load at the end of the step (active-low)       |
| `nJ_OE`  | in        | drive `AH_BUS` (active-low)                    |
| `CLK`    | in        | the CPU clock                                  |
| `AH_BUS` | tri-state | the high byte of the address bus (8 bits)      |

It's a 74574 (8 D flip-flops with tri-state outputs) and one OR gate of a 7432. The 74574's output enable is `nJ_OE`, so while it's high the outputs are high impedance and `J_REG` doesn't affect the address bus.

The 74574 has no load enable: it loads on every rising edge of its clock. So its clock is `CLK OR nJ_LD`. While `nJ_LD` is high, the clock stays high and nothing loads. While it's low, the clock follows `CLK`, and the 74574 loads the data bus on the rising edge at the end of the step, together with every other register.

In `CPU.dig`, `AH_BUS` goes into the upper half of a splitter whose lower half isn't connected, so `J_REG` only drives the high byte of the address bus.

## Timing

The OR only works because `nJ_LD` never changes while `CLK` is low. The EPROMs change their outputs right after the rising edge (the micro-PC counts on it), so `nJ_LD` settles in the first half of the step, while `CLK` is still high and the OR's output stays high whatever `nJ_LD` does. If `nJ_LD` went high while `CLK` is low, the OR would make a rising edge, and the 74574 would load in the middle of the step.

## Control Signals

| Signal  | Active Level | Function                                                      |
| ------- | ------------ | ------------------------------------------------------------- |
| `nJ_LD` | LOW          | loads the data bus at the end of the step (control bit 43)    |
| `nJ_OE` | LOW          | drives the high byte of the address bus (control bit 44)      |

Both come from EPROM 3 (D11 and D12) and have pull-ups, so they're inactive during the reset (see `reset.md`).

### In the Direct Jumps

| Step | `JMP label`, taken `JCC label`         | `CALL label`, taken `CALLcc label`                |
| ---- | -------------------------------------- | ------------------------------------------------- |
| 0    | fetch word 1                           | fetch word 1                                      |
| 1    | `J_REG` <- `IR[7:0]` (the high byte), PC + 1 | the same                                    |
| 2    | fetch word 2 into the IR               | fetch word 2 into the IR, PC + 1 (the return address) |
| 3    | PC <- `J_REG:IR[7:0]`                  | push PCH                                          |
| 4    |                                        | push PCL                                          |
| 5    |                                        | PC <- `J_REG:IR[7:0]`                             |

Step 1 is `nIRD_OE` + `nJ_LD`, and the last step is `PC_OE` + `nIRA_OE` + `nJ_OE` + `nPC_LD`. So `JMP label` and a taken `JCC label` take 4 cycles, and `CALL label` and a taken `CALLcc label` take 6. `RET` doesn't use `J_REG`, it pops the return address into the MAR.

## Verification

- `digital/tests/J_REG_tests.txt`: it only loads while `nJ_LD` is low, on the rising edge at the end of the step, `AH_BUS` floats while `nJ_OE` is high, and every bit on its own.
- `digital/tests/check_cpu.py`: the programs jump through it all the time, and the address bus is compared with the emulator in every cycle.

## Physical TTL Mapping

| Part           | Chip                       | Quantity |
| -------------- | -------------------------- | -------- |
| the register   | 74HC574                    | 1        |
| the clock gate | 74HC32 (1 of its 4 gates)  | 1        |

Only one gate of the 7432 is used. The other three are as many as the generic OR gates of the MAR and SP load gating (`planning/issues.md`), so on the breadboard they could share this chip.
