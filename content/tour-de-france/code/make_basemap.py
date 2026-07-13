"""Build the bundled, simplified Europe basemap ``data/europe.geojson``.

Source: the public "map-of-europe" GeoJSON (Natural-Earth-derived country
outlines). We keep only the countries the Tour de France has visited plus a few
neighbours for context, drop small offshore islands, and round coordinates to two
decimals (~1 km) so the whole map inlines into the self-contained page at a modest
size. Run once; the output is committed as an input.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

POEM_ROOT = Path(__file__).resolve().parent.parent
OUT = POEM_ROOT / "data" / "europe.geojson"
SOURCE = ("https://raw.githubusercontent.com/leakyMirror/map-of-europe/"
          "master/GeoJSON/europe.geojson")
USER_AGENT = "poemes-insilico/1.0 (research; miquel@ersilia.io)"

# Countries the race has touched (1985-2026) plus immediate context, so the map
# reads as "western Europe" without the clutter of the whole continent.
KEEP = {
    "France", "Spain", "Portugal", "Andorra", "Monaco", "Italy", "San Marino",
    "Switzerland", "Germany", "Belgium", "Netherlands", "Luxembourg",
    "United Kingdom", "Ireland", "Denmark", "Austria",
}
PRECISION = 2       # decimal places (~1.1 km)
MIN_RING_AREA = 0.05  # drop offshore islets smaller than this (square degrees, bbox)


def dedupe(ring: list) -> list:
    out: list = []
    for pt in ring:
        rounded = [round(pt[0], PRECISION), round(pt[1], PRECISION)]
        if not out or out[-1] != rounded:
            out.append(rounded)
    return out


def bbox_area(ring: list) -> float:
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def simplify_polygon(poly: list) -> list | None:
    rings = []
    for ring in poly:
        simplified = dedupe(ring)
        if len(simplified) >= 4 and bbox_area(simplified) >= MIN_RING_AREA:
            rings.append(simplified)
    return rings or None


def simplify_geometry(geom: dict) -> dict | None:
    if geom["type"] == "Polygon":
        rings = simplify_polygon(geom["coordinates"])
        return {"type": "Polygon", "coordinates": rings} if rings else None
    if geom["type"] == "MultiPolygon":
        polys = [p for p in (simplify_polygon(poly) for poly in geom["coordinates"]) if p]
        return {"type": "MultiPolygon", "coordinates": polys} if polys else None
    return None


def main() -> None:
    resp = requests.get(SOURCE, headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    raw = resp.json()

    features = []
    for feat in raw["features"]:
        name = feat["properties"].get("NAME")
        if name not in KEEP:
            continue
        geom = simplify_geometry(feat["geometry"])
        if geom is None:
            continue
        features.append({"type": "Feature", "properties": {"name": name},
                         "geometry": geom})

    out = {"type": "FeatureCollection", "features": features}
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"Wrote {len(features)} countries -> {OUT} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
