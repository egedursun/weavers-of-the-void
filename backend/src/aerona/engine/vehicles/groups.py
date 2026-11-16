from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.vehicles import VehicleGroupRow, VehicleGroupSectionRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import DesignComponentKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.vehicles import VehicleDomain, VehicleStatus
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.vehicles.sections import function_share, group_sections

C = DesignComponentKind
LIFTED = frozenset({VehicleDomain.AIR, VehicleDomain.GAS_GIANT})


@dataclass(frozen=True)
class GroupReading:
    group: VehicleGroupRow
    design: DesignRow
    firepower: float
    armour: int
    pace: int
    troops: int
    cargo: int
    crew_needed: int


async def groups_of(session: AsyncSession, holder_id: int) -> list[VehicleGroupRow]:
    statement = select(VehicleGroupRow).where(VehicleGroupRow.holder_node_id == holder_id, VehicleGroupRow.count > 0)
    return list(await session.scalars(statement.order_by(VehicleGroupRow.id)))


async def read(session: AsyncSession, group: VehicleGroupRow) -> GroupReading | None:
    design = await session.get(DesignRow, group.design_id)
    if design is None or group.count <= 0 or group.status is VehicleStatus.BUILDING:
        return None
    crewed = min(1.0, group.crewed / group.count) if group.count else 0.0
    weapons = await function_share(session, group, C.WEAPON)
    moving = await function_share(session, group, C.PROPULSION) * await function_share(session, group, C.STEERING)
    if design.domain in LIFTED:
        moving *= await function_share(session, group, C.LIFT)
    condition = 0.5 + group.condition / (2 * PERCENT)
    return GroupReading(
        group=group,
        design=design,
        firepower=design.armament * group.count * crewed * weapons * condition,
        armour=clamp_int(round_half_up(design.armour * await function_share(session, group, C.ARMOUR)), 0, PERCENT),
        pace=round_half_up(design.speed * moving),
        troops=round_half_up(design.troops * group.count * await function_share(session, group, C.TROOPS)),
        cargo=round_half_up(design.cargo * group.count * await function_share(session, group, C.HOLD)),
        crew_needed=design.crew * group.count,
    )


async def add_vehicles(
    session: AsyncSession,
    holder_id: int,
    design: DesignRow,
    count: int,
    *,
    epoch: int,
    crewed: int = 0,
    region_id: int | None = None,
    building: bool = False,
) -> VehicleGroupRow | None:
    if count <= 0 or held(holder_id):
        return None
    statement = select(VehicleGroupRow).where(
        VehicleGroupRow.holder_node_id == holder_id, VehicleGroupRow.design_id == design.id, VehicleGroupRow.status != VehicleStatus.WRECKED
    )
    group = await session.scalar(statement.order_by(VehicleGroupRow.id).limit(1))
    if group is None:
        group = VehicleGroupRow(
            holder_node_id=holder_id,
            design_id=design.id,
            count=0,
            crewed=0,
            condition=PERCENT,
            fuel=0,
            status=VehicleStatus.BUILDING if building else VehicleStatus.READY,
            region_entity_id=region_id,
            built_epoch=epoch,
            locked=[],
        )
        session.add(group)
        await session.flush()
    if "count" in (group.locked or []):
        return group
    group.count += count
    group.crewed = min(group.count, group.crewed + crewed)
    return group


async def move_vehicles(session: AsyncSession, source: VehicleGroupRow, holder_id: int, count: int, *, epoch: int) -> int:
    if count <= 0 or held(source.holder_node_id) or held(holder_id) or "count" in (source.locked or []):
        return 0
    design = await session.get(DesignRow, source.design_id)
    if design is None:
        return 0
    states = await group_sections(session, source.id)
    worst = max((row.damaged + row.disabled + row.destroyed for row in states.values()), default=0)
    sound = max(0, source.count - worst)
    moved = min(count, sound)
    if moved <= 0:
        return 0
    source.count -= moved
    source.crewed = min(source.crewed, source.count)
    await add_vehicles(session, holder_id, design, moved, epoch=epoch, region_id=source.region_entity_id)
    return moved


async def repair_group(session: AsyncSession, group: VehicleGroupRow, points: int, *, yard: bool) -> int:
    if points <= 0 or held(group.holder_node_id):
        return 0
    mended = 0
    for row in (await group_sections(session, group.id)).values():
        if set(row.locked or []) & {"damaged", "disabled", "destroyed"}:
            continue
        mended += mend_states(row, points, yard=yard)
    if "condition" not in (group.locked or []):
        group.condition = clamp_int(group.condition + points, 0, PERCENT)
    return mended


def mend_states(row: VehicleGroupSectionRow, points: int, *, yard: bool) -> int:
    budget = points
    cured = min(row.damaged, budget)
    row.damaged -= cured
    budget -= cured
    lifted = min(row.disabled, budget // 2)
    row.disabled -= lifted
    row.damaged += lifted
    budget -= lifted * 2
    rebuilt = min(row.destroyed, budget // 3) if yard else 0
    row.destroyed -= rebuilt
    row.disabled += rebuilt
    return cured + lifted + rebuilt


async def burn_fuel(ctx: TickContext, group: VehicleGroupRow, payer_id: int) -> bool:
    design = await ctx.session.get(DesignRow, group.design_id)
    if design is None or design.fuel is None or design.fuel_use <= 0 or group.count <= 0:
        return True
    if held(group.holder_node_id) or "fuel" in (group.locked or []):
        return group.fuel > 0
    need = design.fuel_use * group.count
    if group.fuel < need:
        group.fuel += await goods_of(ctx.session, ctx.epoch).take_units(payer_id, design.fuel, need - group.fuel, GoodsFlow.CONSUMPTION)
    if group.fuel < need:
        if "status" not in (group.locked or []):
            group.status = VehicleStatus.LAID_UP
        return False
    group.fuel -= need
    return True


async def salvage(ctx: TickContext, group: VehicleGroupRow, lost: int, taker_id: int | None) -> int:
    if lost <= 0 or taker_id is None or held(taker_id):
        return 0
    design = await ctx.session.get(DesignRow, group.design_id)
    if design is None:
        return 0
    amount = round_half_up(lost * design.structure * ctx.rules.vehicles.salvage_pct / PERCENT)
    commodity = CommodityKind.TIMBER if design.domain in {VehicleDomain.WATER, VehicleDomain.LAND} and design.tech_level <= 2 else CommodityKind.ORE
    return await goods_of(ctx.session, ctx.epoch).add(taker_id, commodity, amount, GoodsFlow.LOOT)


async def take_prizes(ctx: TickContext, group: VehicleGroupRow, taker_id: int | None) -> int:
    if taker_id is None or held(taker_id) or held(group.holder_node_id) or "count" in (group.locked or []):
        return 0
    states = await group_sections(ctx.session, group.id)
    crippled = max((row.disabled for row in states.values()), default=0)
    taken = round_half_up(min(crippled, group.count) * ctx.rules.vehicles.prize_pct / PERCENT)
    if taken <= 0:
        return 0
    design = await ctx.session.get(DesignRow, group.design_id)
    if design is None:
        return 0
    group.count -= taken
    group.crewed = min(group.crewed, group.count)
    for row in states.values():
        row.disabled = max(0, row.disabled - taken)
    await add_vehicles(ctx.session, taker_id, design, taken, epoch=ctx.epoch, region_id=group.region_entity_id)
    return taken
