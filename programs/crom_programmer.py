# CONTROL BITS

# EPROM 1:
PC_INC   = 0    # increment the pc
nPC_LD   = 1    # load the pc (for jmps)
PC_OE    = 2    # 1 = the pc stops driving the address bus (wired to the active-low OE of its 245s, so by default the pc drives it)
nPCL_OE  = 3    # pc outputs the lower byte to the data bus
nPCH_OE  = 4    # pc outputs the higher byte to the data bus
nIRH_LD  = 5    # load the higher byte of the instruction register (the opcode) from ROM
nIRL_LD  = 6    # load the lower byte of the instruction register from ROM (a fetch sets both)
nIRD_OE  = 7    # output the lower byte of the ir to the data bus
nIRA_OE  = 8    # output the lower byte of the ir to the address bus (LB)
nHBA_OE  = 9    # forces the higher byte of the address bus to 0x00
nMPC_RST = 10   # reset the microprogram counter (end of instruction)
nXY_INC  = 11   # increment the XY register pair
XY_DIR   = 12   # 0 = INC, 1 = DEC
nXYA_OE  = 13   # XY register pair output to the address bus
MEM_RD   = 14   # read memory bus (ROM/RAM/MMIO)
MEM_WR   = 15   # write in memory bus (RAM/MMIO)

# EPROM 2:
REG_LD   = 16   # register file load enable
REG_OE   = 17   # register file output enable
MAR_DIR  = 18   # 0 = INC , 1 = DEC
nMARL_LD = 19   # load from data bus into the lower byte of the MAR
nMARH_LD = 20   # load from data bus into the higher byte of the MAR
nMAR_OE  = 21   # output the MAR to the address bus
nMAR_INC = 22   # increment the MAR register
nA_LD    = 23   # loads A without the register file's decoder (ALU operations, so [10:8] can be the subop)
A_SEL    = 24   # multiplexor selector for the input of the accumulator. 0 = data bus, 1 = alu
ALU_S0   = 25   # alu select line 0
ALU_S1   = 26   # alu select line 1
ALU_S2   = 27   # alu select line 2
ALU_CIN  = 28   # carry in on the lowest alu chip
nSHR_OE  = 29   # output a shift right of the accumulator
SHR_IN0  = 30   # bit 7 of the shifted value (0 for SHR, the old C for ROR)
nFL_OE   = 31   # outputs the flag register to the data bus

# EPROM 3:
nFLZN_LD = 32   # loads the Z and N flags
nFLCV_LD = 33   # loads the C and V flags (logic operations only load Z and N, so C and V keep their value)
FL_SEL   = 34   # mux that selects the flag register input between ALU and data bus
nSP_INC  = 35   # increment the SP register
SP_DIR   = 36   # 0 = INC, 1 = DEC
nSP_LD   = 37   # load data from the address bus to the sp
nSP_OE   = 38   # output SP to the address bus
nSPL_OE  = 39   # output SPL to the data bus
nSPH_OE  = 40   # output SPH to the data bus
SRC_SEL  = 41   # source decoder input. 0 = IR[7:5], 1 = IR[10:8] (for ST zp, reg)
nHALT    = 42   # stops the micro-pc from counting (ENP/ENT of the 74163), so the cpu freezes in the current step
# 43-47 unused


active_low_mask = (
    (1 << nPC_LD)   | (1 << nPCL_OE)  | (1 << nPCH_OE)   |
    (1 << nIRH_LD)  | (1 << nIRL_LD)  | (1 << nIRD_OE)   |
    (1 << nIRA_OE)  | (1 << nHBA_OE)  | (1 << nMPC_RST)  |
    (1 << nMARL_LD) | (1 << nMARH_LD) | (1 << nMAR_OE)   |
    (1 << nMAR_INC) | (1 << nXY_INC)  | (1 << nXYA_OE)   |
    (1 << nA_LD)    | (1 << nSHR_OE)  | (1 << nFL_OE)    |
    (1 << nFLZN_LD) | (1 << nFLCV_LD) | (1 << nSP_INC)   |
    (1 << nSP_LD)   | (1 << nSP_OE)   | (1 << nSPL_OE)   |
    (1 << nSPH_OE)  | (1 << nHALT)
)


def check_condition(sub_opcode, z, c, n, v):
    conditions = {
        0: c,        # JC
        1: not c,    # JNC
        2: z,        # JZ
        3: not z,    # JNZ
        4: n,        # JN
        5: not n,    # JNN
        6: v,        # JV
        7: not v     # JNV
    }
    return conditions.get(sub_opcode, False)


# (base opcode, subOp) pairs with no instruction. they end at step 1, so they work as a NOP
FREE_SLOTS = (
    {(3, sub) for sub in range(2, 8)} |
    {(29, 6), (29, 7)} |
    {(30, 5)} |
    {(31, 3), (31, 4)} |
    {(base, sub) for base in (18, 19, 20) for sub in range(8)}  # old ALU opcodes nothing uses yet
)


# 16 address bits = 64k entries (0x10000)
total_address = 1 << 16

def gen_microcode():
    eprom1 = [0] * total_address
    eprom2 = [0] * total_address
    eprom3 = [0] * total_address

    for addr in range(total_address):
        opcode = addr & 0xFF                 # Bits 0-7
        microstep = (addr >> 8) & 0x0F       # Bits 8-11 (4 bits: 0-15)

        z_flag = bool((addr >> 12) & 1)      # Bit 12
        c_flag = bool((addr >> 13) & 1)      # Bit 13
        n_flag = bool((addr >> 14) & 1)      # Bit 14
        v_flag = bool((addr >> 15) & 1)      # Bit 15

        base_opcode = (opcode >> 3) & 0x1F   # Bits 7:3
        sub_opcode  = opcode & 0x07          # Bits 2:0

        control_word = 0

        if microstep == 0:
            control_word |= (1 << MEM_RD) | (1 << nIRH_LD) | (1 << nIRL_LD)
        else:
            if microstep == 1:
                control_word |= (1 << PC_INC)
                if (base_opcode, sub_opcode) in FREE_SLOTS:
                    control_word |= (1 << nMPC_RST)

            take_jump = check_condition(sub_opcode, z_flag, c_flag, n_flag, v_flag)

            if base_opcode == 0:  # MOV REG
                if microstep == 1:
                    control_word |= (1 << nIRD_OE) | (1 << REG_LD) | (1 << nMPC_RST)

            elif base_opcode == 1:  # MOV REG, REG
                if microstep == 1:
                    control_word |= (1 << REG_OE) | (1 << REG_LD) | (1 << nMPC_RST)

            elif base_opcode == 2:
                if sub_opcode == 0: # MOV MARL, Imm
                    if microstep == 1:
                        control_word |= (1 << nIRD_OE) | (1 << nMARL_LD) | (1 << nMPC_RST)
                elif sub_opcode == 1: # MOV MARH, Imm
                    if microstep == 1:
                        control_word |= (1 << nIRD_OE) | (1 << nMARH_LD) | (1 << nMPC_RST)
                elif sub_opcode == 2: # INC MAR
                    if microstep == 1:
                        control_word |= (1 << nMAR_INC) | (1 << nMPC_RST)
                elif sub_opcode == 3: # DEC MAR
                    if microstep == 1:
                        control_word |= (1 << nMAR_INC) | (1 << MAR_DIR) | (1 << nMPC_RST)
                elif sub_opcode == 4: # INC XY
                    if microstep == 1:
                        control_word |= (1 << nXY_INC) | (1 << nMPC_RST)
                elif sub_opcode == 5: # DEC XY
                    if microstep == 1:
                        control_word |= (1 << nXY_INC) | (1 << XY_DIR) | (1 << nMPC_RST)
                elif sub_opcode == 6: # ST XY+, reg: XY only counts on the clock edge, so the write uses the old XY
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nXYA_OE) | (1 << MEM_WR) | (1 << REG_OE) | (1 << nXY_INC) | (1 << nMPC_RST)
                elif sub_opcode == 7: # ST MAR+, reg
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nMAR_OE) | (1 << MEM_WR) | (1 << REG_OE) | (1 << nMAR_INC) | (1 << nMPC_RST)

            elif base_opcode == 3:
                if sub_opcode == 0: # MOV MARL, REG
                    if microstep == 1:
                        control_word |= (1 << REG_OE) | (1 << nMARL_LD) | (1 << nMPC_RST)
                elif sub_opcode == 1: # MOV MARH, REG
                    if microstep == 1:
                        control_word |= (1 << REG_OE) | (1 << nMARH_LD) | (1 << nMPC_RST)

            elif base_opcode == 4:  # LD reg, Imm
                if microstep == 1:
                    control_word |= (1 << PC_OE) | (1 << nIRA_OE) | (1 << nHBA_OE) | (1 << MEM_RD) | (1 << REG_LD) | (1 << nMPC_RST)

            elif base_opcode == 5:  # LD reg, MAR
                if microstep == 1:
                    control_word |= (1 << PC_OE) | (1 << nMAR_OE) | (1 << MEM_RD) | (1 << REG_LD) | (1 << nMPC_RST)

            elif base_opcode == 6:  # LD reg, XY
                if microstep == 1:
                    control_word |= (1 << PC_OE) | (1 << nXYA_OE) | (1 << MEM_RD) | (1 << REG_LD) | (1 << nMPC_RST)

            elif base_opcode == 7:  # ST zp(imm8), reg
                if microstep == 1: # bits [7:5] are part of the address, so the source register is read from [10:8]
                    control_word |= (1 << PC_OE) | (1 << nIRA_OE) | (1 << nHBA_OE) | (1 << MEM_WR) | (1 << REG_OE) | (1 << SRC_SEL) | (1 << nMPC_RST)

            elif base_opcode == 8:  # ST MAR, reg
                if microstep == 1:
                    control_word |= (1 << PC_OE) | (1 << nMAR_OE) | (1 << MEM_WR) | (1 << REG_OE) | (1 << nMPC_RST)

            elif base_opcode == 9:  # ST XY, reg
                if microstep == 1:
                    control_word |= (1 << PC_OE) | (1 << nXYA_OE) | (1 << MEM_WR) | (1 << REG_OE) | (1 << nMPC_RST)

            elif base_opcode == 10: # PUSH reg
                if microstep == 1:
                    control_word |= (1 << PC_OE) | (1 << REG_OE) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << SP_DIR) | (1 << MEM_WR) | (1 << nMPC_RST)

            elif base_opcode == 11: # POP reg
                if microstep == 1:
                    control_word |= (1 << PC_OE) | (1 << nSP_OE) | (1 << nSP_INC)
                elif microstep == 2:
                    control_word |= (1 << PC_OE) | (1 << REG_LD) | (1 << nSP_OE) | (1 << MEM_RD) | (1 << nMPC_RST)

            elif base_opcode in (12, 13, 14, 15):  # ALU A, REG (12), Imm (13), [zp] (14) and [XY] (15): the subop is the operation
                if microstep == 1:
                    # the operand: a register ([7:5]), the immediate (IR[7:0]), or memory at 0x00:IR[7:0] or at XY
                    if base_opcode == 12:
                        control_word |= (1 << REG_OE)
                    elif base_opcode == 13:
                        control_word |= (1 << nIRD_OE)
                    elif base_opcode == 14:
                        control_word |= (1 << PC_OE) | (1 << nIRA_OE) | (1 << nHBA_OE) | (1 << MEM_RD)
                    else:
                        control_word |= (1 << PC_OE) | (1 << nXYA_OE) | (1 << MEM_RD)
                    # the result goes into A with nA_LD, which doesn't go through the register file's
                    # decoder, so [10:8] can be the subop. CP only loads the flags
                    if sub_opcode != 7:
                        control_word |= (1 << A_SEL) | (1 << nA_LD)
                    # every ALU operation loads Z and N, and the arithmetic ones also C and V
                    control_word |= (1 << nFLZN_LD) | (1 << nMPC_RST)
                    if sub_opcode in (0, 1, 2, 3, 7):
                        control_word |= (1 << nFLCV_LD)

                    if sub_opcode == 0:   # ADD: A + B
                        control_word |= (1 << ALU_S0) | (1 << ALU_S1)
                    elif sub_opcode == 1: # ADC: A + B + C
                        control_word |= (1 << ALU_S0) | (1 << ALU_S1)
                        if c_flag:
                            control_word |= (1 << ALU_CIN)
                    elif sub_opcode == 2: # SUB: A - B (A + not B + 1)
                        control_word |= (1 << ALU_S1) | (1 << ALU_CIN)
                    elif sub_opcode == 3: # SBC: A - B - 1 + C
                        control_word |= (1 << ALU_S1)
                        if c_flag:
                            control_word |= (1 << ALU_CIN)
                    elif sub_opcode == 4: # AND
                        control_word |= (1 << ALU_S1) | (1 << ALU_S2)
                    elif sub_opcode == 5: # OR
                        control_word |= (1 << ALU_S0) | (1 << ALU_S2)
                    elif sub_opcode == 6: # XOR
                        control_word |= (1 << ALU_S2)
                    elif sub_opcode == 7: # CP: A - B, only the flags
                        control_word |= (1 << ALU_S1) | (1 << ALU_CIN)

            elif base_opcode == 16:  # LD reg, XY+ (A-F only: X and Y can't load while XY counts)
                if microstep == 1:
                    control_word |= (1 << PC_OE) | (1 << nXYA_OE) | (1 << MEM_RD) | (1 << REG_LD) | (1 << nXY_INC) | (1 << nMPC_RST)

            elif base_opcode == 17:  # LD reg, MAR+
                if microstep == 1:
                    control_word |= (1 << PC_OE) | (1 << nMAR_OE) | (1 << MEM_RD) | (1 << REG_LD) | (1 << nMAR_INC) | (1 << nMPC_RST)

            elif base_opcode == 21:  # INC A
                if microstep == 1:
                    control_word |= (1 << ALU_S0) | (1 << ALU_S1) | (1 << ALU_CIN) | (1 << nIRD_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFLZN_LD) | (1 << nFLCV_LD) | (1 << nMPC_RST)

            elif base_opcode == 22:  # DEC A
                if microstep == 1:
                    control_word |= (1 << ALU_S1) | (1 << nIRD_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFLZN_LD) | (1 << nFLCV_LD) | (1 << nMPC_RST)

            elif base_opcode == 23:  # SHR A
                if microstep == 1:
                    control_word |= (1 << nSHR_OE) | (1 << REG_LD) | (1 << nMPC_RST)

            elif base_opcode == 24:  # ROR A: A = {C, A[7:1]}. C is part of the microcode address,
                if microstep == 1:   # so bit 7 (SHR_IN0) is set only when C = 1
                    control_word |= (1 << nSHR_OE) | (1 << REG_LD) | (1 << nMPC_RST)
                    if c_flag:
                        control_word |= (1 << SHR_IN0)

            elif base_opcode == 25:  # RET cc: a RET if the condition is true, otherwise it ends at step 1
                if take_jump:
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nSP_OE) | (1 << nSP_INC)
                    elif microstep == 2:
                        control_word |= (1 << PC_OE) | (1 << nMARL_LD) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << MEM_RD)
                    elif microstep == 3:
                        control_word |= (1 << PC_OE) | (1 << nMARH_LD) | (1 << nSP_OE) | (1 << MEM_RD)
                    elif microstep == 4:
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nMAR_OE) | (1 << nMPC_RST)
                elif microstep == 1:
                    control_word |= (1 << nMPC_RST)

            elif base_opcode == 26:  # CALL cc imm16: a CALL if the condition is true, otherwise it skips the second word like JCC
                if take_jump:
                    if microstep == 1: # load high byte into marh (and pc++ automatically)
                        control_word |= (1 << nIRD_OE) | (1 << nMARH_LD)
                    elif microstep == 2: # read second word and store in instruction register
                        control_word |= (1 << MEM_RD) | (1 << nIRH_LD) | (1 << nIRL_LD)
                    elif microstep == 3: # load low byte into marl and pc++ (pc is now the return address)
                        control_word |= (1 << nIRD_OE) | (1 << nMARL_LD) | (1 << PC_INC)
                    elif microstep == 4: # push PCH
                        control_word |= (1 << PC_OE) | (1 << nPCH_OE) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << SP_DIR) | (1 << MEM_WR)
                    elif microstep == 5: # push PCL
                        control_word |= (1 << PC_OE) | (1 << nPCL_OE) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << SP_DIR) | (1 << MEM_WR)
                    elif microstep == 6: # load destination from MAR into PC
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nMAR_OE) | (1 << nMPC_RST)
                elif microstep == 2: # not taken: skip the second word and finish (3 cycles total)
                    control_word |= (1 << PC_INC) | (1 << nMPC_RST)

            elif base_opcode == 27:  # JCC imm16
                take_jump = check_condition(sub_opcode, z_flag, c_flag, n_flag, v_flag)

                if microstep == 1:
                    if take_jump: # load high byte into marh (and pc++ automatically)
                        control_word |= (1 << nIRD_OE) | (1 << nMARH_LD)
                    else: # Branch not taken: Skip Low Byte
                        pass

                elif microstep == 2:
                    if take_jump: # Read second word and store in Instruction Register
                        control_word |= (1 << MEM_RD) | (1 << nIRH_LD) | (1 << nIRL_LD)
                    else: # Branch not taken: Skip High Byte and finish instruction (3 cycles total)
                         control_word |= (1 << PC_INC) | (1 << nMPC_RST)

                elif microstep == 3: # Load low byte into MARL and pc++
                        control_word |= (1 << nIRD_OE) | (1 << nMARL_LD) | (1 << PC_INC)

                elif microstep == 4: # Load destination from MAR into PC
                    control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nMAR_OE) | (1 << nMPC_RST)

            elif base_opcode == 28:  # JCC XY
                if microstep == 1:
                    if take_jump:
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nXYA_OE)
                    control_word |= (1 << nMPC_RST)

            elif base_opcode == 29:  # Unconditional jumps & calls (direct and indirect)
                if sub_opcode == 0: # JMP imm16 (same as a taken JCC imm16)
                    if microstep == 1: # load high byte into marh (and pc++ automatically)
                        control_word |= (1 << nIRD_OE) | (1 << nMARH_LD)
                    elif microstep == 2: # read second word and store in instruction register
                        control_word |= (1 << MEM_RD) | (1 << nIRH_LD) | (1 << nIRL_LD)
                    elif microstep == 3: # load low byte into marl
                        control_word |= (1 << nIRD_OE) | (1 << nMARL_LD)
                    elif microstep == 4: # load destination from MAR into PC
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nMAR_OE) | (1 << nMPC_RST)
                elif sub_opcode == 1: # CALL imm16
                    if microstep == 1: # load high byte into marh (and pc++ automatically)
                        control_word |= (1 << nIRD_OE) | (1 << nMARH_LD)
                    elif microstep == 2: # read second word and store in instruction register
                        control_word |= (1 << MEM_RD) | (1 << nIRH_LD) | (1 << nIRL_LD)
                    elif microstep == 3: # load low byte into marl and pc++ (pc is now the return address)
                        control_word |= (1 << nIRD_OE) | (1 << nMARL_LD) | (1 << PC_INC)
                    elif microstep == 4: # push PCH
                        control_word |= (1 << PC_OE) | (1 << nPCH_OE) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << SP_DIR) | (1 << MEM_WR)
                    elif microstep == 5: # push PCL
                        control_word |= (1 << PC_OE) | (1 << nPCL_OE) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << SP_DIR) | (1 << MEM_WR)
                    elif microstep == 6: # load destination from MAR into PC
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nMAR_OE) | (1 << nMPC_RST)
                elif sub_opcode == 2: # JMP MAR
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nMAR_OE) | (1 << nMPC_RST)
                elif sub_opcode == 3: # JMP XY
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nXYA_OE) | (1 << nMPC_RST)
                elif sub_opcode == 4: # CALL MAR
                    # microstep 1 only does the pc++, so the pushed PC is the return address
                    if microstep == 2: # push PCH
                        control_word |= (1 << PC_OE) | (1 << nPCH_OE) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << SP_DIR) | (1 << MEM_WR)
                    elif microstep == 3: # push PCL
                        control_word |= (1 << PC_OE) | (1 << nPCL_OE) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << SP_DIR) | (1 << MEM_WR)
                    elif microstep == 4:
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nMAR_OE) | (1 << nMPC_RST)
                elif sub_opcode == 5: # CALL XY
                    # microstep 1 only does the pc++, so the pushed PC is the return address
                    if microstep == 2: # push PCH
                        control_word |= (1 << PC_OE) | (1 << nPCH_OE) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << SP_DIR) | (1 << MEM_WR)
                    elif microstep == 3: # push PCL
                        control_word |= (1 << PC_OE) | (1 << nPCL_OE) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << SP_DIR) | (1 << MEM_WR)
                    elif microstep == 4:
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nXYA_OE) | (1 << nMPC_RST)

            elif base_opcode == 30: # Stack Pointer operations
                if sub_opcode == 0: # MOV SP, MAR
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nMAR_OE) | (1 << nSP_LD) | (1 << nMPC_RST)
                elif sub_opcode == 1: # MOV MAR, SP
                    if microstep == 1:
                        control_word |= (1 << nSPL_OE) | (1 << nMARL_LD)
                    elif microstep == 2:
                        control_word |= (1 << nSPH_OE) | (1 << nMARH_LD) | (1 << nMPC_RST)
                elif sub_opcode == 2: # MOV SP, XY
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nXYA_OE) | (1 << nSP_LD) | (1 << nMPC_RST)
                elif sub_opcode == 3: # INC SP
                    if microstep == 1:
                        control_word |= (1 << nSP_INC) | (1 << nMPC_RST)
                elif sub_opcode == 4: # DEC SP
                    if microstep == 1:
                        control_word |= (1 << nSP_INC) | (1 << SP_DIR) | (1 << nMPC_RST)
                elif sub_opcode == 6: # MOV X, SPH
                    if microstep == 1:
                        control_word |= (1 << nSPH_OE) | (1 << REG_LD) | (1 << nMPC_RST)
                elif sub_opcode == 7: # MOV Y, SPL
                    if microstep == 1:
                        control_word |= (1 << nSPL_OE) | (1 << REG_LD) | (1 << nMPC_RST)

            elif base_opcode == 31: # LDT, returns, flags and halt
                if sub_opcode == 0: # LDT A, XY: A = low byte of the ROM word at XY (tables in the ROM)
                    if microstep == 1: # only the IR's low byte loads, so the opcode the EPROMs see stays LDT's
                        control_word |= (1 << PC_OE) | (1 << nXYA_OE) | (1 << MEM_RD) | (1 << nIRL_LD)
                    elif microstep == 2: # [10:8] is 0 (sub-op 0), so REG_LD loads A
                        control_word |= (1 << nIRD_OE) | (1 << REG_LD) | (1 << nMPC_RST)

                elif sub_opcode == 1: # RET
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nSP_OE) | (1 << nSP_INC)
                    elif microstep == 2:
                        control_word |= (1 << PC_OE) | (1 << nMARL_LD) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << MEM_RD)
                    elif microstep == 3:
                        control_word |= (1 << PC_OE) | (1 << nMARH_LD) | (1 << nSP_OE) | (1 << MEM_RD)
                    elif microstep == 4:
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nMAR_OE) | (1 << nMPC_RST)

                elif sub_opcode == 2: # LDT A, XY+: LDT, and XY + 1 at the end
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nXYA_OE) | (1 << MEM_RD) | (1 << nIRL_LD)
                    elif microstep == 2: # [10:8] is 2 here, so REG_LD would load C: A loads with nA_LD instead
                        control_word |= (1 << nIRD_OE) | (1 << nA_LD) | (1 << nXY_INC) | (1 << nMPC_RST)

                elif sub_opcode == 5: # PUSHF
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nFL_OE) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << SP_DIR) | (1 << MEM_WR) | (1 << nMPC_RST)

                elif sub_opcode == 6: # POPF
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nSP_OE) | (1 << nSP_INC)
                    elif microstep == 2:
                        control_word |= (1 << PC_OE) | (1 << nFLZN_LD) | (1 << nFLCV_LD) | (1 << FL_SEL) | (1 << nSP_OE) | (1 << MEM_RD) | (1 << nMPC_RST)

                elif sub_opcode == 7: # HALT
                    # step 1 only does the pc++ (so the pc points to the next instruction)
                    if microstep == 2: # freeze the micro-pc here, with nothing else active (no nMPC_RST, CLR has priority over the enables)
                        control_word |= (1 << nHALT)

        f_control_word = control_word ^ active_low_mask

        eprom1[addr] = f_control_word & 0xFFFF
        eprom2[addr] = (f_control_word >> 16) & 0xFFFF
        eprom3[addr] = (f_control_word >> 32) & 0xFFFF

    return eprom1, eprom2, eprom3


def save_digitalhex(filename, data):
    with open(filename, "w") as f:
        f.write("v2.0 raw\n")
        for val in data:
            f.write(f"{val:04X}\n")

if __name__ == "__main__":
    e1, e2, e3 = gen_microcode()

    save_digitalhex("eprom1.hex", e1)
    save_digitalhex("eprom2.hex", e2)
    save_digitalhex("eprom3.hex", e3)
