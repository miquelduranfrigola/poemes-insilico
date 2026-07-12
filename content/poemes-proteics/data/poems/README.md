<!-- Input corpus for the folding experiment. -->
# Poems corpus

Drop one poem per `.txt` file here (UTF-8, Catalan). The filename (without `.txt`)
is the poem's id; each non-empty line is a verse. The pipeline encodes the whole
poem to a protein via the rubric and folds it with ESMFold — poems longer than the
API's 400-residue cap are folded per **domain** (split on verse boundaries).

The bundled files are **full public-domain poems** — replace them with your own:

- `maragall-la-vaca-cega.txt` — Joan Maragall, *La vaca cega* (d. 1911).
- `salvat-res-no-es-mesqui.txt` — Joan Salvat-Papasseit, *Res no és mesquí* (d. 1924).
- `salvat-mester-damor.txt` — Joan Salvat-Papasseit, *Mester d'amor* (d. 1924).
