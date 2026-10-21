# MEMORY MAPPING

The memory layout allocates the first 48 KB of RAM to the lower part of the CPU in order to provide a zero page (`0x0000-0x00FF`).The rest, is divided between the ROM, the Framebuffer and the MMIO/Interrupt vectors in the upper region (`0xC000-0xFFFF`).

## MEMORY MAP

| Address Range   | Size  | Module                             | Active Signal |
| --------------- | ----- | ---------------------------------- | ------------- |
| `0x0000-0xBFFF` | 48 KB | RAM, stack & zero page             | `\RAM_CS`     |
| `0xC000-0xFBFF` | 15 KB | Firmware ROM                       | `\ROM_CS`     |
| `0xFC00-0xFEFF` | 1 KB  | OLED Framebuffer                   | `\FB_CS`      |
| `0xFF00-0xFFFF` | 256 B | MMIO registers & Interrupt vectors | `\MMIO_CS`    |
