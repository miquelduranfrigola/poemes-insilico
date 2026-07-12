"""Secondary-structure content of each folded poem, via PyMOL's DSS.

For every folded domain (cached PDB) we assign secondary structure with PyMOL's
``dss`` and count residues as helix (H), strand/sheet (S) or loop (L). Fractions
are aggregated per poem and written to ``results/secondary.csv``.

This is what lets us go beyond "all alpha helices": strand_pct surfaces the poems
whose proteins form beta sheets.
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

POEM_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from folding import DEFAULT_CACHE, _seq_hash  # noqa: E402
from pipeline import poem_chunks  # noqa: E402

PYMOL_BIN = "pymol"


def _domain_pdbs():
    """Yield (poem_stem, domain_index, pdb_path) for every cached domain."""
    for path in sorted((POEM_ROOT / "data" / "poems").glob("*.txt")):
        for i, seq in enumerate(poem_chunks(path.read_text(encoding="utf-8")), start=1):
            pdb = DEFAULT_CACHE / f"{_seq_hash(seq.strip().upper())}.pdb"
            if pdb.exists():
                yield path.stem, i, pdb


def _run_dss(jobs: list[tuple[str, Path]]) -> dict[str, tuple[int, int, int]]:
    """Run one PyMOL process to count H/S/L per structure; parse SSDATA lines."""
    lines = ["from pymol import cmd"]
    for name, pdb in jobs:
        lines += [
            "cmd.reinitialize()",
            f"cmd.load(r'{pdb}', 'm')",
            "cmd.dss('m')",
            "c = {'H': 0, 'S': 0, 'L': 0}",
            "cmd.iterate('m and name CA', \"c[ss if ss in ('H','S') else 'L'] += 1\","
            " space={'c': c})",
            f"print('SSDATA', '{name}', c['H'], c['S'], c['L'])",
        ]
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write("\n".join(lines) + "\n")
        script = fh.name

    proc = subprocess.run([PYMOL_BIN, "-cq", script], capture_output=True, text=True)
    Path(script).unlink(missing_ok=True)

    out: dict[str, tuple[int, int, int]] = {}
    for line in proc.stdout.splitlines():
        if line.startswith("SSDATA "):
            _, name, h, s, l = line.split()
            out[name] = (int(h), int(s), int(l))
    return out


def compute() -> Path:
    jobs = [(f"{stem}__d{i}", pdb) for stem, i, pdb in _domain_pdbs()]
    if not jobs:
        print("No cached structures. Run pipeline.py first.", file=sys.stderr)
        raise SystemExit(1)

    counts = _run_dss([(n, p) for n, p in jobs])

    # Aggregate domains -> per poem.
    per_poem: dict[str, list[int]] = {}
    for name, (h, s, l) in counts.items():
        stem = name.split("__d")[0]
        acc = per_poem.setdefault(stem, [0, 0, 0])
        acc[0] += h
        acc[1] += s
        acc[2] += l

    out = POEM_ROOT / "results" / "secondary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["poem", "residues_ss", "helix_pct", "strand_pct", "loop_pct"])
        rows = []
        for stem, (h, s, l) in per_poem.items():
            tot = h + s + l or 1
            rows.append((stem, tot, round(100 * h / tot, 1),
                         round(100 * s / tot, 1), round(100 * l / tot, 1)))
        rows.sort(key=lambda r: r[3], reverse=True)  # most beta-sheet first
        w.writerows(rows)

    print(f"\nSecondary structure (most beta-sheet first) -> {out.name}\n")
    print(f"  {'poem':<30} {'H%':>6} {'S%':>6} {'L%':>6}")
    print(f"  {'-'*30} {'-'*6} {'-'*6} {'-'*6}")
    for stem, tot, hp, sp, lp in rows:
        print(f"  {stem:<30} {hp:>6} {sp:>6} {lp:>6}")
    return out


if __name__ == "__main__":
    compute()
