# Poemes computacionals

Recull de poemes en català assistits per eines computacionals. Cada poema té la
seva pròpia carpeta amb el text, les metadades i el codi (en Python) que l'ha
ajudat a néixer. El recull es publica com a lloc web amb GitHub Pages.

## Estructura

Cada poema viu a `content/<slug>/` amb sempre els mateixos fitxers:

- `poem.md` — el poema (català)
- `metadata.yml` — títol, autoria, data, eines, etiquetes, descripció, `page:`
- `README.md` — notes del mètode computacional (anglès)
- `install.sh` — prepara l'entorn i baixa els fitxers grans de Google Drive
- `code/` — el codi en Python (`main.py` calcula; `build_web.py` genera la pàgina)
- `results/index.html` — la pàgina web autocontinguda de la peça
- `assets/drive-manifest.yml` — enllaços als fitxers grans a Google Drive

L'especificació completa i compartida entre repositoris és a
[`CONVENTIONS.md`](CONVENTIONS.md).

## Afegir un poema

```bash
python scripts/new_poem.py "Títol del poema"
```

## Construir el web localment

```bash
pip install -r site/requirements.txt
python site/build_site.py
# obre _site/index.html
```

## Fitxers grans

Els fitxers grans (àudio, vídeo, dades) no es guarden a git: es referencien a un
`drive-manifest.yml` i es baixen amb `scripts/fetch_assets.py`.
