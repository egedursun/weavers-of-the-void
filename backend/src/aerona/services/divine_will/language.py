from collections.abc import Sequence

import pycountry
from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

SURE = 0.9
FEWEST_WORDS = 5

DetectorFactory.seed = 0


def worded(text: str) -> int:
    return sum(1 for word in text.split() if any(letter.isalpha() for letter in word))


def sure_language(text: str) -> str:
    if worded(text) < FEWEST_WORDS:
        return ""
    try:
        found = detect_langs(text)
    except LangDetectException:
        return ""
    best = found[0] if found else None
    return language_name(best.lang) if best is not None and best.prob >= SURE else ""


def language_name(code: str) -> str:
    found = pycountry.languages.get(alpha_2=code.split("-", maxsplit=1)[0])
    return str(found.name) if found is not None else ""


def player_language(current: str, earlier: Sequence[str]) -> str:
    return sure_language(current) or sure_language("\n".join([*earlier, current]))


def strays_from(text: str, wanted: str) -> bool:
    parts = [part for part in text.split("\n") if part.strip()]
    found = {sure_language(part) for part in [text, *parts]}
    return any(language and language != wanted for language in found)
