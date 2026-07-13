#!/usr/bin/env python3
"""El que es perd en la traducció — despoetization CLI.

Neruda's twenty love poems (and the *canción desesperada*) are pushed through
104 sequential Google-Translate languages back to Spanish. "Poetry is what gets
lost in translation" (R. Frost) — so what returns is the despoetized residue.

The canonical artifact lives under ``data/``:
  data/originals/*.txt     Neruda's originals (the input)
  data/despoetized/*.txt   the 2016 despoetized results (the poem)
  data/_meta.json          piece order, titles, incipits

Usage
-----
    python code/main.py                 # method + list of pieces
    python code/main.py --chain         # print the 104-language chain
    python code/main.py poema01         # original + archived despoetization
    python code/main.py --run poema01   # RE-RUN the chain live (needs network +
                                        # deep-translator); result WILL differ
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from despoetize import despoetize, google_translator  # noqa: E402
from languages import NAMES, chain  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load_meta() -> list[dict]:
    return json.loads((DATA / "_meta.json").read_text(encoding="utf-8"))


def read_piece(kind: str, pid: str) -> str:
    return (DATA / kind / f"{pid}.txt").read_text(encoding="utf-8").rstrip("\n")


def cmd_list() -> None:
    meta = load_meta()
    print(f"El que es perd en la traducció — {len(meta)} pieces "
          f"despoetized through {len(chain()) - 1} languages.\n")
    for m in meta:
        print(f"  {m['id']:<9} {m['title']:<24} {m['incipit'][:44]}")
    print("\nShow one:  python code/main.py <id>")


def cmd_chain() -> None:
    seq = chain()
    print(f"{len(seq) - 1} translation steps ({len(seq) - 1} despoetizations):\n")
    print(" ->\n".join(f"[{c}] {NAMES[c]}" for c in seq))


def cmd_show(pid: str) -> None:
    meta = {m["id"]: m for m in load_meta()}
    if pid not in meta:
        raise SystemExit(f"unknown piece '{pid}'. Try: python code/main.py --list")
    print(f"# {meta[pid]['title']}\n")
    print("ORIGINAL (Pablo Neruda)")
    print(read_piece("originals", pid))
    print("\nDESPOETIZED (2016, 104 languages)")
    print(read_piece("despoetized", pid))


def cmd_run(pid: str) -> None:
    meta = {m["id"]: m for m in load_meta()}
    if pid not in meta:
        raise SystemExit(f"unknown piece '{pid}'. Try: python code/main.py --list")
    original = read_piece("originals", pid)

    def progress(i: int, total: int, src: str, tgt: str) -> None:
        print(f"\r[{i + 1:>3}/{total}] {src} -> {tgt}      ", end="", file=sys.stderr)

    translate = google_translator()
    result = despoetize(original, translate, progress=progress)
    print(file=sys.stderr)
    print(f"# {meta[pid]['title']} — re-run (differs from the 2016 artifact)\n")
    print(result)


def main() -> None:
    p = argparse.ArgumentParser(description="Despoetize Neruda's twenty love poems.")
    p.add_argument("piece", nargs="?", help="piece id (e.g. poema01, cancion)")
    p.add_argument("--list", action="store_true", help="list all pieces")
    p.add_argument("--chain", action="store_true", help="print the language chain")
    p.add_argument("--run", metavar="ID", help="re-run the chain live for one piece")
    args = p.parse_args()

    if args.chain:
        cmd_chain()
    elif args.run:
        cmd_run(args.run)
    elif args.piece:
        cmd_show(args.piece)
    else:
        cmd_list()


if __name__ == "__main__":
    main()
