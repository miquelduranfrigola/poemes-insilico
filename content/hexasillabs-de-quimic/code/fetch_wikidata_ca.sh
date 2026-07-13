#!/usr/bin/env bash
# Fetch the Catalan molecule-name reference from Wikidata as CSV.
# Output: data/wikidata-ca.csv  (columns: item, name_ca, cid, smiles, formula)
#
# Reproducible source for the poem's trivial-name pool and structure lookups.
# The query lives in wikidata_ca.rq. WDQS requires a descriptive User-Agent.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POEM_ROOT="$(cd "$HERE/.." && pwd)"
OUT_DIR="$POEM_ROOT/data"
OUT="$OUT_DIR/wikidata-ca.csv"

mkdir -p "$OUT_DIR"

curl -sG 'https://query.wikidata.org/sparql' \
  --data-urlencode "query@$HERE/wikidata_ca.rq" \
  -H 'Accept: text/csv' \
  -H 'User-Agent: poemes-insilico/1.0 (https://github.com/; research/art project)' \
  -o "$OUT"

echo "Wrote $OUT ($(wc -l < "$OUT") lines)"
