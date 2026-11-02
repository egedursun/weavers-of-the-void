from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field

from aerona.constants.language import MIN_SIGNATURE_FILTERED_SYLLABLES
from aerona.constants.units import TENTHS
from aerona.language.alphabet import fold_word, is_consonant
from aerona.language.syllables import syllabify
from aerona.rules.registry import Rules

SyllableCounts = Mapping[str, int]
UnitRandom = Callable[[], float]


@dataclass(frozen=True)
class Phonology:
    initial: SyllableCounts = field(default_factory=dict)
    medial: SyllableCounts = field(default_factory=dict)
    final: SyllableCounts = field(default_factory=dict)
    average_syllables: float = 0.0
    word_count: int = 0

    @property
    def is_empty(self) -> bool:
        return not self.initial

    def syllable_types(self) -> list[str]:
        return [*self.initial, *self.medial, *self.final]


def _accepts(token: str, alphabet: frozenset[str] | None) -> bool:
    if not token or not token.isalpha():
        return False
    if alphabet is None:
        return True
    return all(character in alphabet for character in fold_word(token))


def build_phonology(corpus: Iterable[str], alphabet: frozenset[str] | None, rules: Rules) -> Phonology:
    settings = rules.language
    words = list(corpus)
    initial: dict[str, int] = {}
    medial: dict[str, int] = {}
    final: dict[str, int] = {}
    lengths: list[int] = []
    for entry in words:
        for token in entry.split():
            if not _accepts(token, alphabet):
                continue
            syllables = syllabify(token)
            if not syllables or len(syllables) > settings.phonology_max_syllables:
                continue
            lengths.append(len(syllables))
            initial[syllables[0]] = initial.get(syllables[0], 0) + 1
            if len(syllables) > 1:
                final[syllables[-1]] = final.get(syllables[-1], 0) + 1
            for syllable in syllables[1:-1]:
                medial[syllable] = medial.get(syllable, 0) + 1
    average = sum(lengths) / len(lengths) if lengths else settings.default_avg_syllables / TENTHS
    return Phonology(initial=initial, medial=medial, final=final, average_syllables=average, word_count=len(words))


def weighted_pick(counts: SyllableCounts, random: UnitRandom) -> str:
    if not counts:
        return ""
    remaining = random() * sum(counts.values())
    for key, weight in counts.items():
        remaining -= weight
        if remaining <= 0:
            return key
    return next(iter(counts))


def consonants_of(text: str) -> list[str]:
    return [character for character in text if is_consonant(character)]


def restrict_to_consonants(counts: SyllableCounts, consonants: str) -> SyllableCounts:
    if not consonants:
        return counts
    allowed = set(consonants)
    kept = {key: weight for key, weight in counts.items() if all(character in allowed for character in consonants_of(key))}
    return kept if len(kept) >= MIN_SIGNATURE_FILTERED_SYLLABLES else counts
