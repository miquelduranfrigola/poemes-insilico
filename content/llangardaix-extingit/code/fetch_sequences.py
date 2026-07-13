"""Fetch complete mitochondrial genomes for the lizards we reconstruct from.

The extinct Banyoles lizard of the poem is the *reconstructed common ancestor* of
the common wall lizard (``Podarcis muralis``) and the Komodo dragon
(``Varanus komodoensis``). To reconstruct it we need homologous sequence from
living relatives that bracket the ancestral node, plus an outgroup to root it:

    Lacertoidea (wall-lizard side)   Podarcis muralis, Lacerta viridis
    Anguimorpha (dragon side)        Varanus komodoensis, Heloderma suspectum
    Iguania     (places the node)    Anolis carolinensis
    Gekkota     (outgroup, roots it) Gekko gecko

Instead of a single gene we take the whole **mitochondrial genome** (~16-17 kb),
the standard mid-size object used to characterise and phylogenetically place a
species. From each mitogenome we extract every *gene feature* — the 13
protein-coding genes, the two ribosomal RNAs (12S/16S, i.e. the mitochondrial
ribosome) and the 22 tRNAs — and drop the fast-evolving control region (it cannot
be aligned across ~170 My, and it is not a gene feature, so excluding it is
automatic). Each feature is stored under a normalised key so the aligner can match
homologues across taxa regardless of annotation quirks or gene order.

Translation uses NCBI genetic-code table 2 (vertebrate mitochondrial): ATA=Met,
TGA=Trp, AGA/AGG=stop — these are mitochondrial genes, so the standard code is
wrong here.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import yaml
from Bio import Entrez, SeqIO
from Bio.Seq import Seq

# NCBI asks that Entrez requests identify a contact. Override with ENTREZ_EMAIL.
Entrez.email = os.environ.get("ENTREZ_EMAIL", "poemes-insilico@example.com")
if os.environ.get("ENTREZ_API_KEY"):
    Entrez.api_key = os.environ["ENTREZ_API_KEY"]

MITO_TABLE = 2  # vertebrate mitochondrial genetic code
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "mito"


@dataclass(frozen=True)
class Taxon:
    """One tip of the tree: a species, its role, and its Catalan/English names."""

    species: str          # binomial, also the Entrez organism filter
    common_en: str        # English common name (code-facing)
    common_ca: str        # Catalan common name (for the poem/figure)
    clade: str            # coarse clade label, for the reader
    role: str             # "ingroup" or "outgroup"
    accession: str = ""   # pinned mitogenome accession; if empty, resolve by search


# The taxon set. Mitogenome accessions are pinned (resolved once, then frozen here)
# so the reconstruction is reproducible. Clear an accession to re-resolve by search.
TAXA: list[Taxon] = [
    Taxon("Podarcis muralis", "common wall lizard", "sargantana de paret",
          "Lacertidae", "ingroup", "NC_011607.1"),
    Taxon("Lacerta viridis", "European green lizard", "llangardaix verd",
          "Lacertidae", "ingroup", "NC_008328.1"),
    Taxon("Varanus salvator", "water monitor", "varà aquàtic",
          "Varanidae", "ingroup", "NC_010974.1"),
    Taxon("Heloderma suspectum", "Gila monster", "monstre de Gila",
          "Helodermatidae", "ingroup", "NC_008776.1"),
    Taxon("Anolis carolinensis", "green anole", "anolis verd",
          "Iguania", "ingroup", "EU747728.2"),
    Taxon("Gekko gecko", "tokay gecko", "dragó tokay",
          "Gekkota", "outgroup", "NC_007627.1"),
]

REFERENCE = "Podarcis muralis"

# --- Feature-name normalisation --------------------------------------------

# The 13 canonical mitochondrial protein-coding genes.
CDS_CANONICAL = {
    "ND1", "ND2", "ND3", "ND4", "ND4L", "ND5", "ND6",
    "COX1", "COX2", "COX3", "ATP6", "ATP8", "CYTB",
}

# Synonyms seen in GenBank `gene`/`product` qualifiers -> canonical key.
CDS_SYNONYMS = {
    "COI": "COX1", "CO1": "COX1", "COXI": "COX1",
    "COII": "COX2", "CO2": "COX2", "COXII": "COX2",
    "COIII": "COX3", "CO3": "COX3", "COXIII": "COX3",
    "COB": "CYTB", "CYB": "CYTB",
    "ATPASE6": "ATP6", "ATPASE8": "ATP8",
    "NAD1": "ND1", "NAD2": "ND2", "NAD3": "ND3", "NAD4": "ND4",
    "NAD4L": "ND4L", "NAD5": "ND5", "NAD6": "ND6",
}

# Three-letter amino acid -> one-letter, for tRNA keys (trn<AA1>).
AA3_TO_1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q",
    "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
    "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
    "TYR": "Y", "VAL": "V",
}


def _qual(feature, key: str) -> str:
    return " ".join(feature.qualifiers.get(key, [])).strip()


def _cds_key(feature) -> str | None:
    """Canonical key for a protein-coding gene, or None if unrecognised."""
    for source in (_qual(feature, "gene"), _qual(feature, "product")):
        token = re.sub(r"[^A-Z0-9]", "", source.upper())
        if token in CDS_CANONICAL:
            return token
        if token in CDS_SYNONYMS:
            return CDS_SYNONYMS[token]
    # Product phrases, e.g. "NADH dehydrogenase subunit 4L", "cytochrome b".
    product = _qual(feature, "product").lower()
    if "cytochrome b" in product:
        return "CYTB"
    m = re.search(r"nadh dehydrogenase subunit (\d+)(l?)", product)
    if m:
        return f"ND{m.group(1)}{'L' if m.group(2) else ''}".upper()
    m = re.search(r"cytochrome c oxidase subunit (\d+|i{1,3})", product)
    if m:
        roman = {"i": 1, "ii": 2, "iii": 3}
        num = roman.get(m.group(1), m.group(1))
        return f"COX{num}"
    if "atp synthase" in product or "atpase" in product:
        m = re.search(r"subunit (\d+)", product)
        if m:
            return f"ATP{m.group(1)}"
    return None


def _rrna_key(feature) -> str | None:
    text = (_qual(feature, "product") + " " + _qual(feature, "gene")).lower()
    if "12s" in text or "small" in text or "s-rrna" in text or "rrns" in text:
        return "rrnS"
    if "16s" in text or "large" in text or "l-rrna" in text or "rrnl" in text:
        return "rrnL"
    return None


def _trna_aa(feature) -> str | None:
    """One-letter amino acid for a tRNA feature, or None."""
    for source in (_qual(feature, "product"), _qual(feature, "gene")):
        m = re.search(r"trna?-?([a-z]{3})", source.lower())
        if m and m.group(1).upper() in AA3_TO_1:
            return AA3_TO_1[m.group(1).upper()]
    return None


@dataclass(frozen=True)
class Feature:
    key: str          # e.g. "COX1", "rrnL", "trnL1"
    kind: str         # "CDS" | "rRNA" | "tRNA"
    nt: str           # coding-strand nucleotides
    start: int        # reference start coordinate (for genomic ordering)


def extract_features(record) -> list[Feature]:
    """Pull the CDS / rRNA / tRNA features from a mitogenome, in genome order.

    Duplicated tRNAs (two Leu, two Ser in vertebrate mtDNA) are numbered by their
    order along the genome (trnL1, trnL2, ...) so homologues match across taxa.
    """
    raw: list[tuple[int, str, str, str]] = []  # (start, key, kind, nt)
    for feature in sorted(record.features, key=lambda f: int(f.location.start)):
        start = int(feature.location.start)
        if feature.type == "CDS":
            key = _cds_key(feature)
            kind = "CDS"
        elif feature.type == "rRNA":
            key = _rrna_key(feature)
            kind = "rRNA"
        elif feature.type == "tRNA":
            aa = _trna_aa(feature)
            key = f"trn{aa}" if aa else None
            kind = "tRNA"
        else:
            continue
        if key is None:
            continue
        nt = str(feature.extract(record.seq)).upper().replace("U", "T")
        if set(nt) - set("ACGTN") or len(nt) < 30:
            continue
        raw.append((start, key, kind, nt))

    # Number duplicate keys (tRNA-Leu/Ser) by genome order: trnL -> trnL1, trnL2.
    counts: dict[str, int] = {}
    totals: dict[str, int] = {}
    for _, key, _, _ in raw:
        totals[key] = totals.get(key, 0) + 1
    features: list[Feature] = []
    for start, key, kind, nt in raw:
        if totals[key] > 1:
            counts[key] = counts.get(key, 0) + 1
            key = f"{key}{counts[key]}"
        features.append(Feature(key=key, kind=kind, nt=nt, start=start))
    return features


def _clean_cds(nt: str) -> str:
    """Trim a CDS to whole codons and drop a trailing stop (mito code)."""
    nt = nt[: len(nt) - len(nt) % 3]
    protein = str(Seq(nt).translate(table=MITO_TABLE)).rstrip("*")
    return nt[: 3 * len(protein)]


# --- Fetching ---------------------------------------------------------------

def _candidate_ids(taxon: Taxon) -> list[str]:
    handle = Entrez.esearch(
        db="nuccore",
        term=(f'"{taxon.species}"[Organism] AND mitochondrion[Title] '
              f'AND complete genome[Title]'),
        retmax=10,
        sort="relevance",
    )
    ids = Entrez.read(handle)["IdList"]
    handle.close()
    if not ids:  # some titles say "mitochondrial DNA, complete genome"
        handle = Entrez.esearch(
            db="nuccore",
            term=f'"{taxon.species}"[Organism] AND mitochondrion AND complete genome',
            retmax=10, sort="relevance",
        )
        ids = Entrez.read(handle)["IdList"]
        handle.close()
    if not ids:
        raise RuntimeError(f"no complete mitogenome found for {taxon.species}")
    return ids


def _fetch_record(ident: str):
    handle = Entrez.efetch(db="nuccore", id=ident, rettype="gb", retmode="text")
    record = SeqIO.read(handle, "genbank")
    handle.close()
    return record


def fetch_one(taxon: Taxon):
    """Return (record, features) for a taxon's complete mitogenome.

    A pinned accession is used if present; otherwise we walk the search hits and
    keep the first ~15-20 kb record that yields a full set of gene features.
    """
    candidates = [taxon.accession] if taxon.accession else _candidate_ids(taxon)
    for ident in candidates:
        record = _fetch_record(ident)
        if not (14000 <= len(record.seq) <= 20000):
            time.sleep(0.4)
            continue
        features = extract_features(record)
        if len([f for f in features if f.kind == "CDS"]) >= 12:
            return record, features
        time.sleep(0.4)
    raise RuntimeError(f"no usable mitogenome for {taxon.species}")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sources: dict[str, dict] = {}
    for taxon in TAXA:
        record, features = fetch_one(taxon)
        # Persist one FASTA per species: one record per feature.
        lines = []
        for feat in features:
            nt = _clean_cds(feat.nt) if feat.kind == "CDS" else feat.nt
            lines.append(f">{feat.key}|{feat.kind}|{feat.start}\n{nt}")
        out = DATA_DIR / f"{taxon.species.replace(' ', '_')}.fasta"
        out.write_text("\n".join(lines) + "\n")

        by_kind = {k: sum(1 for f in features if f.kind == k)
                   for k in ("CDS", "rRNA", "tRNA")}
        sources[taxon.species] = {
            "accession": record.id,
            "length_bp": len(record.seq),
            "clade": taxon.clade,
            "role": taxon.role,
            "common_ca": taxon.common_ca,
            "common_en": taxon.common_en,
            "features": by_kind,
        }
        print(f"  {taxon.species:<24} {record.id:<14} {len(record.seq):>6} bp   "
              f"CDS {by_kind['CDS']}  rRNA {by_kind['rRNA']}  tRNA {by_kind['tRNA']}")
        time.sleep(0.4)  # be polite to Entrez without an API key

    (DATA_DIR / "sources.yml").write_text(
        yaml.safe_dump(sources, sort_keys=False, allow_unicode=True)
    )
    print(f"Wrote {len(sources)} mitogenome feature sets + sources.yml to {DATA_DIR}")


if __name__ == "__main__":
    main()
