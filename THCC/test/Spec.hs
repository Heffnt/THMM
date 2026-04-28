-- | hspec entry point. Wires together the per-module specs so
-- @cabal test@ runs them all.
module Main (main) where

import           Test.Hspec (hspec)

import qualified CodeGenSpec
import qualified IntegrationSpec
import qualified LexerSpec
import qualified ParserSpec
import qualified PropSpec

-- | Run the full THCC test suite.
main :: IO ()
main = hspec $ do
    LexerSpec.spec
    ParserSpec.spec
    CodeGenSpec.spec
    IntegrationSpec.spec
    PropSpec.spec
