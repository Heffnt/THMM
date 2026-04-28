# THCC Implementation Specification

## Document Purpose

This document is a complete specification for implementing THCC — a compiler from a small C-like language to THMM machine code, written in Haskell. It captures every design decision, implementation detail, and rationale from the project's planning phase. A developer should be able to implement the project from this document alone.

---

## 1. Project Overview

### 1.1 What We Are Building

A compiler that takes source code written in THCC (a tiny C-like language) and produces machine code that runs on THMM, a custom CPU built in a logic gate simulator. The demo application is computing simple linear regression (ordinary least squares) using the closed-form normal equation.

The project also includes one hardware modification to the THMM CPU: converting the ALU from unsigned to signed (two's complement) arithmetic.

### 1.2 Why We Are Building It

This is a final project for CS536 Programming Language Design at WPI. The class is Haskell-centric and the project must be "programming-language adjacent." We chose to build a compiler because it directly applies PL concepts (grammars, parsing, ASTs, code generation) to a real problem.

The educational thesis is end-to-end transparency: a student can write a high-level program, understand how the compiler processes it, read the generated machine code, and trace its execution through the CPU hardware. Every layer is simple enough to fully understand. This is impossible with real-world toolchains (GCC + x86 is millions of lines of code). The entire THCC compiler should be a few hundred lines of Haskell, and the THMM CPU has 13 instructions.

### 1.3 Why These Specific Choices

**Why a C-like syntax instead of Python-like:** C uses braces and semicolons as delimiters, which are unambiguous single characters that make parsing straightforward. Python's significant indentation requires tracking indentation levels in the lexer, which adds substantial complexity for no educational benefit. Additionally, C's mental model of "variables are named memory locations" maps directly to how THMM works — each variable literally becomes a RAM address.

**Why Haskell:** The class teaches Haskell all semester. The professor's rubric explicitly references Haskell tooling (Haddock docs, HPC coverage, Haskell style guide). Haskell is also a genuinely good fit for compilers — algebraic data types model ASTs naturally, and pattern matching on AST nodes produces clean, readable code generation functions. Parser combinators (Megaparsec) are a well-established Haskell pattern. Using Haskell also demonstrates course material directly in the project.

**Why the normal equation instead of gradient descent:** The normal equation is pure arithmetic — no loops, no branches, no convergence criteria, no learning rate. This means the compiler only needs to support variable declarations, assignment, and arithmetic expressions. No control flow required. Gradient descent would require `while` loops and conditionally checking convergence, which would mean implementing branch instructions in hardware and control flow in the compiler — a much larger scope for a solo project. The normal equation also produces exact results (when the data is chosen carefully), so there's no ambiguity about whether the program ran correctly. A student can verify every intermediate value by hand.

**Why signed arithmetic as the only hardware change:** The normal equation computation produces negative intermediate values. For example, `n * sum_xy - sum_x * sum_y` can be negative depending on the data. With unsigned arithmetic, subtraction wraps around and gives wrong results. We need the ALU to handle negatives correctly. Fortunately, two's complement addition and subtraction already produce the correct bit patterns — the only hardware changes are to the multiplier and divider. This is the minimum viable hardware change. Branch instructions, shift instructions, indirect addressing, etc. are not needed for the core deliverable and are deferred to future work.

---

## 2. The Target Machine: THMM

### 2.1 Architecture Summary

- **Data width:** 16-bit two's-complement values in RAM and the accumulator
- **Instruction width:** 16-bit
- **Instruction format:** 4-bit opcode, 4 unused bits, 8-bit operand/address field
- **Memory:** 256 16-bit words, shared between program instructions and data (Von Neumann architecture)
- **Registers:** Single accumulator. No other general-purpose registers. There is also a program counter (not directly accessible).
- **Instruction set (current, relevant to this project):**

| Opcode | Binary | Instruction | Description |
|--------|--------|-------------|-------------|
| 0 | 0000 | `nop` | Do nothing |
| 1 | 0001 | `halt` | Stop execution |
| 2 | 0010 | `loadm n` | acc = RAM[n] |
| 3 | 0011 | `loadn n` | acc = n (immediate value) |
| 4 | 0100 | `store n` | RAM[n] = acc |
| 5 | 0101 | `goto n` | PC = n |
| 6 | 0110 | `gotoa` | PC = acc |
| 7 | 0111 | `addm n` | acc = acc + RAM[n] |
| 8 | 1000 | `addn n` | acc = acc + n |
| 9 | 1001 | `goif0 n` | if acc == 0 then PC = n |
| 10 | 1010 | `subm n` | acc = acc - RAM[n] |
| 11 | 1011 | `mulm n` | acc = acc × RAM[n] |
| 12 | 1100 | `divm n` | acc = acc ÷ RAM[n] |

- **Hex encoding:** Opcode in top nibble, operand in bottom byte. For example, `loadn 5` = `0x3005`, `store 80` = `0x4050`, `mulm 81` = `0xB051`.

### 2.2 Signed Arithmetic Model

The current simulator already uses signed two's-complement arithmetic throughout the ALU. Addition, subtraction, and multiplication wrap to 16 bits, and division truncates toward zero (C-style) with a deterministic divide-by-zero result of 0.

Instruction encoding, memory layout, program counter logic, and all non-arithmetic instructions are unaffected by the signed interpretation. The compiler emits the same bit patterns; the CPU decides how arithmetic interprets them.

**Why not also add branch instructions, shift, or indirect addressing:** Those are needed for control flow, fixed-point math, and arrays respectively. None of those features are needed for the normal equation demo, which is pure straight-line arithmetic. Keeping the hardware changes minimal reduces scope risk for a solo project and keeps the educational story clean: "we changed one thing in the hardware and it unlocked a useful application."

### 2.3 Instructions Used by the Compiler

The compiler only emits the following instructions:

- `loadn n` — to load literal values into the accumulator
- `loadm n` — to load a variable or temporary into the accumulator
- `store n` — to save the accumulator to a variable or temporary
- `addm n` — addition
- `addn n` — immediate addition when the right-hand operand is a literal
- `subm n` — subtraction
- `mulm n` — multiplication
- `divm n` — division
- `halt` — to end the program

That's 9 out of 13 instructions. The compiler never emits `nop`, `goto`, `gotoa`, or `goif0` because the core language has no control flow.

---

## 3. The Source Language: THCC

### 3.1 Grammar (BNF)

```
program     ::= statement*
statement   ::= "int" IDENT "=" expr ";"
              | "int" IDENT ";"
expr        ::= term (("+"|"-") term)*
term        ::= factor (("*"|"/") factor)*
factor      ::= NUMBER | IDENT | "(" expr ")"
```

Five rules. This is the entire language.

### 3.2 What the Language Supports

- Declaring integer variables with or without an initializer (`int x = 5;` or `int x;`)
- Arithmetic expressions with `+`, `-`, `*`, `/`
- Operator precedence: `*` and `/` bind tighter than `+` and `-` (standard C precedence)
- Parenthesized subexpressions to override precedence
- Variable references in expressions
- Integer literals (must fit in the 8-bit immediate field: 0 to 255)
- C-style single-line comments (`// comment`) — nice to have, trivial to implement in the lexer

### 3.3 What the Language Does NOT Support

- Control flow (`if`, `else`, `while`, `for`) — would require branch instructions in THMM
- Functions — would require a stack, call/return instructions
- Arrays — would require indirect memory access instructions
- Floating point — THMM only has integer arithmetic
- Strings or characters — no I/O mechanism in THMM
- Multiple data types — everything is `int`
- Negative literals in source — write `int x = 0 - 5;` instead of `int x = -5;` (adding unary minus is a minor parser extension but not required)

### 3.4 Why This Specific Grammar

The grammar is the minimum needed to express the normal equation linear regression program. That program requires: variable declarations (to name data points and intermediate results), arithmetic expressions with all four operations (the formula uses add, subtract, multiply, divide), operator precedence (so `n * sum_xy - sum_x * sum_y` groups correctly without parentheses), and parentheses (for the `b` computation: `(sum_y - w * sum_x) / n`).

Nothing else is needed. Adding features beyond this would increase implementation scope without contributing to the core deliverable. Additional features (control flow, functions, arrays) are discussed as future work in the proposal.

---

## 4. The Demo Program

### 4.1 The Algorithm: Ordinary Least Squares (Normal Equation)

For the simple linear regression model `y = w*x + b`, given N data points, the closed-form optimal slope `w` and intercept `b` are:

```
w = (N * Σ(xi*yi) - Σxi * Σyi) / (N * Σ(xi²) - (Σxi)²)
b = (Σyi - w * Σxi) / N
```

This computes the exact best-fit line in one pass — no iteration, no learning rate, no convergence. It's pure arithmetic.

### 4.2 Why This Algorithm

Gradient descent is the more well-known ML algorithm, but it requires iteration (a `while` loop checking convergence), which requires branch instructions in hardware and control flow in the compiler. The normal equation avoids all of that. It also produces exact results (no approximation, no hyperparameter tuning), which means correctness is easy to verify.

### 4.3 The Demo Data

Data points: (1, 3), (2, 5), (3, 7)

These lie exactly on the line y = 2x + 1, so the expected output is w = 2, b = 1.

These data points were chosen because every intermediate value in the computation is small enough to verify by hand:

```
sum_x  = 1 + 2 + 3 = 6          ✓
sum_y  = 3 + 5 + 7 = 15         ✓
sum_xy = 1*3 + 2*5 + 3*7 = 34   ✓
sum_xx = 1*1 + 2*2 + 3*3 = 14   ✓
n * sum_xy = 3 * 34 = 102       ✓
sum_x * sum_y = 6 * 15 = 90     ✓
w_num = 102 - 90 = 12           ✓
w_den = 42 - 36 = 6             ✓
w = 12 / 6 = 2                  ✓
w * sum_x = 2 * 6 = 12          ✓
sum_y - 12 = 3                  ✓
b = 3 / 3 = 1                   ✓
```

The largest intermediate value is 102, well within the 16-bit signed data range and the 8-bit literal range. This is intentional — the demo must not overflow.

### 4.4 The THCC Source Code

```c
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

14 lines, 15 variables (n, x0, y0, x1, y1, x2, y2, sum_x, sum_y, sum_xy, sum_xx, w_num, w_den, w, b). After compilation, the values of `w` and `b` in RAM should be 2 and 1 respectively.

---

## 5. Compiler Architecture

The compiler is a three-stage pipeline: Lexer → Parser → Code Generator. Each stage is a separate Haskell module. The pipeline is one-directional: source text goes in, THMM machine code comes out.

### 5.1 Project Structure

```
THCC/
├── Main.hs                  -- CLI entry point: reads input file, runs pipeline, writes output
├── AST.hs                   -- AST data type definitions
├── Parser.hs                -- Lexing helpers + Megaparsec parser
├── CodeGen.hs               -- Symbolic code generation, linking, and compile facade
├── THMM.hs                  -- THMM instruction data type and serialization
├── test/
│   ├── LexerSpec.hs
│   ├── ParserSpec.hs
│   ├── CodeGenSpec.hs
│   ├── IntegrationSpec.hs   -- Full pipeline tests
│   └── PropSpec.hs          -- QuickCheck properties
├── examples/
│   ├── regression.thcc      -- The linear regression demo
│   ├── regression.expected.asm
│   ├── regression.expected.hex
│   └── simple.thcc          -- Minimal test program
├── thcc.cabal
└── cabal.project
```

### 5.2 Dependencies

- **base** — standard library
- **megaparsec** — parser combinator library
- **containers** — for `Data.Map` (symbol table)
- **text** — for `Text` type (Megaparsec works on `Text` not `String` by default)
- **HUnit** or **hspec** — unit testing
- **QuickCheck** — property-based testing (stretch goal for extra credit)

Install via Cabal: `cabal build` should pull everything in.

---

## 6. Stage 1: Lexer

### 6.1 Purpose

Turn a string of characters into a list of tokens. The lexer handles whitespace, comments, and classifying character sequences into labeled chunks.

### 6.2 Token Data Type

```haskell
data Token
  = KW_Int            -- keyword "int"
  | Ident String      -- variable name (e.g., "sum_xy")
  | IntLit Int        -- integer literal (e.g., 42)
  | Plus              -- "+"
  | Minus             -- "-"
  | Star              -- "*"
  | Slash             -- "/"
  | Equals            -- "="
  | Semicolon         -- ";"
  | LParen            -- "("
  | RParen            -- ")"
  deriving (Show, Eq)
```

### 6.3 Lexing Rules

- **Identifiers:** Start with a letter or underscore, followed by zero or more letters, digits, or underscores. After reading the full identifier string, check if it's the keyword `int`. If yes, emit `KW_Int`. Otherwise, emit `Ident <string>`.
- **Integer literals:** One or more digits. Parse into a Haskell `Int`. No negative literals — the language doesn't support unary minus. (To represent -5, the user writes `0 - 5`.)
- **Operators and punctuation:** Single characters: `+`, `-`, `*`, `/`, `=`, `;`, `(`, `)`. Each maps to exactly one token.
- **Whitespace:** Spaces, tabs, newlines are skipped entirely. They serve only to separate tokens.
- **Comments (nice to have):** If `//` is encountered, skip everything until end of line. This is trivial with Megaparsec's `skipLineComment`.
- **Errors:** If an unrecognized character is encountered (e.g., `@`, `#`, `!`), report an error with line and column number.

### 6.4 Implementation with Megaparsec

Megaparsec provides the `Text.Megaparsec.Char.Lexer` module with helpers:

- `space` — define what counts as whitespace (spaces, tabs, newlines) and what comments look like
- `lexeme` — wraps any parser to automatically consume trailing whitespace
- `decimal` — parses a non-negative integer
- `symbol` — parses an exact string and consumes trailing whitespace

The lexer is roughly 30-40 lines of Haskell. Example sketch:

```haskell
sc :: Parser ()  -- space consumer
sc = L.space space1 (L.skipLineComment "//") empty

lexeme :: Parser a -> Parser a
lexeme = L.lexeme sc

symbol :: Text -> Parser Text
symbol = L.symbol sc

identifier :: Parser Token
identifier = lexeme $ do
  first <- letterChar <|> char '_'
  rest  <- many (alphaNumChar <|> char '_')
  let name = first : rest
  pure $ if name == "int" then KW_Int else Ident name

intLiteral :: Parser Token
intLiteral = IntLit <$> lexeme L.decimal
```

### 6.5 Why Megaparsec Instead of a Hand-Written Lexer

Megaparsec gives us error reporting with line/column numbers for free, handles whitespace skipping cleanly, and is the standard Haskell parsing library. Writing a hand-rolled lexer would mean reimplementing all of this. For a project of this size, the lexer and parser can be combined using Megaparsec's "scannerless parsing" approach — the parser calls lexer-level parsers directly rather than producing an intermediate token list. Either approach works; the separate-stage description is for conceptual clarity.

---

## 7. Stage 2: Parser

### 7.1 Purpose

Take the stream of tokens (or characters, if using scannerless parsing) and produce an Abstract Syntax Tree (AST) — a tree structure that represents the program's meaning with all precedence and grouping resolved.

### 7.2 AST Data Types

```haskell
-- A program is a list of statements
type Program = [Stmt]

-- A statement is a variable declaration
data Stmt
  = Decl String Expr      -- int x = expr;
  | DeclEmpty String       -- int x;
  deriving (Show, Eq)

-- An expression is a tree of operations
data Expr
  = Lit Int                -- integer literal (e.g., 5)
  | Var String             -- variable reference (e.g., "sum_x")
  | BinOp Op Expr Expr    -- binary operation (e.g., x + y)
  deriving (Show, Eq)

-- The four arithmetic operators
data Op = Add | Sub | Mul | Div
  deriving (Show, Eq)
```

### 7.3 How Parsing Works

The parser uses recursive descent: one function per grammar rule, each calling the others for sub-rules. Precedence is encoded by the call structure — lower-precedence operators are parsed at outer levels.

**`parseProgram`:** Parses zero or more statements until end of input.

**`parseStatement`:** Expects `int`, then an identifier, then either `=` followed by an expression and `;` (producing `Decl`), or just `;` (producing `DeclEmpty`). If neither pattern matches, report a parse error.

**`parseExpr`:** Parses a `term`, then looks for `+` or `-`. If found, parses another `term`, wraps both in `BinOp Add` or `BinOp Sub`, and loops (for chained operations like `x + y + z`, which left-associates to `(x + y) + z`).

**`parseTerm`:** Same structure as `parseExpr` but for `*` and `/`. Calls `parseFactor` for operands. Since `parseTerm` is called from within `parseExpr`, multiplications group into subtrees before additions see them — this is how precedence works.

**`parseFactor`:** Handles the leaf nodes. If it sees a number, return `Lit n`. If it sees an identifier, return `Var name`. If it sees `(`, it calls `parseExpr` recursively (so parenthesized subexpressions can contain full expressions with any operators), then expects `)`.

### 7.4 Concrete Example

Input: `int w_num = n * sum_xy - sum_x * sum_y;`

Parsing trace:

```
parseStatement: sees "int", "w_num", "="
  calls parseExpr
    calls parseTerm
      calls parseFactor → "n" → Var "n"
      sees "*", calls parseFactor → "sum_xy" → Var "sum_xy"
      builds BinOp Mul (Var "n") (Var "sum_xy")
      sees "-" → not * or /, so parseTerm returns
    sees "-", consumes it
    calls parseTerm
      calls parseFactor → "sum_x" → Var "sum_x"
      sees "*", calls parseFactor → "sum_y" → Var "sum_y"
      builds BinOp Mul (Var "sum_x") (Var "sum_y")
      sees ";" → not * or /, so parseTerm returns
    builds BinOp Sub (BinOp Mul ...) (BinOp Mul ...)
    sees ";" → not + or -, so parseExpr returns
  sees ";", consumes it
returns: Decl "w_num" (BinOp Sub (BinOp Mul (Var "n") (Var "sum_xy")) (BinOp Mul (Var "sum_x") (Var "sum_y")))
```

Resulting AST:

```
Decl "w_num"
  └── BinOp Sub
        ├── BinOp Mul
        │     ├── Var "n"
        │     └── Var "sum_xy"
        └── BinOp Mul
              ├── Var "sum_x"
              └── Var "sum_y"
```

### 7.5 Left-Associativity for Chained Operations

`x + y + z` must parse as `(x + y) + z`, not `x + (y + z)`. This matters for subtraction and division where grouping changes the result. The `(("+"|"-") term)*` rule in the grammar naturally produces left-associative trees when implemented with a loop: parse the first term, then repeatedly consume an operator and another term, building a left-leaning tree.

```
x + y + z
→ first: Var "x"
→ see "+", parse Var "y", build BinOp Add (Var "x") (Var "y")
→ see "+", parse Var "z", build BinOp Add (BinOp Add (Var "x") (Var "y")) (Var "z")
```

### 7.6 Megaparsec's makeExprParser (Alternative Approach)

Instead of writing `parseExpr`/`parseTerm`/`parseFactor` by hand, Megaparsec offers `makeExprParser` which takes an operator table and builds the parser automatically:

```haskell
expr :: Parser Expr
expr = makeExprParser factor operatorTable

operatorTable :: [[Operator Parser Expr]]
operatorTable =
  [ [ InfixL (BinOp Mul <$ symbol "*")
    , InfixL (BinOp Div <$ symbol "/")
    ]
  , [ InfixL (BinOp Add <$ symbol "+")
    , InfixL (BinOp Sub <$ symbol "-")
    ]
  ]
```

The table is ordered by precedence: first row (mul/div) binds tighter. `InfixL` means left-associative. This produces identical results to the hand-written recursive descent but in fewer lines. Either approach is fine — the hand-written version is more transparent for the educational story, while `makeExprParser` is more idiomatic Megaparsec.

### 7.7 Error Handling

If parsing fails — for example, `int 5 = x;` (number where identifier expected) — Megaparsec reports an error like:

```
line 1, column 5: unexpected integer literal 5, expected identifier
```

This comes for free from how Megaparsec tracks position and expected tokens. No manual error-reporting code is needed for basic cases.

---

## 8. Stage 3: Code Generator

### 8.1 Purpose

Walk the AST and emit a list of THMM instructions. This is where the single-accumulator constraint makes things interesting.

### 8.2 THMM Instruction Data Type

```haskell
data THMMInst
  = LoadM Int      -- loadm n:  acc = RAM[n]
  | LoadN Int      -- loadn n:  acc = n
  | Store Int      -- store n:  RAM[n] = acc
  | AddM Int       -- addm n:   acc = acc + RAM[n]
  | AddN Int       -- addn n:   acc = acc + n
  | SubM Int       -- subm n:   acc = acc - RAM[n]
  | MulM Int       -- mulm n:   acc = acc * RAM[n]
  | DivM Int       -- divm n:   acc = acc / RAM[n]
  | Halt           -- halt
  deriving (Show, Eq)
```

### 8.3 The Two-Pass Strategy

The code generator needs to know where variables live in RAM before it can emit instructions that reference them. But variable addresses depend on the total program length (because variables are placed after the program in memory). And the total program length depends on how many instructions are emitted. This is a chicken-and-egg problem.

The solution is two passes:

**Pass 1 — Count and Allocate:**
1. Walk the entire AST and count how many THMM instructions each statement will produce. Sum to get total instruction count. Add 1 for the `halt` instruction at the end.
2. Assign RAM addresses to user-declared variables, starting at the address immediately after the last instruction.
3. Count the maximum number of temporary addresses needed across all statements (see Section 8.5). Assign temporary addresses starting after the last user variable.

**Pass 2 — Emit:**
1. Walk the AST again, this time actually producing `THMMInst` values with the resolved addresses from the address table.
2. Append `Halt` at the end.

### 8.4 The Address Table

```haskell
type AddressTable = Map String Int
```

Maps variable names to RAM addresses. Built during Pass 1.

Example for the regression program (assuming ~85 instructions total):

```
n       → 85
x0      → 86
y0      → 87
x1      → 88
y1      → 89
x2      → 90
y2      → 91
sum_x   → 92
sum_y   → 93
sum_xy  → 94
sum_xx  → 95
w_num   → 96
w_den   → 97
w       → 98
b       → 99
_tmp0   → 100
_tmp1   → 101
_tmp2   → 102
...
```

The exact addresses depend on the actual instruction count, which is determined during Pass 1.

### 8.5 Expression Flattening: The Core Algorithm

This is the most important part of the code generator. The function `genExpr` takes an expression AST node and emits instructions that leave the result in the accumulator.

**Base cases:**

```
genExpr (Lit n)    = [LoadN n]          -- acc = n
genExpr (Var name) = [LoadM (lookup name symtab)]  -- acc = RAM[var_addr]
```

**Binary operations — the general case:**

For `genExpr (BinOp op left right)`:

```
1. Emit instructions for left     -- result in acc
2. Emit: Store [tmpL]             -- save left result to temporary
3. Emit instructions for right    -- result in acc (clobbers acc, but left is safe in RAM)
4. Emit: Store [tmpR]             -- save right result to temporary
5. Emit: LoadM [tmpL]             -- acc = left result
6. Emit: <op>m [tmpR]             -- acc = left op right
```

Where `<op>m` is `AddM`, `SubM`, `MulM`, or `DivM` depending on `op`.

**Why this pattern and not something more clever:**

The store-both-then-combine pattern is correct for all operators, including non-commutative ones (subtraction, division). For `left - right`, we need `left` in the accumulator and `right` in RAM, so we load left last. The pattern always puts left in the accumulator before the operation, which gives the correct operand order.

For commutative operations (addition, multiplication), you could skip one temporary — after step 3, the right result is in the accumulator and the left is in `tmpL`, so you could do `AddM [tmpL]` directly. This optimization is deliberately not implemented. The naive pattern is easier to verify as correct, and the redundancy creates a teaching opportunity: a student can spot the unnecessary store/load and propose eliminating it.

**Optimization of the simple case:**

When the right operand is a simple `Var` or `Lit` (not a nested `BinOp`), steps 3-5 can be simplified. For `BinOp Mul (Var "n") (Var "sum_xy")`:

```
LoadM [n]           -- acc = n
MulM  [sum_xy]      -- acc = n * sum_xy
```

No temporaries needed — the right operand is already sitting in RAM at a known address. This optimization is worth implementing because it significantly reduces instruction count and temporary usage for the many "simple" expressions in the regression program. The check is: if `right` is a `Var`, you can use its address directly in the operation instruction; if `right` is a `Lit`, you need to store it to a temporary first (because THMM has `mulm` but not `muln` — there's no "multiply by immediate" instruction for most operations).

THMM has `addm` and `addn`, but only `mulm`, `subm`, and `divm` for the other arithmetic operators:
- For `Add` with `Lit` on the right: can use `AddN n` directly (no temporary needed)
- For `Mul`/`Sub`/`Div` with `Lit` on the right: must store the literal to a temporary first, then use `MulM`/`SubM`/`DivM` referencing that temporary
- For any operation with `Var` on the right: can use `<op>M [var_addr]` directly (no temporary needed)

Implementing this simple-right-operand optimization is recommended. It turns the regression program from ~90+ instructions to something more like 60-70. Without it, even `int x0 = 1;` would need a temporary (to store the literal 1, then load it... actually no, `Decl` is not a `BinOp`. Literals on the right side of a binary op are the concern).

**Counter for temporary addresses:**

The code generator maintains a counter for temporary allocation. Each time a temporary is needed, the counter increments:

```haskell
data CodeGenState = CodeGenState
  { nextTemp :: Int      -- next available temporary index
  , maxTemp  :: Int      -- high-water mark across the whole program
  , instructions :: [THMMInst]  -- accumulated instructions (in reverse for efficiency)
  , addressTable :: AddressTable
  }
```

After generating code for each top-level statement, reset `nextTemp` back to 0 (temporaries from one statement don't need to survive to the next — by the time the statement is done, its result is stored in a user variable). Track the maximum `nextTemp` ever reached across all statements — that's how many temporary addresses to reserve.

### 8.6 Generating Statements

**`genStmt (Decl name expr)`:**
1. Call `genExpr expr` — emits instructions, result in accumulator
2. Emit `Store [addr]` where `addr` is looked up from the symbol table

**`genStmt (DeclEmpty name)`:**
No instructions emitted. The variable just gets a slot in the symbol table.

### 8.7 Generating the Full Program

```haskell
genProgram :: Program -> [THMMInst]
genProgram stmts =
  concatMap genStmt stmts ++ [Halt]
```

The `Halt` at the end stops the CPU. Without it, the program counter would advance into the variable data section and try to execute garbage as instructions.

### 8.8 Instruction Counting (Pass 1)

To implement the two-pass strategy, we need a function that counts how many instructions an expression will produce without actually emitting them:

```
countExpr (Lit _)     = 1   -- loadn
countExpr (Var _)     = 1   -- loadm
countExpr (BinOp _ left right)
  | isSimple right    = countExpr left + 1              -- left code + one <op>m
  | otherwise         = countExpr left + 1              -- left code + store tmp
                      + countExpr right + 1             -- right code + store tmp
                      + 1 + 1                           -- loadm tmp + <op>m tmp

countStmt (Decl _ expr) = countExpr expr + 1   -- expr code + store
countStmt (DeclEmpty _) = 0

countProgram stmts = sum (map countStmt stmts) + 1  -- +1 for halt
```

Where `isSimple` checks if the right operand is a `Var` (or `Lit` when using `addn`). This count must exactly match the number of instructions Pass 2 emits. A discrepancy means variable addresses will be wrong and the program will crash.

### 8.9 Complete Walkthrough: Compiling `int w_num = n * sum_xy - sum_x * sum_y;`

AST:

```
Decl "w_num" (BinOp Sub (BinOp Mul (Var "n") (Var "sum_xy"))
                        (BinOp Mul (Var "sum_x") (Var "sum_y")))
```

The outer node is `BinOp Sub`. Both children are `BinOp Mul`, and each mul's operands are simple `Var` nodes.

Code generation:

```
genStmt (Decl "w_num" ...)
  genExpr (BinOp Sub left right)
    -- left is BinOp Mul (Var "n") (Var "sum_xy")
    -- right is BinOp Mul (Var "sum_x") (Var "sum_y")
    -- neither left nor right is simple, so use the full pattern:

    genExpr left = genExpr (BinOp Mul (Var "n") (Var "sum_xy"))
      -- left operand Var "n" is simple: emit LoadM [n_addr]
      -- right operand Var "sum_xy" is simple: emit MulM [sum_xy_addr]
      -- no temporaries needed for this sub-expression
    → [LoadM 85, MulM 94]                    -- acc = n * sum_xy = 102

    Store [_tmp0]                              -- save 102 to temporary

    genExpr right = genExpr (BinOp Mul (Var "sum_x") (Var "sum_y"))
      → [LoadM 92, MulM 93]                  -- acc = sum_x * sum_y = 90

    Store [_tmp1]                              -- save 90 to temporary

    LoadM [_tmp0]                              -- acc = 102
    SubM  [_tmp1]                              -- acc = 102 - 90 = 12

  Store [w_num_addr]                           -- RAM[96] = 12
```

Final instruction sequence (9 instructions):

```
LoadM 85      -- acc = n (3)
MulM  94      -- acc = 3 * 34 = 102
Store 100     -- _tmp0 = 102
LoadM 92      -- acc = sum_x (6)
MulM  93      -- acc = 6 * 15 = 90
Store 101     -- _tmp1 = 90
LoadM 100     -- acc = 102
SubM  101     -- acc = 102 - 90 = 12
Store 96      -- w_num = 12
```

### 8.10 Serialization to Hex

Each `THMMInst` maps to a 16-bit hex value. The format is `OOOO 0000 NNNN NNNN`, where `O` is the 4-bit opcode and `N` is the 8-bit operand/address field.

```haskell
toHex (LoadM n) = printf "%04X" ((0x2 `shiftL` 12) .|. (n .&. 0xFF))  -- 0x20nn
toHex (LoadN n) = printf "%04X" ((0x3 `shiftL` 12) .|. (n .&. 0xFF))  -- 0x30nn
toHex (Store n) = printf "%04X" ((0x4 `shiftL` 12) .|. (n .&. 0xFF))  -- 0x40nn
toHex (AddM n)  = printf "%04X" ((0x7 `shiftL` 12) .|. (n .&. 0xFF))  -- 0x70nn
toHex (AddN n)  = printf "%04X" ((0x8 `shiftL` 12) .|. (n .&. 0xFF))  -- 0x80nn
toHex (SubM n)  = printf "%04X" ((0xA `shiftL` 12) .|. (n .&. 0xFF))  -- 0xA0nn
toHex (MulM n)  = printf "%04X" ((0xB `shiftL` 12) .|. (n .&. 0xFF))  -- 0xB0nn
toHex (DivM n)  = printf "%04X" ((0xC `shiftL` 12) .|. (n .&. 0xFF))  -- 0xC0nn
toHex Halt      = "1000"
```

Verify against the THMM doc examples: `loadn 5` should be `3005` ✓, `store 9` should be `4009` ✓, `addm 9` should be `7009` ✓. The 4 middle bits are always zero.

The assembly text serialization is just:

```haskell
toAsm :: Int -> THMMInst -> String
toAsm lineNum inst = show lineNum ++ ": " ++ case inst of
  LoadM n -> "loadm " ++ show n
  LoadN n -> "loadn " ++ show n
  Store n -> "store " ++ show n
  -- etc.
```

---

## 9. Memory Layout

The compiler produces a memory layout like this:

```
Address 0              ┌──────────────────────┐
                       │                      │
                       │   Program            │
                       │   Instructions       │
                       │   (compiled code)    │
                       │                      │
Address P-1            │   halt               │
                       ├──────────────────────┤
Address P              │   n = 3              │
Address P+1            │   x0 = 1             │
Address P+2            │   y0 = 3             │
                       │   ...                │
Address P+14           │   b                  │
                       ├──────────────────────┤
Address P+15           │   _tmp0              │
Address P+16           │   _tmp1              │
                       │   ...                │
                       ├──────────────────────┤
                       │   (unused)           │
Address 255            └──────────────────────┘
```

Where P is the total number of instructions (including halt). The compiler must ensure P + (number of variables) + (number of temporaries) ≤ 256. For the regression program, this should be well within bounds.

---

## 10. CLI Interface

The compiler should be invoked as:

```bash
thcc input.thcc                    # prints assembly to stdout
thcc input.thcc --hex              # prints hex to stdout
thcc input.thcc -o output.asm      # writes assembly to file
thcc input.thcc -o output.hex --hex  # writes hex to file
```

Minimal argument parsing — this is not the interesting part of the project. Use Haskell's `System.Environment.getArgs` and pattern match. No need for a library like `optparse-applicative` unless you want one.

On parse errors or compilation errors (e.g., undefined variable), print an error message with line/column number and exit with a non-zero exit code.

---

## 11. Error Handling

The compiler should catch and report the following errors:

**Lexer errors:**
- Unrecognized character (e.g., `@`, `#`)
- Integer literal too large (outside the 0 to 255 immediate range — though technically the lexer reads unsigned, the code generator verifies range)

**Parser errors:**
- Missing semicolon
- Missing `=` in declaration
- Unexpected token (e.g., `int 5 = x;`)
- Unmatched parentheses
- These are mostly handled for free by Megaparsec's error reporting

**Code generator errors:**
- Undefined variable (referenced but never declared) — check symbol table
- Duplicate variable declaration (same name declared twice) — check symbol table during insertion
- Program too large (instructions + variables + temporaries > 256 addresses) — check after Pass 1
- Integer literal out of the 8-bit immediate range

---

## 12. Testing Strategy

### 12.1 Unit Tests (HUnit/hspec)

**Lexer tests:** Verify tokenization of individual constructs:
- `"int"` → `[KW_Int]`
- `"sum_xy"` → `[Ident "sum_xy"]`
- `"42"` → `[IntLit 42]`
- `"int x = 5;"` → `[KW_Int, Ident "x", Equals, IntLit 5, Semicolon]`

**Parser tests:** Verify AST construction:
- `"int x = 5;"` → `[Decl "x" (Lit 5)]`
- `"int y = x + 1;"` → `[Decl "y" (BinOp Add (Var "x") (Lit 1))]`
- `"int z = a * b + c;"` → verify precedence: mul groups before add
- `"int w = (a + b) * c;"` → verify parentheses override precedence

**Code generator tests:** Verify instruction output for small programs:
- `"int x = 5;"` → `[LoadN 5, Store <x_addr>, Halt]`
- `"int x = 5; int y = x;"` → `[LoadN 5, Store <x_addr>, LoadM <x_addr>, Store <y_addr>, Halt]`
- `"int a = 2; int b = 3; int c = a + b;"` → verify correct addresses and instruction sequence

**Integration tests:** Compile the full regression program, verify the hex output matches expected values, verify the memory layout.

### 12.2 Property-Based Tests (QuickCheck, stretch goal)

Potential properties:
- All emitted `Store`/`LoadM`/etc. addresses are within 0-255
- All emitted `LoadN` and `AddN` immediates are within 0-255
- Every declared variable appears in the symbol table exactly once
- The instruction count from Pass 1 matches the actual number of instructions from Pass 2 (critical correctness property)
- No variable is referenced before declaration

---

## 13. Documentation Requirements

Per the project rubric:

### 13.1 Code Documentation (10 pts)
- Every function must have a Haddock doc comment explaining what it does
- Every module must have a module-level Haddock comment explaining its role in the pipeline
- Generate standalone Haddock HTML docs

### 13.2 Evaluation Guide (10 pts)
- README.md with: how to install dependencies (`cabal build`), how to run the compiler, how to run the tests, how to run the regression demo end-to-end
- Include the regression.thcc example file
- Include expected output (both assembly and hex) so a reviewer can verify correctness

### 13.3 Project Report (10 pts)
- Separate document covering: goals achieved, challenges encountered, future work
- Must be written by the student (not LLM-generated per class policy)

---

## 14. What NOT to Implement

To keep scope manageable for a solo project, the following are explicitly out of scope. They are discussed as future work in the proposal but should not be implemented:

- **Control flow** (`if`/`else`/`while`) — requires branch instructions in THMM hardware
- **Functions** — requires stack pointer, push/pop, call/return in hardware
- **Arrays** — requires indirect memory access instructions in hardware
- **Optimization passes** — the naive code generation is correct and good enough
- **Unary minus** (`-x`) — use `0 - x` instead
- **Multiple types** — everything is `int`
- **I/O** — THMM has no I/O mechanism; results are inspected by examining RAM in the simulator
- **Separate compilation / linking** — one source file in, one program out

---

## 15. Implementation Notes

The implementation was simplified after the initial design. The compiler is kept as a small Cabal project, but the final source files are flattened into a few top-level Haskell modules rather than nested under a source tree. The CPU simulator uses 16-bit two's-complement data words with 8-bit instruction operands, and the compiler uses `addn` for the simple `x + literal` case. These changes keep the implementation easier to inspect while preserving the original project goal: compile a tiny C-like arithmetic language to THMM machine code and run the linear-regression demo end to end.