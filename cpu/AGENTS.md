# AGENTS.md

## Project: THMM

A software simulation of **THMM** — a minimal 16-bit accumulator CPU
originally designed and built in Logisim Evolution. The original `.circ`
file was lost; this repo rebuilds the machine from a hand-written spec.
The canonical architecture diagram is [docs/datapath.svg](docs/datapath.svg) —
every design choice below should make sense while looking at that file.

## What the machine is

- **Von Neumann**, single-port **256 × 16-bit RAM** holding both code and data.
- **Accumulator architecture**: one data register (Acc, 16b), one Counter
  (PC, 8b), one Instruction Register (IR, 16b). No general-purpose register
  file. Two tiny state bits: a phase flip-flop and a halt latch.
- **Two-phase execution.** One instruction = two clock cycles. The RAM is
  single-port, so its address bus alternates between PC (fetch) and the `n`
  field of the current instruction (execute). A phase flip-flop selects which.
- **13 opcodes** (encoded in the top 4 bits of a 16-bit instruction word).
- **ALU**: Pass / Add / Sub / Mul / Div. 16-bit two's complement.
- **Divide by zero returns 0.** Deterministic stand-in for the Logisim
  error state. See `alu()` in `cpu.py`.

## Design principles (the "why")

### Every circuit component is a Python function

The simulator is **not** an instruction-level interpreter. It is a per-cycle,
1:1 transcription of the schematic. Each hardware block (ALU, decoder, every
mux, every register, RAM, phase flip-flop, halt latch, the explicit AND
gates between decoder and WE targets) is one function. Every labeled wire
on the diagram is one named local variable inside `tick()`.

Why: so the simulator acts as an executable spec for the eventual Logisim
rebuild, and so we can debug by reasoning about the circuit, not about
simulation tricks. If a wire in the SVG has no counterpart in the code, or
vice versa, one of them is wrong.

### Values are bit strings, not ints

Every signal is a Python `str` of `'0'` and `'1'` of a specific fixed width
(1, 3, 4, 8, or 16 bits). RAM cells are 16-character strings. The fib
program is a list of 16-character bit strings.

Using strings is slower and more awkward than using ints. We do it anyway,
because the circuit doesn't have ints — it has wires carrying bit patterns —
and we want the representation to match. ALU arithmetic converts to `int`
internally, but every component boundary is bit strings.

### Signals pass individually, not bundled

`decoder()` returns a 9-tuple in schematic pin order. `tick()` unpacks into
named variables matching the wire labels. No dicts, no records, no
`Signals` type. A bundle would exist in software but not in the circuit.

### State is a flat dict

One `state` dict with six keys: `pc`, `ir`, `acc`, `phase`, `halted`, `ram`.
No class, no methods. Reads and writes are explicit and grep-able.

### Width discipline via naming

Every variable name holding a signal ends in its bit width: `pc8`, `ir16`,
`acc_zero1`, `alu_op3`. A signal without a width suffix is almost certainly
a bug.

### Python, not C

Performance is irrelevant (256 cells, ~128 cycles for fib). Python keeps the
test cycle fast, the file count low, and the eventual web export trivial
(the trace is already JSON-friendly because every value is a string of bits).

## What we are and are NOT building

### In scope
- Single-file simulator (`cpu.py`) that tracks every wire each cycle.
- The Fibonacci program as a list of 16-bit strings (`fib.py`).
- A flat test file with four layers: combinational truth tables, stateful
  semantics, per-instruction end-to-end (two ticks), and a full fib run.

### Explicitly not in scope (for this pass)
- **No assembler.** Programs are hand-encoded 16-bit binary strings with
  mnemonic comments.
- **No visualization code.** The simulator is self-contained. A future
  viewer will consume a trace that's trivial to emit (the state dict is
  already strings).
- **No performance work.**
- **No abstraction beyond "one function per component".**

## Repo layout

- [AGENTS.md](AGENTS.md) — this file
- [docs/datapath.svg](docs/datapath.svg) — canonical architecture diagram
- [cpu.py](cpu.py) — the simulator
- [fib.py](fib.py) — the fib program as 16-bit strings
- [test_cpu.py](test_cpu.py) — all tests (runs with `python test_cpu.py`
  or `pytest test_cpu.py`)

## Invariants to preserve as the code evolves

1. The tick function and the SVG stay line-for-wire consistent. If you
   add a wire or a component in one, add it to the other.
2. Component functions are pure — no reads or writes of `state`. State
   mutation is confined to the edge-update section of `tick()`.
3. Every value on a wire is a bit string of its declared width. If you
   produce an `int` from an internal computation, convert back before
   returning.
4. The decoder's per-opcode branches remain a flat if/elif chain that
   mirrors the spec table row-for-row. Do not factor into a dict of
   pre-built dicts; the spec-to-code correspondence is the point.
