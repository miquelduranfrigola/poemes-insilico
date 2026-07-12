"""Encode Catalan text into a protein (amino-acid) sequence, and back.

The rubric maps each Catalan character to one amino-acid one-letter code, or to a
two-letter code introduced by the escape residue ``W``. It is designed to be:

- **Consistent 1:1** — every amino-acid letter maps to the Catalan letter of the
  same name (``a→A``, ``c→C``, ``k→K``, ... including ``y→Y``, native in the digraph
  "ny"). The one exception is ``w``: the residue ``W`` is reserved as the escape, so
  Catalan "w" is written ``WW``.
- **Reversible** — the code is prefix-free, so a protein decodes back to the exact
  (accent-collapsed) Catalan text. See ``decode``.

``W`` is the escape prefix for every Catalan character that has no amino acid of its
own name (``o u b j x z ç l·l`` and "w" itself). Accents are collapsed to the base
vowel (à→a, è/é→e, í/ï→i, ò/ó→o, ú/ü→u), so encoding is case- and accent-insensitive
and decoding yields unaccented Catalan. ç is kept distinct (it is a grapheme in its
own right, coded ``WK``, not a decorated c).
"""

from __future__ import annotations

import sys
import unicodedata

# --- The rubric -------------------------------------------------------------

ESCAPE = "W"

# 19 direct 1:1 mappings: every amino-acid letter except W maps to its own Catalan
# letter (k → K included, as it should be).
SINGLES: dict[str, str] = {
    "a": "A", "c": "C", "d": "D", "e": "E", "f": "F", "g": "G", "h": "H",
    "i": "I", "k": "K", "l": "L", "m": "M", "n": "N", "p": "P", "q": "Q",
    "r": "R", "s": "S", "t": "T", "v": "V", "y": "Y",
}

# Two-letter codes, all introduced by the escape residue W, for the Catalan
# characters with no amino acid of their own name. Second letters are chosen to be
# mnemonic where Catalan phonology (or shape) allows.
PAIRS: dict[str, str] = {
    "o": "WQ",   # Q is the round, O-shaped letter
    "u": "WV",   # U and V were one letter in Latin
    "b": "WP",   # b = voiced p
    "j": "WG",   # Catalan j = soft g (same sound)
    "z": "WS",   # z = voiced s
    "x": "WH",   # the /ʃ/ "ix" sound
    "ç": "WK",   # c-trencada (keeps K free for the real "k")
    "w": "WW",   # W is the escape, so Catalan "w" doubles it
    "l·l": "WL",  # geminate l, kept distinct from the digraph "ll" -> LL
}

# Private sentinels used during encoding so multi-codepoint units survive
# accent-stripping and per-character iteration.
_CEDILLA = "\x00"    # protects ç from accent normalization
_GEMINATE = "\x01"   # marks the "l·l" geminate as one unit

# Derived reverse tables (built once).
_SINGLE_DECODE = {v: k for k, v in SINGLES.items()}
_PAIR_DECODE = {v: k for k, v in PAIRS.items()}


def _strip_accents(text: str) -> str:
    """Collapse accented vowels to their base letter, but keep ç.

    ç is protected (it is a distinct grapheme with its own code WC, not a decorated
    c) by swapping it for a sentinel before Unicode decomposition, then restoring it.
    """
    protected = text.replace("ç", _CEDILLA).replace("Ç", _CEDILLA)
    decomposed = unicodedata.normalize("NFD", protected)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.replace(_CEDILLA, "ç")


def encode(text: str) -> str:
    """Encode Catalan text into an amino-acid sequence.

    Letters map per the rubric; spaces are preserved; any other character
    (punctuation, digits, ...) is dropped. Output is uppercase amino-acid codes.
    """
    text = _strip_accents(text).lower()
    text = text.replace("l·l", _GEMINATE).replace("ŀ", _GEMINATE)  # ŀ = U+0140

    out: list[str] = []
    for ch in text:
        if ch == _GEMINATE:
            out.append(PAIRS["l·l"])
        elif ch == " ":
            out.append(" ")
        elif ch in SINGLES:
            out.append(SINGLES[ch])
        elif ch in PAIRS:
            out.append(PAIRS[ch])
        # else: drop punctuation / unknown characters
    return "".join(out)


def decode(protein: str) -> str:
    """Decode an amino-acid sequence back to (accent-collapsed) Catalan.

    The code is prefix-free: the escape residue W starts a two-letter code,
    everything else is a single. Unknown symbols are skipped.
    """
    protein = protein.upper()
    out: list[str] = []
    i = 0
    n = len(protein)
    while i < n:
        ch = protein[i]
        if ch == " ":
            out.append(" ")
            i += 1
        elif ch == ESCAPE and i + 1 < n:
            out.append(_PAIR_DECODE.get(protein[i : i + 2], ""))
            i += 2
        else:
            out.append(_SINGLE_DECODE.get(ch, ""))
            i += 1
    return "".join(out)


def _selftest() -> None:
    """Round-trip check on a handful of Catalan samples (accent-collapsed)."""
    samples = [
        ("Catalunya", "catalunya"),
        ("molècula", "molecula"),
        ("força", "força"),
        ("peix", "peix"),
        ("zel", "zel"),
        ("ela l·la", "ela l·la"),
        ("jo bec", "jo bec"),
    ]
    ok = True
    for original, expected_plain in samples:
        enc = encode(original)
        dec = decode(enc)
        passed = dec == expected_plain
        ok = ok and passed
        print(f"  [{'ok' if passed else 'FAIL'}] {original!r} -> {enc} -> {dec!r}")
    print("selftest:", "all round-trips passed" if ok else "FAILURES above")


def main() -> None:
    """CLI: encode Catalan -> protein, or decode with --decode.

    Usage:
      python code/main.py "Catalunya"             # encode
      python code/main.py --decode "CATALWVNYA"   # decode
      echo "molecula" | python code/main.py       # encode from stdin
      python code/main.py --selftest              # round-trip demo
    """
    args = sys.argv[1:]
    if "--selftest" in args:
        _selftest()
        return

    do_decode = "--decode" in args
    args = [a for a in args if a != "--decode"]

    text = " ".join(args) if args else sys.stdin.read().strip()
    if not text:
        print("No input. Pass text as arguments or on stdin.", file=sys.stderr)
        raise SystemExit(1)

    print(decode(text) if do_decode else encode(text))


if __name__ == "__main__":
    main()
