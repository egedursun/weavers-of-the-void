from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.city_rules import ConurbationRow, LandUseRuleRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.entity import EntityType


async def stray_rules(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(LandUseRuleRow).where(LandUseRuleRow.district_id.is_not(None)).order_by(LandUseRuleRow.id)):
        district = await session.get(DistrictRow, row.district_id)
        if district is None or district.settlement_entity_id != row.settlement_entity_id:
            found.append(row.id)
    return found


async def widen_rule(session: AsyncSession, key: int) -> None:
    row = await session.get(LandUseRuleRow, key)
    if row is not None:
        row.district_id = None


async def fitting_members(session: AsyncSession, row: ConurbationRow) -> list[int]:
    core = await session.get(EntityRow, row.core_entity_id)
    kept: list[int] = []
    for member in row.members or []:
        town = await session.get(EntityRow, member)
        fits = town is not None and core is not None and town.entity_type is EntityType.SETTLEMENT and town.world_id == core.world_id
        if fits and member != row.core_entity_id and member not in kept:
            kept.append(member)
    return kept


async def odd_conurbations(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(ConurbationRow).where(ConurbationRow.split_epoch.is_(None)).order_by(ConurbationRow.id))
    return [row.id for row in rows if await fitting_members(session, row) != list(row.members or []) or not row.members]


async def mend_conurbation(session: AsyncSession, key: int) -> None:
    row = await session.get(ConurbationRow, key)
    if row is None:
        return
    row.members = await fitting_members(session, row)
    if not row.members:
        row.split_epoch = row.joined_epoch
