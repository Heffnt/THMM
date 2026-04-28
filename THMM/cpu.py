"""
THMM CPU simulator.

See AGENTS.md for the "why" behind the design, and docs/datapath.svg for
the canonical schematic. Every local variable in tick() is a labeled wire
on that diagram; every function in this file is one block on it.

Signals are bit strings (Python `str` of '0' and '1') of fixed width.
Width suffixes on variable names (`pc8`, `ir16`, `acc_zero1`, `alu_op3`)
document what each wire carries. Width 1 for control signals and flags,
3 for the ALU opcode, 4 for the instruction opcode field, 8 for addresses,
16 for data words.

File layout:
    1. Width helpers
    2. Combinational components (gates, muxes, ALU, decoder, RAM read, zero)
    3. Edge-triggered updates (PC counter, IR/Acc registers, RAM write,
       phase flip-flop, halt latch)
    4. State construction and program loading
    5. The tick loop
    6. The run loop
"""


# ==========================================================================
# 1. WIDTH HELPERS
# ==========================================================================
#
# These are the only places in the file that convert between bit strings
# and Python ints. Any time a component needs to perform arithmetic it goes
# through here, then back out to a bit string of the declared width.

def zeros(width):
    """A bit string of `width` zeros."""
    return '0' * width


def from_int(value, width):
    """Convert a Python int to a bit string of the given width.

    Negative values are two's-complement-wrapped, so `from_int(-1, 8)`
    returns '11111111'. Values outside the width silently wrap — the same
    thing a wire of that width would do in hardware.
    """
    masked = value & ((1 << width) - 1)
    return format(masked, f'0{width}b')


def to_uint(bitstr):
    """Interpret a bit string as an unsigned int."""
    return int(bitstr, 2)


def to_sint(bitstr):
    """Interpret a bit string as a signed two's-complement int."""
    width = len(bitstr)
    u = int(bitstr, 2)
    if u & (1 << (width - 1)):
        return u - (1 << width)
    return u


# ==========================================================================
# 2. COMBINATIONAL COMPONENTS
# ==========================================================================
#
# Every function here is pure — output depends only on inputs, no state
# is read or written. These are the "combinational cloud" of the datapath:
# gates, muxes, the ALU, the decoder, and the RAM read port.

def and2(a1, b1):
    """2-input AND gate."""
    return '1' if a1 == '1' and b1 == '1' else '0'


def not1(a1):
    """Inverter."""
    return '0' if a1 == '1' else '1'


def nor16(v16):
    """16-input NOR. Outputs '1' iff every bit of v16 is '0'.

    This is the zero-detect across the Accumulator. Its output feeds back
    into the decoder so goif0 can make its branch decision (see decoder()).
    """
    return '1' if all(b == '0' for b in v16) else '0'


def mux2_8(sel1, in0_8, in1_8):
    """2-to-1 multiplexer, 8-bit data path."""
    return in1_8 if sel1 == '1' else in0_8


def mux2_16(sel1, in0_16, in1_16):
    """2-to-1 multiplexer, 16-bit data path."""
    return in1_16 if sel1 == '1' else in0_16


def alu(a16, b16, op3):
    """16-bit ALU.

    Opcodes (matching the spec table):
        '000'  Pass  — output = b           (used for loadm / loadn / goto)
        '001'  Add   — output = a + b
        '010'  Sub   — output = a - b
        '011'  Mul   — output = a * b
        '100'  Div   — output = a / b, or 0 if b == 0

    Arithmetic is signed two's complement. Overflow wraps silently, which
    is what a fixed-width adder does in hardware. Division truncates toward
    zero (C-style), not toward negative infinity (which is Python's default).
    """
    a = to_sint(a16)
    b = to_sint(b16)

    if op3 == '000':            # Pass: output = b, ignore a
        result = b
    elif op3 == '001':          # Add
        result = a + b
    elif op3 == '010':          # Sub
        result = a - b
    elif op3 == '011':          # Mul
        result = a * b
    elif op3 == '100':          # Div
        if b == 0:
            # Divide-by-zero policy (see AGENTS.md): yield 0 so the sim
            # stays deterministic. Real hardware would produce whatever
            # the Logisim divider does on that input.
            result = 0
        else:
            # Python's `//` is floor division: -7 // 2 == -4. We want
            # C-style truncation toward zero (-7 / 2 == -3) to match how
            # a signed divider circuit typically behaves.
            q = abs(a) // abs(b)
            if (a < 0) != (b < 0):
                q = -q
            result = q
    else:
        # Unreachable given a well-formed 3-bit opcode.
        result = 0

    return from_int(result, 16)


def decoder(ir16, acc_zero1):
    """Instruction decoder — purely combinational.

    Takes the current IR and the Accumulator's zero flag; emits every
    control + data signal that drives the rest of the datapath.

    The implementation is a flat if/elif chain, one branch per opcode,
    mirroring the spec table row-for-row so the correspondence to the
    documentation stays grep-able. Do not fold into a lookup dict — the
    line-per-row structure is the point.

    The WE outputs returned here have NOT yet been gated by Phase. The
    caller is responsible for ANDing prog_we1, ram_we1, acc_we1 with
    phase1 so writes only fire during the execute half of the cycle.
    Those AND gates are drawn explicitly on the schematic.

    Returns, in schematic pin order:
        prog_we1, prog_mux1, ram_we1,
        alu_mux1, alu_op3, acc_we1,
        halt1, ram_data8, alu_data16
    """
    opcode = ir16[0:4]          # IR[15:12]
    n8 = ir16[8:16]             # IR[7:0]  — the operand/address field

    # Defaults: the nop row. Any opcode that doesn't explicitly override
    # a signal leaves it at its nop value.
    prog_we1   = '0'
    prog_mux1  = '0'
    ram_we1    = '0'
    alu_mux1   = '0'
    alu_op3    = '000'
    acc_we1    = '0'
    halt1      = '0'

    # The decoder always drives the n field onto its two data outputs.
    # Whether the downstream Address Mux / ALU B Mux actually uses them
    # depends on sel lines (Phase and AluMux respectively).
    ram_data8  = n8
    alu_data16 = zeros(8) + n8

    if opcode == '0000':        # nop
        pass

    elif opcode == '0001':      # halt
        halt1 = '1'

    elif opcode == '0010':      # loadm n   — Acc <- RAM[n]
        alu_mux1 = '1'          # ALU B from RAM Dout
        alu_op3  = '000'        # Pass it through
        acc_we1  = '1'

    elif opcode == '0011':      # loadn n   — Acc <- n
        alu_mux1 = '0'          # ALU B from immediate n
        alu_op3  = '000'        # Pass it through
        acc_we1  = '1'

    elif opcode == '0100':      # store n   — RAM[n] <- Acc
        ram_we1 = '1'

    elif opcode == '0101':      # goto n    — PC <- n
        prog_we1  = '1'
        prog_mux1 = '1'         # PC target from ALU (which passes n)
        alu_mux1  = '0'
        alu_op3   = '000'

    elif opcode == '0110':      # gotoa     — PC <- Acc[7:0]
        prog_we1  = '1'
        prog_mux1 = '0'         # PC target from Acc low byte

    elif opcode == '0111':      # addm n    — Acc <- Acc + RAM[n]
        alu_mux1 = '1'
        alu_op3  = '001'        # Add
        acc_we1  = '1'

    elif opcode == '1000':      # addn n    — Acc <- Acc + n
        alu_mux1 = '0'
        alu_op3  = '001'        # Add
        acc_we1  = '1'

    elif opcode == '1001':      # goif0 n   — PC <- n iff Acc == 0
        # The conditional jump is absorbed into ProgWE here — no extra
        # decoder output pin, just a one-gate dependency on acc_zero.
        # If Acc is zero, the jump is armed; otherwise it's suppressed.
        prog_we1  = acc_zero1
        prog_mux1 = '1'         # target from ALU (passes n)
        alu_mux1  = '0'
        alu_op3   = '000'

    elif opcode == '1010':      # subm n    — Acc <- Acc - RAM[n]
        alu_mux1 = '1'
        alu_op3  = '010'        # Sub
        acc_we1  = '1'

    elif opcode == '1011':      # mulm n    — Acc <- Acc * RAM[n]
        alu_mux1 = '1'
        alu_op3  = '011'        # Mul
        acc_we1  = '1'

    elif opcode == '1100':      # divm n    — Acc <- Acc / RAM[n]
        alu_mux1 = '1'
        alu_op3  = '100'        # Div
        acc_we1  = '1'

    # Opcodes 1101..1111 are unused and fall through with nop defaults.

    return (prog_we1, prog_mux1, ram_we1,
            alu_mux1, alu_op3, acc_we1,
            halt1, ram_data8, alu_data16)


def ram_read(ram_cells, addr8):
    """Combinational RAM read. Returns the 16-bit word at `addr8`.

    `ram_cells` is a plain list of 256 bit strings; we index it by the
    decimal value of the address. Read is always valid — writes are
    separately gated by RamWE in `ram_write()`.
    """
    return ram_cells[to_uint(addr8)]


# ==========================================================================
# 3. EDGE-TRIGGERED UPDATES
# ==========================================================================
#
# Each of these is called at most once per tick, during the edge pass.
# They compute the next value of a stateful component given its current
# value plus its control inputs. The register/memory mutation itself is
# done by tick() assigning the return value back into `state`.

def pc_next(pc8, ct1, ld1, d8):
    """PC Counter — 8-bit.

    Logisim Counter semantics: LD dominates CT. If load is asserted, the
    counter takes D. Else if count is asserted, it increments (with wrap).
    Else it holds. Both enables may be low and the PC simply doesn't move.
    """
    if ld1 == '1':
        return d8
    elif ct1 == '1':
        return from_int(to_uint(pc8) + 1, 8)    # 8-bit wrap is automatic
    else:
        return pc8


def ir_next(ir16, we1, din16):
    """D flip-flop with write enable — the Instruction Register."""
    return din16 if we1 == '1' else ir16


def acc_next(acc16, we1, din16):
    """D flip-flop with write enable — the Accumulator."""
    return din16 if we1 == '1' else acc16


def ram_write(ram_cells, addr8, din16, we1):
    """Edge-triggered RAM write. Mutates `ram_cells` in place iff we=1."""
    if we1 == '1':
        ram_cells[to_uint(addr8)] = din16


def phase_toggle(phase1):
    """T flip-flop — toggles every (ungated) clock edge."""
    return not1(phase1)


def halt_latch_next(halted1, set1):
    """Halt latch. Once set, stays set — reset requires an external signal
    that we don't model (the user would power-cycle the circuit).
    """
    return '1' if set1 == '1' else halted1


# ==========================================================================
# 4. STATE + PROGRAM LOADING
# ==========================================================================

def init_state():
    """Reset: PC=0, IR=0, Acc=0, phase=0 (fetch), halt=0, RAM zeroed."""
    return {
        'pc':     zeros(8),
        'ir':     zeros(16),
        'acc':    zeros(16),
        'phase':  zeros(1),
        'halted': zeros(1),
        'ram':    [zeros(16) for _ in range(256)],
    }


def load_program(state, program):
    """Copy a list of 16-bit strings into RAM starting at address 0.

    We insist on bit strings (not ints) because that's the representation
    used on wires, and keeping the program listing in the same form keeps
    the source honest about what's actually in memory.
    """
    for i, word in enumerate(program):
        assert len(word) == 16, \
            f"Program word {i} is not 16 bits: {word!r}"
        assert all(c in '01' for c in word), \
            f"Program word {i} has non-bit chars: {word!r}"
        state['ram'][i] = word


# ==========================================================================
# 5. THE TICK LOOP
# ==========================================================================

def tick(state):
    """One clock edge. One instruction is exactly two ticks (fetch, execute).

    Read this function with docs/datapath.svg open. Every local variable
    here is a labeled wire on that diagram. The function has two passes:

        (a) Combinational pass — trace every wire from the register outputs
            through the cloud of gates/muxes/ALU/decoder to the edge inputs.
        (b) Edge pass — commit the register and memory updates.

    The passes are strictly sequential: no update in (b) observes a value
    from (b). That's how the real circuit behaves — every register samples
    the combinational value that was stable just before the rising edge.
    """
    # --- Read current register outputs ---
    pc8     = state['pc']
    ir16    = state['ir']
    acc16   = state['acc']
    phase1  = state['phase']
    halted1 = state['halted']

    # --- (a) Combinational pass ---

    # Acc zero detect. Its output is one input to the decoder (for goif0).
    acc_zero1 = nor16(acc16)

    # Decoder. Raw WE outputs are PRE-phase-gating; see below.
    (prog_we_raw1, prog_mux1, ram_we_raw1,
     alu_mux1, alu_op3, acc_we_raw1,
     halt1, ram_data8, alu_data16) = decoder(ir16, acc_zero1)

    # Explicit AND gates between decoder and write-enables. These are
    # drawn on the schematic as separate gate symbols — the decoder is
    # unaware of Phase, and these gates are where the execute-only
    # semantics of the WE signals actually come from.
    prog_we1 = and2(prog_we_raw1, phase1)
    ram_we1  = and2(ram_we_raw1,  phase1)
    acc_we1  = and2(acc_we_raw1,  phase1)

    # IR's write-enable is not a decoder output. It's wired directly to
    # !phase, so IR latches only at the end of fetch.
    ir_we1 = not1(phase1)

    # Address Mux: PC during fetch, Ram Data (decoder's n output) during execute.
    addr8 = mux2_8(phase1, pc8, ram_data8)

    # RAM read is combinational and always happens — whether the result is
    # used depends on what else is going on this cycle.
    ram_dout16 = ram_read(state['ram'], addr8)

    # ALU B Mux: immediate (from decoder) or RAM Dout.
    alu_b16 = mux2_16(alu_mux1, alu_data16, ram_dout16)

    # ALU.
    alu_out16 = alu(acc16, alu_b16, alu_op3)

    # ProgMux: source for the PC load value. 0 = Acc low byte (gotoa),
    # 1 = ALU low byte (goto and goif0, where the ALU passes n through).
    prog_target8 = mux2_8(prog_mux1, acc16[8:16], alu_out16[8:16])

    # PC Counter's CT input. It counts during fetch (phase=0) and not
    # during execute — on execute, PC only changes via LD (for jumps).
    pc_ct1 = not1(phase1)

    # --- (b) Edge pass ---
    #
    # When the halt latch is already set the gated clock is dead, so the
    # main registers don't update. The halt latch itself is re-evaluated
    # below — it stays latched once set.

    if halted1 != '1':
        state['ir']    = ir_next(ir16, ir_we1, ram_dout16)
        state['acc']   = acc_next(acc16, acc_we1, alu_out16)
        ram_write(state['ram'], ram_data8, acc16, ram_we1)
        state['pc']    = pc_next(pc8, pc_ct1, prog_we1, prog_target8)
        state['phase'] = phase_toggle(phase1)

    # The halt latch is set only when the decoded instruction is `halt`
    # AND we are actually in the execute phase. Gating prevents spurious
    # halts during fetch, where IR still holds the previous instruction.
    state['halted'] = halt_latch_next(halted1, and2(halt1, phase1))


# ==========================================================================
# 6. THE RUN LOOP
# ==========================================================================

def run(state, max_cycles=10000):
    """Tick until halted or until a cycle budget is reached.

    The budget is a safety net for buggy programs. Real hardware doesn't
    have one. Returns the number of cycles executed.
    """
    for cycles in range(max_cycles):
        if state['halted'] == '1':
            return cycles
        tick(state)
    return max_cycles
