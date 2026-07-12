"""Render the reconstruction: the 'haze' sequence, a genome figure, an HTML block.

Everything is driven by the per-site posteriors in ``results/reconstruction.csv``:

1. **The haze sequence** injected into ``poem.md``. A confident site (posterior of
   the best base >= ``CONFIDENT``) is written as an UPPERCASE base — the bedrock the
   wall lizard and the monitor still share. An uncertain site is written in the real
   notation of doubt: the lowercase IUPAC **ambiguity code** for the smallest set of
   bases whose posterior sums past ``COVER``. Where ~170 My erased the signal, the
   ancestor is literally spelled in the alphabet of uncertainty.

2. **A genome figure** (``results/reconstruction.png``): per-feature mean posterior
   laid out along the mitogenome (the confidence landscape — conserved rRNA/COX vs
   variable ND/ATP8), plus mean posterior by codon position across the coding genes
   (the third-position 'wobble'). matplotlib only, cream palette.

3. **A styled text block** (``results/sequence.html``) in the *poemes-proteics*
   look (cream ground, Space Mono), for embedding in a web page.
"""

from __future__ import annotations

import csv
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap  # noqa: F401 (kept for tweaks)
from matplotlib.patches import Patch

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
POEM_PATH = Path(__file__).resolve().parent.parent / "poem.md"

CONFIDENT = 0.90   # posterior above which a base is written solid (uppercase)
COVER = 0.90       # cumulative posterior an ambiguity code must cover
LINE_WIDTH = 60    # nucleotides per line in the poem / html block

BEGIN = "<!-- BEGIN generated-sequence"
END = "<!-- END generated-sequence -->"

# Cream museum palette (shared look across the gallery); one colour per feature kind.
CREAM = "#f0ebe6"
INK = "#282828"
MUTED = "#8f887d"
RUST = "#a6552f"
GREEN = "#2f7d68"
KIND_COLOR = {"CDS": INK, "rRNA": RUST, "tRNA": GREEN}
KIND_LABEL = {"CDS": "gens de proteïna", "rRNA": "ARN ribosòmic", "tRNA": "ARN de transferència"}

IUPAC = {
    frozenset("A"): "A", frozenset("C"): "C", frozenset("G"): "G",
    frozenset("T"): "T", frozenset("AG"): "R", frozenset("CT"): "Y",
    frozenset("AC"): "M", frozenset("GT"): "K", frozenset("AT"): "W",
    frozenset("CG"): "S", frozenset("ACG"): "V", frozenset("ACT"): "H",
    frozenset("AGT"): "D", frozenset("CGT"): "B", frozenset("ACGT"): "N",
}
BASES = "ACGT"


def kind_of(name: str) -> str:
    if name.startswith("trn"):
        return "tRNA"
    if name in ("rrnS", "rrnL"):
        return "rRNA"
    return "CDS"


def load_reconstruction():
    """Return (map_bases, posteriors, full[4,n], features[list of name per site])."""
    rows = list(csv.DictReader((RESULTS_DIR / "reconstruction.csv").open()))
    map_bases = [r["map_base"] for r in rows]
    posteriors = np.array([float(r["posterior"]) for r in rows])
    full = np.array([[float(r[f"p{b}"]) for r in rows] for b in BASES])
    features = [r["feature"] for r in rows]
    return map_bases, posteriors, full, features


def partitions_from_features(features: list[str]):
    """Contiguous runs -> list of (name, kind, start, end)."""
    parts = []
    start = 0
    for i in range(1, len(features) + 1):
        if i == len(features) or features[i] != features[start]:
            name = features[start]
            parts.append((name, kind_of(name), start, i))
            start = i
    return parts


def _ambiguity_code(site_posterior: np.ndarray) -> str:
    order = np.argsort(site_posterior)[::-1]
    chosen: set[str] = set()
    total = 0.0
    for idx in order:
        chosen.add(BASES[idx])
        total += site_posterior[idx]
        if total >= COVER:
            break
    return IUPAC[frozenset(chosen)].lower()


def haze_sequence(map_bases, posteriors, full) -> str:
    out = []
    for pos, (base, post) in enumerate(zip(map_bases, posteriors)):
        out.append(base.upper() if post >= CONFIDENT
                   else _ambiguity_code(full[:, pos]))
    return "".join(out)


# --- poem.md injection ------------------------------------------------------

def build_poem_block(haze: str, posteriors: np.ndarray) -> str:
    lines = ["```text"]
    for start in range(0, len(haze), LINE_WIDTH):
        lines.append(f"{start + 1:>6}  {haze[start:start + LINE_WIDTH]}")
    lines.append("```")
    confident = (posteriors >= CONFIDENT).mean()
    lines += ["", f"*{len(haze)} bases del genoma mitocondrial · "
                  f"{confident:.0%} segures · {1 - confident:.0%} en la boira del temps*"]
    return "\n".join(lines)


def inject_into_poem(block: str) -> None:
    text = POEM_PATH.read_text(encoding="utf-8")
    begin_line_end = text.index("-->", text.index(BEGIN)) + len("-->")
    end_at = text.index(END)
    POEM_PATH.write_text(
        text[:begin_line_end] + "\n" + block + "\n" + text[end_at:], encoding="utf-8")


# --- figure -----------------------------------------------------------------

def make_figure(posteriors: np.ndarray, partitions) -> None:
    fig, (ax_map, ax_pos) = plt.subplots(
        2, 1, figsize=(10, 6), height_ratios=[3, 1],
        gridspec_kw={"hspace": 0.55})
    fig.patch.set_facecolor(CREAM)

    # Panel A: per-feature mean posterior laid out along the mitogenome.
    ax_map.set_facecolor(CREAM)
    for name, kind, start, end in partitions:
        mean = posteriors[start:end].mean()
        ax_map.bar(start, mean, width=end - start, align="edge",
                   color=KIND_COLOR[kind], edgecolor=CREAM, linewidth=0.4)
        if kind in ("CDS", "rRNA") and (end - start) >= 600:
            ax_map.text((start + end) / 2, mean + 0.004, name, rotation=90,
                        ha="center", va="bottom", fontsize=7, color=INK)
    overall = posteriors.mean()
    ax_map.axhline(overall, color=MUTED, lw=0.8, ls="--")
    ax_map.text(len(posteriors), overall, f" mitjana {overall:.2f}",
                va="center", fontsize=8, color=MUTED)
    ax_map.set_xlim(0, len(posteriors))
    ax_map.set_ylim(0.86, 1.0)
    ax_map.set_title("Genoma mitocondrial de la sargantana de l'avi — "
                     "certesa de la reconstrucció per gen",
                     color=INK, fontsize=12, pad=12)
    ax_map.set_xlabel("posició al genoma (bp)", color=INK, fontsize=9)
    ax_map.set_ylabel("posterior mitjà", color=INK, fontsize=9)
    ax_map.legend(handles=[Patch(facecolor=KIND_COLOR[k], label=KIND_LABEL[k])
                           for k in ("CDS", "rRNA", "tRNA")],
                  loc="lower right", fontsize=8, frameon=False)
    for spine in ("top", "right"):
        ax_map.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax_map.spines[spine].set_color(INK)
    ax_map.tick_params(colors=INK, labelsize=8)

    # Panel B: mean posterior by codon position across the coding genes.
    cds_pos = {0: [], 1: [], 2: []}
    for name, kind, start, end in partitions:
        if kind != "CDS":
            continue
        for off, site in enumerate(range(start, end)):
            cds_pos[off % 3].append(posteriors[site])
    by_pos = [float(np.mean(cds_pos[i])) for i in range(3)]
    ax_pos.set_facecolor(CREAM)
    bars = ax_pos.bar(["1a", "2a", "3a"], by_pos, color=[INK, INK, RUST], width=0.6)
    ax_pos.set_ylim(0, 1)
    ax_pos.set_title("Certesa mitjana per posició del codó (gens de proteïna)",
                     color=INK, fontsize=11, pad=8)
    ax_pos.set_ylabel("posterior", color=INK, fontsize=9)
    for bar, val in zip(bars, by_pos):
        ax_pos.text(bar.get_x() + bar.get_width() / 2, val + 0.02, f"{val:.2f}",
                    ha="center", color=INK, fontsize=9)
    for spine in ("top", "right"):
        ax_pos.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax_pos.spines[spine].set_color(INK)
    ax_pos.tick_params(colors=INK, labelsize=8)

    fig.savefig(RESULTS_DIR / "reconstruction.png", dpi=150,
                facecolor=CREAM, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    map_bases, posteriors, full, features = load_reconstruction()
    partitions = partitions_from_features(features)
    haze = haze_sequence(map_bases, posteriors, full)
    inject_into_poem(build_poem_block(haze, posteriors))
    make_figure(posteriors, partitions)
    print(f"Injected {len(haze)}-base haze sequence into {POEM_PATH.name}")
    print(f"Wrote {RESULTS_DIR / 'reconstruction.png'} "
          f"(run code/build_web.py for results/index.html)")


if __name__ == "__main__":
    main()
