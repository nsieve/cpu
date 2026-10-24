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
    def test_sub(self): self.check_reg_op("SUB")
    def test_sbc(self): self.check_reg_op("SBC")
    def test_cp(self): self.check_reg_op("CP", writes_a=False)
    def test_cp_imm(self): self.check_imm_op("CP", writes_a=False)

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
    def test_xor(self): self.check_logic("XOR", lambda a, b: a ^ b)

    @unittest.expectedFailure
    def test_logic_ops_keep_c_and_v(self):
        # issues.md: the 4 ALU flags are loaded together, so C and V get whatever the 74382 outputs
        for op in ("AND", "OR", "XOR"):
            for a, b, _ in operand_cases(50):
                for cv in (0, C | V):
                    cpu = run(f"{op} A, B", regs={"A": a, "B": b}, flags=cv)
                    self.assertEqual(cpu.flags & (C | V), cv, f"{op} with A={a:02X} B={b:02X}")

    def test_shr(self):
        for a in range(256):
            for flags in (0, Z | C | N | V):
                cpu = run("SHR A", regs={"A": a}, flags=flags)
                self.assertEqual(cpu.r[0], a >> 1)
                self.assertEqual(cpu.flags, flags, "SHR shouldn't change the flags")
                self.assertEqual(cpu.cycles - HALT_CYCLES, 2)

    @unittest.expectedFailure
    def test_ror(self):
        # issues.md: ROR does the same as SHR (SHR_IN0 is never set, and C doesn't go in)
        for a in range(256):
            for carry in (0, 1):
                cpu = run("ROR A", regs={"A": a}, flags=C if carry else 0)
                self.assertEqual(cpu.r[0], carry << 7 | a >> 1, f"ROR A with A={a:02X} C={carry}")


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

    def test_halt(self):
        rom, symbols = em.assemble_source(".ORG 0xC000\nMOV A, 1\nHALT\nMOV A, 2\nHALT")
        cpu = run_rom(rom)
        self.assertEqual((cpu.r[0], cpu.cycles, cpu.upc, cpu.pc), (1, 2 + HALT_CYCLES, 2, 0xC002))
        for _ in range(10):                     # it stays frozen
            cpu.step()
        self.assertEqual((cpu.r[0], cpu.upc, cpu.pc), (1, 2, 0xC002))

    def test_free_slots(self):
        for raw in (0x1600, 0x1700, 0x1A00, 0x1B00, 0x1C00, 0x1D00, 0x1E00, 0x1F00,
                    0xEE00, 0xEF00, 0xF500, 0xF800, 0xFA00, 0xFB00, 0xFC00):
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
        for flags in range(16):
            cpu = run("PUSHF", flags=flags, sp=0xBAFF)
            self.assertEqual((cpu.ram[0xBAFF], cpu.sp), (flags, 0xBAFE))

    @unittest.expectedFailure
    def test_popf(self):
        # issues.md: POPF loads the flags from the ALU (step 2 doesn't set FL_SEL)
        for flags in range(16):
            cpu = run("POPF", sp=0xBAFE, ram={0xBAFF: flags})
            self.assertEqual((cpu.flags, cpu.sp), (flags, 0xBAFF), f"POPF of {flags:04b}")


if __name__ == "__main__":
    unittest.main()
