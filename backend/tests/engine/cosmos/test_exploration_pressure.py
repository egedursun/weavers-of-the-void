from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import MortalStats, PeopleStats
from aerona.engine.phases.exploration import ExplorationScene, Reason, cosmic_exploration, exploration_pressure, exploration_round
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, teach, tick, tuned

QUIET = {"base_chance": 10, "crowded_fill_pct": 100000, "poor_prosperity": 0}


def explore(rules: Rules, hungry_food: int = 0, **values: int) -> Rules:
    return tuned(tuned(rules, "world_effects", hungry_food=hungry_food), "exploration", **values)


async def community(session: AsyncSession, cosmos: Cosmos, region: EntityRow, name: str = "Tarn", **stats: int) -> EntityRow:
    values = {"population": 8000, "prosperity": 60, **stats}
    people = await make_entity(session, name, EntityType.PEOPLE, PeopleStats(**values), world_id=cosmos.home.id, location_id=region.id)
    people.civ_tier = 5
    return people


async def explorer(session: AsyncSession, cosmos: Cosmos, region: EntityRow, name: str = "Iska") -> EntityRow:
    return await make_entity(
        session, name, EntityType.MORTAL, MortalStats(age=30, lifespan=70, intellect=70, agility=70), world_id=cosmos.home.id, location_id=region.id
    )


async def test_pressure_is_the_base_chance_when_nothing_pushes(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, explore(rules, **QUIET))
    region = await make_region(session, "Vale", cosmos.home.id)
    people = await community(session, cosmos, region)
    pressure = await exploration_pressure(ctx, await ExplorationScene.load(ctx), people, [people])
    assert pressure.pct == 10 and pressure.reasons == [] and pressure.explorer is None


async def test_crowding_hunger_and_poverty_raise_the_pressure(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    base = {**QUIET, "crowded_fill_pct": 1, "crowded_bonus_pct": 12, "hungry_bonus_pct": 10}
    ctx = tick(session, explore(rules, **base))
    region = await make_region(session, "Vale", cosmos.home.id)
    people = await community(session, cosmos, region)
    crowded = await exploration_pressure(ctx, await ExplorationScene.load(ctx), people, [people])
    assert crowded.pct == 22 and crowded.reasons == [Reason.NARROW]
    poor_ctx = tick(session, explore(rules, **{**base, "crowded_fill_pct": 100000, "poor_prosperity": 90}))
    poor = await exploration_pressure(poor_ctx, await ExplorationScene.load(poor_ctx), people, [people])
    assert poor.pct == 20 and Reason.POVERTY in poor.reasons
    hungry_ctx = tick(session, explore(rules, **{**base, "crowded_fill_pct": 100000, "hungry_food": 100000}))
    hungry = await exploration_pressure(hungry_ctx, await ExplorationScene.load(hungry_ctx), people, [people])
    assert hungry.pct == 20 and Reason.HUNGER in hungry.reasons


async def test_an_explorer_on_the_land_and_road_knowledge_add_to_the_pressure(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, explore(rules, **{**QUIET, "explorer_bonus_pct": 10, "knowledge_bonus_pct": 8}))
    region = await make_region(session, "Vale", cosmos.home.id)
    people = await community(session, cosmos, region)
    scout = await explorer(session, cosmos, region)
    await teach(session, people, KnowledgeBranch.SEAFARING)
    pressure = await exploration_pressure(ctx, await ExplorationScene.load(ctx), people, [people])
    assert pressure.pct == 28
    assert pressure.reasons == [Reason.EXPLORER, Reason.KNOWLEDGE]
    assert pressure.explorer is not None and pressure.explorer.id == scout.id
    own = await exploration_pressure(ctx, await ExplorationScene.load(ctx), scout, [people])
    assert own.pct == 20 and own.reasons == [Reason.SPIRIT]


async def test_pressure_is_clamped_to_one_hundred(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, explore(rules, **{**QUIET, "base_chance": 95, "explorer_bonus_pct": 40}))
    region = await make_region(session, "Vale", cosmos.home.id)
    people = await community(session, cosmos, region)
    await explorer(session, cosmos, region)
    pressure = await exploration_pressure(ctx, await ExplorationScene.load(ctx), people, [people])
    assert pressure.pct == 100


async def test_one_expedition_per_explorer_and_a_cap_on_new_lands(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    tuned_rules = explore(rules, **{**QUIET, "base_chance": 100, "per_epoch_cap": 2, "new_region_pct": 100})
    first_region = await make_region(session, "Vale", cosmos.home.id)
    second_region = await make_region(session, "Dune", cosmos.home.id)
    await community(session, cosmos, first_region, "Tarn")
    await community(session, cosmos, second_region, "Brask")
    third_region = await make_region(session, "Fen", cosmos.home.id)
    await community(session, cosmos, third_region, "Orun")
    found = await exploration_round(session, tuned_rules, cosmos.home.id)
    assert len(found) == 2
    assert len({result.land.id for result in found}) == 2
    capped = tuned(tuned_rules, "exploration", per_epoch_cap=0)
    assert await exploration_round(session, capped, cosmos.home.id) == []


async def test_one_explorer_leads_only_one_expedition_in_an_epoch(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    tuned_rules = explore(rules, **{**QUIET, "base_chance": 100, "per_epoch_cap": 5, "new_region_pct": 100})
    region = await make_region(session, "Vale", cosmos.home.id)
    await community(session, cosmos, region, "Tarn")
    await community(session, cosmos, region, "Brask")
    await explorer(session, cosmos, region)
    found = await exploration_round(session, tuned_rules, cosmos.home.id)
    assert len(found) == 2
    assert all("Iska set out" not in result.text for result in found)


async def test_cosmic_exploration_is_shuffled_and_capped(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "exploration", route_search_cap=2, route_search_chance=100))
    region = await make_region(session, "Vale", cosmos.home.id)
    for name in ("Iska", "Orla", "Dren", "Veya"):
        seeker = await explorer(session, cosmos, region, name)
        await teach(session, seeker, KnowledgeBranch.MAGIC)
    assert await cosmic_exploration(ctx) == 2
    off = tick(session, tuned(rules, "exploration", route_search_cap=0, route_search_chance=100))
    assert await cosmic_exploration(off) == 0
