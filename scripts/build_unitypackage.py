#!/usr/bin/env python3
"""Build a .unitypackage from the unity/Assets tree without needing Unity.

A .unitypackage is a gzip-compressed tar archive. Each asset is stored under a
directory named by its GUID, containing:

    <guid>/asset       the file content (omitted for folder assets)
    <guid>/asset.meta  the .meta file (carries the GUID)
    <guid>/pathname    the destination path, e.g. "Assets/VEA/Editor/Foo.cs"

Because every .cs already has a committed .meta with a fixed GUID, we can pack
the archive deterministically in CI with no Unity install and no license.

Usage:
    python scripts/build_unitypackage.py [--assets unity/Assets] [--out dist/VEA.unitypackage]
"""
from __future__ import annotations

import argparse
import gzip
import io
import re
import sys
import tarfile
from pathlib import Path

GUID_RE = re.compile(r"^guid:\s*([0-9a-fA-F]{32})\s*$", re.MULTILINE)


def read_guid(meta_path: Path) -> str:
    text = meta_path.read_text(encoding="utf-8")
    m = GUID_RE.search(text)
    if not m:
        raise ValueError(f"no guid found in {meta_path}")
    return m.group(1)


def add_bytes(tar: tarfile.TarFile, arcname: str, data: bytes) -> None:
    info = tarfile.TarInfo(arcname)
    info.size = len(data)
    info.mtime = 0  # deterministic output for reproducible CI builds
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))


def build(assets_dir: Path, out_path: Path, project_root: Path) -> int:
    meta_files = sorted(assets_dir.rglob("*.meta"))
    if not meta_files:
        print(f"error: no .meta files under {assets_dir}", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)

    raw = io.BytesIO()
    count = 0
    with tarfile.open(fileobj=raw, mode="w") as tar:
        for meta in meta_files:
            asset = meta.with_suffix("")  # strip ".meta"
            if not asset.exists():
                print(f"warn: skipping orphan meta {meta}", file=sys.stderr)
                continue

            guid = read_guid(meta)
            # pathname is relative to the project root, forward slashes
            pathname = asset.relative_to(project_root).as_posix()

            add_bytes(tar, f"{guid}/asset.meta", meta.read_bytes())
            add_bytes(tar, f"{guid}/pathname", (pathname + "\n").encode("utf-8"))
            if asset.is_file():
                add_bytes(tar, f"{guid}/asset", asset.read_bytes())
            count += 1
            print(f"  + {pathname}  ({guid})")

    with open(out_path, "wb") as f:
        with gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as gz:
            gz.write(raw.getvalue())

    print(f"\nwrote {out_path} ({out_path.stat().st_size} bytes, {count} assets)")
    return 0


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Build a .unitypackage without Unity")
    parser.add_argument(
        "--assets",
        type=Path,
        default=repo_root / "unity" / "Assets",
        help="path to the Unity Assets directory (default: unity/Assets)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=repo_root / "dist" / "VEA.unitypackage",
        help="output .unitypackage path (default: dist/VEA.unitypackage)",
    )
    args = parser.parse_args()

    assets_dir = args.assets.resolve()
    if not assets_dir.is_dir():
        print(f"error: assets dir not found: {assets_dir}", file=sys.stderr)
        return 1

    # project root = the directory that contains "Assets" (so pathname starts with "Assets/")
    project_root = assets_dir.parent
    return build(assets_dir, args.out.resolve(), project_root)


if __name__ == "__main__":
    raise SystemExit(main())
