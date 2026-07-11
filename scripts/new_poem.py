#!/usr/bin/env python3
"""Scaffold a new poem folder from the `_template/poem` skeleton.

Usage:
    python scripts/new_poem.py "El jardí de nombres"
    python scripts/new_poem.py "El jardí de nombres" --slug el-jardi

Creates `poems/<slug>/` with the standardised files, pre-filling the title,
slug and date in `metadata.yml`. Refuses to overwrite an existing poem.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO_ROOT / "_template" / "poem"
POEMS_DIR = REPO_ROOT / "poems"


def slugify(text: str) -> str:
    """Turn a Catalan title into a lowercase ASCII slug (accents stripped)."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    return ascii_text.strip("-")


def create_poem(title: str, slug: str) -> Path:
    dest = POEMS_DIR / slug
    if dest.exists():
        sys.exit(f"error: poem already exists at {dest.relative_to(REPO_ROOT)}")
    if not TEMPLATE_DIR.exists():
        sys.exit(f"error: template not found at {TEMPLATE_DIR}")

    shutil.copytree(TEMPLATE_DIR, dest)

    today = dt.date.today().isoformat()
    _fill_metadata(dest / "metadata.yml", title=title, slug=slug, date=today)
    _fill_poem(dest / "poem.md", title=title)
    return dest


def _fill_metadata(path: Path, *, title: str, slug: str, date: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^title:.*$", f"title: {title}", text, count=1, flags=re.M)
    text = re.sub(r"^slug:.*$", f"slug: {slug}", text, count=1, flags=re.M)
    text = re.sub(r"^date:.*$", f"date: {date}", text, count=1, flags=re.M)
    path.write_text(text, encoding="utf-8")


def _fill_poem(path: Path, *, title: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^# .*$", f"# {title}", text, count=1, flags=re.M)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title", help="Poem title, in Catalan (quote it)")
    parser.add_argument("--slug", help="Override the auto-generated slug")
    args = parser.parse_args()

    slug = args.slug or slugify(args.title)
    if not slug:
        sys.exit("error: could not derive a slug from the title; pass --slug")

    dest = create_poem(args.title, slug)
    print(f"Created {dest.relative_to(REPO_ROOT)}")
    print("Next: edit poem.md, metadata.yml, code/main.py and install.sh")


if __name__ == "__main__":
    main()
