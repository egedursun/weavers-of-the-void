import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.geography import geography_lines
from aerona.agents.context.lore import tradition_lines
from aerona.agents.context.scope import load_scope
from aerona.catalog.movement import mode_through
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.environment import NotableYearRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import CalendarSlot, TraditionFunction
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import MovementMode, NotableYearKind
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.lore.calendar_slots import festivals_of
from aerona.engine.operations.expeditions import hard_way, way_of
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from aerona.services.books.seasons import festival_plan
from tests.engine.core.factories import bond, entity, seed_core_world, surveyed

RULES = Rules()
M = MovementMode


def test_the_way_taken_is_the_one_with_the_best_passage_a_body_can_use() -> None:
    passability = {M.ON_FOOT.value: 30, M.SWIMMING.value: 20, M.SUBMERGED.value: 90, M.FLYING.value: 100}
    assert mode_through(passability, frozenset({M.ON_FOOT, M.SWIMMING, M.SUBMERGED}), 100) is M.SUBMERGED
    assert mode_through(passability, frozenset({M.ON_FOOT, M.SWIMMING}), 100) is M.ON_FOOT
    assert mode_through(passability, frozenset(), 100) is M.ON_FOOT


def test_a_way_with_little_passage_adds_legs() -> None:
    table = RULES.expeditions
    assert hard_way(table, 4, 100) == 4
    assert hard_way(table, 4, 0) == 4 + 4 * table.hard_way_legs_pct // 100
    assert hard_way(table, 4, 50) > hard_way(table, 4, 100)


async def test_an_expedition_goes_only_by_a_way_its_people_can_use(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert land is not None
    land.passability = {**land.passability, M.ON_FOOT.value: 40}
    ctx = await manual_context(session, "test", RULES)
    way, passage = await way_of(ctx, world.people, world.regions[0], None)
    assert way is M.ON_FOOT and passage == 40
    with pytest.raises(ValidationFailedError):
        await way_of(ctx, world.people, world.regions[0], M.SUBMERGED)


async def tradition(session: AsyncSession, world_id: int, name: str, slot: CalendarSlot, position: int | None, **fields: object) -> TraditionProfileRow:
    made = await entity(session, name, EntityType.TRADITION, TraditionStats(spread=40), world_id=world_id)
    row = TraditionProfileRow(tradition_entity_id=made.id, kind=TraditionFunction.FESTIVAL, calendar_slot=slot, season_position=position, locked=[], **fields)
    session.add(row)
    await session.flush()
    return row


async def test_region_lines_carry_the_passage_of_every_way_and_the_named_years_kept(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    region = world.regions[0]
    year = NotableYearRow(
        world_id=world.world.id, region_entity_id=region.id, epoch=1, year=12, kind=NotableYearKind.HUNGER, name="the Year of Hunger", magnitude=80
    )
    session.add(year)
    await session.flush()
    await tradition(session, world.world.id, "The Thin Days", CalendarSlot.REMEMBRANCE, None, notable_year_id=year.id)
    text = await geography_lines(await load_scope(session, RULES), world.world.id)
    assert "passage by way of travel: " in text and "on foot " in text
    assert "the Year of Hunger (year 12, hunger from famines and failed harvests, magnitude 80; remembered by The Thin Days)" in text
    assert "fertility" in text


async def test_tradition_lines_say_whether_the_time_of_a_festival_comes(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    row = await tradition(session, world.world.id, "The Long Table", CalendarSlot.HARVEST, None, in_season=True)
    await bond(session, world.people.id, row.tradition_entity_id, BondKind.CELEBRATES)
    lines = await tradition_lines(session, world.people.id)
    assert any("kept at harvest, it comes this epoch" in line for line in lines)
    row.in_season = False
    lines = await tradition_lines(session, world.people.id)
    assert any("its time does not come this epoch" in line for line in lines)


async def test_the_year_of_festivals_places_each_festival_on_its_season_in_the_book(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    for position, name in enumerate(("Bloom", "Hush")):
        session.add(
            WorldSeasonRow(
                world_id=world.world.id, position=position, name=name, temperature_shift=0, rain_shift=0, growth=50, travel=50, campaign=50, share_pct=50
            )
        )
    placed = await tradition(session, world.world.id, "The Lantern Walk", CalendarSlot.MIDSUMMER, 0, in_season=True)
    loose = await tradition(session, world.world.id, "The Quiet Count", CalendarSlot.NEW_YEAR, None)
    for row in (placed, loose):
        await bond(session, world.people.id, row.tradition_entity_id, BondKind.CELEBRATES)
    assert {entity.name for entity, _ in await festivals_of(session, world.people.id)} == {"The Lantern Walk", "The Quiet Count"}
    plan = await festival_plan(session, world.people)
    assert plan is not None
    facts = dict(plan.facts)
    assert "The Lantern Walk" in facts["1. Bloom"] and "comes this epoch" in facts["1. Bloom"]
    assert facts["2. Hush"] == "none"
    assert "The Quiet Count" in facts["Whenever its time comes"]
    assert "<circle" in plan.figure
