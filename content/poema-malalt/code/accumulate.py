"""Accumulate many mutations on the evolving poem, appending to evolution.json.

Reaching 100+ mutations by hand is impractical, so this automates the loop with
the same guarantees as the interactive mode:
  * only known CONTENT-word slots mutate (each slot's part of speech is supplied
    below, so grammar/agreement is preserved and function words are never touched);
  * every mutation is a valid single-letter edit of the right part of speech,
    reasonably common (via code/evolve.candidates);
  * edit types follow the cancer spectrum (mostly substitutions);
  * a mutation is skipped if it would break Catalan article elision
    (e.g. "la" + vowel), and each slot never repeats a form (keeps it drifting).

The refrain "Res no és mesquí" has no viable adjective for "mesquí" and no verb
for "és", so it stays conserved on its own. Deterministic via a fixed RNG seed.

    python code/accumulate.py --target 120
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evolve import candidates, load_lexicon, DEFAULT_DICT  # noqa: E402
from main import letter_class  # noqa: E402

POEM_ROOT = HERE.parent
EVO = POEM_ROOT / "data" / "evolution.json"

LETTERS = set("abcdefghijklmnopqrstuvwxyzàèéíïóòúüç·")
VOWELS_H = set("aàáeèéiíïoòóuúüh")
# Preceding words that would need elision if the next word became vowel/h-initial.
ELIDING_PREV = {"el", "la", "de", "na", "del", "al", "pel", "dels", "als", "pels"}
TYPE_W = {"substitution": 0.90, "deletion": 0.07, "insertion": 0.03}

# Determiners and the (gender, number) they impose on the following noun, so a
# noun mutation keeps agreeing with its article ("la" stays feminine singular).
DET = {
    "el": ("M", "S"), "un": ("M", "S"), "del": ("M", "S"), "al": ("M", "S"), "pel": ("M", "S"),
    "tot": ("M", "S"), "la": ("F", "S"), "una": ("F", "S"), "tota": ("F", "S"),
    "els": ("M", "P"), "uns": ("M", "P"), "dels": ("M", "P"), "als": ("M", "P"),
    "les": ("F", "P"), "unes": ("F", "P"),
}

# Content-word slots for the CURRENT (post-24) poem: line index -> {word: POS}.
# POS supplied by hand (in-context), so mutations preserve part of speech.
MUTABLE = {
    0:  {"mesquí": "A"},
    1:  {"horta": "N", "isarda": "A"},
    2:  {"tosca": "A", "nit": "N"},
    3:  {"rosada": "N", "cara": "A"},
    4:  {"son": "N", "surt": "V"},
    5:  {"delit": "N", "bany": "N"},
    6:  {"lli": "N", "casa": "N", "feta": "A"},
    7:  {"mesquí": "A"},
    8:  {"ric": "A", "gata": "N", "colrada": "A"},
    9:  {"mal": "N", "viu": "V"},
    12: {"filla": "N", "vera": "A", "eternament": "R"},
    13: {"mesquí": "A"},
    14: {"dits": "N", "passen": "V"},
    15: {"arriba": "V", "sort": "N", "demanada": "A"},
    16: {"dissimula": "V", "clos": "N", "demanada": "A"},
    17: {"tornar": "V", "néixer": "V", "morir": "V"},
    18: {"plom": "N"},
    19: {"somriure": "N", "fix": "A"},
    20: {"dispersa": "V", "grills": "N", "taronja": "N"},
    21: {"mesquí": "A"},
    22: {"cançó": "N", "conta": "V", "bri": "N", "casa": "N"},
    23: {"avui": "R", "demà": "R", "ahir": "R"},
    24: {"roca": "N"},
    25: {"verge": "N", "jove": "A", "llet": "N", "pit": "N"},
}


def split_affix(token: str):
    """Split a token into (lead_punct, core, trail_punct)."""
    i, j = 0, len(token)
    while i < j and token[i].lower() not in LETTERS:
        i += 1
    while j > i and token[j - 1].lower() not in LETTERS:
        j -= 1
    return token[:i], token[i:j], token[j:]


def find_slot(line: str, word: str):
    """Return (token_index, lead, core, trail) for the token whose core == word."""
    toks = line.split(" ")
    for idx, tok in enumerate(toks):
        lead, core, trail = split_affix(tok)
        if core.lower() == word and "'" not in core and "-" not in core:
            return idx, lead, core, trail
    return None


def edit_type(a: str, b: str) -> str:
    if len(a) == len(b):
        return "substitution"
    return "insertion" if len(b) > len(a) else "deletion"


def reconstruct(evo) -> list[str]:
    lines = list(evo["original"])
    for st in evo["steps"]:
        lines[st["line"]] = st["line_after"]
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description="Accumulate mutations on the evolving poem.")
    ap.add_argument("--target", type=int, default=120, help="total number of mutations to reach")
    ap.add_argument("--min-freq", type=float, default=2.5, help="commonness floor for mutations")
    ap.add_argument("--rng-seed", type=int, default=42)
    args = ap.parse_args()

    evo = json.loads(EVO.read_text(encoding="utf-8"))
    lex = load_lexicon(DEFAULT_DICT)
    rng = random.Random(args.rng_seed)
    lines = reconstruct(evo)

    # Slots are fixed (line, token-index) positions. Letter-level edits never
    # change a line's token count, so indices stay stable and never collide with
    # a same-spelled word elsewhere in the line (as word-scanning would).
    slots, prev = [], {}
    for li, words in MUTABLE.items():
        for w, pos in words.items():
            fs = find_slot(lines[li], w)
            if fs is None:
                continue
            slots.append((li, fs[0], pos))
            prev[(li, fs[0])] = None  # last form left, to avoid immediate A->B->A

    n = len(evo["steps"])
    stalls = 0
    while n < args.target and stalls < 20000:
        li, tidx, pos = rng.choice(slots)
        toks = lines[li].split(" ")
        if tidx >= len(toks):
            stalls += 1
            continue
        lead, core, trail = split_affix(toks[tidx])
        word = core.lower()
        if not word or "'" in core or "-" in core:
            stalls += 1
            continue
        prev_core = split_affix(toks[tidx - 1])[1].lower() if tidx > 0 else ""

        allowed, weights = [], []
        for c in candidates(word, pos, lex, args.min_freq):
            if not c.strict:
                continue  # require full morphological agreement (no coarse fallback)
            if c.word == prev[(li, tidx)]:
                continue  # don't immediately revert (avoid A->B->A ping-pong)
            if prev_core in ELIDING_PREV and c.word[:1] in VOWELS_H:
                continue  # would need elision
            if pos == "N" and prev_core in DET and len(c.tag) >= 4:
                g, num = DET[prev_core]
                if c.tag[2] not in (g, "C") or c.tag[3] not in (num, "N"):
                    continue  # keep article–noun gender/number agreement
            allowed.append(c)
            weights.append(TYPE_W.get(c.edit, 0.5))
        if not allowed:
            stalls += 1
            continue

        c = rng.choices(allowed, weights=weights, k=1)[0]
        new_word = c.word.capitalize() if core[:1].isupper() else c.word
        toks[tidx] = lead + new_word + trail
        new_line = " ".join(toks)

        n += 1
        evo["steps"].append({
            "n": n, "line": li, "before": word, "after": c.word, "pos": pos,
            "edit": edit_type(word, c.word), "line_after": new_line,
        })
        lines[li] = new_line
        prev[(li, tidx)] = word  # the form we just left
        stalls = 0

    EVO.write_text(json.dumps(evo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # spectrum summary
    from collections import Counter
    ec = Counter(s["edit"] for s in evo["steps"])
    print(f"total mutations: {len(evo['steps'])}")
    print(f"edit spectrum: {dict(ec)}")
    print("\nfinal poem:\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
