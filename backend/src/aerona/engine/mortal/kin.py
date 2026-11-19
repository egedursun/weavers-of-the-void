from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.bond_index import bond_lookup
from aerona.db.tables.bonds import BondRow
from aerona.domain.enums.bond import BondKind, BondState

KIN_STATES = (BondState.ACTIVE, BondState.PAST)


async def _ends(session: AsyncSession, kind: BondKind, *, source: int | None = None, target: int | None = None, past: bool = False) -> list[int]:
    states = list(KIN_STATES) if past else [BondState.ACTIVE]
    lookup = await bond_lookup(session)
    if lookup is not None:
        rows = lookup.select([kind], states, [source] if source is not None else None, [target] if target is not None else None)
    else:
        statement = select(BondRow).where(BondRow.kind == kind, BondRow.state.in_(states))
        if source is not None:
            statement = statement.where(BondRow.source_node_id == source)
        if target is not None:
            statement = statement.where(BondRow.target_node_id == target)
        rows = list(await session.scalars(statement.order_by(BondRow.id)))
    return [row.target_node_id if source is not None else row.source_node_id for row in rows]


async def parents_of(session: AsyncSession, mortal_id: int) -> list[int]:
    return await _ends(session, BondKind.PARENT_OF, target=mortal_id, past=True)


async def children_of(session: AsyncSession, mortal_id: int) -> list[int]:
    return await _ends(session, BondKind.PARENT_OF, source=mortal_id, past=True)


async def _either(session: AsyncSession, kind: BondKind, mortal_id: int, *, past: bool = False) -> list[int]:
    found = [*await _ends(session, kind, source=mortal_id, past=past), *await _ends(session, kind, target=mortal_id, past=past)]
    return list(dict.fromkeys(found))


async def spouses_of(session: AsyncSession, mortal_id: int, *, past: bool = False) -> list[int]:
    return await _either(session, BondKind.SPOUSE_OF, mortal_id, past=past)


async def partners_of(session: AsyncSession, mortal_id: int) -> list[int]:
    found = [*await spouses_of(session, mortal_id), *await _either(session, BondKind.CONCUBINE_OF, mortal_id)]
    return list(dict.fromkeys(found))


async def betrothed_of(session: AsyncSession, mortal_id: int) -> list[int]:
    return await _either(session, BondKind.BETROTHED_TO, mortal_id)


async def sworn_kin_of(session: AsyncSession, mortal_id: int) -> list[int]:
    return await _either(session, BondKind.SWORN_KIN, mortal_id)


async def godparents_of(session: AsyncSession, mortal_id: int) -> list[int]:
    return await _ends(session, BondKind.GODPARENT_OF, target=mortal_id)


async def godchildren_of(session: AsyncSession, mortal_id: int) -> list[int]:
    return await _ends(session, BondKind.GODPARENT_OF, source=mortal_id)


async def fosterers_of(session: AsyncSession, mortal_id: int) -> list[int]:
    return await _ends(session, BondKind.FOSTERED_BY, source=mortal_id, past=True)


async def fosterlings_of(session: AsyncSession, mortal_id: int) -> list[int]:
    return await _ends(session, BondKind.FOSTERED_BY, target=mortal_id, past=True)


async def siblings_of(session: AsyncSession, mortal_id: int) -> list[int]:
    found: list[int] = []
    for parent in await parents_of(session, mortal_id):
        found.extend(child for child in await children_of(session, parent) if child != mortal_id)
    return list(dict.fromkeys(found))


async def close_kin_of(session: AsyncSession, mortal_id: int) -> list[int]:
    found = [
        *await parents_of(session, mortal_id),
        *await children_of(session, mortal_id),
        *await spouses_of(session, mortal_id),
        *await siblings_of(session, mortal_id),
        *await fosterers_of(session, mortal_id),
        *await fosterlings_of(session, mortal_id),
        *await sworn_kin_of(session, mortal_id),
    ]
    return [node for node in dict.fromkeys(found) if node != mortal_id]
