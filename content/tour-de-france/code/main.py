"""Reconstruct each Tour de France stage as a smooth arc and write results/routes.json.

This is the computation entry point. It reads the acquired inputs
(``data/stages.csv`` + ``data/geocode.json``) and, for every raced day from 1985
to 2026, draws a gentle curve between the geocoded start and finish towns.

We do NOT have the real road tracks for the older editions -- only the start and
finish towns exist that far back. So each day is reconstructed as a quadratic
Bezier arc: a chord from start to finish, bowed sideways by a fixed fraction of
its length so the lines read as journeys rather than rulers and repeated routes
overlap cleanly. Single-location days (prologues, circuit time trials) become a
small loop around the town. The geometry is deterministic and needs no network.

Output ``results/routes.json`` groups stages by year with the sampled polylines
and per-edition aggregates, ready for the page builder to project and animate.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

POEM_ROOT = Path(__file__).resolve().parent.parent
STAGES = POEM_ROOT / "data" / "stages.csv"
GEOCODE = POEM_ROOT / "data" / "geocode.json"
OUT = POEM_ROOT / "results" / "routes.json"

BOW = 0.16          # sideways bulge of an arc, as a fraction of its chord length
SAMPLES = 44        # points sampled along each stage arc
LOOP_RADIUS = 0.13  # degrees; radius of the loop drawn for single-town stages
LOOP_SAMPLES = 40


def clean_display(town: str) -> str:
    """Human-facing town name: drop the country hint and any 'via ...' tail."""
    name = re.sub(r"\s*\([^)]*\)", "", town)
    name = re.split(r"\s+via\s+", name)[0]
    return name.strip()


def bezier_arc(start: list[float], finish: list[float]) -> list[list[float]]:
    """Quadratic Bezier from start to finish, bowed to one side. [lat, lon] points."""
    lat0, lon0 = start
    lat1, lon1 = finish
    # Work in (x=lon, y=lat); latitude scaling is irrelevant for a stylised arc.
    dx, dy = lon1 - lon0, lat1 - lat0
    length = math.hypot(dx, dy)
    mx, my = (lon0 + lon1) / 2, (lat0 + lat1) / 2
    if length < 1e-9:
        return [[lat0, lon0], [lat1, lon1]]
    # Control point: midpoint pushed along the left-hand normal of the chord.
    nx, ny = -dy / length, dx / length
    cx, cy = mx + nx * BOW * length, my + ny * BOW * length
    points = []
    for i in range(SAMPLES + 1):
        t = i / SAMPLES
        u = 1 - t
        x = u * u * lon0 + 2 * u * t * cx + t * t * lon1
        y = u * u * lat0 + 2 * u * t * cy + t * t * lat1
        points.append([round(y, 4), round(x, 4)])
    return points


def loop(center: list[float]) -> list[list[float]]:
    """A small closed loop around a point, for prologues / circuit time trials."""
    lat, lon = center
    points = []
    for i in range(LOOP_SAMPLES + 1):
        a = 2 * math.pi * i / LOOP_SAMPLES
        points.append([round(lat + LOOP_RADIUS * math.sin(a), 4),
                       round(lon + LOOP_RADIUS * math.cos(a) * 1.4, 4)])
    return points


def main() -> None:
    geo = json.loads(GEOCODE.read_text(encoding="utf-8"))
    with STAGES.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    by_year: dict[int, list[dict]] = defaultdict(list)
    missing: set[str] = set()
    for row in rows:
        start_c, finish_c = geo.get(row["start"]), geo.get(row["finish"])
        if start_c is None:
            missing.add(row["start"])
        if finish_c is None:
            missing.add(row["finish"])
        if start_c is None or finish_c is None:
            continue
        same = row["start"] == row["finish"] or start_c == finish_c
        points = loop(start_c) if same else bezier_arc(start_c, finish_c)
        by_year[int(row["year"])].append({
            "no": row["stage_no"],
            "start": clean_display(row["start"]),
            "finish": clean_display(row["finish"]),
            "km": float(row["distance_km"]),
            "type": row["type"],
            "circuit": same,
            "points": points,
        })

    years = []
    for year in sorted(by_year):
        stages = by_year[year]
        years.append({
            "year": year,
            "n_stages": len(stages),
            "total_km": round(sum(s["km"] for s in stages), 1),
            "grand_depart": stages[0]["start"] if stages else None,
            "stages": stages,
        })

    payload = {
        "meta": {
            "first_year": years[0]["year"],
            "last_year": years[-1]["year"],
            "n_years": len(years),
            "n_stages": sum(y["n_stages"] for y in years),
            "note": ("Arcs are reconstructed connections between each stage's start "
                     "and finish towns, not the real roads: GPS tracks only exist "
                     "from ~2014 onward."),
        },
        "years": years,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")

    print(f"Wrote {payload['meta']['n_stages']} stages across "
          f"{payload['meta']['n_years']} editions -> {OUT} "
          f"({OUT.stat().st_size / 1024:.0f} KB)")
    if missing:
        print(f"\nWARNING: {len(missing)} towns had no coordinates and were skipped.",
              file=sys.stderr)
        print("Add them to code/geocode.py OVERRIDES (or data/geocode.json):",
              file=sys.stderr)
        for town in sorted(missing):
            print(f"  {town}", file=sys.stderr)


if __name__ == "__main__":
    main()
