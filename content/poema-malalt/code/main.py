"""Poema malalt — a word that mutates like a tumour, yet stays a valid word.

This is the computational engine behind the poem. Code and comments are in
English (repo convention); the words it produces are Catalan.

The idea
--------
A word is treated as a tiny genome. It mutates the way somatic mutations arise
in cancer, using the three classes of small mutations:

    substitution (SNV) -> replace one letter
    deletion     (del) -> remove one letter
    insertion    (ins) -> add one letter

Two biological facts are reproduced on purpose:

1. **Mutation-type spectrum.** In pan-cancer data, small somatic mutations are
   overwhelmingly substitutions (~90%); indels make up the rest (~10%), and among
   indels deletions clearly outnumber insertions. Defaults below encode that.

2. **Transition/transversion bias.** Within substitutions, cancer shows more
   transitions than transversions (Ti/Tv ~2). We map the purine/pyrimidine
   class structure onto **vowels vs consonants**: a substitution that keeps the
   class (vowel->vowel, consonant->consonant) is a "transition"; crossing the
   class is a "transversion". Transitions are weighted higher (``--titv``).

Selection = validity
--------------------
The constraint "the result must still be a real word" is not a cosmetic filter:
it *is* the model of selection. In a tumour most mutations are neutral
passengers, a few are drivers, and lethal ones are purged by purifying
selection (the cell dies). Here:

    invalid string  =  a lethal mutation (the cell does not survive)
    valid word      =  a viable cell that lives on

So there are two spectra, exactly as in real tumour genomics:

    * the *mutational process*  -> what we PROPOSE (calibrated to cancer)
    * the *surviving spectrum*  -> what we ACCEPT (reshaped by selection)

We measure both and report how selection shifted the spectrum.

Selection uses canonical dictionary headwords
---------------------------------------------
A mutation survives only if the result is a **canonical dictionary headword** — a
lemma of an open-class word (noun, verb, adjective, adverb). Inflected forms
(plurals, feminines, conjugations) are *not* valid, so lineages are made of
distinct, important dictionary words with no boring morphological repetition. The
headword set is built by ``code/build_lexicon.py`` from the DIEC-derived Softcatala
``catalan-dictionary`` and loaded here as a plain set (see ``load_lexicon``).

The object we grow
------------------
A **clonal tree** (a tumour phylogeny of words): the seed "cell" divides and
accumulates mutations along branches, and every node is a canonical Catalan word.

Usage
-----
    python code/main.py --seed cos --nodes 40
    python code/main.py --seed vida --nodes 60 --rng-seed 7 --emit-poem
"""

from __future__ import annotations

import argparse
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Alphabet and vowel/consonant classes (the "purine/pyrimidine" of letters)
# --------------------------------------------------------------------------- #
BASIC_VOWELS = "aeiou"
ACCENTED_VOWELS = "àèéíïóòúü"
CONSONANTS_STR = "bcdfghjklmnpqrstvwxyzç"

VOWELS = frozenset(BASIC_VOWELS + ACCENTED_VOWELS)
CONSONANTS = frozenset(CONSONANTS_STR)
ALPHABET = tuple(sorted(VOWELS | CONSONANTS))

# --------------------------------------------------------------------------- #
# Cancer-calibrated defaults (pan-cancer averages; tunable on the CLI)
# --------------------------------------------------------------------------- #
# Small somatic mutations are ~90% substitutions; indels ~10%, deletions >
# insertions. These are proposal probabilities for the mutational *process*.
DEFAULT_TYPE_WEIGHTS = {
    "substitution": 0.90,
    "deletion": 0.07,
    "insertion": 0.03,
}
# Transition:transversion ratio within substitutions (~2 in cancer).
DEFAULT_TITV = 2.0

# A surviving word must be at least this long and contain a vowel (a cheap shape
# guard; "importance" and canonicity come from the headword lexicon itself).
DEFAULT_MIN_LENGTH = 3

REPO_POEM_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEXICON = REPO_POEM_ROOT / "data" / "lexicon" / "lemmas.txt"


def letter_class(ch: str) -> str:
    """Return 'vowel', 'consonant' or 'other' for a single character."""
    if ch in VOWELS:
        return "vowel"
    if ch in CONSONANTS:
        return "consonant"
    return "other"


def looks_wordlike(word: str, min_length: int) -> bool:
    """Cheap shape guard: long enough and pronounceable (contains a vowel)."""
    return len(word) >= min_length and any(ch in VOWELS for ch in word)


# --------------------------------------------------------------------------- #
# Validity oracle (selection) — canonical dictionary headwords
# --------------------------------------------------------------------------- #
def load_lexicon(path: Path) -> frozenset[str]:
    """Load the canonical-headword set built by ``code/build_lexicon.py``.

    A word is viable iff it is one of these lemmas, so survivors are canonical,
    important dictionary words and no inflected form (plural/conjugation) can
    appear. Membership is O(1).
    """
    if not path.exists():
        raise SystemExit(
            f"lexicon not found at {path}\n"
            f"Build it first:  python code/build_lexicon.py"
        )
    words = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return frozenset(w for w in words if w)


# --------------------------------------------------------------------------- #
# The mutation model (the proposal distribution)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MutationEvent:
    """One proposed mutation and enough detail to build a spectrum from it."""

    kind: str  # 'substitution' | 'deletion' | 'insertion'
    position: int
    old: str = ""
    new: str = ""
    substitution_class: str = ""  # 'transition' | 'transversion' | '' (n/a)


class MutationModel:
    """Proposes cancer-like mutations of a word (before selection)."""

    def __init__(
        self,
        type_weights: dict[str, float] | None = None,
        titv: float = DEFAULT_TITV,
    ) -> None:
        weights = dict(type_weights or DEFAULT_TYPE_WEIGHTS)
        total = sum(weights.values())
        self.type_weights = {k: v / total for k, v in weights.items()}
        self.titv = titv
        self._kinds = list(self.type_weights)
        self._probs = [self.type_weights[k] for k in self._kinds]

    # -- substitution letter choice, with Ti/Tv bias ------------------------ #
    def _pick_substitute(self, old: str, rng: random.Random) -> tuple[str, str]:
        """Choose a replacement letter for ``old``; return (new, class)."""
        cls = letter_class(old)
        if cls == "vowel":
            same = [c for c in VOWELS if c != old]
            cross = list(CONSONANTS)
        elif cls == "consonant":
            same = [c for c in CONSONANTS if c != old]
            cross = list(VOWELS)
        else:  # unknown character: no class bias, replace with anything
            others = [c for c in ALPHABET if c != old]
            return rng.choice(others), "transversion"

        # transition (same class) with prob titv/(titv+1), else transversion
        if rng.random() < self.titv / (self.titv + 1.0):
            return rng.choice(same), "transition"
        return rng.choice(cross), "transversion"

    def propose(self, word: str, rng: random.Random) -> tuple[str, MutationEvent]:
        """Draw one mutation of ``word``. Returns (child_word, event).

        ``child_word`` may be empty (e.g. deleting the last letter) — callers
        treat empty / invalid results as lethal.
        """
        kind = rng.choices(self._kinds, weights=self._probs, k=1)[0]

        if kind == "substitution" and word:
            pos = rng.randrange(len(word))
            old = word[pos]
            new, sub_class = self._pick_substitute(old, rng)
            child = word[:pos] + new + word[pos + 1 :]
            return child, MutationEvent("substitution", pos, old, new, sub_class)

        if kind == "deletion" and word:
            pos = rng.randrange(len(word))
            old = word[pos]
            child = word[:pos] + word[pos + 1 :]
            return child, MutationEvent("deletion", pos, old=old)

        # insertion (also the fallback if word is empty)
        pos = rng.randrange(len(word) + 1)
        new = rng.choice(ALPHABET)
        child = word[:pos] + new + word[pos:]
        return child, MutationEvent("insertion", pos, new=new)


# --------------------------------------------------------------------------- #
# Spectrum bookkeeping (process vs survivors)
# --------------------------------------------------------------------------- #
@dataclass
class Spectrum:
    """Counts proposed vs viable mutations, to compare process and selection."""

    proposed: Counter = field(default_factory=Counter)
    viable: Counter = field(default_factory=Counter)
    proposed_titv: Counter = field(default_factory=Counter)
    viable_titv: Counter = field(default_factory=Counter)

    def record(self, event: MutationEvent, *, viable: bool) -> None:
        self.proposed[event.kind] += 1
        if event.substitution_class:
            self.proposed_titv[event.substitution_class] += 1
        if viable:
            self.viable[event.kind] += 1
            if event.substitution_class:
                self.viable_titv[event.substitution_class] += 1

    @staticmethod
    def _fmt(counter: Counter) -> str:
        total = sum(counter.values()) or 1
        parts = [
            f"{k}={counter.get(k, 0)} ({100 * counter.get(k, 0) / total:.1f}%)"
            for k in ("substitution", "deletion", "insertion")
        ]
        return "  ".join(parts)

    def report(self) -> str:
        lines = ["Mutational spectrum (mutation type):"]
        lines.append(f"  proposed (process) : {self._fmt(self.proposed)}")
        lines.append(f"  viable (survivors) : {self._fmt(self.viable)}")
        total_prop = sum(self.proposed.values()) or 1
        total_viab = sum(self.viable.values())
        lines.append(
            f"  viability (acceptance) rate: "
            f"{100 * total_viab / total_prop:.1f}% "
            f"({total_viab}/{total_prop} proposals survived)"
        )

        def titv_ratio(c: Counter) -> str:
            ts, tv = c.get("transition", 0), c.get("transversion", 0)
            return f"{ts}:{tv} (Ti/Tv={ts / tv:.2f})" if tv else f"{ts}:{tv}"

        lines.append("Transition/transversion (substitutions only):")
        lines.append(f"  proposed : {titv_ratio(self.proposed_titv)}")
        lines.append(f"  viable   : {titv_ratio(self.viable_titv)}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The clonal tree (a tumour phylogeny of words)
# --------------------------------------------------------------------------- #
@dataclass
class Node:
    word: str
    event: MutationEvent | None = None  # mutation that produced this node
    children: list["Node"] = field(default_factory=list)

    def depth(self) -> int:
        return 1 + max((c.depth() for c in self.children), default=0)

    def size(self) -> int:
        return 1 + sum(c.size() for c in self.children)


def _children_count(rng: random.Random, max_children: int) -> int:
    """How many times a cell tries to divide: mostly 1, sometimes more."""
    # Weighted toward a single child so lineages read as slow transformations,
    # with occasional branching (subclones).
    choices = list(range(1, max_children + 1))
    weights = [1.0 / (i + 1) for i in range(max_children)]  # 1:0.5:0.33...
    return rng.choices(choices, weights=weights, k=1)[0]


def grow_tree(
    seed: str,
    is_valid,
    model: MutationModel,
    rng: random.Random,
    n_nodes: int,
    max_children: int = 3,
    min_length: int = DEFAULT_MIN_LENGTH,
    attempt_cap: int = 600,
) -> tuple[Node, Spectrum]:
    """Grow a clonal tree of distinct canonical words from ``seed``.

    Each node "divides" a small number of times; every division does rejection
    sampling (propose a mutation, keep it only if the result is a novel canonical
    headword). ``attempt_cap`` bounds effort per division so dead ends stay leaves.
    """
    if not is_valid(seed):
        raise SystemExit(
            f"seed {seed!r} is not a canonical Catalan headword in the lexicon.\n"
            f"Try its dictionary form (singular / masculine / infinitive)."
        )

    spectrum = Spectrum()
    root = Node(seed)
    used = {seed}
    # Queue of cells still eligible to divide.
    dividing = [root]

    while dividing and len(used) < n_nodes:
        # Pop a random dividing cell for an organic (non-layered) shape.
        parent = dividing.pop(rng.randrange(len(dividing)))
        target = _children_count(rng, max_children)

        for _ in range(target):
            if len(used) >= n_nodes:
                break
            child = _spawn_child(
                parent, used, is_valid, model, rng, spectrum, min_length, attempt_cap
            )
            if child is not None:
                parent.children.append(child)
                used.add(child.word)
                dividing.append(child)

    return root, spectrum


def _spawn_child(parent, used, is_valid, model, rng, spectrum, min_length, attempt_cap):
    """Try to produce one novel, viable child of ``parent`` (or None).

    A mutation is "viable" (survives selection) only if the result is a canonical
    dictionary headword of word-like shape.
    """
    for _ in range(attempt_cap):
        child_word, event = model.propose(parent.word, rng)
        viable = looks_wordlike(child_word, min_length) and is_valid(child_word)
        spectrum.record(event, viable=viable)
        if viable and child_word not in used:
            return Node(child_word, event)
    return None


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render_tree(root: Node) -> str:
    """Render the clonal tree as an indented genealogy (ASCII box-drawing)."""
    lines = [root.word]

    def walk(node: Node, prefix: str) -> None:
        for i, child in enumerate(node.children):
            last = i == len(node.children) - 1
            branch = "└─ " if last else "├─ "
            lines.append(prefix + branch + child.word)
            walk(child, prefix + ("   " if last else "│  "))

    walk(root, "")
    return "\n".join(lines)


def longest_lineage(root: Node) -> list[str]:
    """Return the words along the deepest root-to-leaf path (a word ladder)."""
    best: list[str] = []

    def walk(node: Node, path: list[str]) -> None:
        nonlocal best
        path = path + [node.word]
        if not node.children:
            if len(path) > len(best):
                best = path
            return
        for child in node.children:
            walk(child, path)

    walk(root, [])
    return best


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--seed", required=True, help="the seed word (the first cell)")
    p.add_argument("--nodes", type=int, default=40, help="target number of words")
    p.add_argument("--max-children", type=int, default=3, help="max divisions per cell")
    p.add_argument(
        "--min-length", type=int, default=DEFAULT_MIN_LENGTH,
        help="minimum surviving word length (shape guard)",
    )
    p.add_argument("--titv", type=float, default=DEFAULT_TITV, help="transition:transversion ratio")
    p.add_argument("--sub", type=float, default=DEFAULT_TYPE_WEIGHTS["substitution"])
    p.add_argument("--dele", type=float, default=DEFAULT_TYPE_WEIGHTS["deletion"])
    p.add_argument("--ins", type=float, default=DEFAULT_TYPE_WEIGHTS["insertion"])
    p.add_argument("--attempts", type=int, default=600, help="rejection-sampling tries per division")
    p.add_argument("--rng-seed", type=int, default=0, help="RNG seed (reproducibility)")
    p.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON, help="canonical-headword list")
    p.add_argument("--emit-poem", action="store_true", help="write ../poem.md")
    return p


def main() -> None:
    args = build_arg_parser().parse_args()
    rng = random.Random(args.rng_seed)
    lexicon = load_lexicon(args.lexicon)
    is_valid = lexicon.__contains__
    model = MutationModel(
        type_weights={"substitution": args.sub, "deletion": args.dele, "insertion": args.ins},
        titv=args.titv,
    )

    root, spectrum = grow_tree(
        args.seed.lower(),
        is_valid,
        model,
        rng,
        n_nodes=args.nodes,
        max_children=args.max_children,
        min_length=args.min_length,
        attempt_cap=args.attempts,
    )

    tree_text = render_tree(root)
    print(tree_text)
    print()
    print(f"tree: {root.size()} words, depth {root.depth()}")
    lineage = longest_lineage(root)
    print("longest lineage: " + " → ".join(lineage))
    print()
    print(spectrum.report())

    if args.emit_poem:
        poem_path = REPO_POEM_ROOT / "poem.md"
        header = (
            f"# Poema malalt\n\n"
            f"<!-- Generated by code/main.py (seed {args.seed!r}, rng {args.rng_seed}). -->\n\n"
        )
        poem_path.write_text(header + "```\n" + tree_text + "\n```\n", encoding="utf-8")
        print(f"\nwrote {poem_path}")


if __name__ == "__main__":
    main()
