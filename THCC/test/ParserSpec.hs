-- | Tests for THCC parsing and expression precedence.
module ParserSpec (spec) where

import qualified Data.Text     as T
import           Test.Hspec

import           AST
import           Parser

parse' :: String -> Either String Program
parse' src = case parseProgramText "test" (T.pack src) of
    Left err -> Left (show err)
    Right p  -> Right p

-- | Parser behavior.
spec :: Spec
spec = describe "Parser" $ do
    describe "declarations" $ do
        it "parses an initialized declaration" $
            parse' "int x = 5;" `shouldBe` Right [Decl "x" (Lit 5)]

        it "parses a bare declaration" $
            parse' "int y;" `shouldBe` Right [DeclEmpty "y"]

        it "parses multiple statements" $
            parse' "int a = 1; int b = 2;"
                `shouldBe` Right [Decl "a" (Lit 1), Decl "b" (Lit 2)]

    describe "expressions" $ do
        it "resolves precedence of * over +" $
            parse' "int z = a + b * c;"
                `shouldBe` Right
                    [ Decl "z"
                        (BinOp Add (Var "a")
                            (BinOp Mul (Var "b") (Var "c")))
                    ]

        it "groups parenthesised subexpressions first" $
            parse' "int w = (a + b) * c;"
                `shouldBe` Right
                    [ Decl "w"
                        (BinOp Mul
                            (BinOp Add (Var "a") (Var "b"))
                            (Var "c"))
                    ]

        it "left-associates chained subtraction" $
            parse' "int r = a - b - c;"
                `shouldBe` Right
                    [ Decl "r"
                        (BinOp Sub
                            (BinOp Sub (Var "a") (Var "b"))
                            (Var "c"))
                    ]

        it "handles the w_num shape from the regression demo" $
            parse' "int w_num = n * sum_xy - sum_x * sum_y;"
                `shouldBe` Right
                    [ Decl "w_num"
                        (BinOp Sub
                            (BinOp Mul (Var "n")     (Var "sum_xy"))
                            (BinOp Mul (Var "sum_x") (Var "sum_y")))
                    ]

    describe "errors" $ do
        it "reports missing semicolon" $
            case parse' "int x = 5" of
                Left _  -> pure ()
                Right _ -> expectationFailure "accepted missing semicolon"
