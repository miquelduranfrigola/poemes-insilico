"""Assemble the self-contained "Versos proteics" gallery (HTML).

Art-museum treatment: a quiet left index and a spacious content pane showing one
piece at a time. The landing entry explains the rubric; each poem entry loops
through its words — as each word lights up red, the residues it produced light up
red both in the protein sequence (otherwise grey) and in the 3D structure (grey
cartoon), synchronised. Structures are live 3Dmol.js viewers (inlined), so residues
can be recoloured on the fly; they auto-spin.

Space Mono throughout, on a cream ground. Merges results/globularity.csv +
data/poems/_meta.json + the folded PDBs (from cache) + inlined 3Dmol.js + the inlined
Space Mono webfont. The rubric table is read live from main.py. Writes
index.html (poem-folder root; everything inlined; no external requests).
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

POEM_ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from folding import DEFAULT_CACHE, _seq_hash  # noqa: E402
from main import ESCAPE, PAIRS, SINGLES  # noqa: E402
from pipeline import poem_chunks, to_sequence  # noqa: E402

POEMS_DIR = POEM_ROOT / "data" / "poems"

# Amino-acid one-letter code -> Catalan name.
AA_CA = {
    "A": "alanina", "R": "arginina", "N": "asparagina", "D": "aspartat",
    "C": "cisteïna", "E": "glutamat", "Q": "glutamina", "G": "glicina",
    "H": "histidina", "I": "isoleucina", "L": "leucina", "K": "lisina",
    "M": "metionina", "F": "fenilalanina", "P": "prolina", "S": "serina",
    "T": "treonina", "W": "triptòfan", "Y": "tirosina", "V": "valina",
}


def _load():
    with (POEM_ROOT / "results" / "globularity.csv").open(encoding="utf-8") as fh:
        glob = {r["poem"]: r for r in csv.DictReader(fh)}
    meta_raw = json.loads((POEMS_DIR / "_meta.json").read_text("utf-8"))
    meta = {name: (title, author) for name, title, author in meta_raw}
    return glob, meta


def _pdb_text(seq: str) -> str:
    """Backbone-only PDB (N, CA, C, O) — all 3Dmol needs for a cartoon, ~half the size."""
    raw = (DEFAULT_CACHE / f"{_seq_hash(seq.strip().upper())}.pdb").read_text(encoding="utf-8")
    keep = []
    for line in raw.splitlines():
        if line.startswith("ATOM"):
            if line[12:16].strip() in ("N", "CA", "C", "O"):
                keep.append(line)
        elif line.startswith(("TER", "END")):
            keep.append(line)
    return "\n".join(keep) + "\n"


def _poem_payload(text: str):
    """Return (data, verses_html, sequence_html).

    data = {"pdbs": [...per domain...], "words": [{dom,a,b}...]} where a..b are
    1-based residue numbers within that domain (0 if the word yields no residues).
    Word spans in the verses and residue spans in the sequence share `data-w`.
    """
    chunks = poem_chunks(text)
    cum = [0]
    for c in chunks:
        cum.append(cum[-1] + len(c))
    tot = cum[-1] or 1
    pdbs = [_pdb_text(c) for c in chunks]

    words, verses, seqspans = [], [], []
    wi, g = 0, 0
    for line in text.splitlines():
        if not line.strip():
            if verses and not verses[-1].startswith('<span class="br"'):
                verses.append('<span class="br"></span>')  # stanza break
            continue
        toks = line.split()
        parts = []
        for ti, tok in enumerate(toks):
            res = to_sequence(tok)
            L = len(res)
            a, b = g, g + L
            g = b
            eol = 1 if ti == len(toks) - 1 else 0
            if L > 0:
                d = 0
                while d + 1 < len(cum) and a >= cum[d + 1]:
                    d += 1
                words.append({"dom": d, "a": a - cum[d] + 1, "b": b - cum[d], "n": L, "eol": eol})
                hue = round(240 * ((a + b) / 2) / tot)  # N-term red -> C-term blue
                style = f' style="--c:hsl({hue},62%,48%)"'
            else:
                words.append({"dom": -1, "a": 0, "b": 0, "n": 0, "eol": eol})
                style = ""
            parts.append(f'<span class="wd" data-w="{wi}">{html.escape(tok)}</span>')
            seqspans.append(f'<span class="res" data-w="{wi}"{style}>{html.escape(res)}</span>')
            wi += 1
        verses.append('<span class="v">' + " ".join(parts) + "</span>")

    return ({"pdbs": pdbs, "words": words, "off": cum[:-1], "tot": tot},
            "\n".join(verses), "".join(seqspans))


def _viewers_html(n: int) -> str:
    return "".join(f'<div class="viewer" data-dom="{i}"></div>' for i in range(n))


def _entry(stem, glob, meta, data_out) -> str:
    title, author = meta.get(stem, (stem, ""))
    text = (POEMS_DIR / f"{stem}.txt").read_text("utf-8")
    payload, verses_html, seq_html = _poem_payload(text)
    data_out[f"poem-{stem}"] = payload
    return f"""
    <section class="entry" id="poem-{stem}" hidden>
      <p class="kicker">{html.escape(author)}</p>
      <h2 class="title">{html.escape(title)}</h2>
      <div class="split">
        <div class="structures">{_viewers_html(len(payload["pdbs"]))}</div>
        <div class="poem">{verses_html}</div>
      </div>
      <div class="seqfull"><div class="seq">{seq_html}</div></div>
    </section>"""


def _rubric_section() -> str:
    directs = "".join(
        f'<span class="map"><b>{html.escape(k)}</b> → {v} <i>{AA_CA[v]}</i></span>'
        for k, v in SINGLES.items())
    escapes = "".join(f'<span class="map"><b>{html.escape(k)}</b> → {v}</span>'
                      for k, v in PAIRS.items())
    return f"""
    <section class="entry" id="rubric">
      <h1 class="title">Metodologia</h1>
      <p class="prose">Cada lletra que ja és un codi d'aminoàcid es mapa a si mateixa;
        la resta s'escapa amb <b>{ESCAPE}</b> seguida d'un aminoàcid.</p>

      <p class="seclab">Correspondència directa</p>
      <div class="maps">{directs}</div>

      <p class="seclab">Escapaments amb {ESCAPE} ({AA_CA[ESCAPE]})</p>
      <div class="maps">{escapes}</div>
    </section>"""


def build() -> Path:
    glob, meta = _load()
    font_css = (POEM_ROOT.parent.parent / "shared" / "vendor" / "spacemono.css").read_text(encoding="utf-8")
    lib_js = (HERE / "vendor" / "3Dmol-min.js").read_text(encoding="utf-8")

    poems = [s for s in glob if (POEMS_DIR / f"{s}.txt").exists()]
    catalog = sorted(poems, key=lambda k: float(glob[k]["score"]), reverse=True)

    def title_of(stem):
        return meta.get(stem, (stem, ""))[0]

    menu = []
    for s in catalog:
        menu.append(f'<li><a data-target="poem-{s}" href="#poem-{s}">{html.escape(title_of(s))}</a></li>')
    menu.append('<li class="meto"><a data-target="rubric" href="#rubric">Metodologia</a></li>')
    default = f"poem-{catalog[0]}" if catalog else "rubric"

    data_out: dict = {}
    entries = _rubric_section() + "".join(_entry(s, glob, meta, data_out) for s in catalog)

    page = (_TEMPLATE
            .replace("{{FONT}}", font_css)
            .replace("{{DEFAULT}}", default)
            .replace("{{MENU}}", "\n".join(menu))
            .replace("{{ENTRIES}}", entries)
            .replace("{{LIB}}", lib_js)
            .replace("{{DATA}}", json.dumps(data_out, ensure_ascii=False)))
    out = POEM_ROOT / "index.html"
    nav = (POEM_ROOT.parent.parent / "shared" / "vendor" / "menu-nav.html").read_text(encoding="utf-8")
    out.write_text(page + nav, encoding="utf-8")
    return out


_TEMPLATE = r"""<title>Versos proteics</title>
<style>
{{FONT}}
  :root{
    --ground:#f0ebe6; --ink:#282828; --muted:#8f887d; --line:#ddd6cb; --hair:#e7e1d7;
    --accent:#2f7d68; --red:#c7513b;
    --mono:"Space Mono", ui-monospace, Menlo, monospace;
  }
  *{ scrollbar-width:none; -ms-overflow-style:none; }
  *::-webkit-scrollbar{ display:none; width:0; height:0; }
  /* overflow-x on <html> only: on <body> it makes <body> a scroll container and breaks the sticky rail */
  html{ scroll-behavior:smooth; overflow-x:hidden; }
  html, body{ margin:0; padding:0; background:var(--ground); }
  .wrap{ background:var(--ground); color:var(--ink); font-family:var(--mono);
         font-size:14px; line-height:1.65; min-height:100vh; -webkit-font-smoothing:antialiased; }
  .wrap *{ box-sizing:border-box; }
  .wrap a{ color:var(--ink); text-decoration:none; transition:opacity .15s ease; }
  .wrap a:hover{ opacity:.55; }

  .site{ display:flex; align-items:flex-start; min-height:100vh; }

  .index{ width:220px; flex:none; position:sticky; top:0; align-self:flex-start;
          height:100vh; overflow:auto; padding:30px 22px; border-right:1px solid var(--line); }
  .brand{ margin-bottom:26px; line-height:1.35; min-height:58px; }
  .brand b{ font-weight:700; font-size:14px; display:block; letter-spacing:-.01em; }
  .brand span{ display:block; color:var(--muted); font-size:11px; margin-top:4px; text-transform:uppercase; letter-spacing:.08em; }
  .menu{ list-style:none; margin:0; padding:0; font-size:14px; }
  .menu li a{ display:block; padding:3px 0; }
  .menu li a.on{ text-decoration:underline; text-underline-offset:3px; }
  .menu li.meto{ margin-top:18px; padding-top:14px; border-top:1px solid var(--hair); }
  .menu li.meto a{ color:var(--ink); font-size:14px; }

  .view{ flex:1; min-width:0; }
  .entry{ max-width:1000px; margin:0 auto; padding:114px clamp(22px,6vw,80px) clamp(40px,7vw,104px); }

  .kicker{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:0 0 14px; }
  .title{ font-weight:400; font-size:clamp(24px,3.4vw,32px); line-height:1.1; letter-spacing:-.02em;
          margin:0; text-wrap:balance; }
  .dims{ font-size:11px; letter-spacing:.18em; text-transform:uppercase; color:var(--muted); margin:16px 0 0; }

  .structures{ display:flex; flex-direction:column; gap:clamp(14px,3vw,22px); align-items:center; }
  .viewer{ position:relative; width:100%; max-width:280px; aspect-ratio:1; pointer-events:none; }
  .viewer canvas{ border-radius:2px; pointer-events:none; }

  /* structures (left, stacked) · poem (right, sized to its longest verse so no line is cut) */
  .split{ display:grid; grid-template-columns:280px max-content; gap:clamp(24px,4vw,56px);
          align-items:start; margin:clamp(30px,5vw,56px) 0 0; }
  @media (max-width:760px){ .split{ grid-template-columns:1fr; } }

  .poem{ font-size:14px; line-height:1.95; overflow-x:auto; }
  .poem .v{ display:block; white-space:nowrap; }
  .poem .br{ display:block; height:.9em; }
  .wd{ color:rgba(40,40,40,.22); transition:color .25s ease; }   /* grows: faint -> ink */
  .wd.on{ color:var(--ink); }

  /* sequence spans the full width beneath both columns; fills in the same rainbow */
  .seqfull{ margin-top:clamp(28px,5vw,48px); border-top:1px solid var(--line); padding-top:22px; }
  .seq{ font-size:11px; line-height:2.0; word-break:break-all; }
  .res{ color:rgba(40,40,40,.16); transition:color .25s ease; }
  .res.on{ color:var(--c); }

  .prose{ max-width:60ch; margin:0 0 6px; }
  .seclab{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:38px 0 14px; }
  .maps{ display:grid; grid-template-columns:repeat(auto-fill,minmax(158px,1fr)); gap:9px 20px; max-width:720px; }
  .map{ color:var(--ink); } .map b{ color:var(--ink); font-weight:400; }
  .map i{ color:var(--muted); font-style:normal; }

  .entry[hidden]{ display:none; }
  .entry{ animation:appear .3s ease both; }
  @keyframes appear{ from{ opacity:0; transform:translateY(8px); } to{ opacity:1; transform:none; } }

  @media (max-width:900px){
    .site{ display:block; }
    .index{ width:auto; position:static; height:auto; overflow:visible; padding:20px 22px;
            border-right:0; border-bottom:1px solid var(--line);
            display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 18px; }
    .brand{ margin:0 14px 0 0; min-height:auto; }
    .menu{ display:flex; flex-wrap:wrap; gap:4px 16px; }
    .menu li.grp{ margin:0; width:100%; }
    .cx{ display:none; }
    .structures{ position:static; }
  }
  @media (prefers-reduced-motion: reduce){ html{ scroll-behavior:auto; } .entry{ animation:none; } }
</style>

<div class="wrap"><div class="site">
  <nav class="index">
    <div class="brand"><a data-target="{{DEFAULT}}" href="#{{DEFAULT}}"><b>Versos proteics</b></a>
      <span>Alfabet d'aminoàcids</span></div>
    <ol class="menu">{{MENU}}</ol>
  </nav>
  <main class="view">
    {{ENTRIES}}
  </main>
</div></div>

<script>{{LIB}}</script>
<script>
  var DATA = {{DATA}};
  var DEFAULT_ID = "{{DEFAULT}}";
  (function(){
    var links = [].slice.call(document.querySelectorAll('[data-target]'));
    var entries = [].slice.call(document.querySelectorAll('.entry'));
    var active = null;

    function teardown(){
      if(!active) return;
      if(active.st){ active.st.stop = true; clearTimeout(active.st.timer); }
      (active.viewers || []).forEach(function(v){ try{ v.spin(false); v.clear(); }catch(e){} });
      var el = document.getElementById(active.id);
      if(el){
        el.querySelectorAll('.viewer canvas').forEach(function(c){ c.remove(); });
        el.querySelectorAll('.on').forEach(function(h){ h.classList.remove('on'); });
      }
      active = null;
    }

    var GREY = 0xbdb8ae, RED = 0xc7513b;

    function initEntry(id){
      var el = document.getElementById(id), d = DATA[id];
      if(!el || !d || !window.$3Dmol) return;
      var conts = [].slice.call(el.querySelectorAll('.viewer'));
      var viewers = [];
      d.pdbs.forEach(function(pdb, idx){
        var c = conts[idx]; if(!c) return;
        var v = $3Dmol.createViewer(c, {backgroundColor:0xf0ebe6});
        v.setBackgroundColor(0xf0ebe6, 0);
        v.addModel(pdb, 'pdb');
        v.setStyle({}, {cartoon:{color:GREY}});
        v.zoomTo(); v.render(); v.resize(); v.render();
        v.spin('y', 0.5);
        viewers.push(v);
      });

      var wd = [], res = [];
      el.querySelectorAll('.wd').forEach(function(s){ wd[+s.dataset.w] = s; });
      el.querySelectorAll('.res').forEach(function(s){ res[+s.dataset.w] = s; });
      var words = d.words, off = d.off, tot = d.tot, i = 0, fDom = -1, fB = 0;

      function grad(idx){  // fixed rainbow along the whole protein (N->C), per domain
        return {cartoon:{colorscheme:{prop:'resi', gradient:'roygb',
                min:1 - off[idx], max:tot - off[idx]}}};
      }
      function paint(){  // reveal the rainbow cumulatively from the N-terminus
        viewers.forEach(function(v, idx){
          if(idx < fDom){
            v.setStyle({}, grad(idx));
          } else if(idx === fDom && fB > 0){
            v.setStyle({}, {cartoon:{color:GREY}});
            var arr = []; for(var r = 1; r <= fB; r++) arr.push(r);
            v.setStyle({resi:arr}, grad(idx));
          } else {
            v.setStyle({}, {cartoon:{color:GREY}});
          }
          v.render();
        });
      }
      var st = {stop:false, timer:null};
      function step(){
        if(st.stop) return;
        if(i === 0){  // restart the fill
          el.querySelectorAll('.on').forEach(function(x){ x.classList.remove('on'); });
          fDom = -1; fB = 0; paint();
        }
        var w = words[i];
        if(wd[i]) wd[i].classList.add('on');
        if(res[i]) res[i].classList.add('on');
        if(w && w.a > 0){ fDom = w.dom; fB = w.b; paint(); }
        var dur = 250 + 28 * (w ? w.n : 0) + ((w && w.eol) ? 300 : 0);  // reading pace
        i = (i + 1) % words.length;
        st.timer = setTimeout(step, dur);
      }
      active = {id:id, viewers:viewers, st:st};
      step();
    }

    function show(id){
      var found = false;
      entries.forEach(function(e){ var on = e.id === id; e.hidden = !on; if(on) found = true; });
      if(!found){ id = 'rubric'; document.getElementById('rubric').hidden = false; }
      links.forEach(function(a){ a.classList.toggle('on', a.dataset.target === id); });
      teardown();
      window.scrollTo({top:0, behavior:'auto'});
      if(DATA[id]) requestAnimationFrame(function(){ initEntry(id); });
    }

    links.forEach(function(a){
      a.addEventListener('click', function(ev){
        ev.preventDefault();
        history.replaceState(null, '', '#' + a.dataset.target);
        show(a.dataset.target);
      });
    });
    window.addEventListener('resize', function(){
      if(active){ active.viewers.forEach(function(v){ try{ v.resize(); v.render(); }catch(e){} }); }
    });
    show(location.hash ? location.hash.slice(1) : DEFAULT_ID);
  })();
</script>
"""


if __name__ == "__main__":
    print(build())
