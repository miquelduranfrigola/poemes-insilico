"""The 104-language despoetization chain.

The original 2016 project drove Google Translate's full language roster in a
single cycle: starting from Spanish (``es``), translate into the next language
in alphabetical order, then the next, ... all the way around the alphabet and
back to Spanish. Poetry is what gets lost in translation — so the poem that
returns is the *despoetized* residue of Neruda's original.

``LANGUAGES`` is Google Translate's roster as it stood in 2016 (the exact list
the notebook printed), sorted by ISO code. ``chain()`` reproduces the cyclic
succession that produced the archived results; ``NAMES`` maps each code to its
Catalan language name (shown in the gallery and the CLI).
"""

from __future__ import annotations

# Google Translate's roster (2016), sorted by ISO code — verbatim from the
# original notebook's `sorted(languages)` output.
LANGUAGES: list[str] = [
    "af", "am", "ar", "az", "be", "bg", "bn", "bs", "ca", "ceb", "co", "cs",
    "cy", "da", "de", "el", "en", "eo", "es", "et", "eu", "fa", "fi", "fr",
    "fy", "ga", "gd", "gl", "gu", "ha", "haw", "hi", "hmn", "hr", "ht", "hu",
    "hy", "id", "ig", "is", "it", "iw", "ja", "jw", "ka", "kk", "km", "kn",
    "ko", "ku", "ky", "la", "lb", "lo", "lt", "lv", "mg", "mi", "mk", "ml",
    "mn", "mr", "ms", "mt", "my", "ne", "nl", "no", "ny", "pa", "pl", "ps",
    "pt", "ro", "ru", "sd", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr",
    "st", "su", "sv", "sw", "ta", "te", "tg", "th", "tl", "tr", "uk", "ur",
    "uz", "vi", "xh", "yi", "yo", "zh", "zh-TW", "zu",
]

# Catalan language names (shown in the web gallery and the CLI).
NAMES: dict[str, str] = {
    "af": "Afrikaans", "am": "Amhàric", "ar": "Àrab", "az": "Azerbaidjanès",
    "be": "Bielorús", "bg": "Búlgar", "bn": "Bengalí", "bs": "Bosnià",
    "ca": "Català", "ceb": "Cebuà", "co": "Cors", "cs": "Txec",
    "cy": "Gal·lès", "da": "Danès", "de": "Alemany", "el": "Grec",
    "en": "Anglès", "eo": "Esperanto", "es": "Castellà", "et": "Estonià",
    "eu": "Basc", "fa": "Persa", "fi": "Finès", "fr": "Francès",
    "fy": "Frisó", "ga": "Irlandès", "gd": "Gaèlic escocès", "gl": "Gallec",
    "gu": "Gujarati", "ha": "Hausa", "haw": "Hawaià", "hi": "Hindi",
    "hmn": "Hmong", "hr": "Croat", "ht": "Crioll haitià", "hu": "Hongarès",
    "hy": "Armeni", "id": "Indonesi", "ig": "Igbo", "is": "Islandès",
    "it": "Italià", "iw": "Hebreu", "ja": "Japonès", "jw": "Javanès",
    "ka": "Georgià", "kk": "Kazakh", "km": "Khmer", "kn": "Kannada",
    "ko": "Coreà", "ku": "Kurd", "ky": "Kirguís", "la": "Llatí",
    "lb": "Luxemburguès", "lo": "Laosià", "lt": "Lituà", "lv": "Letó",
    "mg": "Malgaix", "mi": "Maori", "mk": "Macedoni", "ml": "Malaiàlam",
    "mn": "Mongol", "mr": "Marathi", "ms": "Malai", "mt": "Maltès",
    "my": "Birmà", "ne": "Nepalès", "nl": "Neerlandès", "no": "Noruec",
    "ny": "Chichewa", "pa": "Panjabi", "pl": "Polonès", "ps": "Paixtu",
    "pt": "Portuguès", "ro": "Romanès", "ru": "Rus", "sd": "Sindi",
    "si": "Singalès", "sk": "Eslovac", "sl": "Eslovè", "sm": "Samoà",
    "sn": "Xona", "so": "Somali", "sq": "Albanès", "sr": "Serbi",
    "st": "Sotho", "su": "Sondanès", "sv": "Suec", "sw": "Suahili",
    "ta": "Tàmil", "te": "Telugu", "tg": "Tadjik", "th": "Tai",
    "tl": "Filipí", "tr": "Turc", "uk": "Ucraïnès", "ur": "Urdú",
    "uz": "Uzbek", "vi": "Vietnamita", "xh": "Xosa", "yi": "Ídix",
    "yo": "Ioruba", "zh": "Xinès", "zh-TW": "Xinès trad.",
    "zu": "Zulu",
}

START = "es"


def chain(start: str = START) -> list[str]:
    """The cyclic language succession, e.g. ``[es, et, eu, ..., en, eo, es]``.

    Begins and ends at ``start``, visiting every other language exactly once in
    alphabetical order. Each adjacent pair is one translation step; there are
    ``len(LANGUAGES)`` steps (the despoetizations).
    """
    n = len(LANGUAGES)
    i = LANGUAGES.index(start)
    order = [LANGUAGES[(i + k) % n] for k in range(n)]
    return order + [start]


def steps(start: str = START) -> list[tuple[str, str]]:
    """The chain as ``(source, target)`` translation steps."""
    seq = chain(start)
    return list(zip(seq[:-1], seq[1:]))


if __name__ == "__main__":
    seq = chain()
    print(f"{len(LANGUAGES)} languages, {len(steps())} translation steps")
    print(" -> ".join(f"[{c}] {NAMES[c]}" for c in seq))
