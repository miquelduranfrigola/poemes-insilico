"""The 104-language despoetization chain.

The original 2016 project drove Google Translate's full language roster in a
single cycle: starting from Spanish (``es``), translate into the next language
in alphabetical order, then the next, ... all the way around the alphabet and
back to Spanish. Poetry is what gets lost in translation — so the poem that
returns is the *despoetized* residue of Neruda's original.

``LANGUAGES`` is Google Translate's roster as it stood in 2016 (the exact list
the notebook printed), sorted by ISO code. ``chain()`` reproduces the cyclic
succession that produced the archived results; ``NAMES`` maps each code to the
English language name used in the method note.
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

# English language names (as used in the original method note).
NAMES: dict[str, str] = {
    "af": "Afrikaans", "am": "Amharic", "ar": "Arabic", "az": "Azerbaijani",
    "be": "Belarusian", "bg": "Bulgarian", "bn": "Bengali", "bs": "Bosnian",
    "ca": "Catalan", "ceb": "Cebuano", "co": "Corsican", "cs": "Czech",
    "cy": "Welsh", "da": "Danish", "de": "German", "el": "Greek",
    "en": "English", "eo": "Esperanto", "es": "Spanish", "et": "Estonian",
    "eu": "Basque", "fa": "Persian", "fi": "Finnish", "fr": "French",
    "fy": "Frisian", "ga": "Irish", "gd": "Scots Gaelic", "gl": "Galician",
    "gu": "Gujarati", "ha": "Hausa", "haw": "Hawaiian", "hi": "Hindi",
    "hmn": "Hmong", "hr": "Croatian", "ht": "Haitian Creole", "hu": "Hungarian",
    "hy": "Armenian", "id": "Indonesian", "ig": "Igbo", "is": "Icelandic",
    "it": "Italian", "iw": "Hebrew", "ja": "Japanese", "jw": "Javanese",
    "ka": "Georgian", "kk": "Kazakh", "km": "Khmer", "kn": "Kannada",
    "ko": "Korean", "ku": "Kurdish (Kurmanji)", "ky": "Kyrgyz", "la": "Latin",
    "lb": "Luxembourgish", "lo": "Lao", "lt": "Lithuanian", "lv": "Latvian",
    "mg": "Malagasy", "mi": "Maori", "mk": "Macedonian", "ml": "Malayalam",
    "mn": "Mongolian", "mr": "Marathi", "ms": "Malay", "mt": "Maltese",
    "my": "Myanmar (Burmese)", "ne": "Nepali", "nl": "Dutch", "no": "Norwegian",
    "ny": "Chichewa", "pa": "Punjabi", "pl": "Polish", "ps": "Pashto",
    "pt": "Portuguese", "ro": "Romanian", "ru": "Russian", "sd": "Sindhi",
    "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian", "sm": "Samoan",
    "sn": "Shona", "so": "Somali", "sq": "Albanian", "sr": "Serbian",
    "st": "Sesotho", "su": "Sundanese", "sv": "Swedish", "sw": "Swahili",
    "ta": "Tamil", "te": "Telugu", "tg": "Tajik", "th": "Thai",
    "tl": "Filipino", "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu",
    "uz": "Uzbek", "vi": "Vietnamese", "xh": "Xhosa", "yi": "Yiddish",
    "yo": "Yoruba", "zh": "Chinese", "zh-TW": "Chinese (Traditional)",
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
