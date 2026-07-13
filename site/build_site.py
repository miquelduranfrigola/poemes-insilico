#!/usr/bin/env python3
"""Build the *poemes computacionals* static website into ``_site/``.

The single source of truth is each ``content/<slug>/`` folder: this reads every
``metadata.yml``. A piece with a ``page:`` key is served from its self-contained
``results/index.html`` verbatim; otherwise ``poem.md`` is rendered. The index is a
left-sidebar shell that shows each piece in an iframe. Authors never edit HTML.

Poetry-aware rendering (the important part)
-------------------------------------------
Plain Markdown collapses single line breaks, which destroys verse and stanza
structure. Instead we render ``poem.md`` ourselves:

* a blank line separates **estrofes** (stanzas) -> each becomes its own block,
* every line inside a stanza is a **verse** -> kept on its own line,
* fenced ``` code blocks are preserved verbatim (used by poems whose body is a
  generated diagram, e.g. the mutation tree), and
* the leading ``# Title`` and HTML comments are stripped (the title comes from
  ``metadata.yml``).

Usage
-----
    python site/build_site.py                 # -> ./_site
    python site/build_site.py --out public
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

SITE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SITE_DIR.parent
POEMS_DIR = REPO_ROOT / "content"
TEMPLATES_DIR = SITE_DIR / "templates"
STATIC_DIR = SITE_DIR / "static"

_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_TITLE_RE = re.compile(r"^\s*#\s+.*$", re.MULTILINE)


@dataclass
class Poem:
    slug: str
    title: str
    date: str
    order: int | None
    author: str
    language: str
    description_html: str
    tools: list[dict]
    tags: list[str]
    poem_html: str
    page_src: Path | None = None  # optional self-contained page to serve verbatim


# --------------------------------------------------------------------------- #
# Poetry-aware rendering
# --------------------------------------------------------------------------- #
def render_poem_body(markdown_text: str) -> str:
    """Render a ``poem.md`` body into HTML that preserves verses and estrofes."""
    text = _COMMENT_RE.sub("", markdown_text)
    text = _TITLE_RE.sub("", text, count=1)
    lines = text.replace("\r\n", "\n").split("\n")

    blocks: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        stripped = lines[i].strip()

        # Fenced code block -> <pre> preserved verbatim (e.g. a mutation tree).
        if stripped.startswith("```"):
            code: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # consume the closing fence
            escaped = html.escape("\n".join(code))
            blocks.append(f'<pre class="poem-figure">{escaped}</pre>')
            continue

        # Blank line -> stanza separator.
        if stripped == "":
            i += 1
            continue

        # Gather one stanza (consecutive non-blank, non-fence lines).
        verses: list[str] = []
        while i < n and lines[i].strip() != "" and not lines[i].strip().startswith("```"):
            verses.append(html.escape(lines[i].rstrip()))
            i += 1
        stanza = '<br>\n'.join(verses)
        blocks.append(f'<p class="estrofa">{stanza}</p>')

    return "\n".join(blocks)


def render_paragraphs(text: str | None) -> str:
    """Render a prose field (e.g. description) into <p> paragraphs.

    Unlike a poem, prose reflows: single newlines (YAML line-wrapping) are joined
    with a space; only blank lines start a new paragraph.
    """
    if not text:
        return ""
    chunks = [c.strip() for c in text.replace("\r\n", "\n").split("\n\n")]
    out = []
    for chunk in chunks:
        if not chunk:
            continue
        flowed = " ".join(line.strip() for line in chunk.split("\n"))
        out.append(f"<p>{html.escape(flowed)}</p>")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_poem(folder: Path) -> Poem | None:
    meta_path = folder / "metadata.yml"
    poem_path = folder / "poem.md"
    if not meta_path.exists() or not poem_path.exists():
        return None

    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    for required in ("title", "slug", "date"):
        if not meta.get(required):
            raise SystemExit(f"{meta_path}: missing required field '{required}'")
    if meta["slug"] != folder.name:
        raise SystemExit(f"{meta_path}: slug '{meta['slug']}' != folder '{folder.name}'")

    # Optional: a poem may ship a self-contained HTML page (an immersive gallery)
    # to serve instead of the templated poem.md — e.g. the mutation animation.
    page_src = None
    if meta.get("page"):
        candidate = (folder / str(meta["page"])).resolve()
        if candidate.exists():
            page_src = candidate
        else:
            raise SystemExit(f"{meta_path}: page '{meta['page']}' not found at {candidate}")

    order = meta.get("order")
    return Poem(
        slug=str(meta["slug"]),
        title=str(meta["title"]),
        date=str(meta["date"]),
        order=int(order) if order is not None else None,
        author=str(meta.get("author", "")),
        language=str(meta.get("language", "ca")),
        description_html=render_paragraphs(meta.get("description")),
        tools=list(meta.get("tools") or []),
        tags=list(meta.get("tags") or []),
        poem_html=render_poem_body(poem_path.read_text(encoding="utf-8")),
        page_src=page_src,
    )


def discover_poems() -> list[Poem]:
    poems = []
    for folder in sorted(p for p in POEMS_DIR.iterdir() if p.is_dir()):
        poem = load_poem(folder)
        if poem is not None:
            poems.append(poem)
    # Explicit `order` (ascending) wins; poems without it fall back to newest-first
    # by ISO date. Two stable passes: date desc, then order (None sorts last).
    poems.sort(key=lambda p: p.date, reverse=True)
    poems.sort(key=lambda p: (p.order is None, p.order if p.order is not None else 0))
    return poems


# --------------------------------------------------------------------------- #
# Building
# --------------------------------------------------------------------------- #
def build(out_dir: Path) -> None:
    poems = discover_poems()

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # Static assets.
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, out_dir / "static")

    site_title = "Poemes in silico"

    index_tmpl = env.get_template("index.html")
    (out_dir / "index.html").write_text(
        index_tmpl.render(site_title=site_title, poems=poems, root=""),
        encoding="utf-8",
    )

    poem_tmpl = env.get_template("poem.html")
    for poem in poems:
        poem_out = out_dir / poem.slug
        poem_out.mkdir(parents=True, exist_ok=True)
        if poem.page_src is not None:
            # Serve the poem's self-contained gallery verbatim.
            shutil.copyfile(poem.page_src, poem_out / "index.html")
        else:
            (poem_out / "index.html").write_text(
                poem_tmpl.render(site_title=site_title, poem=poem, root="../"),
                encoding="utf-8",
            )

    print(f"Built {len(poems)} poem(s) into {out_dir}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the poemes-computacionals website.")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "_site", help="output directory")
    args = parser.parse_args()
    build(args.out)


if __name__ == "__main__":
    main()
