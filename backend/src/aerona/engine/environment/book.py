from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import SkyEventRow, StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow, PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.environment import ScarKind, WeatherEffect
from aerona.domain.enums.world import SkyEventKind
from aerona.engine.environment.weather import Weather, WeatherInputs, weather_at
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
        return weather_at(self.rules, world_seed, epoch, slot, self.inputs(region, season))

    def calendar_holders(self) -> dict[int, CalendarRow]:
        return dict(self.calendars)


def scar_depth(region: RegionEnvironmentRow | None, kind: ScarKind) -> int:
    return region.scars.get(kind.value, 0) if region is not None else 0


def add_scar(region: RegionEnvironmentRow, kind: ScarKind, depth: int) -> int:
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
