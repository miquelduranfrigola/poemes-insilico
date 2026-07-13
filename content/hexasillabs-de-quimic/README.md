<!-- Method notes for this poem. Written in ENGLISH (code-facing documentation). -->
# hexasillabs-de-quimic — method

A poem whose **verses are molecule names**. Each line is the name of a real
molecule, written in Catalan. Because those names are *found objects*, the poet
does not write syllables — the molecules provide them. The work is constraint
satisfaction + curation: fetch names, verbalise, count Catalan syllables, keep the
ones that scan, and arrange them.

## Final concept — one life told through its molecules

The poem is **the arc of a human life, fetus to death**, in **8 stanzas (one per
stage) × 4 verses = 32 molecules**. Tone: the dark, human side of pharmacology
(the code, the NICU, the medicated child, teen drugs, love & psychedelics, doping,
over-medication, poisons).

Triple constraint on every verse:
1. the molecule **represents its life stage**;
2. it is a **hexasyllable** — 6 syllables to the last stress (*fins a l'última
   tònica*), counted by `code/sillabes.js`;
3. it makes the **stanza rhyme** — each stage has its own suffix (mostly `-ina`;
   *Adultesa* is `-ona`, steroids/doping).

Because a plain-stressed suffix like `-ina` puts the accent on the penult, a
6-syllable verse needs a **7-written-syllable** name — a selective filter, which is
why the pool had to be enlarged (Wikidata Catalan labels + names translated from
English, e.g. `-ine → -ina`).

Stages and their molecules are in `poem.md`; the per-stage rationale + how each
structure is fetched is in `code/build_web.py`.

## Verbalisation standard (the heart of the poem)

A written IUPAC string is not what a Catalan reader *says*. The verses are the
**spoken** form, so before counting syllables we expand the name deterministically.
This ruleset is the poem's voice and must be explicit and auditable:

- **Locant numbers → Catalan cardinals:** `2` → *dos*, `1,3,7` → *u tres set*.
- **Letter locants → letter names:** `N-` → *ena*, `O-` → *o*, `S-` → *essa*,
  `H` → *hac*.
- **Stereo/geometry descriptors:** `(R)` → *erre*, `(S)` → *essa*, `(E)` → *e*,
  `(Z)` → *zeta* (final policy TBD — may be dropped).
- **Silent symbols:** hyphens, commas and brackets are not pronounced.
- **Already words:** multiplying prefixes *di, tri, tetra, hexa* and roots
  (*metil, hidroxi, fenil*…) are kept as written.

> Important: the syllable counter (`code/sillabes.js`) treats **digits as word
> separators and does not pronounce them**. Verbalisation (digits → words) must
> therefore happen *before* counting.

## Syllable counting

Catalan syllabification is delegated to **Softcatalà's** own engine, run headlessly
so counts match <https://www.softcatala.org/sillabes/> exactly. See
`code/vendor/softcatala/SOURCE.md`. The relevant output is the **poetic** count
(`poetic1`), which counts up to the last stressed syllable — the metric length of
the verse.

```bash
node code/sillabes.js "propan-u-ol" "àcid butanoic"   # human table
node code/sillabes.js --json "metà" "età"             # machine-readable
```

### Note on language of the code

This poem deviates from the repo default (Python): Catalan syllabification is
inherently tied to Softcatalà's **JavaScript** engine, which we run unmodified for
exact reproducibility. The syllable counter is therefore Node/JS. The rest of the
pipeline (see below) may orchestrate it from Python or JS — TBD.

## Catalan name sources

There is **no large dataset of systematic Catalan IUPAC names** — systematic names
are rule-generated, not stored. The largest machine-readable source of *Catalan
molecule names* is **Wikidata** (labels are mostly trivial, some semi-systematic).

- `code/wikidata_ca.rq` + `code/fetch_wikidata_ca.sh` pull every Wikidata item with
  both a PubChem CID (P662) and a Catalan label into `data/wikidata-ca.csv`
  (columns: `item, name_ca, cid`).
- Snapshot retrieved 2026-07-11: **3,959 unique molecules / 3,941 unique names.**
  A few are inorganic/elements (e.g. *titani*) — filter as needed.
- **~205 names already carry locants** (systematic-ish: *1-pentanol*,
  *àcid 2-metilpropanoic*, *butan-1-amina*), directly usable for the systematic
  style. The rest are trivial names and, via their CID, provide **structures**
  (SMILES) to *generate* more systematic names.
- Rough per-family counts (naive suffix match, includes false positives):
  alcohols `-ol` ≈267, ketones `-ona` ≈176, amines `-amina` ≈89, amides `-amida`
  ≈60, aldehydes `-al` ≈57, carboxylic acids `àcid …-oic` ≈20, plus `-ina` ≈845.

### Themed pool (Catalan Wikipedia categories)

To give the poem *meaningful* molecules (poisons, drugs, foods, metabolites…), we
harvest Catalan Wikipedia category members and keep those present in the Wikidata
CID pool (which attaches a CID and filters out non-molecule concept pages).

- `code/fetch_categories_ca.py` → `data/categories-ca.csv`
  (`name_ca, cid, themes, poetic_syllables`). Rate-limited (polite throttling).
- Theme → seed categories: **farmacs** (Fàrmacs, Antibiòtics, Antisèptics),
  **verins** (Toxines, Alcaloides), **aliments** (Additius alimentaris),
  **metabolits** (Neurotransmissors, Hormones, Àcids grassos, Aminoàcids),
  **organiques** (Compostos orgànics, Esteroides, Lípids). Subcategories are
  expanded one level (junk subcats filtered by name).
- Snapshot: **678 unique molecules** — organiques 261, metabolits 218, aliments
  127, farmacs 89, verins 68. At 6 syllables: 70 total (rich in metabolites/fatty
  acids and organiques; thin in verins/farmacs).
- **Gap: detergents/surfactants** have no usable Catalan Wikipedia category. Some
  cleaning agents surface via Antisèptics (bleach, benzalkonium chloride).
- Syllable/verbalisation helpers live in `code/molname.py` (shared by
  `syllable_histogram.py` and `fetch_categories_ca.py`).

## Choosing the metre (data-driven)

We measured real, verbalised Catalan IUPAC names with `sillabes.js`. Poetic counts:

| Verbalised name | poetic syllables |
|-----------------|:----------------:|
| `butanal` | 3 |
| `propan-u-ol` / `butan-u-ol` | 4 |
| `pentan-dos-ona` | 4 |
| `àcid butanoic` / `àcid propanoic` | 5 |
| `dos-metilpropan-u-ol` | 7 |
| `ena-metilmetanamina` (N-methylmethanamine) | 8 |
| `ena-fenilacetamida` (N-phenylacetamide) | 8 |
| `u tres set-trimetilxantina` (caffeine) | 8 |
| `àcid dos-hidroxibenzoic` | 8 |
| `àcid dos-acetoxibenzoic` (aspirin) | 9 |
| `ena-quatre-hidroxifenil-acetamida` (paracetamol) | 13 |

**Findings.** Bare family members are short (3–5). Length is *tunable*: because
IUPAC names are compositional, adding chain length, methyl/hydroxy substituents,
or more locants raises the count predictably. So any target metre is reachable by
choosing suitably decorated molecules within each family. The histogram over a
real candidate pool will tell us where the molecules are *abundant* and *natural*.

- Likely sweet spot: **decasíl·lab (10)** — noble, and reachable with lightly
  decorated names — or **alexandrí (12, 6+6)** if the pool is rich, with the
  caesura optionally landing on a substituent ‖ parent seam.
- Final choice is deferred to the histogram step in the pipeline.

## Pipeline (planned `code/`)

1. **Candidate pool** — curated molecules per family → PubChem CIDs.
2. **Fetch** English IUPAC names from PubChem (PUG-REST).
3. **Translate** EN → CA systematic IUPAC (documented rule module).
4. **Verbalise** numbers/letters per the standard above.
5. **Count** Catalan poetic syllables via `sillabes.js`.
6. **Histogram** of lengths → fix the metre.
7. **Select** 6 families × 4 members at the target length; order for rhyme.
8. **Emit** `poem.md`.

Main risk: reliable EN → CA systematic-name translation. Start with a ~10-molecule
proof of concept before scaling.

## The poem, stanza by stanza (8 × 4)

Each stanza rhymes with **its own suffix** (a different sound per age, so the poem
doesn't drone on `-ina`), and the tone is mixed — tender, wry, dark.

| Stage | Rhyme | Molecules | Tone / angle |
|-------|-------|-----------|--------------|
| Fetus | -ina | desoxiguanosina · desoxicitidina · desoxitimidina · triiodotironina | the genetic code + the thyroid that wires the brain |
| Nadó | -ol | colecalciferol · ergocalciferol · fenoxietanol · isoproterenol | the drops and puffs: vitamin D, vaccine preservative, asthma |
| Infantesa | -il | butanoat d'etil · hexanoat d'etil · butirat de pentil · salicilat d'etil | the sweet smells: pineapple, apple, banana, mint (esters) |
| Adolescència | -ona | metiltestosterona · fluoximesterona · espironolactona · desoximetasona | puberty hormones and acne |
| Joventut | -ina | feniletilamina · dimetiltriptamina · dietiltriptamina · hidroximescalina | falling in love and hallucinogens |
| Adultesa | -oic | àcid undecanoic · àcid tridecanoic · àcid icosanoic · àcid octandioic | the fats that quietly accumulate |
| Vellesa | -ida | acetazolamida · acetohexamida · ciclopentiazida · meticlotiazida | the chronic-disease pillbox: glaucoma, diabetes, blood pressure |
| Mort | -ita | hidroxiapatita · calcita · pirita · hematita | minerals — the hexasyllable **collapses into stone** (bone, lime, sulfur, the iron of blood as rust) |

`-ina` now appears in only **two** stanzas (Fetus, Joventut). At **Mort** the metre is
broken on purpose: the flowing hexasyllable turns to short, hard mineral words — the
body become stone. Minerals are drawn schematically (ionic SMILES).

All 32 verified at 6 poetic syllables (`node code/sillabes.js`). *feniletilamina*
and *hidroximescalina* are drawn from a representative SMILES; the rest resolve from
PubChem by English name. Each molecule carries a short gloss on the web page.

## Web page

`code/build_web.py` → `index.html`: a self-contained page that reads as a
**standalone poem** in the collection's visual language (Space Mono on a cream
ground — same tokens and vendored webfont as `versos-proteics`). The poem runs down
the page as stanzas, the life stage only whispered (a small faint label). **Each
stanza has one animation panel** on its left that cycles through that stanza's four
molecules (fading; the matching verse lights up); the names read as the stanza and
each **gloss sits in a parallel column** to its right. The title is not bold. No
external requests; single-theme cream. Structures (**RDKit + CoordGen**) resolve from
PubChem (English name / CID) or a SMILES override; minerals are schematic (ionic).
Eventually to be merged with `versos-proteics` into one shared gallery.

## How to run (current)

```bash
node code/sillabes.js --help                          # syllable counter
bash code/fetch_wikidata_ca.sh                        # Catalan names + CID -> data/wikidata-ca.csv
python code/fetch_categories_ca.py                    # themed pool -> data/categories-ca.csv
conda run -n <env> python code/syllable_histogram.py  # length histogram (matplotlib)
conda run -n <env> python code/draw_molecules.py      # 2D structure grid (RDKit)
conda run -n <env> python code/build_web.py           # index.html (RDKit + Node)
```

## Files

- `poem.md` — the poem itself (Catalan).
- `metadata.yml` — title, author, tools, tags, description.
- `code/sillabes.js` — Catalan syllable counter (Node; Softcatalà engine).
- `code/vendor/softcatala/` — vendored Softcatalà syllabification engine.
- `docs/` — Catalan IUPAC nomenclature reference (PDF) + citation.
