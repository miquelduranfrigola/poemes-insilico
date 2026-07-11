# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**poemes-computacionals** — a collection of poems in Catalan, each assisted by computational tools and paired with the Python code that produced it. The collection is published as a static website via GitHub Pages.

The structure is a shared standard meant to be replicated across sibling "poemes" repositories. The authoritative spec is [`CONVENTIONS.md`](CONVENTIONS.md) — read it before adding or restructuring content.

## Language rules (important)

- **Poems and user-facing text** (titles, `metadata.yml` descriptions/tags, website UI, README.md at repo root) → **Catalan**.
- **Code and code-facing docs** (per-poem `README.md`, docstrings, comments, identifiers) → **English**. Code is **Python**.

## Structure

- `poems/<slug>/` — one folder per poem, the standardised unit. `<slug>` is an accent-stripped ASCII slug of the Catalan title. Fixed filenames: `poem.md` (Catalan), `metadata.yml`, `README.md` (English), `install.sh`, `requirements.txt`, `code/main.py`, `assets/drive-manifest.yml`.
- `_template/poem/` — copy-me skeleton mirroring the poem unit.
- `shared/` — small shared assets + repo-wide `drive-manifest.yml`.
- `scripts/` — `new_poem.py` (scaffold), `fetch_assets.py` (Drive downloads).
- `site/` — `build_site.py`, Jinja2 `templates/`, `static/`, `requirements.txt`.
- `.github/workflows/pages.yml` — build `_site` and deploy to Pages on push to `main`.

## Large files — Google Drive, not git

Large/binary assets are **never committed**. They are listed in `drive-manifest.yml` files (per-poem under `assets/`, and repo-wide under `shared/`) and downloaded on demand by `scripts/fetch_assets.py`. `.gitignore` excludes the downloaded bytes; only the manifests are tracked. Git LFS/DVC are intentionally not used here.

## Common commands

```bash
# Add a new poem (scaffolds poems/<slug>/ from _template/poem)
python scripts/new_poem.py "Títol del poema en català"

# Set up one poem's isolated env and pull its Drive assets
cd poems/<slug> && bash install.sh

# Fetch large assets for a manifest without a full install
python scripts/fetch_assets.py poems/<slug>/assets/drive-manifest.yml

# Build the website locally into ./_site
pip install -r site/requirements.txt
python site/build_site.py            # add --out DIR to change output
```

The site builder is the source of truth: it reads each `poems/<slug>/metadata.yml` and renders `poem.md` to HTML. Never hand-edit generated HTML — edit the markdown/metadata and rebuild.

## Conventions to preserve

- `metadata.yml` requires `title`, `slug` (must equal the folder name), and `date` (ISO `YYYY-MM-DD`, used for site ordering — newest first).
- Every poem folder keeps the same fixed filenames so the tooling and website can rely on them.
- The repo-root `README.md` and commit messages are in Catalan.
