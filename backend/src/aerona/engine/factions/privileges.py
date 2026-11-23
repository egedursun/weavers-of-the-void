from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.estates import EstatePrivilegeRow, EstateProfileRow
from aerona.domain.enums.faction import EstatePrivilege
from aerona.domain.enums.society import SocialClass


async def reserved_class(session: AsyncSession, realm_id: int) -> SocialClass | None:
    found = await session.scalar(
        select(EstateProfileRow.social_class)
        .join(EstatePrivilegeRow, EstatePrivilegeRow.estate_entity_id == EstateProfileRow.faction_entity_id)
        .where(EstateProfileRow.polity_entity_id == realm_id, EstatePrivilegeRow.privilege == EstatePrivilege.RESERVED_OFFICES)
        .order_by(EstateProfileRow.faction_entity_id)
        .limit(1)
    )
    return SocialClass(found) if found is not None else None


async def landed_class(session: AsyncSession, realm_id: int) -> SocialClass | None:
    found = await session.scalar(
        select(EstateProfileRow.social_class)
        .join(EstatePrivilegeRow, EstatePrivilegeRow.estate_entity_id == EstateProfileRow.faction_entity_id)
        .where(EstateProfileRow.polity_entity_id == realm_id, EstatePrivilegeRow.privilege == EstatePrivilege.LAND_HOLDING)
        .order_by(EstateProfileRow.faction_entity_id)
        .limit(1)
    )
    return SocialClass(found) if found is not None else None
