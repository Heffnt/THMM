-- | Code generation, linking, and the top-level compiler pipeline.
--
-- Code generation emits symbolic THMM instructions whose memory operands
-- are labels. Linking resolves those labels to concrete RAM addresses once
-- the final instruction count is known.
module CodeGen
    ( Label(..)
    , SymInst(..)
    , CompileError(..)
    , CodeGenOutput(..)
    , LinkOutput(..)
    , genProgram
    , link
    , compile
    , formatError
    ) where

import           Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import           Data.Text       (Text)
import           Text.Megaparsec (errorBundlePretty)

import           AST
import           Parser          (parseProgramText)
import           THMM

-- | A symbolic address: either a user variable or a temporary slot.
data Label
    = LVar String
    | LTmp Int
    deriving (Show, Eq, Ord)

-- | A THMM instruction before concrete memory addresses are assigned.
data SymInst
    = SLoadM Label
    | SLoadN Int
    | SStore Label
    | SAddM  Label
    | SAddN  Int
    | SSubM  Label
    | SMulM  Label
    | SDivM  Label
    | SHalt
    deriving (Show, Eq)

-- | Errors that can arise during parsing, code generation, or linking.
data CompileError
    = ParseError         String
    | UndefinedVar       String
    | DuplicateDecl      String
    | LiteralOutOfRange  Int
    | ProgramTooLarge    Int Int
    deriving (Show, Eq)

-- | Symbolic pass output. Variables are in declaration order, and
-- temporaries are counted by the largest statement-local requirement.
data CodeGenOutput = CodeGenOutput
    { cgoInsts    :: [SymInst]
    , cgoVars     :: [String]
    , cgoMaxTemps :: Int
    } deriving (Show, Eq)

-- | Linked output: concrete instructions plus the variable address table.
data LinkOutput = LinkOutput
    { linkedInsts  :: [THMMInst]
    , addressTable :: [(String, Int)]
    } deriving (Show, Eq)

-- | Compile an AST to symbolic instructions.
genProgram :: Program -> Either CompileError CodeGenOutput
genProgram stmts = do
    vars <- collectVars stmts
    (insts, maxT) <- foldStmts vars stmts
    pure CodeGenOutput
        { cgoInsts    = insts ++ [SHalt]
        , cgoVars     = vars
        , cgoMaxTemps = maxT
        }

foldStmts :: [String] -> [Stmt] -> Either CompileError ([SymInst], Int)
foldStmts _    []     = Right ([], 0)
foldStmts vars (s:ss) = do
    (is1, t1) <- genStmt vars s
    (is2, t2) <- foldStmts vars ss
    pure (is1 ++ is2, max t1 t2)

-- | Walk all declarations once to build the variable list and reject
-- duplicates.
collectVars :: [Stmt] -> Either CompileError [String]
collectVars = go []
  where
    go acc []                       = Right (reverse acc)
    go acc (Decl name _    : rest)  = step acc name rest
    go acc (DeclEmpty name : rest)  = step acc name rest

    step acc name rest
        | name `elem` acc = Left (DuplicateDecl name)
        | otherwise       = go (name : acc) rest

-- | Compile one declaration. Bare declarations only reserve storage.
genStmt :: [String] -> Stmt -> Either CompileError ([SymInst], Int)
genStmt vars (Decl name expr) = do
    (insts, t) <- genExpr vars expr
    pure (insts ++ [SStore (LVar name)], t)
genStmt _    (DeclEmpty _)    = Right ([], 0)

-- | Emit code that leaves the expression's value in the accumulator.
genExpr :: [String] -> Expr -> Either CompileError ([SymInst], Int)
genExpr _ (Lit n)
    | n < 0 || n > 255 = Left (LiteralOutOfRange n)
    | otherwise        = Right ([SLoadN n], 0)

genExpr vars (Var x)
    | x `elem` vars    = Right ([SLoadM (LVar x)], 0)
    | otherwise        = Left (UndefinedVar x)

genExpr vars (BinOp op l r) = case r of
    Var x
        | x `elem` vars -> do
            (ls, lt) <- genExpr vars l
            pure (ls ++ [opMem op (LVar x)], lt)
        | otherwise -> Left (UndefinedVar x)

    Lit n
        | n < 0 || n > 255 -> Left (LiteralOutOfRange n)
        | op == Add -> do
            (ls, lt) <- genExpr vars l
            pure (ls ++ [SAddN n], lt)
        | otherwise -> do
            (ls, lt) <- genExpr vars l
            let tIdx = lt
                stashLit = [SLoadN n, SStore (LTmp tIdx)]
                combine  = [opMem op (LTmp tIdx)]
            pure (stashLit ++ ls ++ combine, lt + 1)

    _ -> do
        (ls, lt) <- genExpr vars l
        (rs, rt) <- genExpr vars r
        let tL     = rt
            tR     = tL + 1
            newMax = max lt (tR + 1)
            insts  = ls
                  ++ [SStore (LTmp tL)]
                  ++ rs
                  ++ [SStore (LTmp tR)]
                  ++ [SLoadM (LTmp tL), opMem op (LTmp tR)]
        pure (insts, newMax)

-- | Map a binary operator to the memory-form instruction constructor.
opMem :: Op -> Label -> SymInst
opMem Add = SAddM
opMem Sub = SSubM
opMem Mul = SMulM
opMem Div = SDivM

-- | Resolve every symbolic address. Fails if code plus data would exceed
-- THMM's 256-word memory.
link :: CodeGenOutput -> Either CompileError LinkOutput
link (CodeGenOutput insts vars maxT)
    | total > 256 = Left (ProgramTooLarge total 256)
    | otherwise = do
        resolved <- traverse (resolveInst table) insts
        pure LinkOutput
            { linkedInsts  = resolved
            , addressTable = varAddrs
            }
  where
    numInsts  = length insts
    numVars   = length vars
    total     = numInsts + numVars + maxT

    varAddrs  = zip vars [numInsts ..]
    tempAddrs = [(i, numInsts + numVars + i) | i <- [0 .. maxT - 1]]

    table :: Map Label Int
    table = Map.fromList $
            [(LVar v, a) | (v, a) <- varAddrs]
         ++ [(LTmp i, a) | (i, a) <- tempAddrs]

resolveInst :: Map Label Int -> SymInst -> Either CompileError THMMInst
resolveInst t (SLoadM lbl) = LoadM <$> lookupLbl t lbl
resolveInst _ (SLoadN n)   = Right (LoadN n)
resolveInst t (SStore lbl) = Store <$> lookupLbl t lbl
resolveInst t (SAddM  lbl) = AddM  <$> lookupLbl t lbl
resolveInst _ (SAddN  n)   = Right (AddN n)
resolveInst t (SSubM  lbl) = SubM  <$> lookupLbl t lbl
resolveInst t (SMulM  lbl) = MulM  <$> lookupLbl t lbl
resolveInst t (SDivM  lbl) = DivM  <$> lookupLbl t lbl
resolveInst _ SHalt        = Right Halt

lookupLbl :: Map Label Int -> Label -> Either CompileError Int
lookupLbl t lbl = case Map.lookup lbl t of
    Just a  -> Right a
    Nothing -> case lbl of
        LVar name -> Left (UndefinedVar name)
        LTmp i    -> error $ "linker bug: temp slot " ++ show i
                           ++ " referenced but not allocated"

-- | Run the full pipeline on source text.
compile :: String -> Text -> Either CompileError LinkOutput
compile sourceName src = case parseProgramText sourceName src of
    Left bundle -> Left (ParseError (errorBundlePretty bundle))
    Right ast   -> genProgram ast >>= link

-- | Render a compile error for display to the user.
formatError :: CompileError -> String
formatError (ParseError msg)         = "parse error:\n" ++ msg
formatError (UndefinedVar name)      = "undefined variable: " ++ name
formatError (DuplicateDecl name)     = "duplicate declaration: " ++ name
formatError (LiteralOutOfRange n)    =
    "literal " ++ show n ++ " out of range; THMM's loadn supports [0, 255]"
formatError (ProgramTooLarge used c) =
    "program too large: " ++ show used ++ " cells needed, only "
    ++ show c ++ " available"
