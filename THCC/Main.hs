-- | THCC command-line driver.
--
-- Usage:
--
-- @
--     thcc input.thcc                    -- print assembly to stdout
--     thcc input.thcc --hex              -- print 4-char hex words
--     thcc input.thcc --bits             -- print 16-char bit strings
--     thcc input.thcc -o output.asm      -- write assembly to file
-- @
module Main (main) where

import qualified Data.Text.IO       as TIO
import           System.Environment (getArgs)
import           System.Exit        (die, exitFailure)
import           System.IO          (hPutStrLn, stderr)

import           CodeGen            (LinkOutput (..), compile, formatError)
import           THMM               (THMMInst, toAsm, toBits, toHex)

data Format = FAsm | FHex | FBits deriving (Show, Eq)

data Options = Options
    { optInput  :: FilePath
    , optOutput :: Maybe FilePath
    , optFormat :: Format
    }

-- | Parse CLI arguments, compile the input file, and write the selected
-- output format.
main :: IO ()
main = do
    args <- getArgs
    opts <- parseArgs args
    src  <- TIO.readFile (optInput opts)
    case compile (optInput opts) src of
        Left err -> do
            hPutStrLn stderr (formatError err)
            exitFailure
        Right linked -> do
            let out = renderOutput (optFormat opts) linked
            case optOutput opts of
                Nothing   -> putStr out
                Just path -> writeFile path out

renderOutput :: Format -> LinkOutput -> String
renderOutput fmt (LinkOutput insts varMap) = case fmt of
    FAsm  -> renderAsm insts varMap
    FHex  -> unlines (map toHex insts)
    FBits -> unlines (map toBits insts)

renderAsm :: [THMMInst] -> [(String, Int)] -> String
renderAsm insts varMap = unlines $ body ++ footer
  where
    body   = zipWith formatLine [0 :: Int ..] insts
    footer = "" : "; variables:" : [ "; " ++ name ++ " -> RAM[" ++ show a ++ "]"
                                   | (name, a) <- varMap ]
    formatLine i inst = pad (show i) ++ ": " ++ toAsm inst
    pad s = replicate (3 - length s) ' ' ++ s

parseArgs :: [String] -> IO Options
parseArgs args = go Nothing Nothing FAsm args
  where
    go (Just input) out fmt [] =
        pure Options { optInput = input, optOutput = out, optFormat = fmt }
    go Nothing _ _ [] = usage "no input file"
    go input out _   ("--hex"  : rest) = go input out FHex  rest
    go input out _   ("--bits" : rest) = go input out FBits rest
    go input out _   ("--asm"  : rest) = go input out FAsm  rest
    go input _   fmt ("-o" : path : rest) = go input (Just path) fmt rest
    go Nothing  out fmt (path : rest)
        | take 1 path /= "-" = go (Just path) out fmt rest
    go _ _ _ (x : _) = usage ("unrecognized argument: " ++ x)

usage :: String -> IO a
usage msg = die $ unlines
    [ "thcc: " ++ msg
    , ""
    , "usage: thcc INPUT.thcc [--asm | --hex | --bits] [-o OUTPUT]"
    ]
