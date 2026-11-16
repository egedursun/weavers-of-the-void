from collections import defaultdict

from sqlalchemy import select

from aerona.catalog.materials import MATERIALS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import ReplicatorLineRow, ReplicatorPresenceRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.made import ReplicatorOutput, ReplicatorStage
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.minds.profiles import profile_of
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.structures.construction import material_commodity

DONE = frozenset({ReplicatorStage.STOPPED, ReplicatorStage.EXTINCT})
LOOSE = frozenset({ReplicatorStage.SPREADING, ReplicatorStage.RUNAWAY})
OUTPUT_GOODS = {ReplicatorOutput.GOODS: CommodityKind.TOOLS, ReplicatorOutput.MEDICINE: CommodityKind.MEDICINE}


def stage_of(rules_spread: int, rules_runaway: int, containment: int) -> ReplicatorStage:
    if containment < rules_runaway:
        return ReplicatorStage.RUNAWAY
    if containment < rules_spread:
        return ReplicatorStage.SPREADING
    return ReplicatorStage.WORKING


async def towns_by_region(ctx: TickContext, atlas: RegionAtlas) -> dict[int, list[EntityRow]]:
    found: dict[int, list[EntityRow]] = defaultdict(list)
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in towns:
        region = atlas.top_region(town.id)
        if region is not None:
            found[region].append(town)
    return found


async def feed(ctx: TickContext, line: ReplicatorLineRow, towns: list[EntityRow], wanted: int) -> int:
    commodity = material_commodity(MATERIALS[line.feedstock].family)
    eaten = 0
    ledger = goods_of(ctx.session, ctx.epoch)
    for town in towns:
        if eaten >= wanted:
            break
        eaten += await ledger.take_units(town.id, commodity, wanted - eaten, GoodsFlow.INPUT)
    return eaten


async def yield_to(ctx: TickContext, line: ReplicatorLineRow, presence: ReplicatorPresenceRow, towns: list[EntityRow]) -> None:
    table = ctx.rules.replicators
    for town in towns:
        if held(town.id):
            continue
        if line.stage is ReplicatorStage.RUNAWAY or line.output is ReplicatorOutput.DISASSEMBLY:
            shift_stat(town, "prosperity", -table.runaway_harm, 0)
        elif line.output is ReplicatorOutput.REPAIR:
            shift_stat(town, "prosperity", table.repair_yield, 0, high=PERCENT)
        elif line.output is ReplicatorOutput.STRUCTURES:
            profile = await ctx.session.get(SettlementProfileRow, town.id)
            if profile is not None:
                profile.construction_capacity += table.repair_yield
        elif line.output in OUTPUT_GOODS:
            units = round_half_up(table.goods_yield * presence.mass * presence.growth / PERCENT / PERCENT)
            await goods_of(ctx.session, ctx.epoch).add(town.id, OUTPUT_GOODS[line.output], units, GoodsFlow.PRODUCTION)
        elif line.output is ReplicatorOutput.TERRAFORMING:
            shift_stat(town, "prosperity", table.repair_yield // 2, 0, high=PERCENT)


async def spread(ctx: TickContext, atlas: RegionAtlas, line: ReplicatorLineRow, presence: ReplicatorPresenceRow, here: set[int]) -> int:
    seeded = 0
    for region in atlas.neighbours(presence.place_node_id):
        if region in here or held(region):
            continue
        ctx.session.add(ReplicatorPresenceRow(line_id=line.id, place_node_id=region, mass=presence.mass // 4, growth=presence.growth, locked=[]))
        here.add(region)
        seeded += 1
        break
    if seeded:
        presence.mass -= presence.mass // 4
        await note(ctx, f"{line.name} spread into a neighbouring land.", key="replicator.spread", ids=[presence.place_node_id])
    return seeded


async def stop_runaway(ctx: TickContext, line: ReplicatorLineRow) -> bool:
    if not line.kill_switch or line.stage is not ReplicatorStage.RUNAWAY:
        return False
    if line.mind_node_id is not None and (await profile_of(ctx.session, ctx.rules, line.mind_node_id, ctx.epoch)).will is MindWill.EXCEEDING:
        return False
    line.stage = ReplicatorStage.STOPPED
    await note(ctx, f"{line.name} was stopped by its kill switch.", key="replicator.stopped", ids=[])
    return True


async def run_line(ctx: TickContext, atlas: RegionAtlas, towns: dict[int, list[EntityRow]], line: ReplicatorLineRow) -> None:
    table = ctx.rules.replicators
    if ctx.rng(f"replicator.error.{line.id}.{ctx.epoch}").chance(line.error_pct) and "containment" not in line.locked:
        line.containment = clamp_percent(line.containment - table.drift_containment)
    if "stage" not in line.locked and line.stage is not ReplicatorStage.CONTAINED:
        line.stage = stage_of(table.spread_containment, table.runaway_containment, line.containment)
    if await stop_runaway(ctx, line):
        return
    presences = list(
        await ctx.session.scalars(select(ReplicatorPresenceRow).where(ReplicatorPresenceRow.line_id == line.id).order_by(ReplicatorPresenceRow.id))
    )
    here = {row.place_node_id for row in presences}
    for presence in presences:
        local = towns.get(presence.place_node_id, [])
        if held(presence.place_node_id) or "mass" in presence.locked:
            continue
        wanted = round_half_up(presence.mass * line.growth_pct * presence.growth / PERCENT / PERCENT)
        eaten = await feed(ctx, line, local, wanted * table.feedstock_per_mass) if wanted else 0
        presence.mass = max(0, presence.mass + (eaten // max(1, table.feedstock_per_mass)) - (0 if eaten else max(1, presence.mass // 20)))
        await yield_to(ctx, line, presence, local)
        if line.stage in LOOSE and presence.mass >= table.spread_mass:
            await spread(ctx, atlas, line, presence, here)
    if presences and all(row.mass <= 0 for row in presences) and "stage" not in line.locked:
        line.stage = ReplicatorStage.EXTINCT
        await note(ctx, f"{line.name} died out.", key="replicator.extinct", ids=[])


@reads("table.community_stocks", "table.entities", "table.mind_profiles", "table.replicator_lines", "table.replicator_presences")
@writes("table.community_stocks", "table.entities", "table.replicator_lines", "table.replicator_presences", "table.settlement_profiles")
async def run_replicators(ctx: TickContext) -> None:
    lines = list(await ctx.session.scalars(select(ReplicatorLineRow).where(ReplicatorLineRow.stage.not_in(list(DONE))).order_by(ReplicatorLineRow.id)))
    if not lines:
        return
    atlas = await RegionAtlas.load(ctx.session)
    towns = await towns_by_region(ctx, atlas)
    for line in lines:
        if line.owner_node_id is not None and held(line.owner_node_id):
            continue
        await run_line(ctx, atlas, towns, line)
        ctx.count("replicator_lines_run")
    await ctx.session.flush()
