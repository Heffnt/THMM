-- | Tests for symbolic THMM code generation.
module CodeGenSpec (spec) where

import           Test.Hspec

import           AST
import           CodeGen

-- | Code generation behavior.
spec :: Spec
spec = describe "CodeGen (symbolic)" $ do
    it "emits loadn + store for a simple literal declaration" $ do
        let prog = [Decl "x" (Lit 5)]
        case genProgram prog of
            Left err -> expectationFailure (show err)
            Right (CodeGenOutput insts vars maxT) -> do
                insts   `shouldBe` [SLoadN 5, SStore (LVar "x"), SHalt]
                vars    `shouldBe` ["x"]
                maxT    `shouldBe` 0

    it "uses no temporary for 'left op (Var _)'" $ do
        let prog = [Decl "a" (Lit 1), Decl "b" (Lit 2),
                    Decl "c" (BinOp Add (Var "a") (Var "b"))]
        case genProgram prog of
            Left err -> expectationFailure (show err)
            Right out -> do
                -- RHS is Var "b", so the combine step is a plain AddM — no temp needed.
                cgoInsts out `shouldContain` [SLoadM (LVar "a"), SAddM (LVar "b")]
                cgoMaxTemps out `shouldBe` 0

    it "uses addn when RHS is a literal and op is Add" $ do
        let prog = [Decl "a" (Lit 1), Decl "b" (BinOp Add (Var "a") (Lit 7))]
        case genProgram prog of
            Left err -> expectationFailure (show err)
            Right out ->
                cgoInsts out `shouldContain` [SAddN 7]

    it "materializes a literal to a temp for subtract-by-literal" $ do
        let prog = [Decl "a" (Lit 9), Decl "b" (BinOp Sub (Var "a") (Lit 2))]
        case genProgram prog of
            Left err -> expectationFailure (show err)
            Right out -> do
                cgoInsts out `shouldContain` [SLoadN 2, SStore (LTmp 0)]
                cgoInsts out `shouldContain` [SSubM (LTmp 0)]

    it "uses the full dance for nested BinOp on the right" $ do
        -- a - (b + c)
        let prog = [ Decl "a" (Lit 1), Decl "b" (Lit 2), Decl "c" (Lit 3)
                   , Decl "d" (BinOp Sub (Var "a")
                                         (BinOp Add (Var "b") (Var "c")))
                   ]
        case genProgram prog of
            Left err -> expectationFailure (show err)
            Right out ->
                cgoMaxTemps out `shouldBe` 2

    it "rejects undefined variables" $
        genProgram [Decl "x" (Var "y")] `shouldBe` Left (UndefinedVar "y")

    it "rejects duplicate declarations" $
        genProgram [Decl "x" (Lit 1), Decl "x" (Lit 2)]
            `shouldBe` Left (DuplicateDecl "x")

    it "rejects literals outside [0, 255]" $
        genProgram [Decl "x" (Lit 300)]
            `shouldBe` Left (LiteralOutOfRange 300)
