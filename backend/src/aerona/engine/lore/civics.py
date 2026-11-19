from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.techniques import TECHNIQUES
from aerona.db.tables.polity import PolityProfileRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.lore.research import has_technique
from aerona.engine.polity.book import Realm
from aerona.engine.primitives.knowledge import BranchLevels, known_levels


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


def realm_holders(realm: Realm) -> list[int]:
    return [realm.entity.id, *([realm.profile.core_entity_id] if realm.profile.core_entity_id is not None else [])]


async def realm_levels(session: AsyncSession, realm: Realm) -> dict[int, BranchLevels]:
    return await known_levels(session, realm_holders(realm))


def reaches(levels: dict[int, BranchLevels] | None, realm: Realm, gate: tuple[KnowledgeBranch, int] | None) -> bool:
    if gate is None:
        return True
    branch, level = gate
    return any((levels or {}).get(holder, {}).get(branch, 0) >= level for holder in realm_holders(realm))


def unlearned(technique: Technique | None) -> str:
    return TECHNIQUES[technique].label.lower() if technique is not None else ""


async def realm_allows(session: AsyncSession, realm: Realm, technique: Technique | None) -> bool:
    return await holders_know(session, realm_holders(realm), technique)
