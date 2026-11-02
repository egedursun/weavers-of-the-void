from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow, LeyLineRow, PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, PlaceCover, RiverClass, ScarKind, SoilKind, TerrainKind, WaterSource
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.environment.seasons import season_count_for
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

REGION_ENUMS: dict[str, type[StrEnum]] = {
    "dominant_terrain": TerrainKind,
    "soil": SoilKind,
    "river_class": RiverClass,
    "coast_kind": CoastKind,
}
REGION_NUMBERS = frozenset(
    {
        "elevation_mean",
        "roughness",
        "latitude",
        "moisture",
        "base_forest",
        "forest_cover",
        "base_wetland",
        "wetland",
        "soil_fertility",
        "soil_base",
        "temperature",
        "rainfall",
        "disease_load",
        "magic_density",
        "defensibility",
        "cleared",
        "farmed",
        "grazed",
        "mined",
        "built",
        "erosion",
    }
)
LOCKABLE = frozenset(
    {
        "dominant_terrain",
        "river_class",
        "coast_kind",
        "elevation_mean",
        "roughness",
        "latitude",
        "moisture",
        "base_forest",
        "forest_cover",
        "base_wetland",
        "wetland",
        "temperature",
        "rainfall",
        "disease_load",
        "defensibility",
    }
)
PLACE_ENUMS: dict[str, type[StrEnum]] = {"terrain": TerrainKind, "cover": PlaceCover, "water_source": WaterSource}
PLACE_NUMBERS = frozenset({"height_advantage", "soil_fertility"})
SEASON_NUMBERS: dict[str, tuple[int, int]] = {
    "temperature_shift": (-PERCENT, PERCENT),
    "rain_shift": (-PERCENT, PERCENT),
    "growth": (0, PERCENT),
    "travel": (0, PERCENT),
    "campaign": (0, PERCENT),
}


async def region_ground(session: AsyncSession, region_id: int) -> RegionEnvironmentRow:
    found = await session.get(RegionEnvironmentRow, region_id)
    if found is None:
        raise NotFoundError("This region has not been surveyed yet; run the environment survey first.")
    return found


async def place_ground(session: AsyncSession, place_id: int) -> PlaceEnvironmentRow:
    found = await session.get(PlaceEnvironmentRow, place_id)
    if found is None:
        raise NotFoundError("This place has not been surveyed yet; run the environment survey first.")
    return found


def coerce(field: str, value: int | str, enums: dict[str, type[StrEnum]], numbers: frozenset[str]) -> int | StrEnum:
    if field in enums:
        try:
            return enums[field](str(value))
        except ValueError as error:
            raise ValidationFailedError(f"{value} is not a valid {field.replace('_', ' ')}.") from error
    if field in numbers:
        if not isinstance(value, int):
            raise ValidationFailedError(f"{field.replace('_', ' ')} takes a whole number.")
        return clamp_int(value, 0, PERCENT)
    raise ValidationFailedError(f"{field.replace('_', ' ')} cannot be set by hand.")


def set_region_field(ground: RegionEnvironmentRow, field: str, value: int | str, *, lock: bool) -> None:
    setattr(ground, field, coerce(field, value, REGION_ENUMS, REGION_NUMBERS))
    locked = set(ground.locked)
    if lock and field in LOCKABLE:
        locked.add(field)
    ground.locked = sorted(locked)


def unlock_region_field(ground: RegionEnvironmentRow, field: str) -> bool:
    if field not in ground.locked:
        return False
    ground.locked = sorted(set(ground.locked) - {field})
    return True


def set_place_field(ground: PlaceEnvironmentRow, field: str, value: int | str | bool) -> None:
    if field == "chokepoint":
        ground.chokepoint = bool(value)
        return
    if isinstance(value, bool):
        raise ValidationFailedError(f"{field.replace('_', ' ')} does not take yes or no.")
    setattr(ground, field, coerce(field, value, PLACE_ENUMS, PLACE_NUMBERS))


def set_scar(ground: RegionEnvironmentRow, kind: ScarKind, depth: int) -> None:
    scars = dict(ground.scars)
    if depth <= 0:
        scars.pop(kind.value, None)
    else:
        scars[kind.value] = clamp_int(depth, 0, PERCENT)
    ground.scars = scars


def set_mineral(ground: RegionEnvironmentRow, material: str, richness: int) -> None:
    layers = dict(ground.mineral_layers)
    if richness <= 0:
        layers.pop(material, None)
    else:
        layers[material] = clamp_int(richness, 0, PERCENT)
    ground.mineral_layers = layers


async def world_seasons(session: AsyncSession, world_id: int) -> list[WorldSeasonRow]:
    return list(await session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id).order_by(WorldSeasonRow.position)))


async def reorder_seasons(session: AsyncSession, world_id: int, order: list[int]) -> list[WorldSeasonRow]:
    seasons = await world_seasons(session, world_id)
    if sorted(order) != [season.position for season in seasons]:
        raise ValidationFailedError("Name every season of the world exactly once, by its current position.")
    by_position = {season.position: season for season in seasons}
    offset = len(seasons)
    for season in seasons:
        season.position += offset
    await session.flush()
    for new_position, old_position in enumerate(order):
        by_position[old_position].position = new_position
        by_position[old_position].edited = True
    await session.flush()
    return sorted(seasons, key=lambda season: season.position)


async def edit_season(session: AsyncSession, season_id: int, values: dict[str, int], name: str | None) -> WorldSeasonRow:
    season = await session.get(WorldSeasonRow, season_id)
    if season is None:
        raise NotFoundError("No such season.")
    for key, value in values.items():
        bounds = SEASON_NUMBERS.get(key)
        if bounds is None:
            raise ValidationFailedError(f"{key.replace('_', ' ')} is not a season value.")
        setattr(season, key, clamp_int(value, *bounds))
    if name is not None:
        season.name = name
    season.edited = True
    await session.flush()
    return season


def set_world_calendar(rules: Rules, world: WorldRow, *, axial_tilt: int | None, year_length_days: int | None, day_length_hours: int | None) -> None:
    settings = rules.seasons
    if axial_tilt is not None:
        world.axial_tilt = clamp_int(axial_tilt, 0, settings.tilt_max)
        world.season_count = season_count_for(rules, world.world_type, world.axial_tilt)
    if year_length_days is not None:
        world.year_length_days = clamp_int(year_length_days, settings.year_days_min, settings.year_days_max)
    if day_length_hours is not None:
        world.day_length_hours = max(1, day_length_hours)


async def astronomy_record(session: AsyncSession, knowledge_id: int) -> EntityRow:
    record = await session.get(EntityRow, knowledge_id)
    if record is None or record.entity_type is not EntityType.KNOWLEDGE or record.knowledge_branch is not KnowledgeBranch.ASTRONOMY:
        raise ValidationFailedError("A calendar is kept in a knowledge record of astronomy.")
    return record


async def rename_months(session: AsyncSession, knowledge_id: int, names: list[str]) -> CalendarRow:
    calendar = await session.get(CalendarRow, knowledge_id)
    if calendar is None:
        raise NotFoundError("This record keeps no calendar.")
    if len(names) != len(calendar.month_names):
        raise ValidationFailedError(f"The calendar has {len(calendar.month_names)} months; name each of them.")
    calendar.month_names = [name.strip() for name in names]
    await session.flush()
    return calendar


async def drop_calendar(session: AsyncSession, knowledge_id: int) -> bool:
    calendar = await session.get(CalendarRow, knowledge_id)
    if calendar is None:
        return False
    await session.delete(calendar)
    await session.flush()
    return True


async def ley_line(session: AsyncSession, line_id: int) -> LeyLineRow:
    found = await session.get(LeyLineRow, line_id)
    if found is None:
        raise NotFoundError("No such ley line.")
    return found


async def sever_ley(session: AsyncSession, line_id: int, *, until_epoch: int, son_id: int | None = None) -> LeyLineRow:
    line = await ley_line(session, line_id)
    line.severed = True
    line.severed_until_epoch = until_epoch
    line.severed_by_son_id = son_id
    await session.flush()
    return line


async def restore_ley(session: AsyncSession, line_id: int) -> LeyLineRow:
    line = await ley_line(session, line_id)
    line.severed = False
    line.severed_until_epoch = None
    line.severed_by_son_id = None
    await session.flush()
    return line
