from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import FamineLoreRow, IntensificationRow, SoilNutrientRow
from aerona.db.tables.collective import GenerationRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.ecology import SpeciesProductRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow, RegionEnvironmentRow
from aerona.db.tables.flora import RegionCropRow
from aerona.db.tables.industry import CommunityMethodRow
from aerona.db.tables.settlement import SettlementInfrastructureRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import NutrientKind
from aerona.domain.enums.collective import FormativeKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import NotableYearKind, RiverClass, SoilKind
from aerona.domain.enums.industry import MethodKind, ProcessKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.agrarian.rings import put
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.nature.microbes import microbe_factor, soil_lives
from aerona.engine.primitives.capacity import LAND_COMMUNITY_TYPES, CapacityModel
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

N = NutrientKind
HALF = 50


@dataclass
class SoilTally:
    pressed: int = 0
    intensified: int = 0
    soils: int = 0
    salted: int = 0
    peoples: int = 0
    famine_foods: int = 0


@dataclass(frozen=True)
class FieldWork:
    rotating: set[int]
    terraced: set[int]
    irrigated: dict[int, int]
    drained: set[int]
    fodder: dict[int, float]
    roots: dict[int, float]


async def sown_shares(ctx: TickContext) -> tuple[dict[int, float], dict[int, float]]:
    yields: dict[int, set[CommodityKind]] = defaultdict(set)
    for species_id, commodity in await ctx.session.execute(select(SpeciesProductRow.species_entity_id, SpeciesProductRow.commodity)):
        if commodity is not None:
            yields[species_id].add(commodity)
    fodder: dict[int, float] = defaultdict(float)
    roots: dict[int, float] = defaultdict(float)
    for row in await ctx.session.scalars(select(RegionCropRow)):
        kinds = yields.get(row.plant_entity_id, set())
        if CommodityKind.FODDER in kinds:
            fodder[row.region_entity_id] = min(1.0, fodder[row.region_entity_id] + row.share / PERCENT)
        if CommodityKind.TUBERS in kinds:
            roots[row.region_entity_id] = min(1.0, roots[row.region_entity_id] + row.share / PERCENT)
    return dict(fodder), dict(roots)


async def press_land(ctx: TickContext, tally: SoilTally) -> None:
    table = ctx.rules.boserup
    capacity = await CapacityModel.load(ctx.session, ctx.rules)
    loads = capacity.build_loads(await canon(ctx.session, LAND_COMMUNITY_TYPES))
    rows = {row.region_entity_id: row for row in await ctx.session.scalars(select(IntensificationRow))}
    for key, load in sorted(loads.items()):
        kind, region_id = key
        if kind != "region" or load.population <= 0 or not load.communities or held(region_id):
            continue
        community = load.communities[0]
        ceiling = max(1.0, capacity.capacity(load, community, capacity.effective_fertility(community)))
        pressure = clamp_int(load.population / ceiling * PERCENT, 0, PERCENT * 3)
        over = max(0, pressure - table.onset)
        row = rows.get(region_id)
        if row is None:
            row = IntensificationRow(region_entity_id=region_id, locked=[])
            ctx.session.add(row)
        before = row.intensity
        target = clamp_int(over * table.intensity_pct / PERCENT, 0, PERCENT)
        put(row, "pressure", pressure)
        put(row, "intensity", clamp_int(row.intensity + (target - row.intensity) * table.drift_pct / PERCENT, 0, PERCENT))
        put(row, "research_boost", clamp_int(over * table.boost_pct / PERCENT, 0, table.boost_cap))
        row.updated_epoch = ctx.epoch
        tally.pressed += 1
        if before < HALF <= row.intensity:
            tally.intensified += 1
            await record(
                ctx,
                "boserup.intensified",
                roles={IncidentRole.SUBJECT: region_id},
                facts={"intensity": row.intensity, "pressure": row.pressure},
                place=region_id,
            )


async def field_work(ctx: TickContext, atlas: RegionAtlas) -> FieldWork:
    rotating: set[int] = set()
    terraced: set[int] = set()
    for community_id, method in await ctx.session.execute(
        select(CommunityMethodRow.community_node_id, CommunityMethodRow.method).where(CommunityMethodRow.process == ProcessKind.FARMING)
    ):
        region = atlas.top_region(community_id)
        if region is None:
            continue
        if method is MethodKind.CROP_ROTATION:
            rotating.add(region)
        elif method is MethodKind.IRRIGATED_TERRACES:
            terraced.add(region)
    irrigated: dict[int, int] = defaultdict(int)
    for settlement_id, level in await ctx.session.execute(
        select(SettlementInfrastructureRow.settlement_entity_id, SettlementInfrastructureRow.irrigation).where(SettlementInfrastructureRow.irrigation > 0)
    ):
        region = atlas.top_region(settlement_id)
        if region is not None:
            irrigated[region] = max(irrigated[region], level)
    for region in terraced:
        irrigated[region] = max(irrigated[region], 1)
    drained: set[int] = set()
    for (holder_id,) in await ctx.session.execute(select(HolderTechniqueRow.holder_entity_id).where(HolderTechniqueRow.technique == Technique.DRAINAGE)):
        region = atlas.top_region(holder_id)
        if region is not None:
            drained.add(region)
    fodder, roots = await sown_shares(ctx)
    return FieldWork(rotating, terraced, dict(irrigated), drained, fodder, roots)


def soil_life_of(rules: Rules, life: float) -> float:
    span = rules.microbes.recycling_pct / PERCENT
    return PERCENT / 2 * (1 + (life - 1) / span) if span > 0 else PERCENT / 2


def nutrient_change(ctx: TickContext, land: RegionEnvironmentRow, nutrient: NutrientKind, stock: int, work: FieldWork, *, life: float = 1.0) -> float:
    table = ctx.rules.nutrients
    region = land.entity_id
    farmed, grazed = land.farmed / PERCENT, land.grazed / PERCENT
    fallow = max(0, land.cleared - land.farmed - land.grazed) / PERCENT
    natural = (land.soil_base - stock) / table.recovery_divisor * life
    if nutrient is N.FIXED:
        return (
            natural
            - farmed * table.fixed_draw
            + (table.rotation_fix if region in work.rotating else 0)
            + fallow * table.fallow_pct
            + grazed * table.manure_pct / 2
            + farmed * work.fodder.get(region, 0.0) * table.fodder_fix
        )
    if nutrient is N.MINERAL:
        return (
            natural
            - farmed * (table.mineral_draw + work.roots.get(region, 0.0) * table.root_mineral)
            + (table.river_silt if land.river_class is not RiverClass.NONE else 0)
        )
    if nutrient is N.ORGANIC:
        return (
            natural
            - farmed * table.organic_draw
            - land.erosion / PERCENT * table.erosion_pct
            + (grazed * table.manure_pct + land.forest_cover / PERCENT * table.litter_pct) * life
            + (grazed * ctx.rules.soils.leached_amend_gain if land.soil is SoilKind.LEACHED else 0)
        )
    return stored_change(ctx, land, nutrient, stock, work, life=life)


def stored_change(ctx: TickContext, land: RegionEnvironmentRow, nutrient: NutrientKind, stock: int, work: FieldWork, *, life: float) -> float:
    table = ctx.rules.nutrients
    region = land.entity_id
    if nutrient is N.SEED_BANK:
        return (
            land.forest_cover / PERCENT * table.seed_build
            + (PERCENT - land.cleared) / PERCENT * table.seed_build / 2
            - land.cleared / PERCENT * table.seed_draw
        )
    if nutrient is N.SOIL_LIFE:
        return (soil_life_of(ctx.rules, life) - stock) * table.soil_life_follow_pct / PERCENT
    irrigation = work.irrigated.get(region, 0)
    if irrigation > 0 and region not in work.drained:
        return float(irrigation * table.irrigation_salt)
    return -float(table.leach)


async def feed_soils(ctx: TickContext, atlas: RegionAtlas, tally: SoilTally) -> None:
    work = await field_work(ctx, atlas)
    lives = await soil_lives(ctx.session)
    found: dict[int, dict[NutrientKind, SoilNutrientRow]] = defaultdict(dict)
    for row in await ctx.session.scalars(select(SoilNutrientRow)):
        found[row.region_entity_id][row.nutrient] = row
    for land in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id)):
        if atlas.is_water(land.entity_id) or held(land.entity_id):
            continue
        stocks = found[land.entity_id]
        for nutrient in NutrientKind:
            known = stocks.get(nutrient)
            if known is None:
                stocks[nutrient] = SoilNutrientRow(
                    region_entity_id=land.entity_id,
                    nutrient=nutrient,
                    stock=0 if nutrient is N.SALINITY else land.forest_cover if nutrient is N.SEED_BANK else land.soil_base,
                    updated_epoch=ctx.epoch,
                    locked=[],
                )
                ctx.session.add(stocks[nutrient])
                continue
            row = known
            before = row.stock
            if "stock" not in row.locked:
                row.stock = clamp_int(
                    row.stock + nutrient_change(ctx, land, nutrient, row.stock, work, life=microbe_factor(ctx.rules, lives.get(land.entity_id))), 0, PERCENT
                )
            put(row, "trend", clamp_int(row.stock - before, -PERCENT, PERCENT))
            row.updated_epoch = ctx.epoch
            if nutrient is N.SALINITY and before < ctx.rules.nutrients.noted_salinity <= row.stock:
                tally.salted += 1
                await record(ctx, "nutrients.salted", roles={IncidentRole.SUBJECT: land.entity_id}, facts={"salinity": row.stock}, place=land.entity_id)
            elif nutrient is N.SALINITY and row.stock < ctx.rules.nutrients.noted_salinity // 2 <= before:
                await record(ctx, "nutrients.recovered", roles={IncidentRole.SUBJECT: land.entity_id}, facts={"salinity": row.stock}, place=land.entity_id)
        tally.soils += 1


async def hungry_years(ctx: TickContext) -> dict[int, int]:
    since = ctx.epoch - ctx.rules.famine_foods.memory_epochs
    rows = await ctx.session.execute(
        select(NotableYearRow.region_entity_id, func.count())
        .where(NotableYearRow.kind == NotableYearKind.HUNGER, NotableYearRow.epoch >= since, NotableYearRow.region_entity_id.is_not(None))
        .group_by(NotableYearRow.region_entity_id)
    )
    return {region: int(count) for region, count in rows.all() if region is not None}


@dataclass
class Homes:
    regions: dict[int, set[int]]
    communities: dict[int, set[int]]


async def people_homes(ctx: TickContext, atlas: RegionAtlas) -> Homes:
    homes = Homes(defaultdict(set), defaultdict(set))
    for entity in await canon(ctx.session, [EntityType.PEOPLE, EntityType.SETTLEMENT]):
        people = await people_of(ctx.session, entity)
        region = atlas.top_region(entity.id)
        if people is None or people.status is not EntityStatus.CANON:
            continue
        homes.communities[people.id].add(entity.id)
        if region is not None:
            homes.regions[people.id].add(region)
    return homes


async def famine_generations(ctx: TickContext) -> dict[int, int]:
    found: dict[int, int] = defaultdict(int)
    for row in await ctx.session.scalars(select(GenerationRow).where(GenerationRow.passed_epoch.is_(None))):
        if FormativeKind.FAMINE.value in row.formative:
            found[row.community_entity_id] += 1
    return found


async def remember_famines(ctx: TickContext, atlas: RegionAtlas, tally: SoilTally) -> None:
    table = ctx.rules.famine_foods
    years = await hungry_years(ctx)
    generations = await famine_generations(ctx)
    homes = await people_homes(ctx, atlas)
    lore = {row.people_entity_id: row for row in await ctx.session.scalars(select(FamineLoreRow))}
    for people_id, regions in sorted(homes.regions.items()):
        if held(people_id):
            continue
        formed = sum(generations.get(community, 0) for community in homes.communities.get(people_id, set()))
        target = clamp_int(sum(years.get(region, 0) for region in regions) * table.per_famine + formed * table.per_generation, 0, PERCENT)
        row = lore.get(people_id)
        if row is None:
            if target <= 0:
                continue
            row = FamineLoreRow(people_entity_id=people_id, locked=[])
            ctx.session.add(row)
        knew = row.famine_foods
        put(row, "memory", max(round_half_up(row.memory * (PERCENT - table.fade_pct) / PERCENT), target))
        put(row, "famine_foods", row.memory >= table.foods_at or (row.famine_foods and row.memory >= table.foods_at // 2))
        aim = row.memory * table.storage_pct / PERCENT
        put(row, "storage", clamp_int(row.storage + (aim - row.storage) * table.drift_pct / PERCENT, 0, PERCENT))
        row.updated_epoch = ctx.epoch
        tally.peoples += 1
        if row.famine_foods and not knew:
            tally.famine_foods += 1
            people = await ctx.session.get(EntityRow, people_id)
            if people is not None:
                await record(
                    ctx,
                    "famine.foods_learned",
                    roles={IncidentRole.SUBJECT: people.id},
                    facts={"memory": row.memory, "storage": row.storage},
                )


async def keep_soil(ctx: TickContext, tally: SoilTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    await press_land(ctx, tally)
    await feed_soils(ctx, atlas, tally)
    await remember_famines(ctx, atlas, tally)
    await ctx.session.flush()
