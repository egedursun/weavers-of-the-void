import re
import unicodedata
from functools import cache

from aerona.constants.language import CONLANG_CONSONANTS, CONLANG_VOWELS, UNICODE_LETTER_MARKER, UNICODE_MODIFIER_MARKER

VOWELS = frozenset(CONLANG_VOWELS)
CONSONANTS = frozenset(CONLANG_CONSONANTS)
LETTERS = VOWELS | CONSONANTS
CONLANG_VOWEL_CLASS = re.escape(CONLANG_VOWELS)


def is_vowel(character: str) -> bool:
    return character in VOWELS


def is_consonant(character: str) -> bool:
    return character in CONSONANTS


@cache
def fold_letter(character: str) -> str:
    lowered = character.lower()
    if len(lowered) == 1 and lowered in LETTERS:
        return lowered
    decomposed = unicodedata.normalize("NFKD", lowered)
    if decomposed and decomposed[0] in LETTERS:
        return decomposed[0]
    name = unicodedata.name(lowered[:1], "") if lowered else ""
    words = name.split()
    if UNICODE_LETTER_MARKER not in words:
        return ""
    tail = words[words.index(UNICODE_LETTER_MARKER) + 1 :]
    if UNICODE_MODIFIER_MARKER in tail:
        tail = tail[: tail.index(UNICODE_MODIFIER_MARKER)]
    for word in reversed(tail):
        candidate = word.lower()
        if len(candidate) == 1 and candidate in LETTERS:
            return candidate
    return ""


def fold_word(word: str) -> str:
    return "".join(fold_letter(character) for character in word)


def leading_consonants(text: str) -> str:
    index = 0
    while index < len(text) and not is_vowel(text[index]):
        index += 1
    return text[:index]


def strip_leading_consonants(text: str) -> str:
    return text[len(leading_consonants(text)) :]


def first_word(text: str) -> str:
    parts = text.split()
    return parts[0] if parts else ""


def capitalize_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def strip_diacritics(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(character for character in decomposed if not unicodedata.combining(character))
