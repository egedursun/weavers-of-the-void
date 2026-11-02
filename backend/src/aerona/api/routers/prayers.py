from fastapi import APIRouter
from sqlalchemy import select

from aerona.api.actions import Alias, mount_all
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import MessageRecord, NodeRef
from aerona.api.views.common import node_refs
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.node import NodeKind
from aerona.services.images.records import cover_of

router = APIRouter(tags=["prayers"])

ALIASES = (Alias("POST", "/prayers/{message_id}/answer", "answer_prayer", path_fields={"message_id": "message_id"}),)


class PrayerView(ApiModel):
    message: MessageRecord
    sender: NodeRef | None
    sender_cover: str | None = None


@router.get("/prayers", response_model=list[PrayerView])
async def list_prayers(services: ServicesDep) -> list[PrayerView]:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        creator = await CosmosRepository(session).creator()
        if creator is None:
            return []
        limit = rules.server.prayer_list
        base = (
            select(MessageRow)
            .join(NodeRow, NodeRow.id == MessageRow.sender_node_id)
            .where(MessageRow.recipient_node_id == creator.id, MessageRow.intent == MessageIntent.PRAYER)
            .order_by(MessageRow.answered, MessageRow.id.desc())
        )
        from_sons = list(await session.scalars(base.where(NodeRow.kind == NodeKind.SON).limit(limit)))
        from_mortals = list(await session.scalars(base.where(NodeRow.kind == NodeKind.ENTITY).limit(limit)))
        merged = sorted([*from_sons, *from_mortals], key=lambda row: (row.answered, -row.id))
        refs = await node_refs(session, [row.sender_node_id for row in merged])
        covers = {node_id: await cover_of(session, node_id) for node_id in {row.sender_node_id for row in merged}}
        return [
            PrayerView(message=MessageRecord.model_validate(row), sender=refs.get(row.sender_node_id), sender_cover=covers.get(row.sender_node_id))
            for row in merged
        ]


mount_all(router, ALIASES, tag="prayers")
