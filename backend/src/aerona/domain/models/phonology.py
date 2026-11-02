from pydantic import Field

from aerona.domain.enums.world import LanguageTexture
from aerona.domain.models.base import ValueObject


class Phonology(ValueObject):
    vowels: tuple[str, ...] = Field(min_length=1)
    consonants: tuple[str, ...] = Field(min_length=1)
    forbidden_sounds: tuple[str, ...] = ()
    onsets: tuple[str, ...] = ()
    codas: tuple[str, ...] = ()
    syllable_patterns: tuple[str, ...] = Field(min_length=1)
    preferred_endings: tuple[str, ...] = ()
    texture: LanguageTexture = LanguageTexture.FREE
    min_syllables: int = Field(ge=1)
    max_syllables: int = Field(ge=1)
    sample_names: tuple[str, ...] = ()

    def allows_vowel(self, vowel: str) -> bool:
        return vowel.casefold() in {item.casefold() for item in self.vowels}

    def forbidden_in(self, word: str) -> tuple[str, ...]:
        folded = word.casefold()
        return tuple(sound for sound in self.forbidden_sounds if sound.casefold() in folded)


class LanguageSignature(ValueObject):
    consonants: str
    cluster: str = ""
    ending: str = ""
    length_bias: int = 0
