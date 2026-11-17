from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.powers import PowerRegistryRow, PowerRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.powers import PowerState
from aerona.engine.context import TickContext
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

BREACHING = frozenset({SpellForm.FORCE, SpellForm.EARTH, SpellForm.SPACE})
DEFAULT_STRENGTH = 3


async def unit_share(session: AsyncSession, army_ids: list[int], kind: UnitKind) -> float:
    if not army_ids:
        return 0.0
    rows = (
        await session.execute(select(ArmyUnitRow.kind, func.sum(ArmyUnitRow.count)).where(ArmyUnitRow.army_entity_id.in_(army_ids)).group_by(ArmyUnitRow.kind))
    ).all()
    total = sum(int(count or 0) for _, count in rows)
    found = sum(int(count or 0) for unit, count in rows if unit is kind)
    return found / total if total else 0.0


async def conscript_strength(session: AsyncSession, owner_id: int) -> float:
    drafted = select(PowerRegistryRow.holder_node_id).where(PowerRegistryRow.polity_entity_id == owner_id, PowerRegistryRow.conscripted.is_(True))
    mean = await session.scalar(select(func.avg(PowerRow.strength)).where(PowerRow.holder_node_id.in_(drafted), PowerRow.state == PowerState.ACTIVE))
    return float(mean) if mean is not None else DEFAULT_STRENGTH


async def power_edge(session: AsyncSession, rules: Rules, owner_id: int, army_ids: list[int], foe_army_ids: list[int]) -> float:
    gifted = await unit_share(session, army_ids, UnitKind.GIFTED)
    if not gifted:
        return 1.0
    damped = await unit_share(session, foe_army_ids, UnitKind.DAMPENERS) * rules.powers.dampener_pct / PERCENT
    lift = gifted * await conscript_strength(session, owner_id) * rules.powers.unit_strength_pct / PERCENT
    return 1 + lift * max(0.0, 1 - damped)


async def foe_armies(session: AsyncSession, war_id: int | None, owner_id: int) -> list[int]:
    if war_id is None:
        return []
    return list(await session.scalars(select(ArmyRow.entity_id).where(ArmyRow.war_id == war_id, ArmyRow.owner_entity_id != owner_id)))


async def field_gifted(ctx: TickContext, polity_id: int, kind: UnitKind, count: int) -> bool:
    army = await ctx.session.scalar(
        select(ArmyRow.entity_id).where(ArmyRow.owner_entity_id == polity_id, ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id).limit(1)
    )
    if army is None or held(army) or count <= 0:
        return False
    unit = await ctx.session.scalar(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army, ArmyUnitRow.kind == kind).limit(1))
    if unit is None:
        ctx.session.add(ArmyUnitRow(army_entity_id=army, kind=kind, count=count))
    elif "count" not in (unit.locked or []):
        unit.count = max(unit.count, count)
    return True


async def breach_by_power(ctx: TickContext, siege: SiegeRow) -> bool:
    drafted = select(PowerRegistryRow.holder_node_id).where(
        PowerRegistryRow.polity_entity_id == siege.besieger_entity_id, PowerRegistryRow.conscripted.is_(True)
    )
    strong = await ctx.session.scalar(
        select(PowerRow.id)
        .where(
            PowerRow.holder_node_id.in_(drafted),
            PowerRow.state == PowerState.ACTIVE,
            PowerRow.form.in_(list(BREACHING)),
            PowerRow.strength >= ctx.rules.powers.siege_breach,
        )
        .limit(1)
    )
    if strong is None or "breaches" in siege.locked:
        return False
    siege.breaches += 1
    await record(ctx, "power.breach", roles={IncidentRole.SUBJECT: siege.besieged_entity_id})
    return True
