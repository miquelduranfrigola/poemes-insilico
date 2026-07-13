"""Assemble the self-contained "El que es perd en la traducció" gallery (HTML).

Art-museum treatment in the house style of *poemes proteics*: a quiet sticky left
column beside the content. The site has two distinct sections the reader switches
between (never scrolls between) — "Poemes" (the pieces flowing one after another)
and "Metodologia". Space Mono on a cream ground, everything inlined (no external
requests).

Each poem entry is just its title, the despoetized residue, and a fold-away toggle
for Neruda's original — no per-poem widgets. The concept is illustrated once, in the
closing "Metodologia" entry: the full 104-language grid animates a sweep through the
chain (es -> et -> eu -> ... -> es), each language lighting up as the poem crosses it
and fading once passed, looping while the section is on screen.

Reads: data/_meta.json, data/originals/*.txt, data/despoetized/*.txt, the language
chain from code/languages.py, and the inlined Space Mono webfont. Writes
index.html (poem-folder root).
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


def _entry(m: dict) -> str:
    pid, title = m["id"], m["title"]
    original = _verses_html(_read("originals", pid))
    despo = _verses_html(_read("despoetized", pid))
    return f"""
    <section class="entry poem-entry" id="p-{pid}">
      <h2 class="title">{html.escape(title)}</h2>
      <div class="poem despo">{despo}</div>

      <details class="orig">
        <summary>Original</summary>
        <div class="poem original">{original}</div>
      </details>
    </section>"""


def _lede() -> str:
    """The collection title at the head of the content column."""
    return """
    <header class="entry lede">
      <p class="kicker">Pablo Neruda · despoetitzat</p>
      <h1 class="title">Veinte poemas de amor y una canción desesperada</h1>
      <p class="epigraph">«Poetry is what gets lost in translation.» — Robert Frost</p>
    </header>"""


def _method_entry() -> str:
    seq = chain()
    maps = "".join(
        f'<span class="map"><b>[{html.escape(c)}]</b> {html.escape(NAMES[c])}</span>'
        for c in seq)
    return f"""
    <section class="entry" id="metodologia">
      <h1 class="title">Metodologia</h1>

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

      <p class="seclab">La cadena · <span class="chaincount">original → despoetitzat</span></p>
      <div class="maps">{maps}</div>
    </section>"""


def build() -> Path:
    font_css = (HERE.parents[2] / "shared" / "vendor" / "spacemono.css").read_text(encoding="utf-8")
    meta = json.loads((DATA / "_meta.json").read_text(encoding="utf-8"))

    # Two distinct sections the reader switches between (never scrolls between):
    # the poems (which flow one after another within their section) and the
    # closing method note.
    menu = [
        '<li><a data-target="sec-poemes" href="#sec-poemes">Veinte poemas de amor…</a></li>',
        '<li class="meto"><a data-target="sec-metode" '
        'href="#sec-metode">Metodologia</a></li>',
    ]

    poems = _lede() + "".join(_entry(m) for m in meta)
    entries = (f'<section class="section" id="sec-poemes">{poems}</section>'
               f'<section class="section" id="sec-metode" hidden>{_method_entry()}</section>')

    chain_json = json.dumps([[c, NAMES[c]] for c in chain()], ensure_ascii=False)

    page = (_TEMPLATE
            .replace("{{FONT}}", font_css)
            .replace("{{MENU}}", "\n".join(menu))
            .replace("{{ENTRIES}}", entries)
            .replace("{{CHAIN}}", chain_json))
    out = POEM_ROOT / "index.html"
    nav = (HERE.parents[2] / "shared" / "vendor" / "menu-nav.html").read_text(encoding="utf-8")
    out.write_text(page + nav, encoding="utf-8")
    return out


_TEMPLATE = r"""<title>El que es perd en la traducció</title>
<style>
{{FONT}}
  :root{
    --ground:#f0ebe6; --ink:#282828; --muted:#8f887d; --line:#ddd6cb; --hair:#e7e1d7;
    --accent:#2f7d68; --red:#c7513b;
    --mono:"Space Mono", ui-monospace, Menlo, monospace;
  }
  *{ scrollbar-width:none; -ms-overflow-style:none; }
  *::-webkit-scrollbar{ display:none; width:0; height:0; }
  /* Horizontal clip on <html> only: it propagates to the viewport, so the sticky
     sidebar still measures against the viewport. Putting overflow on <body> would
     make <body> a (non-scrolling) scroll container and break position:sticky. */
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
  .brand{ margin-bottom:26px; line-height:1.35; }
  .brand b{ font-weight:700; font-size:14px; display:block; letter-spacing:-.01em; }
  .brand span{ display:block; color:var(--muted); font-size:11px; margin-top:4px; text-transform:uppercase; letter-spacing:.08em; }
  .menu{ list-style:none; margin:0; padding:0; font-size:14px; }
  .menu li a{ display:block; padding:3px 0; }
  .menu li a.on{ text-decoration:underline; text-underline-offset:3px; }
  .menu li.meto{ margin-top:18px; padding-top:14px; border-top:1px solid var(--hair); }
  .menu li.meto a{ color:var(--ink); font-size:14px; }

  .view{ flex:1; min-width:0; }
  .section[hidden]{ display:none; }
  .entry{ max-width:1000px; margin:0 auto; padding:clamp(40px,7vw,104px) clamp(22px,6vw,80px);
          scroll-margin-top:24px; }
  .entry + .entry{ border-top:1px solid var(--hair); }

  .title{ font-weight:400; font-size:clamp(24px,3.4vw,32px); line-height:1.1; letter-spacing:-.02em;
          margin:0; text-wrap:balance; }

  /* collection title at the head of the content column: author kicker ABOVE the
     title (matching the sibling pieces), then the title, then the epigraph */
  .kicker{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:0 0 14px; }
  .lede .epigraph{ color:var(--ink); font-style:italic; margin:18px 0 0; max-width:60ch; }

  /* despoetized residue; the original is behind a details toggle */
  .poem{ font-size:14px; line-height:1.95; }
  .poem .v{ display:block; }
  .poem .br{ display:block; height:.9em; }
  .despo{ color:var(--ink); margin-top:clamp(18px,2.6vw,28px); }
  .orig{ margin-top:clamp(22px,3.5vw,36px); }
  .orig>summary{ cursor:pointer; color:var(--muted); font-size:12px; letter-spacing:.02em;
                 list-style:none; outline:none; }
  .orig>summary::-webkit-details-marker{ display:none; }
  .orig>summary::before{ content:"+ "; }
  .orig[open]>summary::before{ content:"– "; }
  .orig>summary:hover{ color:var(--ink); }
  .orig .original{ margin-top:14px; color:var(--muted); }

  /* method */
  .prose{ max-width:62ch; margin:20px 0 0; }
  .prose i{ color:var(--muted); font-style:italic; }
  .seclab{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:40px 0 16px; }
  /* the readout is a value, not a label: normal case + tracking, matching the grid names */
  .chaincount{ color:var(--red); text-transform:none; letter-spacing:0; }
  /* the chain, made legible: each language lights up as the poem crosses it, then fades */
  .maps{ display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:8px 20px; max-width:820px; }
  .map{ color:var(--muted); transition:color .14s ease; white-space:nowrap; }
  .map b{ color:var(--ink); font-weight:400; transition:color .14s ease; }
  .map.done, .map.done b{ color:#c9c2b6; }        /* already crossed — faded */
  .map.now, .map.now b{ color:var(--red); }        /* the language being crossed now */

  /* revealed as it scrolls into view (JS enhancement; visible by default) */
  .entry.reveal{ opacity:0; transform:translateY(10px); transition:opacity .5s ease, transform .5s ease; }
  .entry.reveal.in{ opacity:1; transform:none; }

  @media (max-width:900px){
    .site{ display:block; }
    .index{ width:auto; position:static; height:auto; overflow:visible; padding:20px 22px;
            border-right:0; border-bottom:1px solid var(--line);
            display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 18px; }
    .brand{ margin:0 14px 0 0; }
    .menu{ display:flex; flex-wrap:wrap; gap:4px 16px; }
  }
  @media (prefers-reduced-motion: reduce){
    html{ scroll-behavior:auto; }
    .entry.reveal{ opacity:1; transform:none; transition:none; }
    .map, .map b{ transition:none; }
  }
</style>

<div class="wrap"><div class="site">
  <nav class="index">
    <div class="brand"><a data-target="sec-poemes" href="#sec-poemes">
      <b>El que es perd en la traducció</b><span>Despoetització</span></a></div>
    <ol class="menu">{{MENU}}</ol>
  </nav>
  <main class="view" id="top">
    {{ENTRIES}}
  </main>
</div></div>

<script>
  var CHAIN = {{CHAIN}};           // [[code, name], ...] es ... es
  (function(){
    var sections = [].slice.call(document.querySelectorAll('.section'));
    var ids = sections.map(function(s){ return s.id; });
    var links = [].slice.call(document.querySelectorAll('[data-target]'));
    var entries = [].slice.call(document.querySelectorAll('.entry'));
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Methodology grid: sweep a highlight through the 104-language chain in order —
    // each language lights up as the poem crosses it, then fades — looping. This is
    // the one place the concept is animated; the poems themselves stay plain text.
    var chips = [].slice.call(document.querySelectorAll('#metodologia .map'));
    var count = document.querySelector('#metodologia .chaincount');
    var steps = chips.length - 1;        // 104 crossings between the two Spanish ends
    var timer = null, running = false;

    function gridReset(){
      chips.forEach(function(c){ c.className = 'map'; });
      if(count) count.textContent = 'original → despoetitzat';
    }
    function gridStep(i){
      if(!running) return;
      if(i > steps){                     // round-trip closed -> pause, then loop
        if(count) count.textContent = 'original → despoetitzat';
        timer = setTimeout(gridCycle, 3200);
        return;
      }
      chips.forEach(function(c, k){
        c.className = 'map' + (k < i ? ' done' : (k === i ? ' now' : ''));
      });
      var here = CHAIN[i];               // [code, name] of the language reached
      if(count) count.textContent = here[1] + ' · ' + i + ' / ' + steps;
      timer = setTimeout(function(){ gridStep(i + 1); }, 58);
    }
    function gridCycle(){ gridReset(); timer = setTimeout(function(){ gridStep(0); }, 600); }
    function gridStart(){ if(running || reduce || !chips.length) return; running = true; gridCycle(); }
    function gridStop(){ running = false; clearTimeout(timer); gridReset(); }

    // Reveal-on-scroll: entries fade up as they enter their section's viewport.
    if('IntersectionObserver' in window){
      entries.forEach(function(el){ el.classList.add('reveal'); });
      var revealObs = new IntersectionObserver(function(ents){
        ents.forEach(function(en){
          if(en.isIntersecting){ en.target.classList.add('in'); revealObs.unobserve(en.target); }
        });
      }, {rootMargin:'0px 0px -8% 0px', threshold:0.05});
      entries.forEach(function(el){ revealObs.observe(el); });
    }

    // Switch between the two sections; each has its own scroll. The grid only runs
    // while Metodologia is the section on show.
    function show(id){
      if(ids.indexOf(id) < 0) id = ids[0];
      sections.forEach(function(s){ s.hidden = s.id !== id; });
      links.forEach(function(a){ a.classList.toggle('on', a.dataset.target === id); });
      window.scrollTo({top:0, behavior:'auto'});
      if(id === 'sec-metode') gridStart(); else gridStop();
    }
    links.forEach(function(a){
      a.addEventListener('click', function(ev){
        ev.preventDefault();
        history.replaceState(null, '', '#' + a.dataset.target);
        show(a.dataset.target);
      });
    });
    show(location.hash ? location.hash.slice(1) : ids[0]);
  })();
</script>
"""


if __name__ == "__main__":
    print(build())
