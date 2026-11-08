from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.cosmic_state import WorldLeakItemRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import DeferredStepRow
from aerona.db.tables.foreign_gods import OuterBargainRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.routes import HorizonIntuitionRow, RouteRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import HorizonStatus, TravelMethod
from aerona.domain.enums.world import HorrorEventKind
from aerona.domain.models.entity_stats import CultStats, LanguageStats, MortalStats, OuterBeingStats, PeopleStats, PlaceStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.leak import apply_leak, leak_cap
from aerona.engine.phases.exploration import (
    LandSearch,
    Reason,
    exploration_sentence,
    find_land,
    land_measure,
    record_intuition,
    search_route,
    settle_intuition,
)
from aerona.engine.phases.horror import (
    SanityBand,
    horror_event,
    outer_arrivals,
    outer_influence,
    reopen_severed,
    reseal_temporary,
    son_sanity_band,
    update_leaks,
    update_sanity,
    update_son_sanity,
)
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_son, make_world, teach, tick, tuned


def test_exploration_sentence_never_shows_measures() -> None:
    text = exploration_sentence([Reason.NARROW, Reason.HUNGER, Reason.EXPLORER, Reason.KNOWLEDGE], 0, "Iska")
    assert text == "when their homeland grew too small and when their food ran short led by Iska trusting what they knew of travel"


async def test_land_measure_counts_crowding(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    region = await make_region(session, "Coast", cosmos.home.id)
    for index in range(rules.exploration.crowded_communities_per_region):
        await make_entity(session, f"Folk {index}", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id, location_id=region.id)
    measure = await land_measure(session, rules, cosmos.home.id)
    assert measure.regions == 1 and measure.narrow and measure.ratio == rules.exploration.crowded_communities_per_region


async def test_find_land_and_pioneers(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "exploration", pioneer_chance=100))
    region = await make_region(session, "Coast", cosmos.home.id)
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=20000), world_id=cosmos.home.id, location_id=region.id)
    result = await find_land(ctx, LandSearch(cosmos.home.id, explorer=people, kind=EntityType.PLACE, reason="when their homeland grew too small"))
    assert result is not None and result.land.entity_type is EntityType.PLACE and result.land.location_id == region.id
    assert EntityFlag.DISCOVERY in await EntityRepository(session).flags(result.land.id)
    assert result.pioneer is not None and result.pioneer.location_id == result.land.id
    assert await BondRepository(session).exists_between(people.id, result.land.id, BondKind.DISCOVERED)


async def test_route_search_finds_a_route_or_senses_a_world(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    sage = await make_entity(ctx.session, "Iska", EntityType.MORTAL, MortalStats(intellect=90, age=40, lifespan=80), world_id=cosmos.home.id)
    await teach(ctx.session, sage, KnowledgeBranch.GATE_LORE)
    found = await search_route(ctx, sage, "following old roads", certain=True)
    assert found.route is not None and found.target is not None and found.target.id == other.id and found.vehicle is not None
    text = await record_intuition(ctx, sage, "following old roads", TravelMethod.DREAM_JOURNEY)
    assert "sensed" in text
    intuition = await ctx.session.scalar(select(HorizonIntuitionRow))
    assert intuition is not None and await ctx.session.scalar(select(DeferredStepRow)) is not None
    born = await make_world(ctx.session, "Somnia")
    await settle_intuition(ctx, intuition, born)
    assert intuition.status is HorizonStatus.BORN and intuition.result_world_id == born.id
    assert await ctx.session.scalar(select(func.count()).select_from(RouteRow).where(RouteRow.world_b_id == born.id)) == 1


def test_young_world_leak_cap(rules: Rules, cosmos: Cosmos) -> None:
    world = cosmos.home
    world.created_epoch = 4
    cap = leak_cap(rules, world, 5)
    assert cap == rules.cosmic_horror.young_cap + rules.cosmic_horror.young_cap_growth
    world.leakage = cap + 10
    assert apply_leak(world, 20, cap) == cap + 10


async def test_leak_rises_with_forbidden_knowledge(ctx: TickContext, cosmos: Cosmos) -> None:
    for index in range(3):
        people = await make_entity(ctx.session, f"Folk {index}", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
        await teach(ctx.session, people, KnowledgeBranch.FORBIDDEN)
    await update_leaks(ctx, await KnowledgeMap.load(ctx.session))
    assert cosmos.home.leakage > 0
    items = list(await ctx.session.scalars(select(WorldLeakItemRow.item).where(WorldLeakItemRow.world_id == cosmos.home.id)))
    assert "forbidden knowledge" in items


async def test_madness_births_whisperers(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "cosmic_horror", madness_chance=100, whisperers_chance=100))
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    people.sanity = 5
    await update_sanity(ctx, await KnowledgeMap.load(session))
    cult = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.CULT))
    assert cult is not None and EntityFlag.OUTER_CULT in await EntityRepository(session).flags(cult.id)
    assert EntityFlag.WHISPER_SOURCE in await EntityRepository(session).flags(people.id)


async def test_outer_being_arrives_and_gnaws(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "cosmic_horror", outer_being_chance=100))
    region = await make_region(session, "Rift", cosmos.home.id, danger=90)
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id, location_id=region.id)
    cult = await make_entity(session, "Whisper", EntityType.CULT, CultStats(followers=50), world_id=cosmos.home.id, flags=[EntityFlag.OUTER_CULT])
    cosmos.home.leakage = 95
    assert await outer_arrivals(ctx) == 1
    assert cosmos.home.leakage == 95 - rules.cosmic_horror.outer_being_entry_leak_drop
    await outer_influence(ctx)
    being = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.OUTER_BEING))
    assert being is not None and await BondRepository(session).exists_between(cult.id, being.id, BondKind.WORSHIPS)
    assert people.sanity is not None and people.sanity < rules.cosmic_horror.default_sanity


async def test_son_sanity_erodes_and_bands(ctx: TickContext, cosmos: Cosmos) -> None:
    son = await make_son(ctx.session, "Velan", cosmos.home.id)
    cosmos.home.leakage = 100
    being = await make_entity(ctx.session, "Unspoken", EntityType.OUTER_BEING, OuterBeingStats(influence=50), world_id=cosmos.home.id)
    ctx.session.add(OuterBargainRow(outer_entity_id=being.id, son_id=son.id, epoch=1))
    await ctx.session.flush()
    await update_son_sanity(ctx, await KnowledgeMap.load(ctx.session))
    horror = ctx.rules.cosmic_horror
    expected = (
        horror.son_default_sanity - (100 / horror.son_leak_erosion_divisor + horror.son_outer_erosion + horror.son_bargain_erosion) + horror.son_sanity_repair
    )
    assert son.sanity == round(expected)
    son.sanity = 1
    assert son_sanity_band(ctx.rules, son) is SanityBand.MAD
    seer = await make_son(ctx.session, "Morak", cosmos.home.id, domains=(Domain.MADNESS, Domain.DREAM))
    await update_son_sanity(ctx, await KnowledgeMap.load(ctx.session))
    assert seer.sanity is not None and seer.sanity > round(expected)


async def test_horror_events(ctx: TickContext, cosmos: Cosmos) -> None:
    people = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    eye = await horror_event(ctx, HorrorEventKind.EYE_IN_THE_SKY, cosmos.home)
    assert eye is not None and people.sanity == ctx.rules.cosmic_horror.default_sanity - ctx.rules.cosmic_horror.sky_eye_sanity_loss
    language = await make_entity(ctx.session, "Tarnic", EntityType.LANGUAGE, LanguageStats(), world_id=cosmos.home.id)
    for index in range(10):
        ctx.session.add(LexemeRow(language_entity_id=language.id, word=f"word{index}", meaning="thing", added_by_kind=ActorKind.ENGINE, epoch=1))
    await ctx.session.flush()
    await horror_event(ctx, HorrorEventKind.WAVE_OF_SILENCE, cosmos.home)
    remaining = await ctx.session.scalar(select(func.count()).select_from(LexemeRow))
    assert remaining == 10 - 10 * ctx.rules.cosmic_horror.silence_word_loss_pct // 100
    region = await make_region(ctx.session, "Barrens", cosmos.home.id)
    place = await make_entity(ctx.session, "Empty Hollow", EntityType.PLACE, PlaceStats(), world_id=cosmos.home.id, location_id=region.id)
    text = await horror_event(ctx, HorrorEventKind.VISIT_OF_THE_VOID, cosmos.home)
    assert text is not None and place.status is EntityStatus.DESTROYED
    await horror_event(ctx, HorrorEventKind.STARS_ALIGN, cosmos.home)
    assert cosmos.home.leakage == ctx.rules.cosmic_horror.alignment_leak


async def test_routes_reopen_and_reseal(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    severed = await make_route(ctx.session, cosmos.home.id, other.id, active=False)
    severed.temp_closed_until_epoch = ctx.epoch
    temporary = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.SLINGSHOT_ORBIT)
    temporary.temp_open_until_epoch = ctx.epoch
    assert await reopen_severed(ctx) == 1 and severed.active
    assert await reseal_temporary(ctx) == 1 and not temporary.active
