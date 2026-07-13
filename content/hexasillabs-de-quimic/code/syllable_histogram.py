#!/usr/bin/env python3
"""Count Catalan (poetic) syllables of every molecule name in the Wikidata pool
and plot the length distribution.

Pipeline:
  1. Read data/wikidata-ca.csv (unique Catalan names).
  2. Verbalise each name (see verbalise()): spell out locant digits and isolated
     letter locants, drop bracketed stereo descriptors. This is a FIRST, simplified
     version of the poem's verbalisation standard, enough to measure length.
  3. Feed the verbalised names to code/sillabes.js (Softcatala engine, headless)
     and read the *poetic* count (up to the last stressed syllable = verse metre).
  4. Write data/syllables-ca.csv and plot data/syllable-histogram.png (matplotlib).

Run (needs a conda env with matplotlib + Node on PATH):
  conda run -n <env> python code/syllable_histogram.py
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from molname import verbalise, poetic_counts

HERE = os.path.dirname(os.path.abspath(__file__))
POEM = os.path.dirname(HERE)
CSV_IN = os.path.join(POEM, "data", "wikidata-ca.csv")
CSV_OUT = os.path.join(POEM, "data", "syllables-ca.csv")
FIG_OUT = os.path.join(POEM, "data", "syllable-histogram.png")


# --- Plot --------------------------------------------------------------------

def plot_histogram(ax, counts):
    """Bar chart of how many names have each poetic syllable length."""
    lo, hi = min(counts), max(counts)
    xs = list(range(lo, hi + 1))
    freq = {x: 0 for x in xs}
    for c in counts:
        freq[c] += 1
    ys = [freq[x] for x in xs]
    ax.bar(xs, ys, color="#3b6ea5", edgecolor="white", linewidth=0.4)
    # Mark the classical Catalan metres.
    for metre, name in [(8, "octosíl·lab"), (10, "decasíl·lab"), (12, "alexandrí")]:
        if lo <= metre <= hi:
            ax.axvline(metre, color="#d1662a", linestyle="--", linewidth=1.2, zorder=3)
            ax.text(metre, max(ys) * 0.97, name, rotation=90, va="top", ha="right",
                    color="#d1662a", fontsize=8)
    ax.set_xlabel("Síl·labes poètiques (fins a l'última tònica)")
    ax.set_ylabel("Nombre de noms de molècula")
    ax.set_title("Llargada sil·làbica dels noms de molècules (Wikidata, català)")
    ax.set_xticks([x for x in xs if x % 2 == 0])
    ax.spines[["top", "right"]].set_visible(False)


def main():
    names = sorted({r["name_ca"] for r in csv.DictReader(open(CSV_IN))})
    verb = [verbalise(n) for n in names]
    pairs = [(n, v) for n, v in zip(names, verb) if v]     # drop empties
    names, verb = [p[0] for p in pairs], [p[1] for p in pairs]

    counts = poetic_counts(verb)

    with open(CSV_OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name_ca", "verbalised", "poetic_syllables"])
        for n, v, c in zip(names, verb, counts):
            w.writerow([n, v, c if c is not None else ""])

    valid = [c for c in counts if c is not None]
    valid.sort()
    n = len(valid)
    median = valid[n // 2]
    mode = max(set(valid), key=valid.count)
    print(f"names counted: {n}")
    print(f"min={valid[0]}  median={median}  mode={mode}  max={valid[-1]}")
    for m in (7, 8, 10, 12):
        print(f"  = {m} syllables: {valid.count(m)} names")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    plot_histogram(ax, valid)
    fig.tight_layout()
    fig.savefig(FIG_OUT, dpi=200)
    print(f"wrote {CSV_OUT}\nwrote {FIG_OUT}")


if __name__ == "__main__":
    main()
