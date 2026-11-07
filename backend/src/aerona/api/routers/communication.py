from collections.abc import Iterable, Mapping
from enum import StrEnum

from fastapi import APIRouter, Path
from sqlalchemy import or_, select

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.communication import CipherView, CorrespondenceView, DispatchView, PublicOpinionView, SignalView
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_refs
from aerona.catalog.communication import CONTENT_LABELS, ENVOY_LABELS, MEDIUM_LABELS, SIGNAL_LABELS, SIGNAL_STATE_LABELS, STATE_LABELS, SUBJECT_LABELS
from aerona.core.errors import NotFoundError
from aerona.db.tables.communication import CipherRow, PublicOpinionRow, SignalLinkRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.agent import MessageIntent

router = APIRouter(tags=["communication"])
NO_NODE = "Nothing lives there."
UNSET = "Unrecorded"


def labels[K: StrEnum](table: Mapping[K, str]) -> list[LabelView]:
    return [LabelView(key=key.value, label=label) for key, label in table.items()]


def refs_of(refs: Mapping[int, NodeRef], ids: Iterable[int]) -> list[NodeRef]:
    return [refs[node_id] for node_id in ids if node_id in refs]


def ref(refs: Mapping[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


def dispatch_view(row: MessageRow, refs: Mapping[int, NodeRef]) -> DispatchView:
    return DispatchView(
        id=row.id,
        sender=ref(refs, row.sender_node_id),
        recipient=ref(refs, row.recipient_node_id),
        medium=row.medium,
        medium_label=MEDIUM_LABELS[row.medium] if row.medium is not None else UNSET,
        content=row.content,
        content_label=CONTENT_LABELS[row.content] if row.content is not None else UNSET,
        state=row.state,
        state_label=STATE_LABELS[row.state] if row.state is not None else UNSET,
        language=ref(refs, row.language_node_id),
        envoy=ref(refs, row.envoy_node_id),
        envoy_fate=row.envoy_fate,
        envoy_fate_label=ENVOY_LABELS[row.envoy_fate] if row.envoy_fate is not None else None,
        intercepted_by=ref(refs, row.intercepted_by_node_id),
        payload=row.payload or {},
        sent_epoch=row.epoch,
        arrival_epoch=row.arrival_epoch,
        forged=row.forged,
        misread=row.misread,
        enciphered=row.enciphered,
        held=sorted(row.locked or []),
    )


def opinion_view(row: PublicOpinionRow, refs: Mapping[int, NodeRef]) -> PublicOpinionView:
    return PublicOpinionView(
        community=ref(refs, row.community_node_id),
        subject=ref(refs, row.subject_node_id),
        subject_kind=row.subject,
        subject_label=SUBJECT_LABELS[row.subject],
        approval=row.approval,
        censored=row.censored,
        epoch=row.epoch,
        held=sorted(row.locked or []),
    )


def cipher_view(row: CipherRow, refs: Mapping[int, NodeRef]) -> CipherView:
    return CipherView(
        owner=ref(refs, row.owner_node_id),
        strength=row.strength,
        broken_by=refs_of(refs, row.broken_by),
        attempts=sum(row.attempts.values()),
        break_known=row.break_known,
        since_epoch=row.since_epoch,
        held=sorted(row.locked or []),
    )


def signal_view(row: SignalLinkRow, refs: Mapping[int, NodeRef]) -> SignalView:
    return SignalView(
        id=row.id,
        owner=ref(refs, row.owner_node_id),
        kind=row.kind,
        kind_label=SIGNAL_LABELS[row.kind],
        start=ref(refs, row.from_region_id),
        end=ref(refs, row.to_region_id),
        state=row.state,
        state_label=SIGNAL_STATE_LABELS[row.state],
        since_epoch=row.since_epoch,
        held=sorted(row.locked or []),
    )


@router.get("/correspondence/{node_id}", response_model=CorrespondenceView)
async def correspondence_view(services: ServicesDep, node_id: int = Path(ge=1)) -> CorrespondenceView:
    async with reader(services) as session:
        if await session.get(NodeRow, node_id) is None:
            raise NotFoundError(NO_NODE)
        dispatches = list(
            await session.scalars(
                select(MessageRow)
                .where(
                    MessageRow.intent == MessageIntent.DISPATCH,
                    or_(MessageRow.sender_node_id == node_id, MessageRow.recipient_node_id == node_id, MessageRow.intercepted_by_node_id == node_id),
                )
                .order_by(MessageRow.id.desc())
            )
        )
        opinions = list(
            await session.scalars(
                select(PublicOpinionRow)
                .where(or_(PublicOpinionRow.community_node_id == node_id, PublicOpinionRow.subject_node_id == node_id))
                .order_by(PublicOpinionRow.community_node_id, PublicOpinionRow.subject_node_id)
            )
        )
        cipher = await session.get(CipherRow, node_id)
        read = [row for row in await session.scalars(select(CipherRow).order_by(CipherRow.owner_node_id)) if node_id in row.broken_by]
        signals = list(await session.scalars(select(SignalLinkRow).where(SignalLinkRow.owner_node_id == node_id).order_by(SignalLinkRow.id)))
        ids = {
            node
            for node in (
                *(
                    item
                    for row in dispatches
                    for item in (row.sender_node_id, row.recipient_node_id, row.language_node_id, row.envoy_node_id, row.intercepted_by_node_id)
                ),
                *(item for row in opinions for item in (row.community_node_id, row.subject_node_id)),
                *(item for row in [*([cipher] if cipher else []), *read] for item in (row.owner_node_id, *row.broken_by)),
                *(item for row in signals for item in (row.owner_node_id, row.from_region_id, row.to_region_id)),
            )
            if node is not None
        }
        refs = await node_refs(session, ids)
        return CorrespondenceView(
            node_id=node_id,
            sent=[dispatch_view(row, refs) for row in dispatches if row.sender_node_id == node_id],
            received=[dispatch_view(row, refs) for row in dispatches if row.recipient_node_id == node_id],
            intercepted=[dispatch_view(row, refs) for row in dispatches if row.intercepted_by_node_id == node_id],
            opinions=[opinion_view(row, refs) for row in opinions if row.community_node_id == node_id],
            regarded=[opinion_view(row, refs) for row in opinions if row.subject_node_id == node_id],
            cipher=cipher_view(cipher, refs) if cipher is not None else None,
            ciphers_read=[cipher_view(row, refs) for row in read],
            signals=[signal_view(row, refs) for row in signals],
            mediums=labels(MEDIUM_LABELS),
            contents=labels(CONTENT_LABELS),
            states=labels(STATE_LABELS),
            subjects=labels(SUBJECT_LABELS),
            signal_kinds=labels(SIGNAL_LABELS),
            signal_states=labels(SIGNAL_STATE_LABELS),
        )
