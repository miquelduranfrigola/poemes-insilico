"""Geocode the unique towns in ``data/stages.csv`` into ``data/geocode.json``.

Every distinct start/finish town (verbatim, e.g. ``"Barcelona (Spain)"``) is
mapped to ``[lat, lon]`` using the OpenStreetMap Nominatim service. Towns recur
heavily across editions, so only a few hundred lookups are needed.

The cache is written incrementally and the script is resumable: on a re-run it
skips towns already resolved (and never re-queries them), so an interrupted run
just continues. Nominatim's usage policy is respected: one request per second,
a descriptive User-Agent, and English results. Towns that cannot be resolved are
listed at the end for manual entry into ``OVERRIDES`` (or directly into the JSON).
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path

import requests

POEM_ROOT = Path(__file__).resolve().parent.parent
STAGES = POEM_ROOT / "data" / "stages.csv"
OUT = POEM_ROOT / "data" / "geocode.json"

USER_AGENT = "poemes-insilico/1.0 (https://github.com/; research; miquel@ersilia.io)"
ENDPOINT = "https://nominatim.openstreetmap.org/search"

COUNTRIES = {
    "Spain", "Italy", "Belgium", "Netherlands", "Germany", "Luxembourg",
    "Switzerland", "Andorra", "United Kingdom", "England", "Ireland",
    "Denmark", "Monaco", "San Marino",
}

# Hand-resolved coordinates for towns Nominatim cannot place from their name
# (ski stations, circuits, renamed places). Extend as needed; these win over the
# live lookup. Keys must match the town string in stages.csv verbatim.
OVERRIDES: dict[str, list[float]] = {
    # Ski-station / composite finishes and a few foreign towns Nominatim misses.
    "Andorra Arcalis": [42.632, 1.552],
    "Andorra-Arcalis (Andorra)": [42.632, 1.552],
    "Antony/Parc de Sceaux": [48.769, 2.297],
    "Arenberg Porte du Hainaut": [50.398, 3.409],
    "Brussels-Royal Palace (Belgium)": [50.842, 4.362],
    "Finhaut–Émosson (Switzerland)": [46.070, 6.930],
    "Foix Prat d'Albis": [42.930, 1.580],
    "La Super Planche des Belles Filles": [47.775, 6.777],
    "La Toussuire – Les Sybelles": [45.253, 6.293],
    "La Toussuire-Les Sybelles": [45.253, 6.293],
    "Maubourguet Pays du Val d’Adour": [43.468, 0.036],
    "Roskilde": [55.641, 12.080],
    "Super-Besse Sancy": [45.513, 2.853],
    "Val d'Aran/Pla-de-Beret (Spain)": [42.705, 0.980],
    "Vejle": [55.710, 9.535],
    "Vitoria-Gasteiz": [42.850, -2.672],
}


def unique_towns() -> list[str]:
    towns: set[str] = set()
    with STAGES.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            towns.add(row["start"])
            towns.add(row["finish"])
    return sorted(towns)


def build_query(town: str) -> tuple[str, str]:
    """Turn a stage-town string into (place_name, country) for Nominatim."""
    country = "France"
    name = town
    match = re.search(r"\(([^)]+)\)", town)
    if match:
        if match.group(1).strip() in COUNTRIES:
            country = match.group(1).strip()
        name = town[: match.start()].strip()
    name = re.split(r"\s+via\s+", name)[0].strip()          # drop "... via X"
    name = re.sub(r"^Circuit(\s+de)?\s+", "", name).strip()  # "Circuit de Nevers" -> "Nevers"
    return name, country


def geocode(town: str) -> list[float] | None:
    if town in OVERRIDES:
        return OVERRIDES[town]
    name, country = build_query(town)
    params = {
        "q": f"{name}, {country}",
        "format": "json",
        "limit": 1,
        "accept-language": "en",
        "email": "miquel@ersilia.io",
    }
    resp = requests.get(
        ENDPOINT, params=params, headers={"User-Agent": USER_AGENT}, timeout=30
    )
    resp.raise_for_status()
    hits = resp.json()
    if not hits:
        return None
    return [round(float(hits[0]["lat"]), 5), round(float(hits[0]["lon"]), 5)]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cache: dict[str, list[float]] = {}
    if OUT.exists():
        cache = json.loads(OUT.read_text(encoding="utf-8"))

    towns = unique_towns()
    todo = [t for t in towns if t not in cache]
    print(f"{len(towns)} unique towns; {len(cache)} cached; {len(todo)} to resolve")

    misses: list[str] = []
    for i, town in enumerate(todo, 1):
        try:
            coord = geocode(town)
        except Exception as exc:  # noqa: BLE001 - report and keep going
            print(f"  [{i}/{len(todo)}] ERROR {town}: {exc}", file=sys.stderr)
            coord = None
        if coord is None:
            misses.append(town)
            print(f"  [{i}/{len(todo)}] MISS  {town}")
        else:
            cache[town] = coord
            if i % 25 == 0 or i == len(todo):
                OUT.write_text(json.dumps(cache, ensure_ascii=False, indent=0,
                                          sort_keys=True), encoding="utf-8")
                print(f"  [{i}/{len(todo)}] ... saved ({len(cache)} resolved)")
        time.sleep(1.05)  # Nominatim: max 1 request per second

    OUT.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True),
                   encoding="utf-8")
    print(f"\nResolved {len(cache)}/{len(towns)} towns -> {OUT}")
    if misses:
        print(f"\n{len(misses)} unresolved (add to OVERRIDES or edit the JSON):")
        for town in misses:
            print(f"  {town}")


if __name__ == "__main__":
    main()
