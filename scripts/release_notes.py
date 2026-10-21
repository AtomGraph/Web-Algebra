"""Print a version's section of CHANGELOG.md, for its GitHub Release.

    python scripts/release_notes.py 2.0.0

Exits with an error if the changelog has no section for the version, so a
release is not made without notes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def notes(version: str, text: str) -> str:
    match = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]: )", text, re.M | re.S)
    if match is None:
        raise SystemExit(f"CHANGELOG.md has no section for {version}")
    return match.group(1).strip() + "\n"


if __name__ == "__main__":
    print(notes(sys.argv[1], CHANGELOG.read_text(encoding="utf-8")), end="")
