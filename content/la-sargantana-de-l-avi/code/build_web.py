"""Build the self-contained web page for "La sargantana de l'avi" -> results/index.html.

Renders the reconstructed ancestral mitogenome (the "haze" sequence) in the shared
Space Mono / cream look, with the Space Mono webfont **inlined** from
shared/vendor/spacemono.css (no external requests). Served verbatim by the site via
the poem's `page: results/index.html` key.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

POEM_ROOT = Path(__file__).resolve().parent.parent
REPO = POEM_ROOT.parent.parent
RESULTS = POEM_ROOT / "results"
FONT_CSS = (REPO / "shared" / "vendor" / "spacemono.css").read_text(encoding="utf-8")
LINE_WIDTH = 60


def build() -> Path:
    lines = (RESULTS / "ancestor.fasta").read_text().splitlines()
    seq = "".join(l.strip() for l in lines if not l.startswith(">"))
    wrapped = "\n".join(textwrap.wrap(seq, LINE_WIDTH))
    html = f"""<!doctype html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>La sargantana de l'avi</title>
<style>
{FONT_CSS}
  :root{{ --ground:#f0ebe6; --ink:#282828; --muted:#8f887d; --line:#ddd6cb;
          --mono:"Space Mono", ui-monospace, Menlo, monospace; }}
  html,body{{ margin:0; padding:0; background:var(--ground); }}
  body{{ color:var(--ink); font-family:var(--mono); font-size:14px; line-height:1.65;
         -webkit-font-smoothing:antialiased; }}
  .entry{{ max-width:900px; margin:0 auto; padding:clamp(40px,7vw,96px) clamp(22px,6vw,72px); }}
  .kicker{{ font-size:11px; letter-spacing:.24em; text-transform:uppercase; color:var(--muted); margin:0 0 14px; }}
  .title{{ font-weight:400; font-size:clamp(24px,3.4vw,32px); line-height:1.1; letter-spacing:-.02em; margin:0; }}
  .dims{{ font-size:11px; letter-spacing:.18em; text-transform:uppercase; color:var(--muted); margin:16px 0 0; }}
  .seqbox{{ margin-top:clamp(28px,5vw,48px); border-top:1px solid var(--line); padding-top:24px; }}
  .fasta-head{{ color:var(--muted); font-size:12px; margin:0 0 12px; word-break:break-all; }}
  pre.seq{{ margin:0; font-family:var(--mono); font-size:13px; line-height:2.0;
            white-space:pre; overflow-x:auto; letter-spacing:.02em; }}
</style>
</head>
<body>
  <div class="entry">
    <p class="kicker">Poemes computacionals</p>
    <h1 class="title">La sargantana de l'avi</h1>
    <p class="dims">genoma mitocondrial &middot; avantpassat Podarcis &times; Varanus &middot; {len(seq)} pb &middot; reconstrucció ML</p>
    <div class="seqbox">
      <p class="fasta-head">&gt;sargantana_avi_ancestor mitogenome | ML reconstruction (HKY85)</p>
<pre class="seq">{wrapped}</pre>
    </div>
  </div>
</body>
</html>
"""
    out = RESULTS / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build())
