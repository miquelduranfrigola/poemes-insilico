"""Entry point: reconstruct the extinct Banyoles lizard's cytb and render the poem.

The pipeline, end to end:

    fetch_sequences.py  complete mitogenomes of six living lizards (Entrez) [network]
    align.py            per-feature alignment, concatenated into one matrix
    reconstruct.py      ML ancestral sequence reconstruction (HKY85 + pruning)
    render.py           the 'haze' sequence into poem.md + a figure + sequence.html

By default this runs align -> reconstruct -> render from the committed sequences in
``data/mito`` (no network). Pass ``--fetch`` to refresh those sequences from NCBI
first (set ENTREZ_EMAIL, and optionally ENTREZ_API_KEY, in the environment).

    python code/main.py            # reconstruct + render from committed data
    python code/main.py --fetch    # re-download sequences, then reconstruct + render
"""

from __future__ import annotations

import sys

from align import build_alignment
from reconstruct import (fit_and_reconstruct, repair_cds_stops,
                         _write_outputs, summarise)
import render
import fetch_sequences


def main() -> None:
    if "--fetch" in sys.argv[1:]:
        print("Fetching mitogenomes from NCBI ...")
        fetch_sequences.main()
        print()

    print("Aligning mitogenome features (per-feature, concatenated) ...")
    _, alignment, partitions = build_alignment()

    print("Reconstructing the ancestral mitogenome (ML, HKY85) ...")
    rec = fit_and_reconstruct(alignment)
    repair_cds_stops(rec, partitions)
    _write_outputs(rec, partitions)
    summarise(rec, partitions)

    print("\nRendering poem + figure + sequence.html ...")
    render.main()


if __name__ == "__main__":
    main()
