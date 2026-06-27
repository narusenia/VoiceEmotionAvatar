#!/usr/bin/env python3
"""Remove generated artifacts (cross-platform).

Deletes build/output directories and Python caches. The local uv install
(.uv/) and downloaded models are left alone so a clean doesn't force a
multi-GB re-download.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Top-level directories to remove outright.
DIRS = [".venv", "dist", "build"]

# Glob patterns (relative to ROOT) for caches scattered through the tree.
GLOBS = ["**/__pycache__", "**/*.egg-info", "**/*.py[cod]"]


def rm(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        print(f"  removed dir  {path.relative_to(ROOT)}")
    elif path.exists():
        path.unlink(missing_ok=True)
        print(f"  removed file {path.relative_to(ROOT)}")


def main() -> int:
    for name in DIRS:
        rm(ROOT / name)
    for pattern in GLOBS:
        for p in ROOT.glob(pattern):
            if ".uv" in p.relative_to(ROOT).parts:
                continue
            rm(p)
    print("clean done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
