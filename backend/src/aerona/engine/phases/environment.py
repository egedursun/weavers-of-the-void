from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from sqlalchemy import delete, func, select

from aerona.cartography.biomes import Biome
from aerona.cartography.model import RegionRecord
from aerona.catalog.evolution import STAGE_COVER, climax_stage
from aerona.catalog.place_terrain import height_of, kind_spec
from aerona.catalog.weather import WEATHER
from aerona.constants.cartography import BIOME_COUNT
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.agrarian import IntensificationRow, LandRingRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow, LeyLineRow, NotableYearRow, PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.happenings import RegionGeomorphRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held as frozen
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityType
from aerona.domain.enums.environment import CoastKind, LandUse, NotableYearKind, RiverClass, ScarKind, SoilKind, WeatherEffect, WeatherKind
from aerona.domain.enums.evolution import KeystoneRole
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.nature import PlantDefence
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.world import ClimateEra, Discovery
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.agrarian.book import Cushion, cushioned, famine_cushions, harvest_lift, intensities, nutrient_shift, nutrient_stocks, ring_shares, rings_of
from aerona.engine.climes.shifts import clime_shifts
from aerona.engine.context import TickContext
from aerona.engine.cosmos.climate import current_heat, world_heat
from aerona.engine.cosmos.cycles import cycles_by_world, soil_swing
from aerona.engine.cosmos.orbits import SKYLESS_WORLDS, rogue_worlds, root_of
from aerona.engine.cosmos.phenomena import phenomenon_passability
from aerona.engine.cosmos.star_types import star_heat
from aerona.engine.cosmos.world_views import world_views
from aerona.engine.cosmos.worldlife import cosmic_disease
from aerona.engine.dominion.book import DominionBook
from aerona.engine.ecology.domestication import grazing_heads
from aerona.engine.ecology.flora import CropBook, crop_year
from aerona.engine.ecology.keystones import pollination, serve_land, services_by_region
from aerona.engine.environment.battles import backfill_battle_ground
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.geomorph import course_of, desert_rainfall, desert_terrain, shapes_by_region
from aerona.engine.environment.ley import LeyWeb, candidate_lines, cut_by_land, pair
from aerona.engine.environment.ley_works import backfill_attunement, empower_works
from aerona.engine.environment.long_seasons import winter_share
from aerona.engine.environment.notable import backfill_notable_years, remember_years
from aerona.engine.environment.place_backfill import ensure_profiles
from aerona.engine.environment.places import place_kind_of
from aerona.engine.environment.profile import (
    Geography,
    Ground,
    Make,
    Surroundings,
    TerrainReading,
    Works,
    band_of,
    climate_factor,
    crop_mix,
    defensibility_of,
    disease_load_of,
    fertility_from,
    make_of,
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
from aerona.engine.environment.works import backfill_typed_works, works_by_region
from aerona.engine.environment.years import SampledYear, world_years
from aerona.engine.industry.pollution import disease_extra, fertility_factor
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.loops.delay import lagged
from aerona.engine.lore.calendar_rites import backfill_holy_days, hallow_holy_days
from aerona.engine.means.water import irrigation_lift
from aerona.engine.nature.cover import cover_of, poisoned_forage, smothered
from aerona.engine.phase import Phase
from aerona.engine.primitives.capacity import LAND_COMMUNITY_TYPES, CapacityModel, RegionKey, RegionLoad
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap, knowledge_level
from aerona.engine.primitives.map_store import stored_regions
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, canon, flags_by_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import base_stat, set_base_stats, stat, stat_or
from aerona.engine.recording.record import FactInput, RoleValue, record
from aerona.engine.structures.readers import regions_of
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

MIN_LAND_SIZE = 0.1
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


def mapped_geography(entry: RegionRecord) -> Geography | None:
    found = entry.geography
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
    world_heat: int = 0
    pass_shift: int = 0
    sky_heat: int | None = None
    dominion_heat: int = 0
    make: Make = field(default_factory=Make)
    clime_rain: int = 0
    clime_heat: int = 0
    sea: int | None = None

    def surroundings(self, rules: Rules, env: RegionEnvironmentRow) -> Surroundings:
        return Surroundings(
            world_type=self.world.world_type,
            era=self.era,
            coastal=env.coast_kind is not CoastKind.NONE,
            highland=is_highland(rules, geography_of(env)),
            ruins=self.ruins,
            chokepoints=self.chokepoints,
            star_heat=star_heat(rules, self.star) if self.sky_heat is None else self.sky_heat,
            works=self.works,
            cleared=env.cleared,
            shift_heat=self.world_heat + self.dominion_heat + env.temperature_shift + current_heat(rules, env.current) + self.clime_heat,
            shift_rain=env.rainfall_shift + self.clime_rain,
            pass_shift=self.pass_shift,
        )


def factor_of(rules: Rules, env: RegionEnvironmentRow, works: Works, sea: int | None = None) -> float:
    mix = crop_mix(rules, farmed=env.farmed, grazed=env.grazed, coastal=env.coast_kind is not CoastKind.NONE, river=env.river_class, sea=sea)
    return climate_factor(rules, temperature=env.temperature, rainfall=env.rainfall, river=env.river_class, scars=env.scars, works=works, mix=mix)


def apply_geography(env: RegionEnvironmentRow, geography: Geography, coast: CoastKind, course: RiverClass | None = None) -> None:
    locked = set(env.locked)
    values = {
        "biome_mix": geography.biome_mix,
        "elevation_mean": geography.elevation_mean,
        "roughness": geography.roughness,
        "latitude": geography.latitude,
        "moisture": geography.moisture,
        "base_forest": geography.base_forest,
        "base_wetland": geography.base_wetland,
        "river_class": course or geography.river_class,
        "coast_kind": coast,
    }
    for key, value in values.items():
        if key not in locked:
            setattr(env, key, value)


def refresh_climate(
    rules: Rules, env: RegionEnvironmentRow, around: Surroundings, axial_tilt: int, tides: int = 0, *, shape: RegionGeomorphRow | None = None
) -> None:
    locked = set(env.locked)
    geography = geography_of(env)
    if "temperature" not in locked:
        env.temperature = temperature_of(rules, geography, around)
    if "rainfall" not in locked:
        env.rainfall = rainfall_of(rules, geography, around)
    desert_rainfall(rules, env, shape)
    if "temperature_band" not in locked:
        env.temperature_band = band_of(rules, env.temperature)
    if "seasonality" not in locked:
        env.seasonality = seasonality_of(rules, env.latitude, axial_tilt)
    if "wetland" not in locked:
        env.wetland = clamp_int(env.base_wetland * (PERCENT + (env.rainfall - rules.environment.ideal_rainfall)) / PERCENT, 0, PERCENT)
    if "forest_cover" not in locked:
        env.forest_cover = min(STAGE_COVER[env.succession], clamp_int(env.base_forest * (PERCENT - env.cleared) / PERCENT, 0, PERCENT))
    if "dominant_terrain" not in locked:
        reading = TerrainReading(geography, around, env.temperature, env.rainfall, env.wetland, env.built)
        env.dominant_terrain = terrain_of(rules, reading)
    desert_terrain(env, shape)
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
    fresh = {mode: clamp_int(value + around.pass_shift, 0, PERCENT) for mode, value in passability_of(rules, ground).items()}
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
    env.succession = climax_stage(geography.base_forest, geography.base_wetland, base)
    around = context.surroundings(rules, env)
    refresh_climate(rules, env, around, context.world.axial_tilt or 0, context.world.tidal_strength or 0)
    env.mineral_layers = mineral_layers(
        rules, ctx.environment.rng(f"minerals.{region.id}"), geography, context.world.world_type, env.dominant_terrain, make=context.make
    )
    fertility = stat(region, "fertility")
    if fertility is not None:
        env.soil_fertility = soil_for(fertility, factor_of(rules, env, context.works, context.sea))
        env.soil_base = env.soil_fertility
        env.derived_fertility = fertility
    return env


def new_place_environment(rules: Rules, place: EntityRow, region_id: int | None, factor: float, kind: PlaceKind) -> PlaceEnvironmentRow:
    profile = kind_spec(kind)
    fertility = stat(place, "fertility")
    soil = soil_for(fertility, factor) if fertility is not None else rules.environment.ideal_rainfall
    return PlaceEnvironmentRow(
        entity_id=place.id,
        region_entity_id=region_id,
        terrain=profile.terrain,
        cover=profile.cover,
        water_source=profile.water,
        height_advantage=clamp_int(height_of(rules, profile.height), 0, PERCENT),
        chokepoint=profile.chokepoint,
        soil_fertility=soil,
        derived_fertility=fertility,
        locked=[],
    )


async def moons_by_world(ctx: TickContext) -> Counter[int]:
    statement = select(WorldRow.parent_world_id, func.count()).where(WorldRow.parent_world_id.is_not(None)).group_by(WorldRow.parent_world_id)
    rows = await ctx.session.execute(statement)
    return Counter({parent: count for parent, count in rows if parent is not None})


async def ensure_world_calendar(ctx: TickContext, world: WorldRow, moons: int, orbit: float) -> bool:
    rules = ctx.rules
    created = False
    if world.axial_tilt is None or world.season_count is None or world.year_length_days is None or world.day_length_hours is None:
        calendar = world_calendar(rules, ctx.environment.rng(f"calendar.{world.id}"), world.world_type, orbit)
        world.axial_tilt = calendar.axial_tilt if world.axial_tilt is None else world.axial_tilt
        world.year_length_days = calendar.year_length_days if world.year_length_days is None else world.year_length_days
        world.day_length_hours = calendar.day_length_hours if world.day_length_hours is None else world.day_length_hours
        world.season_count = calendar.season_count if world.season_count is None else world.season_count
        created = True
    if "moon_count" not in world.calendar_locked:
        world.moon_count = moons
    if world.tidal_strength is None and "tidal_strength" not in world.calendar_locked:
        world.tidal_strength = tidal_strength(rules, world.moon_count or 0)
    existing = await ctx.session.scalar(select(func.count()).select_from(WorldSeasonRow).where(WorldSeasonRow.world_id == world.id))
    if not existing:
        await write_seasons(ctx, world)
        created = True
    return created


async def write_seasons(ctx: TickContext, world: WorldRow) -> list[WorldSeasonRow]:
    count = world.season_count or 1
    held = {
        row.position: row
        for row in await ctx.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world.id, WorldSeasonRow.edited.is_(True)))
        if row.position < count
    }
    await ctx.session.execute(delete(WorldSeasonRow).where(WorldSeasonRow.world_id == world.id, WorldSeasonRow.id.not_in([row.id for row in held.values()])))
    rows = [
        held.get(draft.position)
        or WorldSeasonRow(
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
        for draft in season_drafts(ctx.rules, world.world_type, count, world.axial_tilt or 0)
    ]
    ctx.session.add_all([row for row in rows if row.id is None])
    await ctx.session.flush()
    return rows


def root_world(book: EnvironmentBook, world: WorldRow) -> WorldRow:
    seen: set[int] = set()
    while world.parent_world_id is not None and world.parent_world_id in book.worlds and world.id not in seen:
        seen.add(world.id)
        world = book.worlds[world.parent_world_id]
    return world


def governs(world: WorldRow, star: StarRow | None, rogue: set[int]) -> bool:
    return world.world_type not in SKYLESS_WORLDS and (star is not None or world.id in rogue)


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
    hindered = await phenomenon_passability(ctx)
    contexts: dict[int, RegionContext] = {}
    skies = {row.world_id: row for row in await ctx.session.scalars(select(WorldPhysicsRow))}
    rogue = await rogue_worlds(ctx.session)
    dominion = await DominionBook.load(ctx.session)
    shifts = await clime_shifts(ctx.session, ctx.rules, ctx.epoch)
    views = await world_views(ctx.session, ctx.rules)
    for region in regions:
        world = book.worlds.get(region.world_id)
        if world is None:
            continue
        physics = skies.get(world.id)
        sky_heat = physics.heat_shift if physics is not None and governs(world, book.star_of(root_world(book, world)), rogue) else None
        contexts[region.id] = RegionContext(
            world=world,
            era=world.climate_era,
            ruins=ruins[region.id],
            chokepoints=chokepoints[region.id],
            star=book.star_of(world),
            works=works.get(region.id, Works()),
            world_heat=world_heat(ctx.rules, world, book.star_of(world), sky_heat),
            pass_shift=hindered[region.id],
            sky_heat=sky_heat,
            make=make_of(ctx.rules, physics),
            dominion_heat=dominion.scale_at(ctx.rules, region.id, DivineScale.HEAT) * ctx.rules.dominion.heat_per_step,
            clime_rain=shifts.get(region.id, (0, 0))[0],
            clime_heat=shifts.get(region.id, (0, 0))[1],
            sea=views[world.id].sea_pct if world.id in views else None,
        )
    return contexts


async def survey_places(ctx: TickContext, book: EnvironmentBook, contexts: dict[int, RegionContext]) -> int:
    kinds = await ensure_profiles(ctx, book)
    placed = 0
    for place in unheld(await canon(ctx.session, [EntityType.PLACE])):
        if place.id in book.places:
            continue
        region_id = book.atlas.top_region(place.id)
        env = book.regions.get(region_id) if region_id is not None else None
        context = contexts.get(region_id) if region_id is not None else None
        factor = (
            factor_of(ctx.rules, env, context.works if context is not None else Works(), context.sea if context is not None else None)
            if env is not None
            else 1.0
        )
        kind = kinds.get(place.id) or await place_kind_of(ctx.session, place.id)
        row = new_place_environment(ctx.rules, place, region_id, factor, kind)
        ctx.session.add(row)
        book.places[place.id] = row
        placed += 1
    await ctx.session.flush()
    return placed


async def run_backfills(ctx: TickContext) -> None:
    ctx.count("typed_works_backfilled", await backfill_typed_works(ctx))
    ctx.count("battles_grounded", await backfill_battle_ground(ctx))


@reads(
    "event.severity",
    "people.population",
    "place.fertility",
    "region.breadth",
    "region.fertility",
    "region.magic",
    "settlement.population",
    "table.applied_fixups",
    "table.battles",
    "table.beast_profiles",
    "table.bonds",
    "table.calendars",
    "table.climate_oscillations",
    "table.cosmic_features",
    "table.cosmos",
    "table.custom_kinds",
    "table.dimensional_events",
    "table.dimensions",
    "table.districts",
    "table.dominions",
    "table.entities",
    "table.entity_flags",
    "table.era_deeds",
    "table.forced_weather",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.god_designs",
    "table.god_scales",
    "table.holder_custom_techniques",
    "table.holder_levels",
    "table.holder_techniques",
    "table.monsoon_seasons",
    "table.nodes",
    "table.notable_years",
    "table.phenomenon_footprints",
    "table.phenomenon_profiles",
    "table.place_environment",
    "table.place_profiles",
    "table.plant_profiles",
    "table.polity_profiles",
    "table.region_dominion",
    "table.region_environment",
    "table.region_geomorphology",
    "table.region_winds",
    "table.settlement_infrastructure",
    "table.sky_events",
    "table.species_ranges",
    "table.stars",
    "table.structure_profiles",
    "table.world_maps",
    "table.world_physics",
    "table.world_seasons",
    "table.world_type_profiles",
    "table.worlds",
)
@writes(
    "table.applied_fixups",
    "table.battles",
    "table.districts",
    "table.notable_years",
    "table.place_environment",
    "table.place_profiles",
    "table.region_environment",
    "table.settlement_infrastructure",
    "table.world_seasons",
    "table.worlds",
)
async def environment_survey(ctx: TickContext) -> None:
    ctx.count("notable_years_backfilled", await backfill_notable_years(ctx))
    ctx.count("notable_years_remembered", await remember_years(ctx))
    moons = await moons_by_world(ctx)
    worlds = list(await ctx.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)))
    calendars = 0
    by_id = {world.id: world for world in worlds}
    for world in unheld(worlds):
        calendars += int(await ensure_world_calendar(ctx, world, moons[world.id], root_of(by_id, world).orbit))
    records = {stored.id: stored for world_records in (await stored_regions(ctx.session)).values() for stored in world_records}
    book = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
    regions = unheld(await canon(ctx.session, [EntityType.REGION]))
    contexts = await region_contexts(ctx, book, regions)
    shapes = await shapes_by_region(ctx.session)
    created = synced = 0
    fresh: list[RegionEnvironmentRow] = []
    for region in regions:
        context = contexts.get(region.id)
        if context is None:
            continue
        stored = records.get(region.id)
        mapped = mapped_geography(stored) if stored is not None else None
        coast = stored.geography.coast_kind if stored is not None and stored.geography is not None else CoastKind.NONE
        env = book.regions.get(region.id)
        if env is None:
            env = new_region_environment(ctx, region, mapped or fallback_geography(ctx.rules, region), coast, context)
            env.surveyed = mapped is not None
            ctx.session.add(env)
            book.regions[region.id] = env
            fresh.append(env)
            created += 1
        elif mapped is not None:
            apply_geography(env, mapped, coast, course_of(shapes, region.id))
            if not env.surveyed:
                env.mineral_layers = mineral_layers(
                    ctx.rules, ctx.environment.rng(f"minerals.{region.id}"), mapped, context.world.world_type, env.dominant_terrain, make=context.make
                )
            env.surveyed = True
            synced += 1
    await ctx.session.flush()
    await settle_new_ground(ctx, fresh)
    placed = await survey_places(ctx, book, contexts)
    ctx.count("worlds_given_seasons", calendars)
    ctx.count("regions_surveyed", created)
    ctx.count("regions_resynced", synced)
    ctx.count("places_surveyed", placed)
    await run_backfills(ctx)


SCAR_DECAY: Mapping[ScarKind, Callable[[Rules], int]] = total(
    ScarKind,
    {
        ScarKind.BATTLEFIELD: lambda rules: rules.scars.battlefield_decay,
        ScarKind.PLAGUE_GROUND: lambda rules: rules.scars.plague_ground_decay,
        ScarKind.MADE_BARREN: lambda rules: rules.scars.salted_earth_decay,
        ScarKind.BURNED: lambda rules: rules.scars.burned_decay,
        ScarKind.CRATER: lambda rules: rules.scars.crater_decay,
        ScarKind.HAUNTED: lambda rules: rules.scars.haunted_decay,
        ScarKind.BLIGHTED: lambda rules: rules.scars.blighted_decay,
        ScarKind.LEAK_WOUND: lambda rules: rules.scars.leak_wound_decay,
        ScarKind.PLUNDERED: lambda rules: rules.campaign_depth.plunder_heal,
        ScarKind.EARTHWORKS: lambda rules: rules.army_depth.earthworks_decay,
        ScarKind.MILITARY_ROAD: lambda rules: rules.army_depth.road_decay,
        ScarKind.BRIDGE_DOWN: lambda rules: rules.army_depth.bridge_down_decay,
    },
)


def decay_scars(rules: Rules, env: RegionEnvironmentRow) -> None:
    decay = {kind: worn(rules) for kind, worn in SCAR_DECAY.items()}
    kept = {
        key: depth if f"scar.{key}" in env.locked else depth - decay[ScarKind(key)]
        for key, depth in env.scars.items()
        if f"scar.{key}" in env.locked or depth - decay[ScarKind(key)] > 0
    }
    if kept != env.scars:
        env.scars = kept


def fold_external(env_fertility: int | None, current: int | None, soil: int) -> int:
    if env_fertility is None or current is None or current == env_fertility:
        return soil
    return clamp_int(soil + current - env_fertility, 0, PERCENT)


def recover_soil(rules: Rules, env: RegionEnvironmentRow, nutrients: int = 0) -> None:
    if "soil_fertility" in env.locked:
        return
    settings = rules.climate_effects
    gap = clamp_int(env.soil_base + nutrients, 0, PERCENT) - env.soil_fertility
    divisor = settings.fertility_recovery_divisor if gap > 0 else settings.fertility_decline_divisor
    env.soil_fertility = clamp_int(env.soil_fertility + gap / divisor, 0, PERCENT)


async def sanitation_by_region(ctx: TickContext, book: EnvironmentBook, communities: list[EntityRow]) -> dict[int, int]:
    knowledge = await KnowledgeMap.load(ctx.session)
    planned = {row.settlement_entity_id: row.sanitation for row in await ctx.session.scalars(select(SettlementProfileRow))}
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
        share = planned.get(community.id, share)
        weighted[region_id] += population * min(ctx.rules.environment.sanitation_cap_pct, share)
    return {region_id: round_half_up(weighted[region_id] / totals[region_id]) for region_id in totals if totals[region_id]}


async def worked_soil(ctx: TickContext, env: RegionEnvironmentRow, swing: int, shift: int) -> int:
    recover_soil(ctx.rules, env, swing + await lagged(ctx, BalanceLoop.SALINISATION, env.entity_id, shift))
    return await lagged(ctx, BalanceLoop.SOIL_EXHAUSTION, env.entity_id, env.soil_fertility)


@reads(
    "people.population",
    "place.fertility",
    "region.breadth",
    "region.fertility",
    "region.magic",
    "settlement.population",
    "table.bonds",
    "table.calendars",
    "table.climate_oscillations",
    "table.cosmic_features",
    "table.cosmos",
    "table.dimensional_events",
    "table.dimensions",
    "table.districts",
    "table.dominions",
    "table.ecosystem_services",
    "table.entities",
    "table.entity_flags",
    "table.forced_weather",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.god_designs",
    "table.god_scales",
    "table.holder_levels",
    "table.monsoon_seasons",
    "table.nodes",
    "table.phenomenon_footprints",
    "table.phenomenon_profiles",
    "table.place_environment",
    "table.plant_profiles",
    "table.polity_profiles",
    "table.region_dominion",
    "table.region_environment",
    "table.region_geomorphology",
    "table.region_pollution",
    "table.region_winds",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.sky_events",
    "table.soil_nutrients",
    "table.species_ranges",
    "table.stars",
    "table.structure_profiles",
    "table.world_cycles",
    "table.world_maps",
    "table.world_physics",
    "table.world_seasons",
    "table.world_type_profiles",
    "table.worlds",
)
@writes("place.fertility", "region.fertility", "table.entities", "table.place_environment", "table.region_environment")
async def environment_derive(ctx: TickContext) -> None:
    rules = ctx.rules
    book = await EnvironmentBook.load(ctx.session, rules, ctx.epoch)
    regions = await canon(ctx.session, [EntityType.REGION])
    contexts = await region_contexts(ctx, book, regions)
    capacity = await CapacityModel.load(ctx.session, rules)
    communities = await canon(ctx.session, LAND_COMMUNITY_TYPES)
    loads = capacity.build_loads(communities)
    sanitation = await sanitation_by_region(ctx, book, communities)
    shapes = await shapes_by_region(ctx.session)
    fouled = {row.region_node_id: row for row in await ctx.session.scalars(select(RegionPollutionRow))}
    services = await services_by_region(ctx.session)
    cycles, stocks = await cycles_by_world(ctx.session), await nutrient_stocks(ctx.session)
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
        refresh_climate(rules, env, around, context.world.axial_tilt or 0, context.world.tidal_strength or 0, shape=shapes.get(region.id))
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
            env.disease_load = clamp_int(env.disease_load + disease_extra(rules, fouled.get(region.id)) + cosmic_disease(rules, context.world), 0, PERCENT)
        serve_land(rules, env, services.get(region.id))
        current = base_stat(region, "fertility")
        if "soil_fertility" not in env.locked:
            env.soil_fertility = fold_external(env.derived_fertility, current, env.soil_fertility)
        soil = await worked_soil(ctx, env, soil_swing(rules, cycles.get(env.world_id)), nutrient_shift(rules, stocks.get(env.entity_id), env.soil_base))
        if current is not None or not region.is_water:
            set_base_stats(
                region,
                fertility=fertility_from(soil, factor_of(rules, env, context.works, context.sea) * fertility_factor(rules, fouled.get(region.id))),
            )
            env.derived_fertility = base_stat(region, "fertility")
            derived += 1
    for place_env in book.places.values():
        place = await ctx.session.get(EntityRow, place_env.entity_id)
        env = book.region_of(place_env.region_entity_id)
        context = contexts.get(place_env.region_entity_id) if place_env.region_entity_id is not None else None
        if place is None or env is None or context is None or stat(place, "fertility") is None:
            continue
        place_env.soil_fertility = fold_external(place_env.derived_fertility, base_stat(place, "fertility"), place_env.soil_fertility)
        soiled = fertility_factor(rules, fouled.get(place_env.region_entity_id or -1))
        set_base_stats(place, fertility=fertility_from(place_env.soil_fertility, factor_of(rules, env, context.works, context.sea) * soiled))
        place_env.derived_fertility = base_stat(place, "fertility")
    await ctx.session.flush()
    ctx.count("regions_derived", derived)


def land_target(value: float) -> int:
    return clamp_int(value, 0, PERCENT)


def drift(current: int, target: int, divisor: int) -> int:
    return clamp_int(current + (target - current) / max(1, divisor), 0, PERCENT)


def work_land(
    rules: Rules,
    env: RegionEnvironmentRow,
    capacity: CapacityModel,
    load: RegionLoad,
    divisor: int,
    *,
    herds: int = 0,
    ring: LandRingRow | None = None,
    size: float = 1.0,
) -> None:
    settings = rules.land_use
    farm_pct, graze_pct = ring_shares(rules, ring.ring) if ring is not None else (PERCENT, PERCENT)
    community = load.communities[0]
    ceiling = max(1.0, capacity.capacity(load, community, capacity.effective_fertility(community)))
    occupancy = load.population / ceiling * PERCENT
    farming = load.agriculture / load.population
    settled = sum(stat_or(item, "population", 0) for item in load.communities if item.entity_type is EntityType.SETTLEMENT)
    locked = set(env.locked)
    if "farmed" not in locked:
        env.farmed = drift(env.farmed, land_target(occupancy * farming * settings.farm_target_pct / PERCENT * farm_pct / PERCENT), divisor)
    if "grazed" not in locked:
        pasture = occupancy * (1 - farming) * settings.graze_target_pct / PERCENT + herds / rules.husbandry.graze_head_per_pct
        env.grazed = drift(env.grazed, land_target(pasture * graze_pct / PERCENT), divisor)
    if "built" not in locked:
        env.built = drift(env.built, land_target(settled / (settings.built_population_per_pct * max(MIN_LAND_SIZE, size))), divisor)
    cleared = env.farmed + env.built * settings.cleared_built_pct / PERCENT + env.grazed * settings.cleared_grazed_pct / PERCENT
    if "cleared" not in locked:
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
            env.forest_cover = min(STAGE_COVER[env.succession], clamp_int(env.base_forest * (PERCENT - env.cleared) / PERCENT, 0, PERCENT))


@dataclass(frozen=True)
class LandMark:
    erosion: int
    farmed: int
    soil: int
    cleared: int


def land_turns(rules: Rules, env: RegionEnvironmentRow, before: LandMark) -> list[tuple[str, dict[str, FactInput]]]:
    settings = rules.land_use
    turns: list[tuple[str, dict[str, FactInput]]] = []
    if before.erosion < settings.erosion_noted <= env.erosion:
        turns.append(("land.erosion", {"erosion": env.erosion}))
    if before.farmed <= settings.overfarm_threshold < env.farmed:
        turns.append(("land.overfarmed", {"farmed": env.farmed}))
    if before.soil >= settings.exhausted_soil_below > env.soil_fertility:
        turns.append(("land.soil_exhausted", {"fertility": env.soil_fertility}))
    if before.cleared > 0 == env.cleared:
        turns.append(("land.rewilded", {"forest": env.forest_cover}))
    return turns


async def note_land(ctx: TickContext, env: RegionEnvironmentRow, before: LandMark) -> None:
    turns = land_turns(ctx.rules, env, before)
    if not turns:
        return
    for key, facts in turns:
        await record(ctx, key, roles={IncidentRole.SUBJECT: env.entity_id}, facts=facts, place=env.entity_id, world_id=env.world_id)


@reads(
    "people.population",
    "place.fertility",
    "region.breadth",
    "region.fertility",
    "settlement.population",
    "table.bonds",
    "table.calendars",
    "table.cosmos",
    "table.creator",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.forced_weather",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.herds",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.land_rings",
    "table.node_births",
    "table.nodes",
    "table.place_environment",
    "table.polity_profiles",
    "table.region_environment",
    "table.sky_events",
    "table.sons",
    "table.stars",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes("table.chronicle", "table.chronicle_entities", "table.incident_facts", "table.incident_participants", "table.incidents", "table.region_environment")
def land_sizes(atlas: RegionAtlas, region_ids: list[int]) -> dict[int, float]:
    measured = {region_id: record.size for region_id in region_ids if (record := atlas.record(region_id)) is not None and record.size > 0}
    mean = sum(measured.values()) / len(measured) if measured else 1.0
    return {region_id: size / mean for region_id, size in measured.items()}


async def land_use(ctx: TickContext) -> None:
    rules = ctx.rules
    settings = rules.land_use
    book = await EnvironmentBook.load(ctx.session, rules, ctx.epoch)
    capacity = await CapacityModel.load(ctx.session, rules)
    loads = capacity.build_loads(await canon(ctx.session, LAND_COMMUNITY_TYPES))
    grazing = await grazing_heads(ctx.session)
    rings = await rings_of(ctx.session)
    worked = rewilded = 0
    sizes = land_sizes(book.atlas, list(book.regions))
    for region_id, env in book.regions.items():
        before = LandMark(env.erosion, env.farmed, env.soil_fertility, env.cleared)
        load = loads.get(("region", region_id))
        if load is None or load.population <= 0:
            for key in LandUse:
                if key.value not in env.locked:
                    setattr(env, key.value, max(0, getattr(env, key.value) - settings.rewild_rate))
            rewilded += 1
        else:
            work_land(
                rules, env, capacity, load, settings.drift_divisor, herds=grazing.get(region_id, 0), ring=rings.get(region_id), size=sizes.get(region_id, 1.0)
            )
            worked += 1
        if "erosion" not in env.locked:
            env.erosion = (
                clamp_int(env.cleared * env.roughness / PERCENT * settings.erosion_pct / PERCENT, 0, PERCENT)
                if env.roughness >= settings.erosion_roughness
                else 0
            )
        loss = env.erosion * settings.erosion_soil_pct / PERCENT
        if env.farmed > settings.overfarm_threshold:
            loss += (env.farmed - settings.overfarm_threshold) * settings.overfarm_soil_pct / PERCENT
        if "soil_fertility" not in env.locked:
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
    regions: set[int] = set(await regions_of(ctx.session, [StructureKind.OBSERVATORY], book.atlas))
    if not book.calendars:
        return regions
    for bond in await active_bonds(ctx.session, [BondKind.KNOWS], targets=list(book.calendars)):
        region_id = book.atlas.top_region(bond.source_node_id)
        if region_id is not None:
            regions.add(region_id)
    return regions


def year_harvest(
    rules: Rules, *, growth: int, weather_growth: int, farming: float, agriculture: float, planned: bool, blight: int, soil: int, crops: float = 1.0
) -> int:
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
        * max(0.0, crops)
    )
    return clamp_int(value, 0, settings.harvest_max_pct)


@dataclass(frozen=True)
class Notable:
    kind: NotableYearKind
    year: YearHarvest
    magnitude: int
    name: str


async def record_notable(ctx: TickContext, key: str, world: WorldRow, region: EntityRow | None, notable: Notable) -> NotableYearRow:
    roles: dict[IncidentRole, RoleValue] = (
        {IncidentRole.SUBJECT: region.id if region is not None else world.id, IncidentRole.PLACE: region.id if region is not None else None}
        if notable.kind is NotableYearKind.WEATHER
        else {IncidentRole.PLACE: region.id if region is not None else None}
    )
    written = await record(
        ctx,
        key,
        roles=roles,
        facts={
            "name": notable.name,
            "year": notable.year.year,
            "harvest": notable.year.harvest,
            "weather": notable.year.weather,
            "magnitude": notable.magnitude,
        },
        place=region.id if region is not None else None,
        world_id=world.id,
        magnitude=notable.magnitude,
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
            body=f"A year of empty stores in {region.name}.",
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
    crops: CropBook
    productivity: dict[int, int] = field(default_factory=dict)
    services: dict[int, dict[KeystoneRole, int]] = field(default_factory=dict)
    lifts: dict[int, IntensificationRow] = field(default_factory=dict)
    cushions: dict[int, Cushion] = field(default_factory=dict)
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
        crops = season.crops.factor(env.entity_id, crop_year(rules, weather))
        value = year_harvest(
            rules,
            growth=growth,
            weather_growth=weather.effect(WeatherEffect.GROWTH),
            farming=farming,
            agriculture=agriculture,
            planned=env.entity_id in season.planned,
            blight=env.scars.get(ScarKind.BLIGHTED.value, 0),
            soil=env.soil_fertility,
            crops=crops,
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
        laws, table = await ctx.laws(), ctx.rules.natural_laws
        dark = table.night_harvest_pct if laws.has_at(NaturalLaw.ETERNAL_NIGHT, world.id, env.entity_id) else PERCENT
        upturned = table.reversed_harvest_pct if laws.has_at(NaturalLaw.SEASONS_REVERSED, world.id, env.entity_id) else PERCENT
        wintered = await winter_share(ctx, world.id)
        worked = PERCENT + season.productivity.get(env.entity_id, 0) * ctx.rules.dominion.harvest_per_step_pct
        pollinated = pollination(ctx.rules, season.services.get(env.entity_id))
        env.harvest_pct = round_half_up(
            sum(item.harvest for item in results)
            / len(results)
            * dark
            / PERCENT
            * upturned
            / PERCENT
            * wintered
            / PERCENT
            * worked
            / PERCENT
            * pollinated
            * harvest_lift(ctx.rules, season.lifts.get(env.entity_id))
            * await irrigation_lift(ctx, env)
            * smothered(ctx.rules, await cover_of(ctx.session, env.entity_id, PlantDefence.ALLELOPATHY))
        )
        grown = env.harvest_pct
        env.harvest_pct, foraged = cushioned(ctx.rules, env.harvest_pct, season.cushions.get(env.entity_id))
        if foraged:
            spoiled = poisoned_forage(ctx.rules, await cover_of(ctx.session, env.entity_id, PlantDefence.TOXINS))
            env.harvest_pct = round_half_up(env.harvest_pct - (env.harvest_pct - grown) * spoiled)
        if foraged and "disease_load" not in env.locked:
            env.disease_load = clamp_int(env.disease_load + ctx.rules.famine_foods.health_cost, 0, PERCENT)
    region = await ctx.session.get(EntityRow, env.entity_id)
    if region is None:
        return 0
    found = 0
    worst = min(results, key=lambda item: (item.harvest, item.offset))
    if worst.harvest < settings.notable_threshold:
        name = f"the Hungry Year in {region.name}"
        await record_notable(ctx, "year.hunger", world, region, Notable(NotableYearKind.HUNGER, worst, PERCENT - worst.harvest, name))
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
    plenty = Notable(NotableYearKind.PLENTY, best, best.harvest - PERCENT, f"the Year of Plenty in {region.name}")
    await record_notable(ctx, "year.plenty", world, region, plenty)
    return 1


async def weather_year(ctx: TickContext, world: WorldRow, season: HarvestSeason) -> int:
    if season.worst_weather is None or season.worst_weather[0] < ctx.rules.harvest.notable_weather_severity:
        return 0
    severity, year, env = season.worst_weather
    region = await ctx.session.get(EntityRow, env.entity_id)
    label = WEATHER[year.weather].label
    name = f"the Year of {label}"
    await record_notable(ctx, "year.weather", world, region, Notable(NotableYearKind.WEATHER, year, clamp_int(severity, 0, PERCENT), name))
    if year.weather is WeatherKind.ASH_FALL and env.soil is not SoilKind.VOLCANIC and "soil" not in env.locked:
        env.soil = SoilKind.TEPHRA
        if "soil_base" not in env.locked:
            env.soil_base = natural_soil(ctx.rules, SoilKind.TEPHRA, env.moisture)
    return 1


@reads(
    "people.population",
    "settlement.population",
    "table.applied_fixups",
    "table.bonds",
    "table.calendars",
    "table.cosmos",
    "table.creator",
    "table.dimensional_events",
    "table.dimensions",
    "table.dominions",
    "table.ecosystem_services",
    "table.entities",
    "table.famine_lore",
    "table.forced_weather",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.god_designs",
    "table.god_scales",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.intensification",
    "table.irregular_seasons",
    "table.natural_law_profiles",
    "table.node_births",
    "table.nodes",
    "table.place_environment",
    "table.plant_profiles",
    "table.polity_profiles",
    "table.preparedness",
    "table.region_crops",
    "table.region_dominion",
    "table.region_environment",
    "table.sky_events",
    "table.sons",
    "table.species_products",
    "table.species_profiles",
    "table.stars",
    "table.structure_profiles",
    "table.water_lifts",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_seasons",
    "table.world_type_profiles",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.notable_years",
    "table.region_environment",
)
async def harvest(ctx: TickContext) -> None:
    rules = ctx.rules
    book = await EnvironmentBook.load(ctx.session, rules, ctx.epoch)
    capacity = await CapacityModel.load(ctx.session, rules)
    knowledge = await KnowledgeMap.load(ctx.session)
    loads = capacity.build_loads(await canon(ctx.session, LAND_COMMUNITY_TYPES))
    planned = await calendar_regions(ctx, book)
    crops = await CropBook.load(ctx.session, rules, book.regions)
    dominion = await DominionBook.load(ctx.session)
    services = await services_by_region(ctx.session)
    lifts = await intensities(ctx.session)
    cushions = await famine_cushions(ctx.session, book.atlas)
    notable = 0
    for world in book.worlds.values():
        if frozen(world.id):
            continue
        regions = [env for env in book.regions.values() if env.world_id == world.id and ("region", env.entity_id) in loads and not frozen(env.entity_id)]
        if not regions:
            continue
        years = world_years(ctx.environment, world.id, "harvest")
        productivity = {env.entity_id: dominion.scale_at(rules, env.entity_id, DivineScale.PRODUCTIVITY) for env in regions}
        season = HarvestSeason(book, loads, knowledge, planned, book.growing_season(world.id), years, crops, productivity, services, lifts, cushions)
        for env in regions:
            notable += await region_harvest(ctx, world, season, env)
        notable += await weather_year(ctx, world, season)
        notable += await plenty_year(ctx, world, season)
    await ctx.session.flush()
    ctx.count("notable_years", notable)


@reads(
    "table.applied_fixups",
    "table.bonds",
    "table.calendars",
    "table.entities",
    "table.forced_weather",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.nodes",
    "table.notable_years",
    "table.place_environment",
    "table.region_environment",
    "table.sky_events",
    "table.stars",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "table.applied_fixups",
    "table.bonds",
    "table.calendars",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.name_registry",
    "table.nodes",
    "table.tradition_profiles",
)
async def calendars(ctx: TickContext) -> None:
    rules = ctx.rules
    settings = rules.calendars
    book = await EnvironmentBook.load(ctx.session, rules, ctx.epoch)
    lores = [lore for lore in await canon(ctx.session, [EntityType.KNOWLEDGE]) if lore.knowledge_branch is KnowledgeBranch.ASTRONOMY]
    adopted = commemorated = 0
    hallowed = await backfill_holy_days(ctx)
    rng = ctx.rng("adopt")
    for lore in lores:
        knowers = [bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.KNOWS], targets=[lore.id])]
        calendar = book.calendars.get(lore.id)
        if calendar is None:
            if not knowers or knowledge_level(rules, lore) < settings.min_astronomy_level or not rng.chance(settings.adoption_chance):
                continue
            calendar = await adopt_calendar(ctx, lore, knowers[0])
            book.calendars[lore.id] = calendar
            adopted += 1
        regions = {region for knower in knowers if (region := book.atlas.top_region(knower)) is not None}
        commemorated += await commemorate_hard_years(ctx, calendar, regions)
        hallowed += await hallow_holy_days(ctx, calendar)
    ctx.count("calendars_adopted", adopted)
    ctx.count("holy_days_added", commemorated)
    ctx.count("holy_day_traditions", hallowed)
    await ctx.session.flush()


async def month_names(ctx: TickContext, seasons: list[WorldSeasonRow], speaker_id: int, record_id: int) -> list[str]:
    namer = Namer(ctx.session, ctx.rules)
    names: list[str] = []
    for season in seasons:
        derived = await namer.from_speaker(speaker_id, f"calendar.{record_id}.{season.position}", NameKind.PLACE)
        names.append(derived or f"Month of {season.name}")
    return names


async def adopt_calendar(ctx: TickContext, lore: EntityRow, holder_id: int) -> CalendarRow:
    book_seasons = list(await ctx.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == lore.world_id).order_by(WorldSeasonRow.position)))
    calendar = CalendarRow(
        knowledge_entity_id=lore.id,
        world_id=lore.world_id,
        adopted_epoch=ctx.epoch,
        anchor_year=epoch_start_year(ctx.epoch, ctx.rules.time.years_per_epoch),
        anchor_incident_id=None,
        month_names=await month_names(ctx, book_seasons, holder_id, lore.id),
        holy_days=[],
    )
    ctx.session.add(calendar)
    first = calendar.month_names[0] if calendar.month_names else "the first"
    written = await record(
        ctx,
        "season.calendar_adopted",
        roles={IncidentRole.ACTOR: holder_id, IncidentRole.SUBJECT: lore.id},
        facts={"months": len(calendar.month_names), "first": first, "anchor_year": calendar.anchor_year},
        world_id=lore.world_id,
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
            await record(
                ctx,
                "environment.ley_line_formed",
                roles={IncidentRole.ORIGIN: key[0], IncidentRole.DESTINATION: key[1]},
                facts={"strength": strength},
                world_id=regions[key[0]].world_id,
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
        mystery: dict[int, int] = {}
        if degree[region_id] >= settings.nexus_lines and candidates:
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
                await record(
                    ctx,
                    "environment.nexus_formed",
                    roles={IncidentRole.SUBJECT: place.entity_id, IncidentRole.PLACE: region_id},
                    facts={"lines": degree[region_id], "mystery": mystery.get(place.entity_id, 0) if chosen is not None else 0},
                    place=region_id,
                )
            place.nexus = becomes
    return crowned


@reads(
    "place.mystery",
    "region.magic",
    "structure.function",
    "table.applied_fixups",
    "table.entities",
    "table.ley_lines",
    "table.nodes",
    "table.place_environment",
    "table.region_environment",
    "table.structure_designs",
    "table.structure_ley",
    "table.structure_profiles",
    "table.world_maps",
)
@writes(
    "structure.function",
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.ley_lines",
    "table.place_environment",
    "table.region_environment",
    "table.structure_ley",
    "table.structure_profiles",
)
async def ley_lines(ctx: TickContext) -> None:
    web = await LeyWeb.load(ctx.session)
    regions = {region.id: region for region in await canon(ctx.session, [EntityType.REGION])}
    grounds = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    formed = await weave_lines(ctx, web, regions, grounds)
    await ctx.session.flush()
    crowned = await crown_nexus(ctx, web, grounds)
    ctx.count("works_attuned_backfilled", await backfill_attunement(ctx))
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
