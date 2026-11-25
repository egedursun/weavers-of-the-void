import heapq
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.rocks import ROCKS
from aerona.catalog.strata import STRATA
from aerona.catalog.wind_belts import CURRENTS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import RegionGeologyRow, RegionStratumRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, ScarKind
from aerona.domain.enums.geology import DeepPassageOrigin, RockKind, UndergroundStratum
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepLocus
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.environment.book import add_scar
from aerona.engine.environment.cells import open_the_way_down
from aerona.engine.environment.columns import column_depth, columns_by_region, stratum_depth
from aerona.engine.phases.geography import NATURES_BY_SUBTYPE, seed_place
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.recording.terms import explaining, term
from aerona.rules.registry import Rules

U = UndergroundStratum
BREACHING = frozenset({U.MAGMA_SEA})


@dataclass
class DeepTally:
    layers: int = 0
    veins: int = 0
    strata: int = 0
    fires: int = 0
    tapped: int = 0
    stressed: int = 0


async def strata_by_region(session: AsyncSession) -> dict[int, list[RegionStratumRow]]:
    found: dict[int, list[RegionStratumRow]] = {}
    for row in await session.scalars(select(RegionStratumRow).order_by(RegionStratumRow.region_entity_id, RegionStratumRow.id)):
        found.setdefault(row.region_entity_id, []).append(row)
    return found


async def reached_strata(session: AsyncSession, stratum: UndergroundStratum) -> Counter[int]:
    found: Counter[int] = Counter()
    for region_id in await session.scalars(
        select(RegionStratumRow.region_entity_id).where(RegionStratumRow.stratum == stratum, RegionStratumRow.reached_epoch.is_not(None))
    ):
        found[region_id] += 1
    return found


async def mines_in(ctx: TickContext, region_id: int) -> list[StructureProfileRow]:
    rows = await ctx.session.scalars(
        select(StructureProfileRow)
        .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
        .where(StructureProfileRow.kind == StructureKind.MINE, EntityRow.status == EntityStatus.CANON)
        .order_by(StructureProfileRow.structure_entity_id)
    )
    atlas = await RegionAtlas.load(ctx.session)
    return [row for row in rows if atlas.top_region(row.structure_entity_id) == region_id]


async def gas_fire(ctx: TickContext, region_id: int) -> bool:
    if not ctx.rng(f"gas.{region_id}.{ctx.epoch}").chance(ctx.rules.rocks.coal_gas_pct):
        return False
    harm = ctx.rules.rocks.coal_gas_harm
    for mine in await mines_in(ctx, region_id):
        if not held(mine.structure_entity_id) and "condition" not in (mine.locked or []):
            mine.condition = clamp_int(mine.condition - harm, 0, PERCENT)
    await record(ctx, "mine.gas_fire", roles={IncidentRole.PLACE: region_id}, facts={"harm": harm}, place=region_id)
    return True


async def dig_coal(ctx: TickContext, region_id: int) -> None:
    community = next(iter((await RegionAtlas.load(ctx.session)).communities_in(region_id)), None)
    if community is not None and not held(community):
        await goods_of(ctx.session, ctx.epoch).add(community, CommodityKind.COAL, ctx.rules.rocks.coal_fuel, GoodsFlow.EXTRACTION)


async def reach_layer(ctx: TickContext, ground: RegionEnvironmentRow, row: RegionGeologyRow, tally: DeepTally) -> None:
    row.reached_epoch = ctx.epoch
    tally.layers += 1
    await record(
        ctx, "geology.layer_reached", roles={IncidentRole.PLACE: ground.entity_id}, facts={"rock": row.rock, "order": row.depth_order}, place=ground.entity_id
    )
    for material, richness in sorted(row.veins.items()):
        if "mineral_layers" in ground.locked or material in (ground.mineral_layers or {}):
            continue
        ground.mineral_layers = {**(ground.mineral_layers or {}), material: richness}
        tally.veins += 1
        await record(
            ctx, "geology.vein_found", roles={IncidentRole.PLACE: ground.entity_id}, facts={"vein": material, "richness": richness}, place=ground.entity_id
        )


async def reach_stratum(
    ctx: TickContext,
    ground: RegionEnvironmentRow,
    row: RegionStratumRow,
    tally: DeepTally,
    *,
    origin: DeepPassageOrigin = DeepPassageOrigin.DUG,
    digger_id: int | None = None,
    by_node_id: int | None = None,
) -> None:
    row.reached_epoch = ctx.epoch
    tally.strata += 1
    await record(
        ctx,
        "deep.stratum_reached",
        roles={IncidentRole.PLACE: ground.entity_id},
        facts={"stratum": row.stratum},
        place=ground.entity_id,
        steps=(StepDraft(StepAction.ENTER, locus_kind=StepLocus.STRATUM, locus_key=row.stratum.value, locus_node=ground.entity_id),),
    )
    await open_the_way_down(ctx, ground, row.stratum, origin=origin, digger_id=digger_id, by_node_id=by_node_id)
    if row.stratum in BREACHING:
        await breach(ctx, ground, row)
    elif row.stratum is U.DEEP_UNDERWORLD:
        below = await ctx.session.scalar(
            select(EntityRow.id)
            .where(EntityRow.world_id == ground.world_id, EntityRow.is_underworld.is_(True), EntityRow.status == EntityStatus.CANON)
            .limit(1)
        )
        if below is not None:
            await connect(ctx.session, ground.entity_id, below, BondKind.DISCOVERED, ctx.epoch, description="a way down")
    elif row.stratum is U.UNDER_OCEAN and ctx.rng(f"bore.{row.id}").chance(ctx.rules.underground.bore_flood_pct):
        add_scar(ground, ScarKind.FLOODED, PERCENT // 4)
    elif STRATA[row.stratum].caves and ctx.rng(f"cavern.{row.id}").chance(ctx.rules.underground.cavern_place_pct):
        await open_cave(ctx, ground)


async def open_cave(ctx: TickContext, ground: RegionEnvironmentRow) -> None:
    region = await ctx.session.get(EntityRow, ground.entity_id)
    if region is not None:
        await seed_place(ctx, region, move=False, nature=NATURES_BY_SUBTYPE["cave"])


async def breach(ctx: TickContext, ground: RegionEnvironmentRow, row: RegionStratumRow) -> None:
    row.breached_epoch = ctx.epoch
    if row.stratum is U.MAGMA_SEA and "scar.burned" not in ground.locked:
        add_scar(ground, ScarKind.BURNED, ctx.rules.underground.magma_breach_scar)
    await record(
        ctx,
        "deep.stratum_breached",
        roles={IncidentRole.PLACE: ground.entity_id},
        facts={"stratum": row.stratum},
        place=ground.entity_id,
        steps=(StepDraft(StepAction.BREACH, locus_kind=StepLocus.STRATUM, locus_key=row.stratum.value, locus_node=ground.entity_id),),
    )


async def draw_reservoir(ctx: TickContext, ground: RegionEnvironmentRow, row: RegionStratumRow, tally: DeepTally) -> None:
    table = ctx.rules.underground
    atlas = await RegionAtlas.load(ctx.session)
    community = next(iter(atlas.communities_in(ground.entity_id)), None)
    if community is None or row.volume <= 0 or "volume" in row.locked:
        return
    if row.tapped_epoch is None:
        row.tapped_epoch = ctx.epoch
        tally.tapped += 1
        await record(ctx, "deep.reservoir_tapped", roles={IncidentRole.PLACE: ground.entity_id}, facts={"volume": row.volume}, place=ground.entity_id)
    drawn = min(row.volume, table.reservoir_draw)
    row.volume -= drawn
    await goods_of(ctx.session, ctx.epoch).add(community, CommodityKind.FUEL, drawn, GoodsFlow.EXTRACTION)
    if row.pressure >= PERCENT // 2 and ctx.rng(f"blowout.{row.id}.{ctx.epoch}").chance(table.blowout_pct):
        row.pressure = clamp_int(row.pressure - PERCENT // 4, 0, PERCENT)
        add_scar(ground, ScarKind.POISONED, PERCENT // 5)
        await breach(ctx, ground, row)


def regrow(ctx: TickContext, rows: list[RegionGeologyRow]) -> None:
    for row in rows:
        if row.rock is RockKind.LIVING_TISSUE and "thickness" not in row.locked:
            row.thickness = clamp_int(row.thickness + ctx.rules.rocks.tissue_regrowth, 1, PERCENT)


def dissolve_salt(rules_pct: int, rows: list[RegionGeologyRow]) -> int:
    dissolved = 0
    for row in rows:
        if row.rock is RockKind.HALITE and "thickness" not in row.locked:
            cut = round_half_up(row.thickness * rules_pct / PERCENT)
            row.thickness = max(1, row.thickness - cut)
            dissolved += cut
    return dissolved


def stress_fault(ctx: TickContext, row: RegionStratumRow, worked: bool) -> bool:
    if not STRATA[row.stratum].faulted or "pressure" in row.locked or row.pressure >= PERCENT:
        return False
    table = ctx.rules.underground
    with explaining():
        term("underground.fault_stress_rate", table.fault_stress_rate, source_node_id=row.region_entity_id)
        if worked:
            term("underground.fault_mining_stress", table.fault_mining_stress, source_node_id=row.region_entity_id)
        row.pressure = clamp_int(row.pressure + table.fault_stress_rate + (table.fault_mining_stress if worked else 0), 0, PERCENT)
    return True


async def ripe_faults(session: AsyncSession) -> set[int]:
    statement = select(RegionStratumRow.region_entity_id).where(RegionStratumRow.stratum == U.FAULT_ZONE, RegionStratumRow.pressure >= PERCENT)
    return set(await session.scalars(statement.order_by(RegionStratumRow.region_entity_id)))


async def release_fault(session: AsyncSession, region_id: int) -> int | None:
    statement = select(RegionStratumRow).where(RegionStratumRow.region_entity_id == region_id, RegionStratumRow.stratum == U.FAULT_ZONE)
    row = await session.scalar(statement.limit(1))
    if row is None or "pressure" in row.locked:
        return None
    stress = row.pressure
    with explaining():
        term("underground.fault_released", -stress, source_node_id=region_id)
        row.pressure = 0
    return stress


def drift_shares(rules: Rules, start: int, neighbours: Callable[[int], list[int]], coasts: Mapping[int, OceanCurrent]) -> dict[int, float]:
    budget = float(rules.rocks.pumice_drift_reach * PERCENT)
    if budget <= 0:
        return {start: 1.0} if start in coasts else {}
    left = {start: budget}
    edge = [(-budget, start)]
    while edge:
        spare, here = heapq.heappop(edge)
        if -spare < left.get(here, 0.0):
            continue
        for other in neighbours(here):
            if other not in coasts:
                continue
            remaining = -spare - max(1, PERCENT - CURRENTS[coasts[other]].sailing_pct(rules))
            if remaining >= 0 and remaining > left.get(other, -1.0):
                left[other] = remaining
                heapq.heappush(edge, (-remaining, other))
    return {region_id: share / budget for region_id, share in left.items() if region_id in coasts}


async def raft_drift(ctx: TickContext, region: EntityRow) -> dict[int, float]:
    rows = await ctx.session.execute(
        select(RegionEnvironmentRow.entity_id, RegionEnvironmentRow.current).where(
            RegionEnvironmentRow.world_id == region.world_id, RegionEnvironmentRow.coast_kind != CoastKind.NONE
        )
    )
    coasts = {entity_id: current for entity_id, current in rows.all()}
    atlas = await RegionAtlas.load(ctx.session)
    return drift_shares(ctx.rules, region.id, atlas.neighbours, coasts)


async def pumice_rafts(ctx: TickContext, region: EntityRow) -> int:
    columns = await columns_by_region(ctx.session, [region.id])
    if region.world_id is None or not any(ROCKS[row.rock].floats for row in columns.get(region.id, [])):
        return 0
    reached = await raft_drift(ctx, region)
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.location_id.in_(sorted(reached)), EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    gathered = 0
    for town in towns:
        stone = round_half_up(ctx.rules.rocks.pumice_drift_stone * reached[town.location_id or region.id])
        if held(town.id) or stone <= 0:
            continue
        await goods_of(ctx.session, ctx.epoch).add(town.id, CommodityKind.STONE, stone, GoodsFlow.EXTRACTION)
        gathered += 1
    if gathered:
        await record(ctx, "rocks.pumice_rafts", roles={IncidentRole.PLACE: region.id}, facts={"shores": gathered}, place=region.id)
    return gathered


async def deepen(ctx: TickContext) -> DeepTally:
    tally = DeepTally()
    columns = await columns_by_region(ctx.session)
    strata = await strata_by_region(ctx.session)
    for depth_region, unders in sorted(strata.items()):
        if held(depth_region):
            continue
        above = await ctx.session.get(RegionEnvironmentRow, depth_region)
        worked = (above is not None and above.mined > 0) or any(under.stratum is U.RESERVOIR and under.tapped_epoch is not None for under in unders)
        tally.stressed += sum(1 for under in unders if stress_fault(ctx, under, worked))
    for region_id, rows in sorted(columns.items()):
        if held(region_id):
            continue
        regrow(ctx, rows)
        ground = await ctx.session.get(RegionEnvironmentRow, region_id)
        if ground is None or ground.mined <= 0:
            continue
        depth = ground.mined * ctx.rules.rocks.depth_per_mined
        floor = 0
        for row in rows:
            floor += row.thickness
            if row.reached_epoch is None and depth >= floor - row.thickness:
                await reach_layer(ctx, ground, row, tally)
        if any(row.rock is RockKind.COAL and row.reached_epoch is not None for row in rows):
            await dig_coal(ctx, region_id)
            tally.fires += int(await gas_fire(ctx, region_id))
        for under in strata.get(region_id, []):
            if under.reached_epoch is None and depth >= stratum_depth(ctx.rules, rows, under.stratum) and depth > column_depth(rows) // 2:
                await reach_stratum(ctx, ground, under, tally)
            if under.stratum is U.RESERVOIR and under.reached_epoch is not None:
                await draw_reservoir(ctx, ground, under, tally)
    await ctx.session.flush()
    return tally
