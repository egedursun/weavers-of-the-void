from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.entity import EntityType


async def signatories_of(session: AsyncSession, realm_id: int) -> list[int]:
    profile = await session.get(PolityProfileRow, realm_id)
    core = profile.core_entity_id if profile is not None else None
    return sorted({realm_id} | ({core} if core is not None else set()))


async def realm_of_party(session: AsyncSession, party_id: int) -> int | None:
    party = await session.get(EntityRow, party_id)
    if party is not None and party.entity_type is EntityType.POLITY:
        return party.id
    found: int | None = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == party_id).limit(1))
    return found
