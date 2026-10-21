# Reset Buffer & Logic

It's a 16-bit buffer that has the address `0xC000` hardwired in its inputs, meaning all bits are 0 except for the 2 MSB.
This buffer is only activated when the reset button is pressed, but it needs the rising edge of the clock cycle to work, but the falling edge can be ignored.

For the Hardware reset logic, it was also needed to change the program counter input and output, so that when the reset signal is on, it behaves differently. 
This happens because the program counter by default it's outputting its address to the address bus, so if the buffer of the reset was enabled, it would short.

## Program Counter Load Enable

Since the signal for the program counter to load is active-low, as well as the control bit for it, the only times the PC should load a value should be when the reset is low and the load signal goes low, otherwise, it shouldn't.

| Reset signal | nPC_LD | OUTPUT |
| ------------ | ------ | ------ |
| 0            | 0      | 0      |
| 0            | 1      | 1      |
| 1            | 0      | 1      |
| 1            | 1      | 0      |

A single XOR gate would be needed.

## Program Counter Output Enable

For the output enable, since it's controlled with a 74245, its input is also active-low, but in this case, the control bit was inverted so that it's active-high, making it work exactly the same as the previous one, and also only needing one XOR gate.

| Reset signal | PC_LD | OUTPUT |
| ------------ | ----- | ------ |
| 0            | 0     | 0      |
| 0            | 1     | 1      |
| 1            | 0     | 1      |
| 1            | 1     | 0      |
