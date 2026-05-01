"""Generate the THCC presentation deck as a .pptx for import into Google Slides.

This wrapper delegates to ``make_slides.mjs`` so the final deck is produced by a
cleaner PPTX exporter than the old python-pptx implementation.
"""

from pathlib import Path
import subprocess
import sys


def main() -> int:
    here = Path(__file__).resolve().parent
    return subprocess.call(["node", str(here / "make_slides.mjs")], cwd=here)


if __name__ == "__main__":
    raise SystemExit(main())
