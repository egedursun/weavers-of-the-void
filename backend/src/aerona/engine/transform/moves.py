from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.context import TickContext
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.transform.ledger import Ledger


async def make(ctx: TickContext, ledger: Ledger, spec: RecordSpec) -> EntityRow:
    entity = await create_record(ctx, spec)
    ledger.made(entity.id)
    return entity


def end(ctx: TickContext, ledger: Ledger, entity: EntityRow, status: EntityStatus) -> None:
    ledger.set(entity, "status", status)
    ledger.set(entity, "end_epoch", ctx.epoch)


async def bind(ctx: TickContext, ledger: Ledger, link: tuple[int, int, BondKind], description: str, *, role: BondRole | None = None) -> None:
    source, target, kind = link
    if source == target:
        return
    bond = await BondRepository(ctx.session).connect(BondDraft(source, target, kind, ctx.epoch, description, role=role))
    if bond is not None:
        ledger.added(bond)


def unbind(ctx: TickContext, ledger: Ledger, bond: BondRow, reason: str) -> None:
    ledger.set(bond, "state", BondState.PAST)
    ledger.set(bond, "closed_epoch", ctx.epoch)
    ledger.set(bond, "closed_reason", reason)


async def bonds_to(ctx: TickContext, target: int, kinds: tuple[BondKind, ...]) -> list[BondRow]:
    statement = select(BondRow).where(BondRow.target_node_id == target, BondRow.kind.in_(kinds), BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    return list(await ctx.session.scalars(statement))


async def bonds_from(ctx: TickContext, source: int, kinds: tuple[BondKind, ...]) -> list[BondRow]:
    statement = select(BondRow).where(BondRow.source_node_id == source, BondRow.kind.in_(kinds), BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    return list(await ctx.session.scalars(statement))


async def move_bonds(ctx: TickContext, ledger: Ledger, old: int, new: int, *, kinds: tuple[BondKind, ...], reason: str) -> int:
    moved = 0
    for bond in await bonds_to(ctx, old, kinds):
        if bond.source_node_id == new:
            continue
        unbind(ctx, ledger, bond, reason)
        await bind(ctx, ledger, (bond.source_node_id, new, bond.kind), bond.description or reason)
        moved += 1
    return moved
