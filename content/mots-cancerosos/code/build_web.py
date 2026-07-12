"""Assemble the self-contained "Mots cancerosos" gallery (HTML).

Same museum treatment as the sibling "Poemes proteics": Space Mono on a cream
ground, a quiet left index and a spacious content pane. Here the piece is a poem
that *evolves*: starting from a seed poem, one word (a gene) mutates per step by a
single-letter edit — each mutated word lights up red as the poem drifts, looping.
It is auto-playing, not interactive (no controls).

Reads data/evolution.json (the ordered mutation log) and the inlined Space Mono
webfont (code/vendor/spacemono.css). Writes results/evolution.html — everything
inlined, no external requests.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

POEM_ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent

POS_CA = {"N": "nom", "V": "verb", "A": "adjectiu", "R": "adverbi"}
EDIT_CA = {"substitution": "substitució", "deletion": "deleció", "insertion": "inserció"}


def _highlight(prev_line: str, new_line: str) -> str:
    """new_line as HTML with the changed token(s) wrapped in <span class=mut>."""
    p, n = prev_line.split(" "), new_line.split(" ")
    i = 0
    while i < len(p) and i < len(n) and p[i] == n[i]:
        i += 1
    j = 0
    while j < (len(p) - i) and j < (len(n) - i) and p[-1 - j] == n[-1 - j]:
        j += 1
    pre, mid, suf = n[:i], (n[i: len(n) - j] if j else n[i:]), (n[len(n) - j:] if j else [])
    out = []
    if pre:
        out.append(html.escape(" ".join(pre)))
    out.append('<span class="mut">' + html.escape(" ".join(mid)) + "</span>")
    if suf:
        out.append(html.escape(" ".join(suf)))
    return " ".join(out)


def _payload():
    data = json.loads((POEM_ROOT / "data" / "evolution.json").read_text(encoding="utf-8"))
    cur = list(data["original"])
    steps = []
    for st in data["steps"]:
        li = st["line"]
        hi = _highlight(cur[li], st["line_after"])
        cur[li] = st["line_after"]
        steps.append({
            "n": st["n"], "line": li, "before": st["before"], "after": st["after"],
            "pos": POS_CA.get(st["pos"], st["pos"]), "edit": EDIT_CA.get(st["edit"], st["edit"]),
            "plain": html.escape(st["line_after"]), "hi": hi,
        })
    return {
        "title": data.get("title", "Evolució"),
        "source": data.get("source", {}),
        "conserved": data.get("conserved", {}),
        "initLines": [html.escape(l) for l in data["original"]],
        "steps": steps,
    }


def build() -> Path:
    font_css = (HERE.parents[2] / "shared" / "vendor" / "spacemono.css").read_text(encoding="utf-8")
    payload = _payload()
    src = payload["source"]
    conserved_note = payload.get("conserved", {}).get("note", "")

    page = (_TEMPLATE
            .replace("{{FONT}}", font_css)
            .replace("{{AUTHOR}}", html.escape(src.get("author", "")))
            .replace("{{SEED}}", html.escape(src.get("poem", "")))
            .replace("{{CONSERVED}}", html.escape(conserved_note))
            .replace("{{DATA}}", json.dumps(payload, ensure_ascii=False))
            .replace("{{POS}}", json.dumps(POS_CA, ensure_ascii=False))
            .replace("{{EDIT}}", json.dumps(EDIT_CA, ensure_ascii=False)))
    out = POEM_ROOT / "results" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    nav = (HERE.parents[2] / "shared" / "vendor" / "menu-nav.html").read_text(encoding="utf-8")
    out.write_text(page + nav, encoding="utf-8")
    return out


_TEMPLATE = r"""<title>Mots cancerosos</title>
<style>
{{FONT}}
  :root{
    --ground:#f0ebe6; --ink:#282828; --muted:#8f887d; --line:#ddd6cb; --hair:#e7e1d7;
    --accent:#2f7d68; --red:#c7513b;
    --mono:"Space Mono", ui-monospace, Menlo, monospace;
  }
  *{ scrollbar-width:none; -ms-overflow-style:none; }
  *::-webkit-scrollbar{ display:none; width:0; height:0; }
  html,body{ margin:0; padding:0; background:var(--ground); overflow-x:hidden; }
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
  .entry{ max-width:1000px; margin:0 auto; padding:clamp(40px,7vw,104px) clamp(22px,6vw,80px); }
  .entry[hidden]{ display:none; }
  .entry{ animation:appear .3s ease both; }
  @keyframes appear{ from{ opacity:0; transform:translateY(8px);} to{ opacity:1; transform:none;} }

  .kicker{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:0 0 14px; }
  .title{ font-weight:400; font-size:clamp(24px,3.4vw,32px); line-height:1.1; letter-spacing:-.02em;
          margin:0; text-wrap:balance; }
  .dims{ font-size:11px; letter-spacing:.18em; text-transform:uppercase; color:var(--muted);
         margin:18px 0 0; min-height:1.4em; }
  .dims b{ color:var(--ink); font-weight:400; } .dims .arrow,.dims .rd{ color:var(--red); }

  .poem{ font-size:15px; line-height:2.05; margin:clamp(30px,5vw,52px) 0 0; overflow-x:auto; }
  .poem .v{ display:block; white-space:nowrap; }
  .poem .br{ display:block; height:.9em; }
  .mut{ color:var(--red); }

  .prose{ max-width:60ch; margin:0 0 10px; }
  .seclab{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:34px 0 12px; }
  .maps{ display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:9px 20px; max-width:720px; }
  .map b{ color:var(--red); font-weight:400; } .map i{ color:var(--muted); font-style:normal; }

  @media (max-width:900px){
    .site{ display:block; }
    .index{ width:auto; position:static; height:auto; overflow:visible; padding:20px 22px;
            border-right:0; border-bottom:1px solid var(--line);
            display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 18px; }
    .brand{ margin:0 14px 0 0; } .menu{ display:flex; flex-wrap:wrap; gap:4px 16px; }
  }
  @media (prefers-reduced-motion: reduce){ .entry{ animation:none; } }
</style>

<div class="wrap"><div class="site">
  <nav class="index">
    <div class="brand"><a data-target="poem" href="#poem"><b>Mots cancerosos</b></a>
      <span>l'evolució d'un poema</span></div>
    <ol class="menu">
      <li><a data-target="poem" href="#poem" class="on">Res no és mesquí (mutant)</a></li>
      <li class="meto"><a data-target="metode" href="#metode">Metodologia</a></li>
    </ol>
  </nav>
  <main class="view">
    <section class="entry" id="poem">
      <p class="kicker">{{AUTHOR}} · poema llavor</p>
      <h2 class="title">{{SEED}}</h2>
      <p class="dims" id="dims"></p>
      <div class="poem" id="poemtext"></div>
    </section>
    <section class="entry" id="metode" hidden>
      <h1 class="title">Metodologia</h1>
      <p class="prose">El poema és un genoma i cada paraula, un gen. A cada pas, una
        paraula muta per una sola lletra —substitució, inserció o deleció—, tal com
        les mutacions somàtiques del càncer. La mutació només sobreviu si (1) dona una
        paraula catalana real, (2) manté la categoria gramatical i la concordança, i
        (3) el poema encara té sentit. Cada mot mutat s'encén en <span class="rd" style="color:var(--red)">vermell</span>.</p>
      <p class="prose">{{CONSERVED}}</p>
    </section>
  </main>
</div></div>

<script>
  var DATA = {{DATA}};
  (function(){
    var links = [].slice.call(document.querySelectorAll('[data-target]'));
    var entries = [].slice.call(document.querySelectorAll('.entry'));
    var N = DATA.steps.length, timer = null, s = 0;
    var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    // Adaptive pace: whole loop ~90s regardless of how many mutations there are.
    var base = Math.max(28, Math.min(240, Math.round(90000 / N)));

    function linesAt(k){
      var lines = DATA.initLines.slice();
      for(var i=0;i<k;i++){ var st=DATA.steps[i]; lines[st.line]=st.plain; }
      return lines;
    }
    function paint(){
      var lines = linesAt(s), box = document.getElementById('poemtext'), dims = document.getElementById('dims');
      box.innerHTML = lines.map(function(t){ return '<span class="v">'+t+'</span>'; }).join('');
      if(s>=1){
        var st = DATA.steps[s-1];
        box.children[st.line].innerHTML = st.hi;
        dims.innerHTML = 'Mutació '+st.n+' / '+N+' &nbsp; <b>'+st.before+'</b> <span class="arrow">→</span> <b>'+
          st.after+'</b> &nbsp; '+st.pos+' · '+st.edit;
      } else {
        dims.innerHTML = 'Poema llavor · '+ (DATA.source.author||'');
      }
    }
    function loop(){
      paint();
      var dur = (s===0) ? 700 : (s===N ? 1600 : base);
      s = (s>=N) ? 0 : s+1;
      timer = setTimeout(loop, dur);
    }

    function show(id){
      entries.forEach(function(e){ e.hidden = e.id !== id; });
      links.forEach(function(a){ a.classList.toggle('on', a.dataset.target===id); });
      if(timer){ clearTimeout(timer); timer=null; }
      if(id==='poem'){ s=0; if(reduce){ s=N; paint(); } else { loop(); } }
      window.scrollTo({top:0});
    }
    links.forEach(function(a){
      a.addEventListener('click', function(ev){ ev.preventDefault();
        history.replaceState(null,'','#'+a.dataset.target); show(a.dataset.target); });
    });
    show((location.hash||'#poem').slice(1) || 'poem');
  })();
</script>
"""


if __name__ == "__main__":
    print(build())
