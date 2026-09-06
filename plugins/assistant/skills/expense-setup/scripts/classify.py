#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["pypdf>=5.0"]
# ///
"""Classify receipts into <workdir>/unprocessed/<category>/ and move them there."""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

CATEGORIES = ("amazon", "photos", "screenshots", "other")
PHOTO_EXT = {".jpg", ".jpeg", ".heic", ".heif"}
SHOT_EXT = {".png", ".webp", ".gif"}
SKIP_NAMES = {"expenses.csv"}  # dotfiles are skipped separately


def pdf_head_text(path: Path, chars: int = 4000) -> str:
    try:
        import logging

        from pypdf import PdfReader

        logging.getLogger("pypdf").setLevel(logging.CRITICAL)
        return (PdfReader(str(path)).pages[0].extract_text() or "")[:chars]
    except Exception:
        return ""


def classify(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        blob = (path.name + " " + pdf_head_text(path)).lower()
        return "amazon" if "amazon" in blob else "other"
    if ext in PHOTO_EXT:
        return "photos"
    if ext in SHOT_EXT:
        # Screenshots have no camera EXIF; a phone photo saved as PNG does.
        return "photos" if b"Exif" in path.read_bytes()[:8192] else "screenshots"
    return "other"


def slug(stem: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-.") or "receipt"


def unique(dest_dir: Path, name: str, taken: set[Path]) -> Path:
    stem, ext = Path(name).stem, Path(name).suffix
    cand = dest_dir / f"{slug(stem)}{ext.lower()}"
    n = 1
    while cand.exists() or cand in taken:
        cand = dest_dir / f"{slug(stem)}-{n}{ext.lower()}"
        n += 1
    taken.add(cand)
    return cand


def plan(src: Path, workdir: Path) -> list[dict]:
    managed = {workdir / "unprocessed", workdir / "processed"}
    taken: set[Path] = set()
    out = []
    for f in sorted(src.rglob("*")):
        if not f.is_file() or f.name in SKIP_NAMES or f.name.startswith("."):
            continue
        if any(p in managed for p in f.parents):
            continue
        cat = classify(f)
        dest = unique(workdir / "unprocessed" / cat, f.name, taken)
        out.append({"src": str(f), "dest": str(dest), "category": cat})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path, help="directory of loose receipts")
    ap.add_argument("--workdir", type=Path, help="defaults to src")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    workdir = a.workdir or a.src
    if not a.src.is_dir():
        print(f"not a directory: {a.src}", file=sys.stderr)
        return 1

    moves = plan(a.src.resolve(), workdir.resolve())
    if not a.dry_run:
        for cat in CATEGORIES:
            (workdir / "unprocessed" / cat).mkdir(parents=True, exist_ok=True)
            (workdir / "processed" / cat).mkdir(parents=True, exist_ok=True)
        for m in moves:
            shutil.move(m["src"], m["dest"])
    print(json.dumps({"dry_run": a.dry_run, "count": len(moves), "moves": moves}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
