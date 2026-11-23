from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.genetics import DWELLINGS
from aerona.db.tables.dwelling_kinds import DwellingKindRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.domain.enums.genetics import DwellingKind
from aerona.domain.enums.kinds import KindConcept, KindStance

HOUSED = (KindStance.MAKES, KindStance.USES, KindStance.FAVOURS)


BUILT_INS = "dwelling_built_ins"
CHOSEN = "dwelling_chosen"


async def built_ins(session: AsyncSession) -> dict[str, DwellingKindRow]:
    known = session.info.get(BUILT_INS)
    if known is None:
        rows = await session.scalars(select(DwellingKindRow).where(DwellingKindRow.built_in_key.is_not(None)))
        known = {row.built_in_key: row for row in rows if row.built_in_key is not None}
        session.info[BUILT_INS] = known
    return known


async def built_in_dwelling(session: AsyncSession, key: str) -> DwellingKindRow:
    known = await built_ins(session)
    found = known.get(key)
    if found is not None and found in session:
        return found
    found = await session.scalar(select(DwellingKindRow).where(DwellingKindRow.built_in_key == key))
    if found is not None:
        known[key] = found
        return found
    spec = DWELLINGS[DwellingKind(key)]
    row = DwellingKindRow(
        name=spec.label,
        category=spec.level,
        rooms=spec.rooms,
        quality=spec.quality,
        upkeep=spec.upkeep,
        mobile=int(spec.mobile),
        built_in=True,
        built_in_key=spec.key,
        created_epoch=0,
        retired=False,
        locked=[],
    )
    session.add(row)
    await session.flush()
    known[key] = row
    return row


async def ensure_built_in_dwellings(session: AsyncSession) -> int:
    known = set(await session.scalars(select(DwellingKindRow.built_in_key).where(DwellingKindRow.built_in_key.is_not(None))))
    missing = [key for key in DWELLINGS if key not in known]
    for key in missing:
        await built_in_dwelling(session, key)
    return len(missing)


async def dwelling_of_people(session: AsyncSession, people_id: int | None, key: str) -> DwellingKindRow:
    built = await built_in_dwelling(session, key)
    if people_id is None:
        return built
    chosen: dict[tuple[int, str], int] = session.info.setdefault(CHOSEN, {})
    cached = chosen.get((people_id, key))
    if cached is not None:
        row = await session.get(DwellingKindRow, cached)
        if row is not None:
            return row
    held = select(KindHoldingRow.kind_id).where(
        KindHoldingRow.concept == KindConcept.DWELLING, KindHoldingRow.holder_node_id == people_id, KindHoldingRow.stance.in_(HOUSED)
    )
    own = await session.scalar(
        select(DwellingKindRow)
        .where(DwellingKindRow.id.in_(held), DwellingKindRow.category == built.category, DwellingKindRow.retired.is_(False))
        .order_by(DwellingKindRow.built_in, DwellingKindRow.id)
        .limit(1)
    )
    picked = own or built
    chosen[(people_id, key)] = picked.id
    return picked


async def dwelling_kind_row(session: AsyncSession, kind_id: int | None) -> DwellingKindRow:
    found = await session.get(DwellingKindRow, kind_id) if kind_id is not None else None
    return found or await built_in_dwelling(session, "hut")
