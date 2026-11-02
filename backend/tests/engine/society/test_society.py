from sqlalchemy import select

from aerona.db.tables.entities import EntityFlagRow
from aerona.db.tables.lore import LexemeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityType
from aerona.domain.models.entity_stats import LanguageStats
from aerona.engine.phases.society import language_and_faith, love_and_rivalry, uprisings
from aerona.engine.primitives.first_bonds import bind_language_and_faith
from aerona.engine.primitives.stats import stat
from tests.engine.society.factories import Realm, active_bonds, bonded, chronicle_keys, context, link, make, mortal, named, people, settlement, son, tuned


async def test_bootstrap_adopts_nearest_language_and_first_faith(realm: Realm) -> None:
    elders = await people(realm, "Elders")
    tongue = await make(realm.session, "Elder Speech", EntityType.LANGUAGE, LanguageStats(spread=30), world_id=realm.world.id)
    await link(realm.session, elders.id, tongue.id, BondKind.SPEAKS)
    god = await son(realm.session, "Hearth", realm.world.id)
    await link(realm.session, elders.id, god.id, BondKind.WORSHIPS)
    newcomers = await people(realm, "Newcomers")
    ctx = context(realm.session, tuned(deep_life={"first_faith_chance": 100}))
    await language_and_faith(ctx)
    assert await bonded(realm.session, newcomers.id, tongue.id, BondKind.SPEAKS)
    assert await bonded(realm.session, newcomers.id, god.id, BondKind.WORSHIPS)


async def test_lonely_people_invent_a_tongue_and_seek_a_god(realm: Realm) -> None:
    hermits = await people(realm, "Hermits")
    ctx = context(realm.session, tuned(deep_life={"first_faith_chance": 100}, deep_world={"new_people_worship_creator_chance": 0}))
    binding = await bind_language_and_faith(ctx, hermits)
    assert binding.new_language and binding.seeking
    languages = await named(realm.session, EntityType.LANGUAGE)
    assert languages[0].engine_kind is EngineKind.PRIMITIVE_LANGUAGE
    words = list(await realm.session.scalars(select(LexemeRow.word).where(LexemeRow.language_entity_id == languages[0].id)))
    assert words
    assert await realm.session.get(EntityFlagRow, (hermits.id, EntityFlag.SEEKING_GOD)) is not None
    keys = await chronicle_keys(realm.session)
    assert "settling.primitive_language" in keys
    assert "settling.seeking_god" in keys


async def test_poverty_raises_rebels(realm: Realm) -> None:
    city = await settlement(realm, "Slums", population=9000, prosperity=5)
    ctx = context(realm.session, tuned(society={"poverty_revolt_chance": 100}))
    await uprisings(ctx)
    rebels = await named(realm.session, EntityType.FACTION)
    assert len(rebels) == 1
    assert rebels[0].engine_kind is EngineKind.REBELS
    assert await bonded(realm.session, rebels[0].id, city.id, BondKind.ENEMY)
    assert stat(city, "prosperity") == max(0, 5 - ctx.rules.society.poverty_revolt_prosperity_loss)
    assert "society.poverty_uprising" in await chronicle_keys(realm.session)


async def test_co_located_adults_fall_in_love_or_rivalry(realm: Realm) -> None:
    town = await settlement(realm, "Meeting")
    first = await mortal(realm, "Ari", location_id=town.id)
    second = await mortal(realm, "Bo", location_id=town.id)
    await mortal(realm, "Child", location_id=town.id, age=3)
    await mortal(realm, "Faraway", location_id=realm.far_region.id)
    ctx = context(realm.session, tuned(society={"love_rivalry_chance": 100, "love_share_pct": 100}))
    await love_and_rivalry(ctx)
    assert await bonded(realm.session, first.id, second.id, BondKind.LOVES)
    assert ctx.environment.stats.counters["test.pairs"] == 1
    assert not await active_bonds(realm.session, second.id, BondKind.ENEMY)
