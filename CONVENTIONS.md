# Conventions

This document is the **shared specification** for repositories in the
*poemes computacionals* family. Any repository that holds computer-assisted
poems follows the same structure so that tooling (site builder, asset fetcher,
scaffolder) and readers can rely on a predictable layout.

## Languages

- **Poems and all user-facing text** (titles, descriptions, tags, the website
  UI) are written in **Catalan**.
- **Code and code-facing documentation** (per-poem `README.md`, docstrings,
  comments, variable names) are written in **English**.
- Code is **Python** by default.

## The poem unit

Every poem lives in its own folder under `content/<slug>/`. The `<slug>` is a
lowercase ASCII slug derived from the Catalan title, accents stripped, words
joined with hyphens (e.g. *"El jardí de nombres"* → `el-jardi-de-nombres`).

Each poem folder contains the **same fixed filenames**:

| Path | Language | Purpose |
|------|----------|---------|
| `poem.md` | Catalan | The poem itself. First `# ` heading is the title. |
| `metadata.yml` | Catalan | Structured metadata (schema below). |
| `README.md` | English | Notes on the computational method + how to run. |
| `install.sh` | — | Portable env setup + Drive asset fetch (contract below). |
| `requirements.txt` | — | Python dependencies for this poem's code (optional). |
| `code/` | English | Python code. `main.py` = computation entry; `build_web.py` = builds the page. |
| `results/index.html` | — | The self-contained web page (served by the site; see below). |
| `assets/drive-manifest.yml` | — | Links to large assets on Google Drive. |

Each piece ships **one self-contained web page** at the fixed path
`results/index.html`, built by `code/build_web.py` (inlining fonts/assets, no
external requests), and wired into the site via `page: results/index.html` in
`metadata.yml`. Heavy intermediates (`cache/`, `results/snapshots/`,
`results/videos/`, big raw inputs) are git-ignored; only `results/index.html` is
committed.

Start a new poem by copying `_template/poem/`, or run
`python scripts/new_poem.py "Títol en català"`.

## `metadata.yml` schema

```yaml
title: El jardí de nombres        # Catalan; also shown as the poem title
slug: el-jardi-de-nombres         # must match the folder name
author: Miquel Duran-Frigola
date: 2026-07-11                  # ISO date (YYYY-MM-DD); drives site ordering
language: ca
page: results/index.html         # self-contained page served verbatim by the site
tools:                            # computational tools used (may be empty)
  - name: nom-de-l-eina
    description: Com s'ha fet servir (Catalan).
tags:                             # free-form, for grouping/filtering
  - generatiu
description: |                    # Catalan, multi-line
  Descripció del poema i del procés.
```

`title`, `slug` and `date` are required; the rest are optional.

## Large files — Google Drive only

Large or binary assets (audio, video, datasets, big images) are **not committed
to git**. Instead:

- List them in a `drive-manifest.yml` — per poem (`content/<slug>/assets/`) and/or
  repo-wide (`shared/drive-manifest.yml`).
- `scripts/fetch_assets.py` downloads each entry to its `path`.
- Downloaded bytes under `assets/` are gitignored; only the manifest is tracked.

Manifest entry schema:

```yaml
- name: raw-audio
  path: assets/raw-audio.wav      # destination, relative to the manifest's folder
  url: https://drive.google.com/uc?id=FILE_ID
  bytes: 5242880                  # optional, informational
```

Trade-off: these assets are **not version-controlled** and depend on the Drive
links staying available. Keep the links public (or shared) and stable.

## `install.sh` contract

Each poem's `install.sh` is self-contained and portable. Run from inside the
poem folder, it:

1. Creates an isolated `.venv` for that poem.
2. Installs `requirements.txt` if present.
3. Runs `scripts/fetch_assets.py assets/drive-manifest.yml` to pull Drive assets.

This keeps every poem independently reproducible.

## Website

The site builder (`site/build_site.py`) reads every `content/<slug>/metadata.yml`
and produces a **left-index shell** (`_site/index.html`) that lists every piece and
shows the selected one in an iframe. Each piece is served from its committed
`results/index.html` via the `page:` key (the builder copies it verbatim to
`_site/<slug>/index.html`); a piece without `page:` falls back to templated
`poem.md` rendering. The whole site shares one look — Space Mono on cream. GitHub
Actions (`.github/workflows/pages.yml`) builds and deploys `_site` on push to `main`.

## Repository layout

```
content/<slug>/       one folder per poem (the unit above)
_template/poem/       copy-me skeleton for a new poem
shared/               small shared assets, repo-wide drive-manifest.yml, vendor/ (fonts)
scripts/              new_poem.py (scaffold), fetch_assets.py (Drive)
site/                 build_site.py, templates/, static/ (style.css, spacemono.css)
.github/workflows/    pages.yml (build + deploy)
```
