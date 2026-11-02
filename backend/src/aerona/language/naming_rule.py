import re
from collections.abc import Collection

from pydantic import BaseModel, ConfigDict

from aerona.language.alphabet import fold_word, is_consonant, is_vowel
from aerona.rules.registry import Rules

WORD_SEPARATORS = re.compile("[\\s,'\\u2019\\-]+")


class NamingRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    vowels: str = ""
    consonants: str = ""
    forbidden_sounds: tuple[str, ...] = ()
    sample_names: tuple[str, ...] = ()
    endings: tuple[str, ...] = ()

    def allows_letter(self, letter: str) -> bool:
        if is_vowel(letter):
            return not self.vowels or letter in self.vowels
        if is_consonant(letter):
            return not self.consonants or letter in self.consonants
        return True

    def alphabet(self) -> frozenset[str] | None:
        if not self.vowels or not self.consonants:
            return None
        return frozenset(self.vowels + self.consonants)


class NamingViolation(BaseModel):
    model_config = ConfigDict(frozen=True)

    word: str
    forbidden_letters: tuple[str, ...] = ()
    forbidden_sounds: tuple[str, ...] = ()


def naming_violations(name: str, rule: NamingRule, ordinary_words: Collection[str], rules: Rules) -> list[NamingViolation]:
    settings = rules.language
    ordinary = {fold_word(word) for word in ordinary_words}
    ordinary_roots = {word[: settings.root_letters] for word in ordinary if len(word) >= settings.root_letters}
    violations: list[NamingViolation] = []
    for raw in WORD_SEPARATORS.split(name):
        word = fold_word(raw)
        if len(word) < settings.dialect_root_min_letters or word in ordinary or word[: settings.root_letters] in ordinary_roots:
            continue
        letters = tuple(dict.fromkeys(letter for letter in word if not rule.allows_letter(letter)))
        sounds = tuple(sound for sound in rule.forbidden_sounds if sound and fold_word(sound) in word)
        if letters or sounds:
            violations.append(NamingViolation(word=raw, forbidden_letters=letters, forbidden_sounds=sounds))
    return violations
