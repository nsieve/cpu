# Program Counter

## Overview & Memory Layout

The Program Counter, or _PC_, is a 16-bit register that holds the address of the next instruction to be fetched. It is implemented as a 16-bit synchronous up counter with parallel load, using four 74161 4-bit binary counters.
### Initialization

At reset, the PC loads the hardwired vector `0xC000`, which is the start of ROM. This guarantees that after reset the CPU begins executing from a known location instead of `0x0000`.

## Hardware Architecture & Data Path

The PC is built from four 74161 4-bit synchronous binary counters cascaded into a single 16-bit counter. The output of the PC is driven either onto the address bus, for normal fetching operations, or the data bus, for loading the PC into the RAM.
![](notes/Attachments/Pasted%20image%2020261023235822.png)
<img src="../Attachments/pc_dig.png" alt="Program Counter ICs" width="900" />

### Reset Circuit

During reset, the PC has to stop driving the address bus (the Reset Buffer drives `0xC000` on it) and load that address. Two gates force this, no matter what the control bits say:

| PC input       | Logic                | During reset                        |
| -------------- | -------------------- | ----------------------------------- |
| `/LD` (74161)  | `nPC_LD` AND `nRST`  | always 0, so it loads on every edge |
| `/OE` (74245s) | `PC_OE` OR `RST`     | always 1, so it's off the bus       |

At first these were XOR gates, which only worked if the microcode wasn't using `nPC_LD` or `PC_OE` at that moment. More about the whole reset in `reset.md`.

## Control Signals & Operations

| Signal    | Active Level | Function                                           |
| --------- | ------------ | -------------------------------------------------- |
| `PC_INC`  | HIGH         | Enables incrementing on the 74161s                 |
| `nPC_LD`  | LOW          | Enables parallel load into the PC from address bus |
| `PC_OE`   | *HIGH        | Drives the PC onto the address bus                 |
| `nPCL_OE` | LOW          | Enables parallel load into the PCL from data bus   |
| `nPCH_OE` | LOW          | Enables parallel load into the PCH from data bus   |
| `RST`     | HIGH         | Forces PC load from vector and disables output     |

_*note: the `PC_OE` is active LOW, but for the sake of convenience it's put as active high. It's done that way so that the microprogrammer doesn't need to activate it on every "normal" instruction_

### Operations

## Timing, Latches & Critical Paths

The 74161 is a synchronous, edge-triggered counter. Its outputs change only on the rising edge of the clock, after the internal propagation delay `t_pd`.

## Design Justifications

### 74161 Instead of 74191

The PC only needs to increment and load. It never needs to decrement. The 74161 is a dedicated up counter with parallel load, so it requires fewer control signals than the 74191. This makes the wiring simpler and the control logic smaller. The 74191 is still used for the Stack Pointer, MAR and XY register pair, because those need both increment and decrement.