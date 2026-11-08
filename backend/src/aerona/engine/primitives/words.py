import re
from collections.abc import Iterable
from functools import cache

ENDINGS = r"(?:s|es)?"


@cache
def word_pattern(word: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![^\W\d_]){re.escape(word)}{ENDINGS}(?![^\W\d_])")


def names_word(text: str, words: Iterable[str]) -> bool:
    return any(word_pattern(word.casefold()).search(text.casefold()) for word in words)
