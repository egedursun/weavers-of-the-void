from sqlalchemy import select

from aerona.catalog.bonds import bond_fits
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.context import TickContext
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.transform.ledger import Ledger

KINDS_ALL = tuple(BondKind)


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


async def carry_bonds(ctx: TickContext, ledger: Ledger, subject_id: int, result_id: int) -> int:
    old = await ctx.session.get(EntityRow, subject_id)
    new = await ctx.session.get(EntityRow, result_id)
    if old is None or new is None or old.id == new.id:
        return 0
    carried = 0
    held_now = {
        (bond.source_node_id, bond.target_node_id, bond.kind) for bond in [*await bonds_from(ctx, new.id, KINDS_ALL), *await bonds_to(ctx, new.id, KINDS_ALL)]
    }
    for bond in [*await bonds_from(ctx, old.id, KINDS_ALL), *await bonds_to(ctx, old.id, KINDS_ALL)]:
        outgoing = bond.source_node_id == old.id
        other_id = bond.target_node_id if outgoing else bond.source_node_id
        if other_id == new.id:
            continue
        other = await ctx.session.get(EntityRow, other_id)
        if other is None or other.status is not EntityStatus.CANON:
            continue
        source, target = (new, other) if outgoing else (other, new)
        if not bond_fits(bond.kind, source.entity_type, target.entity_type) or (source.id, target.id, bond.kind) in held_now:
            continue
        await bind(ctx, ledger, (source.id, target.id, bond.kind), bond.description or f"carried over from {old.name}", role=bond.role)
        held_now.add((source.id, target.id, bond.kind))
        carried += 1
    return carried
