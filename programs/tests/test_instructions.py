# Every instruction on the emulator, checked against what isa.md says it does.
#
# Each test assembles a few instructions followed by HALT, sets up the registers and
# memory directly, runs it, and compares the result (and the cycles) with a model of
# the ISA written here from isa.md, not from the microcode. Known bugs from
# planning/issues.md are marked as expected failures: when one gets fixed, its test
# shows up as an "unexpected success", and the marker can go.
#
#   python3 -m unittest discover -s programs/tests -v

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import emulator as em

REGS = "ABCDEFXY"
Z, C, N, V = 1, 2, 4, 8
HALT_CYCLES = 3
EDGES = [0x00, 0x01, 0x7F, 0x80, 0x81, 0xFE, 0xFF]


def run(source, regs=None, flags=0, ram=None, mar=0, sp=0, max_cycles=2000):
    """Assembles source at 0xC000 with a HALT at the end, sets up the CPU and runs it."""
    rom, symbols = em.assemble_source(".ORG 0xC000\n" + source + "\n    HALT\n")
    return run_rom(rom, regs, flags, ram, mar, sp, max_cycles, symbols)


def run_rom(rom, regs=None, flags=0, ram=None, mar=0, sp=0, max_cycles=2000, symbols=None):
    cpu = em.CPU(rom)
    for name, value in (regs or {}).items():
        cpu.r[REGS.index(name)] = value
    cpu.flags, cpu.mar, cpu.sp = flags, mar, sp
    for addr, value in (ram or {}).items():
        cpu.ram[addr] = value
        cpu.written[addr] = 1
    if not cpu.run(max_cycles):
        raise AssertionError("the CPU didn't halt")
    cpu.symbols = symbols or {}
    return cpu


def flag_bits(res, c=0, v=0):
    return (res == 0) * Z | c * C | (res >> 7) * N | v * V


def signed(x):
    return x - 256 if x & 0x80 else x


def ref_arith(op, a, b, carry):
    """isa.md for the arithmetic instructions: returns (result, flags).
    C is the carry for additions, and 'no borrow' for subtractions."""
    if op == "ADD":   u, s = a + b, signed(a) + signed(b)
    elif op == "ADC": u, s = a + b + carry, signed(a) + signed(b) + carry
    elif op == "INC": u, s = a + 1, signed(a) + 1
    elif op in ("SUB", "CP"): u, s = a - b, signed(a) - signed(b)
    elif op == "SBC": u, s = a - b - 1 + carry, signed(a) - signed(b) - 1 + carry
    elif op == "DEC": u, s = a - 1, signed(a) - 1
    else: raise ValueError(op)
    res = u & 0xFF
    c = int(u > 0xFF) if op in ("ADD", "ADC", "INC") else int(u >= 0)
    return res, flag_bits(res, c, int(not -128 <= s <= 127))


def operand_cases(count=150, seed=1):
    rnd = random.Random(seed)
    cases = [(a, b, c) for a in EDGES for b in EDGES for c in (0, 1)]
    cases += [(rnd.randrange(256), rnd.randrange(256), rnd.randrange(2)) for _ in range(count)]
    return cases


ALU_OPS = ["ADD", "ADC", "SUB", "SBC", "AND", "OR", "XOR", "CP"]     # in subop order

def ref_alu(op, a, b, flags):
    """isa.md for the 8 ALU operations: returns (A, flags) after 'op A, b' with these flags before."""
    if op in ("AND", "OR", "XOR"):                  # only Z and N load, C and V keep their value
        res = {"AND": a & b, "OR": a | b, "XOR": a ^ b}[op]
        return res, flags & (C | V) | flag_bits(res) & (Z | N)
    res, new_flags = ref_arith(op, a, b, flags >> 1 & 1)
    return (a if op == "CP" else res), new_flags



def flags_byte(flags):
    """Z C N V (bits 0-3, like cpu.flags) -> the byte PUSHF writes: 0000VCNZ."""
    return flags & 9 | (flags & 2) << 1 | (flags & 4) >> 1

class TestMoves(unittest.TestCase):
    def test_mov_reg_imm(self):
        for i, r in enumerate(REGS):
            cpu = run(f"MOV {r}, 0x{0x30 + i:02X}")
            self.assertEqual(cpu.r[i], 0x30 + i)
            self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def test_mov_reg_reg(self):
        values = {r: 0x11 * (i + 1) for i, r in enumerate(REGS)}
        for d in REGS:
            for s in REGS:
                cpu = run(f"MOV {d}, {s}", regs=values)
                expected = dict(values, **{d: values[s]})
                self.assertEqual(cpu.r, [expected[r] for r in REGS], f"MOV {d}, {s}")
                self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def test_mar_loads(self):
        self.assertEqual(run("MOV MARL, 0x34\nMOV MARH, 0x12", mar=0xFFFF).mar, 0x1234)
        for i, r in enumerate(REGS):
            cpu = run(f"MOV MARL, {r}\nMOV MARH, {r}", regs={r: 0x40 + i})
            self.assertEqual(cpu.mar, (0x40 + i) * 0x101, r)

    def test_inc_dec_mar(self):
        for start, inst, end in ((0x00FF, "INC", 0x0100), (0xFFFF, "INC", 0x0000),
                                 (0x0100, "DEC", 0x00FF), (0x0000, "DEC", 0xFFFF)):
            cpu = run(f"{inst} MAR", mar=start)
            self.assertEqual(cpu.mar, end, f"{inst} MAR from 0x{start:04X}")
            self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def test_inc_dec_xy(self):
        for start, inst, end in ((0x00FF, "INC", 0x0100), (0xFFFF, "INC", 0x0000), (0x12FF, "INC", 0x1300),
                                 (0x0100, "DEC", 0x00FF), (0x0000, "DEC", 0xFFFF), (0x1300, "DEC", 0x12FF)):
            cpu = run(f"{inst} XY", regs={"X": start >> 8, "Y": start & 0xFF})
            self.assertEqual(cpu.r[6] << 8 | cpu.r[7], end, f"{inst} XY from 0x{start:04X}")
            self.assertEqual(cpu.cycles - HALT_CYCLES, 2)


class TestLoadsAndStores(unittest.TestCase):
    def test_ld_zero_page(self):
        for i, r in enumerate(REGS):
            cpu = run(f"LD {r}, 0x{0x20 + 7 * i:02X}", ram={0x20 + 7 * i: 0xA0 + i})
            self.assertEqual(cpu.r[i], 0xA0 + i, r)
            self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def test_st_zero_page(self):
        # bits [7:5] of the address never match the register, like in main.asm
        values = {r: 0x11 * (i + 1) for i, r in enumerate(REGS)}
        for i, r in enumerate(REGS):
            addr = 0xE0 - 0x20 * i if i else 0x25
            cpu = run(f"ST 0x{addr:02X}, {r}", regs=values)
            self.assertEqual(cpu.ram[addr], values[r], f"ST 0x{addr:02X}, {r}")
            self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def test_ld_st_mar(self):
        for i, r in enumerate(REGS):
            cpu = run(f"LD {r}, MAR", mar=0x1234, ram={0x1234: 0x50 + i})
            self.assertEqual(cpu.r[i], 0x50 + i)
            cpu = run(f"ST MAR, {r}", mar=0x2345, regs={r: 0x60 + i})
            self.assertEqual(cpu.ram[0x2345], 0x60 + i)

    def test_ld_st_xy(self):
        for i, r in enumerate(REGS):
            regs = {"X": 0x34, "Y": 0x56}
            cpu = run(f"LD {r}, XY", regs=regs, ram={0x3456: 0x70 + i})
            self.assertEqual(cpu.r[i], 0x70 + i)
            regs[r] = regs.get(r, 0x80 + i)
            cpu = run(f"ST XY, {r}", regs=regs)
            self.assertEqual(cpu.ram[0x3456], regs[r])

    def test_push_pop(self):
        for i, r in enumerate(REGS):
            cpu = run(f"PUSH {r}", regs={r: 0x90 + i}, sp=0xBAFF)
            self.assertEqual((cpu.ram[0xBAFF], cpu.sp), (0x90 + i, 0xBAFE))
            self.assertEqual(cpu.cycles - HALT_CYCLES, 2)
            cpu = run(f"POP {r}", sp=0xBAFE, ram={0xBAFF: 0xA0 + i})
            self.assertEqual((cpu.r[i], cpu.sp), (0xA0 + i, 0xBAFF))
            self.assertEqual(cpu.cycles - HALT_CYCLES, 3)

    def test_push_pop_order(self):
        cpu = run("PUSH A\nPUSH B\nPOP C\nPOP D", regs={"A": 1, "B": 2}, sp=0xBAFF)
        self.assertEqual((cpu.r[2], cpu.r[3], cpu.sp), (2, 1, 0xBAFF))

    def test_push_pop_xy(self):
        # pseudo-instructions: PUSH XY is PUSH X + PUSH Y, and POP XY is POP Y + POP X
        cpu = run("PUSH XY\nMOV X, 0\nMOV Y, 0\nPOP XY", regs={"X": 0x12, "Y": 0x34}, sp=0xBAFF)
        self.assertEqual((cpu.r[6], cpu.r[7], cpu.sp), (0x12, 0x34, 0xBAFF))
        self.assertEqual((cpu.ram[0xBAFF], cpu.ram[0xBAFE]), (0x12, 0x34))
        self.assertEqual(cpu.cycles - HALT_CYCLES, 2 + 2 + 2 + 2 + 3 + 3)

    def test_ld_st_xy_plus(self):
        # the access uses XY, and XY + 1 happens on the same clock edge (also from Y into X)
        for start in (0x3456, 0x12FF, 0x00FF):
            regs = {"X": start >> 8, "Y": start & 0xFF}
            for i, r in enumerate("ABCDEF"):
                cpu = run(f"LD {r}, XY+", regs=regs, ram={start: 0x70 + i})
                self.assertEqual(cpu.r[i], 0x70 + i, f"LD {r}, XY+ from 0x{start:04X}")
                self.assertEqual(cpu.r[6] << 8 | cpu.r[7], start + 1, f"LD {r}, XY+ from 0x{start:04X}")
                self.assertEqual(cpu.cycles - HALT_CYCLES, 2)
            for i, r in enumerate(REGS):
                values = dict(regs)
                values.setdefault(r, 0x80 + i)              # ST XY+, X stores the old X
                cpu = run(f"ST XY+, {r}", regs=values)
                self.assertEqual(cpu.ram[start], values[r], f"ST XY+, {r} at 0x{start:04X}")
                self.assertEqual(cpu.r[6] << 8 | cpu.r[7], start + 1, f"ST XY+, {r} at 0x{start:04X}")
                self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def test_ld_x_or_y_xy_plus(self):
        # X and Y can't load while XY counts: the assembler rejects it, and the emulator reports it
        for r in ("X", "Y"):
            with self.assertRaises(em.assembler.AssemblerError):
                em.assemble_source(f".ORG 0xC000\nLD {r}, XY+")
            with self.assertRaises(em.EmulatorError):
                run(f".RAW 0x{0x10 << 11 | REGS.index(r) << 8:04X}", regs={"X": 0x12, "Y": 0x34})

    def test_ld_st_mar_plus(self):
        for start in (0x3456, 0x12FF, 0x00FF):
            for i, r in enumerate(REGS):
                cpu = run(f"LD {r}, MAR+", mar=start, ram={start: 0x50 + i})
                self.assertEqual((cpu.r[i], cpu.mar), (0x50 + i, start + 1), f"LD {r}, MAR+ from 0x{start:04X}")
                self.assertEqual(cpu.cycles - HALT_CYCLES, 2)
                cpu = run(f"ST MAR+, {r}", mar=start, regs={r: 0x60 + i})
                self.assertEqual((cpu.ram[start], cpu.mar), (0x60 + i, start + 1), f"ST MAR+, {r} at 0x{start:04X}")
                self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def test_copy(self):
        # what the auto-increments are for: copying memory takes 4 cycles per byte
        source = """
            MOV X, 0x20
            MOV Y, 0x00
            MOV MARH, 0x30
            MOV MARL, 0x00
            LD B, XY+
            ST MAR+, B
            LD B, XY+
            ST MAR+, B
            LD B, XY+
            ST MAR+, B
        """
        data = {0x2000: 0x11, 0x2001: 0x22, 0x2002: 0x33}
        cpu = run(source, ram=data)
        self.assertEqual(bytes(cpu.ram[0x3000:0x3003]), bytes([0x11, 0x22, 0x33]))
        self.assertEqual((cpu.r[6] << 8 | cpu.r[7], cpu.mar), (0x2003, 0x3003))
        self.assertEqual(cpu.cycles - HALT_CYCLES, 4 * 2 + 3 * 4)


class TestAlu(unittest.TestCase):
    def check_reg_op(self, op, writes_a=True):
        rom, _ = em.assemble_source(f".ORG 0xC000\n{op} A, B\nHALT")
        for a, b, carry in operand_cases():
            cpu = run_rom(rom, regs={"A": a, "B": b}, flags=C if carry else 0)
            res, flags = ref_arith(op, a, b, carry)
            self.assertEqual(cpu.r[0], res if writes_a else a, f"{op} A, B with A={a:02X} B={b:02X} C={carry}")
            self.assertEqual(em.flags_str(cpu.flags), em.flags_str(flags),
                             f"{op} A, B with A={a:02X} B={b:02X} C={carry}")
            self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def check_imm_op(self, op, writes_a=True):
        rom, _ = em.assemble_source(f".ORG 0xC000\n{op} A, 0\nHALT")
        for a, b, carry in operand_cases():
            rom[0] = rom[0] & 0xFF00 | b
            cpu = run_rom(rom, regs={"A": a}, flags=C if carry else 0)
            res, flags = ref_arith(op, a, b, carry)
            self.assertEqual(cpu.r[0], res if writes_a else a, f"{op} A, 0x{b:02X} with A={a:02X}")
            self.assertEqual(em.flags_str(cpu.flags), em.flags_str(flags), f"{op} A, 0x{b:02X} with A={a:02X}")

    def test_add(self): self.check_reg_op("ADD")
    def test_add_imm(self): self.check_imm_op("ADD")
    def test_adc(self): self.check_reg_op("ADC")
    def test_adc_imm(self): self.check_imm_op("ADC")
    def test_sub(self): self.check_reg_op("SUB")
    def test_sub_imm(self): self.check_imm_op("SUB")
    def test_sbc(self): self.check_reg_op("SBC")
    def test_sbc_imm(self): self.check_imm_op("SBC")
    def test_cp(self): self.check_reg_op("CP", writes_a=False)
    def test_cp_imm(self): self.check_imm_op("CP", writes_a=False)

    def test_alu_memory_operands(self):
        # ALU A, [zp] (0x0E) and ALU A, [XY] (0x0F): the same 8 operations, with the operand from RAM
        for op in ALU_OPS:
            for operand, addr in (("[0x40]", 0x0040), ("[0xFF]", 0x00FF), ("[XY]", 0x1234)):
                rom, _ = em.assemble_source(f".ORG 0xC000\n{op} A, {operand}\nHALT")
                for a, b, carry in operand_cases(40):
                    before = carry * C | (a & 1) * V
                    cpu = run_rom(rom, regs={"A": a, "X": 0x12, "Y": 0x34}, flags=before, ram={addr: b})
                    res, flags = ref_alu(op, a, b, before)
                    self.assertEqual((cpu.r[0], em.flags_str(cpu.flags)), (res, em.flags_str(flags)),
                                     f"{op} A, {operand} with A={a:02X} mem={b:02X} C={carry}")
                    self.assertEqual((cpu.r[6], cpu.r[7]), (0x12, 0x34), f"{op} A, {operand} changed XY")
                    self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def test_alu_opcodes(self):
        # ALU A, REG is 0x0C, A, Imm 0x0D, A, [zp] 0x0E and A, [XY] 0x0F, and the subop is the operation
        for subop, op in enumerate(ALU_OPS):
            rom, _ = em.assemble_source(f".ORG 0xC000\n.EQU VAR 0x21\n{op} A, C\n{op} A, 0x5A\n{op} A, [0x5A]\n"
                                        f"{op} A, [ VAR ]\n{op} A, [XY]\n{op} A, XY")
            self.assertEqual(rom[0], 0x0C << 11 | subop << 8 | 2 << 5, f"{op} A, C")
            self.assertEqual(rom[1], 0x0D << 11 | subop << 8 | 0x5A, f"{op} A, 0x5A")
            self.assertEqual(rom[2], 0x0E << 11 | subop << 8 | 0x5A, f"{op} A, [0x5A]")
            self.assertEqual(rom[3], 0x0E << 11 | subop << 8 | 0x21, f"{op} A, [ VAR ]")
            self.assertEqual(rom[4:6], [0x0F << 11 | subop << 8] * 2, f"{op} A, [XY] and {op} A, XY")

    def test_alu_keeps_the_other_registers(self):
        # A loads with nA_LD, not through the decoder, so the subop in [10:8] doesn't load B-Y
        values = {r: 0x21 * (i + 1) & 0xFF for i, r in enumerate(REGS)}
        values.update(X=0x12, Y=0x34)                   # [XY] has to point to the RAM
        for op in ALU_OPS:
            for src in ("B", "0x0F", "[0x40]", "[XY]"):
                cpu = run(f"{op} A, {src}", regs=values)
                self.assertEqual(cpu.r[1:], [values[r] for r in REGS[1:]], f"{op} A, {src}")

    def test_alu_with_every_register(self):
        values = {r: 0x10 + i for i, r in enumerate(REGS)}
        for i, r in enumerate(REGS):
            cpu = run(f"ADD A, {r}", regs=values)
            self.assertEqual(cpu.r[0], (0x10 + 0x10 + i) & 0xFF, f"ADD A, {r}")

    def test_inc_dec(self):
        for op in ("INC", "DEC"):
            for a in range(256):
                for carry in (0, 1):
                    cpu = run(f"{op} A", regs={"A": a}, flags=C if carry else 0)
                    res, flags = ref_arith(op, a, 0, carry)
                    self.assertEqual((cpu.r[0], em.flags_str(cpu.flags)), (res, em.flags_str(flags)),
                                     f"{op} A with A={a:02X}")

    def check_logic(self, op, fn, imm=False):
        source = f"{op} A, 0" if imm else f"{op} A, B"
        rom, _ = em.assemble_source(f".ORG 0xC000\n{source}\nHALT")
        for a, b, carry in operand_cases():
            if imm:
                rom[0] = rom[0] & 0xFF00 | b
            cpu = run_rom(rom, regs={"A": a, "B": b}, flags=C if carry else 0)
            res = fn(a, b)
            self.assertEqual(cpu.r[0], res, f"{op} with A={a:02X} B={b:02X}")
            self.assertEqual(cpu.flags & (Z | N), flag_bits(res) & (Z | N), f"{op} with A={a:02X} B={b:02X}")
            self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def test_and(self): self.check_logic("AND", lambda a, b: a & b)
    def test_and_imm(self): self.check_logic("AND", lambda a, b: a & b, imm=True)
    def test_or(self): self.check_logic("OR", lambda a, b: a | b)
    def test_or_imm(self): self.check_logic("OR", lambda a, b: a | b, imm=True)
    def test_xor(self): self.check_logic("XOR", lambda a, b: a ^ b)
    def test_xor_imm(self): self.check_logic("XOR", lambda a, b: a ^ b, imm=True)

    def test_logic_ops_keep_c_and_v(self):
        # the logic operations only load Z and N (nFLZN_LD), so C and V keep their value
        for op in ("AND", "OR", "XOR"):
            for a, b, _ in operand_cases(50):
                for cv in (0, C | V):
                    cpu = run(f"{op} A, B", regs={"A": a, "B": b}, flags=cv)
                    self.assertEqual(cpu.flags & (C | V), cv, f"{op} with A={a:02X} B={b:02X}")
                    cpu = run(f"{op} A, {b}", regs={"A": a}, flags=cv)
                    self.assertEqual(cpu.flags & (C | V), cv, f"{op} with A={a:02X} Imm={b:02X}")

    def test_shr(self):
        # A = {0, A[7:1]}, C = the bit shifted out (A[0]) and V = 0. Z and N don't change
        for a in range(256):
            for flags in (0, Z | C | N | V):
                cpu = run("SHR A", regs={"A": a}, flags=flags)
                self.assertEqual(cpu.r[0], a >> 1)
                self.assertEqual(em.flags_str(cpu.flags), em.flags_str(flags & (Z | N) | (a & 1) * C),
                                 f"SHR A with A={a:02X} and flags {em.flags_str(flags)}")
                self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def test_ror(self):
        # A = {C, A[7:1]} and C = A[0], a rotate through the carry (the microcode sets SHR_IN0,
        # bit 7, only when C = 1). V = 0, Z and N don't change
        for a in range(256):
            for flags in (0, C, Z | N | V, Z | C | N | V):
                carry = flags >> 1 & 1
                cpu = run("ROR A", regs={"A": a}, flags=flags)
                what = f"ROR A with A={a:02X} and flags {em.flags_str(flags)}"
                self.assertEqual(cpu.r[0], carry << 7 | a >> 1, what)
                self.assertEqual(em.flags_str(cpu.flags), em.flags_str(flags & (Z | N) | (a & 1) * C), what)
                self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    def test_16_bit_shift_right(self):
        # SHR on the high byte, then ROR on the low byte: the bit in between goes through C
        for value in (0x0001, 0x0100, 0x8001, 0xFFFF, 0x1234, 0xA5A5, 0x0000):
            cpu = run("MOV A, X\nSHR A\nMOV X, A\nMOV A, Y\nROR A\nMOV Y, A",
                      regs={"X": value >> 8, "Y": value & 0xFF})
            self.assertEqual(cpu.r[6] << 8 | cpu.r[7], value >> 1, f"0x{value:04X} >> 1")
            self.assertEqual(cpu.flags >> 1 & 1, value & 1, f"C after 0x{value:04X} >> 1")

    def test_ldt(self):
        # LDT A, XY: A = the low byte of the ROM word at XY, in 3 cycles. Only the IR's low byte
        # loads, so the high byte of the table word doesn't matter (.TABLE puts LDT's opcode there)
        source = """
            MOV X, HIGH:TABLE
            MOV Y, LOW:TABLE
            {moves}
            LDT A, XY
            HALT
        TABLE:
            .TABLE 0x00, 0x41, 0xFF, 7
            .RAW 0x3C99
        """
        for index, expected in enumerate([0x00, 0x41, 0xFF, 0x07, 0x99]):
            moves = "\n".join(["INC XY"] * index)
            rom, symbols = em.assemble_source(".ORG 0xC000\n" + source.format(moves=moves))
            cpu = run_rom(rom, regs={"A": 0x5A}, flags=Z | C | N | V, symbols=symbols)
            self.assertEqual(cpu.r[0], expected, f"LDT of table entry {index}")
            self.assertEqual(cpu.flags, Z | C | N | V, "LDT shouldn't change the flags")
            self.assertEqual(cpu.cycles, 2 + 2 + 2 * index + 3 + HALT_CYCLES, f"LDT of table entry {index}")
        self.assertEqual([w >> 8 for w in rom[symbols["TABLE"] - 0xC000:][:4]], [0xF8] * 4, ".TABLE words")

    def test_ldt_xy_plus(self):
        # LDT A, XY+: LDT A, XY and then XY + 1, still 3 cycles. Its subop is 2, so A loads with
        # nA_LD and C (register 2) must not change
        source = """
            MOV X, HIGH:TABLE
            MOV Y, LOW:TABLE
            LDT A, XY+
            MOV B, A
            LDT A, XY+
            MOV D, A
            LDT A, XY+
            HALT
        TABLE:
            .TABLE 0x41, 0x42
            .RAW 0x3C99
        """
        rom, symbols = em.assemble_source(".ORG 0xC000\n" + source)
        cpu = run_rom(rom, regs={"C": 0x5A}, flags=Z | C | N | V, symbols=symbols)
        self.assertEqual((cpu.r[1], cpu.r[3], cpu.r[0]), (0x41, 0x42, 0x99))
        self.assertEqual(cpu.r[2], 0x5A, "LDT A, XY+ loaded C")
        self.assertEqual(cpu.r[6] << 8 | cpu.r[7], symbols["TABLE"] + 3)
        self.assertEqual(cpu.flags, Z | C | N | V, "LDT A, XY+ shouldn't change the flags")
        self.assertEqual(cpu.cycles, 2 + 2 + 3 * 3 + 2 * 2 + HALT_CYCLES)


class TestJumps(unittest.TestCase):
    def test_conditional_jumps(self):
        for i, cond in enumerate(em.CONDITIONS):
            bit = [C, C, Z, Z, N, N, V, V][i]
            for flags in (0, bit):
                taken = bool(flags) != (i % 2 == 1)
                cpu = run_source_with_target(f"J{cond} TARGET", flags=flags)
                self.assertEqual(cpu.r[0], 2 if taken else 1, f"J{cond} with flags {em.flags_str(flags)}")
                self.assertEqual(cpu.jump_cycles, 5 if taken else 3, f"J{cond} cycles")

    def test_conditional_jumps_xy(self):
        for i, cond in enumerate(em.CONDITIONS):
            bit = [C, C, Z, Z, N, N, V, V][i]
            for flags in (0, bit):
                taken = bool(flags) != (i % 2 == 1)
                cpu = run_source_with_target(f"J{cond} XY", flags=flags, setup="MOV X, HIGH:TARGET\nMOV Y, LOW:TARGET")
                self.assertEqual(cpu.r[0], 2 if taken else 1, f"J{cond} XY with flags {em.flags_str(flags)}")
                self.assertEqual(cpu.jump_cycles, 2)

    def test_jmp(self):
        for jump, setup, cycles in (("JMP TARGET", "", 5),
                                    ("JMP MAR", "MOV MARH, HIGH:TARGET\nMOV MARL, LOW:TARGET", 2),
                                    ("JMP XY", "MOV X, HIGH:TARGET\nMOV Y, LOW:TARGET", 2)):
            cpu = run_source_with_target(jump, setup=setup)
            self.assertEqual(cpu.r[0], 2, jump)
            self.assertEqual(cpu.jump_cycles, cycles, jump)

    def test_direct_jump_overwrites_mar(self):
        cpu = run_source_with_target("JMP TARGET", mar=0x1234)
        self.assertEqual(cpu.mar, cpu.symbols["TARGET"])

    def test_call_ret(self):
        for call, setup, cycles in (("CALL SUB", "", 7),
                                    ("CALL MAR", "MOV MARH, HIGH:SUB\nMOV MARL, LOW:SUB", 5),
                                    ("CALL XY", "MOV X, HIGH:SUB\nMOV Y, LOW:SUB", 5)):
            source = f"""
                {setup}
            CALLER:
                {call}
            BACK:
                MOV B, 0x77
                HALT
            SUB:
                MOV A, 0x66
                RET
            """
            rom, symbols = em.assemble_source(".ORG 0xC000\n" + source)
            cpu = run_rom(rom, sp=0xBAFF, symbols=symbols)
            back = symbols["BACK"]
            self.assertEqual((cpu.r[0], cpu.r[1]), (0x66, 0x77), call)
            self.assertEqual(cpu.sp, 0xBAFF, f"{call}: SP after RET")
            self.assertEqual((cpu.ram[0xBAFF], cpu.ram[0xBAFE]), (back >> 8, back & 0xFF), f"{call}: return address")
            setup_cycles = 2 * len(setup.splitlines()) if setup else 0
            # setup + CALL + MOV A + RET + MOV B + HALT
            self.assertEqual(cpu.cycles, setup_cycles + cycles + 2 + 5 + 2 + HALT_CYCLES, call)

    def test_conditional_calls(self):
        source = """
            {call}
        BACK:
            MOV B, 0x77
            HALT
        SUB:
            MOV A, 0x66
            RET
        """
        for i, cond in enumerate(em.CONDITIONS):
            bit = [C, C, Z, Z, N, N, V, V][i]
            for flags in (0, bit):
                taken = bool(flags) != (i % 2 == 1)
                rom, symbols = em.assemble_source(".ORG 0xC000\n" + source.format(call=f"CALL{cond} SUB"))
                cpu = run_rom(rom, flags=flags, sp=0xBAFF, symbols=symbols)
                what = f"CALL{cond} with flags {em.flags_str(flags)}"
                self.assertEqual((cpu.r[0], cpu.r[1], cpu.sp), (0x66 if taken else 0, 0x77, 0xBAFF), what)
                if taken:
                    back = symbols["BACK"]
                    self.assertEqual((cpu.ram[0xBAFF], cpu.ram[0xBAFE]), (back >> 8, back & 0xFF), what)
                # CALLcc (+ MOV A + RET) + MOV B + HALT
                self.assertEqual(cpu.cycles, (7 + 2 + 5 if taken else 3) + 2 + HALT_CYCLES, what)

    def test_conditional_returns(self):
        source = """
            CALL SUB
            MOV B, 0x77
            HALT
        SUB:
            {ret}
            MOV A, 0x55
            RET
        """
        for i, cond in enumerate(em.CONDITIONS):
            bit = [C, C, Z, Z, N, N, V, V][i]
            for flags in (0, bit):
                taken = bool(flags) != (i % 2 == 1)
                rom, symbols = em.assemble_source(".ORG 0xC000\n" + source.format(ret=f"RET{cond}"))
                cpu = run_rom(rom, flags=flags, sp=0xBAFF, symbols=symbols)
                what = f"RET{cond} with flags {em.flags_str(flags)}"
                self.assertEqual((cpu.r[0], cpu.r[1], cpu.sp), (0 if taken else 0x55, 0x77, 0xBAFF), what)
                self.assertEqual(cpu.flags, flags, what)
                # CALL + RETcc (+ MOV A + RET) + MOV B + HALT
                self.assertEqual(cpu.cycles, 7 + (5 if taken else 2 + 2 + 5) + 2 + HALT_CYCLES, what)

    def test_conditional_call_syntax(self):
        for source in ("CALLZ MAR", "CALLNC XY", "RETZ A"):
            with self.assertRaises(em.assembler.AssemblerError, msg=source):
                em.assemble_source(".ORG 0xC000\n" + source)

    def test_halt(self):
        rom, symbols = em.assemble_source(".ORG 0xC000\nMOV A, 1\nHALT\nMOV A, 2\nHALT")
        cpu = run_rom(rom)
        self.assertEqual((cpu.r[0], cpu.cycles, cpu.upc, cpu.pc), (1, 2 + HALT_CYCLES, 2, 0xC002))
        for _ in range(10):                     # it stays frozen
            cpu.step()
        self.assertEqual((cpu.r[0], cpu.upc, cpu.pc), (1, 2, 0xC002))

    def test_free_slots(self):
        old_alu = [base << 11 | sub << 8 for base in (0x12, 0x13, 0x14) for sub in (0, 5)]
        for raw in [0x1A00, 0x1B00, 0x1C00, 0x1D00, 0x1E00, 0x1F00,
                    0xEE00, 0xEF00, 0xF500, 0xFB00, 0xFC00] + old_alu:
            values = {r: 0x21 * (i + 1) & 0xFF for i, r in enumerate(REGS)}
            cpu = run(f".RAW 0x{raw:04X}", regs=values, flags=Z | N, mar=0x1234, sp=0x4321)
            self.assertEqual(cpu.r, [values[r] for r in REGS], f".RAW 0x{raw:04X}")
            self.assertEqual((cpu.flags, cpu.mar, cpu.sp), (Z | N, 0x1234, 0x4321), f".RAW 0x{raw:04X}")
            self.assertEqual(cpu.cycles - HALT_CYCLES, 2, f".RAW 0x{raw:04X}")


def run_source_with_target(jump, flags=0, setup="", mar=0):
    """Runs: setup, the jump, MOV A, 1 / HALT, TARGET: MOV A, 2 / HALT.
    Leaves the cycles the jump took in cpu.jump_cycles."""
    source = f"""
        {setup}
        {jump}
        MOV A, 1
        HALT
    TARGET:
        MOV A, 2
        HALT
    """
    rom, symbols = em.assemble_source(".ORG 0xC000\n" + source)
    cpu = run_rom(rom, flags=flags, mar=mar, symbols=symbols)
    setup_cycles = 2 * len([l for l in setup.splitlines() if l.strip()])
    cpu.jump_cycles = cpu.cycles - setup_cycles - 2 - HALT_CYCLES
    return cpu


class TestStack(unittest.TestCase):
    def test_sp_moves(self):
        self.assertEqual(run("MOV SP, MAR", mar=0x1234).sp, 0x1234)
        self.assertEqual(run("MOV SP, XY", regs={"X": 0xBA, "Y": 0xFF}).sp, 0xBAFF)
        cpu = run("MOV MAR, SP", sp=0x4567)
        self.assertEqual((cpu.mar, cpu.cycles - HALT_CYCLES), (0x4567, 3))
        cpu = run("MOV X, SPH\nMOV Y, SPL", sp=0x89AB)
        self.assertEqual((cpu.r[6], cpu.r[7]), (0x89, 0xAB))

    def test_inc_dec_sp(self):
        self.assertEqual(run("INC SP", sp=0x00FF).sp, 0x0100)
        self.assertEqual(run("DEC SP", sp=0x0100).sp, 0x00FF)
        self.assertEqual(run("DEC SP", sp=0x0000).sp, 0xFFFF)

    def test_pushf(self):
        # the pushed byte is 0000VCNZ (Z N C V in bits 0-3), while cpu.flags is Z C N V
        for flags in range(16):
            cpu = run("PUSHF", flags=flags, sp=0xBAFF)
            self.assertEqual((cpu.ram[0xBAFF], cpu.sp), (flags_byte(flags), 0xBAFE))

    def test_popf(self):
        for flags in range(16):
            cpu = run("POPF", sp=0xBAFE, ram={0xBAFF: flags_byte(flags)})
            self.assertEqual((cpu.flags, cpu.sp), (flags, 0xBAFF), f"POPF of {flags_byte(flags):04b}")


if __name__ == "__main__":
    unittest.main()
