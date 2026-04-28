-- | THMM machine instructions and serialization.
--
-- THCC emits the opcodes needed for straight-line arithmetic: load,
-- store, addition, subtraction, multiplication, division, and halt.
-- Jump and nop opcodes exist in the hardware but THCC never emits them.
module THMM
    ( THMMInst(..)
    , toAsm
    , toBits
    , toHex
    , opcodeNibble
    ) where

import Data.Bits   (shiftL, shiftR, (.&.), (.|.))
import Data.Char   (intToDigit)
import Text.Printf (printf)

-- | One THMM instruction.
data THMMInst
    = LoadM Int
    | LoadN Int
    | Store Int
    | AddM  Int
    | AddN  Int
    | SubM  Int
    | MulM  Int
    | DivM  Int
    | Halt
    deriving (Show, Eq)

-- | The 4-bit opcode for an instruction.
opcodeNibble :: THMMInst -> Int
opcodeNibble inst = case inst of
    Halt    -> 0x1
    LoadM _ -> 0x2
    LoadN _ -> 0x3
    Store _ -> 0x4
    AddM  _ -> 0x7
    AddN  _ -> 0x8
    SubM  _ -> 0xA
    MulM  _ -> 0xB
    DivM  _ -> 0xC

-- | The low 8-bit operand for an instruction, or 0 for 'Halt'.
operandByte :: THMMInst -> Int
operandByte inst = case inst of
    Halt    -> 0
    LoadM n -> n .&. 0xFF
    LoadN n -> n .&. 0xFF
    Store n -> n .&. 0xFF
    AddM  n -> n .&. 0xFF
    AddN  n -> n .&. 0xFF
    SubM  n -> n .&. 0xFF
    MulM  n -> n .&. 0xFF
    DivM  n -> n .&. 0xFF

-- | Encode an instruction as a 16-bit integer:
-- top 4 bits opcode, next 4 bits zero, low 8 bits operand.
toWord16 :: THMMInst -> Int
toWord16 inst = (opcodeNibble inst `shiftL` 12) .|. operandByte inst

-- | Encode an instruction as a 16-character bit string, which is what
-- @cpu.py@ loads directly.
toBits :: THMMInst -> String
toBits inst = [bit i | i <- [15, 14 .. 0]]
  where
    w = toWord16 inst
    bit i = intToDigit ((w `shiftR` i) .&. 1)

-- | Encode an instruction as a 4-digit uppercase hex string.
toHex :: THMMInst -> String
toHex inst = printf "%04X" (toWord16 inst)

-- | Human-readable assembly mnemonic.
toAsm :: THMMInst -> String
toAsm inst = case inst of
    LoadM n -> "loadm " ++ show n
    LoadN n -> "loadn " ++ show n
    Store n -> "store " ++ show n
    AddM  n -> "addm "  ++ show n
    AddN  n -> "addn "  ++ show n
    SubM  n -> "subm "  ++ show n
    MulM  n -> "mulm "  ++ show n
    DivM  n -> "divm "  ++ show n
    Halt    -> "halt"
