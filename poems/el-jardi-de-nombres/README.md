<!-- Method notes for this poem. Written in ENGLISH (code-facing documentation). -->
# Title of the poem — method

Short description, in English, of the computational method used to assist this
poem: the idea, the model or algorithm, the inputs and the outputs.

## How to run

```bash
bash install.sh          # create the venv, install deps, fetch Drive assets
source .venv/bin/activate
python code/main.py       # regenerate the computational material
```

## Files

- `poem.md` — the poem itself (Catalan).
- `metadata.yml` — title, author, tools, tags, description.
- `code/` — the Python code that assisted the poem (English).
- `assets/drive-manifest.yml` — links to large assets stored on Google Drive.
