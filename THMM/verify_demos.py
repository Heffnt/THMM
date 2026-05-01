"""
Verify the 5 demo programs compile and produce expected outputs.

Run: python verify_demos.py
"""
import os
import re
import subprocess
import sys

from cpu import init_state, load_program, run, to_sint

THCC_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'THCC'))


def compile_program(thcc_path):
    """Compile .thcc file via cabal, return (program_bits, varmap)."""
    bits_proc = subprocess.run(
        ['cabal', '-v0', 'run', 'thcc', '--', thcc_path, '--bits'],
        cwd=THCC_DIR, check=True, capture_output=True, text=True,
    )
    asm_proc = subprocess.run(
        ['cabal', '-v0', 'run', 'thcc', '--', thcc_path, '--asm'],
        cwd=THCC_DIR, check=True, capture_output=True, text=True,
    )
    program = bits_proc.stdout.splitlines()
    varmap = {m.group(1): int(m.group(2))
              for m in re.finditer(r';\s+(\w+)\s+->\s+RAM\[(\d+)\]', asm_proc.stdout)}
    return program, varmap


def run_program(program, max_cycles=20000):
    """Load program, run to halt, return final state."""
    state = init_state()
    load_program(state, program)
    cycles = run(state, max_cycles=max_cycles)
    if state['halted'] != '1':
        raise RuntimeError(f"program did not halt within {max_cycles} cycles")
    return state, cycles


def read_var(state, varmap, name):
    """Read a named variable from RAM as a signed int."""
    return to_sint(state['ram'][varmap[name]])


def report(name, ok, info=''):
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {name}{(" -- " + info) if info else ""}')
    return ok


def verify_caesar():
    print('demo_caesar.thcc:')
    src = os.path.join(THCC_DIR, 'examples', 'demo_caesar.thcc')
    program, varmap = compile_program(src)
    print(f'  compiled: {len(program)} instructions, {len(varmap)} variables')
    state, cycles = run_program(program)
    print(f'  ran {cycles} cycles')

    expected = "AMAZINGTHINGS"
    actual = ''.join(chr(read_var(state, varmap, f'p{i}')) for i in range(len(expected)))
    ok = actual == expected
    return report('decrypted message', ok,
                  f'expected {expected!r}, got {actual!r}')


def verify_projectile():
    print('demo_projectile.thcc:')
    src = os.path.join(THCC_DIR, 'examples', 'demo_projectile.thcc')
    program, varmap = compile_program(src)
    print(f'  compiled: {len(program)} instructions, {len(varmap)} variables')
    state, cycles = run_program(program)
    print(f'  ran {cycles} cycles')

    # Expected from y_n = 55n - 5n^2, x_n = 20n
    expected_y = [50, 90, 120, 140, 150, 150, 140, 120, 90, 50, 0]
    expected_x = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 220]

    all_ok = True
    for i in range(1, 12):
        x = read_var(state, varmap, f'x{i}')
        y = read_var(state, varmap, f'y{i}')
        ex, ey = expected_x[i-1], expected_y[i-1]
        ok = (x == ex and y == ey)
        all_ok = all_ok and ok
        report(f'step {i:2d}: ({x:4d}, {y:4d})', ok,
               '' if ok else f'expected ({ex}, {ey})')
    return all_ok


def verify_xor():
    print('demo_xor.thcc:')
    src = os.path.join(THCC_DIR, 'examples', 'demo_xor.thcc')
    program, varmap = compile_program(src)
    print(f'  compiled: {len(program)} instructions, {len(varmap)} variables')
    state, cycles = run_program(program)
    print(f'  ran {cycles} cycles')

    cases = [('p_a', 0, 0, 0), ('p_b', 0, 1, 1),
             ('p_c', 1, 0, 1), ('p_d', 1, 1, 0)]
    all_ok = True
    for name, x, y, exp in cases:
        actual = read_var(state, varmap, name)
        ok = actual == exp
        all_ok = all_ok and ok
        report(f'XOR({x},{y}) = {actual}', ok,
               '' if ok else f'expected {exp}')
    return all_ok


def verify_e():
    print('demo_e.thcc:')
    src = os.path.join(THCC_DIR, 'examples', 'demo_e.thcc')
    program, varmap = compile_program(src)
    print(f'  compiled: {len(program)} instructions, {len(varmap)} variables')
    state, cycles = run_program(program)
    print(f'  ran {cycles} cycles')

    e_val = read_var(state, varmap, 'e')
    expected = 2716   # truncated-integer Taylor sum
    ok = e_val == expected
    return report(f'e * 1000 = {e_val}', ok,
                  '' if ok else f'expected {expected}')


def verify_bezier():
    print('demo_bezier.thcc:')
    src = os.path.join(THCC_DIR, 'examples', 'demo_bezier.thcc')
    program, varmap = compile_program(src)
    print(f'  compiled: {len(program)} instructions, {len(varmap)} variables')
    state, cycles = run_program(program)
    print(f'  ran {cycles} cycles')

    expected = [(0, 0), (15, 56), (50, 75), (84, 56), (100, 0)]
    all_ok = True
    for i, (ex, ey) in enumerate(expected):
        x = read_var(state, varmap, f'X{i}')
        y = read_var(state, varmap, f'Y{i}')
        ok = (x == ex and y == ey)
        all_ok = all_ok and ok
        report(f'T={i}: ({x:4d}, {y:4d})', ok,
               '' if ok else f'expected ({ex}, {ey})')
    return all_ok


VERIFIERS = [
    verify_caesar,
    verify_projectile,
    verify_xor,
    verify_e,
    verify_bezier,
]


if __name__ == '__main__':
    results = []
    for fn in VERIFIERS:
        try:
            ok = fn()
        except Exception as e:
            print(f'  ERROR: {type(e).__name__}: {e}')
            ok = False
        results.append((fn.__name__, ok))
        print()

    passed = sum(1 for _, ok in results if ok)
    print(f'{passed}/{len(results)} demos passed')
    sys.exit(0 if passed == len(results) else 1)
