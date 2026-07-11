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

Every poem lives in its own folder under `poems/<slug>/`. The `<slug>` is a
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
| `code/` | English | Python code that assisted the poem. Entry point `main.py`. |
| `assets/drive-manifest.yml` | — | Links to large assets on Google Drive. |

Start a new poem by copying `_template/poem/`, or run
`python scripts/new_poem.py "Títol en català"`.

## `metadata.yml` schema

```yaml
title: El jardí de nombres        # Catalan; also shown as the poem title
slug: el-jardi-de-nombres         # must match the folder name
author: Miquel Duran-Frigola
date: 2026-07-11                  # ISO date (YYYY-MM-DD); drives site ordering
language: ca
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

- List them in a `drive-manifest.yml` — per poem (`poems/<slug>/assets/`) and/or
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

The site builder (`site/build_site.py`) reads every `poems/<slug>/metadata.yml`
and renders `poem.md` into an index page plus one page per poem under `_site/`.
The markdown + metadata are the single source of truth — authors never edit
HTML. GitHub Actions (`.github/workflows/pages.yml`) builds and deploys `_site`
to GitHub Pages on every push to `main`.

## Repository layout

```
poems/<slug>/        one folder per poem (the unit above)
_template/poem/       copy-me skeleton for a new poem
shared/               small shared assets + repo-wide drive-manifest.yml
scripts/              new_poem.py (scaffold), fetch_assets.py (Drive)
site/                 build_site.py, templates/, static/, requirements.txt
.github/workflows/    pages.yml (build + deploy)
```
