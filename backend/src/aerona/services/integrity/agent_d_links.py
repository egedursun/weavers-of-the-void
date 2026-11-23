from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.identity import POINTED_LAYERS
from aerona.catalog.lore import slot_fit
from aerona.catalog.marks import MARKS
from aerona.catalog.pacts import LORE_PRICES, THIRD_PARTY_STATES
from aerona.catalog.revivals import REVIVAL_WAYS
from aerona.db.tables.belonging import HeldIdentityRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.customs import BodyMarkRow, RevivalRow
from aerona.db.tables.made import AugmentRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.renown import DeedClaimRow, LoreTradeRow
from aerona.db.tables.statecraft import CrisisRow
from aerona.domain.enums.renown import ClaimStatus, ServiceTask
from aerona.domain.enums.statecraft import CrisisState

POINTED = POINTED_LAYERS


async def lost_identity_targets(session: AsyncSession) -> list[int]:
    found: set[int] = set()
    rows = await session.scalars(
        select(HeldIdentityRow).where(HeldIdentityRow.layer.in_(POINTED), HeldIdentityRow.value_node_id.is_not(None)).order_by(HeldIdentityRow.holder_entity_id)
    )
    for row in rows:
        if row.value_node_id is not None and await session.get(NodeRow, row.value_node_id) is None:
            found.add(row.holder_entity_id)
    return sorted(found)


async def clear_identity_target(session: AsyncSession, key: int) -> None:
    for layer in POINTED:
        row = await session.get(HeldIdentityRow, (key, layer))
        if row is not None and row.value_node_id is not None and "value_node_id" not in row.locked and await session.get(NodeRow, row.value_node_id) is None:
            row.value_node_id = None


async def misfit_revivals(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(RevivalRow).order_by(RevivalRow.id))
    return [row.id for row in rows if row.goal not in REVIVAL_WAYS[row.way].goals]


async def refit_revival(session: AsyncSession, key: int) -> None:
    row = await session.get(RevivalRow, key)
    if row is not None and "goal" not in row.locked:
        row.goal = sorted(REVIVAL_WAYS[row.way].goals)[0]


async def unbacked_implants(session: AsyncSession) -> list[int]:
    shown = [kind for kind, spec in MARKS.items() if spec.shows_augment]
    found: list[int] = []
    for row in await session.scalars(select(BodyMarkRow).where(BodyMarkRow.kind.in_(shown)).order_by(BodyMarkRow.id)):
        augment = await session.get(AugmentRow, row.augment_id) if row.augment_id is not None else None
        if augment is None or augment.bearer_node_id != row.holder_node_id:
            found.append(row.id)
    return found


async def strike_unbacked_implant(session: AsyncSession, key: int) -> None:
    row = await session.get(BodyMarkRow, key)
    if row is not None and not row.locked:
        await session.delete(row)


async def unslotted_traditions(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(TraditionProfileRow).where(TraditionProfileRow.calendar_slot.is_(None)).order_by(TraditionProfileRow.tradition_entity_id)
    )
    return [row.tradition_entity_id for row in rows if slot_fit(row.kind, row.stage) is not None]


async def slot_tradition(session: AsyncSession, key: int) -> None:
    row = await session.get(TraditionProfileRow, key)
    if row is not None and "calendar_slot" not in row.locked:
        row.calendar_slot = slot_fit(row.kind, row.stage)


async def unnamed_mediations(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(CrisisRow.id).where(CrisisRow.state.in_(list(THIRD_PARTY_STATES)), CrisisRow.mediator_entity_id.is_(None)).order_by(CrisisRow.id)
    )
    return list(rows)


async def reopen_unnamed_mediation(session: AsyncSession, key: int) -> None:
    row = await session.get(CrisisRow, key)
    if row is not None and "state" not in row.locked:
        row.state, row.resolved_epoch = CrisisState.ESCALATING, None


async def lone_disputes(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(DeedClaimRow.id).where(DeedClaimRow.status == ClaimStatus.DISPUTED, DeedClaimRow.contested_by_node_id.is_(None)).order_by(DeedClaimRow.id)
    )
    return list(rows)


async def settle_lone_dispute(session: AsyncSession, key: int) -> None:
    row = await session.get(DeedClaimRow, key)
    if row is not None and "status" not in row.locked:
        row.status = ClaimStatus.STANDING


async def taskless_services(session: AsyncSession) -> list[int]:
    deferred = [price for price, spec in LORE_PRICES.items() if spec.deferred]
    rows = await session.scalars(select(LoreTradeRow.id).where(LoreTradeRow.price.in_(deferred), LoreTradeRow.task.is_(None)).order_by(LoreTradeRow.id))
    return list(rows)


async def name_service_task(session: AsyncSession, key: int) -> None:
    row = await session.get(LoreTradeRow, key)
    if row is not None:
        row.task = next(iter(ServiceTask))
