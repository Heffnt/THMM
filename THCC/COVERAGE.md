# THCC Coverage

Generated with:

```powershell
cabal test --enable-coverage

$TIX = "dist-newstyle\build\x86_64-windows\ghc-9.6.7\thcc-0.1.0.0\t\thcc-test\hpc\vanilla\tix\thcc-test.tix"
$LIB_MIX = "dist-newstyle\build\x86_64-windows\ghc-9.6.7\thcc-0.1.0.0\build\extra-compilation-artifacts\hpc\vanilla\mix"
$TEST_MIX = "dist-newstyle\build\x86_64-windows\ghc-9.6.7\thcc-0.1.0.0\t\thcc-test\build\thcc-test\thcc-test-tmp\extra-compilation-artifacts\hpc\vanilla\mix"
hpc report $TIX --hpcdir=$LIB_MIX --hpcdir=$TEST_MIX `
  --include=AST --include=Parser --include=THMM --include=CodeGen
```

Library coverage summary:

```text
 72% expressions used (454/625)
 35% boolean coverage (5/14)
      30% guards (4/13), 6 always True, 2 always False, 1 unevaluated
     100% 'if' conditions (1/1)
     100% qualifiers (0/0)
 45% alternatives used (34/75)
 90% local declarations used (19/21)
 44% top-level declarations used (40/90)
```

The generated HTML report is written under:

```text
dist-newstyle/build/x86_64-windows/ghc-9.6.7/thcc-0.1.0.0/t/thcc-test/hpc/vanilla/html/hpc_index.html
```

The HTML is generated build output and is intentionally not committed.
