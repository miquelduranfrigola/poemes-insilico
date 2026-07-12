"""Assemble the self-contained "Veinte poemas de amor" gallery (HTML).

Art-museum treatment in the house style of *poemes proteics*: a quiet sticky left
index and a spacious content pane showing one piece at a time. Space Mono on a
cream ground, everything inlined (no external requests).

Each poem entry shows Neruda's original beside its despoetized residue. Activating
an entry runs the despoetization "engine": a sweep through the 104-language chain
(es -> et -> eu -> ... -> es) — the current language ticks by, a track fills, the
original slowly dims, and when the round-trip closes the despoetized text is
revealed. Then it loops. A closing "Metodologia" entry prints the full chain.

Reads: data/_meta.json, data/originals/*.txt, data/despoetized/*.txt, the language
chain from code/languages.py, and the inlined Space Mono webfont. Writes
results/despoetitzacio.html.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

POEM_ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from languages import NAMES, chain  # noqa: E402

DATA = POEM_ROOT / "data"


def _verses_html(text: str) -> str:
    """Render a poem body: one span per verse, blank lines become stanza breaks."""
    out = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.strip() == "":
            if out and not out[-1].startswith('<span class="br"'):
                out.append('<span class="br"></span>')
            continue
        out.append(f'<span class="v">{html.escape(line.rstrip())}</span>')
    while out and out[-1].startswith('<span class="br"'):
        out.pop()
    return "\n".join(out)


def _read(kind: str, pid: str) -> str:
    return (DATA / kind / f"{pid}.txt").read_text(encoding="utf-8")


def _entry(m: dict, default: bool) -> str:
    pid, title, incipit = m["id"], m["title"], m["incipit"]
    original = _verses_html(_read("originals", pid))
    despo = _verses_html(_read("despoetized", pid))
    hidden = "" if default else " hidden"
    return f"""
    <section class="entry poem-entry" id="p-{pid}"{hidden}>
      <p class="kicker">Pablo Neruda · Veinte poemas de amor</p>
      <h2 class="title">{html.escape(title)}</h2>
      <p class="incipit">«{html.escape(incipit)}»</p>

      <div class="split">
        <div class="col">
          <p class="collab">Original</p>
          <div class="poem original">{original}</div>
        </div>
        <div class="col">
          <p class="collab">Despoetitzat · 104 llengües</p>
          <div class="poem despo veiled">{despo}</div>
        </div>
      </div>

      <div class="engine">
        <div class="engbar">
          <span class="readout">[es] Spanish</span>
          <span class="counter">0 / 104</span>
        </div>
        <div class="track"></div>
      </div>
    </section>"""


def _method_entry() -> str:
    seq = chain()
    maps = "".join(
        f'<span class="map"><b>[{html.escape(c)}]</b> {html.escape(NAMES[c])}</span>'
        for c in seq)
    return f"""
    <section class="entry" id="metodologia" hidden>
      <p class="kicker">Mètode</p>
      <h1 class="title">Despoetització</h1>
      <p class="epigraph">«Poetry is what gets lost in translation.» — Robert Frost</p>

      <p class="prose">Cada poema d'amor de Neruda ha travessat 104 traduccions
        automàtiques encadenades amb el traductor de Google: del castellà a
        l'estonià, de l'estonià al basc… tota la volta de l'abecedari de llengües
        i, finalment, de tornada al castellà. A cada salt el poema perd una mica
        més; el que en torna és el residu <i>despoetitzat</i> —el sediment de sentit
        que sobreviu al viatge.</p>
      <p class="prose">Es mostra el resultat sense cap modificació, més enllà de
        petites correccions gramaticals. Els resultats són els de la tirada
        original de 2016; una nova tirada donaria un residu diferent, perquè el
        traductor no para de canviar.</p>

      <p class="seclab">La cadena · es → … → es</p>
      <div class="maps">{maps}</div>

      <p class="prose src">Els <i>Veinte poemas de amor</i> originals de Pablo Neruda:
        arxiu (PDF).</p>
    </section>"""


def build() -> Path:
    font_css = (HERE.parents[2] / "shared" / "vendor" / "spacemono.css").read_text(encoding="utf-8")
    meta = json.loads((DATA / "_meta.json").read_text(encoding="utf-8"))

    default_id = f"p-{meta[0]['id']}" if meta else "metodologia"

    menu = [f'<li><a data-target="p-{m["id"]}" href="#p-{m["id"]}">'
            f'{html.escape(m["title"])}</a></li>' for m in meta]
    menu.append('<li class="foot"><a data-target="metodologia" '
                'href="#metodologia">Metodologia</a></li>')

    entries = "".join(_entry(m, i == 0) for i, m in enumerate(meta)) + _method_entry()

    chain_json = json.dumps([[c, NAMES[c]] for c in chain()], ensure_ascii=False)

    page = (_TEMPLATE
            .replace("{{FONT}}", font_css)
            .replace("{{DEFAULT}}", default_id)
            .replace("{{MENU}}", "\n".join(menu))
            .replace("{{ENTRIES}}", entries)
            .replace("{{CHAIN}}", chain_json))
    out = POEM_ROOT / "results" / "index.html"
    out.write_text(page, encoding="utf-8")
    return out


_TEMPLATE = r"""<title>Veinte poemas de amor</title>
<style>
{{FONT}}
  :root{
    --ground:#f0ebe6; --ink:#282828; --muted:#8f887d; --line:#ddd6cb; --hair:#e7e1d7;
    --accent:#2f7d68; --red:#c7513b;
    --mono:"Space Mono", ui-monospace, Menlo, monospace;
  }
  *{ scrollbar-width:none; -ms-overflow-style:none; }
  *::-webkit-scrollbar{ display:none; width:0; height:0; }
  html{ scroll-behavior:smooth; }
  html, body{ margin:0; padding:0; background:var(--ground); overflow-x:hidden; }
  .wrap{ background:var(--ground); color:var(--ink); font-family:var(--mono);
         font-size:14px; line-height:1.65; min-height:100vh; -webkit-font-smoothing:antialiased; }
  .wrap *{ box-sizing:border-box; }
  .wrap a{ color:var(--ink); text-decoration:none; transition:opacity .15s ease; }
  .wrap a:hover{ opacity:.55; }

  .site{ display:flex; align-items:flex-start; min-height:100vh; }

  .index{ width:clamp(210px,20vw,260px); flex:none; position:sticky; top:0; align-self:flex-start;
          height:100vh; overflow:auto; padding:34px 24px; border-right:1px solid var(--line); }
  .brand{ margin-bottom:26px; line-height:1.35; }
  .brand b{ font-weight:400; font-size:14px; display:block; letter-spacing:-.01em; }
  .brand span{ color:var(--muted); font-size:11px; }
  .menu{ list-style:none; margin:0; padding:0; font-size:14px; }
  .menu li a{ display:block; padding:3px 0; }
  .menu li a.on{ text-decoration:underline; text-underline-offset:3px; }
  .menu li.foot{ margin-top:26px; padding-top:12px; border-top:1px solid var(--hair); }
  .menu li.foot a{ color:var(--muted); font-size:11px; }

  .view{ flex:1; min-width:0; }
  .entry{ max-width:1000px; margin:0 auto; padding:clamp(40px,7vw,104px) clamp(22px,6vw,80px); }

  .kicker{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:0 0 14px; }
  .title{ font-weight:400; font-size:clamp(24px,3.4vw,32px); line-height:1.1; letter-spacing:-.02em;
          margin:0; text-wrap:balance; }
  .incipit{ color:var(--muted); font-style:italic; margin:14px 0 0; max-width:60ch; }

  /* original (left) · despoetized (right) */
  .split{ display:grid; grid-template-columns:1fr 1fr; gap:clamp(24px,4vw,56px);
          align-items:start; margin:clamp(30px,5vw,52px) 0 0; }
  @media (max-width:760px){ .split{ grid-template-columns:1fr; } }
  .collab{ font-size:11px; letter-spacing:.2em; text-transform:uppercase; color:var(--muted);
           margin:0 0 16px; padding-bottom:8px; border-bottom:1px solid var(--hair); }

  .poem{ font-size:14px; line-height:1.95; }
  .poem .v{ display:block; }
  .poem .br{ display:block; height:.9em; }
  .original{ transition:opacity .4s ease; }
  .despo{ color:var(--ink); }
  /* the residue is veiled until the round-trip closes */
  .despo.veiled{ opacity:0; filter:blur(6px); transform:translateY(6px); }
  .despo{ transition:opacity .7s ease, filter .7s ease, transform .7s ease; }

  /* the despoetization engine */
  .engine{ margin-top:clamp(30px,5vw,52px); border-top:1px solid var(--line); padding-top:20px; }
  .engbar{ display:flex; align-items:baseline; justify-content:space-between; gap:16px; }
  .readout{ font-size:13px; letter-spacing:.02em; }
  .readout b{ font-weight:400; color:var(--red); }
  .counter{ font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }
  .track{ display:flex; gap:2px; margin-top:12px; height:14px; align-items:stretch; }
  .track i{ flex:1 1 0; background:rgba(40,40,40,.10); transition:background .12s ease; }
  .track i.done{ background:rgba(40,40,40,.42); }
  .track i.now{ background:var(--red); }

  /* method */
  .epigraph{ color:var(--ink); font-style:italic; margin:18px 0 0; max-width:60ch; }
  .prose{ max-width:62ch; margin:20px 0 0; }
  .prose.src{ color:var(--muted); font-size:12px; }
  .prose i{ color:var(--muted); font-style:italic; }
  .seclab{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:40px 0 16px; }
  .maps{ display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:8px 20px; max-width:820px; }
  .map{ color:var(--muted); } .map b{ color:var(--ink); font-weight:400; }

  .entry[hidden]{ display:none; }
  .entry{ animation:appear .3s ease both; }
  @keyframes appear{ from{ opacity:0; transform:translateY(8px); } to{ opacity:1; transform:none; } }

  @media (max-width:900px){
    .site{ display:block; }
    .index{ width:auto; position:static; height:auto; overflow:visible; padding:20px 22px;
            border-right:0; border-bottom:1px solid var(--line);
            display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 18px; }
    .brand{ margin:0 14px 0 0; }
    .menu{ display:flex; flex-wrap:wrap; gap:4px 16px; }
  }
  @media (prefers-reduced-motion: reduce){
    html{ scroll-behavior:auto; } .entry{ animation:none; }
    .original,.despo{ transition:none; }
  }
</style>

<div class="wrap"><div class="site">
  <nav class="index">
    <div class="brand"><a data-target="{{DEFAULT}}" href="#{{DEFAULT}}">
      <b>Veinte poemas de amor</b><span>Pablo Neruda · despoetitzats</span></a></div>
    <ol class="menu">{{MENU}}</ol>
  </nav>
  <main class="view">
    {{ENTRIES}}
  </main>
</div></div>

<script>
  var CHAIN = {{CHAIN}};           // [[code, name], ...] es ... es
  var DEFAULT_ID = "{{DEFAULT}}";
  (function(){
    var links = [].slice.call(document.querySelectorAll('[data-target]'));
    var entries = [].slice.call(document.querySelectorAll('.entry'));
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var active = null;  // {id, timer}

    function teardown(){
      if(!active) return;
      clearTimeout(active.timer);
      active = null;
    }

    function runEngine(el){
      var readout = el.querySelector('.readout');
      var counter = el.querySelector('.counter');
      var track = el.querySelector('.track');
      var original = el.querySelector('.original');
      var despo = el.querySelector('.despo');
      var steps = CHAIN.length - 1;       // 104

      // Build the track once.
      if(track && !track.children.length){
        for(var k=0;k<steps;k++){ track.appendChild(document.createElement('i')); }
      }
      var bars = track ? [].slice.call(track.children) : [];

      var state = {timer:null};
      active = state;

      function reset(){
        if(despo){ despo.classList.add('veiled'); }
        if(original){ original.style.opacity = '1'; }
        bars.forEach(function(b){ b.className=''; });
        if(readout){ readout.innerHTML = '[es] Spanish'; }
        if(counter){ counter.textContent = '0 / ' + steps; }
      }

      if(reduce){                          // no sweep: just show the residue
        reset();
        if(despo) despo.classList.remove('veiled');
        if(original) original.style.opacity = '0.55';
        return;
      }

      function sweep(i){
        if(active !== state) return;
        if(i >= steps){                    // round-trip closed
          if(despo) despo.classList.remove('veiled');
          if(readout) readout.innerHTML = '[es] Spanish · <b>fet</b>';
          if(counter) counter.textContent = steps + ' / ' + steps;
          state.timer = setTimeout(function(){ i = 0; cycle(); }, 3800);
          return;
        }
        var tgt = CHAIN[i+1];              // language we translate INTO
        if(bars[i-1]) bars[i-1].className = 'done';
        if(bars[i]) bars[i].className = 'now';
        if(readout) readout.innerHTML = '[' + tgt[0] + '] ' + tgt[1];
        if(counter) counter.textContent = (i+1) + ' / ' + steps;
        if(original) original.style.opacity = (1 - 0.5 * (i+1)/steps).toFixed(3);
        state.timer = setTimeout(function(){ sweep(i+1); }, 46);
      }
      function cycle(){ reset(); state.timer = setTimeout(function(){ sweep(0); }, 700); }
      cycle();
    }

    function show(id){
      var found = false;
      entries.forEach(function(e){ var on = e.id === id; e.hidden = !on; if(on) found = true; });
      if(!found){ id = DEFAULT_ID; var d = document.getElementById(id); if(d) d.hidden = false; }
      links.forEach(function(a){ a.classList.toggle('on', a.dataset.target === id); });
      teardown();
      window.scrollTo({top:0, behavior:'auto'});
      var el = document.getElementById(id);
      if(el && el.classList.contains('poem-entry')){
        requestAnimationFrame(function(){ runEngine(el); });
      }
    }

    links.forEach(function(a){
      a.addEventListener('click', function(ev){
        ev.preventDefault();
        history.replaceState(null, '', '#' + a.dataset.target);
        show(a.dataset.target);
      });
    });
    show(location.hash ? location.hash.slice(1) : DEFAULT_ID);
  })();
</script>
"""


if __name__ == "__main__":
    print(build())
