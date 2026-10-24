- Be able to generate QR codes on the OLED screen(for example the QR link for the github repo)
- Make a compiler (or adapt an existent one)
- Serial port (UART) to talk with a PC: print text to a terminal for debugging, and later load programs into RAM without reprogramming the ROM. A UART chip (like a 6850) is easier but breaks the 74HC-only rule, and bit-banging it through an MMIO pin is cheap in chips but hard to time
- Random numbers with a software generator (LFSR or xorshift, only needs shifts and XOR), seeded by reading the timer when the user presses the first key. This works if the timer is a free-running counter the program can read
- 7-segment display for numbers: done in the simulation with a MAX7219 on the SPI port (model in `digital/max7219_sim.dig`, driver in `programs/lib/max7219.asm`). Still to decide if the real module goes on the breadboard
- A Digital component for the SSD1306 OLED (and the MAX7219), as its own repo: nobody seems to have one, and it would let people test display code in the simulation. Either as a `.dig` model or as a Java plugin for Digital

## ISA Improvements

Things that came up while writing the first programs (Fibonacci, primes, the MAX7219 driver):

- ALU operations with an immediate: only `ADD`, `AND` and `CP` have one, so subtracting a constant takes `MOV B, Imm` + `SUB A, B`. The 6 free sub-ops of `0x03` (2-7) could hold `SUB`, `SBC`, `ADC`, `OR` and `XOR A, Imm`. Only microcode and assembler, the same as `ADD A, Imm` with other ALU select bits. `OR`/`XOR` with an immediate are also what's needed to set and clear single bits in the MMIO registers
- Fix the known microcode bugs (`issues.md`): `ROR` is the same as `SHR`, shifts don't update the carry (no fast shift-and-add multiplication without it), `POPF` doesn't set `FL_SEL`, and logic operations load C and V
- Tables in the ROM: right now the ROM only goes to the IR, so a program can't read constant data from it (fonts, images, lookup tables). Instead of a new 74245 from the ROM to the data bus, the IR can do it with the same trick as the direct jumps: a `LDT A, XY` instruction (`0x1F` sub-op 0, so the destination is A) loads the word at XY into the IR and then outputs its low byte with `nIRD_OE`. Every table word has the same opcode in its high byte (`0xF8`), so the opcode the control unit sees doesn't change. 3 cycles, no hardware, the assembler would need a `.TABLE` directive
- Store with auto-increment, `ST XY+, REG` (`0x02` sub-op 6 or 7): store at XY and increment XY in the same step (it only changes on the clock edge). Half the instructions to fill or copy memory, like the framebuffer. The load version doesn't fit as well, because the destination comes from `[10:8]`
- Not worth it for now: relative jumps (faster loops and they don't overwrite the MAR, but they need a 16-bit adder for the PC) and a hardware multiplier (a table of squares gets most of the speed)

## Demo Ideas (For the Final Presentation)

- Snake or Pong on the OLED with the keyboard: interactive, and it uses everything at once
- The Mandelbrot set on the OLED, drawn line by line. It needs multiplication, done in software (shift and add) or with a table of squares (x·y = ((x+y)² − (x−y)²) / 4), which is about 10 times faster
- A small monitor: type commands on the keyboard to look at and change memory, or run programs
- A short video of the CPU running in the README, and later one of the breadboard
