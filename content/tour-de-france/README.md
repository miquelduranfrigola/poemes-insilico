<!-- Method notes for this poem. Written in ENGLISH (code-facing documentation). -->
# Tour de França — method

An animated map that plays through every edition of the Tour de France from 1985
(the year the author was born) to 2026, drawing each day's stage as a bowed arc
between its start and finish town. As the years play, the routes accumulate into a
palimpsest — the shape of four decades traced across France and its borders.

## The honest data caveat

The real GPS tracks of the stages (the actual roads ridden) only exist from around
**2014** onward. For 1985–2013 nobody logged them, so those road paths cannot be
downloaded from anywhere. What *does* exist for all 42 editions is the start and
finish town of every stage. So each day here is a **reconstruction**: a curve
connecting two towns, not the real road. This is stated plainly in the page's
"Metodologia" section too.

## Pipeline

1. **`code/fetch_stages.py`** — scrape the per-edition English Wikipedia articles
   (`<year>_Tour_de_France`) into `data/stages.csv`
   (`year, stage_no, date, start, finish, distance_km, type`). Detects the schedule
   table by its columns and is robust across all editions 1985–2026.
2. **`code/geocode.py`** — geocode the unique towns via OpenStreetMap Nominatim
   into `data/geocode.json` (`town -> [lat, lon]`). Resumable and cached; 1 req/s.
   Unresolved towns are listed at the end for manual entry into `OVERRIDES`.
3. **`code/make_basemap.py`** — build the simplified western-Europe outline
   `data/europe.geojson` from public Natural-Earth-derived data (run once).
4. **`code/main.py`** — the computation entry point. Reads `stages.csv` +
   `geocode.json` and writes `results/routes.json`: each stage as a sampled Bézier
   arc (or a small loop for prologues / circuit time trials), grouped by year with
   per-edition aggregates. Deterministic, no network.
5. **`code/build_web.py`** — assemble the self-contained `index.html`: inlines the
   Space Mono webfont, the routes and the basemap; renders the SVG map and the
   1985→2026 timeline animation; appends the shared keyboard-nav snippet.

`data/` holds committed **inputs** (`stages.csv`, `geocode.json`, `europe.geojson`);
`results/routes.json` is the committed **output**; `index.html` is the built page.

## How to run

```bash
bash install.sh                 # create the venv and install deps
source .venv/bin/activate
python code/fetch_stages.py     # -> data/stages.csv        (network)
python code/geocode.py          # -> data/geocode.json      (network, ~12 min)
python code/make_basemap.py     # -> data/europe.geojson    (network, once)
python code/main.py             # -> results/routes.json    (offline)
python code/build_web.py        # -> index.html             (offline)
```

The committed `data/` and `results/` files mean steps 1–4 can be skipped; running
`code/build_web.py` alone rebuilds the page.

## Files

- `poem.md` — the poem itself (Catalan).
- `metadata.yml` — title, author, tools, tags, description.
- `code/` — the Python pipeline (English).
- `data/` — committed inputs (stage list, geocode cache, basemap).
- `results/` — committed output (`routes.json`).
- `index.html` — the self-contained animated page (built).
- `assets/drive-manifest.yml` — unused here (no large binaries).
