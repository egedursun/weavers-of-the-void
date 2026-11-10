from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow, ForcedWeatherRow, LeyLineRow, NotableYearRow, StructureLeyRow, WorldSeasonRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import NotableYearKind, WeatherKind
from aerona.engine.environment.control import CALENDAR_FIELDS, SEASON_NUMBERS, hold_calendar
from aerona.engine.environment.ley_works import LEY_WORK_KINDS, ley_row
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

DERIVED_CALENDAR = frozenset({"year_length_days", "day_length_hours", "moon_count", "tidal_strength", "season_count"})
SEASONS_MAX = 6
NAME_MAX = 120
LEY_FLAGS = frozenset({"attuned", "on_ley_line", "at_nexus"})


async def _world(session: AsyncSession, world_id: int) -> WorldRow:
    world = await session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    return world


async def _seasons(session: AsyncSession, world_id: int) -> list[WorldSeasonRow]:
    return list(await session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id).order_by(WorldSeasonRow.position)))


async def _renumber(session: AsyncSession, seasons: list[WorldSeasonRow]) -> None:
    offset = len(seasons) + SEASONS_MAX
    for season in seasons:
        season.position += offset
    await session.flush()
    for position, season in enumerate(seasons):
        season.position = position
    await session.flush()


async def add_season(session: AsyncSession, world_id: int, name: str, values: dict[str, int], position: int | None) -> WorldSeasonRow:
    world = await _world(session, world_id)
    seasons = await _seasons(session, world_id)
    if len(seasons) >= SEASONS_MAX:
        raise ValidationFailedError(f"A world keeps at most {SEASONS_MAX} seasons.")
    numbers = {key: clamp_int(values.get(key, (low + high) // 2 if low >= 0 else 0), low, high) for key, (low, high) in SEASON_NUMBERS.items()}
    row = WorldSeasonRow(world_id=world_id, position=len(seasons) + SEASONS_MAX * 2, name=name.strip(), edited=True, **numbers)
    session.add(row)
    await session.flush()
    at = len(seasons) if position is None else max(0, min(position, len(seasons)))
    ordered = [*seasons[:at], row, *seasons[at:]]
    await _renumber(session, ordered)
    world.season_count = len(ordered)
    hold_calendar(world, "season_count")
    await session.flush()
    return row


async def remove_season(session: AsyncSession, season_id: int) -> WorldSeasonRow:
    season = await session.get(WorldSeasonRow, season_id)
    if season is None:
        raise NotFoundError("No such season.")
    seasons = await _seasons(session, season.world_id)
    if len(seasons) <= 1:
        raise ValidationFailedError("A world keeps at least one season.")
    world = await _world(session, season.world_id)
    removed = season.position
    await session.delete(season)
    await session.flush()
    rest = [item for item in seasons if item.id != season_id]
    await _renumber(session, rest)
    world.season_count = len(rest)
    hold_calendar(world, "season_count")
    statement = select(TraditionProfileRow).where(TraditionProfileRow.season_position.is_not(None), TraditionProfileRow.season_position >= removed)
    for row in await session.scalars(statement):
        position = row.season_position or 0
        row.season_position = None if position == removed else position - 1
    await session.flush()
    return season


async def release_season(session: AsyncSession, season_id: int) -> WorldSeasonRow:
    season = await session.get(WorldSeasonRow, season_id)
    if season is None:
        raise NotFoundError("No such season.")
    if not season.edited:
        raise ValidationFailedError(f"{season.name} is not held.")
    season.edited = False
    await session.flush()
    return season


def set_moons(world: WorldRow, rules: Rules, *, moon_count: int | None, tidal_strength: int | None) -> None:
    if moon_count is not None:
        world.moon_count = max(0, moon_count)
        hold_calendar(world, "moon_count")
        if tidal_strength is None and "tidal_strength" not in world.calendar_locked:
            world.tidal_strength = clamp_int(world.moon_count * rules.seasons.tide_per_moon, 0, PERCENT)
            hold_calendar(world, "tidal_strength")
    if tidal_strength is not None:
        world.tidal_strength = clamp_int(tidal_strength, 0, PERCENT)
        hold_calendar(world, "tidal_strength")


async def release_calendar(session: AsyncSession, world_id: int, fields: list[str]) -> WorldRow:
    world = await _world(session, world_id)
    unknown = [field for field in fields if field not in CALENDAR_FIELDS]
    if unknown or not fields:
        raise ValidationFailedError(f"Release one of {', '.join(sorted(CALENDAR_FIELDS))}.")
    world.calendar_locked = [field for field in world.calendar_locked if field not in fields]
    for field in fields:
        if field not in DERIVED_CALENDAR:
            setattr(world, field, None)
    if "axial_tilt" in fields:
        world.season_count = None
    await session.flush()
    return world


async def edit_weather(
    session: AsyncSession, forced_id: int, *, kind: WeatherKind | None, until_epoch: int | None, season_position: int | None, every_season: bool
) -> ForcedWeatherRow:
    row = await session.get(ForcedWeatherRow, forced_id)
    if row is None:
        raise NotFoundError("No such forced weather.")
    if kind is not None:
        row.kind = kind
    if until_epoch is not None:
        if until_epoch < row.from_epoch:
            raise ValidationFailedError(f"The weather is held from epoch {row.from_epoch}; it cannot end before that.")
        row.until_epoch = until_epoch
    if every_season:
        row.season_position = None
    elif season_position is not None:
        row.season_position = max(0, season_position)
    await session.flush()
    return row


async def notable_year(session: AsyncSession, notable_id: int) -> NotableYearRow:
    row = await session.get(NotableYearRow, notable_id)
    if row is None:
        raise NotFoundError("No such notable year.")
    return row


async def edit_notable_year(
    session: AsyncSession,
    notable_id: int,
    *,
    name: str | None,
    magnitude: int | None,
    kind: NotableYearKind | None,
    weather: WeatherKind | None,
    year: int | None,
) -> NotableYearRow:
    row = await notable_year(session, notable_id)
    if name is not None:
        row.name = name.strip()[:NAME_MAX]
    if magnitude is not None:
        row.magnitude = clamp_int(magnitude, 0, PERCENT)
    if kind is not None:
        row.kind = kind
    if weather is not None:
        row.weather = weather
    if row.kind is NotableYearKind.WEATHER and row.weather is None:
        raise ValidationFailedError("A year of weather needs its weather.")
    if year is not None:
        row.year = max(0, year)
    await session.flush()
    return row


async def delete_notable_year(session: AsyncSession, notable_id: int) -> NotableYearRow:
    row = await notable_year(session, notable_id)
    for calendar in await session.scalars(select(CalendarRow).where(CalendarRow.world_id == row.world_id)):
        if any(day.get("notable_year_id") == row.id for day in calendar.holy_days):
            calendar.holy_days = [{**day, "notable_year_id": None} if day.get("notable_year_id") == row.id else day for day in calendar.holy_days]
    await session.delete(row)
    await session.flush()
    return row


async def calendar_of(session: AsyncSession, knowledge_id: int) -> CalendarRow:
    calendar = await session.get(CalendarRow, knowledge_id)
    if calendar is None:
        raise NotFoundError("This record keeps no calendar.")
    return calendar


def holy_day_entry(name: str, *, season_position: int | None, notable_year_id: int | None, tradition_id: int | None, year: int | None) -> dict[str, Any]:
    return {
        "name": name.strip()[:NAME_MAX],
        "season_position": season_position,
        "notable_year_id": notable_year_id,
        "tradition_entity_id": tradition_id,
        "year": year,
    }


async def set_holy_day(session: AsyncSession, knowledge_id: int, index: int | None, entry: dict[str, Any]) -> CalendarRow:
    calendar = await calendar_of(session, knowledge_id)
    days = [dict(day) for day in calendar.holy_days]
    notable_id = entry.get("notable_year_id")
    if isinstance(notable_id, int):
        notable = await notable_year(session, notable_id)
        entry["year"] = entry.get("year") or notable.year
    tradition_id = entry.get("tradition_entity_id")
    if isinstance(tradition_id, int):
        tradition = await session.get(EntityRow, tradition_id)
        if tradition is None or tradition.entity_type is not EntityType.TRADITION:
            raise ValidationFailedError("A holy day can only keep a tradition.")
        profile = await session.get(TraditionProfileRow, tradition_id)
        if profile is not None:
            profile.calendar_entity_id = knowledge_id
            if entry.get("season_position") is not None:
                profile.season_position = entry["season_position"]
            profile.locked = sorted({*profile.locked, "calendar_entity_id", "season_position"})
    if index is None:
        days.append(entry)
    elif 0 <= index < len(days):
        days[index] = {**days[index], **{key: value for key, value in entry.items() if value is not None or key == "season_position"}}
    else:
        raise NotFoundError("No such holy day.")
    calendar.holy_days = days
    await session.flush()
    return calendar


async def remove_holy_day(session: AsyncSession, knowledge_id: int, index: int) -> dict[str, Any]:
    calendar = await calendar_of(session, knowledge_id)
    days = [dict(day) for day in calendar.holy_days]
    if not 0 <= index < len(days):
        raise NotFoundError("No such holy day.")
    removed = days.pop(index)
    tradition_id = removed.get("tradition_entity_id")
    profile = await session.get(TraditionProfileRow, tradition_id) if isinstance(tradition_id, int) else None
    if profile is not None and profile.calendar_entity_id == knowledge_id:
        profile.calendar_entity_id = None
        profile.locked = [item for item in profile.locked if item != "calendar_entity_id"]
    calendar.holy_days = days
    await session.flush()
    return removed


async def set_anchor(session: AsyncSession, knowledge_id: int, anchor_year: int) -> CalendarRow:
    calendar = await calendar_of(session, knowledge_id)
    calendar.anchor_year = max(0, anchor_year)
    await session.flush()
    return calendar


async def set_ley_strength(session: AsyncSession, line_id: int, strength: int) -> LeyLineRow:
    line = await session.get(LeyLineRow, line_id)
    if line is None:
        raise NotFoundError("No such ley line.")
    line.strength = clamp_int(strength, 0, PERCENT)
    line.forged = True
    await session.flush()
    return line


async def dissolve_ley(session: AsyncSession, line_id: int) -> LeyLineRow:
    line = await session.get(LeyLineRow, line_id)
    if line is None:
        raise NotFoundError("No such ley line.")
    await session.delete(line)
    await session.flush()
    return line


async def structure(session: AsyncSession, structure_id: int) -> EntityRow:
    work = await session.get(EntityRow, structure_id)
    if work is None or work.entity_type is not EntityType.STRUCTURE:
        raise NotFoundError("No such structure.")
    return work


async def set_ley_work(session: AsyncSession, structure_id: int, values: dict[str, bool], release: list[str]) -> StructureLeyRow:
    work = await structure(session, structure_id)
    row = await ley_row(session, work)
    unknown = [key for key in [*values, *release] if key not in LEY_FLAGS]
    if unknown:
        raise ValidationFailedError(f"A work's ley ties are {', '.join(sorted(LEY_FLAGS))}.")
    for key, value in values.items():
        setattr(row, key, value)
    if "attuned" in release:
        row.attuned = work.engine_kind in LEY_WORK_KINDS
    row.locked = sorted({*row.locked, *values} - set(release))
    await session.flush()
    return row
