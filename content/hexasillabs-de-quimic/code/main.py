"""Entry point for "Hexasíl·labs de químic".

The piece's core operation: take Catalan IUPAC molecule names, verbalise their
numbers and locant letters into spoken Catalan (2 → dos, N- → ena), and count the
poetic syllables (up to the last stress) with the Softcatalà engine
(``code/sillabes.js`` run headless with Node).

    python code/main.py "propan-2-ol" "àcid acètic"   # count the given names
    python code/main.py                                 # usage

The self-contained web page is built separately by ``code/build_web.py`` →
``index.html`` (poem-folder root).
"""

from __future__ import annotations

import sys

from molname import poetic_counts, verbalise


def main() -> None:
    names = sys.argv[1:]
    if not names:
        print(__doc__)
        return
    verbalised = [verbalise(n) for n in names]
    counts = poetic_counts(verbalised)
    for name, spoken, count in zip(names, verbalised, counts):
        shown = "—" if count is None else str(count)
        print(f"{shown:>3}  síl·labes  ·  {name}  →  {spoken}")


if __name__ == "__main__":
    main()
