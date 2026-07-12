#!/usr/bin/env python3
"""Shared helpers: verbalise a written molecule name into its spoken Catalan form
and count its poetic syllables via sillabes.js (Softcatala engine, headless).

Verbalisation is a FIRST, simplified version of the poem's standard: spell out
locant digits and isolated letter locants, drop bracketed stereo descriptors.
The syllable counter treats digits as separators, so this must run before it.
"""
import json
import os
import re
import shutil
import subprocess

SILLABES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sillabes.js")

_UNITS = ["zero", "u", "dos", "tres", "quatre", "cinc", "sis", "set", "vuit", "nou"]
_TEENS = {10: "deu", 11: "onze", 12: "dotze", 13: "tretze", 14: "catorze",
          15: "quinze", 16: "setze", 17: "disset", 18: "divuit", 19: "dinou"}
_TENS = {20: "vint", 30: "trenta", 40: "quaranta", 50: "cinquanta", 60: "seixanta",
         70: "setanta", 80: "vuitanta", 90: "noranta"}
_LETTERS = {"N": "ena", "O": "o", "S": "essa", "H": "hac", "P": "pe", "C": "ce"}


def _cardinal(n):
    """Catalan cardinal for 0..99; larger numbers are read digit by digit."""
    if n < 10:
        return _UNITS[n]
    if n < 20:
        return _TEENS[n]
    if n < 100:
        if n % 10 == 0:
            return _TENS[n]
        return f"{_TENS[n // 10 * 10]}-i-{_UNITS[n % 10]}"
    return " ".join(_UNITS[int(d)] for d in str(n))


def verbalise(name):
    """Turn a written name into its spoken Catalan form for syllable counting."""
    s = re.sub(r"\([^)]*\)", " ", name)                          # drop (RS), (E)...
    s = re.sub(r"(?<![A-Za-zÀ-ÿ])([NOSHPC])(?=-)",
               lambda m: " " + _LETTERS[m.group(1)] + " ", s)     # N- -> ena
    s = re.sub(r"\d+", lambda m: " " + _cardinal(int(m.group())) + " ", s)  # 2 -> dos
    return re.sub(r"\s+", " ", s).strip()


def poetic_counts(verbalised_names):
    """Poetic syllable count for each verbalised name (None if empty)."""
    node = shutil.which("node") or "node"
    proc = subprocess.run(
        [node, SILLABES, "--json"],
        input="\n".join(verbalised_names),
        capture_output=True, text=True, check=True,
    )
    data = json.loads(proc.stdout)
    return [None if d.get("empty") else d.get("poetic1") for d in data]
