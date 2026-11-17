import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.environment import CalendarRow, ForcedWeatherRow, LeyLineRow, NotableYearRow, StructureLeyRow, WorldSeasonRow
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import NotableYearKind, WeatherKind
from aerona.domain.models.entity_stats import KnowledgeStats, StructureStats, TraditionStats
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import calendar
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def _undo(session: AsyncSession, entry_id: int | None, epoch: int) -> list[str]:
    assert entry_id is not None
    changes = await changes_of(session, entry_id)
    names = label_names(changes, await node_names(session, changes))
    return (await UndoRun(session, epoch, changes, names).run()).conflicts


async def _seasons(session: AsyncSession, world: PlayerWorld, count: int = 3) -> list[WorldSeasonRow]:
    rows = [
        WorldSeasonRow(
            world_id=world.world.id,
            position=index,
            name=f"Season {index}",
            temperature_shift=0,
            rain_shift=0,
            growth=40 + index * 10,
            travel=50,
            campaign=50,
            edited=False,
        )
        for index in range(count)
    ]
    session.add_all(rows)
    world.world.season_count = count
    await session.flush()
    return rows


async def _positions(session: AsyncSession, world: PlayerWorld) -> list[str]:
    statement = select(WorldSeasonRow).where(WorldSeasonRow.world_id == world.world.id).order_by(WorldSeasonRow.position)
    return [row.name for row in await session.scalars(statement)]


async def test_a_single_season_is_added_released_and_removed(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await _seasons(session, world)
    added = await calendar.add_season(scope, calendar.AddSeason(world_id=world.world.id, name="The Burning", position=1, growth=10))
    assert await _positions(session, world) == ["Season 0", "The Burning", "Season 1", "Season 2"]
    assert world.world.season_count == 4
    burning = await session.scalar(select(WorldSeasonRow).where(WorldSeasonRow.name == "The Burning"))
    assert burning is not None and burning.edited and burning.growth == 10
    await calendar.release_season(scope, calendar.SeasonTarget(season_id=burning.id))
    assert not burning.edited
    with pytest.raises(ValidationFailedError):
        await calendar.release_season(scope, calendar.SeasonTarget(season_id=burning.id))
    first = await session.scalar(select(WorldSeasonRow).where(WorldSeasonRow.name == "Season 0"))
    assert first is not None
    await calendar.remove_season(scope, calendar.SeasonTarget(season_id=first.id))
    assert await _positions(session, world) == ["The Burning", "Season 1", "Season 2"]
    assert world.world.season_count == 3
    assert added.ledger_entry_id is not None


async def test_the_last_season_cannot_be_removed(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    rows = await _seasons(session, world, count=1)
    with pytest.raises(ValidationFailedError):
        await calendar.remove_season(scope, calendar.SeasonTarget(season_id=rows[0].id))


async def test_moons_and_tides_are_held_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await calendar.set_moons(scope, calendar.SetMoons(world_id=world.world.id, moon_count=3, tidal_strength=70))
    assert (world.world.moon_count, world.world.tidal_strength) == (3, 70)
    assert sorted(world.world.calendar_locked) == ["moon_count", "tidal_strength"]
    await calendar.release_calendar(scope, calendar.ReleaseCalendar(world_id=world.world.id, fields=["moon_count", "tidal_strength"]))
    assert world.world.calendar_locked == []
    with pytest.raises(ValidationFailedError):
        await calendar.release_calendar(scope, calendar.ReleaseCalendar(world_id=world.world.id, fields=["colour"]))


async def test_a_notable_year_is_rewritten_undone_and_struck(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    row = NotableYearRow(
        world_id=world.world.id, region_entity_id=world.region.id, epoch=2, year=60, kind=NotableYearKind.HUNGER, name="the Lean Year", magnitude=50
    )
    session.add(row)
    await session.flush()
    outcome = await calendar.edit_notable_year(scope, calendar.EditNotableYear(notable_id=row.id, name="the Starving Year", magnitude=90))
    assert (row.name, row.magnitude) == ("the Starving Year", 90)
    assert await _undo(session, outcome.ledger_entry_id, world.cosmos.epoch) == []
    await session.refresh(row)
    assert (row.name, row.magnitude) == ("the Lean Year", 50)
    notable_id = row.id
    with pytest.raises(ValidationFailedError):
        await calendar.edit_notable_year(scope, calendar.EditNotableYear(notable_id=notable_id, kind=NotableYearKind.WEATHER))
    await calendar.delete_notable_year(scope, calendar.NotableTarget(notable_id=notable_id))
    assert await session.get(NotableYearRow, notable_id) is None


async def test_holy_days_found_fasts_bind_traditions_and_move_the_anchor(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await _seasons(session, world)
    record = await make_entity(session, "Star Count", EntityType.KNOWLEDGE, world_id=world.world.id, stats=KnowledgeStats(level=2, spread=20))
    keeper = CalendarRow(knowledge_entity_id=record.id, world_id=world.world.id, adopted_epoch=1, anchor_year=0, month_names=["A", "B", "C"], holy_days=[])
    notable = NotableYearRow(
        world_id=world.world.id, region_entity_id=world.region.id, epoch=2, year=70, kind=NotableYearKind.HUNGER, name="the Ash Year", magnitude=60
    )
    session.add_all([keeper, notable])
    await session.flush()
    await calendar.set_holy_day(
        scope, calendar.SetHolyDay(knowledge_id=record.id, name="Fast of Ash", season_position=0, notable_year_id=notable.id, found_tradition=True)
    )
    day = keeper.holy_days[0]
    assert day["year"] == 70 and isinstance(day["tradition_entity_id"], int)
    fast = await session.get(TraditionProfileRow, day["tradition_entity_id"])
    assert fast is not None and fast.kind is TraditionFunction.FAST
    assert fast.notable_year_id == notable.id and fast.calendar_entity_id == record.id
    feast = await make_entity(session, "Feast of Bread", EntityType.TRADITION, world_id=world.world.id, stats=TraditionStats(spread=10, rigidity=10))
    session.add(TraditionProfileRow(tradition_entity_id=feast.id, kind=TraditionFunction.FESTIVAL, cost={}, effects={}, locked=[]))
    await session.flush()
    await calendar.set_holy_day(scope, calendar.SetHolyDay(knowledge_id=record.id, name="Bread Day", season_position=2, tradition_id=feast.id))
    profile = await session.get(TraditionProfileRow, feast.id)
    assert profile is not None and profile.season_position == 2 and profile.calendar_entity_id == record.id
    assert {"season_position", "calendar_entity_id"} <= set(profile.locked)
    await calendar.set_holy_day(scope, calendar.SetHolyDay(knowledge_id=record.id, index=1, name="Day of Bread", season_position=1))
    assert keeper.holy_days[1]["name"] == "Day of Bread" and keeper.holy_days[1]["season_position"] == 1
    await calendar.remove_holy_day(scope, calendar.HolyDayTarget(knowledge_id=record.id, index=1))
    assert [item["name"] for item in keeper.holy_days] == ["Fast of Ash"]
    assert profile.calendar_entity_id is None
    await calendar.set_anchor(scope, calendar.SetAnchor(knowledge_id=record.id, anchor_year=412))
    assert keeper.anchor_year == 412


async def test_ley_lines_take_a_held_strength_and_can_be_unmade(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    other = await make_entity(session, "Far Vale", EntityType.REGION, world_id=world.world.id)
    low, high = sorted((world.region.id, other.id))
    line = LeyLineRow(world_id=world.world.id, region_a_id=low, region_b_id=high, strength=30, formed_epoch=1)
    session.add(line)
    await session.flush()
    await calendar.set_ley_strength(scope, calendar.LeyStrength(line_id=line.id, strength=85))
    assert line.strength == 85 and line.forged
    await calendar.dissolve_ley(scope, calendar.LeyLineTarget(line_id=line.id))
    assert await session.get(LeyLineRow, line.id) is None


async def test_a_work_is_tied_to_the_ley_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    work = await make_entity(
        session,
        "Spire",
        EntityType.STRUCTURE,
        world_id=world.world.id,
        location_id=world.region.id,
        stats=StructureStats(splendor=5, durability=50, function=40),
    )
    await calendar.set_ley_work(scope, calendar.LeyWork(structure_id=work.id, values={"attuned": True, "at_nexus": True}))
    row = await session.get(StructureLeyRow, work.id)
    assert row is not None and row.attuned and row.at_nexus
    assert row.locked == ["at_nexus", "attuned"]
    await calendar.set_ley_work(scope, calendar.LeyWork(structure_id=work.id, release=["attuned"]))
    assert not row.attuned and row.locked == ["at_nexus"]
    with pytest.raises(ValidationFailedError):
        await calendar.set_ley_work(scope, calendar.LeyWork(structure_id=work.id, values={"glows": True}))


async def test_held_weather_can_be_changed(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    row = ForcedWeatherRow(region_entity_id=world.region.id, world_id=world.world.id, from_epoch=2, until_epoch=3, season_position=1, kind=WeatherKind.RAIN)
    session.add(row)
    await session.flush()
    await calendar.edit_weather(scope, calendar.EditWeather(forced_id=row.id, kind=WeatherKind.BLIZZARD, until_epoch=9, every_season=True))
    assert (row.kind, row.until_epoch, row.season_position) == (WeatherKind.BLIZZARD, 9, None)
    with pytest.raises(ValidationFailedError):
        await calendar.edit_weather(scope, calendar.EditWeather(forced_id=row.id, until_epoch=1))
