#!/usr/bin/env python3
"""Build a THEMED pool of Catalan molecule names from Catalan Wikipedia categories.

For each theme we take the pages of a few seed categories plus the pages of their
direct subcategories (depth 1). We then keep only titles that also appear in the
Wikidata CID pool (data/wikidata-ca.csv) — this both attaches a PubChem CID and
filters out non-molecule concept pages ("Fàrmac", "Toxina", ...). Finally we
count Catalan poetic syllables for each survivor.

Output: data/categories-ca.csv  (name_ca, cid, themes, poetic_syllables)

Run (needs Node on PATH; rate-limited, ~1-2 min):
  python code/fetch_categories_ca.py
"""
import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from molname import verbalise, poetic_counts

HERE = os.path.dirname(os.path.abspath(__file__))
POEM = os.path.dirname(HERE)
POOL_CSV = os.path.join(POEM, "data", "wikidata-ca.csv")
OUT_CSV = os.path.join(POEM, "data", "categories-ca.csv")
API = "https://ca.wikipedia.org/w/api.php"

# Theme -> seed Catalan Wikipedia categories (subcategories are expanded one level).
# Detergents/surfactants have no usable Catalan category (known gap).
THEMES = {
    "farmacs": ["Fàrmacs", "Antibiòtics", "Antisèptics"],
    "verins": ["Toxines", "Alcaloides"],
    "aliments": ["Additius alimentaris"],
    "metabolits": ["Neurotransmissors", "Hormones", "Àcids grassos", "Aminoàcids"],
    "organiques": ["Compostos orgànics", "Esteroides", "Lípids"],
}


MIN_INTERVAL = 2.5          # seconds between requests (be polite: avoids 429)
_last_call = [0.0]
# Subcategory names that are not collections of molecules (skip to cut calls/junk).
_SKIP_SUBCAT = re.compile(
    r"codis|essencials|trastorns|abús|ramaderia|per element|per sistema|"
    r"orfes|contra la covid|receptor|teràpi|extrahospital", re.IGNORECASE)


def _throttle():
    wait = MIN_INTERVAL - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()


def api_get(params):
    last = None
    for attempt in range(6):
        _throttle()
        url = API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "poemes-computacionals/1.0 (research)"})
        try:
            with urllib.request.urlopen(req, timeout=60) as fh:
                return json.load(fh)
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:
                time.sleep(15 * (attempt + 1))    # long back off on rate limit
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e                              # transient network hiccup
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"API request failed after retries: {last}")


_cache = {}


def members(cat, cmtype):
    """All category members of the given type ('page' or 'subcat'), cached."""
    key = (cat, cmtype)
    if key in _cache:
        return _cache[key]
    out, cont = [], {}
    while True:
        d = api_get({"action": "query", "list": "categorymembers",
                     "cmtitle": f"Categoria:{cat}", "cmlimit": "500",
                     "cmtype": cmtype, "format": "json", **cont})
        out += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        if "continue" in d:
            cont = {"cmcontinue": d["continue"]["cmcontinue"]}
        else:
            break
    _cache[key] = out
    return out


def theme_titles(seeds):
    """Article titles for a theme: seed categories + their direct subcategories."""
    titles = set()
    for cat in seeds:
        titles.update(members(cat, "page"))
        for sub in members(cat, "subcat"):
            name = sub.replace("Categoria:", "")
            if _SKIP_SUBCAT.search(name):
                continue
            titles.update(members(name, "page"))
    return {t for t in titles if ":" not in t}


def norm(name):
    """Normalise for matching: lowercase, drop trailing '(...)', collapse spaces."""
    return re.sub(r"\s+", " ", re.sub(r"\s*\([^)]*\)\s*$", "", name)).strip().lower()


def main():
    pool = {}
    for r in csv.DictReader(open(POOL_CSV)):
        pool.setdefault(norm(r["name_ca"]), (r["name_ca"], r["cid"]))

    mol_themes = {}   # cid-name -> {"name": name_ca, "cid": cid, "themes": set()}
    for theme, seeds in THEMES.items():
        matched = 0
        for title in theme_titles(seeds):
            hit = pool.get(norm(title))
            if hit:
                name_ca, cid = hit
                e = mol_themes.setdefault(cid, {"name": name_ca, "cid": cid, "themes": set()})
                e["themes"].add(theme)
                matched += 1
        print(f"{theme}: {matched} molècules amb CID")

    mols = sorted(mol_themes.values(), key=lambda e: e["name"].lower())
    counts = poetic_counts([verbalise(m["name"]) for m in mols])

    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name_ca", "cid", "themes", "poetic_syllables"])
        for m, c in zip(mols, counts):
            w.writerow([m["name"], m["cid"], "|".join(sorted(m["themes"])),
                        c if c is not None else ""])

    print(f"\nTotal molècules úniques: {len(mols)}")
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
