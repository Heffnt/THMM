-- | QuickCheck properties for generated THCC programs.
module PropSpec (spec) where

import           Data.List       (nub)
import qualified Data.Text       as T
import           Test.Hspec
import           Test.QuickCheck

import           AST
import qualified CodeGen         as CG
import           THMM

-- | Property-based tests for code generation and linking invariants.
spec :: Spec
spec = describe "QuickCheck properties" $ do
    it "compiles generated well-formed programs" $
        property prop_compile_succeeds_for_well_formed

    it "keeps all operands in the 8-bit field" $
        property prop_operands_in_range

    it "always emits a final halt" $
        property prop_program_ends_with_halt

    it "keeps symbolic and linked instruction counts equal" $
        property prop_codegen_count_matches_link

    it "allocates distinct variable addresses" $
        property prop_addresses_unique

newtype WellFormedProgram = WellFormedProgram Program
    deriving (Show)

instance Arbitrary WellFormedProgram where
    arbitrary = sized $ \n -> do
        len <- chooseInt (1, max 1 (min 8 (n + 1)))
        WellFormedProgram <$> genProgram len
    shrink (WellFormedProgram p) =
        [WellFormedProgram p' | p' <- shrinkList (const []) p, not (null p')]

genProgram :: Int -> Gen Program
genProgram len = go [] 0
  where
    go _ i | i >= len = pure []
    go names i = do
        let name = "v" ++ show i
        expr <- genExpr names 3
        rest <- go (name : names) (i + 1)
        pure (Decl name expr : rest)

genExpr :: [String] -> Int -> Gen Expr
genExpr names depth
    | depth <= 0 = genAtom names
    | otherwise = frequency $
        [ (3, genAtom names)
        , (2, BinOp <$> genOp <*> genExpr names (depth - 1)
                    <*> genExpr names (depth - 1))
        ]

genAtom :: [String] -> Gen Expr
genAtom []    = Lit <$> genLitInt
genAtom names = frequency
    [ (2, Lit <$> genLitInt)
    , (3, Var <$> elements names)
    ]

genOp :: Gen Op
genOp = elements [Add, Sub, Mul, Div]

genLitInt :: Gen Int
genLitInt = chooseInt (0, 255)

prop_compile_succeeds_for_well_formed :: WellFormedProgram -> Property
prop_compile_succeeds_for_well_formed (WellFormedProgram p) =
    case CG.compile "generated" (T.pack (renderProgram p)) of
        Right _  -> property True
        Left err -> counterexample (CG.formatError err) False

prop_operands_in_range :: WellFormedProgram -> Property
prop_operands_in_range (WellFormedProgram p) =
    case linked p of
        Left err -> counterexample (show err) False
        Right out -> conjoin (map instOperandsInRange (CG.linkedInsts out))

prop_program_ends_with_halt :: WellFormedProgram -> Property
prop_program_ends_with_halt (WellFormedProgram p) =
    case linked p of
        Left err -> counterexample (show err) False
        Right out -> not (null insts) .&&. last insts === Halt
          where
            insts = CG.linkedInsts out

prop_codegen_count_matches_link :: WellFormedProgram -> Property
prop_codegen_count_matches_link (WellFormedProgram p) =
    case CG.genProgram p of
        Left err -> counterexample (show err) False
        Right cgo -> case CG.link cgo of
            Left err -> counterexample (show err) False
            Right out -> length (CG.cgoInsts cgo)
                === length (CG.linkedInsts out)

prop_addresses_unique :: WellFormedProgram -> Property
prop_addresses_unique (WellFormedProgram p) =
    case linked p of
        Left err -> counterexample (show err) False
        Right out -> addrs === nub addrs
          where
            addrs = map snd (CG.addressTable out)

linked :: Program -> Either CG.CompileError CG.LinkOutput
linked p = CG.genProgram p >>= CG.link

instOperandsInRange :: THMMInst -> Property
instOperandsInRange inst = case inst of
    LoadM n -> inRange n
    LoadN n -> inRange n
    Store n -> inRange n
    AddM  n -> inRange n
    AddN  n -> inRange n
    SubM  n -> inRange n
    MulM  n -> inRange n
    DivM  n -> inRange n
    Halt    -> property True

inRange :: Int -> Property
inRange n = counterexample ("operand out of range: " ++ show n) $
    n >= 0 && n <= 255

renderProgram :: Program -> String
renderProgram = unlines . map renderStmt

renderStmt :: Stmt -> String
renderStmt stmt = case stmt of
    Decl name expr  -> "int " ++ name ++ " = " ++ renderExpr expr ++ ";"
    DeclEmpty name  -> "int " ++ name ++ ";"

renderExpr :: Expr -> String
renderExpr expr = case expr of
    Lit n        -> show n
    Var name     -> name
    BinOp op l r -> "(" ++ renderExpr l ++ " " ++ renderOp op
                 ++ " " ++ renderExpr r ++ ")"

renderOp :: Op -> String
renderOp op = case op of
    Add -> "+"
    Sub -> "-"
    Mul -> "*"
    Div -> "/"
