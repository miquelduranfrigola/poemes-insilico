<!-- Reference for this poem. Written in ENGLISH (code-facing docs). -->
# Rubric: Catalan ↔ amino-acid encoding

The rule in one line: **every amino-acid letter encodes the Catalan letter of the
same name; the residue `W` is the escape for everything else.**

There are 20 amino-acid one-letter codes: `A R N D C E Q G H I L K M F P S T W Y V`.
Nineteen of them double as Catalan letters and map straight through. `W` is held
back as an escape prefix, so any Catalan character without an amino acid of its own
name (`o u b j x z ç l·l`, and `w` itself) is written as `W` + one letter.

## Direct 1:1 (19)

```
a→A  c→C  d→D  e→E  f→F  g→G  h→H  i→I  k→K  l→L
m→M  n→N  p→P  q→Q  r→R  s→S  t→T  v→V  y→Y
```

- `k→K` is honest 1:1 (K = Lysine). Rare in Catalan, but it keeps the rule clean.
- `y→Y` is *native*, not a loanword hack: Catalan writes /ɲ/ as the digraph **`ny`**
  (`canya`, `Catalunya`), so `n·y → NY`.

## Escape codes (`W` + letter)

| Catalan | code | mnemonic |
|--------:|:-----|:---------|
| `o`   | `WQ` | `Q` is the round, O-shaped letter |
| `u`   | `WV` | U and V were one letter in Latin |
| `b`   | `WP` | b = voiced p (bilabial pair) |
| `j`   | `WG` | Catalan j = soft g (*girafa / jaqueta*) |
| `z`   | `WS` | z = voiced s |
| `x`   | `WH` | the /ʃ/ "ix" sound |
| `ç`   | `WK` | c-trencada — leaves `K` free for the real `k` |
| `w`   | `WW` | `W` is the escape, so Catalan `w` doubles it |
| `l·l` | `WL` | geminate l, kept distinct from `ll → LL` |

Second letters are only ever consumed as the *second* symbol of a `W`-pair, so the
code stays **prefix-free**: on decode, a `W` means "read two", anything else means
"read one".

## Normalisation

- **Case-insensitive:** output is uppercase amino-acid codes.
- **Accents collapse** to the base vowel: à→a, è/é→e, í/ï→i, ò/ó→o, ú/ü→u. `ç` is
  *not* collapsed (it has its own code, `WK`).
- **Spaces** are preserved (they also separate words on decode). Other punctuation
  and digits are dropped.
- Because accents are dropped, decoding is faithful at the *letter* level but
  returns unaccented Catalan (e.g. `química → quimica`).

## Digraphs fall out for free

Letter-by-letter encoding reproduces the digraphs without special cases:
`ny → NY`, `ll → LL`, `rr → RR`, `ss → SS`, `qu → QWV`, `ix → IWH`. The geminate
`l·l → WL` is the one that must stay distinct from `ll → LL`.

## Examples

```
Catalunya        → CATALWVNYA        → catalunya
molècula         → MWQLECWVLA        → molecula
força major      → FWQRWKA MAWGWQR   → força major
zel i caça       → WSEL I CAWKA      → zel i caça
```

## Related

Implemented (encoder + decoder + round-trip self-test) in
[`../code/main.py`](../code/main.py):

```bash
python code/main.py "Catalunya"            # encode
python code/main.py --decode "CATALWVNYA"  # decode
python code/main.py --selftest             # round-trip demo
```
