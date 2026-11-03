from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import delete, func, select

from aerona.cartography.biomes import Biome
from aerona.cartography.model import RegionRecord
from aerona.catalog.place_terrain import place_profile
from aerona.catalog.weather import WEATHER
from aerona.constants.cartography import BIOME_COUNT
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow, LeyLineRow, NotableYearRow, PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityType
from aerona.domain.enums.environment import CoastKind, LandUse, NotableYearKind, RiverClass, ScarKind, SoilKind, WeatherEffect, WeatherKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.world import ClimateEra, Discovery
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.star_types import star_heat
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.ley import LeyWeb, candidate_lines, cut_by_land, pair
from aerona.engine.environment.notable import backfill_notable_years
from aerona.engine.environment.profile import (
    Geography,
    Ground,
    Surroundings,
    TerrainReading,
    Works,
    band_of,
    climate_factor,
    defensibility_of,
    disease_load_of,
    fertility_from,
    mineral_layers,
    natural_soil,
    passability_of,
    rainfall_of,
    seasonality_of,
    soil_for,
    soil_of,
    temperature_of,
    terrain_of,
)
from aerona.engine.environment.seasons import season_drafts, tidal_strength, world_calendar
from aerona.engine.environment.years import SampledYear, grant_sub_steps, sampled_years
from aerona.engine.phase import Phase
from aerona.engine.primitives.capacity import LAND_COMMUNITY_TYPES, CapacityModel, RegionKey, RegionLoad
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap, knowledge_level
from aerona.engine.primitives.map_store import stored_regions
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, canon, flags_by_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

GEOGRAPHY_FIELDS = ("biome_mix", "elevation_mean", "roughness", "latitude", "moisture", "base_forest", "base_wetland", "river_class", "coast_kind")
HIGHLAND_BIOMES = (Biome.DRY_HILLS, Biome.WET_HILLS, Biome.MOUNTAINS, Biome.PEAKS)
EXTREME_WEATHER = frozenset(
    {
        WeatherKind.BLIZZARD,
        WeatherKind.HAIL,
        WeatherKind.SANDSTORM,
        WeatherKind.MAGIC_STORM,
        WeatherKind.ASH_FALL,
        WeatherKind.VOID_RAIN,
        WeatherKind.ECLIPSE_DARK,
        WeatherKind.HEAT_WAVE,
    }
)


def fallback_geography(rules: Rules, region: EntityRow) -> Geography:
    settings = rules.environment
    mix = [0] * BIOME_COUNT
    mix[Biome.DEEP_WATER if region.is_water else Biome.MID_LOWLAND] = PERCENT
    return Geography(
        biome_mix=mix,
        elevation_mean=0 if region.is_water else settings.unmapped_elevation,
        roughness=0 if region.is_water else settings.unmapped_roughness,
        latitude=settings.unmapped_latitude,
        moisture=settings.ideal_rainfall,
        base_forest=0 if region.is_water else settings.unmapped_forest,
        base_wetland=0,
        river_class=RiverClass.NONE,
    )


def mapped_geography(record: RegionRecord) -> Geography | None:
    found = record.geography
    if found is None:
        return None
    return Geography(
        biome_mix=list(found.biome_mix),
        elevation_mean=found.elevation_mean,
        roughness=found.roughness,
        latitude=found.latitude,
        moisture=found.moisture,
        base_forest=found.forest,
        base_wetland=found.wetland,
        river_class=found.river_class,
    )


def geography_of(env: RegionEnvironmentRow) -> Geography:
    return Geography(
        biome_mix=list(env.biome_mix),
        elevation_mean=env.elevation_mean,
        roughness=env.roughness,
        latitude=env.latitude,
        moisture=env.moisture,
        base_forest=env.base_forest,
        base_wetland=env.base_wetland,
        river_class=env.river_class,
    )


def is_highland(rules: Rules, geography: Geography) -> bool:
    return sum(geography.biome_mix[biome] for biome in HIGHLAND_BIOMES) >= rules.environment.terrain_dominant_share_pct


@dataclass
class RegionContext:
    world: WorldRow
    era: ClimateEra | None
    ruins: int
    chokepoints: int
    star: StarRow | None = None
    works: Works = field(default_factory=Works)

    def surroundings(self, rules: Rules, env: RegionEnvironmentRow) -> Surroundings:
        return Surroundings(
            world_type=self.world.world_type,
            era=self.era,
            coastal=env.coast_kind is not CoastKind.NONE,
            highland=is_highland(rules, geography_of(env)),
            ruins=self.ruins,
            chokepoints=self.chokepoints,
            star_heat=star_heat(rules, self.star),
            works=self.works,
        )


def factor_of(rules: Rules, env: RegionEnvironmentRow, works: Works) -> float:
    return climate_factor(rules, temperature=env.temperature, rainfall=env.rainfall, river=env.river_class, scars=env.scars, works=works)


def apply_geography(env: RegionEnvironmentRow, geography: Geography, coast: CoastKind) -> None:
    locked = set(env.locked)
    values = {
        "biome_mix": geography.biome_mix,
        "elevation_mean": geography.elevation_mean,
        "roughness": geography.roughness,
        "latitude": geography.latitude,
        "moisture": geography.moisture,
        "base_forest": geography.base_forest,
        "base_wetland": geography.base_wetland,
        "river_class": geography.river_class,
        "coast_kind": coast,
    }
    for key, value in values.items():
        if key not in locked:
            setattr(env, key, value)


def refresh_climate(rules: Rules, env: RegionEnvironmentRow, around: Surroundings, axial_tilt: int, tides: int = 0) -> None:
    locked = set(env.locked)
    geography = geography_of(env)
    if "temperature" not in locked:
        env.temperature = temperature_of(rules, geography, around)
    if "rainfall" not in locked:
        env.rainfall = rainfall_of(rules, geography, around)
    env.temperature_band = band_of(rules, env.temperature)
    if "seasonality" not in locked:
        env.seasonality = seasonality_of(rules, env.latitude, axial_tilt)
    if "wetland" not in locked:
        env.wetland = clamp_int(env.base_wetland * (PERCENT + (env.rainfall - rules.environment.ideal_rainfall)) / PERCENT, 0, PERCENT)
    if "forest_cover" not in locked:
        env.forest_cover = clamp_int(env.base_forest * (PERCENT - env.cleared) / PERCENT, 0, PERCENT)
    if "dominant_terrain" not in locked:
        reading = TerrainReading(geography, around, env.temperature, env.rainfall, env.wetland, env.built)
        env.dominant_terrain = terrain_of(rules, reading)
    held = {key.removeprefix("passability."): env.passability.get(key.removeprefix("passability.")) for key in locked if key.startswith("passability.")}
    ground = Ground(
        roughness=env.roughness,
        forest=env.forest_cover,
        wetland=env.wetland,
        river=env.river_class,
        temperature=env.temperature,
        coast=env.coast_kind,
        terrain=env.dominant_terrain,
        tides=tides,
        works=around.works,
    )
    fresh = passability_of(rules, ground)
    env.passability = {**fresh, **{mode: value for mode, value in held.items() if value is not None}}
    if "defensibility" not in locked:
        env.defensibility = defensibility_of(rules, roughness=env.roughness, forest=env.forest_cover, river=env.river_class, chokepoints=around.chokepoints)


def new_region_environment(ctx: TickContext, region: EntityRow, geography: Geography, coast: CoastKind, context: RegionContext) -> RegionEnvironmentRow:
    rules = ctx.rules
    soil = soil_of(rules, geography, context.world.world_type, geography.base_wetland)
    base = natural_soil(rules, soil, geography.moisture)
    env = RegionEnvironmentRow(
        entity_id=region.id,
        world_id=region.world_id,
        surveyed=False,
        biome_mix=geography.biome_mix,
        elevation_mean=geography.elevation_mean,
        roughness=geography.roughness,
        latitude=geography.latitude,
        moisture=geography.moisture,
        base_forest=geography.base_forest,
        forest_cover=geography.base_forest,
        base_wetland=geography.base_wetland,
        wetland=geography.base_wetland,
        river_class=geography.river_class,
        coast_kind=coast,
        soil=soil,
        soil_fertility=base,
        soil_base=base,
        temperature=0,
        temperature_band=band_of(rules, 0),
        rainfall=0,
        seasonality=0,
        disease_load=0,
        mineral_layers={},
        magic_density=clamp_int(stat_or(region, "magic", 0), 0, PERCENT),
        passability={},
        defensibility=0,
        scars={},
        cleared=0,
        farmed=0,
        grazed=0,
        mined=0,
        built=0,
        erosion=0,
        harvest_pct=PERCENT,
        derived_fertility=None,
        locked=[],
    )
    around = context.surroundings(rules, env)
    refresh_climate(rules, env, around, context.world.axial_tilt or 0, context.world.tidal_strength or 0)
    env.mineral_layers = mineral_layers(rules, ctx.environment.rng(f"minerals.{region.id}"), geography, context.world.world_type, env.dominant_terrain)
    fertility = stat(region, "fertility")
    if fertility is not None:
        env.soil_fertility = soil_for(fertility, factor_of(rules, env, context.works))
        env.soil_base = env.soil_fertility
        env.derived_fertility = fertility
    return env


def new_place_environment(rules: Rules, place: EntityRow, region_id: int | None, factor: float) -> PlaceEnvironmentRow:
    profile = place_profile(place.subtype)
    fertility = stat(place, "fertility")
    soil = soil_for(fertility, factor) if fertility is not None else rules.environment.ideal_rainfall
    return PlaceEnvironmentRow(
        entity_id=place.id,
        region_entity_id=region_id,
        terrain=profile.terrain,
        cover=profile.cover,
        water_source=profile.water,
        height_advantage=clamp_int(profile.height(rules), 0, PERCENT),
        chokepoint=profile.chokepoint,
        soil_fertility=soil,
        derived_fertility=fertility,
        locked=[],
    )


async def moons_by_world(ctx: TickContext) -> Counter[int]:
    statement = select(WorldRow.parent_world_id, func.count()).where(WorldRow.parent_world_id.is_not(None)).group_by(WorldRow.parent_world_id)
    rows = await ctx.session.execute(statement)
    return Counter({parent: count for parent, count in rows if parent is not None})


async def ensure_world_calendar(ctx: TickContext, world: WorldRow, moons: int) -> bool:
    rules = ctx.rules
    created = False
    if world.axial_tilt is None or world.season_count is None or world.year_length_days is None or world.day_length_hours is None:
        calendar = world_calendar(rules, ctx.environment.rng(f"calendar.{world.id}"), world.world_type, world.orbit)
        world.axial_tilt = calendar.axial_tilt if world.axial_tilt is None else world.axial_tilt
        world.year_length_days = calendar.year_length_days if world.year_length_days is None else world.year_length_days
        world.day_length_hours = calendar.day_length_hours if world.day_length_hours is None else world.day_length_hours
        world.season_count = calendar.season_count if world.season_count is None else world.season_count
        created = True
    world.moon_count = moons
    world.tidal_strength = tidal_strength(rules, moons)
    existing = await ctx.session.scalar(select(func.count()).select_from(WorldSeasonRow).where(WorldSeasonRow.world_id == world.id))
    if not existing:
        await write_seasons(ctx, world)
        created = True
    return created


async def write_seasons(ctx: TickContext, world: WorldRow) -> list[WorldSeasonRow]:
    await ctx.session.execute(delete(WorldSeasonRow).where(WorldSeasonRow.world_id == world.id))
    rows = [
        WorldSeasonRow(
            world_id=world.id,
            position=draft.position,
            name=draft.name,
            temperature_shift=draft.temperature_shift,
            rain_shift=draft.rain_shift,
            growth=draft.growth,
            travel=draft.travel,
            campaign=draft.campaign,
            edited=False,
        )
        for draft in season_drafts(ctx.rules, world.world_type, world.season_count or 1, world.axial_tilt or 0)
    ]
    ctx.session.add_all(rows)
    await ctx.session.flush()
    return rows


BRIDGE_SUBTYPE = "bridge"
HARBOUR_SUBTYPE = "harbour"


async def works_by_region(ctx: TickContext, book: EnvironmentBook) -> dict[int, Works]:
    knowledge = await KnowledgeMap.load(ctx.session)
    tallies: dict[int, Counter[str]] = {}
    for entity in await canon(ctx.session, [EntityType.STRUCTURE, EntityType.SETTLEMENT]):
        region_id = book.atlas.top_region(entity.id)
        if region_id is None:
            continue
        tally = tallies.setdefault(region_id, Counter())
        subtype = (entity.subtype or "").lower()
        if entity.entity_type is EntityType.STRUCTURE:
            tally["bridges"] += BRIDGE_SUBTYPE in subtype
            tally["harbours"] += HARBOUR_SUBTYPE in subtype
            continue
        tally["roads"] += knowledge.knows(entity.id, KnowledgeBranch.ARCHITECTURE)
        tally["irrigation"] += knowledge.level(entity.id, KnowledgeBranch.AGRICULTURE) >= ctx.rules.environment.irrigation_agriculture_level
    return {
        region_id: Works(roads=tally["roads"], bridges=tally["bridges"], harbours=tally["harbours"], irrigation=tally["irrigation"])
        for region_id, tally in tallies.items()
    }


async def region_contexts(ctx: TickContext, book: EnvironmentBook, regions: list[EntityRow]) -> dict[int, RegionContext]:
    ruined = await flags_by_entity(ctx.session, EntityFlag.RUIN)
    ruins: Counter[int] = Counter()
    for entity_id in ruined:
        top = book.atlas.top_region(entity_id)
        if top is not None:
            ruins[top] += 1
    chokepoints: Counter[int] = Counter()
    for place in book.places.values():
        if place.chokepoint and place.region_entity_id is not None:
            chokepoints[place.region_entity_id] += 1
    works = await works_by_region(ctx, book)
    contexts: dict[int, RegionContext] = {}
    for region in regions:
        world = book.worlds.get(region.world_id)
        if world is None:
            continue
        contexts[region.id] = RegionContext(
            world=world,
            era=world.climate_era,
            ruins=ruins[region.id],
            chokepoints=chokepoints[region.id],
            star=book.star_of(world),
            works=works.get(region.id, Works()),
        )
    return contexts


async def environment_survey(ctx: TickContext) -> None:
    ctx.count("notable_years_backfilled", await backfill_notable_years(ctx))
    moons = await moons_by_world(ctx)
    worlds = list(await ctx.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)))
    calendars = 0
    for world in worlds:
        calendars += int(await ensure_world_calendar(ctx, world, moons[world.id]))
    records = {record.id: record for world_records in (await stored_regions(ctx.session)).values() for record in world_records}
    book = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
    regions = await canon(ctx.session, [EntityType.REGION])
    contexts = await region_contexts(ctx, book, regions)
    created = synced = 0
    fresh: list[RegionEnvironmentRow] = []
    for region in regions:
        context = contexts.get(region.id)
        if context is None:
            continue
        record = records.get(region.id)
        mapped = mapped_geography(record) if record is not None else None
        coast = record.geography.coast_kind if record is not None and record.geography is not None else CoastKind.NONE
        env = book.regions.get(region.id)
        if env is None:
            env = new_region_environment(ctx, region, mapped or fallback_geography(ctx.rules, region), coast, context)
            env.surveyed = mapped is not None
            ctx.session.add(env)
            book.regions[region.id] = env
            fresh.append(env)
            created += 1
        elif mapped is not None:
            apply_geography(env, mapped, coast)
            if not env.surveyed:
                env.mineral_layers = mineral_layers(
                    ctx.rules, ctx.environment.rng(f"minerals.{region.id}"), mapped, context.world.world_type, env.dominant_terrain
                )
            env.surveyed = True
            synced += 1
    await ctx.session.flush()
    await settle_new_ground(ctx, fresh)
    placed = 0
    for place in await canon(ctx.session, [EntityType.PLACE]):
        if place.id in book.places:
            continue
        region_id = book.atlas.top_region(place.id)
        env = book.regions.get(region_id) if region_id is not None else None
        context = contexts.get(region_id) if region_id is not None else None
        factor = factor_of(ctx.rules, env, context.works if context is not None else Works()) if env is not None else 1.0
        row = new_place_environment(ctx.rules, place, region_id, factor)
        ctx.session.add(row)
        book.places[place.id] = row
        placed += 1
    await ctx.session.flush()
    ctx.count("worlds_given_seasons", calendars)
    ctx.count("regions_surveyed", created)
    ctx.count("regions_resynced", synced)
    ctx.count("places_surveyed", placed)


def decay_scars(rules: Rules, env: RegionEnvironmentRow) -> None:
    settings = rules.scars
    decay = {
        ScarKind.BATTLEFIELD: settings.battlefield_decay,
        ScarKind.PLAGUE_GROUND: settings.plague_ground_decay,
        ScarKind.SALTED_EARTH: settings.salted_earth_decay,
        ScarKind.BURNED: settings.burned_decay,
        ScarKind.CRATER: settings.crater_decay,
        ScarKind.HAUNTED: settings.haunted_decay,
        ScarKind.BLIGHTED: settings.blighted_decay,
        ScarKind.LEAK_WOUND: settings.leak_wound_decay,
    }
    kept = {key: depth - decay[ScarKind(key)] for key, depth in env.scars.items() if depth - decay[ScarKind(key)] > 0}
    if kept != env.scars:
        env.scars = kept


def fold_external(env_fertility: int | None, current: int | None, soil: int) -> int:
    if env_fertility is None or current is None or current == env_fertility:
        return soil
    return clamp_int(soil + current - env_fertility, 0, PERCENT)


def recover_soil(rules: Rules, env: RegionEnvironmentRow) -> None:
    settings = rules.climate_effects
    gap = env.soil_base - env.soil_fertility
    divisor = settings.fertility_recovery_divisor if gap > 0 else settings.fertility_decline_divisor
    env.soil_fertility = clamp_int(env.soil_fertility + gap / divisor, 0, PERCENT)


async def sanitation_by_region(ctx: TickContext, book: EnvironmentBook, communities: list[EntityRow]) -> dict[int, int]:
    knowledge = await KnowledgeMap.load(ctx.session)
    weighted: Counter[int] = Counter()
    totals: Counter[int] = Counter()
    for community in communities:
        region_id = book.atlas.top_region(community.id)
        if region_id is None:
            continue
        population = stat_or(community, "population", 0)
        totals[region_id] += population
        level = knowledge.level(community.id, KnowledgeBranch.MEDICINE)
        builder = community.entity_type is EntityType.SETTLEMENT and knowledge.knows(community.id, KnowledgeBranch.ARCHITECTURE)
        share = level * ctx.rules.environment.sanitation_medicine_step + (ctx.rules.environment.sanitation_architecture if builder else 0)
        weighted[region_id] += population * min(ctx.rules.environment.sanitation_cap_pct, share)
    return {region_id: round_half_up(weighted[region_id] / totals[region_id]) for region_id in totals if totals[region_id]}


async def environment_derive(ctx: TickContext) -> None:
    rules = ctx.rules
    book = await EnvironmentBook.load(ctx.session, rules, ctx.epoch)
    regions = await canon(ctx.session, [EntityType.REGION])
    contexts = await region_contexts(ctx, book, regions)
    capacity = await CapacityModel.load(ctx.session, rules)
    communities = await canon(ctx.session, LAND_COMMUNITY_TYPES)
    loads = capacity.build_loads(communities)
    sanitation = await sanitation_by_region(ctx, book, communities)
    derived = 0
    for region in regions:
        env = book.regions.get(region.id)
        context = contexts.get(region.id)
        if env is None or context is None:
            continue
        decay_scars(rules, env)
        if "magic_density" not in env.locked:
            env.magic_density = clamp_int(stat_or(region, "magic", env.magic_density), 0, PERCENT)
        around = context.surroundings(rules, env)
        refresh_climate(rules, env, around, context.world.axial_tilt or 0, context.world.tidal_strength or 0)
        load = loads.get(("region", region.id))
        density = 0
        if load is not None and load.communities:
            ceiling = max(1.0, capacity.capacity(load, load.communities[0], capacity.effective_fertility(load.communities[0])))
            density = clamp_int(load.population / ceiling * PERCENT, 0, PERCENT)
        if "disease_load" not in env.locked:
            env.disease_load = disease_load_of(
                rules,
                temperature=env.temperature,
                wetland=env.wetland,
                built=env.built,
                density_pct=density,
                sanitation_pct=sanitation.get(region.id, 0),
                scars=env.scars,
            )
        current = stat(region, "fertility")
        env.soil_fertility = fold_external(env.derived_fertility, current, env.soil_fertility)
        recover_soil(rules, env)
        if current is not None or not region.is_water:
            set_stats(region, fertility=fertility_from(env.soil_fertility, factor_of(rules, env, context.works)))
            env.derived_fertility = stat(region, "fertility")
            derived += 1
    for place_env in book.places.values():
        place = await ctx.session.get(EntityRow, place_env.entity_id)
        env = book.region_of(place_env.region_entity_id)
        context = contexts.get(place_env.region_entity_id) if place_env.region_entity_id is not None else None
        if place is None or env is None or context is None or stat(place, "fertility") is None:
            continue
        place_env.soil_fertility = fold_external(place_env.derived_fertility, stat(place, "fertility"), place_env.soil_fertility)
        set_stats(place, fertility=fertility_from(place_env.soil_fertility, factor_of(rules, env, context.works)))
        place_env.derived_fertility = stat(place, "fertility")
    await ctx.session.flush()
    ctx.count("regions_derived", derived)


def land_target(value: float) -> int:
    return clamp_int(value, 0, PERCENT)


def drift(current: int, target: int, divisor: int) -> int:
    return clamp_int(current + (target - current) / max(1, divisor), 0, PERCENT)


def work_land(rules: Rules, env: RegionEnvironmentRow, capacity: CapacityModel, load: RegionLoad, divisor: int) -> None:
    settings = rules.land_use
    community = load.communities[0]
    ceiling = max(1.0, capacity.capacity(load, community, capacity.effective_fertility(community)))
    occupancy = load.population / ceiling * PERCENT
    farming = load.agriculture / load.population
    settled = sum(stat_or(item, "population", 0) for item in load.communities if item.entity_type is EntityType.SETTLEMENT)
    env.farmed = drift(env.farmed, land_target(occupancy * farming * settings.farm_target_pct / PERCENT), divisor)
    env.grazed = drift(env.grazed, land_target(occupancy * (1 - farming) * settings.graze_target_pct / PERCENT), divisor)
    env.built = drift(env.built, land_target(settled / settings.built_population_per_pct), divisor)
    cleared = env.farmed + env.built * settings.cleared_built_pct / PERCENT + env.grazed * settings.cleared_grazed_pct / PERCENT
    env.cleared = drift(env.cleared, land_target(cleared), divisor)


async def settle_new_ground(ctx: TickContext, created: list[RegionEnvironmentRow]) -> None:
    if not created:
        return
    capacity = await CapacityModel.load(ctx.session, ctx.rules)
    loads = capacity.build_loads(await canon(ctx.session, LAND_COMMUNITY_TYPES))
    for env in created:
        load = loads.get(("region", env.entity_id))
        if load is not None and load.population > 0:
            work_land(ctx.rules, env, capacity, load, 1)
            env.forest_cover = clamp_int(env.base_forest * (PERCENT - env.cleared) / PERCENT, 0, PERCENT)


@dataclass(frozen=True)
class LandMark:
    erosion: int
    farmed: int
    soil: int
    cleared: int


def land_turns(rules: Rules, env: RegionEnvironmentRow, before: LandMark) -> list[tuple[str, str]]:
    settings = rules.land_use
    turns: list[tuple[str, str]] = []
    if before.erosion < settings.erosion_noted <= env.erosion:
        turns.append(("land.erosion", "Rains wash the cleared slopes of {region} down to the rivers; the hills are going bare."))
    if before.farmed <= settings.overfarm_threshold < env.farmed:
        turns.append(("land.overfarmed", "Every field of {region} is ploughed year after year and the earth is given no rest."))
    if before.soil >= settings.exhausted_soil_below > env.soil_fertility:
        turns.append(("land.soil_exhausted", "The soil of {region} is worn out; seed goes in and little comes back."))
    if before.cleared > 0 == env.cleared:
        turns.append(("land.rewilded", "Forest and scrub have taken back the empty fields of {region}."))
    return turns


async def note_land(ctx: TickContext, env: RegionEnvironmentRow, before: LandMark) -> None:
    turns = land_turns(ctx.rules, env, before)
    if not turns:
        return
    region = await ctx.session.get(EntityRow, env.entity_id)
    if region is None:
        return
    for key, text in turns:
        await ctx.chronicle(
            ChronicleKind.CLIMATE,
            text.format(region=region.name),
            template_key=key,
            entity_ids=[region.id],
            world_id=region.world_id,
            place_entity_id=region.id,
            feed_category=FeedCategory.WORLD,
        )


async def land_use(ctx: TickContext) -> None:
    rules = ctx.rules
    settings = rules.land_use
    book = await EnvironmentBook.load(ctx.session, rules, ctx.epoch)
    capacity = await CapacityModel.load(ctx.session, rules)
    loads = capacity.build_loads(await canon(ctx.session, LAND_COMMUNITY_TYPES))
    worked = rewilded = 0
    for region_id, env in book.regions.items():
        before = LandMark(env.erosion, env.farmed, env.soil_fertility, env.cleared)
        load = loads.get(("region", region_id))
        if load is None or load.population <= 0:
            for key in LandUse:
                setattr(env, key.value, max(0, getattr(env, key.value) - settings.rewild_rate))
            rewilded += 1
        else:
            work_land(rules, env, capacity, load, settings.drift_divisor)
            worked += 1
        env.erosion = (
            clamp_int(env.cleared * env.roughness / PERCENT * settings.erosion_pct / PERCENT, 0, PERCENT) if env.roughness >= settings.erosion_roughness else 0
        )
        loss = env.erosion * settings.erosion_soil_pct / PERCENT
        if env.farmed > settings.overfarm_threshold:
            loss += (env.farmed - settings.overfarm_threshold) * settings.overfarm_soil_pct / PERCENT
        env.soil_fertility = clamp_int(env.soil_fertility - loss, 0, PERCENT)
        await note_land(ctx, env, before)
    await ctx.session.flush()
    ctx.count("regions_worked", worked)
    ctx.count("regions_rewilding", rewilded)


@dataclass(frozen=True)
class YearHarvest:
    offset: int
    year: int
    harvest: int
    weather: WeatherKind


async def calendar_regions(ctx: TickContext, book: EnvironmentBook) -> set[int]:
    if not book.calendars:
        return set()
    regions: set[int] = set()
    for bond in await active_bonds(ctx.session, [BondKind.KNOWS], targets=list(book.calendars)):
        region_id = book.atlas.top_region(bond.source_node_id)
        if region_id is not None:
            regions.add(region_id)
    return regions


def year_harvest(rules: Rules, *, growth: int, weather_growth: int, farming: float, agriculture: float, planned: bool, blight: int, soil: int) -> int:
    settings = rules.harvest
    value = (
        PERCENT
        * growth
        / max(1, settings.normal_growth)
        * max(0.0, 1 + settings.soil_weight_pct / PERCENT * (soil / max(1, settings.normal_soil) - 1))
        * (1 + weather_growth / PERCENT)
        * (1 + farming * (agriculture - 1))
        * (1 + (settings.calendar_planning_pct / PERCENT if planned else 0))
        * (1 - min(PERCENT, blight) * rules.scars.blighted_fertility_pct / PERCENT / PERCENT)
    )
    return clamp_int(value, 0, settings.harvest_max_pct)


@dataclass(frozen=True)
class Notable:
    kind: NotableYearKind
    year: YearHarvest
    magnitude: int
    name: str
    text: str


async def record_notable(ctx: TickContext, world: WorldRow, region: EntityRow | None, notable: Notable) -> NotableYearRow:
    written = await ctx.chronicle(
        ChronicleKind.CLIMATE,
        notable.text,
        template_key=f"year.{notable.kind.value}",
        entity_ids=[region.id] if region is not None else [],
        world_id=world.id,
        feed_category=FeedCategory.WORLD,
        place_entity_id=region.id if region is not None else None,
        magnitude=notable.magnitude,
        year=notable.year.year,
    )
    row = NotableYearRow(
        world_id=world.id,
        region_entity_id=region.id if region is not None else None,
        epoch=ctx.epoch,
        year=notable.year.year,
        kind=notable.kind,
        weather=notable.year.weather,
        name=notable.name,
        magnitude=notable.magnitude,
        incident_id=written.incident_id,
    )
    ctx.session.add(row)
    return row


async def famine_event(ctx: TickContext, region: EntityRow, communities: list[EntityRow], name: str, magnitude: int) -> EntityRow:
    event = await create_record(
        ctx,
        RecordSpec(
            name=name[:1].upper() + name[1:],
            entity_type=EntityType.EVENT,
            stats=EventStats(severity=clamp_int(magnitude, 0, PERCENT)),
            body=f"A year of empty granaries in {region.name}.",
            power=ctx.rules.harvest.famine_event_power,
            world_id=region.world_id,
            location_id=region.id,
            subtype="famine",
            engine_kind=EngineKind.FAMINE,
            flags=(EntityFlag.DISASTER,),
        ),
    )
    bonds = BondRepository(ctx.session)
    for community in communities:
        await bonds.connect(BondDraft(event.id, community.id, BondKind.CAUSED, ctx.epoch, "went hungry"))
    return event


@dataclass
class HarvestSeason:
    book: EnvironmentBook
    loads: dict[RegionKey, RegionLoad]
    knowledge: KnowledgeMap
    planned: set[int]
    growing: WorldSeasonRow | None
    years: list[SampledYear]
    worst_weather: tuple[int, YearHarvest, RegionEnvironmentRow] | None = None
    best_plenty: tuple[YearHarvest, RegionEnvironmentRow] | None = None


def region_years(ctx: TickContext, season: HarvestSeason, env: RegionEnvironmentRow) -> list[YearHarvest]:
    rules = ctx.rules
    load = season.loads[("region", env.entity_id)]
    farming = load.agriculture / load.population if load.population else 0.0
    agriculture = max((season.knowledge.effect(rules, community.id, KnowledgeBranch.AGRICULTURE) for community in load.communities), default=1.0) or 1.0
    growth = season.growing.growth if season.growing is not None else rules.harvest.normal_growth
    results: list[YearHarvest] = []
    for sampled in season.years:
        weather = season.book.weather(ctx.environment.world_seed, ctx.epoch, env, season.growing, f"year.{sampled.offset}")
        value = year_harvest(
            rules,
            growth=growth,
            weather_growth=weather.effect(WeatherEffect.GROWTH),
            farming=farming,
            agriculture=agriculture,
            planned=env.entity_id in season.planned,
            blight=env.scars.get(ScarKind.BLIGHTED.value, 0),
            soil=env.soil_fertility,
        )
        results.append(YearHarvest(sampled.offset, sampled.year, value, weather.kind))
        severity = -weather.effect(WeatherEffect.GROWTH) - weather.effect(WeatherEffect.MORALE)
        if weather.kind in EXTREME_WEATHER and (season.worst_weather is None or severity > season.worst_weather[0]):
            season.worst_weather = (severity, results[-1], env)
    return results


async def region_harvest(ctx: TickContext, world: WorldRow, season: HarvestSeason, env: RegionEnvironmentRow) -> int:
    settings = ctx.rules.harvest
    results = region_years(ctx, season, env)
    if "harvest_pct" not in env.locked:
        env.harvest_pct = round_half_up(sum(item.harvest for item in results) / len(results))
    region = await ctx.session.get(EntityRow, env.entity_id)
    if region is None:
        return 0
    found = 0
    worst = min(results, key=lambda item: (item.harvest, item.offset))
    if worst.harvest < settings.notable_threshold:
        name = f"the Hungry Year in {region.name}"
        weather = WEATHER[worst.weather].label.lower()
        text = f"In the year {worst.year} the harvest of {region.name} failed under {weather}: {name} was never forgotten."
        await record_notable(ctx, world, region, Notable(NotableYearKind.HUNGER, worst, PERCENT - worst.harvest, name, text))
        if worst.harvest < settings.famine_event_below:
            await famine_event(ctx, region, season.loads[("region", env.entity_id)].communities, name, PERCENT - worst.harvest)
        found += 1
    best = max(results, key=lambda item: (item.harvest, -item.offset))
    if best.harvest >= settings.plenty_threshold and (season.best_plenty is None or best.harvest > season.best_plenty[0].harvest):
        season.best_plenty = (best, env)
    return found


async def plenty_year(ctx: TickContext, world: WorldRow, season: HarvestSeason) -> int:
    if season.best_plenty is None:
        return 0
    best, env = season.best_plenty
    region = await ctx.session.get(EntityRow, env.entity_id)
    if region is None:
        return 0
    text = f"The granaries of {region.name} overflowed in the year {best.year}."
    await record_notable(ctx, world, region, Notable(NotableYearKind.PLENTY, best, best.harvest - PERCENT, f"the Year of Plenty in {region.name}", text))
    return 1


async def weather_year(ctx: TickContext, world: WorldRow, season: HarvestSeason) -> int:
    if season.worst_weather is None or season.worst_weather[0] < ctx.rules.harvest.notable_weather_severity:
        return 0
    severity, year, env = season.worst_weather
    region = await ctx.session.get(EntityRow, env.entity_id)
    label = WEATHER[year.weather].label
    name = f"the Year of {label}"
    where = f" over {region.name}" if region is not None else ""
    await record_notable(
        ctx,
        world,
        region,
        Notable(NotableYearKind.WEATHER, year, clamp_int(severity, 0, PERCENT), name, f"{label} fell{where} in the year {year.year}: {name}."),
    )
    if year.weather is WeatherKind.ASH_FALL and env.soil is not SoilKind.VOLCANIC and "soil" not in env.locked:
        env.soil = SoilKind.ASH
        env.soil_base = natural_soil(ctx.rules, SoilKind.ASH, env.moisture)
    return 1


async def harvest(ctx: TickContext) -> None:
    rules = ctx.rules
    book = await EnvironmentBook.load(ctx.session, rules, ctx.epoch)
    capacity = await CapacityModel.load(ctx.session, rules)
    knowledge = await KnowledgeMap.load(ctx.session)
    loads = capacity.build_loads(await canon(ctx.session, LAND_COMMUNITY_TYPES))
    planned = await calendar_regions(ctx, book)
    notable = 0
    for world in book.worlds.values():
        regions = [env for env in book.regions.values() if env.world_id == world.id and ("region", env.entity_id) in loads]
        if not regions:
            continue
        years = sampled_years(ctx.environment, world.id)
        years = years[: grant_sub_steps(ctx.environment, len(years))] or years[:1]
        season = HarvestSeason(book, loads, knowledge, planned, book.growing_season(world.id), years)
        for env in regions:
            notable += await region_harvest(ctx, world, season, env)
        notable += await weather_year(ctx, world, season)
        notable += await plenty_year(ctx, world, season)
    await ctx.session.flush()
    ctx.count("notable_years", notable)


async def calendars(ctx: TickContext) -> None:
    rules = ctx.rules
    settings = rules.calendars
    book = await EnvironmentBook.load(ctx.session, rules, ctx.epoch)
    records = [record for record in await canon(ctx.session, [EntityType.KNOWLEDGE]) if record.knowledge_branch is KnowledgeBranch.ASTRONOMY]
    adopted = commemorated = 0
    rng = ctx.rng("adopt")
    for record in records:
        knowers = [bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.KNOWS], targets=[record.id])]
        calendar = book.calendars.get(record.id)
        if calendar is None:
            if not knowers or knowledge_level(rules, record) < settings.min_astronomy_level or not rng.chance(settings.adoption_chance):
                continue
            calendar = await adopt_calendar(ctx, record, knowers[0])
            book.calendars[record.id] = calendar
            adopted += 1
        regions = {region for knower in knowers if (region := book.atlas.top_region(knower)) is not None}
        commemorated += await commemorate_hard_years(ctx, calendar, regions)
    ctx.count("calendars_adopted", adopted)
    ctx.count("holy_days_added", commemorated)
    await ctx.session.flush()


async def month_names(ctx: TickContext, seasons: list[WorldSeasonRow], speaker_id: int, record_id: int) -> list[str]:
    namer = Namer(ctx.session, ctx.rules)
    names: list[str] = []
    for season in seasons:
        derived = await namer.from_speaker(speaker_id, f"calendar.{record_id}.{season.position}", NameKind.PLACE)
        names.append(derived or f"Month of {season.name}")
    return names


async def adopt_calendar(ctx: TickContext, record: EntityRow, holder_id: int) -> CalendarRow:
    book_seasons = list(await ctx.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == record.world_id).order_by(WorldSeasonRow.position)))
    calendar = CalendarRow(
        knowledge_entity_id=record.id,
        world_id=record.world_id,
        adopted_epoch=ctx.epoch,
        anchor_year=epoch_start_year(ctx.epoch, ctx.rules.time.years_per_epoch),
        anchor_incident_id=None,
        month_names=await month_names(ctx, book_seasons, holder_id, record.id),
        holy_days=[],
    )
    ctx.session.add(calendar)
    holder = await ctx.session.get(EntityRow, holder_id)
    who = holder.name if holder is not None else "its keepers"
    first = calendar.month_names[0] if calendar.month_names else "the first"
    written = await ctx.chronicle(
        ChronicleKind.CULTURE,
        f"{who} began to count the year by {record.name}: {len(calendar.month_names)} months, from {first}.",
        template_key="season.calendar_adopted",
        entity_ids=[record.id, holder_id],
        world_id=record.world_id,
    )
    calendar.anchor_incident_id = written.incident_id
    await ctx.session.flush()
    return calendar


def holy_day_cap(rules: Rules, world: WorldRow | None) -> int:
    settings = rules.calendars
    days = world.year_length_days if world is not None and world.year_length_days is not None else rules.seasons.year_days_base
    return settings.holy_day_cap + days // max(1, settings.days_per_extra_holy_day)


async def commemorate_hard_years(ctx: TickContext, calendar: CalendarRow, regions: set[int]) -> int:
    cap = holy_day_cap(ctx.rules, await ctx.session.get(WorldRow, calendar.world_id))
    if not regions or len(calendar.holy_days) >= cap:
        return 0
    known = {day.get("notable_year_id") for day in calendar.holy_days}
    statement = (
        select(NotableYearRow)
        .where(
            NotableYearRow.world_id == calendar.world_id,
            NotableYearRow.kind == NotableYearKind.HUNGER,
            NotableYearRow.region_entity_id.in_(list(regions)),
            NotableYearRow.epoch >= calendar.adopted_epoch,
        )
        .order_by(NotableYearRow.magnitude.desc(), NotableYearRow.id)
    )
    added = 0
    days = list(calendar.holy_days)
    for notable in await ctx.session.scalars(statement):
        if notable.id in known or len(days) >= cap:
            continue
        days.append({"name": f"Fast of {notable.name}", "notable_year_id": notable.id, "year": notable.year})
        added += 1
    if added:
        calendar.holy_days = days
    return added


async def weave_lines(ctx: TickContext, web: LeyWeb, regions: dict[int, EntityRow], grounds: dict[int, RegionEnvironmentRow]) -> int:
    atlas = await RegionAtlas.load(ctx.session)
    wanted = candidate_lines(ctx.rules, atlas, regions, grounds)
    known = {pair(line.region_a_id, line.region_b_id): line for line in web.lines}
    formed = 0
    for key, strength in wanted.items():
        line = known.get(key)
        if line is None:
            line = LeyLineRow(world_id=regions[key[0]].world_id, region_a_id=key[0], region_b_id=key[1], strength=strength, formed_epoch=ctx.epoch)
            ctx.session.add(line)
            web.lines.append(line)
            formed += 1
            first, second = regions[key[0]], regions[key[1]]
            await ctx.chronicle(
                ChronicleKind.CLIMATE,
                f"A ley line woke between {first.name} and {second.name}: the magic of the two lands began to flow as one.",
                template_key="environment.ley_line_formed",
                entity_ids=[first.id, second.id],
                world_id=first.world_id,
            )
        line.strength = max(strength, line.strength) if line.forged else strength
        held = line.severed_until_epoch is not None and line.severed_until_epoch >= ctx.epoch
        line.severed = held or cut_by_land(ctx.rules, grounds, *key)
        if not held:
            line.severed_until_epoch = None
    for key, line in known.items():
        if key not in wanted and line.severed_until_epoch is None and not line.forged:
            await ctx.session.delete(line)
            web.lines.remove(line)
    return formed


async def crown_nexus(ctx: TickContext, web: LeyWeb, grounds: dict[int, RegionEnvironmentRow]) -> int:
    settings = ctx.rules.environment
    degree = web.degree()
    places = list(await ctx.session.scalars(select(PlaceEnvironmentRow)))
    crowned = 0
    by_region: dict[int, list[PlaceEnvironmentRow]] = {}
    for place in places:
        if place.region_entity_id is not None:
            by_region.setdefault(place.region_entity_id, []).append(place)
    for region_id, ground in grounds.items():
        if "magic_density" not in ground.locked:
            ground.magic_density = clamp_int(ground.magic_density + degree[region_id] * settings.ley_convergence, 0, PERCENT)
        candidates = by_region.get(region_id, [])
        chosen: PlaceEnvironmentRow | None = None
        if degree[region_id] >= settings.nexus_lines and candidates:
            mystery: dict[int, int] = {}
            for place in candidates:
                entity = await ctx.session.get(EntityRow, place.entity_id)
                mystery[place.entity_id] = (stat(entity, "mystery") or 0) if entity is not None else 0
            chosen = max(candidates, key=lambda place: (mystery[place.entity_id], -place.entity_id))
        for place in candidates:
            if "nexus" in place.locked:
                continue
            becomes = place is chosen
            if becomes and not place.nexus:
                crowned += 1
                entity = await ctx.session.get(EntityRow, place.entity_id)
                if entity is not None:
                    await ctx.chronicle(
                        ChronicleKind.CLIMATE,
                        f"{degree[region_id]} ley lines meet at {entity.name}: a nexus of power, coveted by armies and priests.",
                        template_key="environment.nexus_formed",
                        entity_ids=[entity.id, region_id],
                        world_id=entity.world_id,
                    )
            place.nexus = becomes
    return crowned


LEY_WORK_KINDS = frozenset({EngineKind.TEMPLE, EngineKind.OBSERVATORY})
LEY_WORK_SUBTYPES = ("gate", "tower", "temple", "observatory", "shrine")


def ley_work(work: EntityRow) -> bool:
    subtype = (work.subtype or "").lower()
    return work.engine_kind in LEY_WORK_KINDS or any(word in subtype for word in LEY_WORK_SUBTYPES)


async def empower_works(ctx: TickContext, web: LeyWeb) -> int:
    settings = ctx.rules.environment
    atlas = await RegionAtlas.load(ctx.session)
    nexus = {place.entity_id for place in await ctx.session.scalars(select(PlaceEnvironmentRow).where(PlaceEnvironmentRow.nexus.is_(True)))}
    degree = web.degree()
    empowered = 0
    for work in await canon(ctx.session, [EntityType.STRUCTURE]):
        region_id = atlas.top_region(work.id)
        if region_id is None or not degree[region_id] or not ley_work(work):
            continue
        gain = settings.ley_function_gain * (settings.nexus_function_mult if work.location_id in nexus else 1)
        current = stat_or(work, "function", settings.ley_function_base)
        if current >= settings.ley_function_cap:
            continue
        set_stats(work, function=clamp_int(current + gain, 0, settings.ley_function_cap))
        empowered += 1
    return empowered


async def ley_lines(ctx: TickContext) -> None:
    web = await LeyWeb.load(ctx.session)
    regions = {region.id: region for region in await canon(ctx.session, [EntityType.REGION])}
    grounds = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    formed = await weave_lines(ctx, web, regions, grounds)
    await ctx.session.flush()
    crowned = await crown_nexus(ctx, web, grounds)
    empowered = await empower_works(ctx, web)
    await ctx.session.flush()
    ctx.count("ley_lines_formed", formed)
    ctx.count("nexus_formed", crowned)
    ctx.count("works_empowered", empowered)


PHASES = (
    Phase("environment_survey", environment_survey),
    Phase("environment_derive", environment_derive),
    Phase("ley_lines", ley_lines),
    Phase("land_use", land_use),
    Phase("harvest", harvest),
    Phase("calendars", calendars),
)
