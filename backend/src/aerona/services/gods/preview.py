import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.mortal import StartedMortalTurn, mortal_prompts
from aerona.agents.runtime import AgentRuntime
from aerona.agents.tool_ports import agent_tool_ports
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.agency import AgentTurnRow, TurnCounterRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import MessageIntent, TurnCounter
from aerona.engine.gods.mortal_opportunities import mortal_opportunities
from aerona.engine.gods.opportunities import creator_hints, son_opportunities
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.opportunities import (
    CreatorHintKind,
    CreatorOpportunitiesContext,
    MortalOpportunitiesContext,
    OpportunityLine,
    SonOpportunitiesContext,
    ordered_lines,
)
from aerona.rules.registry import Rules
from aerona.services.gods.context import require
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.framework.runtime import ToolCatalogue
from aerona.tools.preview import ToolAvailability, mortal_tool_availability, son_tool_availability


@dataclass(frozen=True)
class RenderedLine:
    kind: str
    text: str
    tension: bool
    tools: list[str]


@dataclass(frozen=True)
class RenderedHint:
    kind: CreatorHintKind
    text: str


@dataclass(frozen=True)
class TurnCounterReading:
    counter: TurnCounter
    value: int


@dataclass(frozen=True)
class SonToolsReading:
    son: SonRow
    epoch: int
    action_points_left: int | None
    availability: ToolAvailability
    counters: list[TurnCounterReading]


@dataclass(frozen=True)
class MortalContextReading:
    entity: EntityRow
    epoch: int
    action_points: int
    system_prompt: str
    user_prompt: str
    availability: ToolAvailability
    counters: list[TurnCounterReading]


def tools_in(text: str, names: list[str]) -> list[str]:
    return [name for name in names if re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text)]


def _clean(rendered: str) -> str:
    return rendered.strip().removeprefix("- ").strip()


async def _counters(session: AsyncSession, node_id: int, epoch: int) -> list[TurnCounterReading]:
    rows = await session.scalars(
        select(TurnCounterRow).where(TurnCounterRow.agent_node_id == node_id, TurnCounterRow.epoch == epoch).order_by(TurnCounterRow.counter)
    )
    return [TurnCounterReading(row.counter, row.value) for row in rows]


async def _points(session: AsyncSession, node_id: int, epoch: int) -> int | None:
    turn = await session.get(AgentTurnRow, node_id)
    return turn.action_points_left if turn is not None and turn.epoch == epoch else None


def _shown(line: OpportunityLine, rendered: str, names: list[str]) -> RenderedLine | None:
    text = _clean(rendered)
    if not text:
        return None
    return RenderedLine(getattr(line, "kind", ""), text, line.tension, tools_in(text, names))


async def son_opportunity_lines(session: AsyncSession, rules: Rules, ports: ToolPorts, son_id: int) -> list[RenderedLine]:
    son = require(await session.get(SonRow, son_id), "son")
    epoch = (await CosmosRepository(session).require_cosmos()).epoch
    names = [tool.name for tool in (await son_tool_availability(session, rules, son, ports)).available]
    shown: list[RenderedLine] = []
    for line in ordered_lines(await son_opportunities(session, rules, son, epoch), rules.opportunities.tension_first > 0):
        context = SonOpportunitiesContext(rules=rules, lines=[line], available_tools=names or None)
        item = _shown(line, render(PromptId.SON_OPPORTUNITIES, context), names)
        if item is not None:
            shown.append(item)
    return shown


async def mortal_opportunity_lines(session: AsyncSession, rules: Rules, ports: ToolPorts, entity_id: int) -> list[RenderedLine]:
    entity = require(await session.get(EntityRow, entity_id), "record")
    names = [tool.name for tool in (await mortal_tool_availability(session, rules, entity, ports)).available]
    shown: list[RenderedLine] = []
    for line in ordered_lines(await mortal_opportunities(session, rules, entity), rules.opportunities.tension_first > 0):
        context = MortalOpportunitiesContext(rules=rules, lines=[line], available_tools=names or None)
        item = _shown(line, render(PromptId.MORTAL_OPPORTUNITIES, context), names)
        if item is not None:
            shown.append(item)
    return shown


async def creator_hint_lines(session: AsyncSession, rules: Rules) -> list[RenderedHint]:
    epoch = (await CosmosRepository(session).require_cosmos()).epoch
    hints = await creator_hints(session, rules, epoch)
    base = CreatorOpportunitiesContext(
        rules=rules,
        unanswered_prayers=hints.unanswered_prayers,
        unclaimed_count=len(hints.unclaimed),
        unclaimed_examples=list(hints.unclaimed[: rules.opportunities.list_narrow]),
        rebel_sons=list(hints.rebel_sons),
        fading_sons=list(hints.fading_sons),
        doom=hints.doom,
        doom_threshold=hints.doom_threshold,
        godless_worlds=list(hints.godless_worlds),
        stale_threads=hints.stale_threads,
        essence=hints.essence,
    )
    found: list[RenderedHint] = []
    for kind in CreatorHintKind:
        text = _clean(render(PromptId.CREATOR_OPPORTUNITIES, base.model_copy(update={"only": kind})))
        if text:
            found.append(RenderedHint(kind, text))
    return found


async def son_tools_reading(session: AsyncSession, rules: Rules, ports: ToolPorts, son_id: int) -> SonToolsReading:
    son = require(await session.get(SonRow, son_id), "son")
    epoch = (await CosmosRepository(session).require_cosmos()).epoch
    return SonToolsReading(
        son, epoch, await _points(session, son.id, epoch), await son_tool_availability(session, rules, son, ports), await _counters(session, son.id, epoch)
    )


async def mortal_context_reading(session: AsyncSession, runtime: AgentRuntime, rules: Rules, entity_id: int) -> MortalContextReading:
    entity = require(await session.get(EntityRow, entity_id), "record")
    epoch = (await CosmosRepository(session).require_cosmos()).epoch
    ports = agent_tool_ports(runtime)
    availability = await mortal_tool_availability(session, rules, entity, ports)
    unread = list(
        await session.scalars(
            select(MessageRow.id)
            .where(MessageRow.recipient_node_id == entity.id, MessageRow.intent == MessageIntent.DREAM, MessageRow.is_read.is_(False))
            .order_by(MessageRow.id)
        )
    )
    points = await _points(session, entity.id, epoch)
    action_points = points if points is not None else rules.mortal_agents.action_points
    started = StartedMortalTurn(entity.id, entity.name, epoch, False, action_points, unread)
    catalogue = ToolCatalogue(
        names=[tool.name for tool in availability.available],
        paid=[tool.name for tool in availability.available if tool.action_cost > 0],
        free=[tool.name for tool in availability.available if tool.action_cost == 0],
    )
    system, user = await mortal_prompts(runtime, started, catalogue)
    return MortalContextReading(entity, epoch, action_points, system, user, availability, await _counters(session, entity.id, epoch))


async def dream_messages(session: AsyncSession, entity_id: int, limit: int) -> tuple[list[MessageRow], list[MessageRow]]:
    require(await session.get(EntityRow, entity_id), "record")
    base = select(MessageRow).where(MessageRow.intent == MessageIntent.DREAM)
    received = list(await session.scalars(base.where(MessageRow.recipient_node_id == entity_id).order_by(MessageRow.id.desc()).limit(limit)))
    sent = list(await session.scalars(base.where(MessageRow.sender_node_id == entity_id).order_by(MessageRow.id.desc()).limit(limit)))
    return received, sent
