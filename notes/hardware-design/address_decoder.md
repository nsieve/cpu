# Address Decoder

The address decoder is a module which (as the name says) decodes the chip selects of each memory module. In order to understand it work, let's see the memory map of the CPU, which will clarify what it actually does:

| Address Range   | Size     | Module         | Active Signal |
| --------------- | -------- | -------------- | ------------- |
| `0x0000-0xBEFF` | 47.75 KB | RAM            | `\RAM_CS`     |
| `0xBF00-0xBFFF` | 256 B    | MMIO registers | `\MMIO_CS`    |
| `0xC000-0xFFFF` | 16 KB    | Firmware ROM   | `\ROM_CS`     |

Its only job is to make sure that, when the address is on each address range, the specific active signal of each memory module activates, which since it's active low, goes to zero. The MMIO registers inside their block and the RAM conventions are in `memory_map.md`.

## Decoder Schematic Connections

<img src="../Attachments/adr_dec.png" alt="Address decoder" width="500" />
