"""Per-feature alignment of the mitogenomes, concatenated into one matrix.

Each mitochondrial feature is aligned across the six taxa on its own, then all
features are concatenated in reference (Podarcis) genomic order into a single
genome-wide alignment that the reconstruction engine treats as one supermatrix.

Two alignment currencies, both *reference-anchored* to the common wall lizard
(Podarcis muralis) — its residues/bases define the columns, and every other taxon
is pairwise-aligned to it:

- **protein-coding genes** → translation-guided codon alignment (the "pal2nal"
  idea): align amino acids, thread the original codons back so nucleotide columns
  stay in frame.
- **rRNA and tRNA** → nucleotide alignment directly (they do not code for protein).

Anchoring to one ingroup keeps the whole poem dependency-light (no external MSA
binary). Its cost: insertions relative to the reference are dropped and a taxon
missing the reference's column gets a gap (treated as missing data downstream).
For the protein-coding genes and tRNAs this is faithful; the rRNA expansion
segments are the roughest fit and simply read as extra uncertainty — which is
honest for a reconstruction this deep. Only features present in *all* taxa are
kept (their intersection); anything missing from a taxon's annotation is logged
and dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from Bio import SeqIO
from Bio.Align import PairwiseAligner, substitution_matrices
from Bio.Seq import Seq

from fetch_sequences import DATA_DIR, MITO_TABLE, REFERENCE, TAXA


@dataclass(frozen=True)
class Partition:
    """One feature's span within the concatenated alignment."""

    name: str    # e.g. "COX1", "rrnL", "trnL1"
    kind: str    # "CDS" | "rRNA" | "tRNA"
    start: int   # inclusive nucleotide index in the concatenation
    end: int     # exclusive


def load_features() -> dict[str, dict[str, tuple[str, str, int]]]:
    """species -> {feature_key: (nt, kind, ref_start)} from data/mito/*.fasta."""
    out: dict[str, dict[str, tuple[str, str, int]]] = {}
    for taxon in TAXA:
        path = DATA_DIR / f"{taxon.species.replace(' ', '_')}.fasta"
        feats: dict[str, tuple[str, str, int]] = {}
        for record in SeqIO.parse(path, "fasta"):
            key, kind, start = record.description.split("|")
            feats[key] = (str(record.seq).upper(), kind, int(start))
        out[taxon.species] = feats
    return out


def _protein_aligner() -> PairwiseAligner:
    aligner = PairwiseAligner()
    aligner.mode = "global"
    aligner.substitution_matrix = substitution_matrices.load("BLOSUM62")
    aligner.open_gap_score = -11
    aligner.extend_gap_score = -1
    return aligner


def _nucleotide_aligner() -> PairwiseAligner:
    aligner = PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.open_gap_score = -6
    aligner.extend_gap_score = -0.5
    return aligner


PROTEIN_ALIGNER = _protein_aligner()
NT_ALIGNER = _nucleotide_aligner()


def _anchor(ref_tokens: str, ref_units: list[str],
            seq_tokens: str, seq_units: list[str],
            aligner: PairwiseAligner, gap_unit: str) -> list[str]:
    """Project `seq` onto the reference's columns; one output unit per ref token.

    ``tokens`` are the strings actually aligned (amino acids for CDS, nucleotides
    otherwise); ``units`` are the emitted symbols (codons for CDS, single
    nucleotides otherwise). Reference columns are kept; seq insertions are dropped;
    missing reference columns become ``gap_unit``.
    """
    alignment = aligner.align(ref_tokens, seq_tokens)[0]
    ref_row, seq_row = alignment[0], alignment[1]
    out: list[str] = []
    seq_ptr = 0
    for ref_char, seq_char in zip(ref_row, seq_row):
        if seq_char != "-":
            unit = seq_units[seq_ptr]
            seq_ptr += 1
        else:
            unit = gap_unit
        if ref_char != "-":
            out.append(unit)
    return out


def _codons(nt: str) -> list[str]:
    return [nt[i : i + 3] for i in range(0, len(nt) - len(nt) % 3, 3)]


def _align_cds(ref_nt: str, seqs: dict[str, str]) -> dict[str, str]:
    ref_prot = str(Seq(ref_nt).translate(table=MITO_TABLE)).rstrip("*")
    ref_codons = _codons(ref_nt)[: len(ref_prot)]
    aligned = {REFERENCE: "".join(ref_codons)}
    for species, nt in seqs.items():
        if species == REFERENCE:
            continue
        prot = str(Seq(nt).translate(table=MITO_TABLE)).rstrip("*")
        codons = _codons(nt)[: len(prot)]
        units = _anchor(ref_prot, ref_codons, prot, codons,
                        PROTEIN_ALIGNER, "---")
        aligned[species] = "".join(units)
    return aligned


def _align_nt(ref_nt: str, seqs: dict[str, str]) -> dict[str, str]:
    aligned = {REFERENCE: ref_nt}
    ref_units = list(ref_nt)
    for species, nt in seqs.items():
        if species == REFERENCE:
            continue
        units = _anchor(ref_nt, ref_units, nt, list(nt), NT_ALIGNER, "-")
        aligned[species] = "".join(units)
    return aligned


def build_alignment() -> tuple[list[str], dict[str, str], list[Partition]]:
    """Return (taxa_order, concatenated alignment, partitions)."""
    features = load_features()
    taxa_order = [t.species for t in TAXA]

    shared = set.intersection(*(set(f) for f in features.values()))
    dropped = sorted(set(features[REFERENCE]) - shared)
    if dropped:
        print(f"  dropped {len(dropped)} feature(s) absent from some taxon: "
              f"{', '.join(dropped)}")

    # Reference genomic order.
    ordered = sorted(shared, key=lambda k: features[REFERENCE][k][2])

    concat: dict[str, list[str]] = {sp: [] for sp in taxa_order}
    partitions: list[Partition] = []
    cursor = 0
    for key in ordered:
        kind = features[REFERENCE][key][1]
        seqs = {sp: features[sp][key][0] for sp in taxa_order}
        ref_nt = seqs[REFERENCE]
        aligned = _align_cds(ref_nt, seqs) if kind == "CDS" else _align_nt(ref_nt, seqs)

        width = len(aligned[REFERENCE])
        assert all(len(s) == width for s in aligned.values()), f"ragged: {key}"
        for sp in taxa_order:
            concat[sp].append(aligned[sp])
        partitions.append(Partition(key, kind, cursor, cursor + width))
        cursor += width

    alignment = {sp: "".join(parts) for sp, parts in concat.items()}
    return taxa_order, alignment, partitions


def main() -> None:
    taxa_order, alignment, partitions = build_alignment()
    length = len(alignment[REFERENCE])
    n = {k: sum(1 for p in partitions if p.kind == k)
         for k in ("CDS", "rRNA", "tRNA")}
    print(f"\nConcatenated alignment: {len(taxa_order)} taxa x {length} nt "
          f"({length // 3} codon-equivalents)")
    print(f"  {len(partitions)} features: {n['CDS']} CDS, {n['rRNA']} rRNA, "
          f"{n['tRNA']} tRNA\n")
    for sp in taxa_order:
        gaps = alignment[sp].count("-")
        print(f"  {sp:<24} {gaps:>4} gap nt")


if __name__ == "__main__":
    main()
