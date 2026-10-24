# The programs in programs/ run to the end on the emulator and give the right results.
# Each one runs twice: once like Digital starts (RAM and registers at 0), and once with
# random RAM and registers, like real hardware powers up, to catch programs that only
# work because the memory starts cleared.
#
#   python3 -m unittest discover -s programs/tests -v

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROGRAMS = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, PROGRAMS)
import emulator as em


def run_program(name, keys="", random_state=False, max_cycles=5_000_000):
    rom, symbols = em.load_program(os.path.join(PROGRAMS, name))
    cpu = em.CPU(rom, keys=keys, random_state=random_state)
    displays = []
    cpu.on_display = lambda c: displays.append(c.max7219.text())
    halted = cpu.run(max_cycles)
    cpu.labels = {addr: label for label, addr in symbols.items() if not label.startswith(".")}
    cpu.displays = displays
    cpu.halted_at = cpu.labels.get(cpu.inst_pc) if halted else None
    return cpu


class TestPrograms(unittest.TestCase):
    def check(self, name, **kwargs):
        """Runs the program from a cleared and from a random power-up. Returns both CPUs."""
        cpus = []
        for random_state in (False, True):
            cpu = run_program(name, random_state=random_state, **kwargs)
            if not random_state:
                self.assertEqual(cpu.warnings, {}, f"{name}: warnings")
            cpus.append(cpu)
        return cpus

    def test_main(self):
        for cpu in self.check("main.asm"):
            self.assertEqual(cpu.halted_at, "PASS", f"main.asm failed check {cpu.r[6]} (X)")

    def test_fibonacci(self):
        for cpu in self.check("fibonacci.asm"):
            self.assertEqual(cpu.halted_at, "END")
            self.assertEqual(cpu.max7219.text(), "63245986")          # the last one that fits in 8 digits
            for number in ("00000001", "00000144", "00010946", "39088169"):
                self.assertIn(number, cpu.displays)

    def test_primes(self):
        for cpu in self.check("primes.asm"):
            self.assertEqual(cpu.halted_at, "DONE")
            self.assertEqual(cpu.max7219.text(), "00004999")          # the last prime below 5000
            self.assertEqual(cpu.leds, 669 & 0xFF)                    # 669 primes below 5000

    def test_primes_shown(self):
        cpu = run_program("primes.asm")
        shown = sorted({int(d) for d in cpu.displays})
        sieve = [n for n in range(2, 5001) if all(n % p for p in range(2, int(n ** 0.5) + 1))]
        # every prime is shown; the digit-by-digit updates also show a few in-between numbers,
        # so only check that the primes are all there
        self.assertTrue(set(sieve) <= set(shown), set(sieve) - set(shown))

    def test_max7219_test(self):
        for cpu in self.check("max7219_test.asm"):
            self.assertEqual(cpu.halted_at, "DONE")
            self.assertEqual(cpu.max7219.text(), "00054321")
            self.assertEqual(cpu.leds, 0x07)
            self.assertIn("00012345", cpu.displays)

    def test_keyboard_test(self):
        for random_state in (False, True):
            cpu = em.CPU(em.load_program(os.path.join(PROGRAMS, "keyboard_test.asm"))[0],
                         keys="Ab1", random_state=random_state)
            displays = []
            cpu.on_display = lambda c: displays.append(c.max7219.text())
            cpu.run(100_000)                                           # it never halts, it waits for keys
            self.assertEqual(list(cpu.kb), [], "all the keys were read")
            self.assertEqual(cpu.leds, ord("1"))
            for code in (ord("A"), ord("b"), ord("1")):
                self.assertIn(f"{code:08d}", displays)


if __name__ == "__main__":
    unittest.main()
