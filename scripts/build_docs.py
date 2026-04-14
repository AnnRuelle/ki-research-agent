"""Build docs/ directory from root content for MkDocs."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"

# Directories and files to copy into docs/
COPY_DIRS = ["chapters"]
COPY_FILES = ["index.md", "CHANGELOG.md"]


def build() -> None:
    """Copy content files into docs/ for MkDocs build."""
    # Clean
    if DOCS.exists():
        shutil.rmtree(DOCS)
    DOCS.mkdir()

    # Copy directories
    for d in COPY_DIRS:
        src = ROOT / d
        if src.exists():
            shutil.copytree(src, DOCS / d)

    # Copy files
    for f in COPY_FILES:
        src = ROOT / f
        if src.exists():
            shutil.copy2(src, DOCS / f)

    print(f"Built docs/: {sum(1 for _ in DOCS.rglob('*.md'))} markdown files")


if __name__ == "__main__":
    build()
