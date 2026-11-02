from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.models.entity_stats import LanguageStats, PeopleStats, SettlementStats
from aerona.engine.primitives.language_profile import DEFAULT_PHONOLOGY
from aerona.engine.primitives.naming import Namer
from aerona.epoch.phases.transition import add_epoch_words
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region

WORDS = ["karvelon", "tirnasul", "morvekan", "salterin", "veldranor", "kormalis", "tarvenik", "silmorak", "nerovat", "varkelith", "dorsimal", "lanterik"]


async def language(session: AsyncSession, cosmos: Cosmos, name: str, parent: EntityRow | None = None, words: list[str] | None = None) -> EntityRow:
    entity = await make_entity(session, name, EntityType.LANGUAGE, LanguageStats(spread=10), world_id=cosmos.home.id)
    phonology = DEFAULT_PHONOLOGY.model_copy(update={"sample_names": ("Kelar", "Mirnar")})
    session.add(LanguageProfileRow(entity_id=entity.id, phonology=phonology, seed=name, parent_language_id=parent.id if parent is not None else None))
    for word in words or []:
        session.add(LexemeRow(language_entity_id=entity.id, word=word, meaning="thing", added_by_kind=ActorKind.ENGINE, epoch=1))
    await session.flush()
    return entity


async def test_voice_uses_ancestor_lexicon_persists_and_inherits_signature(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ancestor = await language(session, cosmos, "Old Tarnic", words=WORDS)
    child = await language(session, cosmos, "Young Tarnic", parent=ancestor)
    namer = Namer(session, rules)
    ancestor_voice = await namer.voice(ancestor)
    child_voice = await namer.voice(child)
    assert ancestor_voice.signature is not None and child_voice.signature is not None
    assert not child_voice.phonology.is_empty
    stored = await session.get(LanguageProfileRow, ancestor.id)
    assert stored is not None and stored.signature == ancestor_voice.signature
    again = await Namer(session, rules).voice(ancestor)
    assert again.signature == ancestor_voice.signature
    assert set(child_voice.signature.consonants) - set(ancestor_voice.signature.consonants) <= set("bcdfghjklmnpqrstvwxyz")


async def test_dialect_samples_seed_a_thin_corpus(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    thin = await language(session, cosmos, "Thin Tongue")
    voice = await Namer(session, rules).voice(thin)
    assert not voice.phonology.is_empty


async def test_epoch_words_keep_the_strongest_records_in_the_local_language(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    first = await language(session, cosmos, "Tarnic", words=WORDS)
    second = await language(session, cosmos, "Velic", words=WORDS)
    region = await make_region(session, "Vale", cosmos.home.id)
    people = await make_entity(session, "Velfolk", EntityType.PEOPLE, PeopleStats(population=900), world_id=cosmos.home.id, location_id=region.id)
    await BondRepository(session).connect(BondDraft(people.id, second.id, BondKind.SPEAKS, 1, "tongue"))
    weak = await make_entity(
        session, "Lowtown", EntityType.SETTLEMENT, SettlementStats(population=100), world_id=cosmos.home.id, location_id=region.id, power=1
    )
    strong = await make_entity(
        session, "Hightown", EntityType.SETTLEMENT, SettlementStats(population=100), world_id=cosmos.home.id, location_id=region.id, power=9
    )
    for record in (weak, strong):
        record.birth_epoch = 5
    await session.flush()
    capped = replace(rules, language=replace(rules.language, epoch_words_per_language=1, epoch_word_min_letters=1))
    added = await add_epoch_words(session, capped, 5)
    assert added == 1
    entry = await session.scalar(select(LexemeRow).where(LexemeRow.added_by_node_id.is_not(None)))
    assert entry is not None and entry.added_by_node_id == strong.id
    assert entry.language_entity_id == second.id and first.id != second.id
