from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import SkyEventRow, StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow, ForcedWeatherRow, PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import MovementMode, ScarKind, WeatherEffect
from aerona.domain.enums.world import SkyEventKind
from aerona.engine.environment.weather import Weather, WeatherInputs, weather_at, weather_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import shift_stat
from aerona.rules.registry import Rules

STAR_WIDE_SKY = frozenset({SkyEventKind.SUPERNOVA, SkyEventKind.BLACK_SUN, SkyEventKind.FLARE})


async def active_sky(session: AsyncSession, epoch: int) -> dict[int | None, frozenset[SkyEventKind]]:
    statement = select(SkyEventRow.world_id, SkyEventRow.star_id, SkyEventRow.kind).where(
        SkyEventRow.epoch <= epoch, (SkyEventRow.until_epoch.is_(None)) | (SkyEventRow.until_epoch >= epoch)
    )
    lit: dict[int, list[int]] = {}
    for lit_world_id, lit_star in await session.execute(select(WorldRow.id, WorldRow.star_id).where(WorldRow.star_id.is_not(None))):
        if lit_star is not None:
            lit.setdefault(lit_star, []).append(lit_world_id)
    found: dict[int | None, set[SkyEventKind]] = {}
    for world_id, star_id, kind in await session.execute(statement):
        found.setdefault(world_id, set()).add(kind)
        if kind in STAR_WIDE_SKY and star_id is not None:
            for lit_world in lit.get(star_id, []):
                found.setdefault(lit_world, set()).add(kind)
    return {world_id: frozenset(kinds) for world_id, kinds in found.items()}


async def forced_weather(session: AsyncSession, epoch: int) -> dict[int, list[ForcedWeatherRow]]:
    found: dict[int, list[ForcedWeatherRow]] = {}
    statement = select(ForcedWeatherRow).where(ForcedWeatherRow.from_epoch <= epoch, ForcedWeatherRow.until_epoch >= epoch)
    for row in await session.scalars(statement.order_by(ForcedWeatherRow.id.desc())):
        found.setdefault(row.region_entity_id, []).append(row)
    return found


@dataclass
class EnvironmentBook:
    rules: Rules
    atlas: RegionAtlas
    regions: dict[int, RegionEnvironmentRow]
    places: dict[int, PlaceEnvironmentRow]
    seasons: dict[int, list[WorldSeasonRow]]
    worlds: dict[int, WorldRow]
    calendars: dict[int, CalendarRow]
    sky: dict[int | None, frozenset[SkyEventKind]] = field(default_factory=dict)
    stars: dict[int, StarRow] = field(default_factory=dict)
    forced: dict[int, list[ForcedWeatherRow]] = field(default_factory=dict)
    living_places: frozenset[int] = frozenset()

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules, epoch: int, atlas: RegionAtlas | None = None) -> "EnvironmentBook":
        regions = {row.entity_id: row for row in await session.scalars(select(RegionEnvironmentRow))}
        places = {row.entity_id: row for row in await session.scalars(select(PlaceEnvironmentRow))}
        seasons: dict[int, list[WorldSeasonRow]] = {}
        for row in await session.scalars(select(WorldSeasonRow).order_by(WorldSeasonRow.world_id, WorldSeasonRow.position)):
            seasons.setdefault(row.world_id, []).append(row)
        worlds = {row.id: row for row in await session.scalars(select(WorldRow))}
        calendars = {row.knowledge_entity_id: row for row in await session.scalars(select(CalendarRow))}
        return cls(
            rules=rules,
            atlas=atlas or await RegionAtlas.load(session),
            regions=regions,
            places=places,
            seasons=seasons,
            worlds=worlds,
            calendars=calendars,
            sky=await active_sky(session, epoch),
            stars={row.id: row for row in await session.scalars(select(StarRow))},
            forced=await forced_weather(session, epoch),
            living_places=frozenset(
                await session.scalars(select(EntityRow.id).where(EntityRow.entity_type == EntityType.PLACE, EntityRow.status == EntityStatus.CANON))
            ),
        )

    def star_of(self, world: WorldRow) -> StarRow | None:
        return self.stars.get(world.star_id) if world.star_id is not None else None

    def region_of(self, entity_id: int | None) -> RegionEnvironmentRow | None:
        if entity_id is None:
            return None
        found = self.regions.get(entity_id)
        if found is not None:
            return found
        region_id = self.atlas.top_region(entity_id)
        return self.regions.get(region_id) if region_id is not None else None

    def place_of(self, entity_id: int | None) -> PlaceEnvironmentRow | None:
        return self.places.get(entity_id) if entity_id is not None else None

    def seasons_of(self, world_id: int) -> list[WorldSeasonRow]:
        return self.seasons.get(world_id, [])

    def season_at(self, world_id: int, index: int) -> WorldSeasonRow | None:
        seasons = self.seasons_of(world_id)
        return seasons[index % len(seasons)] if seasons else None

    def growing_season(self, world_id: int) -> WorldSeasonRow | None:
        seasons = self.seasons_of(world_id)
        return max(seasons, key=lambda season: (season.growth, -season.position)) if seasons else None

    def inputs(self, region: RegionEnvironmentRow, season: WorldSeasonRow | None) -> WeatherInputs:
        world = self.worlds.get(region.world_id)
        sky = self.sky.get(region.world_id, frozenset()) | self.sky.get(None, frozenset())
        scale = region.seasonality / PERCENT
        return WeatherInputs(
            region_id=region.entity_id,
            temperature=region.temperature,
            rainfall=region.rainfall,
            latitude=region.latitude,
            magic_density=region.magic_density,
            terrain=region.dominant_terrain,
            leakage=world.leakage if world is not None else 0,
            season_temperature=round(season.temperature_shift * scale) if season is not None else 0,
            season_rain=round(season.rain_shift * scale) if season is not None else 0,
            sky=sky,
        )

    def weather(self, world_seed: int, epoch: int, region: RegionEnvironmentRow, season: WorldSeasonRow | None, slot: str) -> Weather:
        for row in self.forced.get(region.entity_id, []):
            if row.from_epoch <= epoch <= row.until_epoch and (row.season_position is None or (season is not None and season.position == row.season_position)):
                return weather_of(self.rules, row.kind)
        return weather_at(self.rules, world_seed, epoch, slot, self.inputs(region, season))

    def travel_season(self, world_id: int) -> WorldSeasonRow | None:
        seasons = self.seasons_of(world_id)
        return max(seasons, key=lambda season: (season.travel, -season.position)) if seasons else None

    def footed(self, world_seed: int, epoch: int, region: RegionEnvironmentRow, mode: str, *, season: WorldSeasonRow | None, slot: str) -> int:
        base = region.passability.get(mode, PERCENT)
        weather = self.weather(world_seed, epoch, region, season, slot)
        footing = sail_factor(self.rules, weather.effect(WeatherEffect.WIND)) if mode == MovementMode.BOAT.value else weather.factor(WeatherEffect.FOOTING)
        travel = season.travel / PERCENT if season is not None else 1.0
        return clamp_int(base * max(0.0, footing) * travel, 0, PERCENT)

    def clarity(self, world_seed: int, epoch: int, world_id: int, slot: str) -> float:
        regions = [region for region in self.regions.values() if region.world_id == world_id]
        if not regions:
            return 1.0
        season = self.season_at(world_id, epoch)
        seen = [self.weather(world_seed, epoch, region, season, slot).factor(WeatherEffect.VISIBILITY) for region in regions]
        return max(0.0, min(1.0, sum(seen) / len(seen)))

    def calendar_holders(self) -> dict[int, CalendarRow]:
        return dict(self.calendars)


def sail_factor(rules: Rules, wind: int) -> float:
    best = max(1, rules.weather.sail_best_wind)
    sail = wind / best if wind <= best else max(0.0, 1 - (wind - best) / max(1, PERCENT - best))
    return 1 + rules.weather.sail_speed_pct / PERCENT * (sail * 2 - 1)


def add_scar(region: RegionEnvironmentRow, kind: ScarKind, depth: int) -> int:
    if f"scar.{kind.value}" in region.locked:
        return region.scars.get(kind.value, 0)
    scars = dict(region.scars)
    scars[kind.value] = clamp_int(scars.get(kind.value, 0) + depth, 0, PERCENT)
    region.scars = scars
    return scars[kind.value]


def season_attrition(rules: Rules, weather: Weather, *, armour_pct: int, acclimatised: bool) -> float:
    settings = rules.environment
    cold = weather.effect(WeatherEffect.COLD) * (settings.attrition_armour_base_pct + armour_pct) / PERCENT
    heat = weather.effect(WeatherEffect.HEAT) * (settings.attrition_armour_base_pct + armour_pct) / PERCENT
    exposure = (cold + heat) * settings.attrition_exposure_pct / PERCENT / PERCENT
    return exposure * (settings.acclimatised_attrition_pct / PERCENT if acclimatised else 1.0)


async def region_environment(session: AsyncSession, entity_id: int) -> RegionEnvironmentRow | None:
    found = await session.get(RegionEnvironmentRow, entity_id)
    if found is not None:
        return found
    region_id = (await RegionAtlas.load(session)).top_region(entity_id)
    return await session.get(RegionEnvironmentRow, region_id) if region_id is not None else None


SCAR_DANGER: dict[ScarKind, Callable[[Rules], int]] = {
    ScarKind.HAUNTED: lambda rules: rules.scars.haunted_danger_pct,
    ScarKind.LEAK_WOUND: lambda rules: rules.scars.leak_wound_danger_pct,
}


async def scar_region(session: AsyncSession, rules: Rules, region: RegionEnvironmentRow, kind: ScarKind, depth: int) -> int:
    value = add_scar(region, kind, depth)
    danger = SCAR_DANGER.get(kind)
    if danger is not None:
        entity = await session.get(EntityRow, region.entity_id)
        if entity is not None:
            shift_stat(entity, "danger", round(depth * danger(rules) / PERCENT))
    return value
