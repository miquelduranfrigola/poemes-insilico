#!/usr/bin/env python3
"""Draw the 24 poem molecules as a 2D structure grid (6 stanzas x 4 verses).

name_ca --(data/wikidata-ca.csv)--> PubChem CID --(PUG-REST)--> SMILES
--(RDKit)--> 2D depiction. Titles are set with matplotlib so Catalan glyphs
(à, ·) render correctly. Output: data/molecules-2d.png

Run (needs a conda env with rdkit + matplotlib, e.g. ai2050dd):
  conda run -n ai2050dd python code/draw_molecules.py
"""
import csv
import json
import os
import urllib.parse
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rdkit import Chem
from rdkit.Chem import Draw
from rdkit.Chem.Draw import rdMolDraw2D
from PIL import Image
import io

HERE = os.path.dirname(os.path.abspath(__file__))
POEM = os.path.dirname(HERE)
CSV_IN = os.path.join(POEM, "data", "wikidata-ca.csv")
FIG_OUT = os.path.join(POEM, "data", "molecules-2d.png")

# The v2 proposal: 6 thematic stanzas x 4, in poem order. Display names (poem
# casing). "dos-feniletanol" is written verbalised; look it up by its CID name.
STANZAS = [
    ["deshidroemetina", "dimetiltriptamina", "protoanemonina", "citrat de cafeïna"],
    ["glutamat monosòdic", "hidroxitirosol", "benzoat de metil", "propanoat de calci"],
    ["àcid araquidònic", "àcid palmitoleic", "àcid miristoleic", "àcid petroselínic"],
    ["dos-feniletanol", "difenilmetanol", "hexaclorobenzè", "trinitrotoluè"],
    ["acetilcisteïna", "nitrofurantoïna", "òxid de dinitrogen", "povidona iodada"],
    ["hipoclorit de sodi", "hipoclorit de calci", "clorur de benzalconi", "fenoxietanol"],
]
# Display names whose Wikidata label (for CID lookup) differs from the poem line.
CID_ALIAS = {"dos-feniletanol": "2-feniletanol"}
# Molecules with no CID in the pool: a representative SMILES to draw instead.
# Benzalkonium chloride is a homolog mixture; we draw the C12 member.
SMILES_OVERRIDE = {"clorur de benzalconi": "[Cl-].CCCCCCCCCCCC[N+](C)(C)Cc1ccccc1"}


def name_to_cid():
    """Case-insensitive Catalan-name -> PubChem CID map from the Wikidata dump."""
    m = {}
    for r in csv.DictReader(open(CSV_IN)):
        m.setdefault(r["name_ca"].lower(), r["cid"])
    return m


def fetch_smiles(cids):
    """Map CID -> SMILES via one PubChem PUG-REST call (try modern + legacy props)."""
    for prop in ("SMILES", "IsomericSMILES", "CanonicalSMILES"):
        url = (
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
            + ",".join(cids) + f"/property/{prop}/JSON"
        )
        try:
            with urllib.request.urlopen(url, timeout=60) as fh:
                data = json.load(fh)
        except Exception:
            continue
        props = data.get("PropertyTable", {}).get("Properties", [])
        out = {str(p["CID"]): p.get(prop) for p in props if p.get(prop)}
        if out:
            return out
    return {}


def mol_image(smiles, px=340):
    """RDKit 2D depiction as a PIL image (blank placeholder if parsing fails)."""
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return Image.new("RGB", (px, px), "white")
    d = rdMolDraw2D.MolDraw2DCairo(px, px)
    d.drawOptions().padding = 0.12
    rdMolDraw2D.PrepareAndDrawMolecule(d, mol)
    d.FinishDrawing()
    return Image.open(io.BytesIO(d.GetDrawingText()))


def main():
    n2c = name_to_cid()
    flat = [n for row in STANZAS for n in row]
    cids = {n: n2c.get(CID_ALIAS.get(n, n).lower()) for n in flat}
    missing = [n for n, c in cids.items() if not c]
    if missing:
        print("no CID:", missing)
    smiles = fetch_smiles([c for c in cids.values() if c])

    fig, axes = plt.subplots(6, 4, figsize=(13, 19))
    for r, row in enumerate(STANZAS):
        for c, name in enumerate(row):
            ax = axes[r][c]
            cid = cids[name]
            smi = SMILES_OVERRIDE.get(name) or smiles.get(cid, "")
            img = mol_image(smi)
            ax.imshow(img)
            ax.set_title(name, fontsize=12)
            ax.axis("off")
            if not smi:
                ax.text(0.5, 0.5, "(sense estructura)", ha="center", va="center",
                        transform=ax.transAxes, color="gray", fontsize=9)
    fig.suptitle("Hexasíl·labs de químic — estructures 2D (6 estrofes × 4)", fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(FIG_OUT, dpi=150)
    print(f"wrote {FIG_OUT}")


if __name__ == "__main__":
    main()
