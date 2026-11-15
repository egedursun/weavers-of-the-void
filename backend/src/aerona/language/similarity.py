from collections.abc import Iterable
from functools import lru_cache

from aerona.constants.language import FIRST_UNIQUE_SUFFIX_NUMBER, NAME_SIMILARITY_FAR, ROMAN_NUMERAL_LIMIT, ROMAN_NUMERALS
from aerona.language.alphabet import strip_diacritics
from aerona.rules.registry import Rules

NORMALIZED_NAMES = 65536


@lru_cache(maxsize=NORMALIZED_NAMES)
def normalize_name(name: str) -> str:
    return strip_diacritics(name.strip().casefold())


def letter_distance(first: str, second: str) -> int:
    left = normalize_name(first)
    right = normalize_name(second)
    if abs(len(left) - len(right)) > 1:
        return NAME_SIMILARITY_FAR
    previous = list(range(len(right) + 1))
    for row, left_character in enumerate(left, start=1):
        current = [row]
        for column, right_character in enumerate(right, start=1):
            cost = 0 if left_character == right_character else 1
            current.append(min(previous[column] + 1, current[column - 1] + 1, previous[column - 1] + cost))
        previous = current
    return previous[-1]


def within_one_edit(left: str, right: str) -> bool:
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) > len(right):
        left, right = right, left
    index = 0
    while index < len(left) and left[index] == right[index]:
        index += 1
    if len(left) == len(right):
        return left[index + 1 :] == right[index + 1 :]
    return left[index:] == right[index + 1 :]


def roman_numeral(number: int) -> str:
    remaining = max(1, min(number, ROMAN_NUMERAL_LIMIT))
    parts: list[str] = []
    for value, symbol in ROMAN_NUMERALS:
        while remaining >= value:
            parts.append(symbol)
            remaining -= value
    return "".join(parts)


def _is_single_word(name: str) -> bool:
    return len(name.split()) == 1


class NamePool:
    def __init__(self, names: Iterable[str], rules: Rules) -> None:
        self._rules = rules
        self._normalized: set[str] = set()
        self._by_length: dict[int, list[str]] = {}
        self._families: dict[str, list[str]] = {}
        for name in names:
            self.add(name)

    def add(self, name: str) -> None:
        normalized = normalize_name(name)
        if not normalized or normalized in self._normalized:
            return
        self._normalized.add(normalized)
        if not _is_single_word(normalized):
            return
        self._by_length.setdefault(len(normalized), []).append(name)
        root_letters = self._rules.language.root_letters
        if len(normalized) >= root_letters:
            self._families.setdefault(normalized[:root_letters], []).append(name)

    def is_taken(self, name: str) -> bool:
        return normalize_name(name) in self._normalized

    def similar_to(self, name: str, family: bool = True) -> str | None:
        settings = self._rules.language
        normalized = normalize_name(name)
        if not normalized or not _is_single_word(normalized):
            return None
        if len(normalized) <= settings.similar_name_max_length:
            for length in (len(normalized) - 1, len(normalized), len(normalized) + 1):
                if length > settings.similar_name_max_length + 1:
                    continue
                for existing in self._by_length.get(length, ()):
                    known = normalize_name(existing)
                    if known != normalized and within_one_edit(known, normalized):
                        return existing
        if family and len(normalized) >= settings.root_letters:
            relatives = self._families.get(normalized[: settings.root_letters], [])
            if len(relatives) >= settings.name_family_cap:
                return relatives[0]
        return None

    def unique(self, name: str) -> str:
        base = name.strip()
        if not self.is_taken(base):
            return base
        number = FIRST_UNIQUE_SUFFIX_NUMBER
        while self.is_taken(f"{base} {roman_numeral(number)}"):
            number += 1
        return f"{base} {roman_numeral(number)}"
