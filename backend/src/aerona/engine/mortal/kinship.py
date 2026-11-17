from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MarriageRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mortal import MarriageEnd
from aerona.domain.enums.unions import UnionForm, UnionPurpose
from aerona.engine.primitives.queries import connect
from aerona.engine.unions.customs import kept_past_death

KIN_FIXUP = "mortal.typed_kin"
MARRIED_BY = ("arranged marriage", "marriage by treaty", "marriage alliance")


async def marriage_between(session: AsyncSession, first: int, second: int) -> MarriageRow | None:
    statement = select(MarriageRow).where(
        MarriageRow.end_epoch.is_(None),
        or_(
            (MarriageRow.first_id == first) & (MarriageRow.second_id == second),
            (MarriageRow.first_id == second) & (MarriageRow.second_id == first),
        ),
    )
    found: MarriageRow | None = await session.scalar(statement.limit(1))
    return found


async def marriages_of(session: AsyncSession, mortal_id: int, *, ended: bool = True) -> list[MarriageRow]:
    statement = select(MarriageRow).where(or_(MarriageRow.first_id == mortal_id, MarriageRow.second_id == mortal_id))
    if not ended:
        statement = statement.where(MarriageRow.end_epoch.is_(None))
    return list(await session.scalars(statement.order_by(MarriageRow.start_epoch, MarriageRow.id)))


async def close_between(session: AsyncSession, first: int, second: int, kinds: tuple[BondKind, ...], *, epoch: int, reason: str) -> int:
    repository = BondRepository(session)
    closed = 0
    for bond in await repository.active_between(first, second, list(kinds)):
        await repository.deactivate(bond, epoch, reason)
        closed += 1
    return closed


async def marry(
    session: AsyncSession,
    first: EntityRow,
    second: EntityRow,
    epoch: int,
    *,
    form: UnionForm = UnionForm.PAIR,
    purpose: UnionPurpose = UnionPurpose.KINSHIP,
    treaty_id: int | None = None,
    forced: bool = False,
    description: str | None = None,
) -> MarriageRow:
    existing = await marriage_between(session, first.id, second.id)
    if existing is not None:
        return existing
    await close_between(session, first.id, second.id, (BondKind.BETROTHED_TO,), epoch=epoch, reason="wed")
    await connect(session, first.id, second.id, BondKind.SPOUSE_OF, epoch, description=description)
    row = MarriageRow(first_id=first.id, second_id=second.id, form=form, purpose=purpose, treaty_id=treaty_id, start_epoch=max(0, epoch), forced=forced)
    session.add(row)
    await session.flush()
    return row


async def end_marriage(session: AsyncSession, row: MarriageRow, epoch: int, cause: MarriageEnd) -> None:
    if row.end_epoch is not None:
        return
    row.end_epoch = max(row.start_epoch, epoch)
    row.cause_end = cause
    await close_between(session, row.first_id, row.second_id, (BondKind.SPOUSE_OF,), epoch=epoch, reason=cause.value)


async def widow(session: AsyncSession, dead_id: int, epoch: int) -> list[int]:
    survivors: list[int] = []
    for row in await marriages_of(session, dead_id, ended=False):
        survivor = row.second_id if row.first_id == dead_id else row.first_id
        survivors.append(survivor)
        if not await kept_past_death(session, survivor):
            await end_marriage(session, row, epoch, MarriageEnd.DEATH)
    return survivors


async def betroth(session: AsyncSession, first: EntityRow, second: EntityRow, epoch: int, *, description: str | None = None) -> BondRow | None:
    return await connect(session, first.id, second.id, BondKind.BETROTHED_TO, epoch, description=description)


async def add_parent(session: AsyncSession, parent_id: int, child_id: int, epoch: int, *, description: str | None = None) -> BondRow | None:
    return await connect(session, parent_id, child_id, BondKind.PARENT_OF, epoch, description=description)


async def foster(session: AsyncSession, child_id: int, fosterer_id: int, epoch: int, *, description: str | None = None) -> BondRow | None:
    return await connect(session, child_id, fosterer_id, BondKind.FOSTERED_BY, epoch, description=description)


async def mortal_ids(session: AsyncSession, ids: set[int]) -> set[int]:
    if not ids:
        return set()
    rows = await session.scalars(select(EntityRow.id).where(EntityRow.id.in_(list(ids)), EntityRow.entity_type == EntityType.MORTAL))
    return set(rows)


async def backfill_kin(session: AsyncSession, epoch: int) -> dict[str, int]:
    if await session.get(AppliedFixupRow, KIN_FIXUP) is not None:
        return {}
    repository = BondRepository(session)
    descent = list(await session.scalars(select(BondRow).where(BondRow.kind == BondKind.DESCENDS_FROM).order_by(BondRow.id)))
    mortals = await mortal_ids(session, {node for bond in descent for node in (bond.source_node_id, bond.target_node_id)})
    parents = 0
    children: dict[int, set[int]] = {}
    for bond in descent:
        if bond.source_node_id not in mortals or bond.target_node_id not in mortals:
            continue
        if not await repository.active_between(bond.target_node_id, bond.source_node_id, [BondKind.PARENT_OF]):
            made = await connect(session, bond.target_node_id, bond.source_node_id, BondKind.PARENT_OF, bond.epoch, description=bond.description)
            if made is not None and bond.state is not BondState.ACTIVE:
                made.state = bond.state
            parents += 1
        children.setdefault(bond.target_node_id, set()).add(bond.source_node_id)
        await repository.deactivate(bond, epoch, "now a typed parent bond", BondState.HIDDEN_CLOSED)
    loves = list(await session.scalars(select(BondRow).where(BondRow.kind == BondKind.LOVES).order_by(BondRow.id)))
    lovers = await mortal_ids(session, {node for bond in loves for node in (bond.source_node_id, bond.target_node_id)})
    spouses = 0
    for bond in loves:
        first, second = bond.source_node_id, bond.target_node_id
        if first not in lovers or second not in lovers:
            continue
        shared = children.get(first, set()) & children.get(second, set())
        arranged = (bond.description or "") in MARRIED_BY
        if not shared and not arranged:
            continue
        if await marriage_between(session, first, second) is not None:
            continue
        purpose = UnionPurpose.ALLIANCE if arranged else UnionPurpose.KINSHIP
        made = await connect(session, first, second, BondKind.SPOUSE_OF, bond.epoch, description=bond.description)
        row = MarriageRow(first_id=first, second_id=second, purpose=purpose, start_epoch=max(0, bond.epoch), forced=False)
        if bond.state is not BondState.ACTIVE:
            row.end_epoch = bond.closed_epoch or epoch
            row.cause_end = MarriageEnd.DEATH
            if made is not None:
                made.state = BondState.PAST
        session.add(row)
        spouses += 1
    result = {"parents": parents, "marriages": spouses}
    session.add(AppliedFixupRow(key=KIN_FIXUP, result=result))
    await session.flush()
    return result
