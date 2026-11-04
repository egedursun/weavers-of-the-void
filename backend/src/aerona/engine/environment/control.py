from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.biomes import Biome
from aerona.catalog.weather import WEATHER
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow, ForcedWeatherRow, LeyLineRow, NotableYearRow, PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import (
    CoastKind,
    MovementMode,
    NotableYearKind,
    PlaceCover,
    RiverClass,
    ScarKind,
    SoilKind,
    TemperatureBand,
    TerrainKind,
    WaterSource,
    WeatherKind,
)
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.calendar import epoch_start_year
from aerona.engine.environment.seasons import season_count_for
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

REGION_ENUMS: dict[str, type[StrEnum]] = {
    "dominant_terrain": TerrainKind,
    "temperature_band": TemperatureBand,
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
        "seasonality",
        "harvest_pct",
        "sacredness",
        "derived_fertility",
    }
)
LOCKABLE = frozenset(
    {
        "soil",
        "soil_base",
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
        "seasonality",
        "magic_density",
        "harvest_pct",
        "soil_fertility",
        "cleared",
        "farmed",
        "grazed",
        "mined",
        "built",
        "erosion",
        "sacredness",
        "temperature_band",
        "derived_fertility",
        "biome_mix",
    }
)
SCAR_PREFIX = "scar."
SEAM_PREFIX = "seam."
WORLD_SEAM = "world:"
BIOME_COUNT = len(Biome)
PLACE_ENUMS: dict[str, type[StrEnum]] = {"terrain": TerrainKind, "cover": PlaceCover, "water_source": WaterSource}
PLACE_NUMBERS = frozenset({"height_advantage", "soil_fertility"})
PASSABILITY_PREFIX = "passability."
PLACE_FLAGS = frozenset({"chokepoint", "nexus"})
PLACE_LOCKABLE = frozenset({"terrain", "cover", "water_source", "height_advantage", "chokepoint"})
INHERIT = "inherit"
HARVEST_MAX = 200
CAPS: dict[str, int] = {"harvest_pct": HARVEST_MAX}
MODES = frozenset(mode.value for mode in MovementMode)
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
        return clamp_int(value, 0, CAPS.get(field, PERCENT))
    raise ValidationFailedError(f"{field.replace('_', ' ')} cannot be set by hand.")


def set_passability(ground: RegionEnvironmentRow, field: str, value: int | str) -> None:
    mode = field.removeprefix(PASSABILITY_PREFIX)
    if mode not in MODES:
        raise ValidationFailedError(f"{mode.replace('_', ' ')} is not a way of moving.")
    if not isinstance(value, int):
        raise ValidationFailedError("Passability takes a whole number.")
    ground.passability = {**ground.passability, mode: clamp_int(value, 0, PERCENT)}


def set_region_field(ground: RegionEnvironmentRow, field: str, value: int | str, *, lock: bool) -> None:
    if field.startswith(PASSABILITY_PREFIX):
        set_passability(ground, field, value)
    else:
        setattr(ground, field, coerce(field, value, REGION_ENUMS, REGION_NUMBERS))
    locked = set(ground.locked)
    if lock and (field in LOCKABLE or field.startswith(PASSABILITY_PREFIX)):
        locked.add(field)
    ground.locked = sorted(locked)


def unlock_region_field(ground: RegionEnvironmentRow, field: str) -> bool:
    if field not in ground.locked:
        return False
    ground.locked = sorted(set(ground.locked) - {field})
    return True


def set_place_field(ground: PlaceEnvironmentRow, field: str, value: int | str | bool, *, lock: bool = True) -> None:
    if field in PLACE_FLAGS:
        setattr(ground, field, bool(value))
    elif isinstance(value, bool):
        raise ValidationFailedError(f"{field.replace('_', ' ')} does not take yes or no.")
    elif field == "terrain" and value == INHERIT:
        ground.terrain = None
    else:
        setattr(ground, field, coerce(field, value, PLACE_ENUMS, PLACE_NUMBERS))
    if lock and (field in PLACE_LOCKABLE or field == "nexus"):
        ground.locked = sorted({*ground.locked, field})


def unlock_place_field(ground: PlaceEnvironmentRow, field: str) -> bool:
    if field not in ground.locked:
        return False
    ground.locked = sorted(set(ground.locked) - {field})
    return True


def held(ground: RegionEnvironmentRow, field: str) -> bool:
    return field in ground.locked


def hold(ground: RegionEnvironmentRow, field: str, lock: bool) -> None:
    locked = set(ground.locked)
    if lock:
        locked.add(field)
    else:
        locked.discard(field)
    ground.locked = sorted(locked)


def set_scar(ground: RegionEnvironmentRow, kind: ScarKind, depth: int, *, lock: bool = False) -> None:
    scars = dict(ground.scars)
    if depth <= 0:
        scars.pop(kind.value, None)
    else:
        scars[kind.value] = clamp_int(depth, 0, PERCENT)
    ground.scars = scars
    hold(ground, f"{SCAR_PREFIX}{kind.value}", lock and depth > 0)


def world_seam(world_material_id: int) -> str:
    return f"{WORLD_SEAM}{world_material_id}"


def world_seam_id(key: str) -> int | None:
    return int(key.removeprefix(WORLD_SEAM)) if key.startswith(WORLD_SEAM) and key.removeprefix(WORLD_SEAM).isdigit() else None


def set_biome(ground: RegionEnvironmentRow, biome: int, share: int, *, lock: bool) -> None:
    if not 0 <= biome < BIOME_COUNT:
        raise ValidationFailedError("No such biome.")
    mix = [*ground.biome_mix, *([0] * max(0, BIOME_COUNT - len(ground.biome_mix)))]
    mix[biome] = clamp_int(share, 0, PERCENT)
    ground.biome_mix = mix
    hold(ground, "biome_mix", lock or "biome_mix" in ground.locked)


def set_mineral(ground: RegionEnvironmentRow, material: str, richness: int, *, lock: bool = False) -> None:
    layers = dict(ground.mineral_layers)
    if richness <= 0:
        layers.pop(material, None)
    else:
        layers[material] = clamp_int(richness, 0, PERCENT)
    ground.mineral_layers = layers
    hold(ground, f"{SEAM_PREFIX}{material}", lock and richness > 0)


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


async def forge_ley(session: AsyncSession, rules: Rules, first_id: int, second_id: int, *, epoch: int, strength: int | None = None) -> LeyLineRow:
    first, second = await session.get(EntityRow, first_id), await session.get(EntityRow, second_id)
    if first is None or second is None or first.entity_type is not EntityType.REGION or second.entity_type is not EntityType.REGION:
        raise NotFoundError("Both ends of a ley line must be regions.")
    if first.world_id != second.world_id or first.id == second.id:
        raise ValidationFailedError("A ley line joins two different regions of the same world.")
    if second.id not in (await RegionAtlas.load(session)).neighbour_regions(first.id):
        raise ValidationFailedError("A ley line only joins neighbouring regions.")
    low, high = sorted((first.id, second.id))
    line = await session.scalar(select(LeyLineRow).where(LeyLineRow.region_a_id == low, LeyLineRow.region_b_id == high))
    if line is None:
        line = LeyLineRow(world_id=first.world_id, region_a_id=low, region_b_id=high, strength=0, formed_epoch=epoch)
        session.add(line)
    line.forged = True
    line.strength = clamp_int(strength if strength is not None else rules.environment.forged_ley_strength, 0, PERCENT)
    line.severed = False
    line.severed_until_epoch = None
    line.severed_by_son_id = None
    await session.flush()
    return line


async def unforge_ley(session: AsyncSession, line_id: int) -> LeyLineRow:
    line = await ley_line(session, line_id)
    line.forged = False
    await session.flush()
    return line


async def restore_ley(session: AsyncSession, line_id: int) -> LeyLineRow:
    line = await ley_line(session, line_id)
    line.severed = False
    line.severed_until_epoch = None
    line.severed_by_son_id = None
    await session.flush()
    return line


async def force_weather(
    session: AsyncSession, region: EntityRow, kind: WeatherKind, *, from_epoch: int, epochs: int, season_position: int | None, son_id: int | None = None
) -> ForcedWeatherRow:
    if region.entity_type is not EntityType.REGION:
        raise ValidationFailedError("Weather is forced over a region.")
    row = ForcedWeatherRow(
        region_entity_id=region.id,
        world_id=region.world_id,
        from_epoch=max(1, from_epoch),
        until_epoch=max(1, from_epoch) + epochs - 1,
        season_position=season_position,
        kind=kind,
        son_id=son_id,
    )
    session.add(row)
    await session.flush()
    return row


async def release_weather(session: AsyncSession, forced_id: int) -> ForcedWeatherRow:
    row = await session.get(ForcedWeatherRow, forced_id)
    if row is None:
        raise NotFoundError("No such forced weather.")
    await session.delete(row)
    await session.flush()
    return row


NOTABLE_NAMES: dict[NotableYearKind, str] = {
    NotableYearKind.HUNGER: "the Hungry Year in {place}",
    NotableYearKind.PLENTY: "the Year of Plenty in {place}",
    NotableYearKind.WEATHER: "the Year of {weather}",
    NotableYearKind.PESTILENCE: "the Year of Pestilence in {place}",
}


async def force_notable_year(
    session: AsyncSession,
    rules: Rules,
    region: EntityRow,
    kind: NotableYearKind,
    *,
    epoch: int,
    magnitude: int,
    name: str | None,
    weather: WeatherKind | None,
) -> NotableYearRow:
    if region.entity_type is not EntityType.REGION:
        raise ValidationFailedError("A notable year is remembered by a region.")
    if kind is NotableYearKind.WEATHER and weather is None:
        raise ValidationFailedError("A year of weather needs its weather.")
    label = WEATHER[weather].label if weather is not None else ""
    row = NotableYearRow(
        world_id=region.world_id,
        region_entity_id=region.id,
        epoch=max(1, epoch),
        year=epoch_start_year(max(1, epoch), rules.time.years_per_epoch),
        kind=kind,
        weather=weather,
        name=name or NOTABLE_NAMES[kind].format(place=region.name, weather=label),
        magnitude=clamp_int(magnitude, 0, PERCENT),
    )
    session.add(row)
    await session.flush()
    return row
