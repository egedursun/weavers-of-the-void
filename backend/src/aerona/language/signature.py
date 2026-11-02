from aerona.constants.language import SIGNATURE_LENGTH_BIAS_CHOICES, SIGNATURE_SEED_PREFIX
from aerona.constants.units import PERCENT
from aerona.core.keyed_random import Mulberry32, keyed_random
from aerona.domain.models.phonology import LanguageSignature
from aerona.language.alphabet import is_consonant, is_vowel, strip_leading_consonants
from aerona.language.phonology import Phonology
from aerona.rules.registry import Rules


def _distinct(characters: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for character in characters:
        seen.setdefault(character, None)
    return list(seen)


def _inherit(parent: LanguageSignature, consonants: list[str], vowels: list[str], random: Mulberry32, rules: Rules) -> LanguageSignature:
    inherited = list(parent.consonants)
    newcomers = [character for character in consonants if character not in inherited]
    if newcomers and len(inherited) > rules.language.inherited_shift_min_consonants:
        position = random.below(len(inherited))
        inherited[position] = newcomers[random.below(len(newcomers))]
    ending = ""
    if parent.ending:
        replacement = vowels[random.below(len(vowels))]
        ending = parent.ending
        for index, character in enumerate(ending):
            if is_vowel(character):
                ending = ending[:index] + replacement + ending[index + 1 :]
                break
    return LanguageSignature(consonants="".join(_distinct(inherited)), cluster=parent.cluster, ending=ending, length_bias=parent.length_bias)


def _fresh(phonology: Phonology, consonants: list[str], vowels: list[str], random: Mulberry32, rules: Rules) -> LanguageSignature:
    settings = rules.language
    joined = "".join(phonology.syllable_types())
    frequency = {character: joined.count(character) for character in consonants}
    ranked = sorted(consonants, key=lambda character: -frequency[character])
    chosen = [
        character
        for index, character in enumerate(ranked)
        if index < settings.signature_kept_consonants or random() < settings.signature_consonant_pct / PERCENT
    ]
    floor = min(settings.signature_consonant_floor, len(ranked))
    for character in ranked:
        if len(chosen) >= floor:
            break
        if character not in chosen:
            chosen.append(character)
    first = chosen[random.below(len(chosen))]
    others = [character for character in chosen if character != first]
    second_index = random.below(len(chosen) - 1)
    second = others[second_index] if second_index < len(others) else ""
    allowed = set(chosen)
    endings = [ending for ending in phonology.final if all(character in allowed for character in ending if is_consonant(character))]
    ending = strip_leading_consonants(endings[random.below(len(endings))]) if endings else vowels[0] + chosen[0]
    length_bias = random.below(SIGNATURE_LENGTH_BIAS_CHOICES) - 1
    return LanguageSignature(
        consonants="".join(chosen),
        cluster=first + second if first and second else "",
        ending=ending[: settings.signature_ending_max_letters],
        length_bias=length_bias,
    )


__all__ = ["LanguageSignature", "derive_signature"]


def derive_signature(language_key: str, phonology: Phonology, parent: LanguageSignature | None, rules: Rules) -> LanguageSignature | None:
    random = keyed_random(f"{SIGNATURE_SEED_PREFIX}:{language_key}")
    joined = "".join(phonology.syllable_types())
    consonants = _distinct([character for character in joined if is_consonant(character)])
    vowels = _distinct([character for character in joined if is_vowel(character)])
    if len(consonants) < rules.language.signature_min_consonants or not vowels:
        return None
    if parent is not None:
        return _inherit(parent, consonants, vowels, random, rules)
    return _fresh(phonology, consonants, vowels, random, rules)
