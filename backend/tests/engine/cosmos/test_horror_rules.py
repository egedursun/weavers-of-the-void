from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.lore import ChronicleRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import PeopleStats, PlaceStats
from aerona.engine.phases.horror import feed_madness_sons, spontaneous_horror, update_leaks, update_sanity
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_son, make_world, teach, tick, tuned


async def keys(session: AsyncSession) -> set[str]:
    return set(await session.scalars(select(ChronicleRow.template_key)))


async def test_crossing_the_warning_thresholds_writes_warning_notes(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "cosmic_horror", warning_1=1, warning_2=2, outer_being_threshold=3))
    for index in range(4):
        people = await make_entity(session, f"Folk {index}", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
        await teach(session, people, KnowledgeBranch.FORBIDDEN)
    cosmos.home.leakage = 0
    await update_leaks(ctx, await KnowledgeMap.load(session))
    assert cosmos.home.leakage >= 3
    assert {"horror.warning_first", "horror.warning_geometry", "horror.warning_tear"} <= await keys(session)


async def test_no_warning_is_repeated_once_the_threshold_is_passed(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "cosmic_horror", warning_1=1, warning_2=200, outer_being_threshold=200))
    people = await make_entity(session, "Folk", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
    await teach(session, people, KnowledgeBranch.FORBIDDEN)
    cosmos.home.leakage = 0
    await update_leaks(ctx, await KnowledgeMap.load(session))
    await update_leaks(ctx, await KnowledgeMap.load(session))
    rows = list(await session.scalars(select(ChronicleRow).where(ChronicleRow.template_key == "horror.warning_first")))
    assert len(rows) == 1


async def test_a_madness_epidemic_costs_the_community_a_share_of_its_people(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "cosmic_horror", madness_chance=100, whisperers_chance=0, madness_population_loss_pct=10))
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    people.sanity = 5
    await update_sanity(ctx, await KnowledgeMap.load(session))
    assert people.stats.population == 4500
    assert "horror.madness_epidemic" in await keys(session)


async def test_sons_of_madness_feed_on_the_average_leak(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, rules)
    other = await make_world(session, "Velmor")
    cosmos.home.leakage = 80
    other.leakage = 40
    seer = await make_son(session, "Morak", cosmos.home.id, domains=(Domain.MADNESS, Domain.DREAM))
    smith = await make_son(session, "Velan", cosmos.home.id, domains=(Domain.SEA, Domain.SALT))
    seer.existence = 50
    essence_before = seer.essence
    smith_essence = smith.essence
    fed = await feed_madness_sons(ctx)
    horror = rules.cosmic_horror
    assert fed == 1
    assert seer.essence == essence_before + round(60 / horror.madness_son_essence_divisor)
    assert seer.existence == 50 + horror.madness_son_existence_gain
    assert smith.essence == smith_essence


async def test_the_leakiest_world_suffers_at_most_one_horror_per_epoch(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "cosmic_horror", horror_event_divisor=1))
    other = await make_world(session, "Velmor")
    region = await make_region(session, "Barrens", other.id)
    await make_entity(session, "Empty Hollow", EntityType.PLACE, PlaceStats(), world_id=other.id, location_id=region.id)
    cosmos.home.leakage = 10
    other.leakage = 90
    text = await spontaneous_horror(ctx)
    assert text is not None
    rows = list(await session.scalars(select(ChronicleRow).where(ChronicleRow.template_key.like("horror.%"))))
    assert len(rows) == 1 and rows[0].world_id == other.id


async def test_a_tight_world_suffers_no_horror(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, rules)
    cosmos.home.leakage = 0
    assert await spontaneous_horror(ctx) is None


async def test_a_held_people_neither_loses_its_mind_nor_breeds_an_outer_cult(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "cosmic_horror", madness_chance=100, whisperers_chance=100, madness_population_loss_pct=10))
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    people.sanity = 5
    token = HELD_SCOPE.set(HeldScope(only=None, nodes=frozenset({people.id})))
    try:
        await update_sanity(ctx, await KnowledgeMap.load(session))
    finally:
        HELD_SCOPE.reset(token)
    assert people.sanity == 5
    assert people.stats.population == 5000
    assert not {"horror.madness_epidemic", "horror.whisperers"} & await keys(session)
