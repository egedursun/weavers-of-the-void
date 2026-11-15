from fastapi import APIRouter, Path, Query, status
from pydantic import Field
from sqlalchemy import or_, select

from aerona.agents.son_chat import ChatReply, chat_with_son
from aerona.api.actions import Alias, mount_all
from aerona.api.background import require_llm
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.common import JobAccepted, RequestModel
from aerona.api.schemas.gods import DeadSonPanel, DistributionPreviewView, FolkView, MessageView, ResurrectionOrder, SiblingView, SonDetail, SonReputation
from aerona.api.schemas.records import EntitySummary, MessageRecord, NodeRef, SonPublic, SonRecord
from aerona.api.schemas.state import SonRelationItem
from aerona.api.views.common import bond_count, bond_views, images_of, node_refs, son_chronicle, son_public
from aerona.constants.api import RELATION_PAGE_DEFAULT, RELATION_PAGE_MAX
from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import FolkBeliefRow, MessageRow
from aerona.db.tables.sons import SonRelationRow, SonRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind, BondState
from aerona.engine.gods.devotion import resurrection_state
from aerona.services.faith import live_faith
from aerona.services.images.records import cover_of
from aerona.services.player.assignments import distribution_preview
from aerona.services.player.scope import PlayerScope
from aerona.services.state import son_views

router = APIRouter(tags=["sons"])

NO_SON = "No such son."
NOT_DEAD = "That son is not dead."
CHAT_MAX_LENGTH = 20000

ALIASES = (
    Alias("POST", "/sons/summon", "summon_son"),
    Alias("POST", "/sons/distribute", "son:distribute"),
    Alias("PUT", "/sons/{son_id}/order", "command", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/bless", "bless", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/punish", "punish", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/star", "son:star", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/ascend", "son:ascend", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/epic", "son:epic", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/resurrect", "resurrect:son", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/kill", "kill:son", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/devour", "devour:son", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/drain", "drain:son", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/absolute-command", "absolute_command", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/demote", "demote", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/strip-power", "strip_power", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/rebellion", "rebellion:force", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/scheme", "sibling:scheme", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/scatter-bones", "sibling:scatter", path_fields={"son_id": "son_id"}),
    Alias("PUT", "/sons/{son_id}/world", "son:world", path_fields={"son_id": "son_id"}),
    Alias("DELETE", "/sons/{son_id}/protection", "son:protection", path_fields={"son_id": "son_id"}),
    Alias("PATCH", "/sons/{son_id}", "son:edit", path_fields={"son_id": "son_id"}),
    Alias("POST", "/sons/{son_id}/reset-counters", "son:reset_counters", path_fields={"son_id": "son_id"}),
    Alias("PUT", "/sons/{son_id}/image-prompt", "son:image_prompt", path_fields={"son_id": "son_id"}),
)


class ChatRequest(RequestModel):
    text: str = Field(min_length=1, max_length=CHAT_MAX_LENGTH)


@router.get("/sons", response_model=list[SonPublic])
async def list_sons(services: ServicesDep) -> list[SonPublic]:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        return [son_public(view) for view in await son_views(session, rules)]


@router.get("/sons/relations", response_model=list[SonRelationItem])
async def list_relations(services: ServicesDep) -> list[SonRelationItem]:
    async with reader(services) as session:
        rows = await session.scalars(select(SonRelationRow).order_by(SonRelationRow.son_a_id, SonRelationRow.son_b_id))
        return [SonRelationItem.model_validate(row) for row in rows]


@router.get("/sons/distribution-preview", response_model=DistributionPreviewView)
async def distribution_preview_view(services: ServicesDep) -> DistributionPreviewView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        preview = await distribution_preview(PlayerScope(session, rules))
        return DistributionPreviewView.model_validate(preview.model_dump())


@router.get("/sons/{son_id}", response_model=SonDetail)
async def read_son(
    services: ServicesDep,
    son_id: int = Path(ge=1),
    bond_offset: int = Query(default=0, ge=0),
    bond_limit: int = Query(default=RELATION_PAGE_DEFAULT, ge=1, le=RELATION_PAGE_MAX),
) -> SonDetail:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        son = await session.get(SonRow, son_id)
        if son is None:
            raise NotFoundError(NO_SON)
        server = rules.server
        creations = list(await session.scalars(select(EntityRow).where(EntityRow.creator_son_id == son.id).order_by(EntityRow.id.desc())))
        messages = list(
            await session.scalars(
                select(MessageRow)
                .where(or_(MessageRow.sender_node_id == son.id, MessageRow.recipient_node_id == son.id))
                .order_by(MessageRow.id.desc())
                .limit(server.son_messages_shown)
            )
        )
        relations = list(await session.scalars(select(SonRelationRow).where(or_(SonRelationRow.son_a_id == son.id, SonRelationRow.son_b_id == son.id))))
        worshippers = list(
            await session.scalars(
                select(EntityRow)
                .join(BondRow, BondRow.source_node_id == EntityRow.id)
                .where(BondRow.target_node_id == son.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
                .order_by(EntityRow.id)
            )
        )
        beliefs = await session.execute(
            select(FolkBeliefRow, EntityRow.name).join(EntityRow, EntityRow.id == FolkBeliefRow.people_entity_id).where(FolkBeliefRow.god_node_id == son.id)
        )
        children = list(await session.scalars(select(SonRow).where(or_(SonRow.parent_son_id == son.id, SonRow.co_parent_son_id == son.id))))
        others = [relation.son_b_id if relation.son_a_id == son.id else relation.son_a_id for relation in relations]
        refs = await node_refs(session, [*others, *(m.sender_node_id for m in messages), *(m.recipient_node_id for m in messages)])
        anchor = await session.get(EntityRow, son.anchor_entity_id) if son.anchor_entity_id else None
        parent = (await node_refs(session, [son.parent_son_id])).get(son.parent_son_id) if son.parent_son_id else None
        siblings = [
            SiblingView(son=refs[other], value=relation.value, note=relation.note, cover=await cover_of(session, other))
            for relation, other in zip(relations, others, strict=True)
            if other in refs
        ]
        reputation = None
        if son.reputation_label is not None:
            reputation = SonReputation(
                son_id=son.id,
                name=son.name,
                love=son.reputation_love or 0,
                fear=son.reputation_fear or 0,
                forgotten=son.reputation_forgotten or 0,
                unanswered=son.reputation_unanswered or 0,
                last_contact=son.reputation_last_contact_epoch or 0,
                label=son.reputation_label,
            )
        return SonDetail(
            son=SonRecord.model_validate(son),
            kill_cost=rules.death.creator_kill_son_cost,
            reputation=reputation,
            folk_views=[
                FolkView(
                    people_id=row.people_entity_id,
                    people_name=name,
                    local_name=row.local_name,
                    account=row.account,
                    misconception=row.misconception,
                    epoch=row.epoch,
                )
                for row, name in beliefs
            ],
            creations=[EntitySummary.model_validate(row) for row in creations],
            chronicle=await son_chronicle(session, son.id, server.son_chronicle_lines),
            messages=[
                MessageView(
                    id=row.id,
                    epoch=row.epoch,
                    sender=refs.get(row.sender_node_id),
                    recipient=refs.get(row.recipient_node_id),
                    intent=row.intent,
                    text=row.text,
                    tone=row.tone,
                    answered=row.answered,
                )
                for row in messages
            ],
            siblings=siblings,
            bonds=await bond_views(session, son.id, offset=bond_offset, limit=bond_limit),
            bond_total=await bond_count(session, son.id, active_only=False),
            live_faith=await live_faith(session, rules, son.id),
            worshippers=[EntitySummary.model_validate(row) for row in worshippers],
            anchor=EntitySummary.model_validate(anchor) if anchor else None,
            parent=parent,
            children=[NodeRef(id=child.id, kind=child.kind, name=child.name) for child in children],
            images=await images_of(session, son.id),
        )


@router.get("/sons/{son_id}/resurrection", response_model=DeadSonPanel)
async def read_dead_son_panel(services: ServicesDep, son_id: int = Path(ge=1)) -> DeadSonPanel:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        son = await session.get(SonRow, son_id)
        if son is None:
            raise NotFoundError(NO_SON)
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        state = await resurrection_state(session, rules, son, epoch)
        if state is None:
            raise ConflictError(NOT_DEAD)
        return DeadSonPanel(
            son_id=state.son_id,
            name=state.name,
            death_epoch=state.death_epoch,
            death_cause=son.death_cause,
            earliest_return_epoch=state.earliest_epoch,
            epochs_remaining=state.remaining,
            devotion=state.devotion,
            devotion_required=rules.death.resurrection_devotion_required,
            corpse=EntitySummary.model_validate(state.corpse) if state.corpse is not None else None,
            orders=[ResurrectionOrder(id=order.id, name=order.name, devotion=order.devotion, followers=order.followers) for order in state.orders],
            loyal_communities=[EntitySummary.model_validate(entity) for entity in state.faithful],
        )


@router.get("/sons/{son_id}/chat", response_model=list[MessageRecord])
async def read_chat(services: ServicesDep, son_id: int = Path(ge=1)) -> list[MessageRecord]:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        if await session.get(SonRow, son_id) is None:
            raise NotFoundError(NO_SON)
        rows = list(
            await session.scalars(
                select(MessageRow)
                .where(MessageRow.intent == MessageIntent.CHAT, or_(MessageRow.sender_node_id == son_id, MessageRow.recipient_node_id == son_id))
                .order_by(MessageRow.id.desc())
                .limit(rules.council.chat_list_messages)
            )
        )
    return [MessageRecord.model_validate(row) for row in reversed(rows)]


@router.post("/sons/{son_id}/chat", response_model=ChatReply)
async def chat(request: ChatRequest, services: ServicesDep, son_id: int = Path(ge=1)) -> ChatReply:
    require_llm(services, "Speaking with a son")
    return await chat_with_son(services.agents, son_id, request.text)


@router.post("/sons/{son_id}/act", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def act(services: ServicesDep, son_id: int = Path(ge=1)) -> JobAccepted:
    require_llm(services, "A son's turn")
    async with reader(services) as session:
        if await session.get(SonRow, son_id) is None:
            raise NotFoundError(NO_SON)
    return JobAccepted(job_id=await services.orchestrator.submit_son_turn(son_id))


mount_all(router, ALIASES, tag="sons")
