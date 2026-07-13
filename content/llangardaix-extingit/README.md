<!-- Method notes for this poem. Written in ENGLISH (code-facing documentation). -->
# llangardaix-extingit — method

A grandfather claims he once found a fossil lizard on the shore of Lake Banyoles.
Nothing survives — no bone, no DNA. So instead of recovering the animal, we
**reconstruct its genome from its living relatives**, using real ancestral sequence
reconstruction (ASR). The poem's extinct lizard is defined as the **last common
ancestor of the humble common wall lizard (*Podarcis muralis*) and the water
monitor (*Varanus salvator*)** — a deep node, roughly Jurassic (~170 My).

The reconstructed object is the **complete mitochondrial genome** (~15.3 kb): the
standard mid-size, "characterise-a-species" molecule — 13 protein-coding genes, the
two ribosomal RNAs (12S/16S) and the 22 tRNAs. (The control region is omitted: it
evolves too fast to align across this depth, and it is not a gene feature, so it
drops out automatically.) The poem is that genome written out: solid uppercase
where ~170 My have preserved it unchanged, and lowercase IUPAC ambiguity codes
where deep time has erased the signal. The uncertainty is not a flaw — it *is* the
poem.

> **Why the water monitor and not the Komodo dragon?** The poem began with the
> Komodo dragon as the mythic pole, but *Varanus komodoensis* has no complete
> mitochondrial genome in GenBank (only its nuclear genome and a few single genes).
> Its close cousin the water monitor does. For a node ~170 My deep the choice of
> *Varanus* species is immaterial — the whole genus shares an ancestor only
> ~40–50 My ago — so the water monitor stands in with no meaningful loss.

## Why this makes bioinformatic sense

A naïve "midpoint" of two sequences is a meaningless chimera. ASR is the rigorous
form of the idea: given several living sequences, a phylogenetic tree, and a model
of molecular evolution, the sequence at an internal node (an ancestor) is a
statistically estimable quantity. This is a standard, respected method — labs
literally synthesise reconstructed ancestral proteins and test them in vitro. What
we *cannot* do is get the ancestor's actual DNA (no ancient DNA survives that
long), which is exactly the honest tension the poem lives in: the fossil would give
bones; only the living children can lend the ancestor its genes.

## Pipeline

1. **Fetch** (`code/fetch_sequences.py`) — complete mitogenomes from NCBI Entrez
   (Biopython) for six taxa chosen to bracket the ancestral node and root it:

   | Clade | Taxon | Accession | Role |
   |-------|-------|-----------|------|
   | Lacertidae | *Podarcis muralis* | `NC_011607.1` | wall-lizard side |
   | Lacertidae | *Lacerta viridis* | `NC_008328.1` | wall-lizard side |
   | Iguania | *Anolis carolinensis* | `EU747728.2` | places the node |
   | Varanidae | *Varanus salvator* | `NC_010974.1` | monitor ("dragon") side |
   | Helodermatidae | *Heloderma suspectum* | `NC_008776.1` | monitor side |
   | Gekkota | *Gekko gecko* | `NC_007627.1` | outgroup (roots the tree) |

   From each mitogenome we extract every gene feature (13 CDS, 2 rRNA, 22 tRNA),
   normalising names across annotation quirks (`COI`→`COX1`, `COB`→`CYTB`, …),
   letting `feature.extract` handle reverse-strand genes, and numbering the
   duplicated tRNAs (two Leu, two Ser) by genome order. CDS are validated against
   the **vertebrate mitochondrial code** (NCBI table 2: `ATA`=Met, `TGA`=Trp,
   `AGA`/`AGG`=stop). Accessions are pinned for reproducibility.

2. **Align + concatenate** (`code/align.py`) — each feature is aligned across taxa
   on its own, reference-anchored to *Podarcis*: protein-coding genes by
   translation-guided **codon** alignment (in frame), rRNA/tRNA by **nucleotide**
   alignment. Only features present in all six taxa are kept (their intersection;
   *Anolis* lacks an annotated `trnR`, so it is dropped). The features are then
   concatenated in reference genomic order into one ~15.3 kb supermatrix.

3. **Reconstruct** (`code/reconstruct.py`) — the ASR engine, from scratch, run once
   over the whole concatenation:
   - **Tree**: a fixed literature topology (Toxicofera hypothesis), rooted *at the
     ancestral node itself* so it is a trifurcation `(Lacertoidea, Toxicofera,
     Gekko)` — the identifiable unrooted form, and precisely the node we read off.
     See `data/tree.nwk`.
   - **Model**: HKY85 (empirical base frequencies + one transition/transversion
     parameter κ). Time-reversible, so likelihood is root-independent.
   - **Likelihood**: Felsenstein's pruning, vectorised over sites; all nine branch
     lengths and κ fitted by maximum likelihood (L-BFGS-B). Transition matrices via
     eigendecomposition, `P(t) = V·exp(Λt)·V⁻¹`.
   - **Reconstruction**: the **marginal posterior** over {A,C,G,T} per site at the
     root, `P(ancestor base | data, tree, model)`. MAP base = reconstructed base;
     posterior = confidence. Alignment gaps enter as missing data.
   - **Reading-frame repair**: site-independent reconstruction ignores the reading
     frame, so at a few uncertain codons the per-site MAP can spell a premature
     stop. For each such codon in a coding gene we substitute the highest
     *joint*-posterior sense codon (typically 3–4 codons genome-wide) and keep its
     lower posterior, so the site stays honestly uncertain but the gene stays a
     valid ORF.

4. **Render** (`code/render.py`) — writes the "haze" sequence into `poem.md`
   (uppercase if posterior ≥ 0.90, else the lowercase IUPAC ambiguity code covering
   ≥ 0.90 posterior), a genome-wide confidence figure, and a styled `sequence.html`.

## Results (the quotable part)

Running the pipeline (`results/model.txt`, `results/reconstruction.csv`):

- Fitted **κ ≈ 2.1** (a realistic mitochondrial transition bias) and a G-poor base
  composition (~0.14) — the classic mitochondrial strand asymmetry. All 13 coding
  genes reconstruct as **intact ORFs** (no internal stops after frame repair).
- The reconstructed ancestor is a genuine **intermediate**: ~15–24% divergent from
  every living tip (closest to the lacertids, farthest from the monitor),
  identical to none.
- **~88% of the genome reconstructs at posterior ≥ 0.90**; overall mean ≈ 0.94.
  The confidence **landscape across the genome is textbook**: highest at the
  ribosomal RNAs (12S/16S ≈ 0.95) and the conserved oxidase genes (COX2 ≈ 0.95),
  lowest at the fast-evolving ND genes and **ATP8 ≈ 0.90** (the least-conserved
  mitochondrial gene). Within coding genes the haze pools at **third codon
  positions** (≈ 0.87 vs ≈ 0.95–0.98 at first/second) — exactly where the genetic
  code lets bases drift silently. Both are in the figure.

## Honest limitations

- A single HKY model is fitted across the whole concatenation (no per-partition
  rates for rRNA vs tRNA vs codon positions) — a deliberate simplification.
- Alignment is reference-anchored to *Podarcis*: insertions relative to it are
  dropped and taxa missing a column get a gap. Faithful for coding genes and tRNAs;
  the rRNA expansion segments are the roughest fit and simply read as extra haze.
- Deep-node marginal posteriors are somewhat overconfident (a known ASR property),
  so treat the confidence as relative, not absolute.

## How to run

```bash
bash install.sh                 # create the venv + install deps
source .venv/bin/activate

python code/main.py             # reconstruct + render from committed sequences
python code/main.py --fetch     # refresh mitogenomes from NCBI first (set ENTREZ_EMAIL)

python code/align.py            # inspect the concatenated alignment
python code/reconstruct.py      # just the reconstruction + result files
```

## Files

- `poem.md` — the poem itself (Catalan): the verse plus the reconstructed genome.
- `metadata.yml` — title, author, tools, tags, description (Catalan).
- `code/fetch_sequences.py` — Entrez fetch + mitogenome feature extraction.
- `code/align.py` — per-feature codon/nucleotide alignment + concatenation.
- `code/reconstruct.py` — HKY85 + Felsenstein pruning + marginal ASR + frame repair.
- `code/render.py` — haze sequence into `poem.md` + genome figure + `sequence.html`.
- `code/main.py` — orchestrates the whole pipeline.
- `data/mito/*.fasta`, `data/mito/sources.yml` — extracted features + provenance.
- `data/tree.nwk` — the fixed topology used for reconstruction.
- `results/ancestor.fasta`, `reconstruction.csv`, `model.txt`, `reconstruction.png`,
  `sequence.html`.
