from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.urban import CrimeStanceRow
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.urban import CrimeStance
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.services.war import ongoing_wars


async def privateers_against(session: AsyncSession, owner_id: int | None) -> bool:
    realm = await realm_of_community(session, owner_id) if owner_id is not None else None
    if realm is None:
        return False
    foes = {side for war in await ongoing_wars(session, realm) for side in war.sides if side != realm}
    if not foes:
        return False
    privateers = await session.scalar(
        select(CrimeStanceRow.polity_entity_id)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == CrimeStanceRow.faction_entity_id)
        .where(CrimeStanceRow.stance == CrimeStance.CO_OPT, CrimeStanceRow.polity_entity_id.in_(foes), FactionProfileRow.kind == FactionKind.PIRATE_CONFEDERACY)
        .limit(1)
    )
    return privateers is not None
