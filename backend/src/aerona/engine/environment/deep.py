from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.strata import STRATA
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import RegionGeologyRow, RegionStratumRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.geology import RockKind, UndergroundStratum
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.environment.book import add_scar
from aerona.engine.environment.columns import column_depth, columns_by_region, stratum_depth
from aerona.engine.phases.geography import NATURES_BY_SUBTYPE, seed_place
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.recording.record import record

U = UndergroundStratum
BREACHING = frozenset({U.MAGMA_SEA})


@dataclass
class DeepTally:
    layers: int = 0
    veins: int = 0
    strata: int = 0
    fires: int = 0
    tapped: int = 0


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


async def reach_stratum(ctx: TickContext, ground: RegionEnvironmentRow, row: RegionStratumRow, tally: DeepTally) -> None:
    row.reached_epoch = ctx.epoch
    tally.strata += 1
    await record(ctx, "deep.stratum_reached", roles={IncidentRole.PLACE: ground.entity_id}, facts={"stratum": row.stratum}, place=ground.entity_id)
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
    await record(ctx, "deep.stratum_breached", roles={IncidentRole.PLACE: ground.entity_id}, facts={"stratum": row.stratum}, place=ground.entity_id)


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


async def deepen(ctx: TickContext) -> DeepTally:
    tally = DeepTally()
    columns = await columns_by_region(ctx.session)
    strata = await strata_by_region(ctx.session)
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
