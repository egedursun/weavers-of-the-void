from fastapi import APIRouter, Path

from aerona.agents.tool_ports import agent_tool_ports
from aerona.api.dependencies import ServicesDep, reader, world_rules
from aerona.api.schemas.opportunities import (
    BlockedToolView,
    CreatorHintLine,
    CreatorHintLines,
    DreamInbox,
    DreamView,
    MortalAgentContext,
    OpportunityLines,
    OpportunityLineView,
    SonToolsView,
    ToolPreviewView,
    TurnCounterView,
)
from aerona.api.views.common import node_refs
from aerona.db.tables.lore import MessageRow
from aerona.services.gods import preview
from aerona.tools.preview import ToolAvailability

router = APIRouter(tags=["previews"])


def tool_views(availability: ToolAvailability) -> tuple[list[ToolPreviewView], list[BlockedToolView]]:
    available = [ToolPreviewView.model_validate(tool, from_attributes=True) for tool in availability.available]
    blocked = [BlockedToolView.model_validate(tool, from_attributes=True) for tool in availability.blocked]
    return available, blocked


def counter_views(counters: list[preview.TurnCounterReading]) -> list[TurnCounterView]:
    return [TurnCounterView(counter=item.counter, value=item.value) for item in counters]


@router.get("/opportunities/creator", response_model=CreatorHintLines)
async def creator_opportunities(services: ServicesDep) -> CreatorHintLines:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        found = await preview.creator_hint_lines(session, rules)
    return CreatorHintLines(lines=[CreatorHintLine(kind=item.kind, text=item.text) for item in found])


@router.get("/sons/{son_id}/opportunities", response_model=OpportunityLines)
async def son_opportunities(services: ServicesDep, son_id: int = Path(ge=1)) -> OpportunityLines:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        found = await preview.son_opportunity_lines(session, rules, agent_tool_ports(services.agents), son_id)
    return OpportunityLines(
        subject_id=son_id, lines=[OpportunityLineView(kind=item.kind, text=item.text, tension=item.tension, tools=item.tools) for item in found]
    )


@router.get("/entities/{entity_id}/opportunities", response_model=OpportunityLines)
async def entity_opportunities(services: ServicesDep, entity_id: int = Path(ge=1)) -> OpportunityLines:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        found = await preview.mortal_opportunity_lines(session, rules, agent_tool_ports(services.agents), entity_id)
    return OpportunityLines(
        subject_id=entity_id, lines=[OpportunityLineView(kind=item.kind, text=item.text, tension=item.tension, tools=item.tools) for item in found]
    )


@router.get("/sons/{son_id}/tools", response_model=SonToolsView)
async def son_tools(services: ServicesDep, son_id: int = Path(ge=1)) -> SonToolsView:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        reading = await preview.son_tools_reading(session, rules, agent_tool_ports(services.agents), son_id)
    available, blocked = tool_views(reading.availability)
    return SonToolsView(
        son_id=reading.son.id,
        rarity=reading.son.rarity,
        epoch=reading.epoch,
        action_points_left=reading.action_points_left,
        available=available,
        blocked=blocked,
        counters=counter_views(reading.counters),
    )


@router.get("/entities/{entity_id}/agent-context", response_model=MortalAgentContext)
async def entity_agent_context(services: ServicesDep, entity_id: int = Path(ge=1)) -> MortalAgentContext:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        reading = await preview.mortal_context_reading(session, services.agents, rules, entity_id)
    available, blocked = tool_views(reading.availability)
    return MortalAgentContext(
        entity_id=reading.entity.id,
        name=reading.entity.name,
        epoch=reading.epoch,
        action_points=reading.action_points,
        system_prompt=reading.system_prompt,
        user_prompt=reading.user_prompt,
        available=available,
        blocked=blocked,
        counters=counter_views(reading.counters),
    )


@router.get("/entities/{entity_id}/dreams", response_model=DreamInbox)
async def entity_dreams(services: ServicesDep, entity_id: int = Path(ge=1)) -> DreamInbox:
    async with reader(services) as session:
        rules = await world_rules(services, session)
        received, sent = await preview.dream_messages(session, entity_id, rules.server.entity_dreams_shown)
        refs = await node_refs(session, [node for row in (*received, *sent) for node in (row.sender_node_id, row.recipient_node_id)])

    def view(row: MessageRow) -> DreamView:
        return DreamView(
            id=row.id, epoch=row.epoch, sender=refs.get(row.sender_node_id), recipient=refs.get(row.recipient_node_id), text=row.text, is_read=row.is_read
        )

    return DreamInbox(entity_id=entity_id, received=[view(row) for row in received], sent=[view(row) for row in sent])
