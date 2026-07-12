"""Run a text through the despoetization chain.

The transformation is a round-trip through Google Translate's whole language
roster (see :mod:`languages`): Spanish -> Estonian -> Basque -> ... -> Spanish.
Every hop degrades the text a little; what returns is the *despoetized* residue.

This module documents and (best-effort) reproduces the 2016 method. The archived
results under ``data/despoetized/`` are the canonical artifact of the poem — a
re-run today will differ, because Google Translate is a moving target. Re-running
requires the optional ``deep-translator`` dependency and a network connection.
"""

from __future__ import annotations

from typing import Callable

from languages import chain

# Translator = Callable[(text, source, target) -> translated_text]
Translator = Callable[[str, str, str], str]

# The 2016 chain uses Google's historical ISO codes. A few have since been
# renamed; deep-translator (current Google endpoint) expects these instead.
DEEP_TRANSLATOR_REMAP = {
    "iw": "he",      # Hebrew
    "jw": "jv",      # Javanese
    "zh": "zh-CN",   # Chinese (Simplified)
    "zh-TW": "zh-TW",
}


def despoetize(
    text: str,
    translate: Translator,
    start: str = "es",
    capture: bool = False,
    progress: Callable[[int, int, str, str], None] | None = None,
):
    """Translate ``text`` around the whole language chain and back to ``start``.

    Returns the final text, or ``(final, steps)`` if ``capture`` is set, where
    ``steps`` is a list of ``(source, target, text_after)`` for every hop.
    ``progress(i, total, source, target)`` is called before each hop if given.
    """
    seq = chain(start)
    pairs = list(zip(seq[:-1], seq[1:]))
    steps = []
    current = text
    for i, (src, tgt) in enumerate(pairs):
        if progress:
            progress(i, len(pairs), src, tgt)
        current = translate(current, src, tgt)
        if capture:
            steps.append((src, tgt, current))
    return (current, steps) if capture else current


def google_translator() -> Translator:
    """A translator backed by ``deep-translator``'s GoogleTranslator.

    Imported lazily so the poem's archived results stay usable without the dep.
    """
    from deep_translator import GoogleTranslator  # type: ignore

    def translate(text: str, source: str, target: str) -> str:
        src = DEEP_TRANSLATOR_REMAP.get(source, source)
        tgt = DEEP_TRANSLATOR_REMAP.get(target, target)
        return GoogleTranslator(source=src, target=tgt).translate(text)

    return translate
