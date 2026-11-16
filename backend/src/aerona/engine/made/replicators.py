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
from aerona.domain.enums.made import ReplicatorOutput, ReplicatorScale, ReplicatorStage
from aerona.domain.enums.minds import MindAffect, MindOrigin, MindSeat
from aerona.domain.models.entity_stats import PhenomenonStats
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.minds.profiles import law_lets_will_grow, law_of, profile_of
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.structures.construction import material_commodity

DONE = frozenset({ReplicatorStage.STOPPED, ReplicatorStage.EXTINCT})
LOOSE = frozenset({ReplicatorStage.SPREADING, ReplicatorStage.RUNAWAY})
SWARM_POWER = 4
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


async def far_land(ctx: TickContext, line: ReplicatorLineRow, presence: ReplicatorPresenceRow, towns: dict[int, list[EntityRow]], here: set[int]) -> int | None:
    if line.scale is not ReplicatorScale.VESSEL or not ctx.rng(f"replicator.voyage.{line.id}.{ctx.epoch}").chance(ctx.rules.replicators.vessel_reach_chance):
        return None
    home = await ctx.session.get(EntityRow, presence.place_node_id)
    for region in sorted(towns):
        place = await ctx.session.get(EntityRow, region)
        if region not in here and not held(region) and place is not None and home is not None and place.world_id != home.world_id:
            return region
    return None


async def spread(
    ctx: TickContext, atlas: RegionAtlas, line: ReplicatorLineRow, presence: ReplicatorPresenceRow, *, here: set[int], towns: dict[int, list[EntityRow]]
) -> int:
    seeded = 0
    far = await far_land(ctx, line, presence, towns, here)
    if far is not None:
        ctx.session.add(ReplicatorPresenceRow(line_id=line.id, place_node_id=far, mass=presence.mass // 4, growth=presence.growth, locked=[]))
        here.add(far)
        presence.mass -= presence.mass // 4
        if "owner_node_id" not in line.locked:
            line.owner_node_id = None
        await note(ctx, f"{line.name} crossed to another world and slipped its makers' hands.", key="replicator.voyage", ids=[far])
        return 1
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


async def drift_line(ctx: TickContext, line: ReplicatorLineRow, presences: list[ReplicatorPresenceRow]) -> ReplicatorLineRow | None:
    table = ctx.rules.replicators
    rng = ctx.rng(f"replicator.drift.{line.id}.{ctx.epoch}")
    movable = [row for row in presences if "line_id" not in row.locked and not held(row.place_node_id)]
    if len(movable) < 2 or not rng.chance(line.error_pct) or not rng.chance(table.drift_line_chance):
        return None
    child = ReplicatorLineRow(
        name=f"{line.name}, drifted",
        scale=line.scale,
        feedstock=line.feedstock,
        output=rng.pick(list(ReplicatorOutput)),
        growth_pct=line.growth_pct,
        error_pct=line.error_pct,
        set_id=line.set_id,
        containment=clamp_percent(line.containment - table.drift_containment),
        kill_switch=line.kill_switch and rng.chance(PERCENT // 2),
        owner_node_id=line.owner_node_id,
        maker_node_id=line.maker_node_id,
        mind_node_id=None,
        stage=ReplicatorStage.WORKING if line.stage is ReplicatorStage.CONTAINED else line.stage,
        drifted_from_id=line.id,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(child)
    await ctx.session.flush()
    movable[-1].line_id = child.id
    await note(ctx, f"A copy error in {line.name} began a line of its own.", key="replicator.drifted", ids=[movable[-1].place_node_id])
    return child


async def wake_swarm(ctx: TickContext, line: ReplicatorLineRow, presences: list[ReplicatorPresenceRow]) -> EntityRow | None:
    table = ctx.rules.replicators
    if line.mind_node_id is not None or "mind_node_id" in line.locked or not presences or sum(row.mass for row in presences) < table.wake_mass:
        return None
    land = await ctx.session.get(EntityRow, presences[0].place_node_id)
    if land is None or not law_lets_will_grow(await law_of(ctx.session, land.world_id)):
        return None
    rng = ctx.rng(f"replicator.wake.{line.id}.{ctx.epoch}")
    if not rng.chance(table.wake_chance):
        return None
    swarm = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.PHENOMENON,
            name=f"the mind of {line.name}",
            body=f"{line.name} woke as one mind across its many bodies.",
            stats=PhenomenonStats(),
            power=SWARM_POWER,
            location_id=land.id,
            world_id=land.world_id,
        ),
    )
    mind = await profile_of(ctx.session, ctx.rules, swarm.id, ctx.epoch)
    mind.seat, mind.seat_node_id, mind.origin, mind.will = MindSeat.BODIES, swarm.id, MindOrigin.AWAKENED, MindWill.EMERGENT
    mind.affect, mind.capacity = (
        rng.pick(list(MindAffect)),
        clamp_percent(sum(row.mass for row in presences) // table.wake_mass * ctx.rules.minds.baseline_capacity),
    )
    line.mind_node_id = swarm.id
    await note(ctx, f"{line.name} woke as one mind across its many bodies.", key="replicator.woke", ids=[swarm.id])
    return swarm


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
            await spread(ctx, atlas, line, presence, here=here, towns=towns)
    await drift_line(ctx, line, presences)
    await wake_swarm(ctx, line, presences)
    if presences and all(row.mass <= 0 for row in presences) and "stage" not in line.locked:
        line.stage = ReplicatorStage.EXTINCT
        await note(ctx, f"{line.name} died out.", key="replicator.extinct", ids=[])


@reads("table.community_stocks", "table.entities", "table.mind_profiles", "table.replicator_lines", "table.replicator_presences")
@writes("table.community_stocks", "table.entities", "table.mind_profiles", "table.replicator_lines", "table.replicator_presences", "table.settlement_profiles")
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
