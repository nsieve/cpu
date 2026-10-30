#!/usr/bin/env python3
# ==============================================================================
# CPU.dig vs the emulator, cycle by cycle
# ==============================================================================
# Runs programs on CPU.dig (with Digital's own simulator, through CpuTrace.java) and on
# programs/emulator.py, and compares every clock cycle: micro-PC, IR, address bus, data
# bus, control word, A, X, Y and flags. At the end it compares the RAM, SPI_OUT, the LEDs
# and the MAX7219 digits. The emulator is checked against isa.md by programs/tests, so
# if both match, the circuit does what isa.md says.
#
#   python3 digital/tests/check_cpu.py                 the quick set (about 10 s)
#   python3 digital/tests/check_cpu.py --all           also primes.asm (about 1.5 min more)
#   python3 digital/tests/check_cpu.py programs/fibonacci.asm
#
# Needs Java and Digital.jar: set DIGITAL_JAR if it isn't in ~/Applications/Digital/.
# ==============================================================================

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "programs"))
import crom_programmer as cp
import emulator as em

CPU_DIG = os.path.join(ROOT, "digital", "CPU.dig")

# (program, keys, cycles between keys, known difference). A known difference is a bug in
# CPU.dig that isn't fixed yet (planning/issues.md): it's still run, but it only counts as
# a failure if it stops being different, so the note can be removed.
QUICK = [("programs/main.asm", "", 0, None),
         ("programs/tests/all_instructions.asm", "", 0, None),
         ("programs/tests/shifts.asm", "", 0, None),
         ("programs/fibonacci.asm", "", 0, None),
         ("programs/max7219_test.asm", "", 0, None),
         ("programs/keyboard_test.asm", "Ab1", 10_000, None),       # typed while it waits for a key
         ("programs/keyboard_test.asm", "AB", 1_000, None)]         # typed while it sets up the display
SLOW = [("programs/primes.asm", "", 0, None)]
NO_HALT_CYCLES = 40_000          # for programs that never halt (the keyboard test)
MAX_CYCLES = 5_000_000
FIELDS = ["cycle", "micro-PC", "IR", "address bus", "data bus", "control word", "A", "X", "Y", "flags"]
BIT_NAMES = {v: k for k, v in vars(cp).items() if isinstance(v, int) and 0 <= v < 48}


def find_digital_jar():
    candidates = [os.environ.get("DIGITAL_JAR", ""),
                  os.path.expanduser("~/Applications/Digital/Digital.jar"),
                  os.path.expanduser("~/Digital/Digital.jar"),
                  "/opt/Digital/Digital.jar"]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    sys.exit("Digital.jar not found: set DIGITAL_JAR to its path")


def compile_harness(jar, build_dir):
    subprocess.run(["javac", "-nowarn", "-cp", jar, "-d", build_dir, os.path.join(HERE, "CpuTrace.java")],
                   check=True, stderr=subprocess.DEVNULL)


def run_digital(jar, build_dir, rom, max_cycles, keys, interval, work):
    hex_path = os.path.join(work, "program.hex")
    with open(hex_path, "w") as f:
        f.write("v2.0 raw\n" + "\n".join(f"{w:X}" for w in rom) + "\n")
    out_path = os.path.join(work, "digital.txt")
    cmd = ["java", "-cp", f"{jar}{os.pathsep}{build_dir}", "CpuTrace", CPU_DIG, hex_path, str(max_cycles), out_path]
    if keys:
        cmd += [keys, str(interval)]
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL, cwd=os.path.dirname(CPU_DIG))
    trace, final = [], {"ram": {}}
    with open(out_path) as f:
        for line in f:
            parts = line.split()
            if not parts or parts[0].startswith("#"):
                continue
            if parts[0] == "ram":
                final["ram"][int(parts[1], 16)] = int(parts[2], 16)
            elif parts[0] in ("spi", "leds", "keys"):
                final[parts[0]] = int(parts[1], 16)
            elif parts[0] == "display":
                final["display"] = parts[1]
            else:
                trace.append(parts)
    return trace, final


def run_emulator(rom, keys, interval, first, max_cycles):
    cpu = em.CPU(rom, keys="" if interval else keys, strict=False)
    # X, Y and the flags have no reset: start with what Digital had after its reset
    cpu.r[6], cpu.r[7], cpu.flags = int(first[7], 16), int(first[8], 16), int(first[9], 16)
    trace, places = [], []
    def write(line):
        trace.append(line.split())
        places.append(cpu.inst_pc)
    while not cpu.halted and cpu.cycles < max_cycles:
        n = cpu.cycles
        if interval and n and n % interval == 0 and n // interval <= len(keys):
            cpu.kb.append(ord(keys[n // interval - 1]) & 0xFF)
        nxt = min(max_cycles, (n // interval + 1) * interval) if interval else max_cycles
        cpu.run_traced(nxt, write)
    return cpu, trace, places


def describe_difference(emu, dig):
    out = []
    for i, name in enumerate(FIELDS):
        if emu[i] != dig[i]:
            if name == "control word":
                diff = int(emu[i], 16) ^ int(dig[i], 16)
                bits = [BIT_NAMES.get(b, str(b)) for b in range(48) if diff >> b & 1]
                out.append(f"control bits {', '.join(bits)}")
            else:
                out.append(f"{name} emulator {emu[i]} / Digital {dig[i]}")
    return "; ".join(out)


def check(program, keys, interval, jar, build_dir, max_cycles):
    rom, symbols = em.load_program(os.path.join(ROOT, program))
    labels = {addr: name for name, addr in symbols.items() if not name.startswith(".")}
    with tempfile.TemporaryDirectory() as work:
        dig_trace, dig_final = run_digital(jar, build_dir, rom, max_cycles, keys, interval, work)
    cpu, emu_trace, places = run_emulator(rom, keys, interval, dig_trace[0], max_cycles)

    problems = []
    if len(emu_trace) != len(dig_trace):
        problems.append(f"the emulator ran {len(emu_trace):,} cycles and Digital {len(dig_trace):,}")
    shown = 0
    for n, (emu, dig) in enumerate(zip(emu_trace, dig_trace)):
        if n == 0:
            emu, dig = emu[:2] + emu[3:], dig[:2] + dig[3:]     # the IR still has whatever it had before the reset
            emu.insert(2, "-"), dig.insert(2, "-")
        if emu != dig:
            if shown < 12:
                pc = places[n]
                label = labels.get(pc, "")
                problems.append(f"cycle {n:,} (step {emu[1]} of {cpu.instruction_at(pc)} at 0x{pc:04X}"
                                f"{' ' + label if label else ''}): {describe_difference(emu, dig)}")
            shown += 1
            if emu[3] != dig[3] and emu[3] != "----" and dig[3] != "----" and emu[1] == "0":
                problems.append("the program went a different way here, so the rest isn't compared")
                break
    if shown > 12:
        problems.append(f"... {shown - 12:,} more cycles are different")

    emu_ram = {a: v for a, v in enumerate(cpu.ram[:em.MMIO_START]) if v}
    if emu_ram != dig_final["ram"]:
        diff = sorted(set(emu_ram) | set(dig_final["ram"]))
        diff = [a for a in diff if emu_ram.get(a, 0) != dig_final["ram"].get(a, 0)]
        problems.append("RAM is different at " + ", ".join(
            f"0x{a:04X} (emulator {emu_ram.get(a, 0):02X}, Digital {dig_final['ram'].get(a, 0):02X})" for a in diff[:6])
            + (f" and {len(diff) - 6} more" if len(diff) > 6 else ""))
    for name, emu_value in (("spi", cpu.spi), ("leds", cpu.leds), ("keys", len(cpu.kb))):
        if emu_value != dig_final[name]:
            problems.append(f"{name}: emulator {emu_value:02X}, Digital {dig_final[name]:02X}")
    if cpu.max7219.text() != dig_final["display"]:
        problems.append(f"display: emulator {cpu.max7219.text()}, Digital {dig_final['display']}")
    return len(dig_trace), problems


def main():
    p = argparse.ArgumentParser(description="Compares CPU.dig with the emulator, cycle by cycle.")
    p.add_argument("programs", nargs="*", help=".asm or .hex files (default: the quick set)")
    p.add_argument("--all", action="store_true", help="also run the slow programs (primes.asm)")
    p.add_argument("--keys", default="", help="keys for the programs given on the command line")
    p.add_argument("--key-interval", type=int, default=0, metavar="CYCLES",
                   help="type the keys one every CYCLES cycles instead of all at the start")
    args = p.parse_args()

    if shutil.which("java") is None or shutil.which("javac") is None:
        sys.exit("needs java and javac")
    jar = find_digital_jar()
    runs = [(os.path.relpath(os.path.abspath(path), ROOT), args.keys, args.key_interval, None)
            for path in args.programs]
    if not runs:
        runs = QUICK + (SLOW if args.all else [])

    failed = known = 0
    with tempfile.TemporaryDirectory() as build_dir:
        compile_harness(jar, build_dir)
        for program, keys, interval, known_difference in runs:
            max_cycles = NO_HALT_CYCLES if "keyboard" in program else MAX_CYCLES
            typing = f" (keys {keys!r}" + (f", one every {interval:,} cycles)" if interval else ")") if keys else ""
            print(f"{program}{typing} ...", end=" ", flush=True)
            cycles, problems = check(program, keys, interval, jar, build_dir, max_cycles)
            if problems and known_difference:
                known += 1
                print(f"different, as expected ({cycles:,} cycles in Digital)\n    known: {known_difference}")
                for problem in problems[:4]:
                    print(f"    {problem}")
            elif problems:
                failed += 1
                print(f"DIFFERENT ({cycles:,} cycles in Digital)")
                for problem in problems:
                    print(f"    {problem}")
            elif known_difference:
                failed += 1
                print(f"SAME, but it was expected to be different: if this got fixed, remove the note in check_cpu.py"
                      f"\n    ({known_difference})")
            else:
                print(f"same, {cycles:,} cycles")
    summary = f"{len(runs) - failed - known} same, {known} known differences, {failed} failed"
    print(summary)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
