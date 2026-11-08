from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.dangers import HAZARDS, HazardSpec
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.region import RegionHazardRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import RiverClass, ScarKind, WeatherEffect
from aerona.domain.enums.region import HazardSeason, TerrainHazard
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.environment.book import EnvironmentBook, add_scar
from aerona.engine.environment.years import grant_sub_steps, sampled_years
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.military.units import stacks_of, sync, take
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

PERMILLE = 1000
FLOODING_RIVERS = frozenset({RiverClass.RIVER, RiverClass.GREAT_RIVER})


@dataclass
class HazardTally:
    strikes: int = 0
    dead: int = 0
    injured: int = 0
    soldiers: int = 0


CHANCES: dict[TerrainHazard, Callable[[Rules], int]] = {
    TerrainHazard.AVALANCHE: lambda rules: rules.hazards.avalanche_chance,
    TerrainHazard.SPRING_FLOOD: lambda rules: rules.hazards.spring_flood_chance,
    TerrainHazard.WILDFIRE: lambda rules: rules.hazards.wildfire_chance,
    TerrainHazard.WHITEOUT: lambda rules: rules.hazards.whiteout_chance,
}
THRESHOLDS: dict[TerrainHazard, Callable[[Rules], int]] = {
    TerrainHazard.AVALANCHE: lambda rules: rules.hazards.avalanche_weather_min,
    TerrainHazard.SPRING_FLOOD: lambda rules: rules.hazards.spring_flood_weather_min,
    TerrainHazard.WILDFIRE: lambda rules: rules.hazards.wildfire_weather_min,
    TerrainHazard.WHITEOUT: lambda rules: rules.hazards.whiteout_weather_min,
}
DEATHS: dict[TerrainHazard, Callable[[Rules], int]] = {
    TerrainHazard.AVALANCHE: lambda rules: rules.hazards.avalanche_deaths_permille,
    TerrainHazard.SPRING_FLOOD: lambda rules: rules.hazards.spring_flood_deaths_permille,
    TerrainHazard.WILDFIRE: lambda rules: rules.hazards.wildfire_deaths_permille,
    TerrainHazard.WHITEOUT: lambda rules: rules.hazards.whiteout_deaths_permille,
}
ARMY_LOSSES: dict[TerrainHazard, Callable[[Rules], int]] = {
    TerrainHazard.AVALANCHE: lambda rules: rules.hazards.avalanche_army_pct,
    TerrainHazard.SPRING_FLOOD: lambda rules: rules.hazards.spring_flood_army_pct,
    TerrainHazard.WILDFIRE: lambda rules: rules.hazards.wildfire_army_pct,
    TerrainHazard.WHITEOUT: lambda rules: rules.hazards.whiteout_army_pct,
}


def chance_of(rules: Rules, hazard: TerrainHazard) -> int:
    return CHANCES[hazard](rules)


def threshold_of(rules: Rules, hazard: TerrainHazard) -> int:
    return THRESHOLDS[hazard](rules)


def deaths_of(rules: Rules, hazard: TerrainHazard) -> int:
    return DEATHS[hazard](rules)


def army_loss_of(rules: Rules, hazard: TerrainHazard) -> int:
    return ARMY_LOSSES[hazard](rules)


def exposed(rules: Rules, hazard: TerrainHazard, spec: HazardSpec, ground: RegionEnvironmentRow) -> bool:
    if hazard is TerrainHazard.SPRING_FLOOD:
        return ground.dominant_terrain in spec.terrains or ground.river_class in FLOODING_RIVERS
    if hazard is TerrainHazard.WILDFIRE:
        return ground.dominant_terrain in spec.terrains and ground.forest_cover >= rules.hazards.wildfire_forest_min
    return ground.dominant_terrain in spec.terrains


def season_for(seasons: list[WorldSeasonRow], kind: HazardSeason) -> WorldSeasonRow | None:
    if not seasons:
        return None
    if kind is HazardSeason.COLDEST:
        return min(seasons, key=lambda season: (season.temperature_shift, season.position))
    if kind is HazardSeason.WETTEST:
        return max(seasons, key=lambda season: (season.rain_shift, -season.position))
    return max(seasons, key=lambda season: (season.temperature_shift, -season.rain_shift, -season.position))


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
                    spec.words,
                    kind=spec.injury,
                    severity=rules.hazards.injury_severity,
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
    season_name = season.name if season is not None else "a hard season"
    write = await ctx.chronicle(
        ChronicleKind.DISASTER,
        spec.line.format(region=region.name, season=season_name.lower(), deaths=dead) + (f"; {injured} were hurt" if injured else "") + ".",
        template_key=f"hazard.{hazard.value}",
        entity_ids=[region.id, *hurt_ids],
        world_id=region.world_id,
        place_entity_id=region.id,
        magnitude=min(PERCENT, dead),
        year=year,
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
    tally.dead += dead
    tally.injured += injured
    tally.soldiers += soldiers


async def roll_hazards(ctx: TickContext) -> HazardTally:
    rules = ctx.rules
    tally = HazardTally()
    book = await EnvironmentBook.load(ctx.session, rules, ctx.epoch)
    atlas = book.atlas
    for region_id in sorted(book.regions):
        if held(region_id):
            continue
        ground = book.regions[region_id]
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
                if tally.strikes >= rules.hazards.per_epoch_cap:
                    return tally
                weather = book.weather(ctx.environment.world_seed, ctx.epoch, ground, season, f"hazard.{hazard.value}.{year.year}")
                power = strength_of(rules, hazard, spec, dict(weather.effects))
                if power and ctx.rng(f"hazard.{region_id}.{hazard.value}.{year.year}").chance(chance_of(rules, hazard) * power / PERCENT):
                    await strike(ctx, atlas, ground, hazard, season=season, year=year.year, tally=tally)
                    break
    await ctx.session.flush()
    return tally


async def _armies_in(ctx: TickContext, region_id: int) -> bool:
    found = await ctx.session.scalar(select(ArmyProfileRow.army_entity_id).where(ArmyProfileRow.region_entity_id == region_id).limit(1))
    return found is not None
