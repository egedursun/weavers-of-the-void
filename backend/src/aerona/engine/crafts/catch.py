from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.catch import GEAR, grounds_in
from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import CatchGroundRow
from aerona.domain.enums.crafts import CatchMedium, Gear
from aerona.domain.enums.ecology import AnimalRole
from aerona.engine.climes.shifts import upwelling
from aerona.engine.couplings.closures import closure_factor
from aerona.engine.ecology.domestication import heads_kept_for
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules

LAND_GROUNDS = grounds_in(CatchMedium.LAND)


def gear_pct(rules: Rules, gear: Gear) -> int:
    return GEAR[gear].rate(rules)


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
    rows = list(await session.scalars(select(CatchGroundRow).where(CatchGroundRow.source_entity_id == source_id).order_by(CatchGroundRow.region_entity_id)))
    if not rows:
        return 1.0
    pressed = 1 - GEAR[rows[0].gear].depletion(rules) / PERCENT / 2
    return pressed * (rules.grounds.collapsed_regrowth_pct / PERCENT if any(row.collapsed for row in rows) else 1.0)


async def trap_factors(session: AsyncSession, rules: Rules) -> dict[tuple[int, int], float]:
    rows = await session.scalars(select(CatchGroundRow).where(CatchGroundRow.ground.in_(LAND_GROUNDS)))
    hounds = await heads_kept_for(session, AnimalRole.HUNTING)
    atlas = await RegionAtlas.load(session)
    found: dict[tuple[int, int], float] = {}
    for row in rows:
        kept = any(hounds.get(town, 0) > 0 for town in atlas.communities_in(row.region_entity_id))
        hounded = 1 + rules.species_roles.hunting_catch_pct / PERCENT if kept and GEAR[row.gear].needs_animals else 1.0
        found[row.source_entity_id, row.region_entity_id] = worked(rules, row) * hounded if kept or not GEAR[row.gear].needs_animals else 0.0
    return found
