-- | End-to-end compiler pipeline tests.
module IntegrationSpec (spec) where

import qualified Data.Text     as T
import           Test.Hspec

import           CodeGen (LinkOutput (..), compile)
import           THMM    (THMMInst (..))

-- | Full pipeline behavior.
spec :: Spec
spec = describe "Full pipeline" $ do

    it "compiles a three-line program end-to-end" $ do
        let src = T.pack "int a = 5; int b = 7; int c = a + b;"
        case compile "inline" src of
            Left err -> expectationFailure (show err)
            Right (LinkOutput insts varMap) -> do
                let aAddr = lookup "a" varMap
                    bAddr = lookup "b" varMap
                    cAddr = lookup "c" varMap
                last insts `shouldBe` Halt
                insts  `shouldContain` [LoadN 5]
                insts  `shouldContain` [LoadN 7]
                -- The third statement should end with: loadm a; addm b; store c.
                -- We don't pin exact indices; just check the triple is there.
                (aAddr, bAddr, cAddr) `shouldSatisfy` \(a, b, c) ->
                    case (a, b, c) of
                        (Just aA, Just bA, Just cA) ->
                            [LoadM aA, AddM bA, Store cA]
                                `isInfixOf` insts
                        _ -> False

    it "compiles the regression demo and reports w and b addresses" $ do
        let src = T.pack regressionSrc
        case compile "regression" src of
            Left err -> expectationFailure (show err)
            Right (LinkOutput _ varMap) -> do
                lookup "w" varMap `shouldSatisfy` \m -> case m of
                    Just a  -> a >= 0 && a < 256
                    Nothing -> False
                lookup "b" varMap `shouldSatisfy` \m -> case m of
                    Just a  -> a >= 0 && a < 256
                    Nothing -> False

regressionSrc :: String
regressionSrc = unlines
    [ "int n = 3;"
    , "int x0 = 1; int y0 = 3;"
    , "int x1 = 2; int y1 = 5;"
    , "int x2 = 3; int y2 = 7;"
    , "int sum_x  = x0 + x1 + x2;"
    , "int sum_y  = y0 + y1 + y2;"
    , "int sum_xy = x0 * y0 + x1 * y1 + x2 * y2;"
    , "int sum_xx = x0 * x0 + x1 * x1 + x2 * x2;"
    , "int w_num = n * sum_xy - sum_x * sum_y;"
    , "int w_den = n * sum_xx - sum_x * sum_x;"
    , "int w = w_num / w_den;"
    , "int b = (sum_y - w * sum_x) / n;"
    ]

-- | Naive list "contains this contiguous sub-list" check.
isInfixOf :: Eq a => [a] -> [a] -> Bool
isInfixOf needle haystack =
    any (needle `prefixOf`) (tails haystack)
  where
    prefixOf [] _ = True
    prefixOf _ [] = False
    prefixOf (x:xs) (y:ys) = x == y && prefixOf xs ys
    tails [] = [[]]
    tails xs@(_:rest) = xs : tails rest
