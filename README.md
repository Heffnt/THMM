# TomsHardwareStack

A 100% custom hardware stack, end-to-end and fully inspectable at every layer.

- [**THMM/**](THMM/) — THMM, a 16-bit accumulator CPU with 13 opcodes and 256 words
  of shared code/data RAM. Simulated in Python, with every wire of the schematic
  in [docs/datapath.svg](THMM/docs/datapath.svg) corresponding 1:1 to a variable
  in [cpu.py](THMM/cpu.py).
- [**THCC/**](THCC/) — THCC, a compiler from a tiny C-like language to THMM
  machine code. Written in Haskell. Pipeline: Parser → CodeGen (symbolic)
  → linker → hex/asm/bits output.

The two halves talk through a plain-text file: THCC emits 16-bit bit-string
words and `cpu.py`'s `load_program` reads them.

## Prerequisites

- Python 3 (for the simulator).
- GHC + cabal (for the compiler). Install via [GHCup](https://www.haskell.org/ghcup/).
  The test suite uses `hspec`; `cabal test` will pull it in automatically.

## Running the CPU alone

```bash
cd THMM
python test_cpu.py       # runs the full test suite (cpu + fib + end-to-end)
# or
pytest test_cpu.py
```

The CPU tests include four layers of isolated testing (combinational truth
tables, stateful semantics, per-instruction end-to-end, full fib) plus one
end-to-end test that shells out to THCC.

## Compiling and running a THCC program

```bash
cd THCC
cabal build              # builds the compiler + library
cabal test               # runs unit, integration, and QuickCheck tests
cabal run thcc -- examples/regression.thcc                     # prints assembly
cabal run thcc -- examples/regression.thcc --hex               # prints hex words
cabal run thcc -- examples/regression.thcc --bits -o prog.bits # writes bit-strings
```

To compile and then execute the regression demo on the simulator from the repo
root:

```python
import os
import re
import subprocess

from THMM.cpu import init_state, load_program, run, to_sint

thcc_dir = os.path.join(os.getcwd(), "THCC")
source = os.path.join(thcc_dir, "examples", "regression.thcc")

bits = subprocess.check_output(
    ["cabal", "-v0", "run", "thcc", "--", source, "--bits"],
    cwd=thcc_dir,
    text=True,
).splitlines()
asm = subprocess.check_output(
    ["cabal", "-v0", "run", "thcc", "--", source, "--asm"],
    cwd=thcc_dir,
    text=True,
)
varmap = {
    m.group(1): int(m.group(2))
    for m in re.finditer(r";\s+(\w+)\s+->\s+RAM\[(\d+)\]", asm)
}

state = init_state()
load_program(state, bits)
run(state, max_cycles=5000)
print("w =", to_sint(state["ram"][varmap["w"]]))
print("b =", to_sint(state["ram"][varmap["b"]]))
```

Expected output:

```text
w = 2
b = 1
```

## The THCC source language

```c
int n = 3;
int x0 = 1; int y0 = 3;
int sum_xy = x0 * y0 + ...;
int w = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x);
```

- Variables only, all of type `int` (one type, 16-bit two's complement).
- Arithmetic with `+ - * /`, standard C precedence, left-associative.
- Parens to override precedence.
- Line comments with `//`.
- No control flow, no functions, no arrays — by design. The demo payload is
  straight-line arithmetic (ordinary least squares) chosen so that none of
  those features are needed.
- Literals are 0..255 (the only range `loadn` can express directly on THMM).
  For negative values, write `0 - 5` instead of `-5`.

See [THCC/examples/regression.thcc](THCC/examples/regression.thcc) for the
linear-regression demo. Expected assembly and hex outputs are committed as
[THCC/examples/regression.expected.asm](THCC/examples/regression.expected.asm)
and [THCC/examples/regression.expected.hex](THCC/examples/regression.expected.hex).

## Output formats

- `--asm` (default): human-readable mnemonics, one per line, with a `; variables:`
  footer listing which RAM address each variable was allocated to.
- `--hex`: 4-character hex words (e.g. `3005` for `loadn 5`).
- `--bits`: 16-character bit strings, which is what `cpu.py`'s `load_program`
  consumes directly.

## Coverage

```bash
cd THCC
cabal test --enable-coverage
# HPC HTML lands under dist-newstyle/.../hpc/vanilla/html/hpc_index.html
```

## Expected results

- `cd THCC && cabal test`: `29 examples, 0 failures`.
- `cd THMM && python test_cpu.py`: `45 / 45 passed`.
- `cd THCC && cabal haddock --haddock-all`: 100% documented library modules
  (`AST`, `Parser`, `THMM`, `CodeGen`), executable, and test modules.
- Regression demo result after running on the CPU: `w = 2`, `b = 1`.
- Regression addresses in the current assembly fixture: `w -> RAM[96]`,
  `b -> RAM[97]`.

## Repo layout

```
THMM/
├── THMM/                  Python simulator + tests
│   ├── cpu.py
│   ├── fib.py
│   ├── test_cpu.py
│   └── docs/datapath.svg
├── THCC/                  Haskell compiler
│   ├── thcc.cabal
│   ├── Main.hs
│   ├── AST.hs
│   ├── Parser.hs
│   ├── CodeGen.hs
│   ├── THMM.hs
│   ├── test/*.hs
│   └── examples/*.thcc
└── README.md              (this file)
```
