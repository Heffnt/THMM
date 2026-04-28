{-# LANGUAGE OverloadedStrings #-}

-- | Lexing and parsing for THCC.
--
-- The grammar is:
--
-- @
-- program   ::= statement*
-- statement ::= \"int\" IDENT (\"=\" expr)? \";\"
-- expr      ::= term   ((\"+\"|\"-\") term)*
-- term      ::= factor ((\"*\"|\"/\") factor)*
-- factor    ::= NUMBER | IDENT | \"(\" expr \")\"
-- @
--
-- The lexer-level helpers are in this same module to keep the compiler
-- small and easy to inspect. Expressions are parsed with Megaparsec's
-- 'makeExprParser' so precedence and left associativity are explicit in
-- one operator table.
module Parser
    ( Parser
    , sc
    , lexeme
    , symbol
    , keyword
    , identifier
    , integer
    , parens
    , semicolon
    , equalsSign
    , parseProgram
    , parseProgramText
    , expression
    , statement
    ) where

import           Control.Monad.Combinators.Expr (Operator (..),
                                                 makeExprParser)
import           Data.Text                      (Text)
import qualified Data.Text                      as T
import           Data.Void                      (Void)
import           Text.Megaparsec                (ParseErrorBundle, Parsec,
                                                 between, empty, eof, many,
                                                 notFollowedBy, parse, try,
                                                 (<|>))
import           Text.Megaparsec.Char           (alphaNumChar, char,
                                                 letterChar, space1, string)
import qualified Text.Megaparsec.Char.Lexer     as L

import           AST

-- | The parser monad. @Void@ means we use Megaparsec's default error
-- component, and the input is 'Text'.
type Parser = Parsec Void Text

-- | Eat spaces, tabs, newlines, and @\/\/@ line comments.
sc :: Parser ()
sc = L.space space1 (L.skipLineComment "//") empty

-- | Wrap a parser so it automatically consumes trailing whitespace.
lexeme :: Parser a -> Parser a
lexeme = L.lexeme sc

-- | Parse an exact string and trailing whitespace.
symbol :: Text -> Parser Text
symbol = L.symbol sc

-- | Parse a reserved word, ensuring it is not the prefix of a longer
-- identifier.
keyword :: Text -> Parser ()
keyword kw = (lexeme . try) $ do
    _ <- string kw
    notFollowedBy (alphaNumChar <|> char '_')

reservedWords :: [String]
reservedWords = ["int"]

-- | Parse an identifier and reject reserved words.
identifier :: Parser String
identifier = (lexeme . try) $ do
    first <- letterChar <|> char '_'
    rest  <- many (alphaNumChar <|> char '_')
    let name = first : rest
    if name `elem` reservedWords
        then fail $ "unexpected reserved word " ++ show name
        else pure name

-- | Parse a non-negative decimal integer.
integer :: Parser Int
integer = lexeme L.decimal

-- | Wrap a parser in balanced parentheses.
parens :: Parser a -> Parser a
parens = between (symbol (T.pack "(")) (symbol (T.pack ")"))

-- | Semicolon token.
semicolon :: Parser ()
semicolon = symbol (T.pack ";") >> pure ()

-- | Assignment @=@ token.
equalsSign :: Parser ()
equalsSign = symbol (T.pack "=") >> pure ()

-- | Top-level program: zero or more statements, then end of input.
parseProgram :: Parser Program
parseProgram = between sc eof (many statement)

-- | Run the parser on raw source text. The first argument is the source
-- name used in parse errors.
parseProgramText :: String -> Text -> Either (ParseErrorBundle Text Void) Program
parseProgramText = parse parseProgram

-- | @int IDENT ( = expr )? ;@
statement :: Parser Stmt
statement = do
    keyword (T.pack "int")
    name <- identifier
    initialiser name <|> empty' name
  where
    initialiser name = do
        equalsSign
        e <- expression
        semicolon
        pure (Decl name e)
    empty' name = do
        semicolon
        pure (DeclEmpty name)

-- | An expression with standard C arithmetic precedence.
expression :: Parser Expr
expression = makeExprParser factor operatorTable

-- | Operator table, ordered from tighter to looser binding.
operatorTable :: [[Operator Parser Expr]]
operatorTable =
    [ [ binaryL (T.pack "*") Mul
      , binaryL (T.pack "/") Div
      ]
    , [ binaryL (T.pack "+") Add
      , binaryL (T.pack "-") Sub
      ]
    ]
  where
    binaryL sym op = InfixL (BinOp op <$ symbol sym)

-- | A factor is a literal, variable reference, or parenthesized
-- expression.
factor :: Parser Expr
factor =
        parens expression
    <|> Lit <$> integer
    <|> Var <$> identifier
