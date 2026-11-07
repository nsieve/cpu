# Direct Jumps

### The Problem

Initially, Jump instructions were only possible as indirect, meaning that if I wanted to jump to a label, the only possible way to do so in 1 line of code was to let the assembler handle it and treat it as a pseudo-instruction which decodes into three instructions:

```
MOV MARH, LABEL_HIGH
MOV MARL, LABEL_LOW
JCC/JMP MAR
```

This solution had many problems.
First of all, it was the slowest, because it had to execute 3 whole instructions just for a jump label.
Second, if a conditional jump's condition is NOT met, the instruction would still take as long as if the condition is met, purely because it would be checked at the last instruction.
And third, and by far most importantly, if an interrupt is triggered, since it synchronizes on the microstep 0 (as well as other conditions), it could happen that the first or second instructions (loading MAR) are performed, and once the routine is finished and everything gets popped back, since the MAR is not pushed onto the stack, the values would be lost and therefore the instruction would be incorrect.

### The Solution

Native 2-word jumps.
Now, not only the indirect jumps (JMP MAR, JMP XY) are in the instruction set, but the direct jumps are not treated as a pseudoinstruction, they are a 2-word instruction.
Because the ROM can only read a word at a time, an instruction with a 16bit immediate must be done in two words.

It would be decoded like this:
· word 1: instruction opcode + label_high
· word 2: instruction opcode + label_low

This way, all three problems from before are fixed, because, since it's treated as two instructions, the microsteps are less, but also, because the condition check is done at the beginning, if conditions are not met, it quickly increments the pc again to point at the next instruction, and most importantly, since it is treated as 1 instruction, the microprogram counter is not reset until the entire instruction is performed, meaning that if interrupt happens on the middle of the execution, it would wait until the instruction is finished, eliminating MAR register corruption.

### Direct vs Indirect

So now there are two kinds of jumps (and calls):

- Direct (`JMP label`, `JCC label`, `CALL label`, `CALLcc label`): the target address is written inside the two words of the instruction itself. The PC loads from the address bus, so the whole target has to be on the bus at once, but the IR only holds one word. So in step 1 the high byte (from word 1) goes into the jump register (`J_REG`, see `hardware-design/jump_register.md`), word 2 is fetched into the IR, and in the last step `J_REG` drives the high byte of the address bus and the IR the low byte (like in the zero-page instructions), and the PC loads it. The MAR isn't touched. Before `J_REG`, the MAR held the target, so whatever was in the MAR was lost after every direct jump or call, and they took one more cycle (the low byte had to be copied into MARL).
- Indirect (`JMP MAR`, `JMP XY`, `JCC XY`, `CALL MAR`, `CALL XY`): the CPU jumps to whatever address is already in that register. These are 1-word instructions.

To keep them organized, all jumps, calls and conditional returns live in opcodes 25 to 29 (`RET` is in 31, with `LDT`, the flags and `HALT`):

| Opcode | Subop | Instruction | Cycles |
| ------ | ----- | ----------- | ------ |
| 25 | 0-7 (condition) | RETcc | 5 taken, 2 not taken |
| 26 | 0-7 (condition) | CALLcc label | 6 taken, 3 not taken |
| 27 | 0-7 (condition) | JCC label | 4 taken, 3 not taken |
| 28 | 0-7 (condition) | JCC XY | 2 |
| 29 | 0 | JMP label | 4 |
| 29 | 1 | CALL label | 6 |
| 29 | 2 | JMP MAR | 2 |
| 29 | 3 | JMP XY | 2 |
| 29 | 4 | CALL MAR | 5 |
| 29 | 5 | CALL XY | 5 |
| 31 | 1 | RET | 5 |

The conditions are: 0 = C, 1 = NC, 2 = Z, 3 = NZ, 4 = N, 5 = NN, 6 = V, 7 = NV. There is no `JCC MAR`, only `JCC XY`.

For the calls, the PC is pushed only AFTER it has been incremented past the whole instruction, so the address saved on the stack is always the one of the next instruction (before, the high byte was pushed before the increment, which broke when the CALL was at the end of a page like `0xC0FF`). `CALL label` does that second increment in the same step as the fetch of word 2 (the IR loads and the PC counts on the same clock edge, so the fetch still uses the old address), so the pushes start in step 3.

`RET` and `RETcc` still go through the MAR: they pop the return address into MARL and MARH, and the PC loads it from there. So the MAR is lost after them.
