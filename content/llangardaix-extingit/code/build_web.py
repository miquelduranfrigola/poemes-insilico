"""Build the self-contained web page for "Llangardaix extingit" -> index.html (poem-folder root).

A left sections column ("El genoma" · "Metodologia") beside the content, in the
shared Space Mono / cream look, with the webfont inlined from
shared/vendor/spacemono.css (no external requests). Served verbatim via `page:`.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

POEM_ROOT = Path(__file__).resolve().parent.parent
REPO = POEM_ROOT.parent.parent
RESULTS = POEM_ROOT / "results"
FONT_CSS = (REPO / "shared" / "vendor" / "spacemono.css").read_text(encoding="utf-8")
LINE_WIDTH = 60

METHOD = """\
<p>Reconstrucció de seqüències ancestrals (ASR) del genoma mitocondrial de
l'avantpassat comú de la sargantana de paret (<i>Podarcis muralis</i>) i el varà
aquàtic (<i>Varanus salvator</i>), a partir de sis espècies vives.</p>
<p>Es descarreguen els mitogenomes complets de GenBank (NCBI&nbsp;Entrez /
Biopython), s'alineen gen a gen i s'infereix l'avantpassat per màxima
versemblança amb el model <b>HKY85</b> i la poda de Felsenstein. Cada base
s'escriu en majúscula quan el posterior de la millor base supera 0,90; si no,
s'escriu amb el codi d'ambigüitat IUPAC del conjunt mínim de bases que cobreix el
90&nbsp;% del posterior —l'alfabet del dubte allà on el temps ha esborrat el
senyal.</p>
"""


def build() -> Path:
    lines = (RESULTS / "ancestor.fasta").read_text().splitlines()
    seq = "".join(l.strip() for l in lines if not l.startswith(">"))
    wrapped = "\n".join(textwrap.wrap(seq, LINE_WIDTH))
    html = f"""<!doctype html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Llangardaix extingit</title>
<style>
{FONT_CSS}
  :root{{ --ground:#f0ebe6; --ink:#282828; --muted:#8f887d; --line:#ddd6cb;
          --mono:"Space Mono", ui-monospace, Menlo, monospace; }}
  *{{ box-sizing:border-box; scrollbar-width:none; }} *::-webkit-scrollbar{{ display:none; }}
  html,body{{ margin:0; padding:0; background:var(--ground); }}
  body{{ color:var(--ink); font-family:var(--mono); font-size:14px; line-height:1.65;
         -webkit-font-smoothing:antialiased; }}
  a{{ color:var(--ink); text-decoration:none; }} a:hover{{ opacity:.55; }}
  .app{{ display:flex; align-items:flex-start; min-height:100vh; }}
  .scol{{ width:220px; flex:none; position:sticky; top:0; height:100vh;
          padding:30px 22px; border-right:1px solid var(--line); }}
  .brand{{ margin-bottom:26px; line-height:1.35; min-height:58px; }}
  .brand b{{ font-weight:700; font-size:14px; display:block; letter-spacing:-.01em; }}
  .brand span{{ display:block; font-size:11px; color:var(--muted); margin-top:4px;
                text-transform:uppercase; letter-spacing:.08em; }}
  .scol a{{ display:block; padding:4px 0; }}
  .scol a.meto{{ margin-top:16px; padding-top:12px; border-top:1px solid var(--line); }}
  .scol a.on{{ text-decoration:underline; text-underline-offset:3px; }}
  .scontent{{ flex:1; min-width:0; }}
  .entry{{ max-width:1000px; margin:0 auto; padding:114px clamp(22px,6vw,80px) clamp(40px,7vw,104px); }}
  .kicker{{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:0 0 14px; }}
  .title{{ font-weight:400; font-size:clamp(24px,3.4vw,32px); line-height:1.1; letter-spacing:-.02em; margin:0; }}
  .dims{{ font-size:11px; letter-spacing:.18em; text-transform:uppercase; color:var(--muted); margin:16px 0 0; }}
  .seqbox{{ margin-top:clamp(28px,5vw,48px); border-top:1px solid var(--line); padding-top:24px; }}
  .fasta-head{{ color:var(--muted); font-size:12px; margin:0 0 12px; word-break:break-all; }}
  pre.seq{{ margin:0; font-size:13px; line-height:2.0; white-space:pre; overflow-x:auto; letter-spacing:.02em; }}
  .prose{{ max-width:60ch; }} .prose p{{ margin:0 0 1rem; }}
  section[hidden]{{ display:none; }}
</style>
</head>
<body>
  <div class="app">
    <nav class="scol">
      <div class="brand"><b>Llangardaix extingit</b><span>genoma inferit</span></div>
      <a data-sec="obra" class="on" href="#obra">El genoma</a>
      <a class="meto" data-sec="meto" href="#meto">Metodologia</a>
    </nav>
    <main class="scontent">
      <section id="obra" class="entry">
        <p class="kicker">Llangardaix extingit</p>
        <h1 class="title">El genoma inferit</h1>
        <p class="dims">avantpassat Podarcis &times; Varanus &middot; {len(seq)} pb &middot; reconstrucció ML</p>
        <div class="seqbox">
          <p class="fasta-head">&gt;sargantana_avi_ancestor mitogenome | ML reconstruction (HKY85)</p>
<pre class="seq">{wrapped}</pre>
        </div>
      </section>
      <section id="meto" class="entry" hidden>
        <h1 class="title">Metodologia</h1>
        <div class="prose" style="margin-top:clamp(24px,4vw,40px)">{METHOD}</div>
      </section>
    </main>
  </div>
  <script>
    (function(){{
      var links=[].slice.call(document.querySelectorAll('[data-sec]'));
      var secs=[].slice.call(document.querySelectorAll('section[id]'));
      function show(id){{
        if(!document.getElementById(id)) id='obra';
        secs.forEach(function(s){{ s.hidden = s.id!==id; }});
        links.forEach(function(a){{ a.classList.toggle('on', a.dataset.sec===id); }});
        window.scrollTo(0,0);
      }}
      links.forEach(function(a){{ a.addEventListener('click', function(e){{ e.preventDefault();
        history.replaceState(null,'','#'+a.dataset.sec); show(a.dataset.sec); }}); }});
      show(location.hash.slice(1) || 'obra');
    }})();
  </script>
</body>
</html>
"""
    nav = (REPO / "shared" / "vendor" / "menu-nav.html").read_text(encoding="utf-8")
    out = POEM_ROOT / "index.html"
    out.write_text(html + nav, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build())
