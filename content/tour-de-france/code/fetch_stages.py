"""Acquire every Tour de France stage from 1985 to 2026 into ``data/stages.csv``.

Source of truth: the English Wikipedia article for each edition
(``https://en.wikipedia.org/wiki/<year>_Tour_de_France``). Every edition carries
a "Schedule and results" table with a remarkably stable shape:

    Stage | Date | Course | Distance | Type | Type.1 | Winner

We detect that table by its columns (not a fixed index), then parse each row:

* ``Course`` is either ``"Start to Finish"`` or a single town (prologues, circuit
  time trials) where start == finish. A trailing ``(Country)`` marks a foreign
  town and is kept as a geocoding hint; a non-country parenthetical (e.g.
  ``Paris (Champs-Élysées)``) is a district and is dropped from the town name.
* ``Distance`` looks like ``"199.2 km (123.8 mi)"`` -> we keep the kilometres.
* ``Type.1`` is the human terrain label (``Flat stage``, ``Mountain stage``, ...).
* Rest-day and total rows carry a non-stage label and are skipped.

The result is a flat CSV, one row per raced day, committed as an input. Network
is only needed for this one-off acquisition; the CSV is hand-correctable.
"""

from __future__ import annotations

import csv
import re
import sys
import time
from datetime import date, datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

POEM_ROOT = Path(__file__).resolve().parent.parent
OUT = POEM_ROOT / "data" / "stages.csv"

FIRST_YEAR = 1985
LAST_YEAR = 2026

USER_AGENT = "poemes-insilico/1.0 (https://github.com/; research; miquel@ersilia.io)"

# Parenthetical tokens that denote a country (a geocoding hint) rather than a
# city district. Anything else in parentheses is treated as a district and dropped.
COUNTRIES = {
    "Spain", "Italy", "Belgium", "Netherlands", "Germany", "Luxembourg",
    "Switzerland", "Andorra", "United Kingdom", "England", "Ireland",
    "Denmark", "Monaco", "San Marino",
}

# A valid stage label: prologue "P" or a number, optionally split ("5a"/"5b").
STAGE_RE = re.compile(r"^(P|\d+[ab]?)$")
DISTANCE_RE = re.compile(r"([\d][\d.,]*)\s*km")
FOOTNOTE_RE = re.compile(r"\[[^\]]*\]")
FIELDS = ["year", "stage_no", "date", "start", "finish", "distance_km", "type"]


def fetch_html(year: int) -> str:
    url = f"https://en.wikipedia.org/wiki/{year}_Tour_de_France"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=45)
    resp.raise_for_status()
    return resp.text


def stage_table(html: str) -> pd.DataFrame | None:
    """Return the schedule table, detected by its columns."""
    for table in pd.read_html(StringIO(html)):
        cols = [str(c) for c in table.columns]
        low = [c.lower() for c in cols]
        if "stage" in low and "course" in low and "distance" in low:
            table.columns = cols
            return table
    return None


def clean_town(raw: str) -> str:
    """Normalise one endpoint: strip footnotes and non-country parentheticals."""
    town = FOOTNOTE_RE.sub("", str(raw)).strip()
    match = re.search(r"\(([^)]*)\)", town)
    if match and match.group(1).strip() not in COUNTRIES:
        # District/qualifier such as "Paris (Champs-Élysées)" -> "Paris".
        town = town[: match.start()].strip()
    return town


def split_course(course: str) -> tuple[str, str] | None:
    """Return (start, finish) towns, or None if the row is not a stage course."""
    text = FOOTNOTE_RE.sub("", str(course)).strip()
    # Normalise non-breaking / thin spaces so dash separators match.
    text = re.sub(r"[\xa0\u2009\u202f]", " ", text)
    if not text or text.lower() in {"nan", "rest day", "total"}:
        return None
    # " to " is the canonical separator; en/em dashes appear in a few editions.
    for sep in (" to ", " – ", " — "):
        if sep in text:
            start, finish = text.split(sep, 1)
            return clean_town(start), clean_town(finish)
    town = clean_town(text)  # single-location prologue / circuit time trial
    return town, town


def parse_distance(raw: str) -> float | None:
    match = DISTANCE_RE.search(str(raw))
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def parse_date(raw: str, year: int) -> str:
    text = FOOTNOTE_RE.sub("", str(raw)).strip()
    for fmt in ("%d %B", "%d %b"):
        try:
            return datetime.strptime(f"{text} {year}", f"{fmt} %Y").date().isoformat()
        except ValueError:
            continue
    return text


def parse_year(year: int) -> list[dict]:
    df = stage_table(fetch_html(year))
    if df is None:
        raise RuntimeError(f"no stage table found for {year}")

    type_col = "Type.1" if "Type.1" in df.columns else "Type"
    rows: list[dict] = []
    for _, row in df.iterrows():
        stage_no = FOOTNOTE_RE.sub("", str(row["Stage"])).strip()
        # Editions without a prologue have an all-numeric Stage column, which
        # pandas reads as floats ("1.0"); normalise back to plain integers.
        stage_no = re.sub(r"\.0$", "", stage_no)
        if not STAGE_RE.match(stage_no):
            continue  # rest day, "Total", header echo, etc.
        endpoints = split_course(row["Course"])
        distance = parse_distance(row["Distance"])
        if endpoints is None or distance is None:
            continue
        start, finish = endpoints
        rows.append({
            "year": year,
            "stage_no": stage_no,
            "date": parse_date(row.get("Date", ""), year),
            "start": start,
            "finish": finish,
            "distance_km": round(distance, 1),
            "type": FOOTNOTE_RE.sub("", str(row.get(type_col, ""))).strip(),
        })
    if not rows:
        raise RuntimeError(f"stage table for {year} parsed to zero rows")
    return rows


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    problems: list[str] = []
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        try:
            rows = parse_year(year)
            all_rows.extend(rows)
            print(f"{year}: {len(rows):2d} stages")
        except Exception as exc:  # noqa: BLE001 - report and continue per edition
            problems.append(f"{year}: {exc}")
            print(f"{year}: FAILED - {exc}", file=sys.stderr)
        time.sleep(1)  # be polite to Wikipedia

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    years = sorted({r["year"] for r in all_rows})
    print(f"\nWrote {len(all_rows)} stages across {len(years)} editions -> {OUT}")
    if problems:
        print("\nEditions needing manual attention:")
        for line in problems:
            print(f"  {line}")


if __name__ == "__main__":
    main()
