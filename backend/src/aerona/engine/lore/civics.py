from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.techniques import TECHNIQUES
from aerona.db.tables.polity import PolityProfileRow
from aerona.domain.enums.culture import Technique
from aerona.engine.lore.research import has_technique
from aerona.engine.polity.book import Realm


async def holders_know(session: AsyncSession, holder_ids: list[int], technique: Technique | None) -> bool:
    if technique is None:
        return True
    for holder in holder_ids:
        if await has_technique(session, holder, technique):
            return True
    return False


async def polity_allows(session: AsyncSession, polity_id: int, technique: Technique | None) -> bool:
    profile = await session.get(PolityProfileRow, polity_id)
    holders = [polity_id, *([profile.core_entity_id] if profile is not None and profile.core_entity_id is not None else [])]
    return await holders_know(session, holders, technique)


def unlearned(technique: Technique | None) -> str:
    return TECHNIQUES[technique].label.lower() if technique is not None else ""


async def realm_allows(session: AsyncSession, realm: Realm, technique: Technique | None) -> bool:
    holders = [realm.entity.id, *([realm.profile.core_entity_id] if realm.profile.core_entity_id is not None else [])]
    return await holders_know(session, holders, technique)
