# Memory Mapping

The RAM goes first, in the lower part of the address space, so that the zero page (`0x0000-0x00FF`) is RAM and `LD`/`ST` with an 8-bit address can use it. The ROM takes the top 16 KB, and the 256 bytes right below it are the MMIO registers. After a reset the PC starts at `0xC000`, the start of the ROM (see `reset.md`).

## Memory Map

| Address Range   | Size     | Module         | Active Signal |
| --------------- | -------- | -------------- | ------------- |
| `0x0000-0xBEFF` | 47.75 KB | RAM            | `\RAM_CS`     |
| `0xBF00-0xBFFF` | 256 B    | MMIO registers | `\MMIO_CS`    |
| `0xC000-0xFFFF` | 16 KB    | Firmware ROM   | `\ROM_CS`     |

## MMIO Registers

The MMIO module only decodes `A0-A2` (with a 74138), so it has 8 addresses, and they repeat every 8 bytes through the whole `0xBF00-0xBFFF` block (`0xBF08` is the same as `0xBF00`, and so on). 4 of them are used:

| Address         | Name            | Direction | What it does                                                         |
| --------------- | --------------- | --------- | -------------------------------------------------------------------- |
| `0xBF00`        | Keyboard data   | Read      | The code of the key. Reading it also takes it out of the keyboard's buffer |
| `0xBF01`        | Keyboard status | Read      | Bit 7 = 1 when there's a key waiting                                 |
| `0xBF02`        | `SPI_OUT`       | Write     | Bit 0 = SCLK, 1 = MOSI, 2 = OLED D/C, 3 = OLED CS, 4 = MAX7219 CS     |
| `0xBF03`        | `DISPLAY`       | Write     | The 8 LEDs                                                           |
| `0xBF04-0xBF07` | -               | -         | Free                                                                 |

## RAM Conventions

Nothing in the hardware separates these, it's only how the programs use the RAM, so a program can change it if it needs to:

| Address Range   | What                    | Notes                                                    |
| --------------- | ----------------------- | -------------------------------------------------------- |
| `0x0000-0x000F` | Zero page, free         | `main.asm` uses it for its checks                        |
| `0x0010-0x003F` | Zero page, library      | Used by `programs/lib/max7219.asm`                       |
| `0x0040-0x00FF` | Zero page, program      | Each program's own variables                             |
| `0x0100-0xBAFF` | General RAM and stack   | The stack starts at `0xBAFF` and grows down              |
| `0xBB00-0xBEFF` | OLED framebuffer        | 1 KB (128x64 pixels, 1 bit each), for the OLED once it's built |

The framebuffer doesn't have its own chip select: the program draws in normal RAM and then sends it to the OLED over SPI.
