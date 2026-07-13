<!-- Method notes for this poem. Written in ENGLISH (code-facing documentation). -->
# Versos proteics — method

Catalan poems are rewritten as **proteins**. Each character is mapped to an
amino acid (or a two-letter escape code) by a fixed rubric, the resulting sequence
is **folded** into a 3D structure with ESMFold, and we measure **how globular** the
fold is. The question the poem plays with: which verses "want" to be proteins?

## Pipeline

1. **Encode** (`code/main.py`) — the Catalan→amino-acid rubric. Every amino-acid
   letter encodes the Catalan letter of the same name (`a→A`, `k→K`, `y→Y`…); `W`
   is an escape prefix for the rest (`o→WQ`, `u→WV`, `ç→WK`, `w→WW`, `l·l→WL`…).
   Reversible (prefix-free); accents collapse to the base vowel. Full table in
   [`docs/rubric.md`](docs/rubric.md).
2. **Fold** (`code/folding.py`) — ESMFold via the free ESM Atlas API
   (`api.esmatlas.com`, single-sequence, no MSA). PDBs are cached under `cache/`
   by sequence hash; the ~400-residue cap is handled by chunking.
3. **Score globularity** (`code/globularity.py`) — from the Cα trace: radius of
   gyration `Rg` vs. the empirical globular expectation `Rg0 ≈ 2.2·N^0.38` Å,
   relative shape anisotropy `κ²` (0 = sphere, 1 = rod), and mean pLDDT. These
   combine into a `score ∈ [0,1]` (higher = more globular *and* confidently folded).
4. **Rank** (`code/pipeline.py`) — encode → fold → score every poem in
   `data/poems/*.txt`, writing a ranked `results/globularity.csv`.

## How to run

```bash
bash install.sh                 # create the venv + install deps
source .venv/bin/activate

python code/main.py "Catalunya"          # encode one line     -> CATALWVNYA
python code/main.py --decode "CATALWVNYA"  # decode back        -> catalunya
python code/main.py --selftest           # rubric round-trip demo

python code/pipeline.py                  # fold + rank data/poems (whole-poem units)
python code/pipeline.py --unit verse     # fold each verse separately, average per poem
```

## Inputs / outputs

- `data/poems/*.txt` — input corpus (one poem per file; bundled files are short
  public-domain samples — replace with your own). See `data/poems/README.md`.
- `results/globularity.csv` — ranked globularity metrics per poem.
- `cache/` — folded PDBs pulled from the API (git-ignored, regenerable).

## Files

- `poem.md` — the poem itself (Catalan).
- `metadata.yml` — title, author, tools, tags, description.
- `docs/rubric.md` — the encoding rubric reference.
- `code/` — `main.py` (rubric codec), `folding.py`, `globularity.py`, `pipeline.py`.
