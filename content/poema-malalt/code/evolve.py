"""Evolving-poem mode — mutate a poem word by word, keeping it a valid text.

Companion to ``main.py`` (which grows a clonal tree from a single word). Here the
whole poem is the genome and each **word is a gene**. We mutate one word with the
same cancer-calibrated single-letter edits, but a mutation only survives if it is:

    1. a real Catalan word,
    2. the **same part of speech / morphology** as the original (so the poem stays
       grammatical — noun->noun, adjective->adjective, with gender/number/tense
       agreement preserved when possible), and
    3. semantically plausible — judged by a human/LLM reader, not by this script.

This module handles (1) and (2): given a word and its part of speech, it lists the
valid, agreement-matching, reasonably-common single-edit mutations. A reader (the
poet, or an LLM) supplies the part of speech from context and judges (3), then
picks a candidate and moves on — so the poem visibly evolves while staying alive.

Part of speech is one of: N (noun), V (verb), A (adjective), R (adverb). Proper
nouns are always excluded.

Usage
-----
    python code/evolve.py --word fosca --pos A          # list candidates
    python code/evolve.py --word calla --pos V
    python code/evolve.py --word gat --pos N --propose 5   # cancer-weighted draws
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from pathlib import Path

from wordfreq import zipf_frequency

# Reuse the alphabet and the cancer-calibrated mutation model from the tree engine.
from main import ALPHABET, VOWELS, MutationModel

POEM_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DICT = POEM_ROOT / "data" / "lexicon" / "diccionari.txt"

OPEN_CLASS = frozenset("NVAR")
DEFAULT_MIN_FREQ = 3.0  # poems: a bit stricter than the tree, plausibility matters
POS_NAMES = {"N": "noun", "V": "verb", "A": "adjective", "R": "adverb"}


# --------------------------------------------------------------------------- #
# Lexicon: form -> set of open-class morphological tags (FreeLing tagset)
# --------------------------------------------------------------------------- #
def load_lexicon(path: Path) -> dict[str, set[str]]:
    """Load ``form -> {tags}`` keeping only open-class, non-proper-noun tags."""
    if not path.exists():
        raise SystemExit(
            f"lexicon not found at {path}\n"
            f"Build it first:  python code/build_lexicon.py  (it downloads diccionari.txt)"
        )
    lex: dict[str, set[str]] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) != 3:
                continue
            form, _lemma, tag = parts
            if tag[0] not in OPEN_CLASS or tag[:2] == "NP":
                continue
            lex.setdefault(form.lower(), set()).add(tag)
    return lex


# --------------------------------------------------------------------------- #
# Single-edit neighbours and candidate selection
# --------------------------------------------------------------------------- #
def single_edit_neighbors(word: str) -> set[str]:
    """All strings one substitution, insertion or deletion away from ``word``."""
    out: set[str] = set()
    for i in range(len(word)):
        for c in ALPHABET:
            if c != word[i]:
                out.add(word[:i] + c + word[i + 1 :])   # substitution
        out.add(word[:i] + word[i + 1 :])                # deletion
    for i in range(len(word) + 1):
        for c in ALPHABET:
            out.add(word[:i] + c + word[i:])             # insertion
    out.discard(word)
    return out


def edit_type(src: str, dst: str) -> str:
    """Classify a single edit by length change (inputs are known 1-edit apart)."""
    if len(dst) == len(src):
        return "substitution"
    return "insertion" if len(dst) > len(src) else "deletion"


@dataclass
class Candidate:
    word: str
    tag: str          # the matched tag
    edit: str         # substitution | insertion | deletion
    zipf: float
    strict: bool      # True = full-tag (agreement) match, False = coarse-POS fallback


def candidates(word: str, pos: str, lex: dict[str, set[str]], min_freq: float) -> list[Candidate]:
    """Valid, POS-preserving, common single-edit mutations of ``word``.

    Prefers full morphological agreement (a shared full tag with ``word``); falls
    back to the broad part of speech only if no strict candidate exists. Results
    are sorted by real-usage frequency, most common first.
    """
    word = word.lower()
    own_tags = {t for t in lex.get(word, set()) if t[0] == pos}  # agreement tags

    strict: list[Candidate] = []
    coarse: list[Candidate] = []
    for cand in single_edit_neighbors(word):
        tags = lex.get(cand)
        if not tags:
            continue
        pos_tags = [t for t in tags if t[0] == pos]
        if not pos_tags:
            continue
        z = zipf_frequency(cand, "ca")
        if z < min_freq:
            continue
        shared = own_tags & set(pos_tags)
        if shared:
            strict.append(Candidate(cand, sorted(shared)[0], edit_type(word, cand), z, True))
        else:
            coarse.append(Candidate(cand, pos_tags[0], edit_type(word, cand), z, False))

    chosen = strict if strict else coarse
    chosen.sort(key=lambda c: c.zipf, reverse=True)
    return chosen


def propose(word: str, pos: str, lex: dict[str, set[str]], min_freq: float,
            n: int, model: MutationModel, rng: random.Random, attempt_cap: int = 2000) -> list[Candidate]:
    """Draw up to ``n`` distinct viable mutations using cancer-weighted proposals."""
    pool = {c.word: c for c in candidates(word, pos, lex, min_freq)}
    if not pool:
        return []
    picks: list[Candidate] = []
    seen: set[str] = set()
    for _ in range(attempt_cap):
        child, _event = model.propose(word.lower(), rng)
        if child in pool and child not in seen:
            seen.add(child)
            picks.append(pool[child])
            if len(picks) >= n:
                break
    return picks


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _print_candidates(word: str, pos: str, cands: list[Candidate]) -> None:
    kind = "strict agreement" if (cands and cands[0].strict) else "broad-POS fallback"
    header = f"{word}  ({POS_NAMES.get(pos, pos)})"
    if not cands:
        print(f"{header}: no viable {POS_NAMES.get(pos, pos)} mutations found")
        return
    print(f"{header} — {len(cands)} candidate(s) [{kind}]:")
    for c in cands:
        agree = "" if c.strict else "  (broad)"
        print(f"  {c.word:14} {c.tag:9} {c.edit:12} zipf={c.zipf:.2f}{agree}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--word", required=True, help="the word (gene) to mutate")
    p.add_argument("--pos", required=True, choices=sorted(OPEN_CLASS), help="its part of speech")
    p.add_argument("--min-freq", type=float, default=DEFAULT_MIN_FREQ,
                   help="how common a mutated word must be (higher = only more common)")
    p.add_argument("--propose", type=int, default=0, metavar="N",
                   help="instead of listing all, draw N cancer-weighted viable mutations")
    p.add_argument("--titv", type=float, default=2.0, help="transition:transversion ratio")
    p.add_argument("--rng-seed", type=int, default=0, help="RNG seed for --propose")
    p.add_argument("--dict", type=Path, default=DEFAULT_DICT, help="form->POS lexicon path")
    args = p.parse_args()

    lex = load_lexicon(args.dict)

    if args.propose:
        model = MutationModel(titv=args.titv)
        rng = random.Random(args.rng_seed)
        cands = propose(args.word, args.pos, lex, args.min_freq, args.propose, model, rng)
        print(f"{args.word} — {len(cands)} cancer-weighted draw(s):")
        for c in cands:
            print(f"  {c.word:14} {c.tag:9} {c.edit:12} zipf={c.zipf:.2f}")
    else:
        _print_candidates(args.word, args.pos, candidates(args.word, args.pos, lex, args.min_freq))


if __name__ == "__main__":
    main()
