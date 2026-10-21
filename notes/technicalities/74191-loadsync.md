# 74191 Load Synchronization

The 74191 ICs are 4-bit synchronous, reversible, up/down binary counters. Although they operate synchronously, the load control works asynchronously.

They are used in two different places on the CPU. First is on the Register File, for the XY register pair, and secondly, is for the Stack Pointer. In both cases, they are wired almost identically, and it's solved the same way.

For the XY register pair, the 74138 decoder outputs are active-low. For the SP, that load signal com[mar](notes/hardware-design/mar.md)es from the microprogrammed Control Unit, and it can be coded to be output high by default, and only when loading it goes low.

The way this is solved so that loads can be done safely is to load on the falling edge of the clock tick, since the instructions and (most of) the CPU works on the rising edge of the clock.

The 74191's load input is active-low, so if I wanted to only load when the load bit is low and also on the falling edge of the clock:

| Load bit | CLK | Output |
| -------- | --- | ------ |
| 0        | 0   | 0      |
| 0        | 1   | 1      |
| 1        | 0   | 1      |
| 1        | 1   | 1      |

So just an OR gate would solve this.