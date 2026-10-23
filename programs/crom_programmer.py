# CONTROL BITS

# EPROM 1:
PC_INC   = 0    # increment the pc
nPC_LD   = 1    # load the pc (for jmps)
PC_OE    = 2    # 1 = the pc stops driving the address bus (wired to the active-low OE of its 245s, so by default the pc drives it)
nPCL_OE  = 3    # pc outputs the lower byte to the data bus
nPCH_OE  = 4    # pc outputs the higher byte to the data bus
nIR_LD   = 5    # load the data from ROM the instruction register
nIRD_OE  = 6    # output the lower byte of the ir to the data bus
nIRA_OE  = 7    # output the lower byte of the ir to the address bus (LB)
nHBA_OE  = 8    # forces the higher byte of the address bus to 0x00
nMPC_RST = 9    # reset the microprogram counter (end of instruction)
MEM_RD   = 10   # read memory bus (ROM/RAM/FB/MMIO)
MEM_WR   = 11   # write in memory bus (RAM/FB/MMIO)
nMARL_LD = 12   # load from data bus into the lower byte of the MAR
nMARH_LD = 13   # load from data bus into the higher byte of the MAR
nMAR_OE  = 14   # output the MAR to the address bus
nMAR_INC = 15   # increment the MAR register

# EPROM 2:
MAR_DIR  = 16   # 0 = INC , 1 = DEC
REG_LD   = 17   # register file load enable
REG_OE   = 18   # register file output enable
nXY_INC  = 19   # increment the XY register pair
XY_DIR   = 20   # 0 = INC, 1 = DEC
nXYA_OE  = 21   # XY register pair output to the address bus
A_SEL    = 22   # multiplexor selector for the input of the accumulator. 0 = data bus, 1 = alu
ALU_S0   = 23   # alu select line 0
ALU_S1   = 24   # alu select line 1
ALU_S2   = 25   # alu select line 2
nALU_OE  = 26   # output the result of the alu to the data bus
ALU_CIN  = 27   # carry in on the lowest alu chip
nSHR_OE  = 28   # output a shift right of the accumulator
SHR_IN0  = 29   # bit 0 of the shr buffer; 0 = SHR, 1 = ROR
nFL_OE   = 30   # outputs the flag register to the data bus
nFL_LD   = 31   # loads the flag register

# EPROM 3:
FL_SEL   = 32   # mux that selects the flag register input between ALU and data bus (only first 4 flags)
nSP_INC  = 33   # increment the SP register
SP_DIR   = 34   # 0 = INC, 1 = DEC
nSP_LD   = 35   # load data from the address bus to the sp
nSP_OE   = 36   # output SP to the address bus
nSPL_OE  = 37   # output SPL to the data bus
nSPH_OE  = 38   # output SPH to the data bus
SRC_SEL  = 39   # source decoder input. 0 = IR[7:5], 1 = IR[10:8] (for ST zp, reg)
nHALT    = 40   # stops the micro-pc from counting (ENP/ENT of the 74163), so the cpu freezes in the current step
# 41-47 unused


active_low_mask = (
    (1 << nPC_LD)   | (1 << nPCL_OE)  | (1 << nPCH_OE)   |
    (1 << nIR_LD)   | (1 << nIRD_OE)  | (1 << nIRA_OE)   |
    (1 << nHBA_OE)  | (1 << nMPC_RST) | (1 << nMARL_LD)  |
    (1 << nMARH_LD) | (1 << nMAR_OE)  | (1 << nXY_INC)   |
    (1 << nXYA_OE)  | (1 << nALU_OE)  | (1 << nSHR_OE)   |
    (1 << nFL_OE)   | (1 << nFL_LD)   | (1 << nSP_INC)   |
    (1 << nSP_LD)   | (1 << nSP_OE)   | (1 << nSPL_OE)   |
    (1 << nSPH_OE)  | (1 << nMAR_INC) | (1 << nHALT)
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
    {(2, 6), (2, 7)} |
    {(3, sub) for sub in range(2, 8)} |
    {(29, 6), (29, 7)} |
    {(30, 5)} |
    {(31, 0), (31, 2), (31, 3), (31, 4)}
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
            control_word |= (1 << MEM_RD) | (1 << nIR_LD)
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

            elif base_opcode == 12:  # ADD A, reg
                if microstep == 1:
                    control_word |= (1 << ALU_S0) | (1 << ALU_S1) | (1 << REG_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFL_LD) | (1 << nMPC_RST)

            elif base_opcode == 13:  # ADD A, imm8
                if microstep == 1:
                    control_word |= (1 << ALU_S0) | (1 << ALU_S1) | (1 << nIRD_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFL_LD) | (1 << nMPC_RST)

            elif base_opcode == 14:  # ADC A, reg
                if microstep == 1:
                    control_word |= (1 << ALU_S0) | (1 << ALU_S1) | (1 << REG_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFL_LD) | (1 << nMPC_RST)
                    if c_flag:
                        control_word |= (1 << ALU_CIN)

            elif base_opcode == 15:  # SUB A, reg
                if microstep == 1:
                    control_word |= (1 << ALU_S1) | (1 << ALU_CIN) | (1 << REG_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFL_LD) | (1 << nMPC_RST)

            elif base_opcode == 16:  # SBC A, reg
                if microstep == 1:
                    control_word |= (1 << ALU_S1) | (1 << REG_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFL_LD) | (1 << nMPC_RST)
                    if c_flag:
                        control_word |= (1 << ALU_CIN)

            elif base_opcode == 17:  # AND A, reg
                if microstep == 1:
                    control_word |= (1 << ALU_S1) | (1 << ALU_S2) | (1 << REG_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFL_LD) | (1 << nMPC_RST)

            elif base_opcode == 18:  # AND A, imm8
                if microstep == 1:
                    control_word |= (1 << ALU_S1) | (1 << ALU_S2) | (1 << nIRD_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFL_LD) | (1 << nMPC_RST)

            elif base_opcode == 19:  # OR A, reg
                if microstep == 1:
                    control_word |= (1 << ALU_S0) | (1 << ALU_S2) | (1 << REG_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFL_LD) | (1 << nMPC_RST)

            elif base_opcode == 20:  # XOR A, reg
                if microstep == 1:
                    control_word |= (1 << ALU_S2) | (1 << REG_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFL_LD) | (1 << nMPC_RST)

            elif base_opcode == 21:  # INC A
                if microstep == 1:
                    control_word |= (1 << ALU_S0) | (1 << ALU_S1) | (1 << ALU_CIN) | (1 << nIRD_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFL_LD) | (1 << nMPC_RST)

            elif base_opcode == 22:  # DEC A
                if microstep == 1:
                    control_word |= (1 << ALU_S1) | (1 << nIRD_OE) | (1 << REG_LD) | (1 << A_SEL) | (1 << nFL_LD) | (1 << nMPC_RST)

            elif base_opcode == 23:  # SHR A
                if microstep == 1:
                    control_word |= (1 << nSHR_OE) | (1 << REG_LD) | (1 << nMPC_RST)

            elif base_opcode == 24:  # ROR A
                if microstep == 1:
                    control_word |= (1 << nSHR_OE) | (1 << REG_LD) | (1 << nMPC_RST)

            elif base_opcode == 25:  # CP A, reg
                if microstep == 1:
                    control_word |= (1 << ALU_S1) | (1 << ALU_CIN) | (1 << REG_OE) | (1 << nFL_LD) | (1 << nMPC_RST)

            elif base_opcode == 26:  # CP A, imm
                if microstep == 1:
                    control_word |= (1 << ALU_S1) | (1 << ALU_CIN) | (1 << nIRD_OE) | (1 << nFL_LD) | (1 << nMPC_RST)

            elif base_opcode == 27:  # JCC imm16
                take_jump = check_condition(sub_opcode, z_flag, c_flag, n_flag, v_flag)

                if microstep == 1:
                    if take_jump: # load high byte into marh (and pc++ automatically)
                        control_word |= (1 << nIRD_OE) | (1 << nMARH_LD)
                    else: # Branch not taken: Skip Low Byte
                        pass

                elif microstep == 2:
                    if take_jump: # Read second word and store in Instruction Register
                        control_word |= (1 << MEM_RD) | (1 << nIR_LD)
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
                        control_word |= (1 << MEM_RD) | (1 << nIR_LD)
                    elif microstep == 3: # load low byte into marl
                        control_word |= (1 << nIRD_OE) | (1 << nMARL_LD)
                    elif microstep == 4: # load destination from MAR into PC
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nMAR_OE) | (1 << nMPC_RST)
                elif sub_opcode == 1: # CALL imm16
                    if microstep == 1: # load high byte into marh (and pc++ automatically)
                        control_word |= (1 << nIRD_OE) | (1 << nMARH_LD)
                    elif microstep == 2: # read second word and store in instruction register
                        control_word |= (1 << MEM_RD) | (1 << nIR_LD)
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

            elif base_opcode == 31: # Returns, flags and halt
                if sub_opcode == 1: # RET
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nSP_OE) | (1 << nSP_INC)
                    elif microstep == 2:
                        control_word |= (1 << PC_OE) | (1 << nMARL_LD) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << MEM_RD)
                    elif microstep == 3:
                        control_word |= (1 << PC_OE) | (1 << nMARH_LD) | (1 << nSP_OE) | (1 << MEM_RD)
                    elif microstep == 4:
                        control_word |= (1 << PC_OE) | (1 << nPC_LD) | (1 << nMAR_OE) | (1 << nMPC_RST)

                elif sub_opcode == 5: # PUSHF
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nFL_OE) | (1 << nSP_OE) | (1 << nSP_INC) | (1 << SP_DIR) | (1 << MEM_WR) | (1 << nMPC_RST)

                elif sub_opcode == 6: # POPF
                    if microstep == 1:
                        control_word |= (1 << PC_OE) | (1 << nSP_OE) | (1 << nSP_INC)
                    elif microstep == 2:
                        control_word |= (1 << PC_OE) | (1 << nFL_LD) | (1 << nSP_OE) | (1 << MEM_RD) | (1 << nMPC_RST)

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
