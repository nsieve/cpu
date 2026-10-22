# Fetch-Execute Overlap

### The Problem

In my previous CPU, every instruction started the same way:

| Step | What it does                  |
| ---- | ----------------------------- |
| 0    | fetch the instruction into the IR |
| 1    | increment the PC              |
| 2... | execute the instruction       |

Step 1 did nothing else than incrementing the PC, so even the simplest instruction (like `MOV reg, imm8`) took 3 cycles, and most of them took about 3.

### How I Realized

The idea came from the 2-word instructions. In those, the PC has to be incremented between the first and the second word, and I realized that I could do it in the same step as the instruction was already doing something else, instead of giving it a step of its own. And then it hit me that the exact same thing could be done with the first word, which means every instruction.

### How It Works

In the SFD-8, step 1 always does `PC_INC` together with the actual work of the instruction:

| Step | What it does                                    |
| ---- | ----------------------------------------------- |
| 0    | `MEM_RD`, `nIR_LD`: fetch the instruction        |
| 1    | `PC_INC` + execute the instruction (+ `nMPC_RST`) |

This works because the PC only changes on the clock edge at the end of step 1, so during the whole step it still holds the address of the current instruction, and the increment doesn't need any bus. Most instructions finish right there, so they take 2 cycles instead of 3.

The PC drives the address bus by default. When an instruction needs the address bus for something else (like `LD reg, MAR` or `PUSH`), it activates `PC_OE`, which disconnects the PC from the bus. The PC keeps counting anyway, because the 74161 increments whether its output is enabled or not.

Some examples comparing both CPUs:

| Instruction      | CPUv3 | SFD-8 |
| ---------------- | ----- | ----- |
| `MOV reg, imm8`  | 3     | 2     |
| `LD reg, [XY]`   | 3     | 2     |
| `PUSH reg`       | 3     | 2     |
| `POP reg`        | 4     | 3     |

### Where It Can't Overlap

There are a few instructions where step 1 can only do `PC_INC`, and the real work has to wait for step 2:

- `CALL MAR` and `CALL XY`: the PC itself is what gets pushed onto the stack, and the pushed value has to be the return address (the instruction after the CALL). Since the PC only changes at the end of step 1, pushing during step 1 would push the address of the CALL itself, so the pushes start at step 2. This is the same reason `CALL label` only pushes after its last `PC_INC`. (This was actually a bug: the high byte of the PC was being pushed before the increment took effect, and it broke when the CALL was at the end of a page, like `0xC0FF`.)
- `JCC label` when the jump is not taken: the PC has to skip the second word, so it has to be incremented twice, and a counter can only count once per clock edge. That's why it takes 3 cycles instead of 2.

Other instructions take more than 2 cycles, but not because of the overlap:

- `POP`, `RET` and `POPF`: the SP has to move before the read, so that takes its own step.
- `MOV MAR, SP`: the SP goes through the 8-bit data bus in two halves.
