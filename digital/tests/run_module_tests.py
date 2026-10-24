#!/usr/bin/env python3
# ==============================================================================
# Module tests: the test cases in digital/tests/*_tests.txt, run with Digital
# ==============================================================================
# Each MODULE_tests.txt holds test cases for digital/MODULE.dig, in Digital's own test
# syntax (the one of the Testcase component). "## name" starts a test case, and the
# signals are the module's pins with spaces and brackets turned into underscores
# (A IN -> A_IN, [15:11] -> I15_11).
#
# For every module, this copies digital/ into a temporary folder, makes a test circuit
# there (the module as a subcircuit, its pins wired to inputs and outputs, and the test
# cases: ModuleWrapper.java) and runs it with Digital's command line. The .dig files in
# digital/ are never changed.
#
#   python3 digital/tests/run_module_tests.py              all the modules
#   python3 digital/tests/run_module_tests.py ALU PC       some of them
#   python3 digital/tests/run_module_tests.py --keep DIR   also save the test circuits in DIR,
#                                                          to open them in Digital (F8 runs them)
#
# Needs Java and Digital.jar: set DIGITAL_JAR if it isn't in ~/Applications/Digital/.
# ==============================================================================

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DIGITAL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from check_cpu import find_digital_jar
import crom_programmer as cp      # (check_cpu puts programs/ in the path)

_eproms = None


def expand(text):
    """Fills in the microcode placeholders of the CTRLUNIT tests:
      {cw OPC STEP FLAGS}  the 3 EPROM words at that address (FLAGS = Z | C<<1 | N<<2 | V<<3)
      {reset}              the 3 words with every control bit inactive (what the pull resistors give)
    so the tests follow crom_programmer.py when the microcode changes."""
    global _eproms

    def words(value):
        return " ".join(f"0x{value >> shift & 0xFFFF:04X}" for shift in (0, 16, 32))

    def cw(m):
        global _eproms
        if _eproms is None:
            _eproms = cp.gen_microcode()
        opc, step, flags = (int(x, 0) for x in m.group(1).split())
        addr = opc | step << 8 | flags << 12
        return words(_eproms[0][addr] | _eproms[1][addr] << 16 | _eproms[2][addr] << 32)

    text = re.sub(r"\{cw ((?:0x[0-9A-Fa-f]+|\d+) \d+ \d+)\}", cw, text)
    return text.replace("{reset}", words(cp.active_low_mask))


def print_failure(lines):
    # Digital prints the whole table of a failed test case: show the result of every test case,
    # and only the header and the first wrong rows (they have "E: expected / F: found") of each table
    shown = 0
    for i, line in enumerate(lines):
        if line.endswith(("passed", "failed")) or line.endswith(")") and "failed (" in line:
            print(f"    {line}")
            shown = 0
            if i + 1 < len(lines) and "failed" in line:
                print(f"        {lines[i + 1]}")
        elif "E:" in line and shown < 8:
            print(f"        {line}")
            shown += 1
        elif not line.startswith(("Tests have failed",)) and " " not in line.strip():
            print(f"    {line}")


def main():
    p = argparse.ArgumentParser(description="Runs the module test cases in digital/tests with Digital.")
    p.add_argument("modules", nargs="*", help="module names, like ALU (default: all of them)")
    p.add_argument("--keep", metavar="DIR", help="save the test circuits (and copies of the modules) in DIR")
    args = p.parse_args()

    jar = find_digital_jar()
    tests = sorted(glob.glob(os.path.join(HERE, "*_tests.txt")))
    if args.modules:
        tests = [t for t in tests if os.path.basename(t)[:-len("_tests.txt")] in args.modules]
    failed = []
    with tempfile.TemporaryDirectory() as work:
        build = os.path.join(work, "build")
        circuits = os.path.join(work, "circuits")
        os.mkdir(build)
        os.mkdir(circuits)
        subprocess.run(["javac", "-nowarn", "-cp", jar, "-d", build, os.path.join(HERE, "ModuleWrapper.java")],
                       check=True, stderr=subprocess.DEVNULL)
        for path in glob.glob(os.path.join(DIGITAL, "*.dig")):
            shutil.copy(path, circuits)

        for test_file in tests:
            module = os.path.basename(test_file)[:-len("_tests.txt")]
            wrapper = f"{module}_test.dig"
            expanded = os.path.join(work, os.path.basename(test_file))
            with open(test_file) as f, open(expanded, "w") as out:
                out.write(expand(f.read()))
            subprocess.run(["java", "-cp", f"{jar}{os.pathsep}{build}", "ModuleWrapper", circuits,
                            f"{module}.dig", expanded, wrapper], check=True, stderr=subprocess.DEVNULL)
            result = subprocess.run(["java", "-cp", jar, "CLI", "test", "-circ", os.path.join(circuits, wrapper),
                                     "-verbose"], capture_output=True, text=True)
            lines = [l for l in (result.stdout + result.stderr).splitlines()
                     if l.strip() and not l.startswith("WARNING")]
            passed = [l for l in lines if l.endswith(": passed")]
            ok = result.returncode == 0 and passed and len(passed) == sum(1 for l in lines if l.endswith(("passed", "failed")))
            print(f"{module}: {len(passed)} test cases passed" if ok else f"{module}: FAILED")
            if not ok:
                failed.append(module)
                print_failure(lines)

        if args.keep:
            os.makedirs(args.keep, exist_ok=True)
            for path in glob.glob(os.path.join(circuits, "*.dig")):
                shutil.copy(path, args.keep)
            print(f"the test circuits are in {args.keep} (open one in Digital and press F8)")

    print("all the module tests passed" if not failed else f"failed: {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
