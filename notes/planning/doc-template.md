temporal file to structure how each module will be documented:

1. Module Overview and Pinouts
   - summary of what the module does
   - interactions with buses (control, data, address)
   - table listing inputs, outputs and control line (bit-width, direction (in/out/tristate), active polarity (active-high/active-low))

2. Internal architecture and data path
   - block diagram
   - simulation schematic (digital)

3. Control signals and operation logic
   - table showing how control signals configure operations
   - status and flag generation (for alu)

4. Timing, latches and critical paths
   - details about clock sensitivity (like the load for the 74191)
   - critical path delays showing the propagation delays in simulation to calculate max theoretical clock freq and prevent race conditions

5. Verification and testbench results
   - (learn how to use) test cases in digital
   - glitches or bugs during simulation (if there are)

6. Physical TTL mapping
   - exact IC chips required for the real breadboard implementation
   - maybe the digital schematic with those ICs