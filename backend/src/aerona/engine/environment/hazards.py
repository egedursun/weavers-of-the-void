from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.dangers import HAZARDS, HazardSpec
from aerona.catalog.terrain import TERRAIN
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.region import RegionHazardRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.crafts import InsuranceCover
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, ScarKind, SeasonWarmth, WeatherEffect
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.region import HazardSeason, TerrainHazard
from aerona.engine.body.hits import Harm
from aerona.engine.climes.shifts import fire_wind
from aerona.engine.context import TickContext
from aerona.engine.crafts.cover import claim
from aerona.engine.environment.book import EnvironmentBook, add_scar
from aerona.engine.environment.season_shape import season_of_warmth, season_phase, wettest
from aerona.engine.environment.succession import burn_back
from aerona.engine.environment.years import grant_sub_steps, sampled_years
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.military.units import stacks_of, sync, take
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import round_half_up, scaled_cap
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import record
from aerona.engine.water.courses import slide_dam
from aerona.rules.registry import Rules

PERMILLE = 1000
FLOODING_RIVERS = frozenset({RiverClass.RIVER, RiverClass.GREAT_RIVER})


@dataclass
class HazardTally:
    strikes: int = 0
    dead: int = 0
    injured: int = 0
    soldiers: int = 0
    by_world: dict[int, int] = field(default_factory=dict)


CHANCES: dict[TerrainHazard, Callable[[Rules], int]] = {
    TerrainHazard.AVALANCHE: lambda rules: rules.hazards.avalanche_chance,
    TerrainHazard.SPRING_FLOOD: lambda rules: rules.hazards.spring_flood_chance,
    TerrainHazard.WILDFIRE: lambda rules: rules.hazards.wildfire_chance,
    TerrainHazard.WHITEOUT: lambda rules: rules.hazards.whiteout_chance,
    TerrainHazard.MUDSLIDE: lambda rules: rules.hazards.mudslide_chance,
    TerrainHazard.FLASH_FLOOD: lambda rules: rules.hazards.flash_flood_chance,
    TerrainHazard.THIN_ICE: lambda rules: rules.hazards.thin_ice_chance,
    TerrainHazard.ICE_JAM: lambda rules: rules.hazards.ice_jam_chance,
    TerrainHazard.STORM_SURGE: lambda rules: rules.hazards.storm_surge_chance,
    TerrainHazard.DUST_STORM: lambda rules: rules.hazards.dust_storm_chance,
}
THRESHOLDS: dict[TerrainHazard, Callable[[Rules], int]] = {
    TerrainHazard.AVALANCHE: lambda rules: rules.hazards.avalanche_weather_min,
    TerrainHazard.SPRING_FLOOD: lambda rules: rules.hazards.spring_flood_weather_min,
    TerrainHazard.WILDFIRE: lambda rules: rules.hazards.wildfire_weather_min,
    TerrainHazard.WHITEOUT: lambda rules: rules.hazards.whiteout_weather_min,
    TerrainHazard.MUDSLIDE: lambda rules: rules.hazards.mudslide_weather_min,
    TerrainHazard.FLASH_FLOOD: lambda rules: rules.hazards.flash_flood_weather_min,
    TerrainHazard.THIN_ICE: lambda rules: rules.hazards.thin_ice_weather_min,
    TerrainHazard.ICE_JAM: lambda rules: rules.hazards.ice_jam_weather_min,
    TerrainHazard.STORM_SURGE: lambda rules: rules.hazards.storm_surge_weather_min,
    TerrainHazard.DUST_STORM: lambda rules: rules.hazards.dust_storm_weather_min,
}
DEATHS: dict[TerrainHazard, Callable[[Rules], int]] = {
    TerrainHazard.AVALANCHE: lambda rules: rules.hazards.avalanche_deaths_permille,
    TerrainHazard.SPRING_FLOOD: lambda rules: rules.hazards.spring_flood_deaths_permille,
    TerrainHazard.WILDFIRE: lambda rules: rules.hazards.wildfire_deaths_permille,
    TerrainHazard.WHITEOUT: lambda rules: rules.hazards.whiteout_deaths_permille,
    TerrainHazard.MUDSLIDE: lambda rules: rules.hazards.mudslide_deaths_permille,
    TerrainHazard.FLASH_FLOOD: lambda rules: rules.hazards.flash_flood_deaths_permille,
    TerrainHazard.THIN_ICE: lambda rules: rules.hazards.thin_ice_deaths_permille,
    TerrainHazard.ICE_JAM: lambda rules: rules.hazards.ice_jam_deaths_permille,
    TerrainHazard.STORM_SURGE: lambda rules: rules.hazards.storm_surge_deaths_permille,
    TerrainHazard.DUST_STORM: lambda rules: rules.hazards.dust_storm_deaths_permille,
}
ARMY_LOSSES: dict[TerrainHazard, Callable[[Rules], int]] = {
    TerrainHazard.AVALANCHE: lambda rules: rules.hazards.avalanche_army_pct,
    TerrainHazard.SPRING_FLOOD: lambda rules: rules.hazards.spring_flood_army_pct,
    TerrainHazard.WILDFIRE: lambda rules: rules.hazards.wildfire_army_pct,
    TerrainHazard.WHITEOUT: lambda rules: rules.hazards.whiteout_army_pct,
    TerrainHazard.MUDSLIDE: lambda rules: rules.hazards.mudslide_army_pct,
    TerrainHazard.FLASH_FLOOD: lambda rules: rules.hazards.flash_flood_army_pct,
    TerrainHazard.THIN_ICE: lambda rules: rules.hazards.thin_ice_army_pct,
    TerrainHazard.ICE_JAM: lambda rules: rules.hazards.ice_jam_army_pct,
    TerrainHazard.STORM_SURGE: lambda rules: rules.hazards.storm_surge_army_pct,
    TerrainHazard.DUST_STORM: lambda rules: rules.hazards.dust_storm_army_pct,
}
WORKS_CUT: dict[TerrainHazard, Callable[[Rules], int]] = {
    TerrainHazard.MUDSLIDE: lambda rules: rules.hazards.mudslide_works_cut_pct,
    TerrainHazard.FLASH_FLOOD: lambda rules: rules.hazards.flash_flood_works_cut_pct,
    TerrainHazard.THIN_ICE: lambda rules: rules.hazards.thin_ice_works_cut_pct,
    TerrainHazard.ICE_JAM: lambda rules: rules.hazards.ice_jam_works_cut_pct,
    TerrainHazard.STORM_SURGE: lambda rules: rules.hazards.storm_surge_works_cut_pct,
    TerrainHazard.DUST_STORM: lambda rules: rules.hazards.dust_storm_works_cut_pct,
}


def chance_of(rules: Rules, hazard: TerrainHazard, built: int = 0) -> float:
    cut = WORKS_CUT[hazard](rules) * built / PERCENT if hazard in WORKS_CUT else 0
    return CHANCES[hazard](rules) * (PERCENT - cut) / PERCENT


def loose_slope(ground: RegionEnvironmentRow) -> bool:
    return ground.cleared > 0 or ground.scars.get(ScarKind.ERODED.value, 0) > 0 or ground.scars.get(ScarKind.DEFORESTED.value, 0) > 0


SEASONED: dict[TerrainHazard, Callable[[RegionEnvironmentRow], bool]] = {
    TerrainHazard.MUDSLIDE: lambda ground: ground.wetland > 0 and loose_slope(ground),
    TerrainHazard.FLASH_FLOOD: lambda ground: ground.rainfall > 0,
    TerrainHazard.THIN_ICE: lambda ground: ground.river_class is not RiverClass.NONE or ground.coast_kind is not CoastKind.NONE,
    TerrainHazard.ICE_JAM: lambda ground: ground.river_class in FLOODING_RIVERS,
    TerrainHazard.STORM_SURGE: lambda ground: ground.coast_kind is not CoastKind.NONE,
    TerrainHazard.DUST_STORM: lambda ground: ground.forest_cover < PERCENT // 4 or ground.scars.get(ScarKind.OVERGRAZED.value, 0) > 0,
}


def threshold_of(rules: Rules, hazard: TerrainHazard) -> int:
    return THRESHOLDS[hazard](rules)


def deaths_of(rules: Rules, hazard: TerrainHazard) -> int:
    return DEATHS[hazard](rules)


def army_loss_of(rules: Rules, hazard: TerrainHazard) -> int:
    return ARMY_LOSSES[hazard](rules)


def exposed(rules: Rules, hazard: TerrainHazard, spec: HazardSpec, ground: RegionEnvironmentRow) -> bool:
    if spec.traits:
        return bool(spec.traits & TERRAIN[ground.dominant_terrain].traits) and hazard in SEASONED and SEASONED[hazard](ground)
    if hazard is TerrainHazard.SPRING_FLOOD:
        return hazard in TERRAIN[ground.dominant_terrain].hazards or ground.river_class in FLOODING_RIVERS
    if hazard is TerrainHazard.WILDFIRE:
        return hazard in TERRAIN[ground.dominant_terrain].hazards and ground.forest_cover >= rules.hazards.wildfire_forest_min
    return hazard in TERRAIN[ground.dominant_terrain].hazards


def season_for(seasons: list[WorldSeasonRow], kind: HazardSeason) -> WorldSeasonRow | None:
    if not seasons:
        return None
    if kind is HazardSeason.WARMING:
        phases = season_phase(seasons)
        return next((season for season in seasons if phases[season.position].warmth is SeasonWarmth.WARMING), seasons[0])
    if kind is HazardSeason.DRIEST:
        return min(seasons, key=lambda season: (season.rain_shift, season.position))
    if kind is HazardSeason.COLDEST:
        return season_of_warmth(seasons, SeasonWarmth.COLDEST) or seasons[0]
    if kind is HazardSeason.WETTEST:
        return wettest(seasons)
    return season_of_warmth(seasons, SeasonWarmth.WARMEST) or seasons[0]


def strength_of(rules: Rules, hazard: TerrainHazard, spec: HazardSpec, effects: dict[WeatherEffect, int]) -> int:
    value = effects.get(spec.effect, 0)
    if value < threshold_of(rules, hazard):
        return 0
    if hazard is TerrainHazard.WILDFIRE and effects.get(WeatherEffect.WET, 0) > rules.hazards.wildfire_wet_max:
        return 0
    return value


async def strike(
    ctx: TickContext, atlas: RegionAtlas, ground: RegionEnvironmentRow, hazard: TerrainHazard, *, season: WorldSeasonRow | None, year: int, tally: HazardTally
) -> None:
    rules = ctx.rules
    spec = HAZARDS[hazard]
    region = await ctx.session.get(EntityRow, ground.entity_id)
    if region is None:
        return
    dead = injured = soldiers = 0
    hurt_ids: list[int] = []
    for community_id in atlas.communities_in(ground.entity_id):
        community = await ctx.session.get(EntityRow, community_id)
        if community is None or community.status is not EntityStatus.CANON or community.entity_type not in {EntityType.SETTLEMENT, EntityType.PEOPLE}:
            continue
        population = round(stat(community, "population") or 0)
        lost = min(population, round_half_up(population * deaths_of(rules, hazard) / PERMILLE))
        if lost > 0:
            with flowing(FlowCategory.DISASTER):
                set_stats(community, population=population - lost)
            dead += lost
            await claim(ctx.session, community.id, InsuranceCover.HOUSE, rules.insurance.house_payout)
        mortals = list(
            await ctx.session.scalars(
                select(EntityRow)
                .where(await present_in(ctx.session, community), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
                .order_by(EntityRow.id)
            )
        )
        rng = ctx.rng(f"hazard.hurt.{community.id}.{hazard.value}.{year}")
        for mortal in rng.sample(mortals, min(len(mortals), rules.hazards.named_hurt)):
            await apply_hits(
                ctx,
                mortal,
                Harm(
                    rules.hazards.injury_damage,
                    HarmCause.DISASTER,
                    spec.label.lower(),
                    damage_type=spec.damage,
                    event_entity_id=region.id,
                ),
            )
            hurt_ids.append(mortal.id)
            injured += 1
    armies = await ctx.session.scalars(
        select(EntityRow)
        .join(ArmyProfileRow, ArmyProfileRow.army_entity_id == EntityRow.id)
        .where(ArmyProfileRow.region_entity_id == ground.entity_id, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for army in list(armies):
        rows = await stacks_of(ctx.session, army.id)
        loss = take(rows, round_half_up((stat(army, "size") or 0) * army_loss_of(rules, hazard) / PERCENT))
        if loss > 0:
            sync(army, rows, rules)
            soldiers += loss
    if hazard is TerrainHazard.WILDFIRE and f"scar.{ScarKind.BURNED.value}" not in ground.locked:
        add_scar(ground, ScarKind.BURNED, rules.hazards.wildfire_scar)
    if hazard is TerrainHazard.WILDFIRE:
        burn_back(ground, ctx.epoch)
    if hazard is TerrainHazard.MUDSLIDE:
        await slide_dam(ctx, ground)
    season_name = season.name if season is not None else "a hard season"
    write = await record(
        ctx,
        "hazard.struck",
        roles={IncidentRole.PLACE: region.id, IncidentRole.VICTIM: hurt_ids},
        facts={"hazard": hazard, "season": season_name.lower(), "deaths": dead, "injured": injured, "soldiers": soldiers},
        place=region.id,
        world_id=region.world_id,
        magnitude=min(PERCENT, dead),
    )
    ctx.session.add(
        RegionHazardRow(
            world_id=ground.world_id,
            region_entity_id=ground.entity_id,
            hazard=hazard,
            epoch=ctx.epoch,
            year=year,
            season_name=season.name if season is not None else None,
            deaths=dead,
            injured=injured,
            soldiers_lost=soldiers,
            incident_id=write.incident_id,
        )
    )
    tally.strikes += 1
    tally.by_world[ground.world_id] = tally.by_world.get(ground.world_id, 0) + 1
    tally.dead += dead
    tally.injured += injured
    tally.soldiers += soldiers


async def roll_hazards(ctx: TickContext) -> HazardTally:
    rules = ctx.rules
    tally = HazardTally()
    book = await EnvironmentBook.load(ctx.session, rules, ctx.epoch)
    atlas = book.atlas
    regions_of_world: dict[int, int] = {}
    for ground in book.regions.values():
        regions_of_world[ground.world_id] = regions_of_world.get(ground.world_id, 0) + 1
    for region_id in ctx.rng("hazard.order").shuffled(sorted(book.regions)):
        if held(region_id):
            continue
        ground = book.regions[region_id]
        world_cap = scaled_cap(rules.hazards.per_epoch_cap, rules.hazards.regions_per_extra_strike, regions_of_world.get(ground.world_id, 0))
        hazards = [hazard for hazard, spec in HAZARDS.items() if exposed(rules, hazard, spec, ground)]
        if not hazards or (not atlas.communities_in(region_id) and not await _armies_in(ctx, region_id)):
            continue
        years = sampled_years(ctx.environment, ground.world_id)
        years = years[: grant_sub_steps(ctx.environment, len(years))]
        seasons = book.seasons_of(ground.world_id)
        for hazard in hazards:
            spec = HAZARDS[hazard]
            season = season_for(seasons, spec.season)
            for year in years:
                if tally.by_world.get(ground.world_id, 0) >= world_cap:
                    break
                weather = book.weather(ctx.environment.world_seed, ctx.epoch, ground, season, f"hazard.{hazard.value}.{year.year}")
                power = strength_of(rules, hazard, spec, dict(weather.effects))
                fanned = await fire_wind(ctx.session, rules, region_id) if hazard is TerrainHazard.WILDFIRE else 1.0
                if power and ctx.rng(f"hazard.{region_id}.{hazard.value}.{year.year}").chance(
                    chance_of(rules, hazard, ground.built) * power / PERCENT * fanned
                ):
                    await strike(ctx, atlas, ground, hazard, season=season, year=year.year, tally=tally)
                    break
    await ctx.session.flush()
    return tally


async def _armies_in(ctx: TickContext, region_id: int) -> bool:
    found = await ctx.session.scalar(select(ArmyProfileRow.army_entity_id).where(ArmyProfileRow.region_entity_id == region_id).limit(1))
    return found is not None
