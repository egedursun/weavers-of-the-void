from itertools import permutations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.gatherings import TITLE_ROLES
from aerona.core.grammar import spoken
from aerona.db.tables.gatherings import CollectionMemberRow, CollectionPlaceRow, CollectionRow
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.engine.history.collections import names_of, title_text

NAME_LOCK = "name"


def one_standing(kind: CollectionKind, first: CollectionRole, second: CollectionRole) -> bool:
    return any(first in roles and second in roles for roles in TITLE_ROLES[kind])


def mixed_titles(kind: CollectionKind, members: dict[int, CollectionRole], names: dict[int, str]) -> dict[str, dict[int, CollectionRole]]:
    label = spoken(kind).capitalize()
    named = [node for node in members if node in names and members[node] is not CollectionRole.WITNESS and members[node] is not CollectionRole.PLACE]
    return {
        f"{label} of {names[first]} and {names[second]}": {first: members[first], second: members[second]}
        for first, second in permutations(named, 2)
        if not one_standing(kind, members[first], members[second])
    }


async def collection_parts(session: AsyncSession, row: CollectionRow) -> tuple[dict[int, CollectionRole], list[int]]:
    joined = select(CollectionMemberRow).where(CollectionMemberRow.collection_id == row.id)
    members = {member.node_id: member.role for member in await session.scalars(joined.order_by(CollectionMemberRow.since_epoch, CollectionMemberRow.node_id))}
    places = list(
        await session.scalars(
            select(CollectionPlaceRow.place_entity_id).where(CollectionPlaceRow.collection_id == row.id).order_by(CollectionPlaceRow.place_entity_id)
        )
    )
    return members, places


async def proper_title(session: AsyncSession, row: CollectionRow) -> str | None:
    if NAME_LOCK in (row.locked or []):
        return None
    members, places = await collection_parts(session, row)
    names = await names_of(session, [*members, *places])
    named = mixed_titles(row.kind, members, names).get(row.name)
    if named is None:
        return None
    title = title_text(row.kind, named, places, names)
    return title if title != row.name else None


async def mixed_collection_titles(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(CollectionRow).where(CollectionRow.name.contains(" and ")).order_by(CollectionRow.id)):
        if await proper_title(session, row) is not None:
            found.append(row.id)
    return found


async def retitle_collection(session: AsyncSession, collection_id: int) -> None:
    row = await session.get(CollectionRow, collection_id)
    if row is None:
        return
    title = await proper_title(session, row)
    if title is not None:
        row.name = title
