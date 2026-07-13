# Method — the despoetization chain

<!-- Code-facing documentation (English). -->

*Veinte poemas de amor y una canción desesperada* by Pablo Neruda (1924) is
**despoetized** by round-tripping each poem through Google Translate's whole
language roster: from Spanish, into the next language alphabetically, then the
next, ... and finally back to Spanish. There are **104 translation
steps** (104 despoetizations). Poetry is what gets lost in translation.

The chain is derived programmatically in `code/languages.py` (sorted roster +
cyclic succession starting at `es`) and verified to reproduce the original 2016
method note exactly.

## The full chain (es → … → es)

```
[es] Spanish -> [et] Estonian -> [eu] Basque -> [fa] Persian -> [fi] Finnish ->
[fr] French -> [fy] Frisian -> [ga] Irish -> [gd] Scots Gaelic -> [gl] Galician ->
[gu] Gujarati -> [ha] Hausa -> [haw] Hawaiian -> [hi] Hindi -> [hmn] Hmong ->
[hr] Croatian -> [ht] Haitian Creole -> [hu] Hungarian -> [hy] Armenian -> [id] Indonesian ->
[ig] Igbo -> [is] Icelandic -> [it] Italian -> [iw] Hebrew -> [ja] Japanese ->
[jw] Javanese -> [ka] Georgian -> [kk] Kazakh -> [km] Khmer -> [kn] Kannada ->
[ko] Korean -> [ku] Kurdish (Kurmanji) -> [ky] Kyrgyz -> [la] Latin -> [lb] Luxembourgish ->
[lo] Lao -> [lt] Lithuanian -> [lv] Latvian -> [mg] Malagasy -> [mi] Maori ->
[mk] Macedonian -> [ml] Malayalam -> [mn] Mongolian -> [mr] Marathi -> [ms] Malay ->
[mt] Maltese -> [my] Myanmar (Burmese) -> [ne] Nepali -> [nl] Dutch -> [no] Norwegian ->
[ny] Chichewa -> [pa] Punjabi -> [pl] Polish -> [ps] Pashto -> [pt] Portuguese ->
[ro] Romanian -> [ru] Russian -> [sd] Sindhi -> [si] Sinhala -> [sk] Slovak ->
[sl] Slovenian -> [sm] Samoan -> [sn] Shona -> [so] Somali -> [sq] Albanian ->
[sr] Serbian -> [st] Sesotho -> [su] Sundanese -> [sv] Swedish -> [sw] Swahili ->
[ta] Tamil -> [te] Telugu -> [tg] Tajik -> [th] Thai -> [tl] Filipino ->
[tr] Turkish -> [uk] Ukrainian -> [ur] Urdu -> [uz] Uzbek -> [vi] Vietnamese ->
[xh] Xhosa -> [yi] Yiddish -> [yo] Yoruba -> [zh] Chinese -> [zh-TW] Chinese (Traditional) ->
[zu] Zulu -> [af] Afrikaans -> [am] Amharic -> [ar] Arabic -> [az] Azerbaijani ->
[be] Belarusian -> [bg] Bulgarian -> [bn] Bengali -> [bs] Bosnian -> [ca] Catalan ->
[ceb] Cebuano -> [co] Corsican -> [cs] Czech -> [cy] Welsh -> [da] Danish ->
[de] German -> [el] Greek -> [en] English -> [eo] Esperanto -> [es] Spanish ->
```

## Notes

- The roster is Google Translate's set of languages **as of 2016** — the exact
  list the original notebook printed. Codes are Google's historical ISO codes;
  a few have since been renamed (`iw`→`he` Hebrew, `jw`→`jv` Javanese,
  `zh`→`zh-CN` Chinese), remapped in `code/despoetize.py` for modern re-runs.
- Results are shown with only minor grammatical corrections, as in the original
  project.

## Provenance & attribution

- Originals: Pablo Neruda, *Veinte poemas de amor y una canción desesperada*
  (1924). Source PDF:
  <http://www.archivochile.com/Homenajes/neruda/de_neruda/homenajepneruda0007.pdf>
- Method + despoetized results first produced in 2016 in
  <https://github.com/miquelduranfrigola/litcompu>.
