"""Build the canonical-headword lexicon used as this poem's validity oracle.

Why this exists
---------------
A spell-checker word list (like Hunspell) accepts *every inflected form* and
carries no lemma/part-of-speech data, so mutation trees fill with plurals,
feminines and verb conjugations of the same word. Instead we build the set of
**canonical dictionary headwords** (lemmas) of **open-class** words, so a mutated
string is "valid" only if it is a real, important dictionary word — and plural /
conjugation repetition is impossible by construction.

Source
------
Softcatala ``catalan-dictionary`` (dual LGPL-2.1 / GPL-2.0), a form -> lemma ->
POS table of ~1.18M rows, built from the DIEC + DNV normative dictionaries. This
is the practical, legal path to "official dictionary" words (the DIEC itself has
no bulk download). Each line is ``form lemma TAG`` (space-separated); the tag is
the FreeLing/EAGLES tagset whose first letter is the coarse part of speech.

Output
------
``data/lexicon/lemmas.txt`` — one canonical lemma per line, sorted, unique
(gitignored, reproducible). ``main.py`` loads it into a set.

Usage
-----
    python code/build_lexicon.py                 # download + build (sensible default)
    python code/build_lexicon.py --min-freq 3.0  # stricter: keep only more common words
"""

from __future__ import annotations

import argparse
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from wordfreq import zipf_frequency

DATA_URL = "https://huggingface.co/datasets/softcatala/catalan-dictionary/resolve/main/data.zip"
INNER_NAME = "diccionari.txt"

POEM_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = POEM_ROOT / "data" / "lexicon" / "lemmas.txt"

# Default "how common must a word be" floor, on wordfreq's Zipf scale (higher =
# only more common words). 2.5 keeps ~18k everyday headwords — the sensible
# default; you shouldn't normally need to change it.
DEFAULT_MIN_FREQ = 2.5

# Open-class parts of speech (FreeLing tagset, first letter): Noun, Verb,
# Adjective, adveRb. Proper nouns (tag starts "NP") are excluded separately.
OPEN_CLASS = frozenset("NVAR")

# Characters allowed in a Catalan headword (letters + accents + c-cedilla +
# the l.l middot). Anything with a space, apostrophe, digit or hyphen is dropped.
LETTERS = frozenset("abcdefghijklmnopqrstuvwxyzàèéíïóòúüç·")


def _is_wordlike(token: str) -> bool:
    return bool(token) and all(ch in LETTERS for ch in token)


def download_dictionary(dest: Path) -> None:
    """Download the catalan-dictionary archive and extract diccionari.txt."""
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "data.zip"
        print(f"Downloading {DATA_URL} ...")
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "poemes-insilico/1.0"})
        with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as fh:
            fh.write(resp.read())
        with zipfile.ZipFile(zip_path) as zf:
            zf.extract(INNER_NAME, dest)
    print(f"Extracted {dest / INNER_NAME}")


def build_lemmas(dic_path: Path, min_freq: float) -> list[str]:
    """Return sorted canonical open-class lemmas above the importance floor.

    Importance of a lemma = the highest wordfreq Zipf score among its inflected
    forms (max over forms, so a common verb survives via its common conjugations
    even if the bare infinitive is rarer). ``min_freq`` is on that Zipf scale:
    higher = keep only more common words (~2.5 everyday, ~3.0 stricter).
    """
    lemma_best: dict[str, float] = {}
    with open(dic_path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) != 3:
                continue
            form, lemma, tag = parts
            if tag[0] not in OPEN_CLASS or tag[:2] == "NP":
                continue
            lemma = lemma.lower()
            if not _is_wordlike(lemma):
                continue
            z = zipf_frequency(form.lower(), "ca")
            if z > lemma_best.get(lemma, -1.0):
                lemma_best[lemma] = z
    return sorted(w for w, z in lemma_best.items() if z >= min_freq)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the canonical-headword lexicon.")
    parser.add_argument(
        "--min-freq", type=float, default=DEFAULT_MIN_FREQ,
        help="how common a word must be to count (higher = keep only more common words)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output lemma list path")
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    dic_path = args.out.parent / INNER_NAME
    if not dic_path.exists():
        download_dictionary(args.out.parent)

    lemmas = build_lemmas(dic_path, args.min_freq)
    args.out.write_text("\n".join(lemmas) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} ({len(lemmas)} canonical lemmas, min-freq {args.min_freq})")


if __name__ == "__main__":
    main()
