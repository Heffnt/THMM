# Final Report

> Outline only. Every bullet is a prompt for prose **you** must write before
> submission, per the LLM policy in ProjectGuide.pdf §5.1.

## 0. Project Summary (one short paragraph at the top once written)

- One-sentence pitch: end-to-end transparent stack — high-level THCC source compiled to THMM machine code that runs on a custom 16-bit accumulator CPU
- Target audience: PL experts with no domain background (per §4.1)
- Demo payload: ordinary least squares (closed-form normal equation), expected `w = 2`, `b = 1`
- Educational thesis: every layer (HW sim + compiler + ISA) is small enough to read top-to-bottom — contrast with GCC + x86

## 1. Goals Achieved

### 1.1 Hardware (THMM)
- 16-bit accumulator CPU, 13-opcode ISA, 256-word shared code/data RAM (Von Neumann)
- Two-phase fetch/execute against a single-port RAM
- Signed two's-complement ALU (Pass / Add / Sub / Mul / Div); deterministic divide-by-zero -> 0
- Per-cycle Python simulator (`THMM/cpu.py`) where every wire on `THMM/docs/datapath.svg` is one named local in `tick()`
- Bit-string signals at every component boundary (matches "wires carry patterns", not ints)

### 1.2 Compiler (THCC)
- Source language: `int` declarations, `+ - * /`, parens, `//` line comments, standard C precedence
- Pipeline: Parser -> CodeGen (symbolic) -> linker -> hex / asm / bits output
- Parser: Megaparsec with `makeExprParser`; free line/column error reporting
- CodeGen: two-pass (count + allocate, then emit), naive store-both-then-combine, optimised simple-right-operand case (`addn` for `+ literal`; direct `mulm`/`subm`/`divm` against `Var` addresses)
- Output formats: `--asm` (with variable address footer), `--hex` (4-char words), `--bits` (16-char strings consumed by `load_program`)

### 1.3 Demo working in practice (Goals Achieved §4.1 wants concrete examples)
- `THCC/examples/regression.thcc` -> deterministic machine code -> simulator -> `w = 2`, `b = 1`
- Committed expected fixtures: `regression.expected.asm`, `regression.expected.hex`
- Smoke example: `THCC/examples/simple.thcc`
- Reproduction: copy the README "Compiling and running a THCC program" block

### 1.4 Tests + tooling
- 29 hspec examples across `LexerSpec`, `ParserSpec`, `CodeGenSpec`, `IntegrationSpec`
- QuickCheck `PropSpec` (instruction-count invariant, address bounds, immediate ranges, etc.)
- HPC coverage figures (cite the README Coverage section)
- 45/45 Python tests in `THMM/test_cpu.py`: combinational truth tables, stateful semantics, per-instruction end-to-end (two ticks), full fib, plus end-to-end shell-out to `cabal run thcc` for the regression demo
- Haddock at 100% across library, executable, and test modules

## 2. Challenges Remain

### 2.1 Plan changes accepted during implementation
- Originally specified separate Lexer module + token list -> collapsed to a scannerless Megaparsec parser
- Originally planned nested `src/THCC/` tree -> flattened to top-level Haskell modules for easier reading
- Originally targeted larger immediates -> kept the ISA's 8-bit operand field; literals must fit in `0..255`
- Added `addn` shortcut so common `expr + literal` skips a temporary
- Single source file in / single program out (no separate compilation/linking)

### 2.2 Limits of the current artifact
- No control flow in the language -> no `if`/`else`/`while`/`for`; data-dependent algorithms are out of reach
- No functions -> no call/return, no software stack convention
- No arrays -> data points are individual variables (`x0`, `y0`, …)
- No unary minus -> negative literals must be written `0 - n`
- No I/O -> result inspection is a RAM dump in the simulator
- 8-bit immediate ceiling -> larger constants need synthesis from arithmetic
- Single `int` type, no floats / fixed-point

### 2.3 Hardware items deferred
- Comparison + branch family beyond `goif0` (only `acc == 0` is testable)
- Shift / rotate (no fixed-point)
- Indirect memory addressing (no arrays / pointers)

## 3. Future Works and Roadmap

### 3.1 Language layer
- Control flow (`if` / `while`) once branch instructions exist in HW
- Functions with a software stack convention
- Arrays + indexing once indirect addressing is in HW
- Unary minus, multi-type system (signed/unsigned, byte, fixed-point)
- Richer error reporting (carets, multi-line spans, "did you mean")

### 3.2 Compiler engineering
- Optimisation passes: constant folding, dead store elimination, peephole over emitted instructions
- Smarter temporary allocation (reuse across statements, register-style colouring on the single accumulator)
- Standalone Lexer module if/when the language grows

### 3.3 Hardware
- Comparison + conditional branch instructions to enable iterative algorithms (e.g. gradient descent on the same regression problem)
- Shift / rotate for fixed-point arithmetic
- Indirect addressing for arrays / pointer-style code
- Wider operand field or two-word instructions for full 16-bit immediates

### 3.4 Tooling
- Trace viewer that consumes the simulator's already-bit-string state dict (web-friendly because every value is a string of bits)
- Logisim Evolution rebuild from `THMM/docs/datapath.svg`, validated cycle-for-cycle against `cpu.py`

### 3.5 Domain extension
- Other straight-line workloads (matrix ops, polynomial evaluation, statistical moments)
- Once HW supports control flow: gradient descent on the same regression problem so students can compare closed-form vs iterative

## 4. Implementation Notes for the Grader (maps to §4.4 rubric)

### 4.1 Documentation (10 pts)
- Haddock on every function and module; reproduce with `cabal haddock --haddock-all`
- `README.md` is the evaluation guide (build, run tests, run regression demo end-to-end, expected `w` / `b` values, coverage one-liner)
- This `REPORT.md` covers project-level reflection

### 4.2 Modularity (10 pts)
- Library split into `AST` / `Parser` / `CodeGen` / `THMM` modules; `Main.hs` is just CLI glue
- Function lengths kept under the Haskell guideline; the longest is the codegen walk
- Python simulator: one function per circuit component, mirroring the SVG schematic

### 4.3 Readability (10 pts)
- Haskell follows the standard style guide; cabal warnings clean under `-Wall`
- Python follows PEP8; signal variables carry their bit width as a suffix (`pc8`, `ir16`, `alu_op3`)
- No single-letter names except mathematical conventions in narrow scopes

### 4.4 Innovation / Difficulty (10 pts)
- Three layers (HW sim + compiler + assembler-free direct bit emission) authored from scratch
- Bit-string signal discipline keeps the simulator a literal executable spec for the schematic — supports an eventual Logisim rebuild

### 4.5 Extra credit candidates (up to 30 pts)
- **Parsing**: Megaparsec parser combinator with line/column error reporting
- **Test Suite**: hspec unit + integration + QuickCheck properties + HPC coverage report; plus the four-layer Python test suite that shells back into the Haskell compiler
- **Exceptional Innovation**: end-to-end transparency claim — every layer fits in a few hundred lines and can be read top-to-bottom; literature comparison vs GCC + x86

## 5. Work Allocation / Team Reflection

- Team size: solo (so §4.2 work-division dispute language is N/A)
- Self-reflection bullet to fill in: which milestones overran or underran, and why
- Tooling that paid off: Megaparsec, hspec, HPC, Cursor + cabal repl loop (note the ones that actually mattered)
- What you would structure differently next time (e.g. lexer-first vs scannerless, build the simulator before or after the compiler, etc.)
- Note total time spent (rough estimate is fine; helpful for graders calibrating "Innovation/Difficulty")
