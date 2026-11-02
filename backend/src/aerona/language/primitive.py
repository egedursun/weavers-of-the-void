from dataclasses import dataclass

from aerona.constants.language import PRIMITIVE_FALLBACK_ENDINGS, PRIMITIVE_ROOT_MEANINGS, PRIMITIVE_WORD_SEED_PREFIX
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.language.alphabet import first_word
from aerona.language.generator import NameKind, NamingVoice, generate_name
from aerona.language.lexicon import LexiconEntry
from aerona.language.similarity import NamePool
from aerona.language.syllables import syllabify
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class PrimitiveLanguagePlan:
    name: str
    spread: int
    complexity: int
    sacredness: int
    words: tuple[LexiconEntry, ...]


def primitive_language_name(community_name: str) -> str:
    return f"{first_word(community_name) or community_name} Language"


def primitive_words(voice: NamingVoice, community_name: str, pool: NamePool, rules: Rules) -> tuple[LexiconEntry, ...]:
    syllables = syllabify(first_word(community_name)) or [PRIMITIVE_FALLBACK_ENDINGS[0]]
    words: list[LexiconEntry] = []
    for index, meaning in enumerate(PRIMITIVE_ROOT_MEANINGS):
        generated = generate_name(voice, f"{PRIMITIVE_WORD_SEED_PREFIX}:{index}", NameKind.GENERAL, pool, rules)
        word = generated.lower() if generated else syllables[index % len(syllables)] + PRIMITIVE_FALLBACK_ENDINGS[index]
        words.append(LexiconEntry(word=word, meaning=meaning, part_of_speech=PartOfSpeech.NOUN, origin="first sounds"))
    return tuple(words)


def plan_primitive_language(voice: NamingVoice, community_name: str, pool: NamePool, rules: Rules) -> PrimitiveLanguagePlan:
    life = rules.deep_life
    return PrimitiveLanguagePlan(
        name=primitive_language_name(community_name),
        spread=life.primitive_language_spread,
        complexity=life.primitive_language_complexity,
        sacredness=life.primitive_language_sacredness,
        words=primitive_words(voice, community_name, pool, rules),
    )
