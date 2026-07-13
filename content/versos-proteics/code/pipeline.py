"""End-to-end: Catalan poems -> proteins -> folded structures -> globularity ranking.

For each poem in ``data/poems/*.txt`` this:

1. encodes the text to an amino-acid sequence with the rubric (``main.encode``),
2. folds it with ESMFold via the free ESM Atlas API (``folding.fold_sequence``),
3. scores how globular the structure is (``globularity.score_structure``),

then writes a ranked CSV and prints a table (most globular first).

The folding unit is the whole poem by default (``--unit poem``); sequences longer
than the API cap are folded in chunks and aggregated (length-weighted). Use
``--unit verse`` to fold each line separately and average per poem.

Usage:
  python code/pipeline.py                       # fold data/poems, whole-poem units
  python code/pipeline.py --unit verse          # fold each verse separately
  python code/pipeline.py --poems-dir path/ --out results/mine.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Allow running as `python code/pipeline.py` from the poem root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from folding import MAX_RESIDUES, fold_sequence  # noqa: E402
from globularity import score_structure  # noqa: E402
from main import encode  # noqa: E402

HERE = Path(__file__).resolve().parent
POEM_ROOT = HERE.parent


def to_sequence(text: str) -> str:
    """Encode Catalan text and strip spaces to a bare amino-acid chain."""
    return encode(text).replace(" ", "")


def poem_chunks(text: str, max_len: int = MAX_RESIDUES) -> list[str]:
    """Group whole verses into <=max_len amino-acid chunks (one protein each).

    Splits on verse boundaries so each folded "domain" is a whole set of lines; a
    single verse longer than the cap is hard-split as a last resort.
    """
    chunks: list[str] = []
    cur = ""
    for verse in text.splitlines():
        s = to_sequence(verse)
        if not s:
            continue
        if cur and len(cur) + len(s) > max_len:
            chunks.append(cur)
            cur = ""
        cur += s
        while len(cur) > max_len:
            chunks.append(cur[:max_len])
            cur = cur[max_len:]
    if cur:
        chunks.append(cur)
    return chunks


def _aggregate(scored: list[dict[str, float]]) -> dict[str, float]:
    """Length-weighted mean of per-unit metrics (for chunked / per-verse poems)."""
    total = sum(s["n_residues"] for s in scored) or 1
    keys = ("rg", "rg_expected", "compactness", "anisotropy", "sphericity",
            "mean_plddt", "score")
    agg = {k: round(sum(s[k] * s["n_residues"] for s in scored) / total, 3)
           for k in keys}
    agg["n_residues"] = sum(s["n_residues"] for s in scored)
    agg["n_units"] = len(scored)
    return agg


def analyse_poem(text: str, unit: str) -> dict[str, float] | None:
    """Encode, fold, and score one poem. Returns aggregated metrics or None."""
    if unit == "verse":
        pieces = [to_sequence(v) for v in text.splitlines() if v.strip()]
    else:  # whole poem, split into <=cap domains on verse boundaries
        pieces = poem_chunks(text)
    pieces = [p for p in pieces if len(p) >= 3]

    scored: list[dict[str, float]] = []
    for seq in pieces:
        pdb = fold_sequence(seq)
        if pdb is None:
            continue
        metrics = score_structure(pdb)
        if metrics is not None:
            scored.append(metrics)
    if not scored:
        return None
    return _aggregate(scored) if len(scored) > 1 else {**scored[0], "n_units": 1}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poems-dir", type=Path, default=POEM_ROOT / "data" / "poems")
    parser.add_argument("--unit", choices=("poem", "verse"), default="poem")
    parser.add_argument("--out", type=Path, default=POEM_ROOT / "results" / "globularity.csv")
    args = parser.parse_args()

    poem_files = sorted(p for p in args.poems_dir.glob("*.txt"))
    if not poem_files:
        print(f"No poems found in {args.poems_dir}", file=sys.stderr)
        raise SystemExit(1)

    rows: list[dict[str, object]] = []
    for path in poem_files:
        print(f"folding {path.stem} ...", file=sys.stderr)
        metrics = analyse_poem(path.read_text(encoding="utf-8"), args.unit)
        if metrics is None:
            print(f"  ! folding failed for {path.stem}", file=sys.stderr)
            continue
        rows.append({"poem": path.stem, **metrics})

    if not rows:
        print("No structures produced (API down?).", file=sys.stderr)
        raise SystemExit(1)

    rows.sort(key=lambda r: r["score"], reverse=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["poem", "n_units", "n_residues", "rg", "rg_expected", "compactness",
              "anisotropy", "sphericity", "mean_plddt", "score"]
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    # Console ranking (most globular first).
    print(f"\nGlobularity ranking ({args.unit} units) — higher score = more globular:\n")
    print(f"  {'poem':<28} {'N':>4} {'Rg':>6} {'Rg0':>6} {'κ²':>6} {'pLDDT':>6} {'score':>6}")
    print(f"  {'-'*28} {'-'*4} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
    for r in rows:
        print(f"  {r['poem']:<28} {r['n_residues']:>4} {r['rg']:>6} "
              f"{r['rg_expected']:>6} {r['anisotropy']:>6} {r['mean_plddt']:>6} "
              f"{r['score']:>6}")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
