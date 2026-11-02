from collections.abc import Sequence
from dataclasses import dataclass

from aerona.constants.language import LANGUAGE_LABEL_SUFFIXES, LANGUAGE_LABEL_WORDS
from aerona.constants.units import PER_MILLE
from aerona.language.alphabet import first_word, fold_word
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class CorpusSources:
    world_name: str
    lexicon_words: Sequence[str] = ()
    language_name: str | None = None
    naming_samples: Sequence[str] = ()
    speaker_names: Sequence[str] = ()
    world_names: Sequence[str] = ()


def is_language_label(token: str, world_name: str, rules: Rules) -> bool:
    lowered = token.lower()
    if not lowered:
        return True
    if lowered.endswith(LANGUAGE_LABEL_SUFFIXES) or any(word in lowered for word in LANGUAGE_LABEL_WORDS):
        return True
    root_letters = rules.language.root_letters
    world_root = fold_word(first_word(world_name))[:root_letters]
    return bool(world_root) and fold_word(lowered)[:root_letters] == world_root


def assemble_corpus(sources: CorpusSources, rules: Rules) -> list[str]:
    settings = rules.language
    corpus = [word for word in sources.lexicon_words if word.strip()]
    if sources.language_name:
        token = first_word(sources.language_name)
        if not is_language_label(token, sources.world_name, rules):
            corpus.append(token)
    if len(corpus) < settings.phonology_min_words:
        corpus.extend(sample for sample in sources.naming_samples[: settings.dialect_sample_names] if sample.strip())
    if len(corpus) < settings.phonology_min_words:
        corpus.extend(first_word(name) for name in sources.speaker_names if first_word(name))
    if len(corpus) < settings.phonology_min_words:
        for name in sources.world_names[: settings.phonology_fallback_names]:
            token = first_word(name)
            if token and not is_language_label(token, sources.world_name, rules):
                corpus.append(token)
    return corpus


def world_alphabet(words: Sequence[str], rules: Rules) -> frozenset[str] | None:
    settings = rules.language
    counts: dict[str, int] = {}
    for word in words:
        for letter in fold_word(word):
            counts[letter] = counts.get(letter, 0) + 1
    total = sum(counts.values())
    if total < settings.alphabet_min_samples:
        return None
    return frozenset(letter for letter, count in counts.items() if count * PER_MILLE >= settings.alphabet_min_per_mille * total)
