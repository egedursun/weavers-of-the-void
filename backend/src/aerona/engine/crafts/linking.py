from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import MaterialAffinityRow, SympatheticLinkRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.crafts import AffinityMode, LinkToken
from aerona.domain.enums.culture import MagicSchool
from aerona.rules.registry import Rules


async def link_strength(session: AsyncSession, caster_id: int, target_id: int | None) -> int:
    if target_id is None:
        return 0
    found = await session.scalar(
        select(func.max(SympatheticLinkRow.strength)).where(SympatheticLinkRow.holder_node_id == caster_id, SympatheticLinkRow.target_node_id == target_id)
    )
    return int(found or 0)


async def true_named(session: AsyncSession, caster_id: int, target_id: int | None) -> bool:
    if target_id is None:
        return False
    found = await session.scalar(
        select(SympatheticLinkRow.id)
        .where(SympatheticLinkRow.holder_node_id == caster_id, SympatheticLinkRow.target_node_id == target_id, SympatheticLinkRow.token == LinkToken.TRUE_NAME)
        .limit(1)
    )
    return found is not None


async def link_boost(session: AsyncSession, rules: Rules, caster_id: int, target_id: int | None) -> float:
    return 1 + await link_strength(session, caster_id, target_id) * rules.sympathy.rite_pct / PERCENT / PERCENT


async def affinity_boost(session: AsyncSession, rules: Rules, region_id: int | None, school: MagicSchool, aptitude: float) -> float:
    if region_id is None:
        return 1.0
    rows = await session.execute(
        select(MaterialAffinityRow.power, MaterialAffinityRow.mode)
        .join(ResourceProfileRow, ResourceProfileRow.world_material_id == MaterialAffinityRow.material_id)
        .join(EntityRow, EntityRow.id == ResourceProfileRow.resource_entity_id)
        .where(EntityRow.location_id == region_id, MaterialAffinityRow.school == school)
    )
    table = rules.affinities
    best = 0.0
    for power, mode in rows:
        gift = 1 + aptitude * table.consumed_gift_pct / PERCENT if mode is AffinityMode.CONSUMED else 1.0
        best = max(best, power / PERCENT * table.rite_pct / PERCENT * gift)
    return 1 + best


async def affinity_value(session: AsyncSession, rules: Rules, material_id: int | None) -> float:
    if material_id is None:
        return 1.0
    power = await session.scalar(select(func.max(MaterialAffinityRow.power)).where(MaterialAffinityRow.material_id == material_id))
    return 1 + int(power or 0) * rules.affinities.mining_pct / PERCENT / PERCENT
