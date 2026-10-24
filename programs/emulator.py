#!/usr/bin/env python3
# ==============================================================================
# SFD-8 EMULATOR
# ==============================================================================
# Runs a program on a model of the CPU, one clock cycle (= one microstep) at a time.
#
# The control signals come straight from the microcode in crom_programmer.py (or from
# the eprom*.hex files), so this runs exactly what the EPROMs hold, and the cycle
# counts are exact. The rest of the CPU is a model of the Digital circuits: the buses,
# the registers (all of them load on the rising clock edge), the ALU (two 74382, carry
# and overflow included), the RAM, the ROM (it only goes to the IR) and the MMIO
# (keyboard, SPI_OUT with the MAX7219 on it, and the LEDs).
#
# Anything that would go wrong on real hardware is reported as a problem: two drivers
# on a bus at once, loading from a bus nobody drives, fetching from outside the ROM...
# Reading RAM that was never written (it powers up random) and writing to the ROM area
# are reported as warnings.
#
#   python3 emulator.py primes.asm                  run until HALT
#   python3 emulator.py fibonacci.hex --hz 100e3    times for a 100 kHz clock
#   python3 emulator.py main.asm --trace            print every instruction
#   python3 emulator.py keyboard_test.asm --keys "Ab1" --max-cycles 100000
#   python3 emulator.py --microcode "ADD A, B"      what each microstep does
# ==============================================================================

import argparse
import os
import random
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crom_programmer as cp    # the control bit numbers and the microcode itself
import assembler

# memory map (ADDR_DEC.dig)
MMIO_START = 0xBF00             # RAM below, MMIO up to 0xBFFF
ROM_START = 0xC000              # ROM up to 0xFFFF
ROM_SIZE = 0x4000

# SPI_OUT bits (MMIO 0xBF02)
SPI_SCLK = 1 << 0
SPI_MOSI = 1 << 1
SPI_MAX_CS = 1 << 4

REGS = "ABCDEFXY"
CONDITIONS = ["C", "NC", "Z", "NZ", "N", "NN", "V", "NV"]


class EmulatorError(Exception):
    pass


# ==============================================================================
# FILES
# ==============================================================================

def read_digital_hex(path, size):
    # Digital's "v2.0 raw" format: one hex value per line, and "n*value" repeats a value
    with open(path) as f:
        tokens = f.read().split()
    if tokens[:2] != ["v2.0", "raw"]:
        raise ValueError(f"{path}: not a Digital 'v2.0 raw' hex file")
    words = []
    for tok in tokens[2:]:
        if "*" in tok:
            count, value = tok.split("*")
            words += [int(value, 16)] * int(count)
        else:
            words.append(int(tok, 16))
    if len(words) > size:
        raise ValueError(f"{path}: {len(words)} words, but the memory only has {size}")
    return words + [0] * (size - len(words))


class Microcode(list):
    """The 65536 control words, every bit active-high (1 = the signal is on).
    It also keeps the compiled step of each microcode address."""
    def __init__(self, words):
        super().__init__(words)
        self.steps = [None] * len(self)


_default_microcode = None

def load_microcode(hex_dir=None):
    global _default_microcode
    if hex_dir is None and _default_microcode is not None:
        return _default_microcode
    if hex_dir:
        eproms = [read_digital_hex(os.path.join(hex_dir, f"eprom{i}.hex"), 1 << 16) for i in (1, 2, 3)]
    else:
        eproms = cp.gen_microcode()
    words = Microcode((e1 | e2 << 16 | e3 << 32) ^ cp.active_low_mask for e1, e2, e3 in zip(*eproms))
    if hex_dir is None:
        _default_microcode = words
    return words


def words_to_rom(words):
    # same placement as assembler.generate_digital_hex
    rom = [0] * ROM_SIZE
    for addr, word in words:
        if ROM_START <= addr <= 0xFFFF:
            rom[addr - ROM_START] = word
        elif 0 <= addr < ROM_SIZE:
            rom[addr] = word
        else:
            raise ValueError(f"Address 0x{addr:04X} is outside the ROM")
    return rom


def assemble_source(source, include_dir=HERE):
    """Assembles source text. Returns (rom, symbols)."""
    lines = []
    for line in source.splitlines():
        m = assembler.INCLUDE_RE.match(line)
        lines.append(assembler.expand_includes(os.path.join(include_dir, m.group(1).strip())) if m else line)
    symbols, words = assembler.assemble("\n".join(lines))
    return words_to_rom(words), symbols


def load_program(path):
    """The 16K words of the program ROM (0xC000-0xFFFF) from a .asm or .hex file. Returns (rom, symbols)."""
    if path.lower().endswith(".asm"):
        symbols, words = assembler.assemble(assembler.expand_includes(path))
        return words_to_rom(words), symbols
    return read_digital_hex(path, ROM_SIZE), {}


# ==============================================================================
# ALU: two 74382, the carry out of the low one goes to the carry in of the high one
# ==============================================================================
# The carry and overflow outputs are worked out like the chip does it, with a
# generate/propagate signal per bit. In the logic modes they don't mean anything, but
# they still get loaded into C and V (see planning/issues.md), so they're modeled too.
# These formulas were checked against Digital's 74382 with all 4096 input combinations.

ALU_OPS = ["0", "data - A", "A - data", "A + data", "A XOR data", "A OR data", "A AND data", "0xFF"]

def alu_text(s, cin):
    # the subtractions are A + NOT(B) + carry in, so without the carry in they're one less
    if s in (1, 2):
        return ALU_OPS[s] + ("" if cin else " - 1")
    return ALU_OPS[s] + (" + 1" if s == 3 and cin else "")

def _chip_382(s, a, b, cin):
    if s in (1, 2, 3):                                  # B minus A, A minus B, A plus B
        x, y = {1: (b, ~a & 15), 2: (a, ~b & 15), 3: (a, b)}[s]
        total = x + y + cin
        f = total & 15
        return f, total >> 4, ((x ^ f) & (y ^ f)) >> 3 & 1
    f = {0: 0, 4: a ^ b, 5: a | b, 6: a & b, 7: 15}[s]  # clear, xor, or, and, preset
    g, p = {0: (15, 0), 4: (a & b, a), 5: (0, a & b), 6: (~b & 15, a & b), 7: (0, a & b)}[s]
    carry = cin
    for i in range(4):
        carry = (g >> i & 1) | (p >> i & 1 & carry)
    return f, carry, carry                              # in these modes OVR is the same as the carry

CHIP_382 = [_chip_382(s, a, b, cin) for s in range(8) for a in range(16) for b in range(16) for cin in range(2)]

def alu8(s, a, b, cin):
    """Returns (result, flags), the flags in status register order: bit 0 Z, 1 C, 2 N, 3 V."""
    lo, carry, _ = CHIP_382[s << 9 | (a & 15) << 5 | (b & 15) << 1 | cin]
    hi, c, v = CHIP_382[s << 9 | (a >> 4) << 5 | (b >> 4) << 1 | carry]
    res = hi << 4 | lo
    return res, (res == 0) | c << 1 | (res >> 7) << 2 | v << 3


def flags_str(flags):
    return "".join(name if flags >> bit & 1 else "-" for bit, name in enumerate("ZCNV"))


# ==============================================================================
# DISASSEMBLER
# ==============================================================================

def disassemble(word, next_word=None):
    op, sub, imm = word >> 11, word >> 8 & 7, word & 0xFF
    rd, rs = REGS[sub], REGS[word >> 5 & 7]
    target = f"0x{imm:02X}{next_word & 0xFF:02X}" if next_word is not None else f"0x{imm:02X}xx"
    free = "(free slot, NOP)"
    if op == 0x00: return f"MOV {rd}, 0x{imm:02X}"
    if op == 0x01: return f"MOV {rd}, {rs}"
    if op == 0x02: return [f"MOV MARL, 0x{imm:02X}", f"MOV MARH, 0x{imm:02X}", "INC MAR", "DEC MAR",
                           "INC XY", "DEC XY", free, free][sub]
    if op == 0x03: return [f"MOV MARL, {rs}", f"MOV MARH, {rs}"][sub] if sub < 2 else free
    if op == 0x04: return f"LD {rd}, 0x{imm:02X}"
    if op == 0x05: return f"LD {rd}, MAR"
    if op == 0x06: return f"LD {rd}, XY"
    if op == 0x07: return f"ST 0x{imm:02X}, {rd}"
    if op == 0x08: return f"ST MAR, {rs}"
    if op == 0x09: return f"ST XY, {rs}"
    if op == 0x0A: return f"PUSH {rs}"
    if op == 0x0B: return f"POP {rd}"
    alu = {0x0C: "ADD", 0x0E: "ADC", 0x0F: "SUB", 0x10: "SBC", 0x11: "AND", 0x13: "OR", 0x14: "XOR", 0x19: "CP"}
    if op in alu: return f"{alu[op]} A, {rs}"
    alu_imm = {0x0D: "ADD", 0x12: "AND", 0x1A: "CP"}
    if op in alu_imm: return f"{alu_imm[op]} A, 0x{imm:02X}"
    if op in (0x15, 0x16, 0x17, 0x18): return ["INC", "DEC", "SHR", "ROR"][op - 0x15] + " A"
    if op == 0x1B: return f"J{CONDITIONS[sub]} {target}"
    if op == 0x1C: return f"J{CONDITIONS[sub]} XY"
    if op == 0x1D: return [f"JMP {target}", f"CALL {target}", "JMP MAR", "JMP XY", "CALL MAR", "CALL XY",
                           free, free][sub]
    if op == 0x1E: return ["MOV SP, MAR", "MOV MAR, SP", "MOV SP, XY", "INC SP", "DEC SP", free,
                           "MOV X, SPH", "MOV Y, SPL"][sub]
    return [free, "RET", free, free, free, "PUSHF", "POPF", "HALT"][sub]


def is_two_words(word):
    op, sub = word >> 11, word >> 8 & 7
    return op == 0x1B or (op == 0x1D and sub in (0, 1))


# ==============================================================================
# MICROSTEP COMPILER
# ==============================================================================
# Each control word becomes a small Python function that does that microstep: first
# the buses (what drives the address and data buses with these signals), then the
# clock edge (every register that loads, loads at the same time). It also gives a
# description of the step, used by --microcode.

ADDR_LOW = {"PC": "c.pc & 0xFF", "MAR": "c.mar & 0xFF", "XY": "c.r[7]", "SP": "c.sp & 0xFF", "IR": "ir & 0xFF"}
ADDR_HIGH = {"PC": "c.pc >> 8", "MAR": "c.mar >> 8", "XY": "c.r[6]", "SP": "c.sp >> 8", "0x00": "0"}
ADDR_FULL = {"PC": "c.pc", "MAR": "c.mar", "SP": "c.sp", "XY": "c.r[6] << 8 | c.r[7]"}

def gen_step(cw):
    """Returns (source, description, problems) for one control word (active-high)."""
    on = lambda bit: cw >> bit & 1 == 1
    code = ["ir = c.ir"]
    desc = []
    problems = []

    # ---- address bus ----
    low, high = [], []
    if not on(cp.PC_OE):
        low.append("PC"); high.append("PC")
    for bit, name in ((cp.nMAR_OE, "MAR"), (cp.nXYA_OE, "XY"), (cp.nSP_OE, "SP")):
        if on(bit):
            low.append(name); high.append(name)
    if on(cp.nIRA_OE):
        low.append("IR")
    if on(cp.nHBA_OE):
        high.append("0x00")
    if len(low) > 1 or len(high) > 1:
        problems.append(f"the address bus is driven by {' and '.join(dict.fromkeys(low + high))} at once")
    addr_used = on(cp.MEM_RD) or on(cp.MEM_WR) or on(cp.nPC_LD) or on(cp.nSP_LD) or on(cp.nIR_LD)
    if low and high:
        if low[0] == high[0]:
            code.append(f"abus = {ADDR_FULL[low[0]]}")
            addr_desc = low[0]
        else:
            code.append(f"abus = ({ADDR_HIGH[high[0]]}) << 8 | {ADDR_LOW[low[0]]}")
            addr_desc = "0x00:IR[7:0]" if (high[0], low[0]) == ("0x00", "IR") else f"{high[0]}:{low[0]}"
        if addr_used:
            desc.append(f"address bus = {addr_desc}")
    else:
        code.append("abus = None")
        if addr_used:
            problems.append("the address bus is used, but nothing drives it")
    code.append("c.abus = abus")

    # ---- data bus ----
    drivers = []                                        # (description, expression)
    if on(cp.nPCL_OE): drivers.append(("PCL", "c.pc & 0xFF"))
    if on(cp.nPCH_OE): drivers.append(("PCH", "c.pc >> 8"))
    if on(cp.nIRD_OE): drivers.append(("IR[7:0]", "ir & 0xFF"))
    if on(cp.REG_OE):
        if on(cp.SRC_SEL):
            drivers.append(("{r108}", "c.r[ir >> 8 & 7]"))
        else:
            drivers.append(("{r75}", "c.r[ir >> 5 & 7]"))
    if on(cp.nSHR_OE):
        bit7 = 0x80 if on(cp.SHR_IN0) else 0
        drivers.append((f"A >> 1 (bit 7 = {1 if bit7 else 0})", f"c.r[0] >> 1 | {bit7}"))
    if on(cp.nFL_OE): drivers.append(("flags", "c.flags"))
    if on(cp.nSPL_OE): drivers.append(("SPL", "c.sp & 0xFF"))
    if on(cp.nSPH_OE): drivers.append(("SPH", "c.sp >> 8"))
    if on(cp.nALU_OE):
        problems.append("nALU_OE puts the ALU result on the data bus, but the ALU's B input reads the data bus (a loop)")
    if len(drivers) > 1:
        problems.append(f"the data bus is driven by {' and '.join(d for d, _ in drivers)} at once")

    alu_used = (on(cp.REG_LD) and on(cp.A_SEL)) or (on(cp.nFL_LD) and not on(cp.FL_SEL))
    data_used = (on(cp.REG_LD) or on(cp.nMARL_LD) or on(cp.nMARH_LD) or on(cp.MEM_WR)
                 or (on(cp.nFL_LD) and on(cp.FL_SEL)) or alu_used)
    if on(cp.MEM_RD):
        if drivers:
            code.append("m = c.mem_read(abus)")
            code.append(f"dbus = {drivers[0][1]}")
            code.append(f"if m is not None: c.problem('the memory and {drivers[0][0]} drive the data bus at once')")
            data_desc = drivers[0][0]
        else:
            code.append("dbus = c.mem_read(abus)")
            data_desc = "mem[address]"
            if data_used:
                code.append("if dbus is None: c.problem(f'nothing drives the data bus: 0x{abus:04X} can\\'t be read'); dbus = 0")
    elif drivers:
        code.append(f"dbus = {drivers[0][1]}")
        data_desc = drivers[0][0]
    else:
        code.append("dbus = None")
        data_desc = None
        if data_used:
            problems.append("the data bus is used, but nothing drives it")
            code.append("dbus = 0")
    code.append("c.dbus = dbus")
    if data_used and data_desc:
        desc.append(f"data bus = {data_desc}")

    # ---- ALU (combinational, A and the data bus) ----
    if alu_used:
        s = on(cp.ALU_S0) | on(cp.ALU_S1) << 1 | on(cp.ALU_S2) << 2
        cin = int(on(cp.ALU_CIN))
        code.append(f"res, alufl = alu8({s}, c.r[0], dbus, {cin})")
        desc.append(f"ALU = {alu_text(s, cin)}")

    # ---- clock edge: everything below loads at the same time ----
    if on(cp.MEM_RD) and on(cp.MEM_WR):
        problems.append("MEM_RD and MEM_WR at once")
    if on(cp.MEM_WR):
        code.append("c.mem_write(abus, dbus)")
        desc.append("mem[address] <- data")
    if on(cp.nIR_LD):
        if not on(cp.MEM_RD):
            problems.append("nIR_LD without MEM_RD: the ROM outputs are off")
        code.append("c.ir = c.rom_read(abus)")
        desc.append("IR <- ROM[address]")
    if on(cp.nPC_LD):
        code.append("c.pc = abus")
        desc.append("PC <- address bus")
    elif on(cp.PC_INC):
        code.append("c.pc = (c.pc + 1) & 0xFFFF")
        desc.append("PC <- PC + 1")

    marl, marh = on(cp.nMARL_LD), on(cp.nMARH_LD)
    if (marl or marh) and on(cp.nMAR_INC):
        problems.append("the MAR loads and counts at once")
    if marl and marh:
        code.append("c.mar = dbus << 8 | dbus")
        desc.append("MAR <- data:data")
    elif marl:
        code.append("c.mar = c.mar & 0xFF00 | dbus")
        desc.append("MARL <- data")
    elif marh:
        code.append("c.mar = c.mar & 0xFF | dbus << 8")
        desc.append("MARH <- data")
    elif on(cp.nMAR_INC):
        sign = "-" if on(cp.MAR_DIR) else "+"
        code.append(f"c.mar = (c.mar {sign} 1) & 0xFFFF")
        desc.append(f"MAR <- MAR {sign} 1")

    if on(cp.REG_LD):
        code.append("d = ir >> 8 & 7")
        if on(cp.A_SEL):
            code.append("c.r[d] = res if d == 0 else dbus")
            desc.append("{r108} <- ALU")
        else:
            code.append("c.r[d] = dbus")
            desc.append("{r108} <- data")
    if on(cp.nXY_INC):
        if on(cp.REG_LD):
            problems.append("REG_LD and nXY_INC at once")
        sign = "-" if on(cp.XY_DIR) else "+"
        code.append(f"xy = ((c.r[6] << 8 | c.r[7]) {sign} 1) & 0xFFFF")
        code.append("c.r[6] = xy >> 8")
        code.append("c.r[7] = xy & 0xFF")
        desc.append(f"XY <- XY {sign} 1")

    if on(cp.nSP_LD):
        if on(cp.nSP_INC):
            problems.append("the SP loads and counts at once")
        code.append("c.sp = abus")
        desc.append("SP <- address bus")
    elif on(cp.nSP_INC):
        sign = "-" if on(cp.SP_DIR) else "+"
        code.append(f"c.sp = (c.sp {sign} 1) & 0xFFFF")
        desc.append(f"SP <- SP {sign} 1")

    if on(cp.nFL_LD):
        if on(cp.FL_SEL):
            code.append("c.flags = dbus & 15")
            desc.append("flags <- data[3:0]")
        else:
            code.append("c.flags = alufl")
            desc.append("flags <- ALU (Z C N V)")

    if on(cp.MEM_RD):
        code.append("if c.kb_read: c.kb_consume()")

    if on(cp.nMPC_RST):
        code.append("c.upc = 0")
        desc.append("next instruction")
    elif on(cp.nHALT):
        code.append("c.halted = True")
        desc.append("the micro-PC stops here (HALT)")
    else:
        code.append("c.upc = (c.upc + 1) & 15")

    # static problems are reported when (and only if) the step really runs
    code = [f"c.problem({p!r})" for p in problems] + code
    source = "def step(c):\n" + "".join(f"    {line}\n" for line in code)
    return source, desc, problems


_compiled_steps = {}

def compile_step(cw):
    step = _compiled_steps.get(cw)
    if step is None:
        source, _, _ = gen_step(cw)
        namespace = {"alu8": alu8}
        exec(source, namespace)
        step = _compiled_steps[cw] = namespace["step"]
    return step


# ==============================================================================
# MAX7219 (the model in max7219_sim.dig)
# ==============================================================================

class Max7219:
    def __init__(self):
        self.shift = 0                  # 16-bit shift register, MOSI goes in at bit 0
        self.digits = [0] * 8           # DIG1 (rightmost) .. DIG8, 4 bits each

    def clock(self, mosi):              # rising edge of SCLK
        self.shift = (self.shift << 1 | mosi) & 0xFFFF

    def latch(self):                    # rising edge of CS: registers 1-8 are the digits
        reg = self.shift >> 8 & 15
        if 1 <= reg <= 8:
            self.digits[reg - 1] = self.shift & 15

    def text(self):
        return "".join(f"{d:X}" for d in reversed(self.digits))


# ==============================================================================
# CPU
# ==============================================================================

class CPU:
    def __init__(self, rom, microcode=None, keys="", random_state=False, strict=True):
        self.rom = list(rom) + [0] * (ROM_SIZE - len(rom))
        self.microcode = microcode if microcode is not None else load_microcode()
        self.strict = strict

        # state right after the reset: the reset buffer puts 0xC000 on the address bus
        # and the PC loads it, the micro-PC is cleared and RST clears A-F (74173)
        self.pc = ROM_START
        self.ir = 0
        self.upc = 0
        self.r = [0] * 8                # A B C D E F X Y
        self.mar = 0
        self.sp = 0
        self.flags = 0                  # bit 0 Z, 1 C, 2 N, 3 V
        self.ram = bytearray(0x10000)
        if random_state:                # real hardware: everything without a reset powers up random
            rnd = random.Random()
            self.ram = bytearray(rnd.getrandbits(8) for _ in range(0x10000))
            self.r[6], self.r[7] = rnd.getrandbits(8), rnd.getrandbits(8)
            self.mar, self.sp, self.flags = rnd.getrandbits(16), rnd.getrandbits(16), rnd.getrandbits(4)
        self.written = bytearray(0x10000)

        # MMIO
        self.spi = 0
        self.leds = 0
        self.max7219 = Max7219()
        self.kb = deque(ord(ch) & 0xFF for ch in keys)
        self.kb_read = False
        self.on_display = None          # called after the MAX7219 digits change
        self.on_leds = None             # called after the LEDs change

        # bookkeeping
        self.cycles = 0
        self.instructions = 0
        self.inst_pc = ROM_START        # address of the instruction being executed
        self.halted = False
        self.abus = self.dbus = None    # bus values of the last cycle (None = not driven)
        self.problems = []
        self.warnings = {}              # message -> [count, first place]

    # ---- reporting ----
    def where(self):
        return (f"cycle {self.cycles}, step {self.upc} of the instruction at 0x{self.inst_pc:04X} "
                f"({self.instruction_at(self.inst_pc)})")

    def problem(self, message):
        if self.strict:
            raise EmulatorError(f"{message}\n    at {self.where()}")
        self.problems.append(f"{message} ({self.where()})")

    def warn(self, message):
        entry = self.warnings.setdefault(message, [0, self.where()])
        entry[0] += 1

    def instruction_at(self, addr):
        if not ROM_START <= addr <= 0xFFFF:
            return "outside the ROM"
        word = self.rom[addr - ROM_START]
        nxt = self.rom[addr - ROM_START + 1] if addr < 0xFFFF else None
        return disassemble(word, nxt if is_two_words(word) else None)

    # ---- memory and MMIO (used by the compiled steps) ----
    def mem_read(self, addr):
        """What the memory puts on the data bus for a read, None if nothing drives it."""
        if addr is None:
            return None
        if addr < MMIO_START:
            if not self.written[addr]:
                self.warn("read RAM that was never written (it powers up random)")
            return self.ram[addr]
        if addr < ROM_START:
            reg = addr & 7              # only A0-A2 are decoded
            if reg == 0:                # keyboard data, the read also takes the key out of the buffer
                self.kb_read = True
                return self.kb[0] if self.kb else 0
            if reg == 1:                # keyboard status, bit 7 = a key is waiting
                return 0x80 if self.kb else 0
        return None                     # SPI_OUT and DISPLAY can't be read, and the ROM only goes to the IR

    def kb_consume(self):
        self.kb_read = False
        if self.kb:
            self.kb.popleft()

    def mem_write(self, addr, value):
        if addr is None or value is None:
            return
        if addr < MMIO_START:
            self.ram[addr] = value
            self.written[addr] = 1
        elif addr < ROM_START:
            reg = addr & 7
            if reg == 2:
                self.write_spi(value & 0x1F)    # D5-D7 of that 74377 are grounded
            elif reg == 3:
                self.leds = value
                if self.on_leds:
                    self.on_leds(self)
        else:
            self.warn("wrote to the ROM area (nothing happens)")

    def write_spi(self, value):
        old, self.spi = self.spi, value
        rising = ~old & value
        if rising & SPI_MAX_CS:
            before = list(self.max7219.digits)
            self.max7219.latch()
            if self.max7219.digits != before and self.on_display:
                self.on_display(self)
        if rising & SPI_SCLK:
            self.max7219.clock(value >> 1 & 1)

    def rom_read(self, addr):
        if addr is None or addr < ROM_START:
            self.problem("the IR loads from outside the ROM (the ROM isn't selected)"
                         + ("" if addr is None else f": address 0x{addr:04X}"))
            return 0
        return self.rom[addr - ROM_START]

    # ---- running ----
    def step(self):
        """One clock cycle."""
        if self.upc == 0:
            self.inst_pc = self.pc
            self.instructions += 1
        addr = self.ir >> 8 | self.upc << 8 | self.flags << 12
        steps = self.microcode.steps
        step = steps[addr]
        if step is None:
            step = steps[addr] = compile_step(self.microcode[addr])
        step(self)
        self.cycles += 1

    def run(self, max_cycles=None, on_instruction=None):
        """Runs until HALT or max_cycles. on_instruction(cpu) is called after each instruction.
        Returns True if the CPU halted."""
        steps, microcode = self.microcode.steps, self.microcode
        limit = float("inf") if max_cycles is None else max_cycles
        while not self.halted and self.cycles < limit:
            if self.upc == 0:
                self.inst_pc = self.pc
                self.instructions += 1
            addr = self.ir >> 8 | self.upc << 8 | self.flags << 12
            step = steps[addr]
            if step is None:
                step = steps[addr] = compile_step(microcode[addr])
            step(self)
            self.cycles += 1
            if on_instruction and self.upc == 0:
                on_instruction(self)
        return self.halted

    def run_traced(self, max_cycles, write, on_instruction=None):
        """Like run(), but calls write(line) every cycle with the state during that cycle:
        cycle, micro-PC, IR, address bus, data bus, control word (as the EPROMs hold it), A, X, Y,
        flags. The registers are the ones the cycle starts with. Same format as Digital's trace."""
        while not self.halted and self.cycles < max_cycles:
            cycle, upc, ir, a, x, y, flags = self.cycles, self.upc, self.ir, self.r[0], self.r[6], self.r[7], self.flags
            raw = self.microcode[ir >> 8 | upc << 8 | flags << 12] ^ cp.active_low_mask
            self.step()
            ab = "----" if self.abus is None else f"{self.abus:04X}"
            db = "--" if self.dbus is None else f"{self.dbus:02X}"
            write(f"{cycle} {upc:X} {ir:04X} {ab} {db} {raw:012X} {a:02X} {x:02X} {y:02X} {flags:X}")
            if on_instruction and self.upc == 0:
                on_instruction(self)
        return self.halted

    def state(self):
        return (" ".join(f"{n}={v:02X}" for n, v in zip(REGS, self.r))
                + f" MAR={self.mar:04X} SP={self.sp:04X} flags={flags_str(self.flags)}")


# ==============================================================================
# --microcode: what each step of an instruction does
# ==============================================================================

def flag_condition(group):
    if len(group) == 16:
        return "always"
    for bit, name in enumerate("ZCNV"):
        for value in (0, 1):
            if sorted(group) == [f for f in range(16) if f >> bit & 1 == value]:
                return f"when {name} = {value}"
    return "flags (V N C Z) in {" + ", ".join(f"{f:04b}" for f in group) + "}"


def explain(line, microcode):
    rom, _ = assemble_source(".ORG 0xC000\n" + line)
    word = rom[0]
    two = is_two_words(word)
    names = {"r108": REGS[word >> 8 & 7], "r75": REGS[word >> 5 & 7]}
    opcode = word >> 8
    words = f"0x{word:04X}" + (f" 0x{rom[1]:04X}" if two else "")
    print(f"{disassemble(word, rom[1] if two else None)} = {words}, opcode 0x{opcode:02X} "
          f"(base 0x{opcode >> 3:02X}, subOp {opcode & 7})")

    sequences = {}
    for flags in range(16):
        seq = []
        for upc in range(16):
            cw = microcode[opcode | upc << 8 | flags << 12]
            seq.append(cw)
            if cw >> cp.nMPC_RST & 1 or cw >> cp.nHALT & 1:
                break
        sequences.setdefault(tuple(seq), []).append(flags)

    for seq, group in sequences.items():
        halts = seq[-1] >> cp.nHALT & 1
        cycles = f"{len(seq)} cycles" + (", then it stays in the last step" if halts else "")
        print(f"\n{flag_condition(group)} ({cycles}):" if len(sequences) > 1 else f"\n{cycles}:")
        for upc, cw in enumerate(seq):
            _, desc, problems = gen_step(cw)
            text = ", ".join(desc).format(**names) or "(nothing)"
            print(f"  step {upc:<2} {text}")
            for p in problems:
                print(f"           PROBLEM: {p}")


# ==============================================================================
# COMMAND LINE
# ==============================================================================

def main():
    p = argparse.ArgumentParser(description="Runs an SFD-8 program on a cycle-exact model of the CPU.")
    p.add_argument("program", nargs="?", help=".asm or .hex file")
    p.add_argument("--max-cycles", type=float, default=50e6, help="stop after this many cycles (default 50 million)")
    p.add_argument("--hz", type=float, default=1e6, help="clock frequency for the times shown (default 1 MHz)")
    p.add_argument("--keys", default="", help="characters already waiting in the keyboard buffer")
    p.add_argument("--key-interval", type=float, default=0, metavar="CYCLES",
                   help="type the --keys one every CYCLES cycles instead of all at the start")
    p.add_argument("--trace", action="store_true", help="print every instruction")
    p.add_argument("--cycle-trace", metavar="FILE", help="write the state of every cycle to FILE")
    p.add_argument("-q", "--quiet", action="store_true", help="don't print the display and LED changes")
    p.add_argument("--eprom-hex", metavar="DIR", help="use eprom1-3.hex from DIR instead of crom_programmer.py")
    p.add_argument("--random", action="store_true",
                   help="power up with random RAM and registers, like real hardware")
    p.add_argument("--keep-going", action="store_true", help="don't stop at the first problem")
    p.add_argument("--microcode", metavar="INSTRUCTION", help='show the microsteps of an instruction, like "ADD A, B"')
    args = p.parse_args()

    microcode = load_microcode(args.eprom_hex)
    if args.microcode:
        explain(args.microcode, microcode)
        return 0
    if not args.program:
        p.error("give a program (.asm or .hex), or --microcode")

    rom, symbols = load_program(args.program)
    labels = {addr: name for name, addr in symbols.items() if not name.startswith(".")}
    interval = int(args.key_interval)
    cpu = CPU(rom, microcode, keys="" if interval else args.keys, random_state=args.random,
              strict=not args.keep_going)

    def when(c):
        return f"{c.cycles:>12,} cyc {c.cycles / args.hz:>9.4f} s"

    if not args.quiet:
        cpu.on_display = lambda c: print(f"{when(c)}  display {c.max7219.text()}")
        cpu.on_leds = lambda c: print(f"{when(c)}  leds    {c.leds:08b}")

    trace = None
    if args.trace:
        last = [0]
        def trace(c):
            text = c.instruction_at(c.inst_pc)
            label = labels.get(c.inst_pc, "")
            print(f"{c.inst_pc:04X} {label[:10]:>10}  {text:<18} {c.cycles - last[0]:>2}  {c.state()}")
            last[0] = c.cycles

    def run_with_keys(run):
        # with --key-interval, run up to the next key, type it, and go on
        for i, key in enumerate(args.keys if interval else ""):
            run(min((i + 1) * interval, args.max_cycles))
            if cpu.halted or cpu.cycles >= args.max_cycles:
                return
            cpu.kb.append(ord(key) & 0xFF)
        run(args.max_cycles)

    print(f"--- {args.program} (stops at HALT or after {int(args.max_cycles):,} cycles) ---")
    try:
        if args.cycle_trace:
            with open(args.cycle_trace, "w") as out:
                out.write("# cycle upc ir abus dbus control A X Y flags\n")
                run_with_keys(lambda limit: cpu.run_traced(limit, lambda line: out.write(line + "\n"), trace))
        else:
            run_with_keys(lambda limit: cpu.run(limit, trace))
    except EmulatorError as e:
        print(f"\nPROBLEM: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n(stopped)")

    if cpu.halted:
        label = labels.get(cpu.inst_pc)
        place = f"{label} (0x{cpu.inst_pc:04X})" if label else f"0x{cpu.inst_pc:04X}"
        print(f"--- halted at {place} ---")
    else:
        print(f"--- stopped at 0x{cpu.inst_pc:04X} without halting ---")
    print(f"{cpu.cycles:,} cycles, {cpu.instructions:,} instructions, "
          f"{cpu.cycles / max(cpu.instructions, 1):.2f} cycles per instruction, "
          f"{cpu.cycles / args.hz:.4f} s at {args.hz:,.0f} Hz")
    print(cpu.state())
    print(f"display {cpu.max7219.text()}  leds {cpu.leds:08b}")
    for message, (count, first) in cpu.warnings.items():
        print(f"warning: {message}: {count} time{'s' if count > 1 else ''}, the first at {first}")
    for message in cpu.problems:
        print(f"PROBLEM: {message}")
    return 1 if cpu.problems else 0


if __name__ == "__main__":
    sys.exit(main())
