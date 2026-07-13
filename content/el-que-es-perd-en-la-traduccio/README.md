<!-- Method notes for this poem. Written in ENGLISH (code-facing documentation). -->
# El que es perd en la traducció — method

Pablo Neruda's twenty love poems (plus the *canción desesperada*) are
**despoetized**: each is pushed through **104 sequential Google-Translate
languages** and back to Spanish. "Poetry is what gets lost in translation"
(R. Frost) — so what returns is the degraded residue of the original. The
poem is the collection of those residues, presented in a museum-style gallery
beside Neruda's originals.

This is an archival integration of the 2016 project
[`litcompu`](https://github.com/miquelduranfrigola/litcompu). The despoetized
texts under `data/despoetized/` are the **canonical artifact** (the 2016 run);
the code here documents and reproduces the method, but a fresh run differs
because Google Translate is a moving target.

## The chain

Starting from Spanish (`es`), translate into the next language in alphabetical
order, then the next, ... all the way around Google's 2016 roster and back to
Spanish — 104 translation steps. The exact succession is derived in
`code/languages.py` and verified to match the original method note:

```
es -> et -> eu -> fa -> fi -> fr -> ... -> en -> eo -> es
```

## Pipeline

1. **`code/languages.py`** — Google Translate's 2016 language roster (sorted by
   ISO code), the cyclic `chain()` that reproduces the succession, and Catalan
   names for each code.
2. **`code/despoetize.py`** — runs a text around the chain. `google_translator()`
   provides a `deep-translator` backend (optional dep) with a small code remap
   for the handful of ISO codes Google has since renamed (`iw→he`, `jw→jv`,
   `zh→zh-CN`).
3. **`code/main.py`** — CLI: list pieces, print the chain, show an archived
   original+residue pair, or re-run the chain live for one piece.
4. **`code/build_web.py`** — assembles the self-contained `index.html` (poem-folder
   root): Space Mono on a cream ground, a sticky index, and two sections the reader
   switches between — the poems (each plain text, with Neruda's original behind a
   toggle) and a "Metodologia" note whose 104-language grid animates a sweep through
   the chain. Everything is inlined (no external requests).

## How to run

```bash
bash install.sh                 # create the venv + install deps
source .venv/bin/activate

python code/main.py                  # list all pieces
python code/main.py --chain          # print the 104-language chain
python code/main.py poema01          # original + archived despoetization
python code/main.py --run poema01    # RE-RUN the chain live (needs network);
                                     # result WILL differ from the 2016 artifact

python code/build_web.py             # rebuild index.html
```

## Inputs / outputs

- `data/originals/*.txt` — Neruda's twenty love poems + `cancion` (the input).
- `data/despoetized/*.txt` — the 2016 despoetized residues (the poem).
- `data/_meta.json` — piece order, titles, and original incipits.
- `index.html` — the built page at the poem-folder root (served verbatim as the
  poem's website page via `metadata.yml: page`).

## Files

- `poem.md` — the despoetized collection as plain text (Catalan title).
- `metadata.yml` — title, author, tools, tags, description, `page`.
- `docs/method.md` — the full 104-language chain and provenance.
- `code/` — `languages.py`, `despoetize.py`, `main.py`, `build_web.py`.

## Provenance & attribution

The originals are Pablo Neruda, *Veinte poemas de amor y una canción
desesperada* (1924); source PDF linked from `docs/method.md`. The despoetized
texts are a transformative computational work first produced in 2016.
