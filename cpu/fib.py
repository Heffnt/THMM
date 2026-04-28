"""
Fibonacci program for THMM — hand-encoded as a list of 16-bit strings.

Each word is written in binary so the opcode nibble (top 4 bits) is visible
at a glance, and each line is annotated with the mnemonic and effect.

Data layout (after the setup instructions run, before the loop body):
    RAM[21] = n         loop counter (starts at 5)
    RAM[22] = i         constant 1 (used to decrement n)
    RAM[24] = A         current Fibonacci term (starts at 1)
    RAM[25] = B         previous term (implicit 0 via reset state)
    RAM[26] = t         scratch temp

With n = 5 the loop runs 5 iterations. Under the F(1)=F(2)=1 convention,
the final value loaded into Acc before halt is F(6) = 8.

  | line | machine              | mnemonic        | effect                     |
  |-----:|:---------------------|:----------------|:---------------------------|
  |    0 | 0011 0000 0000 0101  | loadn 5         | acc <- 5                   |
  |    1 | 0100 0000 0001 0101  | store 21        | n = 5                      |
  |    2 | 0011 0000 0000 0001  | loadn 1         | acc <- 1                   |
  |    3 | 0100 0000 0001 0110  | store 22        | i = 1                      |
  |    4 | 0100 0000 0001 1000  | store 24        | A = 1                      |
  |    5 | 0010 0000 0001 0101  | loadm 21        | acc <- n                   |
  |  6 L | 1001 0000 0001 0001  | goif0 17        | if acc==0 jump to halt     |
  |    7 | 0010 0000 0001 1000  | loadm 24        | acc <- A                   |
  |    8 | 0100 0000 0001 1010  | store 26        | t = A                      |
  |    9 | 0111 0000 0001 1001  | addm 25         | acc <- A + B               |
  |   10 | 0100 0000 0001 1000  | store 24        | A = A + B                  |
  |   11 | 0010 0000 0001 1010  | loadm 26        | acc <- t                   |
  |   12 | 0100 0000 0001 1001  | store 25        | B = t                      |
  |   13 | 0010 0000 0001 0101  | loadm 21        | acc <- n                   |
  |   14 | 1010 0000 0001 0110  | subm 22         | acc <- n - 1               |
  |   15 | 0100 0000 0001 0101  | store 21        | n = n - 1                  |
  |   16 | 0101 0000 0000 0110  | goto 6          | back to loop head          |
  | 17 H | 0010 0000 0001 1000  | loadm 24        | acc <- A (final result)    |
  |   18 | 0001 0000 0000 0000  | halt            |                            |
"""

FIB_PROGRAM = [
    "0011000000000101",   #  0:      loadn 5
    "0100000000010101",   #  1:      store 21
    "0011000000000001",   #  2:      loadn 1
    "0100000000010110",   #  3:      store 22
    "0100000000011000",   #  4:      store 24
    "0010000000010101",   #  5:      loadm 21
    "1001000000010001",   #  6 (L):  goif0 17
    "0010000000011000",   #  7:      loadm 24
    "0100000000011010",   #  8:      store 26
    "0111000000011001",   #  9:      addm  25
    "0100000000011000",   # 10:      store 24
    "0010000000011010",   # 11:      loadm 26
    "0100000000011001",   # 12:      store 25
    "0010000000010101",   # 13:      loadm 21
    "1010000000010110",   # 14:      subm  22
    "0100000000010101",   # 15:      store 21
    "0101000000000110",   # 16:      goto  6
    "0010000000011000",   # 17 (H):  loadm 24
    "0001000000000000",   # 18:      halt
]
