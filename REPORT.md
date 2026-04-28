# TomsHardwareStack: Final Report

This project is an end-to-end transparent hardware stack: a high-level language called THCC gets compiled down to machine code that runs on THMM, a custom 16-bit accumulator CPU I built from scratch. The whole point is that every single layer — the hardware simulator, the compiler, and the ISA sitting between them — is small enough that you can actually read the whole thing top to bottom and understand exactly what's going on. That's a pretty stark contrast to something like GCC targeting x86, where no single person could reasonably claim to understand the full picture. The demo payload is an ordinary least squares regression (the closed-form normal equation), and it produces `w = 2`, `b = 1` as expected.

## 1. Goals Achieved

### 1.1 The Hardware: THMM

THMM is a 16-bit accumulator-based CPU with a 13-opcode ISA and 256 words of shared code/data RAM in a Von Neumann layout. The design uses a two-phase fetch/execute cycle against a single-port RAM — during the fetch phase the PC drives the address bus to grab the next instruction, and during the execute phase the instruction's operand field drives it instead. The ALU supports five operations: Pass, Add, Sub, Mul, and Div, all in signed two's complement. Division by zero deterministically returns 0 so the simulator stays predictable (no undefined behavior, no exceptions).

The simulator lives in `THMM/cpu.py`, and I'm pretty proud of how it turned out. Every local variable in the `tick()` function corresponds to a labeled wire on the schematic in `docs/datapath.svg`. If you open both side by side, you can literally trace signals from the register outputs, through the combinational cloud of gates and muxes and the ALU, all the way to the edge-triggered updates. The file is organized into width helpers, combinational components, edge-triggered updates, state management, and the tick/run loops — mirroring how you'd think about the actual circuit.

One thing I really wanted to get right was the bit-string signal discipline. Signals throughout the simulator are Python strings of `'0'` and `'1'` characters, not integers. Width suffixes on variable names (`pc8`, `ir16`, `acc_zero1`, `alu_op3`) document what each wire carries. This keeps the simulator honest about what's actually happening on the wires — patterns of bits, not abstract numbers — and it means the simulator is basically an executable specification for an eventual Logisim rebuild.

### 1.2 The Compiler: THCC

THCC is a compiler written in Haskell that takes a tiny C-like source language and produces THMM machine code. The source language supports `int` variable declarations with initializers, arithmetic with `+ - * /`, parentheses for overriding precedence, and `//` line comments. That's it — no control flow, no functions, no arrays. This is intentional: the demo payload (ordinary least squares) is pure straight-line arithmetic, so none of those features are needed.

The compiler pipeline goes: Parser -> CodeGen (symbolic) -> Linker -> output formatting. Here's how each stage works:

**Parser.** I used Megaparsec with `makeExprParser`, which gives you a nice declarative operator table where you specify precedence levels and associativity. The grammar is scannerless — I originally planned a separate Lexer module with an explicit token list, but Megaparsec's lexer helpers (`L.lexeme`, `L.symbol`, `L.skipLineComment`) made that unnecessary. The parser handles reserved word rejection (so you can't name a variable `int`), and because it's Megaparsec, you get free line/column error reporting on parse failures.

**Code generation.** This is a two-pass process. First, `collectVars` walks all declarations to build the variable list and catch duplicates. Then `genExpr` recursively emits symbolic instructions for each expression. The codegen is naive in the general case — it stores both operands to temporaries, then reloads and combines — but it has two important optimizations. When the right operand is a `Var`, it skips the temporary entirely and just uses the memory-form instruction (`addm`, `subm`, `mulm`, `divm`) directly against that variable's address. When the right operand is a literal and the operation is addition, it emits `addn` (add immediate) instead of materializing the literal to a temp first. These two shortcuts cut the instruction count significantly for typical arithmetic expressions.

**Linker.** The linker resolves symbolic labels (variable names and temporary slot indices) to concrete RAM addresses. The layout is simple: instructions go at the bottom of memory starting at address 0, then user variables, then temporaries. If the total exceeds 256 words, it's a compile error.

**Output formats.** The compiler can emit three formats: `--asm` for human-readable mnemonics with a variable address footer, `--hex` for 4-character hex words, and `--bits` for 16-character bit strings that `cpu.py`'s `load_program` consumes directly. The two halves of the project talk through a plain text file — THCC emits bit strings, and the simulator reads them.

### 1.3 The Demo: It Actually Works

The regression demo (`THCC/examples/regression.thcc`) encodes the closed-form normal equation for ordinary least squares on three hand-picked data points that lie exactly on `y = 2x + 1`:

```
int n = 3;
int x0 = 1; int y0 = 3;
int x1 = 2; int y1 = 5;
int x2 = 3; int y2 = 7;

int sum_x  = x0 + x1 + x2;
int sum_y  = y0 + y1 + y2;
int sum_xy = x0 * y0 + x1 * y1 + x2 * y2;
int sum_xx = x0 * x0 + x1 * x1 + x2 * x2;

int w_num = n * sum_xy - sum_x * sum_y;
int w_den = n * sum_xx - sum_x * sum_x;
int w = w_num / w_den;
int b = (sum_y - w * sum_x) / n;
```

This compiles down to 83 machine instructions (82 arithmetic instructions plus a halt), and after the simulator runs it, you can read `w = 2` and `b = 1` out of RAM at the addresses the compiler reports. The expected assembly and hex outputs are committed as fixtures (`regression.expected.asm`, `regression.expected.hex`), so regressions are immediately visible in version control.

To reproduce the full end-to-end demo from the repo root:

```bash
cd THCC
cabal run thcc -- examples/regression.thcc --bits -o prog.bits
cd ../THMM
python -c "
from cpu import init_state, load_program, run, to_sint
state = init_state()
load_program(state, open('../THCC/prog.bits').read().splitlines())
run(state, max_cycles=5000)
print('w =', to_sint(state['ram'][96]))
print('b =', to_sint(state['ram'][97]))
"
```

Output: `w = 2`, `b = 1`.

### 1.4 Tests and Tooling

I put a lot of effort into testing because with three interacting layers, a bug at any level can cascade in confusing ways.

**Haskell test suite (29 hspec examples, 0 failures).** The tests are split across five spec modules:

- *LexerSpec* (6 tests): Exercises the lexer-level parser helpers — identifier acceptance, reserved word rejection, integer parsing, whitespace/comment handling.
- *ParserSpec* (8 tests): Checks declaration parsing, operator precedence (`*` binds tighter than `+`), parenthesized subexpressions, left associativity of chained subtraction, and error reporting for missing semicolons.
- *CodeGenSpec* (8 tests): Verifies the symbolic code generation — literal declarations, the no-temp optimization for `Var` right operands, the `addn` shortcut, temporary allocation for non-trivial right operands, and error cases (undefined variables, duplicate declarations, out-of-range literals).
- *IntegrationSpec* (2 tests): Full pipeline tests that compile source text all the way to linked instructions and check the output structure.
- *PropSpec* (5 QuickCheck properties): Generates random well-formed programs and checks invariants — compilation always succeeds for well-formed input, all operands fit in the 8-bit field, every program ends with a halt, symbolic and linked instruction counts match, and variable addresses are unique.

**Python test suite (45 tests, all passing).** The CPU tests are organized in five layers of increasing confidence:

1. *Combinational truth tables* (12 tests): Exercises every pure component — AND gates, NOT gates, NOR16 zero-detect, both mux widths, and the full ALU (pass, add with overflow wrap, subtract into negative, multiply, divide with truncation toward zero, divide by zero).
2. *Decoder* (7 tests): Checks that each opcode sets the right control signals — nop drives no enables, halt sets the halt flag, loadm routes RAM to the accumulator, store asserts RAM write enable, goif0 branches when acc is zero and falls through otherwise, gotoa takes its target from the accumulator.
3. *Stateful component semantics* (10 tests): PC counter (count, load, hold, load-dominates-count, 8-bit wrap), IR and Acc register write enables, phase toggle, halt latch set/persist behavior, RAM read/write.
4. *Per-instruction end-to-end* (14 tests): Each test loads a tiny program, runs to halt, and checks the result — covers every instruction the ISA supports.
5. *Full stack end-to-end* (2 tests): The fib program (hand-encoded, verifies the result is F(6) = 8), and the big one — compiles `regression.thcc` with the Haskell compiler, loads the output into the simulator, runs it, and checks `w = 2`, `b = 1`.

**Coverage.** Haskell coverage is available via `cabal test --enable-coverage`, which generates an HPC report. Haddock documentation is at 100% across all library modules (`AST`, `Parser`, `THMM`, `CodeGen`), the executable module, and all test modules. You can regenerate with `cabal haddock --haddock-all`.

## 2. Challenges That Remain

### 2.1 Plan Changes I Made Along the Way

A few things shifted from the original proposal during implementation:

- **Scannerless parser instead of a separate Lexer module.** I originally specified a standalone Lexer that would produce a token list for the Parser to consume. Once I started working with Megaparsec, it became clear that its built-in lexer combinators (`L.lexeme`, `L.symbol`, `L.skipLineComment`) were sufficient, and having a separate token type would just add boilerplate without improving readability. The lexer-level helpers still exist as exported functions in `Parser.hs` and are tested in `LexerSpec.hs`, so nothing was lost.
- **Flat module layout instead of nested `src/THCC/` tree.** I originally planned a `src/THCC/` directory structure, but flattened everything to top-level `.hs` files for easier navigation. With only four library modules, a deep directory hierarchy would have been more ceremony than substance.
- **Kept the 8-bit operand field.** I originally considered supporting larger immediates, but the ISA's 8-bit operand field (0-255) turned out to be fine for the demo workload. Literals outside that range need to be synthesized from arithmetic (e.g., `0 - 5` for -5), which is a real limitation but an acceptable one for a teaching tool.
- **Added the `addn` instruction and shortcut.** This wasn't in the original plan, but once I saw how many unnecessary temporaries the compiler was generating for simple `expr + literal` patterns, adding an add-immediate opcode to the ISA and a matching codegen optimization was a clear win.
- **Single source file, single program.** I didn't implement separate compilation or linking across multiple source files. For a language with no functions and no separate namespaces, there's really no need.

### 2.2 Limits of the Current Artifact

These are things the project can't do, and I want to be upfront about them:

- **No control flow.** There's no `if`/`else`/`while`/`for` in the language. The hardware has `goto`, `gotoa`, and `goif0`, so the ISA could support it, but the compiler doesn't emit jumps for control structures. This means data-dependent algorithms (like gradient descent) are out of reach.
- **No functions.** No call/return mechanism, no stack convention. Every program is a flat sequence of declarations.
- **No arrays.** Data points are individual variables (`x0`, `y0`, ...). The hardware doesn't have indirect memory addressing, so even if the language supported arrays, there'd be no efficient way to index into them.
- **No unary minus.** You have to write `0 - n` instead of `-n`. This is annoying but not a showstopper.
- **No I/O.** The only way to inspect results is to look at the RAM dump after the program halts.
- **8-bit immediate ceiling.** Constants larger than 255 need to be built up from smaller arithmetic.
- **Single `int` type.** No floats, no fixed-point, no unsigned. Everything is signed 16-bit two's complement.

### 2.3 Hardware Items Deferred

- **Comparison and branch family.** The only conditional is `goif0` (branch if accumulator equals zero). A full comparison instruction set (less than, greater than, etc.) would be needed for general-purpose control flow.
- **Shift and rotate.** Without these, there's no practical path to fixed-point arithmetic.
- **Indirect memory addressing.** This would be required for arrays and pointer-style programming.

## 3. Future Works and Roadmap

### 3.1 Language Extensions

The most impactful next step would be adding `if`/`while` to the language, since the hardware already has the `goif0` instruction that could support simple branching. After that, a function call mechanism with a software stack convention would make the language significantly more useful. Arrays and indexing would follow naturally once the hardware gets indirect addressing. On the smaller side, unary minus and a multi-type system (signed/unsigned, byte, fixed-point) would round out the language, and richer error reporting (carets pointing to the error location, "did you mean" suggestions) would improve the developer experience.

### 3.2 Compiler Engineering

There's a lot of room for optimization passes. Constant folding would be the easiest win — expressions like `2 * 3` could be evaluated at compile time instead of emitting instructions. Dead store elimination would clean up unused temporaries. A peephole optimizer over the emitted instruction stream could catch patterns like `store X; loadm X` (which is a no-op if nothing else writes to X between them). Smarter temporary allocation — reusing temp slots across statements instead of allocating fresh ones every time — would reduce the data footprint. And if the language ever grows complex enough to justify it, pulling the lexer-level helpers into a standalone module would be the right move.

### 3.3 Hardware Extensions

The big three are: comparison and conditional branch instructions (to enable iterative algorithms like gradient descent on the same regression problem), shift and rotate (for fixed-point arithmetic), and indirect addressing (for arrays and pointers). A wider operand field or two-word instruction format would also eliminate the 256-literal ceiling.

### 3.4 Tooling

The simulator already outputs bit-string state at every component boundary, which means a trace viewer would be straightforward to build. Since every value is already a string, a web-based visualization could consume the trace directly without any conversion layer. Longer term, a Logisim Evolution rebuild of the datapath from `docs/datapath.svg`, validated cycle-for-cycle against `cpu.py`, would let students see the hardware running "for real" in a circuit simulator.

### 3.5 Domain Extensions

Other straight-line workloads like matrix operations, polynomial evaluation, and statistical moments would make good additional demos. Once the hardware supports control flow, the killer demo would be gradient descent on the same regression problem — students could compare the closed-form solution (what we have now) with an iterative approach and see the tradeoffs firsthand.

## 4. Implementation Notes for the Grader

### 4.1 Documentation (10 pts)

Every function and module in the Haskell codebase has Haddock documentation. You can regenerate it with `cabal haddock --haddock-all`. The Python simulator has module-level and function-level docstrings explaining both the "what" and the "why." The `README.md` serves as the evaluation guide — it covers build prerequisites, how to run tests, how to run the regression demo end-to-end, expected output values, and the coverage one-liner. This report covers the project-level reflection.

### 4.2 Modularity (10 pts)

The Haskell library is split into four modules with clear responsibilities: `AST` defines the syntax tree types, `Parser` handles lexing and parsing, `CodeGen` does symbolic code generation and linking, and `THMM` defines the instruction type and serialization formats. `Main.hs` is pure CLI glue — argument parsing and I/O. Function lengths are kept short; the longest is the `genExpr` codegen walk, and even that is under 30 lines. On the Python side, `cpu.py` has one function per circuit component, directly mirroring the blocks on the schematic. The test files are organized by concern (combinational, stateful, per-instruction, end-to-end).

### 4.3 Readability (10 pts)

The Haskell code follows the standard community style guide and compiles clean under `-Wall`. The Python code follows PEP 8; signal variables carry their bit width as a suffix (`pc8`, `ir16`, `acc_zero1`, `alu_op3`) so you can tell at a glance how wide each wire is. I avoided single-letter variable names except in narrow mathematical scopes where they're the conventional choice (e.g., `a` and `b` as ALU inputs).

### 4.4 Innovation / Difficulty (10 pts)

Three layers — hardware simulator, compiler, and assembler-free direct bit emission — all authored from scratch. The bit-string signal discipline in the simulator means it's not just a functional model of the CPU; it's a literal executable specification for the schematic, where every wire name in the code matches a label on the diagram. This is unusual for educational CPU simulators, which typically operate on integer values and lose the connection to the actual hardware signals.

### 4.5 Extra Credit Candidates (up to 30 pts)

- **Parsing (10 pts):** The parser uses Megaparsec, a real parser combinator library, with `makeExprParser` for declarative precedence handling. Parse errors include line and column numbers for free.
- **Extensive Test Suite (10 pts):** 29 hspec examples across five spec modules (unit tests, integration tests, and QuickCheck property-based tests) on the Haskell side, plus 45 Python tests across five layers on the simulator side. HPC coverage reporting is available via `cabal test --enable-coverage`. The Python test suite includes a cross-project test that shells out to the Haskell compiler, proving the full stack works end-to-end.
- **Exceptional Innovation (10 pts):** The end-to-end transparency claim is the distinguishing feature. Every layer of this project — the CPU, the ISA, and the compiler — fits in a few hundred lines of code and can be read top to bottom by a single person in one sitting. Compare that to GCC (~15 million lines) targeting x86 (~5000-page manual): those tools are incredible engineering achievements, but they're opaque to students trying to understand what a compiler actually does to their code. This project sacrifices generality for inspectability, and I think that tradeoff is worth making for educational purposes.

## 5. Work Allocation / Team Reflection

This was a solo project, so the work division question from Section 4.2 of the rubric doesn't apply.

In terms of what overran and what underran: the hardware simulator came together faster than I expected. Once I committed to the bit-string signal discipline and organized the code to mirror the schematic, the implementation was almost mechanical — each function is just a truth table or a simple state update. The compiler took longer than planned, mostly because I kept going back and forth on how to handle temporary allocation in code generation. My first approach leaked temporaries across statements, which worked fine for simple programs but blew up the RAM footprint on the regression demo. Switching to statement-local temporaries with a global max-temp count fixed it, but that refactor cost about a day.

The tools that really paid off: Megaparsec was the right choice for the parser — `makeExprParser` saved me from hand-rolling precedence climbing, and the error messages are genuinely useful. hspec and QuickCheck made it easy to build up confidence in the compiler incrementally. HPC coverage was nice for finding dead code paths. And honestly, having a fast `cabal repl` loop where I could test individual functions interactively was probably the biggest productivity boost.

If I were starting over, I'd build the simulator first (which I did) but I'd also write the fib program earlier. Having a hand-encoded program that exercises jumps and loops forced me to think about the fetch/execute timing in a way that the straight-line tests didn't. I'd also consider a lexer-first approach if the language were any more complex — the scannerless parser works fine for THCC's tiny grammar, but I can see how it would get messy with more keywords and operators.

Total time spent: roughly 60-70 hours over the course of a few weeks, split roughly 40/60 between the hardware simulator and the compiler (including tests for both).
