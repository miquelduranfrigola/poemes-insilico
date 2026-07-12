# Vendored source: Softcatalà syllable separator/counter

These files are vendored **unmodified** from Softcatalà's "Separador i comptador de
síl·labes en català" — the engine behind <https://www.softcatala.org/sillabes/>.

- **Upstream repo:** <https://github.com/Softcatala/separador-sillabes>
- **Commit pinned:** `b6d270bb89db63a2111aa638f3b30aff987305af`
- **Retrieved:** 2026-07-11

## Files

| File | Role | Origin / license |
|------|------|------------------|
| `ca.js` | Liang TeX-style Catalan hyphenation patterns (`hyphenationPatternsCa`) | Patterns derived from [`jaumeortola/hyphen-ca`](https://github.com/jaumeortola/hyphen-ca). No explicit license header. |
| `hyphen.js` | Franklin M. Liang's hyphenation algorithm in JS | © 2016 Yevhen Tiurin — **MIT** ([ytiurin/hyphen](https://github.com/ytiurin/hyphen)). |
| `hyphen-softcatala.js` | Softcatalà glue: syllable counting (graphic / phonetic / poetic), stress classification, ambiguity hints | Softcatalà. No explicit license file in the upstream repo at the pinned commit. |

> Note: the upstream `separador-sillabes` repo carries no `LICENSE` file at the
> pinned commit. `hyphen.js` is MIT (header preserved). The Catalan patterns come
> from `hyphen-ca`. Before redistributing beyond this research/artistic project,
> confirm the licensing terms with the upstream authors (Softcatalà / Jaume Ortolà).

## Why vendored

The counts in this poem must match the Softcatalà web tool exactly. Rather than
reimplement Catalan syllabification, we run Softcatalà's own JavaScript headlessly
with Node (see `../../sillabes.js`). Pinning the files keeps results reproducible
even if the upstream tool changes.

## How it is driven

`../../sillabes.js` loads these three files into a Node `vm` sandbox that supplies
a stub `console` and a fake `document` (the browser code calls `onChangeFunction()`
and `document.getElementById` at load). It then reproduces the web tool's per-line
pipeline: `getResultLine( hyphenate(text).adjustHyphenatedText() )`.
