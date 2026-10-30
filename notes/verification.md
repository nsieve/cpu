# Verification

There are three layers of checks, and together they cover the whole chain from the instruction set to the circuit:

1. `programs/emulator.py` runs programs on a model of the CPU, using the real microcode from `crom_programmer.py`.
2. `programs/tests/` checks the emulator, and through it the microcode, against what `isa.md` says each instruction does.
3. `digital/tests/` checks the Digital circuits: every module on its own with Digital's test cases, and the whole `CPU.dig` compared with the emulator, cycle by cycle.

If the emulator does what `isa.md` says (layer 2), and `CPU.dig` does exactly what the emulator does (layer 3), then the circuit does what `isa.md` says.

## The Emulator

`programs/emulator.py` simulates the CPU one clock cycle (one microstep) at a time. In every cycle it takes the control word from the microcode, at the same address the EPROMs see (opcode, micro-PC and flags), and does what those control bits do: it works out what drives the address and data buses, and then loads every register that loads on that clock edge. The rest of the CPU is modeled from the `.dig` files:

- the ALU is two 74382, including the carry and overflow they give in the logic modes (checked against Digital's 74382 with all 4096 input combinations)
- the ROM only goes to the IR, so reading the ROM area through the data bus gives nothing
- the MMIO has the keyboard (data and status), `SPI_OUT` with the MAX7219 model on it, and the LEDs

Since it follows the microcode, the cycle counts are exact, and it's fast: `primes.asm` (1.7 million cycles) takes under a second, while Digital needs about a minute and a half for it without the GUI.

```
python3 programs/emulator.py programs/primes.asm                 run until HALT, show the display and LED changes
python3 programs/emulator.py programs/fibonacci.asm --hz 100e3   times for a 100 kHz clock (1 MHz by default)
python3 programs/emulator.py programs/main.asm --trace           print every instruction with the registers after it
python3 programs/emulator.py programs/keyboard_test.asm --keys "Ab1" --key-interval 10000 --max-cycles 40000
python3 programs/emulator.py programs/fibonacci.asm --random     RAM and registers start random, like real hardware
python3 programs/emulator.py --microcode "JZ 0x1234"             what each microstep of an instruction does
```

`--microcode` shows the microcode in words. For a conditional jump it shows both ways:

```
JZ 0x1234 = 0xDA12 0xDA34, opcode 0xDA (base 0x1B, subOp 2)

when Z = 0 (3 cycles):
  step 0  address bus = PC, IR <- ROM[address]
  step 1  PC <- PC + 1
  step 2  PC <- PC + 1, next instruction

when Z = 1 (5 cycles):
  step 0  address bus = PC, IR <- ROM[address]
  step 1  data bus = IR[7:0], PC <- PC + 1, MARH <- data
  step 2  address bus = PC, IR <- ROM[address]
  step 3  data bus = IR[7:0], PC <- PC + 1, MARL <- data
  step 4  address bus = MAR, PC <- address bus, next instruction
```

It stops with an error on anything that would go wrong on real hardware: two drivers on a bus at the same time, loading from a bus nobody drives, or fetching an instruction from outside the ROM. It warns about reading RAM that was never written (it powers up random) and writing to the ROM area.

It doesn't model timing: glitches, races and propagation delays don't exist in it, and every register loads exactly on the clock edge. It starts right after the reset (PC at `0xC000`, micro-PC at 0, A-F cleared), and there's no OLED yet.

## Python Tests

```
python3 -m unittest discover -s programs/tests -v
```

They take about 3 seconds, and only need Python.

- `test_instructions.py`: every instruction, with edge cases and random values, compared with a model of the ISA written from `isa.md` (not from the microcode): the result, the flags and the cycles. The known bugs from `planning/issues.md` (`ROR`, `POPF`, and C and V after the logic operations) are marked as expected failures. When one gets fixed, its test shows up as an "unexpected success", and the marker can go.
- `test_microcode.py`: `eprom1-3.hex` and the three ROMs inside `CTRLUNIT.dig` hold what `crom_programmer.py` makes (Digital keeps its own copy of the ROM data, so it has to be reloaded after every change), every instruction ends, no step drives a bus twice, and the instruction table of `isa.md` has every opcode slot with the right opcode, subOp and cycles.
- `test_programs.py`: every program in `programs/` runs to the end with the right result, and also with random RAM and registers at the start.

## Digital Tests

These need Java and Digital. The scripts look for `Digital.jar` in `~/Applications/Digital/`, or wherever `DIGITAL_JAR` points.

### Module Tests

```
python3 digital/tests/run_module_tests.py              every module (about 15 s)
python3 digital/tests/run_module_tests.py ALU MAR      some of them
python3 digital/tests/run_module_tests.py --keep DIR   also save the test circuits, to open them in Digital
```

Every module has a `MODULE_tests.txt` in `digital/tests/` with test cases in Digital's own test syntax (the one of the Testcase component). Each `## name` line starts a test case, and the signals are the module's pins, with spaces and brackets turned into underscores (`A IN` is `A_IN`, `[15:11]` is `I15_11`).

The tests can't go straight into the `.dig` files, for two reasons. Digital only finds subcircuits in the folder of the circuit it opens (and below it), so a test circuit in `digital/tests/` can't use the modules in `digital/`. And the test syntax doesn't accept pin names with spaces or brackets. So for every module, the script copies `digital/` into a temporary folder and makes a test circuit there: the module as a subcircuit, each pin wired to an input or an output with a name the test syntax accepts, and the test cases (`ModuleWrapper.java`). Then it runs it with Digital's command line. The `.dig` files in `digital/` are never changed. With `--keep`, the test circuits are saved, and opening one in Digital and pressing F8 runs its tests.

A few things to keep in mind when writing them:

- A `C` in the clock column is a whole clock pulse (0, 1, 0) after the other inputs are set.
- In a row every input changes at once. With the 74191 (MAR, SP, X, Y), whose load is asynchronous, changing the data in the same row where a load turns off is a race, so the data only changes while no load is on. In the CPU this can't happen: the load turns off with the clock edge, before the data bus changes.
- The active-low inputs (`nXXX`) start at 1, like the pull resistors keep them in the CPU while it starts. A `defaults: NAME=VALUE` line before the first test case sets other start values (the ALU's `A_LD` and `A_OE` are active low without an `n`).
- `CTRLUNIT_tests.txt` uses `{cw OPC STEP FLAGS}`, which the script fills in with what `crom_programmer.py` gives for that address, so it follows the microcode when it changes.

### The CPU Against the Emulator

```
python3 digital/tests/check_cpu.py                     the quick set (about 20 s)
python3 digital/tests/check_cpu.py --all               also primes.asm (about 1.5 min more)
python3 digital/tests/check_cpu.py programs/fibonacci.asm
```

`CpuTrace.java` runs `CPU.dig` with Digital's own simulator, without the GUI, with a program put into its EEPROM, and writes the state of every clock cycle: the micro-PC, the IR, the address bus, the data bus, the control word, A, X, Y and the flags. `check_cpu.py` runs the same program on the emulator and compares them cycle by cycle, and at the end it compares the RAM, `SPI_OUT`, the LEDs and the MAX7219 digits. When something is different, it says in which cycle and instruction, and what's different.

The quick set is `main.asm`, `programs/tests/all_instructions.asm` (every instruction at least once), `programs/tests/shifts.asm`, `fibonacci.asm`, `max7219_test.asm`, and `keyboard_test.asm` twice: with keys typed while it waits for one, and with keys typed while it sets up the display (that one found the keyboard bug below). Bugs in `CPU.dig` that aren't fixed yet are marked as known differences: they still run, and they only count as a failure if they stop being different.

## What They Found

Everything matches cycle by cycle, including all 1,697,481 cycles of `primes.asm`. At first there were two differences in `CPU.dig`, both fixed now:

- The result of `SHR` and `ROR` never reached the data bus. The wire from the ALU's `ALU` output to `STATUS_REG`'s `D IN` (from (940,300) to (1040,300)) crossed the data bus wire coming up from `A_R OUT` at (960,300) without a junction, so A loaded a floating bus. The `ALU` module itself was fine (its module test passed).
- The keyboard lost keys. When a fetch came right after a write to the MMIO (like every `ST XY` to `SPI_OUT`), `MEM_RD` turned on while the address bus still pointed to the MMIO, so the MMIO decoder could select the keyboard with a read going on, and every glitch on `KB_EN` took a key out of the buffer. The fix was gating `MEM_RD` and `MEM_WR` with the clock (`nMEM.dig`, see `design-decisions/memory-strobes.md`).

Because of that gating, `CpuTrace.java` samples the data bus in the second half of each cycle (`CLK` low), when the memory drives it, and everything else right after the rising edge. It also clears the RAM after the reset: while Digital settles the circuit at power-up, the clock starts low, so the strobes are let through, and a glitch on `MEM_WR` sometimes writes a random byte (not in every run). On the real CPU the RAM is random at power-on anyway, and the reset button can't cause it, because the EPROMs are off during the reset.

They also confirm the known bugs: `ROR` does the same as `SHR`, `POPF` always loads `Z C - V` (the flags of the ALU's clear operation), and the logic operations overwrite C and V.

## When Something Changes

- After changing the microcode: run `crom_programmer.py` and the Python tests. `test_microcode.py` says if the ROMs in `CTRLUNIT.dig` need reloading, and if `isa.md` doesn't match anymore.
- After changing a module: run its module test and `check_cpu.py`.
- After fixing a known bug: remove its `@unittest.expectedFailure` in `test_instructions.py`, or its note in `check_cpu.py` (they say so when it happens).
