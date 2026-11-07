- Be able to generate QR codes on the OLED screen(for example the QR link for the github repo)
- Make a compiler (or adapt an existent one)
- Serial port (UART) to talk with a PC: print text to a terminal for debugging, and later load programs into RAM without reprogramming the ROM. A UART chip (like a 6850) is easier but breaks the 74HC-only rule, and bit-banging it through an MMIO pin is cheap in chips but hard to time
- Random numbers with a software generator (LFSR or xorshift, only needs shifts and XOR), seeded by reading the timer when the user presses the first key. This works if the timer is a free-running counter the program can read
- 7-segment display for numbers: done in the simulation with a MAX7219 on the SPI port (model in `digital/max7219_sim.dig`, driver in `programs/lib/max7219.asm`). Still to decide if the real module goes on the breadboard
- A Digital component for the SSD1306 OLED (and the MAX7219), as its own repo: nobody seems to have one, and it would let people test display code in the simulation. Either as a `.dig` model or as a Java plugin for Digital

## ISA Improvements

Things that came up while writing the first programs (Fibonacci, primes, the MAX7219 driver):

- Not worth it for now: relative jumps (faster loops and they don't overwrite the MAR, but they need a 16-bit adder for the PC) and a hardware multiplier (a table of squares gets most of the speed)

## Demo Ideas (For the Final Presentation)

- Snake or Pong on the OLED with the keyboard: interactive, and it uses everything at once
- The Mandelbrot set on the OLED, drawn line by line. It needs multiplication, done in software (shift and add) or with a table of squares (x·y = ((x+y)² − (x−y)²) / 4), which is about 10 times faster
- A small monitor: type commands on the keyboard to look at and change memory, or run programs
- A short video of the CPU running in the README, and later one of the breadboard
