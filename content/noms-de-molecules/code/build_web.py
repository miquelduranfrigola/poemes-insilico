"""Assemble the self-contained "Noms de molècules" web page (HTML).

Reads as a standalone poem, in the visual language of the sibling "Poemes proteics"
gallery (Space Mono on a cream ground). The poem runs down the page as stanzas —
the life stage only whispered (a small faint label). Each stanza has ONE animation
panel on its left that cycles through that stanza's four molecules (fading); the
matching verse lights up, and each verse's gloss sits in a clear parallel column to
its right.

Each verse is a hexasyllable and each stanza rhymes with its own suffix; at Mort the
metre deliberately collapses into short mineral words. Structures are drawn with RDKit
(CoordGen) and inlined as SVG, resolved from PubChem (English name / CID) or a SMILES
override. No external requests. Writes results/index.html.

Run (needs rdkit + Node on PATH, e.g. conda env ai2050dd):
  conda run -n ai2050dd python code/build_web.py
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
import urllib.request

from rdkit import Chem
from rdkit.Chem import rdCoordGen
from rdkit.Chem.Draw import rdMolDraw2D

HERE = os.path.dirname(os.path.abspath(__file__))
POEM = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(POEM))
FONT_CSS = os.path.join(REPO, "shared", "vendor", "spacemono.css")
OUT = os.path.join(POEM, "results", "index.html")

STAGES = [
    {"id": "fetus", "stage": "fetus", "mols": [
        {"ca": "desoxiguanosina", "en": "deoxyguanosine", "g": "una de les quatre lletres amb què t'escriuen"},
        {"ca": "desoxicitidina",  "en": "deoxycytidine",  "g": "la que sempre s'aparella amb la G"},
        {"ca": "desoxitimidina",  "en": "thymidine",      "g": "la que et distingeix d'un virus d'ARN"},
        {"ca": "triiodotironina", "en": "triiodothyronine", "g": "l'hormona que et cabla el cervell abans de tenir-lo"}]},
    {"id": "nado", "stage": "nadó", "mols": [
        {"ca": "colecalciferol",  "en": "cholecalciferol", "g": "vitamina D en gotes, per un os que no ha vist el sol"},
        {"ca": "ergocalciferol",  "en": "ergocalciferol",  "g": "la mateixa vitamina, però treta d'un bolet"},
        {"ca": "fenoxietanol",    "en": "2-phenoxyethanol", "g": "el conservant que va dins la primera vacuna"},
        {"ca": "isoproterenol",   "en": "isoprenaline",    "g": "el primer cop que et costa respirar"}]},
    {"id": "infantesa", "stage": "infantesa", "mols": [
        {"ca": "butanoat d'etil", "en": "ethyl butanoate", "g": "olor de pinya: el xiclet"},
        {"ca": "hexanoat d'etil", "en": "ethyl hexanoate", "g": "olor de poma: la piruleta"},
        {"ca": "butirat de pentil", "en": "pentyl butyrate", "g": "olor de plàtan: el iogurt de colors"},
        {"ca": "salicilat d'etil", "en": "ethyl salicylate", "g": "olor de menta: la primera pasta de dents"}]},
    {"id": "adolescencia", "stage": "adolescència", "mols": [
        {"ca": "metiltestosterona", "en": "methyltestosterone", "g": "la veu que se't trenca i el borrissol"},
        {"ca": "fluoximesterona",   "en": "fluoxymesterone",    "g": "el que algú es punxa al vestidor del gimnàs"},
        {"ca": "espironolactona",   "en": "spironolactone",     "g": "la pastilla contra els grans (i contra el gènere)"},
        {"ca": "desoximetasona",    "en": "desoximetasone",     "g": "la crema per a la cara vermella"}]},
    {"id": "joventut", "stage": "joventut", "mols": [
        {"ca": "feniletilamina",    "smiles": "NCCc1ccccc1", "g": "el que et deixa el cor quan t'enamores (i la xocolata)"},
        {"ca": "dimetiltriptamina", "en": "dimethyltryptamine", "g": "l'univers sencer en cinc minuts"},
        {"ca": "dietiltriptamina",  "en": "diethyltryptamine",  "g": "la cosina de sortida llarga de la DMT"},
        {"ca": "hidroximescalina",  "smiles": "COc1cc(CCN)cc(OC)c1O", "g": "el que porta el peiot, al desert"}]},
    {"id": "adultesa", "stage": "adultesa", "mols": [
        {"ca": "àcid undecanoic",  "en": "undecanoic acid",  "g": "un greix que s'acumula sense avisar"},
        {"ca": "àcid tridecanoic", "en": "tridecanoic acid", "g": "cadena imparella, rara, com tu als quaranta"},
        {"ca": "àcid icosanoic",   "en": "icosanoic acid",   "g": "vint carbonis de sopar tard i seure molt"},
        {"ca": "àcid octandioic",  "en": "octanedioic acid", "g": "fins la teva suor ja fa una altra olor"}]},
    {"id": "vellesa", "stage": "vellesa", "mols": [
        {"ca": "acetazolamida",   "en": "acetazolamide",   "g": "per al glaucoma: la vista que s'estreny"},
        {"ca": "acetohexamida",   "en": "acetohexamide",   "g": "per al sucre que ja no saps controlar"},
        {"ca": "ciclopentiazida", "en": "cyclopenthiazide", "g": "per a la tensió i les nits al lavabo"},
        {"ca": "meticlotiazida",  "en": "methyclothiazide", "g": "i un altre, per les cames que s'inflen"}]},
    {"id": "mort", "stage": "mort", "mols": [
        {"ca": "hidroxiapatita", "smiles": "[OH-].[Ca+2].[Ca+2].[Ca+2].[Ca+2].[Ca+2].[O-]P([O-])([O-])=O.[O-]P([O-])([O-])=O.[O-]P([O-])([O-])=O", "g": "el mineral de l'os: el que de tu perdura"},
        {"ca": "calcita",  "smiles": "[Ca+2].[O-]C([O-])=O",        "g": "el calci, tornat pedra calcària"},
        {"ca": "pirita",   "smiles": "[Fe+2].[S-][S-]",             "g": "l'or dels ximples, avall"},
        {"ca": "hematita", "smiles": "[O-2].[O-2].[O-2].[Fe+3].[Fe+3]", "g": "el ferro de la sang, ara rovell"}]},
]


def _pubchem(path):
    url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/" + path
    try:
        with urllib.request.urlopen(url, timeout=60) as fh:
            return json.load(fh)
    except Exception:
        return {}


def smiles_for(m):
    if m.get("smiles"):
        return m["smiles"]
    ident = (f"cid/{m['cid']}" if m.get("cid")
             else "name/" + urllib.parse.quote(m["en"]))
    for prop in ("SMILES", "IsomericSMILES", "CanonicalSMILES"):
        data = _pubchem(f"{ident}/property/{prop}/JSON")
        for p in data.get("PropertyTable", {}).get("Properties", []):
            if p.get(prop):
                return p[prop]
    return ""


def mol_svg(smiles, px=360):
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return ""
    rdCoordGen.AddCoords(mol)
    d = rdMolDraw2D.MolDraw2DSVG(px, px)
    opt = d.drawOptions()
    opt.clearBackground = False
    opt.bondLineWidth = 2
    opt.scaleBondWidth = True
    opt.padding = 0.08
    opt.minFontSize = 15
    opt.maxFontSize = 24
    opt.additionalAtomLabelPadding = 0.08
    opt.setAtomPalette({
        -1: (0.16, 0.16, 0.16),
        7: (0.13, 0.34, 0.77), 8: (0.78, 0.20, 0.16),
        16: (0.72, 0.56, 0.10), 17: (0.20, 0.52, 0.28),
        9: (0.20, 0.52, 0.28), 35: (0.55, 0.28, 0.16),
        53: (0.45, 0.25, 0.60), 15: (0.80, 0.45, 0.10),
        11: (0.50, 0.40, 0.35), 20: (0.40, 0.42, 0.45), 19: (0.55, 0.45, 0.20),
        24: (0.35, 0.45, 0.40), 25: (0.55, 0.35, 0.45), 26: (0.62, 0.34, 0.20),
    })
    rdMolDraw2D.PrepareAndDrawMolecule(d, mol)
    d.FinishDrawing()
    return re.sub(r"<\?xml[^>]*\?>\s*", "", d.GetDrawingText()).strip()


def build():
    stanzas, missing = [], []
    for s in STAGES:
        slides, lines = [], []
        for k, m in enumerate(s["mols"]):
            svg = mol_svg(smiles_for(m))
            if not svg:
                missing.append(m["ca"])
            slides.append(f'<div class="slide" data-k="{k}">{svg or "<div class=nostruct>—</div>"}</div>')
            lines.append(f'<div class="line" data-k="{k}">'
                         f'<span class="name">{html.escape(m["ca"])}</span>'
                         f'<span class="gloss">{html.escape(m["g"])}</span></div>')
        stanzas.append(f"""
      <section class="stanza">
        <p class="stage">{html.escape(s['stage'])}</p>
        <div class="split">
          <div class="viewer">{''.join(slides)}</div>
          <div class="verses">{''.join(lines)}</div>
        </div>
      </section>""")

    if missing:
        print("SENSE ESTRUCTURA:", missing)
    font_css = open(FONT_CSS, encoding="utf-8").read()
    page = _TEMPLATE.replace("{{FONT}}", font_css).replace("{{STANZAS}}", "".join(stanzas))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(page)
    return OUT


_TEMPLATE = r"""<title>Noms de molècules</title>
<style>
{{FONT}}
  :root{
    --ground:#f0ebe6; --ink:#282828; --muted:#8f887d; --line:#ddd6cb; --hair:#e7e1d7;
    --gloss:#5c5648; --accent:#2f7d68; --red:#c7513b;
    --mono:"Space Mono", ui-monospace, Menlo, monospace;
  }
  *{ scrollbar-width:none; -ms-overflow-style:none; box-sizing:border-box; }
  *::-webkit-scrollbar{ display:none; width:0; height:0; }
  html{ scroll-behavior:smooth; }
  html, body{ margin:0; padding:0; background:var(--ground); overflow-x:hidden; }
  body{ color:var(--ink); font-family:var(--mono); font-size:14px; line-height:1.65;
        -webkit-font-smoothing:antialiased; }

  .page{ max-width:900px; margin:0 auto; padding:clamp(48px,9vw,110px) clamp(24px,6vw,64px); }

  .mast{ margin:0 0 clamp(44px,8vw,88px); }
  .mast h1{ font-weight:400; font-size:clamp(26px,4vw,40px); letter-spacing:-.02em; margin:0;
            line-height:1.05; }
  .mast p{ color:var(--muted); font-size:12px; letter-spacing:.02em; margin:14px 0 0; max-width:52ch;
           line-height:1.7; }

  .stanza{ padding:clamp(30px,5vw,52px) 0; }
  .stanza + .stanza{ border-top:1px solid var(--line); }
  .stage{ font-size:11px; letter-spacing:.26em; text-transform:uppercase; color:var(--muted);
          opacity:.6; margin:0 0 clamp(16px,2.4vw,24px); }

  .split{ display:grid; grid-template-columns:clamp(210px,26vw,280px) minmax(0,1fr);
          gap:clamp(28px,4.5vw,64px); align-items:center; }
  @media (max-width:720px){ .split{ grid-template-columns:1fr; gap:22px; } }

  .viewer{ position:relative; width:100%; aspect-ratio:1; }
  .slide{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
          opacity:0; transition:opacity .7s ease; }
  .slide.on{ opacity:1; }
  .slide svg{ width:100%; height:100%; overflow:visible; }
  .nostruct{ color:var(--muted); }

  .verses{ display:grid; grid-template-columns:minmax(0,max-content) 1fr;
           column-gap:clamp(18px,3vw,34px); align-items:baseline; }
  .line{ display:contents; }
  .name{ font-size:clamp(16px,2vw,20px); letter-spacing:-.01em; color:var(--ink);
         white-space:nowrap; padding:6px 0; transition:color .4s ease; cursor:default; }
  .gloss{ font-size:12.5px; line-height:1.5; color:var(--gloss); padding:6px 0; }
  .line.on .name{ color:var(--accent); }
  @media (max-width:720px){ .name{ white-space:normal; } }

  .method{ margin-top:clamp(30px,5vw,52px); border-top:1px solid var(--line); padding-top:30px; }
  .seclab{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:0 0 12px; }
  .prose{ font-size:13px; line-height:1.85; margin:0 0 14px; color:var(--ink); max-width:64ch; }
  .prose b{ font-weight:400; } .prose i{ color:var(--muted); font-style:normal; }

  @media (prefers-reduced-motion: reduce){ html{ scroll-behavior:auto; } .slide{ transition:none; } }
</style>

<div class="page">
  <header class="mast">
    <h1>Noms de molècules</h1>
    <p>Una vida en vuit edats, dita amb noms de molècules. Cada vers, un hexasíl·lab;
      cada estrofa, la seva rima. El plafó va passant les molècules de cada edat.</p>
  </header>

  {{STANZAS}}

  <section class="method">
    <p class="seclab">Nota</p>
    <p class="prose">Cada vers és el nom d'una molècula real, en català, i un
      <b>hexasíl·lab</b> (sis síl·labes fins a l'última tònica). Cada estrofa —del fetus
      a la mort— <b>rima</b> amb un sufix diferent. A la mort l'hexasíl·lab es trenca a
      posta: el vers es torna pedra, mineral, curt.</p>
    <p class="prose">Estructures dibuixades amb RDKit; els minerals surten esquemàtics.
      Recompte de síl·labes amb el motor de Softcatalà. <i>Poemes computacionals.</i></p>
  </section>
</div>

<script>
  (function(){
    var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    var stanzas = [].slice.call(document.querySelectorAll('.stanza'));
    stanzas.forEach(function(st, si){
      var slides = [].slice.call(st.querySelectorAll('.slide'));
      var lines = [].slice.call(st.querySelectorAll('.line'));
      if(!slides.length) return;
      var k = 0;
      function paint(){
        slides.forEach(function(s, j){ s.classList.toggle('on', j === k); });
        lines.forEach(function(l, j){ l.classList.toggle('on', j === k); });
      }
      paint();
      if(!reduce){
        // stagger stanzas so they don't all flip in unison
        setTimeout(function(){
          setInterval(function(){ k = (k + 1) % slides.length; paint(); }, 2600);
        }, si * 650);
      }
    });
  })();
</script>
"""


if __name__ == "__main__":
    print(build())
