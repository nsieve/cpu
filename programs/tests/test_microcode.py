# Checks on the microcode itself, and that the files that copy it are in sync:
#   - eprom1-3.hex and the 3 ROMs inside CTRLUNIT.dig hold what crom_programmer.py makes
#   - every instruction ends (nMPC_RST or HALT) and no step drives a bus twice
#   - isa.md lists every instruction, with the right opcode, subOp and cycles
#
#   python3 -m unittest discover -s programs/tests -v

import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "programs"))
import crom_programmer as cp
import emulator as em

ISA_MD = os.path.join(ROOT, "notes", "opcodes&microinstructions", "isa.md")
CTRLUNIT_DIG = os.path.join(ROOT, "digital", "CTRLUNIT.dig")


def cycles(microcode, opcode, flags):
    """Cycles until the step with nMPC_RST (or the HALT step), None if it never ends."""
    for upc in range(16):
        cw = microcode[opcode | upc << 8 | flags << 12]
        if cw >> cp.nMPC_RST & 1 or cw >> cp.nHALT & 1:
            return upc + 1
    return None


def isa_table():
    """The instruction table of isa.md: (mnemonic, base opcode, subOp or None, cycles text)."""
    rows = []
    with open(ISA_MD) as f:
        lines = f.read().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("| Mnemonic"))
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.replace("\\|", "/").strip().strip("|").split("|")]
        mnemonic, opcode, subop, _, _, cyc = cells
        rows.append((mnemonic, int(opcode, 16), None if subop == "-" else int(subop, 16), cyc))
    return rows


def example(mnemonic):
    """A real instruction for a line of the table: 'MOV REG, REG' -> 'MOV B, C'."""
    regs = iter(["B", "C"])
    words = [next(regs) if w == "REG" else "0x12" if w == "Imm" else "0xC100" if w == "label" else w
             for w in mnemonic.replace(",", " , ").split()]
    return " ".join(words).replace(" , ", ", ")


def decode_dig_data(text, size):
    # Digital stores memory contents as comma separated hex values, "n*value" repeats one
    out = []
    for tok in text.replace("\n", "").split(","):
        tok = tok.strip()
        if not tok:
            continue
        if "*" in tok:
            count, value = tok.split("*")
            out += [int(value, 16)] * int(count)
        else:
            out.append(int(tok, 16))
    return out + [0] * (size - len(out))


class TestMicrocodeFiles(unittest.TestCase):
    def setUp(self):
        self.eproms = cp.gen_microcode()

    def test_eprom_hex_files(self):
        for i in range(3):
            path = os.path.join(ROOT, "programs", f"eprom{i + 1}.hex")
            words = em.read_digital_hex(path, 1 << 16)
            diff = [a for a in range(1 << 16) if words[a] != self.eproms[i][a]]
            self.assertEqual(diff[:5], [], f"eprom{i + 1}.hex is out of date, run crom_programmer.py again")

    def test_ctrlunit_dig_roms(self):
        # the ROMs in CTRLUNIT.dig keep their own copy of the data, so they have to be reloaded
        # in Digital after every change of the microcode
        roms = {}
        for ve in ET.parse(CTRLUNIT_DIG).getroot().find("visualElements"):
            if ve.find("elementName").text == "ROM":
                attrs = {e.find("string").text: list(e)[1] for e in ve.find("elementAttributes")}
                roms[attrs["Label"].text] = decode_dig_data(attrs["Data"].text, 1 << 16)
        for i, label in enumerate(["1ROM", "2ROM", "3ROM"]):
            diff = [a for a in range(1 << 16) if roms[label][a] != self.eproms[i][a]]
            self.assertEqual(diff[:5], [], f"ROM {label} in CTRLUNIT.dig doesn't match crom_programmer.py, "
                                           f"reload eprom{i + 1}.hex into it")


class TestMicrocode(unittest.TestCase):
    def setUp(self):
        self.microcode = em.load_microcode()

    def test_every_instruction_ends(self):
        for opcode in range(256):
            for flags in range(16):
                self.assertIsNotNone(cycles(self.microcode, opcode, flags),
                                     f"opcode 0x{opcode:02X} never resets the micro-PC (flags {flags:04b})")

    def test_no_bus_problems(self):
        for opcode in range(256):
            for flags in range(16):
                for upc in range(cycles(self.microcode, opcode, flags)):
                    _, _, problems = em.gen_step(self.microcode[opcode | upc << 8 | flags << 12])
                    self.assertEqual(problems, [], f"opcode 0x{opcode:02X}, step {upc}, flags {flags:04b}")


class TestIsaMd(unittest.TestCase):
    def setUp(self):
        self.microcode = em.load_microcode()
        self.table = isa_table()

    def test_every_slot_is_documented_or_free(self):
        documented = {}
        for mnemonic, base, sub, _ in self.table:
            for s in (range(8) if sub is None else [sub]):
                self.assertNotIn((base, s), documented, f"{mnemonic} and {documented.get((base, s))} share a slot")
                documented[(base, s)] = mnemonic
        for slot in cp.FREE_SLOTS:
            self.assertNotIn(slot, documented, f"free slot {slot} is in isa.md as {documented.get(slot)}")
        missing = {(b, s) for b in range(32) for s in range(8)} - set(documented) - cp.FREE_SLOTS
        self.assertEqual(sorted(missing), [], "opcode slots that aren't in isa.md and aren't free")

    def test_cycles(self):
        for mnemonic, base, sub, text in self.table:
            text = text.replace("*", "")
            for s in (range(8) if sub is None else [sub]):
                opcode = base << 3 | s
                if base == 0x1B:                # JCC label: taken / not taken
                    taken, not_taken = (int(x) for x in text.split("/"))
                    for flags in range(16):
                        z, c, n, v = (flags >> i & 1 for i in range(4))
                        expected = taken if cp.check_condition(s, z, c, n, v) else not_taken
                        self.assertEqual(cycles(self.microcode, opcode, flags), expected, f"{mnemonic} flags {flags:04b}")
                else:
                    for flags in range(16):
                        self.assertEqual(cycles(self.microcode, opcode, flags), int(text),
                                         f"{mnemonic} (opcode 0x{opcode:02X}) with flags {flags:04b}")

    def test_opcodes_match_the_assembler(self):
        for mnemonic, base, sub, _ in self.table:
            source = example(mnemonic)
            rom, _ = em.assemble_source(".ORG 0xC000\n" + source)
            self.assertEqual(rom[0] >> 11, base, f"{mnemonic}: '{source}' assembles to 0x{rom[0]:04X}")
            if sub is not None:
                self.assertEqual(rom[0] >> 8 & 7, sub, f"{mnemonic}: '{source}' assembles to 0x{rom[0]:04X}")

    def test_disassembler(self):
        for mnemonic, _, _, _ in self.table:
            source = example(mnemonic)
            rom, _ = em.assemble_source(".ORG 0xC000\n" + source)
            two = em.is_two_words(rom[0])
            text = em.disassemble(rom[0], rom[1] if two else None)
            norm = lambda s: re.sub(r"\s+", " ", s.upper())
            self.assertEqual(norm(text), norm(source), mnemonic)


if __name__ == "__main__":
    unittest.main()
