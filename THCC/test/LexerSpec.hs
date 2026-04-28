-- | Tests for THCC lexer-level parser helpers.
module LexerSpec (spec) where

import qualified Data.Text       as T
import           Test.Hspec
import           Text.Megaparsec (parse)

import           Parser

-- Convenience: run a lexer parser on a Text input, ignoring the
-- Megaparsec source name.
runP :: Parser a -> String -> Either String a
runP p src = case parse p "test" (T.pack src) of
    Left err -> Left (show err)
    Right a  -> Right a

-- | Lexer helper behavior.
spec :: Spec
spec = describe "Lexer" $ do
    describe "identifier" $ do
        it "accepts a simple name" $
            runP identifier "foo" `shouldBe` Right "foo"
        it "accepts underscores and digits after the first char" $
            runP identifier "sum_xy_2" `shouldBe` Right "sum_xy_2"
        it "rejects the reserved word 'int'" $
            case runP identifier "int" of
                Left _  -> pure ()
                Right v -> expectationFailure $ "accepted reserved word: " ++ v

    describe "integer" $ do
        it "parses decimal literals" $
            runP integer "42" `shouldBe` Right 42
        it "eats trailing whitespace" $
            runP integer "7   " `shouldBe` Right 7

    describe "comments and whitespace" $ do
        it "skips // to end of line" $
            runP (sc *> identifier) "// comment\n  name" `shouldBe` Right "name"
