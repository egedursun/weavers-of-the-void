from collections.abc import Mapping
from enum import StrEnum

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.api.schemas.renown import DeedClaimView, DeedRecordView, LocalReputationView, LoreTradeView, RenownView, StandingView
from aerona.api.views.common import node_ref, node_refs
from aerona.catalog.renown import AXIS_LABELS, CLAIM_LABELS, LORE_LABELS, PRICE_LABELS, STATUS_LABELS
from aerona.core.errors import NotFoundError
from aerona.db.tables.renown import DeedClaimRow, DeedRow, LoreTradeRow, ReputationRow, RulerCurrencyRow
from aerona.engine.renown.book import aggregate
from aerona.engine.renown.currencies import realm_ruled_by

router = APIRouter(tags=["renown"])
NO_NODE = "Nothing lives there."


def labels[K: StrEnum](table: Mapping[K, str]) -> list[LabelView]:
    return [LabelView(key=key.value, label=label) for key, label in table.items()]


def ref_of(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def reputation_views(session: AsyncSession, rows: list[ReputationRow]) -> list[LocalReputationView]:
    refs = await node_refs(session, [item for row in rows for item in (row.subject_node_id, row.community_node_id)])
    return [
        LocalReputationView(
            id=row.id,
            subject=refs.get(row.subject_node_id),
            community=refs.get(row.community_node_id),
            axis=row.axis,
            label=AXIS_LABELS[row.axis],
            skill=row.skill,
            value=row.value,
            heard_epoch=row.heard_epoch,
            held="value" in (row.locked or []),
        )
        for row in rows
    ]


async def deed_views(session: AsyncSession, node_id: int) -> list[DeedRecordView]:
    claimed = select(DeedClaimRow.deed_id).where(DeedClaimRow.claimant_node_id == node_id)
    rows = list(
        await session.scalars(
            select(DeedRow).where(or_(DeedRow.doer_node_id == node_id, DeedRow.id.in_(claimed))).order_by(DeedRow.epoch.desc(), DeedRow.id.desc())
        )
    )
    claims = list(await session.scalars(select(DeedClaimRow).where(DeedClaimRow.deed_id.in_([row.id for row in rows])).order_by(DeedClaimRow.id)))
    refs = await node_refs(
        session, [*(row.doer_node_id for row in rows), *(row.place_node_id for row in rows if row.place_node_id), *(row.claimant_node_id for row in claims)]
    )
    return [
        DeedRecordView(
            id=row.id,
            doer=refs.get(row.doer_node_id),
            act=row.act,
            axis=row.axis,
            label=AXIS_LABELS[row.axis],
            skill=row.skill,
            place=ref_of(refs, row.place_node_id),
            magnitude=row.magnitude,
            witnesses=row.witnesses,
            token=row.token,
            epoch=row.epoch,
            note=row.note,
            claims=[
                DeedClaimView(
                    id=claim.id,
                    claimant=refs.get(claim.claimant_node_id),
                    kind=claim.kind,
                    kind_label=CLAIM_LABELS[claim.kind],
                    status=claim.status,
                    status_label=STATUS_LABELS[claim.status],
                    credited=claim.credited,
                    epoch=claim.epoch,
                    held="status" in (claim.locked or []),
                )
                for claim in claims
                if claim.deed_id == row.id
            ],
        )
        for row in rows
    ]


async def trade_views(session: AsyncSession, node_id: int) -> list[LoreTradeView]:
    rows = list(
        await session.scalars(
            select(LoreTradeRow)
            .where(or_(LoreTradeRow.seller_node_id == node_id, LoreTradeRow.buyer_node_id == node_id))
            .order_by(LoreTradeRow.epoch.desc(), LoreTradeRow.id.desc())
        )
    )
    refs = await node_refs(session, [item for row in rows for item in (row.seller_node_id, row.buyer_node_id, row.subject_node_id) if item])
    return [
        LoreTradeView(
            id=row.id,
            seller=refs.get(row.seller_node_id),
            buyer=refs.get(row.buyer_node_id),
            kind=row.kind,
            kind_label=LORE_LABELS[row.kind],
            key=row.key,
            subject=ref_of(refs, row.subject_node_id),
            value=row.value,
            price=row.price,
            price_label=PRICE_LABELS[row.price],
            epoch=row.epoch,
        )
        for row in rows
    ]


@router.get("/renown/{node_id}", response_model=RenownView)
async def renown_view(services: ServicesDep, node_id: int = Path(ge=1)) -> RenownView:
    async with reader(services) as session:
        ref = await node_ref(session, node_id)
        if ref is None:
            raise NotFoundError(NO_NODE)
        mine = list(
            await session.scalars(select(ReputationRow).where(ReputationRow.subject_node_id == node_id).order_by(ReputationRow.value.desc(), ReputationRow.id))
        )
        held_here = list(
            await session.scalars(
                select(ReputationRow).where(ReputationRow.community_node_id == node_id).order_by(ReputationRow.value.desc(), ReputationRow.id)
            )
        )
        glory, infamy = aggregate(mine)
        purse = await session.get(RulerCurrencyRow, node_id)
        realm = await realm_ruled_by(session, node_id)
        return RenownView(
            node_id=node_id,
            name=ref.name,
            glory=glory,
            infamy=infamy,
            reputations=await reputation_views(session, mine),
            views=await reputation_views(session, held_here),
            standing=StandingView(
                prestige=purse.prestige,
                piety=purse.piety,
                dread=purse.dread,
                tyranny=purse.tyranny,
                trust=purse.trust,
                learning=purse.learning,
                silenced_until=purse.silenced_until,
                updated_epoch=purse.updated_epoch,
                realm=await node_ref(session, realm),
                held=list(purse.locked or []),
            )
            if purse is not None
            else None,
            ruler=realm is not None,
            deeds=await deed_views(session, node_id),
            trades=await trade_views(session, node_id),
            axes=labels(AXIS_LABELS),
            claim_kinds=labels(CLAIM_LABELS),
            claim_statuses=labels(STATUS_LABELS),
            lore_kinds=labels(LORE_LABELS),
        )
