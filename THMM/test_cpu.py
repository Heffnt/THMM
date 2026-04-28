"""
Tests for the THMM CPU simulator.

Four layers, building up in confidence (see AGENTS.md):
    1. Combinational components (truth tables)
    2. Stateful-component semantics (counter, registers, latches)
    3. Per-instruction end-to-end (load a tiny program, run to halt)
    4. Full fib program

Runnable either as `python test_cpu.py` (uses the __main__ block below) or
as `pytest test_cpu.py` — the tests are plain functions that assert.
"""

from cpu import (
    # width helpers
    zeros, from_int, to_uint, to_sint,
    # combinational
    and2, not1, nor16, mux2_8, mux2_16, alu, decoder, ram_read,
    # edge updates
    pc_next, ir_next, acc_next, ram_write, phase_toggle, halt_latch_next,
    # state + tick + run
    init_state, load_program, tick, run,
)
from fib import FIB_PROGRAM


# ==========================================================================
# Layer 1: combinational components
# ==========================================================================

def test_and2_truth_table():
    assert and2('0', '0') == '0'
    assert and2('0', '1') == '0'
    assert and2('1', '0') == '0'
    assert and2('1', '1') == '1'


def test_not1_truth_table():
    assert not1('0') == '1'
    assert not1('1') == '0'


def test_nor16_all_zero_input():
    # The only input value that makes NOR output '1'.
    assert nor16('0' * 16) == '1'


def test_nor16_any_one_bit_kills_it():
    assert nor16('0' * 15 + '1') == '0'
    assert nor16('1' + '0' * 15) == '0'
    assert nor16('0001000100010001') == '0'


def test_mux2_8_selects_correctly():
    a = '00001111'
    b = '11110000'
    assert mux2_8('0', a, b) == a
    assert mux2_8('1', a, b) == b


def test_mux2_16_selects_correctly():
    a = '0' * 16
    b = '1' * 16
    assert mux2_16('0', a, b) == a
    assert mux2_16('1', a, b) == b


def test_alu_pass_ignores_a():
    # Pass outputs B regardless of A — verifies A is not silently added.
    assert alu(from_int(0xABCD, 16), from_int(42, 16), '000') == from_int(42, 16)


def test_alu_add_and_wrap():
    assert alu(from_int(5, 16), from_int(3, 16), '001') == from_int(8, 16)
    # 0x7FFF + 1 wraps to 0x8000 (most negative signed 16b).
    assert alu(from_int(0x7FFF, 16), from_int(1, 16), '001') == from_int(0x8000, 16)


def test_alu_sub_can_go_negative():
    assert alu(from_int(5, 16), from_int(3, 16), '010') == from_int(2, 16)
    # 3 - 5 = -2 → 0xFFFE in two's complement
    assert alu(from_int(3, 16), from_int(5, 16), '010') == from_int(-2, 16)


def test_alu_mul():
    assert alu(from_int(4, 16), from_int(5, 16), '011') == from_int(20, 16)


def test_alu_div_truncates_toward_zero():
    assert alu(from_int(20, 16), from_int(4, 16), '100') == from_int(5, 16)
    # -7 / 2 → -3 (truncate toward zero), NOT -4 (floor).
    assert alu(from_int(-7, 16), from_int(2, 16), '100') == from_int(-3, 16)


def test_alu_div_by_zero_returns_zero():
    # Deterministic policy — see AGENTS.md.
    assert alu(from_int(42, 16), from_int(0, 16), '100') == from_int(0, 16)


# ----- Decoder ------------------------------------------------------------

def _decode(opcode_bits, n_bits='00000000', acc_zero='0'):
    """Helper: build a 16-bit IR from opcode + n and run the decoder."""
    ir = opcode_bits + '0000' + n_bits
    return decoder(ir, acc_zero)


def test_decoder_nop_drives_no_enables():
    (prog_we, _, ram_we, _, _, acc_we, halt, _, _) = _decode('0000')
    assert (prog_we, ram_we, acc_we, halt) == ('0', '0', '0', '0')


def test_decoder_halt():
    (*_, halt, _, _) = _decode('0001')
    assert halt == '1'


def test_decoder_loadm_routes_ram_to_acc():
    # loadm: Acc <- RAM[n] → Alu Mux=1 (RAM), Alu Op=Pass, Acc WE=1.
    (prog_we, _, ram_we, alu_mux, alu_op, acc_we,
     halt, ram_data, _) = _decode('0010', '00010101')
    assert (prog_we, ram_we, acc_we, halt) == ('0', '0', '1', '0')
    assert alu_mux == '1'
    assert alu_op == '000'
    assert ram_data == '00010101'      # n passed onto the Ram Data bus


def test_decoder_store_asserts_ram_we():
    (_, _, ram_we, _, _, acc_we, _, ram_data, _) = _decode('0100', '00010001')
    assert ram_we == '1'
    assert acc_we == '0'
    assert ram_data == '00010001'


def test_decoder_goif0_branch_taken_when_acc_zero():
    (prog_we, prog_mux, *_) = _decode('1001', '00000011', acc_zero='1')
    assert prog_we == '1'
    assert prog_mux == '1'             # target comes from ALU


def test_decoder_goif0_branch_suppressed_when_acc_nonzero():
    (prog_we, *_) = _decode('1001', '00000011', acc_zero='0')
    assert prog_we == '0'


def test_decoder_gotoa_takes_target_from_acc():
    (prog_we, prog_mux, *_) = _decode('0110')
    assert prog_we == '1'
    assert prog_mux == '0'             # target comes from Acc


# ==========================================================================
# Layer 2: stateful-component semantics
# ==========================================================================

def test_pc_counter_counts_when_ct():
    assert pc_next('00000000', ct1='1', ld1='0', d8='00000000') == '00000001'


def test_pc_counter_loads_when_ld():
    assert pc_next('00000000', ct1='0', ld1='1', d8='10101010') == '10101010'


def test_pc_counter_holds_when_neither():
    assert pc_next('00001111', ct1='0', ld1='0', d8='00000000') == '00001111'


def test_pc_counter_load_dominates_count():
    # Logisim Counter: both enables high → load wins.
    assert pc_next('00000000', ct1='1', ld1='1', d8='11110000') == '11110000'


def test_pc_counter_wraps_at_8_bits():
    assert pc_next('11111111', ct1='1', ld1='0', d8='00000000') == '00000000'


def test_ir_register_write_enable():
    assert ir_next('0' * 16, '1', '1' * 16) == '1' * 16
    assert ir_next('1' * 16, '0', '0' * 16) == '1' * 16     # holds when we=0


def test_acc_register_write_enable():
    assert acc_next('0' * 16, '1', '1' * 16) == '1' * 16
    assert acc_next('1' * 16, '0', '0' * 16) == '1' * 16


def test_phase_toggles():
    assert phase_toggle('0') == '1'
    assert phase_toggle('1') == '0'


def test_halt_latch_sets_and_persists():
    assert halt_latch_next('0', '1') == '1'   # set
    assert halt_latch_next('1', '0') == '1'   # already-set persists
    assert halt_latch_next('0', '0') == '0'   # idle


def test_ram_read_and_write():
    cells = [zeros(16) for _ in range(256)]
    ram_write(cells, '00000011', from_int(0xBEEF, 16), '1')
    assert ram_read(cells, '00000011') == from_int(0xBEEF, 16)
    # WE=0 is a no-op.
    ram_write(cells, '00000011', from_int(0, 16), '0')
    assert ram_read(cells, '00000011') == from_int(0xBEEF, 16)


# ==========================================================================
# Layer 3: per-instruction end-to-end (each test runs a tiny program to halt)
# ==========================================================================

def _setup(program, ram_seed=None, acc_seed=None):
    """Build state, load program, optionally seed RAM/Acc, return state."""
    state = init_state()
    load_program(state, program)
    if ram_seed:
        for addr, val in ram_seed.items():
            state['ram'][addr] = val
    if acc_seed is not None:
        state['acc'] = acc_seed
    return state


def test_loadn_sets_acc():
    program = [
        "0011000000101010",   # loadn 42
        "0001000000000000",   # halt
    ]
    state = _setup(program)
    run(state, max_cycles=20)
    assert to_uint(state['acc']) == 42
    assert state['halted'] == '1'


def test_loadm_reads_ram():
    program = [
        "0010000000000011",   # loadm 3
        "0001000000000000",   # halt
    ]
    state = _setup(program, ram_seed={3: from_int(0xBEEF, 16)})
    run(state, max_cycles=20)
    assert to_uint(state['acc']) == 0xBEEF


def test_store_writes_ram():
    program = [
        "0011000000000111",   # loadn 7
        "0100000000000101",   # store 5
        "0001000000000000",   # halt
    ]
    state = _setup(program)
    run(state, max_cycles=20)
    assert to_uint(state['ram'][5]) == 7


def test_addn_adds_immediate_to_acc():
    program = [
        "0011000000000101",   # loadn 5
        "1000000000000011",   # addn 3
        "0001000000000000",   # halt
    ]
    state = _setup(program)
    run(state, max_cycles=20)
    assert to_uint(state['acc']) == 8


def test_addm_adds_ram_to_acc():
    program = [
        "0011000000000101",   # loadn 5
        "0111000000000100",   # addm 4
        "0001000000000000",   # halt
    ]
    state = _setup(program, ram_seed={4: from_int(10, 16)})
    run(state, max_cycles=20)
    assert to_uint(state['acc']) == 15


def test_subm_can_go_negative():
    program = [
        "0011000000000011",   # loadn 3
        "1010000000000100",   # subm 4   — RAM[4]=5 → acc = 3-5 = -2
        "0001000000000000",   # halt
    ]
    state = _setup(program, ram_seed={4: from_int(5, 16)})
    run(state, max_cycles=20)
    # -2 in 16-bit two's complement is 0xFFFE.
    assert state['acc'] == from_int(-2, 16)
    assert to_uint(state['acc']) == 0xFFFE


def test_mulm():
    program = [
        "0011000000000110",   # loadn 6
        "1011000000000100",   # mulm 4
        "0001000000000000",   # halt
    ]
    state = _setup(program, ram_seed={4: from_int(7, 16)})
    run(state, max_cycles=20)
    assert to_uint(state['acc']) == 42


def test_divm_by_zero_yields_zero():
    # RAM[4] defaults to 0. Divide 42 by 0 → 0 per policy.
    program = [
        "0011000000101010",   # loadn 42
        "1100000000000100",   # divm 4
        "0001000000000000",   # halt
    ]
    state = _setup(program)
    run(state, max_cycles=20)
    assert to_uint(state['acc']) == 0


def test_goto_skips_code():
    program = [
        "0101000000000011",   # 0: goto 3
        "0011000011111111",   # 1: loadn 255  (skipped)
        "0001000000000000",   # 2: halt       (skipped)
        "0011000000000001",   # 3: loadn 1
        "0001000000000000",   # 4: halt
    ]
    state = _setup(program)
    run(state, max_cycles=20)
    assert to_uint(state['acc']) == 1


def test_goif0_branches_when_acc_zero():
    # Acc starts at 0, so the branch is taken.
    program = [
        "1001000000000011",   # 0: goif0 3
        "0011000011111111",   # 1: loadn 255  (skipped)
        "0001000000000000",   # 2: halt       (skipped)
        "0011000000000001",   # 3: loadn 1
        "0001000000000000",   # 4: halt
    ]
    state = _setup(program)
    run(state, max_cycles=20)
    assert to_uint(state['acc']) == 1


def test_goif0_falls_through_when_acc_nonzero():
    program = [
        "0011000000000111",   # 0: loadn 7     (acc = 7)
        "1001000000000100",   # 1: goif0 4     (not taken)
        "0011000000000011",   # 2: loadn 3
        "0001000000000000",   # 3: halt
        "0001000000000000",   # 4: halt (unreached)
    ]
    state = _setup(program)
    run(state, max_cycles=20)
    assert to_uint(state['acc']) == 3


def test_gotoa_loads_pc_from_acc_low_byte():
    program = [
        "0110000000000000",   # 0: gotoa — Acc seeded to 4, so PC <- 4
        "0001000000000000",   # 1: halt (skipped)
        "0001000000000000",   # 2: halt (skipped)
        "0001000000000000",   # 3: halt (skipped)
        "0011000000000111",   # 4: loadn 7
        "0001000000000000",   # 5: halt
    ]
    state = _setup(program, acc_seed=from_int(4, 16))
    run(state, max_cycles=20)
    assert to_uint(state['acc']) == 7


def test_halt_freezes_state():
    program = [
        "0001000000000000",   # halt
    ]
    state = _setup(program)
    run(state, max_cycles=20)
    assert state['halted'] == '1'

    # Additional ticks after halt should not change anything.
    snapshot = (state['pc'], state['ir'], state['acc'], state['phase'])
    tick(state)
    tick(state)
    assert (state['pc'], state['ir'], state['acc'], state['phase']) == snapshot
    assert state['halted'] == '1'


# ==========================================================================
# Layer 4: end-to-end fib
# ==========================================================================

def test_fib_halts_within_budget():
    state = init_state()
    load_program(state, FIB_PROGRAM)
    cycles = run(state, max_cycles=500)
    assert state['halted'] == '1'
    assert cycles < 500                # actually halted, didn't hit budget


def test_fib_result_is_8():
    # n = 5 → loop runs 5 times → A becomes F(6) = 8 under F(1)=F(2)=1.
    state = init_state()
    load_program(state, FIB_PROGRAM)
    run(state, max_cycles=500)
    assert to_uint(state['acc']) == 8


# ==========================================================================
# Layer 5: end-to-end, compiler + simulator
# ==========================================================================
#
# Compile THCC's regression.thcc example with the Haskell compiler, load
# the output into the CPU, and verify the linear-regression result lands
# in the RAM addresses the compiler reported. This is the one test that
# proves the whole stack works — if it fails, the regression could be in
# either project, and that's the point. Failure in any earlier layer is
# usually easier to localize.
#
# Requires: `cabal` available on PATH and the THCC project built at
# ../THCC/. Skipped (not failed) if the thcc executable can't be located.

import os
import re
import subprocess

THCC_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'THCC'))
REGRESSION_SRC = os.path.join(THCC_DIR, 'examples', 'regression.thcc')


def _run_thcc(args, capture=True):
    """Invoke `cabal run thcc -- <args>` from the THCC dir.

    `cabal -v0 run` suppresses its own chatter so stdout is the
    compiler's output only. Returns the completed-process object.
    """
    cmd = ['cabal', '-v0', 'run', 'thcc', '--'] + list(args)
    return subprocess.run(
        cmd, cwd=THCC_DIR, check=True,
        capture_output=capture, text=True,
    )


def _compile_to_bits_and_varmap():
    """Run THCC twice: once for the bit-string program, once for the asm
    listing (which prints a `; variables:` footer we can scrape for
    addresses).
    """
    bits = _run_thcc([REGRESSION_SRC, '--bits']).stdout.splitlines()
    asm  = _run_thcc([REGRESSION_SRC, '--asm']).stdout
    varmap = {}
    for m in re.finditer(r';\s+(\w+)\s+->\s+RAM\[(\d+)\]', asm):
        varmap[m.group(1)] = int(m.group(2))
    return bits, varmap


def test_thcc_regression_produces_w_eq_2_and_b_eq_1():
    # Skip if cabal isn't on PATH — the CPU-only tests should still work.
    try:
        subprocess.run(['cabal', '--version'], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("skip  test_thcc_regression_produces_w_eq_2_and_b_eq_1: cabal not available")
        return

    program, varmap = _compile_to_bits_and_varmap()

    state = init_state()
    load_program(state, program)
    cycles = run(state, max_cycles=5000)
    assert state['halted'] == '1', "program did not halt within budget"
    assert cycles < 5000

    # The demo data lies exactly on y = 2x + 1, so the expected optimal
    # slope and intercept are 2 and 1.
    w_addr = varmap['w']
    b_addr = varmap['b']
    w_val  = to_sint(state['ram'][w_addr])
    b_val  = to_sint(state['ram'][b_addr])
    assert w_val == 2, f"expected w=2 at RAM[{w_addr}], got {w_val}"
    assert b_val == 1, f"expected b=1 at RAM[{b_addr}], got {b_val}"


# ==========================================================================
# Entry point: run all tests when invoked directly.
# ==========================================================================

if __name__ == '__main__':
    import sys

    # Collect every function in this module whose name starts with `test_`.
    tests = [(name, obj) for name, obj in list(globals().items())
             if name.startswith('test_') and callable(obj)]

    failures = []
    for name, fn in tests:
        try:
            fn()
        except AssertionError as e:
            failures.append((name, f"AssertionError: {e}"))
            print(f"FAIL  {name}: {e}")
        except Exception as e:
            failures.append((name, f"{type(e).__name__}: {e}"))
            print(f"ERROR {name}: {type(e).__name__}: {e}")
        else:
            print(f"ok    {name}")

    print()
    print(f"{len(tests) - len(failures)} / {len(tests)} passed")
    sys.exit(1 if failures else 0)
