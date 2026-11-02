from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from aerona.constants.language import EPOCH_WORD_SEED_PREFIX
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.entity import EntityType
from aerona.language.alphabet import first_word
from aerona.language.lexicon import LexiconEntry
from aerona.rules.registry import Rules

EPOCH_WORD_TYPES = (
    EntityType.PLACE,
    EntityType.SETTLEMENT,
    EntityType.MORTAL,
    EntityType.EVENT,
    EntityType.KNOWLEDGE,
    EntityType.SPECIES,
    EntityType.ITEM,
    EntityType.STRUCTURE,
    EntityType.TRADITION,
    EntityType.LEGEND,
    EntityType.RESOURCE,
)

PROPER_NOUN_TYPES = frozenset({EntityType.PLACE, EntityType.SETTLEMENT, EntityType.MORTAL})

ENTITY_TYPE_LABELS: dict[EntityType, str] = {
    EntityType.PLACE: "place",
    EntityType.SETTLEMENT: "settlement",
    EntityType.MORTAL: "mortal",
    EntityType.EVENT: "event",
    EntityType.KNOWLEDGE: "knowledge",
    EntityType.SPECIES: "species",
    EntityType.ITEM: "item",
    EntityType.STRUCTURE: "structure",
    EntityType.TRADITION: "tradition",
    EntityType.LEGEND: "legend",
    EntityType.RESOURCE: "resource",
}


@dataclass(frozen=True)
class EpochWordSource:
    entity_id: int
    entity_type: EntityType
    name: str
    subtype: str | None
    language_id: int | None
    named_from_language: bool = False
    already_recorded: bool = False


@dataclass(frozen=True)
class EpochWord:
    language_id: int
    entity_id: int
    entry: LexiconEntry


WordMaker = Callable[[int, str], str | None]


def epoch_word_meaning(entity_type: EntityType, name: str, subtype: str | None) -> str:
    templates: dict[EntityType, str] = {
        EntityType.PLACE: f"{subtype or 'place'}: {name}",
        EntityType.SETTLEMENT: f"{name} city; those who live there",
        EntityType.MORTAL: f"one who is like {name}; {subtype or 'person'}",
        EntityType.EVENT: f"{subtype or 'event'}; a calamity or turning point like {name}",
        EntityType.KNOWLEDGE: f"knowledge of {name}; one who knows it",
        EntityType.SPECIES: f"the creature called {name}",
        EntityType.ITEM: f"{name}; {subtype or 'item'}",
        EntityType.STRUCTURE: f"{name}; {subtype or 'structure'}",
        EntityType.TRADITION: f"{name} day; that rite",
        EntityType.LEGEND: f"the tale of {name}",
        EntityType.RESOURCE: f"{subtype or 'resource'}: {name}",
    }
    return templates.get(entity_type, name)


def epoch_word_origin(epoch: int, name: str, entity_type: EntityType) -> str:
    label = ENTITY_TYPE_LABELS.get(entity_type, entity_type.value)
    return f"Entered the language in Epoch {epoch} when {name} ({label}) was born"


def plan_epoch_words(
    sources: Sequence[EpochWordSource],
    epoch: int,
    make_word: WordMaker,
    known_words: Mapping[int, set[str]],
    rules: Rules,
) -> list[EpochWord]:
    settings = rules.language
    per_language: dict[int, int] = {}
    seen = {language: {word.casefold() for word in words} for language, words in known_words.items()}
    planned: list[EpochWord] = []
    for source in sources:
        if len(planned) >= settings.epoch_words_total:
            break
        language = source.language_id
        if language is None or source.entity_type not in ENTITY_TYPE_LABELS or source.already_recorded:
            continue
        if per_language.get(language, 0) >= settings.epoch_words_per_language:
            continue
        generated = first_word(source.name) if source.named_from_language else make_word(language, f"{EPOCH_WORD_SEED_PREFIX}:{source.entity_id}")
        word = (generated or "").lower()
        if len(word) < settings.epoch_word_min_letters or word.casefold() in seen.setdefault(language, set()):
            continue
        seen[language].add(word.casefold())
        per_language[language] = per_language.get(language, 0) + 1
        part = PartOfSpeech.PROPER_NAME if source.entity_type in PROPER_NOUN_TYPES else PartOfSpeech.NOUN
        entry = LexiconEntry(
            word=word,
            meaning=epoch_word_meaning(source.entity_type, source.name, source.subtype),
            part_of_speech=part,
            origin=epoch_word_origin(epoch, source.name, source.entity_type),
        )
        planned.append(EpochWord(language_id=language, entity_id=source.entity_id, entry=entry))
    return planned
