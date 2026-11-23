import math
import re
from dataclasses import dataclass
from enum import StrEnum

from aerona.constants.language import SYLLABLE_ECHO_LETTERS
from aerona.constants.units import PERCENT, TENTHS
from aerona.core.keyed_random import Mulberry32, keyed_random
from aerona.language.alphabet import CONLANG_VOWEL_CLASS, capitalize_first, leading_consonants
from aerona.language.phonology import Phonology, SyllableCounts, restrict_to_consonants, weighted_pick
from aerona.language.signature import LanguageSignature
from aerona.language.similarity import NamePool
from aerona.language.ugliness import is_ugly_name
from aerona.rules.registry import Rules

VOWEL_CONSONANT_VOWEL = re.compile(f"([{CONLANG_VOWEL_CLASS}])([^{CONLANG_VOWEL_CLASS}])([{CONLANG_VOWEL_CLASS}])")
REPEATED_VOWEL = re.compile(f"([{CONLANG_VOWEL_CLASS}])\\1+")
REPEATED_CONSONANT = re.compile(f"([^{CONLANG_VOWEL_CLASS}\\s])\\1+")


class NameKind(StrEnum):
    PERSON = "person"
    PLACE = "place"
    PEOPLE = "people"
    ARMY = "army"
    GENERAL = "general"
    SEASON = "season"


@dataclass(frozen=True)
class NamingVoice:
    language_key: str
    phonology: Phonology
    signature: LanguageSignature | None = None


def _round_half_up(value: float) -> int:
    return math.floor(value + 0.5)


def _syllable_bias(kind: NameKind, rules: Rules) -> float:
    if kind is NameKind.PERSON:
        return rules.language.person_syllable_bias / TENTHS
    if kind in (NameKind.PLACE, NameKind.PEOPLE):
        return rules.language.place_syllable_bias / TENTHS
    return 0.0


def _append_syllable(parts: list[str], counts: SyllableCounts, random: Mulberry32, rules: Rules) -> None:
    syllable = weighted_pick(counts, random)
    previous = parts[-1]
    for _ in range(rules.language.syllable_repeat_retries):
        if syllable != previous and syllable[:SYLLABLE_ECHO_LETTERS] != previous[:SYLLABLE_ECHO_LETTERS]:
            break
        syllable = weighted_pick(counts, random)
    parts.append(syllable)


def _compose(voice: NamingVoice, kind: NameKind, random: Mulberry32, rules: Rules) -> str:
    settings = rules.language
    phonology = voice.phonology
    signature = voice.signature
    consonants = signature.consonants if signature else ""
    length_bias = signature.length_bias if signature else 0
    jitter = random() - 0.5
    raw_target = phonology.average_syllables + _syllable_bias(kind, rules) + length_bias * settings.signature_length_bias_weight / TENTHS + jitter
    target = max(settings.name_min_syllables, min(settings.name_max_syllables, _round_half_up(raw_target)))
    initial = restrict_to_consonants(phonology.initial, consonants)
    medial = restrict_to_consonants(phonology.medial or phonology.initial, consonants)
    final = restrict_to_consonants(phonology.final or phonology.initial, consonants)
    parts = [weighted_pick(initial, random)]
    for _ in range(1, target - 1):
        _append_syllable(parts, medial, random, rules)
    if target > 1:
        _append_syllable(parts, final, random, rules)
    if signature and signature.ending and target > 1 and random() < settings.signature_ending_pct / PERCENT:
        parts[-1] = leading_consonants(parts[-1]) + signature.ending
    name = "".join(parts)
    if signature and signature.cluster and random() < settings.signature_cluster_pct / PERCENT:
        name = VOWEL_CONSONANT_VOWEL.sub(lambda match: match.group(1) + signature.cluster + match.group(3), name, count=1)
    name = REPEATED_VOWEL.sub(r"\1", name)
    return REPEATED_CONSONANT.sub(r"\1", name)


def generate_name(voice: NamingVoice, seed: str, kind: NameKind, pool: NamePool, rules: Rules) -> str | None:
    settings = rules.language
    if voice.phonology.is_empty:
        return None
    fallback: str | None = None
    for attempt in range(settings.name_attempts):
        random = keyed_random(f"{voice.language_key}:{kind.value}:{seed}:{attempt}")
        name = _compose(voice, kind, random, rules)
        if len(name) < settings.name_min_letters or len(name) > settings.name_max_letters:
            continue
        name = capitalize_first(name)
        if pool.is_taken(name) or is_ugly_name(name, rules):
            continue
        if pool.similar_to(name, family=True) is not None:
            fallback = fallback or name
            continue
        return name
    return fallback
