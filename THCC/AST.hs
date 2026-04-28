-- | Abstract syntax tree for THCC.
--
-- A program is a list of statements. A statement is a variable
-- declaration (with or without an initializer). An expression is a tree
-- of literals, variable references, and binary operations.
module AST
    ( Program
    , Stmt(..)
    , Expr(..)
    , Op(..)
    ) where

-- | A complete THCC source file after parsing.
type Program = [Stmt]

-- | A top-level statement in THCC.
data Stmt
    = Decl      String Expr   -- ^ @int x = expr;@
    | DeclEmpty String        -- ^ @int x;@
    deriving (Show, Eq)

-- | An arithmetic expression.
data Expr
    = Lit   Int               -- ^ integer literal
    | Var   String            -- ^ variable reference
    | BinOp Op Expr Expr      -- ^ binary operation
    deriving (Show, Eq)

-- | Binary arithmetic operators supported by THCC.
data Op = Add | Sub | Mul | Div
    deriving (Show, Eq)
