from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life_traits import TRADE_MODE_TRAITS, having
from aerona.catalog.nature_kinds50 import CARRIERS, COAST_FORMS, LOCAL_CAUSES, SEDIMENTS
from aerona.catalog.terrain import terrains
from aerona.constants.units import PERCENT
from aerona.core.total import partial
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.water import MONTHS, CoastRow, LocalClimateRow, RegionCryosphereRow, SedimentFlowRow
from aerona.db.write_guard import held
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, SoilKind, TerrainKind, TerrainTrait
from aerona.domain.enums.life_traits import TradeModeTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.water import CoastForm, LocalClimateCause, SedimentCarrier, SedimentKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining_alone, term
from aerona.engine.water.courses import keep_courses
from aerona.rules.registry import Rules
from aerona.rules.registry.water import WaterAndIceRules

COAST_OF_KIND: Mapping[CoastKind, CoastForm] = partial(
    CoastKind,
    {
        CoastKind.CLIFF: CoastForm.CLIFF,
        CoastKind.BEACH: CoastForm.BEACH,
        CoastKind.HARBOUR_SITE: CoastForm.LAGOON,
        CoastKind.REEF: CoastForm.REEF,
    },
    without=(CoastKind.NONE,),
)
WATER_MODES = having(TRADE_MODE_TRAITS, TradeModeTrait.WATER_MODES)
THOUSAND = 1000
ROUGH = 60
HIGH = 70
WOODED = 50
DESERT = frozenset({TerrainKind.DESERT})
DRY_LANDS = terrains(TerrainTrait.ARID)
WARM_SEA = 70
STILL_WATER = 60
FILL_BASE = 50


@dataclass
class WaterTally:
    closed: int = 0
    opened: int = 0
    thawed: int = 0
    droughts: int = 0
    silted: int = 0
    lost: int = 0
    grew: int = 0
    glaciers: int = 0
    courses: int = 0
    soils: int = 0


def ice_months_of(rules: Rules, land: RegionEnvironmentRow, shift: int) -> int:
    cold = max(1, rules.environment.cold_below)
    months = round_half_up((cold - land.temperature + land.seasonality // 10) * MONTHS / cold)
    return clamp_int(months + shift, 0, MONTHS)


def frozen_depth_of(rules: Rules, land: RegionEnvironmentRow) -> int:
    frozen = max(1, rules.environment.frozen_below)
    return clamp_int((frozen - land.temperature) * PERCENT // frozen, 0, PERCENT)


def snowpack_of(rules: Rules, land: RegionEnvironmentRow) -> int:
    mild = max(1, rules.environment.temperate_below)
    if land.temperature >= mild:
        return 0
    return clamp_int(land.rainfall * (mild - land.temperature) // mild + land.elevation_mean // 10, 0, PERCENT)


async def towns_in(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> list[EntityRow]:
    found: list[EntityRow] = []
    for community in atlas.communities_in(region_id):
        town = await ctx.session.get(EntityRow, community)
        if town is not None and town.entity_type is EntityType.SETTLEMENT and town.status is EntityStatus.CANON and not held(town.id):
            found.append(town)
    return found


async def cost_towns(ctx: TickContext, atlas: RegionAtlas, region_id: int, key: str, loss: int) -> None:
    for town in await towns_in(ctx, atlas, region_id):
        with explaining_alone():
            term(f"water_and_ice.{key}", -loss, source_node_id=region_id)
            shift_stat(town, "prosperity", -loss, low=0, high=PERCENT)


async def cryosphere_of(ctx: TickContext, region_id: int) -> RegionCryosphereRow:
    row = await ctx.session.get(RegionCryosphereRow, region_id)
    if row is None:
        row = RegionCryosphereRow(region_entity_id=region_id, locked=[])
        ctx.session.add(row)
    return row


def cool(rules: Rules, land: RegionEnvironmentRow, row: RegionCryosphereRow) -> None:
    before_glacier = row.glacier_extent
    with explaining_alone():
        term("water_and_ice.cold", PERCENT - land.temperature, source_node_id=land.entity_id)
        if "ice_months" not in row.locked:
            row.ice_months = ice_months_of(rules, land, row.ice_shift)
        if "ice_thickness" not in row.locked:
            row.ice_thickness = clamp_int(row.ice_months * PERCENT // MONTHS, 0, PERCENT)
        if "frozen_depth" not in row.locked:
            row.frozen_depth = frozen_depth_of(rules, land)
        if "thaw_months" not in row.locked:
            row.thaw_months = MONTHS - row.ice_months if row.frozen_depth > 0 else 0
        if "snowpack" not in row.locked:
            row.snowpack = snowpack_of(rules, land)
        if "glacier_extent" not in row.locked:
            row.glacier_extent = clamp_int(row.glacier_extent + (row.snowpack - PERCENT // 2 - row.glacier_extent) // 4, 0, PERCENT)
        if "glacier_trend" not in row.locked:
            row.glacier_trend = clamp_int(row.glacier_extent - before_glacier, -PERCENT, PERCENT)


async def freeze(ctx: TickContext, land: RegionEnvironmentRow, atlas: RegionAtlas, tally: WaterTally) -> None:
    table = ctx.rules.water_and_ice
    row = await cryosphere_of(ctx, land.entity_id)
    before_ice, before_frozen = row.ice_months, row.frozen_depth
    cool(ctx.rules, land, row)
    closed = row.ice_months >= table.ice_route_block_months
    if closed and before_ice < table.ice_route_block_months:
        tally.closed += 1
        await record(ctx, "land.ice_closed", roles={IncidentRole.PLACE: land.entity_id}, facts={"months": row.ice_months}, place=land.entity_id)
        if row.ice_months >= MONTHS // 2:
            await record(ctx, "land.ice_road", roles={IncidentRole.PLACE: land.entity_id}, facts={"months": row.ice_months}, place=land.entity_id)
    elif not closed and before_ice >= table.ice_route_block_months:
        tally.opened += 1
        await record(ctx, "land.ice_opened", roles={IncidentRole.PLACE: land.entity_id}, facts={"months": row.ice_months}, place=land.entity_id)
    if before_frozen - row.frozen_depth >= table.thaw_step:
        await thaw(ctx, land.entity_id, atlas, before_frozen - row.frozen_depth, tally)
    if abs(row.glacier_trend) >= table.glacier_step:
        tally.glaciers += 1
        key = "land.glacier_advanced" if row.glacier_trend > 0 else "land.glacier_retreated"
        await record(ctx, key, roles={IncidentRole.PLACE: land.entity_id}, facts={"extent": row.glacier_extent}, place=land.entity_id)
    if row.snowpack > 0 and row.snowpack < table.snow_drought_below and land.river_class is not RiverClass.NONE:
        tally.droughts += 1
        downstream = [land.entity_id, *atlas.neighbours(land.entity_id)]
        for region in downstream:
            await cost_towns(ctx, atlas, region, "snow_drought", table.snow_drought_loss * table.snow_water_share_pct // PERCENT)
        await record(ctx, "land.snow_drought", roles={IncidentRole.PLACE: land.entity_id}, facts={"snowpack": row.snowpack}, place=land.entity_id)


async def thaw(ctx: TickContext, region_id: int, atlas: RegionAtlas, fall: int, tally: WaterTally) -> None:
    table = ctx.rules.water_and_ice
    tally.thawed += 1
    if ctx.rng(seed_of("thaw", region_id, ctx.epoch)).chance(table.thaw_collapse_pct):
        await cost_towns(ctx, atlas, region_id, "thaw", table.thaw_loss)
        await record(ctx, "land.thaw_collapse", roles={IncidentRole.PLACE: region_id}, facts={"fall": fall}, place=region_id)
    beds = await ctx.session.scalars(
        select(FossilBedRow)
        .where(FossilBedRow.region_entity_id == region_id, FossilBedRow.frozen.is_(True), FossilBedRow.found_epoch.is_(None))
        .order_by(FossilBedRow.id)
    )
    for bed in list(beds):
        if "found_epoch" in bed.locked:
            continue
        bed.found_epoch = ctx.epoch
        await record(ctx, "land.thaw_release", roles={IncidentRole.PLACE: region_id}, facts={"richness": bed.richness}, place=region_id)


def carried_by(table: WaterAndIceRules, land: RegionEnvironmentRow, frozen_below: int) -> tuple[SedimentCarrier | None, int]:
    if land.river_class is not RiverClass.NONE:
        return SedimentCarrier.RIVER, table.great_river_load if land.river_class is RiverClass.GREAT_RIVER else table.river_load
    ways = (
        (land.temperature < frozen_below, SedimentCarrier.ICE),
        (land.dominant_terrain in DESERT, SedimentCarrier.WIND),
        (land.roughness >= ROUGH, SedimentCarrier.SLOPE),
        (land.coast_kind in COAST_OF_KIND, SedimentCarrier.WAVE),
    )
    carrier = next((way for met, way in ways if met), None)
    return carrier, table.wind_load if carrier is not None else 0


def sediment_kind(land: RegionEnvironmentRow, sink: RegionEnvironmentRow | None, carrier: SedimentCarrier) -> SedimentKind:
    if carrier is SedimentCarrier.RIVER and land.dominant_terrain in DRY_LANDS:
        return SedimentKind.EVAPORITE
    if carrier is SedimentCarrier.WAVE and sink is not None and (sink.coast_kind is CoastKind.REEF or sink.temperature >= WARM_SEA):
        return SedimentKind.CARBONATE
    if carrier in (SedimentCarrier.RIVER, SedimentCarrier.WAVE) and sink is not None and sink.wetland >= STILL_WATER:
        return SedimentKind.CLAY
    return CARRIERS[carrier].kind


async def lay_soils(ctx: TickContext, lands: dict[int, RegionEnvironmentRow], flows: list[SedimentFlowRow]) -> int:
    table = ctx.rules.sediment
    loads: dict[tuple[int, SedimentKind], int] = {}
    for flow in flows:
        loads[flow.sink_region_id, flow.kind] = loads.get((flow.sink_region_id, flow.kind), 0) + flow.load
    laid = 0
    for (region_id, kind), load in sorted(loads.items()):
        land = lands.get(region_id)
        soil = SEDIMENTS[kind].soil
        if land is None or held(region_id) or "soil" in land.locked or land.soil is soil or load < table.soil_lay_load:
            continue
        if ctx.rng(f"sediment_soil.{region_id}.{kind.value}.{ctx.epoch}").chance(table.soil_lay_pct):
            land.soil = soil
            laid += 1
            await record(
                ctx, "land.sediment_laid", roles={IncidentRole.PLACE: region_id}, facts={"sediment": kind, "load": clamp_int(load, 0, PERCENT)}, place=region_id
            )
    for land in lands.values():
        dry = land.dominant_terrain in DRY_LANDS and land.farmed > 0 and land.river_class is not RiverClass.NONE
        open_soil = not held(land.entity_id) and "soil" not in land.locked and land.soil is not SoilKind.SALINE
        if dry and open_soil and ctx.rng(f"salt_irrigation.{land.entity_id}.{ctx.epoch}").chance(table.salt_irrigation_pct):
            land.soil = SoilKind.SALINE
            laid += 1
            await record(
                ctx,
                "land.sediment_laid",
                roles={IncidentRole.PLACE: land.entity_id},
                facts={"sediment": SedimentKind.EVAPORITE, "load": land.farmed},
                place=land.entity_id,
            )
    return laid


async def seed_flows(ctx: TickContext, land: RegionEnvironmentRow, atlas: RegionAtlas, lands: dict[int, RegionEnvironmentRow], sources: set[int]) -> None:
    table = ctx.rules.water_and_ice
    if land.entity_id in sources:
        return
    below = sorted((lands[other].elevation_mean, other) for other in atlas.neighbours(land.entity_id) if other in lands)
    shores = [other for other in atlas.neighbours(land.entity_id) if other in lands and lands[other].coast_kind in COAST_OF_KIND]
    carrier, load = carried_by(table, land, ctx.rules.environment.frozen_below)
    sink = shores[0] if carrier is SedimentCarrier.WAVE and shores else below[0][1] if below and below[0][0] <= land.elevation_mean else None
    if carrier is None or sink is None:
        return
    kind = sediment_kind(land, lands.get(sink), carrier)
    ctx.session.add(SedimentFlowRow(source_region_id=land.entity_id, sink_region_id=sink, carrier=carrier, kind=kind, load=load, locked=[]))


def coast_form(land: RegionEnvironmentRow) -> CoastForm:
    if land.dominant_terrain is TerrainKind.MANGROVE:
        return CoastForm.MANGROVE
    if land.river_class in (RiverClass.RIVER, RiverClass.GREAT_RIVER):
        return CoastForm.ESTUARY
    return COAST_OF_KIND[land.coast_kind]


async def coast_of(ctx: TickContext, land: RegionEnvironmentRow) -> CoastRow | None:
    row = await ctx.session.get(CoastRow, land.entity_id)
    if row is None and land.coast_kind in COAST_OF_KIND:
        row = CoastRow(region_entity_id=land.entity_id, form=coast_form(land), locked=[])
        ctx.session.add(row)
    return row


async def shape_coast(ctx: TickContext, land: RegionEnvironmentRow, sediment: tuple[int, int], atlas: RegionAtlas, tally: WaterTally) -> None:
    inflow, richness = sediment
    table = ctx.rules.water_and_ice
    row = await coast_of(ctx, land)
    if row is None:
        return
    with explaining_alone():
        term("water_and_ice.sediment", inflow, source_node_id=land.entity_id)
        if "rate" not in row.locked:
            spec = COAST_FORMS[row.form]
            wear = table.coast_wear_per_epoch * spec.wear(ctx.rules) // PERCENT
            build = inflow * table.delta_growth_per_epoch // PERCENT * 10 * (PERCENT + spec.build(ctx.rules)) // PERCENT
            row.rate = clamp_int(build - wear, -PERCENT, PERCENT)
        if "progress" not in row.locked:
            row.progress = clamp_int(row.progress + row.rate, -PERCENT, PERCENT)
        shifted = row.form is CoastForm.BARRIER_ISLAND and ctx.rng(f"barrier.{land.entity_id}.{ctx.epoch}").chance(ctx.rules.coasts.barrier_shift_pct)
        if shifted and "progress" not in row.locked:
            row.progress = clamp_int(row.progress - PERCENT // 4, -PERCENT, PERCENT)
        if "harbour_silting" not in row.locked:
            laid = inflow * table.silting_per_epoch * COAST_FORMS[row.form].silting_pct // PERCENT // PERCENT
            row.harbour_silting = clamp_int(row.harbour_silting + laid, 0, PERCENT)
    if row.harbour_silting >= PERCENT and "harbour_silting" not in row.locked:
        tally.silted += 1
        row.harbour_silting = PERCENT // 2
        await cost_towns(ctx, atlas, land.entity_id, "silted", table.silted_loss)
        await record(ctx, "land.silted", roles={IncidentRole.PLACE: land.entity_id}, facts={"silting": PERCENT}, place=land.entity_id)
    if row.progress >= PERCENT:
        tally.grew += 1
        row.progress = 0
        if "form" not in row.locked:
            row.form = CoastForm.DELTA
        if "soil_fertility" not in land.locked:
            land.soil_fertility = clamp_int(land.soil_fertility + table.delta_fertility * richness // PERCENT, 0, PERCENT)
        await record(ctx, "land.delta_grew", roles={IncidentRole.PLACE: land.entity_id}, facts={"fertility": land.soil_fertility}, place=land.entity_id)
    elif row.progress <= -PERCENT:
        tally.lost += 1
        row.progress = 0
        await cost_towns(ctx, atlas, land.entity_id, "coast_lost", table.coast_loss)
        await record(ctx, "land.coast_lost", roles={IncidentRole.PLACE: land.entity_id}, facts={"loss": table.coast_loss}, place=land.entity_id)


async def cause_of(ctx: TickContext, atlas: RegionAtlas, town: EntityRow) -> LocalClimateCause:
    region = atlas.top_region(town.id)
    land = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    if land is None:
        return LocalClimateCause.BUILT
    if land.elevation_mean >= HIGH:
        return LocalClimateCause.SLOPE
    if land.roughness >= ROUGH:
        return LocalClimateCause.VALLEY
    if land.coast_kind in COAST_OF_KIND or land.river_class is not RiverClass.NONE:
        return LocalClimateCause.WATER
    if land.forest_cover >= WOODED:
        return LocalClimateCause.FOREST
    return LocalClimateCause.BUILT


async def warm_towns(ctx: TickContext, atlas: RegionAtlas) -> None:
    table = ctx.rules.water_and_ice
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in list(towns):
        if held(town.id):
            continue
        row = await ctx.session.get(LocalClimateRow, town.id)
        if row is None:
            row = LocalClimateRow(place_entity_id=town.id, cause=await cause_of(ctx, atlas, town), locked=[])
            ctx.session.add(row)
        if "heat_shift" not in row.locked:
            people = stat_or(town, "population", 0)
            row.heat_shift = clamp_int(people // THOUSAND * table.local_heat_per_density + LOCAL_CAUSES[row.cause].heat, -50, 50)
        if "humidity_shift" not in row.locked:
            row.humidity_shift = clamp_int(LOCAL_CAUSES[row.cause].humidity, -50, 50)
        if row.heat_shift >= table.heat_threshold:
            region = atlas.top_region(town.id)
            if region is None or held(region):
                continue
            active = select(OutbreakRow).where(OutbreakRow.region_entity_id == region, OutbreakRow.status == OutbreakStatus.ACTIVE).order_by(OutbreakRow.id)
            for outbreak in await ctx.session.scalars(active):
                if "severity" not in outbreak.locked:
                    with explaining_alone():
                        term("water_and_ice.heat", table.heat_outbreak, source_node_id=town.id)
                        outbreak.severity = clamp_int(outbreak.severity + table.heat_outbreak, 0, PERCENT)


async def ice_open_pct(ctx: TickContext, mode: TradeMode, path: list[int]) -> int:
    if mode not in WATER_MODES or not path:
        return PERCENT
    block = ctx.rules.water_and_ice.ice_route_block_months
    months = [
        row.ice_months
        for row in await ctx.session.scalars(select(RegionCryosphereRow).where(RegionCryosphereRow.region_entity_id.in_(path)))
        if row.ice_months >= block
    ]
    return clamp_int(PERCENT - max(months, default=0) * PERCENT // MONTHS, 0, PERCENT)


async def keep_water(ctx: TickContext, tally: WaterTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    lands = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id))}
    for kept in (RegionCryosphereRow, CoastRow, LocalClimateRow):
        list(await ctx.session.scalars(select(kept)))
    list(await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT)))
    sources = set(await ctx.session.scalars(select(SedimentFlowRow.source_region_id)))
    for land in lands.values():
        if held(land.entity_id):
            continue
        await freeze(ctx, land, atlas, tally)
        await seed_flows(ctx, land, atlas, lands, sources)
    await ctx.session.flush()
    inflow: dict[int, int] = {}
    worth: dict[int, int] = {}
    flows = list(await ctx.session.scalars(select(SedimentFlowRow).order_by(SedimentFlowRow.id)))
    for flow in flows:
        inflow[flow.sink_region_id] = inflow.get(flow.sink_region_id, 0) + flow.load * SEDIMENTS[flow.kind].fill(ctx.rules) // FILL_BASE
        worth[flow.sink_region_id] = worth.get(flow.sink_region_id, 0) + flow.load * SEDIMENTS[flow.kind].fertility(ctx.rules)
    for land in lands.values():
        if not held(land.entity_id):
            came = inflow.get(land.entity_id, 0)
            await shape_coast(ctx, land, (clamp_int(came, 0, PERCENT), worth.get(land.entity_id, 0) // max(1, came)), atlas, tally)
    tally.courses += await keep_courses(ctx, lands, inflow)
    tally.soils += await lay_soils(ctx, lands, flows)
    await warm_towns(ctx, atlas)
    await ctx.session.flush()
