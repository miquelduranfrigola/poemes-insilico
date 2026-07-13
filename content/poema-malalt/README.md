<!-- Method notes for this poem. Written in ENGLISH (code-facing documentation). -->
# poema-malalt — method

A poem where a word **mutates like a tumour and yet stays a valid word**. We treat
a word as a tiny genome, apply the three classes of small somatic mutation with
cancer-like frequencies, and keep only the mutations that land on a **canonical
Catalan dictionary word**. The result is a **clonal tree** — a tumour phylogeny of
words — where every node is an important dictionary word and every edge is a
survivable mutation.

## The biology → words mapping

| Cancer (somatic mutation) | Word operation |
|---------------------------|----------------|
| Substitution (SNV)        | replace one letter |
| Deletion                  | remove one letter  |
| Insertion                 | add one letter     |

Two facts about real cancer genomes are reproduced deliberately:

1. **Mutation-type spectrum.** Small somatic mutations are overwhelmingly
   substitutions (~90%); indels are the rest (~10%), and deletions outnumber
   insertions. Default proposal weights: `substitution 0.90 / deletion 0.07 /
   insertion 0.03` (pan-cancer averages; tunable on the CLI).
2. **Transition/transversion bias.** Within substitutions cancer shows more
   transitions than transversions (Ti/Tv ≈ 2). We map the purine/pyrimidine
   class structure onto **vowels vs consonants**: a substitution that stays in
   its class (vowel→vowel, consonant→consonant) is a *transition*; crossing the
   class is a *transversion*. Transitions are weighted higher (`--titv`, default
   2.0). This also tends to keep the mutated string pronounceable.

## Validity **is** selection (the rigorous part)

Requiring "still a real word" is not a cosmetic filter — it *is* the model of
selection. In a tumour most mutations are neutral passengers, a few are drivers,
and lethal ones are purged by purifying selection (the cell dies):

```
invalid string  =  a lethal mutation (the cell does not survive)
valid word      =  a viable cell that lives on
```

So the process has **two spectra**, exactly as in tumour genomics:

- the **mutational process** — what we *propose* (calibrated to cancer), and
- the **surviving spectrum** — what we *accept* (reshaped by selection).

`code/main.py` measures both and prints how selection shifts them. Typical run:
the proposed spectrum matches the cancer defaults, but among survivors
**insertions almost vanish**, **deletions are enriched**, and the realised
**Ti/Tv climbs far above 2** — class-preserving substitutions survive better.
That shift is a real, quotable result of the piece, not decoration.

## Validity oracle — canonical dictionary headwords

A string counts as a valid word only if it is a **canonical headword (lemma) of an
open-class word** (noun, verb, adjective, adverb). This is what makes survivors feel
like *dictionary* words and removes boring morphological repetition:

- **No inflected forms.** Plurals (`cases`), feminines (`gata`) and verb
  conjugations (`corria`) are *not* valid — only their lemma (`casa`, `gat`,
  `córrer`) is. A tree therefore never fills with `-es`/`-s` variants of the same
  word.
- **Only important words.** Proper nouns, abbreviations and closed-class function
  words (`de`, `que`, …) are excluded, and a real-usage frequency floor keeps the
  words common enough to matter.

The headword set is built by `code/build_lexicon.py` from the **Softcatalà
`catalan-dictionary`** — a form→lemma→POS table of ~1.18M rows built from the DIEC
and DNV normative dictionaries (dual GPL-2.0 / LGPL-2.1). Since the DIEC itself has
no bulk download, this is the practical, legal path to "official dictionary" words.
The builder:

1. keeps rows whose POS is open-class (tag starts `N`/`V`/`A`/`R`, dropping proper
   nouns `NP`) and whose lemma is alphabetic;
2. scores each lemma by the **highest** [`wordfreq`](https://github.com/rspeer/wordfreq)
   Zipf frequency among its inflected forms (so a common verb survives via its
   common conjugations), keeping lemmas above `--min-freq` (default 2.5);
3. writes the unique lemmas to `data/lexicon/lemmas.txt` (gitignored, reproducible).

At runtime `code/main.py` just loads that list into a set — validity is O(1)
membership, no NLP library needed. A light shape guard (`--min-length` 3, must
contain a vowel) removes single letters.

Trade-off: a lemma-only graph is sparser than an all-forms graph, so we raise the
rejection-sampling budget (`--attempts`, default 600). Some common seeds are
naturally near-isolated (e.g. `cervesa` → only `certesa`) and give short trees;
short common seeds (`cos`, `mar`, `casa`) branch richly. Make the vocabulary
stricter/looser by rebuilding the lexicon with a higher/lower `--min-freq`.

## Evolving-poem mode (`code/evolve.py`)

A second mode: instead of growing a tree from one word, treat a **whole poem as a
genome** and each **word as a gene**. One word at a time mutates by the same
cancer-calibrated single-letter edits, but a mutation survives only if it is
(1) a real Catalan word, (2) the **same part of speech with agreement preserved**
(noun→noun, adjective→adjective, keeping gender/number/tense), and (3) still
semantically plausible — judged by a human/LLM reader. The poem then visibly
evolves while staying alive.

`code/evolve.py` handles (1) and (2): given a word and its part of speech it lists
the valid, agreement-matching, common single-edit mutations (reusing the DIEC-
derived `data/lexicon/diccionari.txt` form→POS table and the `main.py` mutation
model). Part of speech in context and semantic plausibility (3) are supplied by the
reader driving the evolution.

```bash
python code/evolve.py --word calla --pos V     # -> balla, talla, falla, calma, ...
python code/evolve.py --word fosca --pos A      # -> tosca, osca (fem-sing agreement)
python code/evolve.py --word gat --pos N --propose 5   # cancer-weighted draws
```

Options: `--pos {N,V,A,R}`, `--min-freq` (default 3.0), `--propose N`, `--titv`,
`--rng-seed`. Agreement is preferred; it falls back to the broad part of speech
only when a word has no strict-agreement neighbour.

## The object we grow

A **clonal tree**: the seed word ("the first cell") divides a small number of
times (weighted toward one child, so lineages read as slow transformations with
occasional subclonal branches). Each division does **rejection sampling** —
propose a mutation, keep it only if the result is a *novel* valid word — bounded
by an attempt cap so dead ends become leaves. The tree is rendered as an indented
genealogy, and the deepest root→leaf path is reported as a "word ladder".

Runs are deterministic given `--rng-seed`, so `poem.md` is reproducible.

## How to run

```bash
bash install.sh                       # venv, install deps, build the lexicon
source .venv/bin/activate
python code/main.py --seed cos --nodes 40 --rng-seed 3
python code/main.py --seed mar --nodes 60 --rng-seed 7 --emit-poem
```

To make the vocabulary stricter or richer, rebuild the lexicon:

```bash
python code/build_lexicon.py --min-freq 3.0   # fewer, more common headwords
```

Key options for `main.py`: `--seed WORD` (the first cell), `--nodes N` (tree size),
`--rng-seed N` (reproducibility), `--titv` (transition:transversion ratio),
`--sub/--dele/--ins` (mutation-type weights), `--min-length`, `--max-children`,
`--attempts` (search budget per step), `--emit-poem` (write `../poem.md`).

## Files

- `poem.md` — the poem itself (Catalan): the rendered clonal tree.
- `metadata.yml` — title, author, tools, tags, description (Catalan).
- `code/main.py` — mutation engine, selection, clonal-tree growth, spectrum report.
- `code/evolve.py` — evolving-poem mode: POS-preserving word mutations for a text.
- `code/build_lexicon.py` — build the canonical-headword lexicon (DIEC-derived).
- `data/lexicon/lemmas.txt` — the generated headword list (gitignored, reproducible).
- `assets/drive-manifest.yml` — links to any large assets on Google Drive.
