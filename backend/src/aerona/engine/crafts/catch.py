from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import CatchGroundRow
from aerona.domain.enums.crafts import CatchGround, Gear
from aerona.engine.climes.shifts import upwelling
from aerona.engine.couplings.closures import closure_factor
from aerona.rules.registry import Rules

LAND_GROUNDS = frozenset({CatchGround.TRAPPING, CatchGround.FOWLING})


def gear_pct(rules: Rules, gear: Gear) -> int:
    table = rules.grounds
    return {
        Gear.LINES: table.lines_pct,
        Gear.NETS: table.nets_pct,
        Gear.WEIRS: table.weirs_pct,
        Gear.TRAPS: table.traps_pct,
        Gear.SNARES: table.snares_pct,
        Gear.HARPOONS: table.harpoons_pct,
    }[gear]


def worked(rules: Rules, row: CatchGroundRow) -> float:
    if row.collapsed:
        return 0.0
    effort = 0.5 + row.effort / PERCENT * rules.grounds.effort_pct / PERCENT
    return gear_pct(rules, row.gear) / PERCENT * effort


async def catch_factor(session: AsyncSession, rules: Rules, source_id: int) -> float:
    rows = list(await session.scalars(select(CatchGroundRow).where(CatchGroundRow.source_entity_id == source_id)))
    if not rows:
        return 1.0
    return worked(rules, rows[0]) * await upwelling(session, rules, rows[0].region_entity_id) * await closure_factor(session, rules, rows[0])


async def regrowth_scale(session: AsyncSession, rules: Rules, source_id: int) -> float:
    rows = list(await session.scalars(select(CatchGroundRow).where(CatchGroundRow.source_entity_id == source_id, CatchGroundRow.collapsed.is_(True))))
    return rules.grounds.collapsed_regrowth_pct / PERCENT if rows else 1.0


async def trap_factors(session: AsyncSession, rules: Rules) -> dict[tuple[int, int], float]:
    rows = await session.scalars(select(CatchGroundRow).where(CatchGroundRow.ground.in_(LAND_GROUNDS)))
    return {(row.source_entity_id, row.region_entity_id): worked(rules, row) for row in rows}
