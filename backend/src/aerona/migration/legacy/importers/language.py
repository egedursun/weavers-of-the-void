from collections import Counter
from collections.abc import Iterable

from sqlalchemy import select

from aerona.constants.migration import NAME_CORPUS_LIMIT, SAMPLE_NAME_LIMIT, SYLLABLE_PATTERN_FALLBACK
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.models.phonology import Phonology
from aerona.engine.primitives.language_profile import DEFAULT_PHONOLOGY
from aerona.engine.primitives.naming import seed_of
from aerona.language.alphabet import fold_word, is_consonant, is_vowel
from aerona.language.syllables import syllabify
from aerona.migration.legacy.context import MigrationContext

PLACE_TYPES = (EntityType.REGION, EntityType.PLACE, EntityType.SETTLEMENT, EntityType.PEOPLE)
CONSONANT_MARK = "C"
VOWEL_MARK = "V"
PATTERN_LIMIT = 4
ENDING_LIMIT = 6
SPEECH_BONDS = (BondKind.SPEAKS,)


def _shape(syllable: str) -> str:
    marks: list[str] = []
    for character in syllable:
        mark = VOWEL_MARK if is_vowel(character) else CONSONANT_MARK if is_consonant(character) else ""
        if mark and (not marks or marks[-1] != mark or mark == CONSONANT_MARK):
            marks.append(mark)
    return "".join(marks)


def derive_phonology(words: Iterable[str]) -> Phonology | None:
    vowels: Counter[str] = Counter()
    consonants: Counter[str] = Counter()
    shapes: Counter[str] = Counter()
    endings: Counter[str] = Counter()
    lengths: list[int] = []
    samples: list[str] = []
    for entry in words:
        for token in entry.split():
            folded = fold_word(token)
            if len(folded) < 2:
                continue
            syllables = syllabify(folded)
            if not syllables:
                continue
            lengths.append(len(syllables))
            vowels.update(character for character in folded if is_vowel(character))
            consonants.update(character for character in folded if is_consonant(character))
            shapes.update(shape for syllable in syllables if (shape := _shape(syllable)))
            if len(syllables) > 1:
                endings[syllables[-1]] += 1
            if len(samples) < SAMPLE_NAME_LIMIT and token[:1].isupper() and token not in samples:
                samples.append(token)
    if not vowels or not consonants or not lengths:
        return None
    return Phonology(
        vowels=tuple(letter for letter, _ in vowels.most_common()),
        consonants=tuple(letter for letter, _ in consonants.most_common()),
        syllable_patterns=tuple(shape for shape, _ in shapes.most_common(PATTERN_LIMIT)) or (SYLLABLE_PATTERN_FALLBACK,),
        preferred_endings=tuple(ending for ending, _ in endings.most_common(ENDING_LIMIT)),
        min_syllables=max(1, min(lengths)),
        max_syllables=max([1, *lengths]),
        sample_names=tuple(samples),
    )


async def _world_names(context: MigrationContext, world_id: int) -> list[str]:
    statement = (
        select(EntityRow.name)
        .where(
            EntityRow.world_id == world_id,
            EntityRow.entity_type.in_(PLACE_TYPES),
            EntityRow.status != EntityStatus.REJECTED,
            EntityRow.origin != EntityOrigin.ENGINE,
        )
        .order_by(EntityRow.id)
        .limit(NAME_CORPUS_LIMIT)
    )
    return list(await context.session.scalars(statement))


async def derive_world_phonology(context: MigrationContext) -> None:
    for world in list(await context.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        phonology = derive_phonology([world.name, *await _world_names(context, world.id)])
        world.phonology = phonology
        context.report.convert("world_phonology_derived" if phonology is not None else "world_phonology_missing")
    await context.session.flush()


async def _language_words(context: MigrationContext, language_id: int) -> list[str]:
    words = list(await context.session.scalars(select(LexemeRow.word).where(LexemeRow.language_entity_id == language_id).order_by(LexemeRow.id)))
    speakers = select(BondRow.source_node_id).where(BondRow.target_node_id == language_id, BondRow.kind.in_(SPEECH_BONDS), BondRow.state == BondState.ACTIVE)
    names = list(await context.session.scalars(select(EntityRow.name).where(EntityRow.id.in_(speakers)).order_by(EntityRow.id).limit(NAME_CORPUS_LIMIT)))
    return [*words, *names]


async def _parent_language(context: MigrationContext, language_id: int) -> int | None:
    statement = (
        select(BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(BondRow.source_node_id == language_id, BondRow.kind == BondKind.DESCENDS_FROM, EntityRow.entity_type == EntityType.LANGUAGE)
        .order_by(BondRow.id)
        .limit(1)
    )
    parent: int | None = await context.session.scalar(statement)
    return parent


async def import_language_profiles(context: MigrationContext) -> None:
    languages = [entity for entity in context.rows.values() if entity.entity_type is EntityType.LANGUAGE]
    reverse = context.ids.reverse_entities()
    for language in sorted(languages, key=lambda entity: entity.id):
        reading = context.readings.get(reverse.get(language.id, 0))
        world = await context.session.get(WorldRow, language.world_id)
        own = derive_phonology([language.name, *await _language_words(context, language.id)])
        phonology = own or (world.phonology if world is not None and world.phonology is not None else DEFAULT_PHONOLOGY)
        context.report.convert("language_phonology_derived" if own is not None else "language_phonology_inherited")
        signature = reading.signature if reading is not None else None
        script = reading.script if reading is not None else None
        if signature is not None:
            context.report.convert("language_signatures")
        if script is not None:
            context.report.convert("writing_systems")
        context.add(
            LanguageProfileRow(
                entity_id=language.id,
                phonology=phonology,
                writing_system=script,
                script_epoch=language.birth_epoch if script is not None else None,
                parent_language_id=await _parent_language(context, language.id),
                seed=seed_of("language", language.id),
                signature=signature,
            )
        )
    await context.flush()
