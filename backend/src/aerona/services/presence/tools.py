import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import SdkMcpTool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.son import turn_points
from aerona.agents.turns.state import begin_turn, turn_row
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.presence import PresenceRecord, SpeakerGroup
from aerona.domain.enums.son import SonStatus
from aerona.rules.registry import Rules
from aerona.services.presence.speakers import Speaker
from aerona.tools.toolkit import Toolkits, TurnToolkit

ACTING_GROUPS = frozenset({SpeakerGroup.SONS, SpeakerGroup.MORTALS, SpeakerGroup.SPIRITS, SpeakerGroup.BEASTS})
READING_GROUPS = frozenset({*ACTING_GROUPS, SpeakerGroup.BEINGS})

Opener = Callable[[], Awaitable[int]]


@dataclass
class SpeakerTools:
    toolkit: TurnToolkit | None
    acting: bool
    points: int
    paused: bool = False
    opener: Opener | None = None
    opened: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def read_only(self) -> frozenset[str]:
        return self.toolkit.read_only_tools if self.toolkit is not None else frozenset()

    @property
    def names(self) -> list[str]:
        return list(self.toolkit.catalogue.names) if self.toolkit is not None else []

    async def open_turn(self) -> None:
        async with self.lock:
            if self.opened or self.opener is None:
                return
            self.points = await self.opener()
            self.opened = True

    def tools(self) -> list[SdkMcpTool[Any]]:
        if self.toolkit is None:
            return []
        return [self.wrapped(tool) for tool in self.toolkit.tools()]

    def wrapped(self, tool: SdkMcpTool[Any]) -> SdkMcpTool[Any]:
        if tool.name in self.read_only:
            return tool
        inner = tool.handler

        async def handler(arguments: dict[str, Any]) -> dict[str, Any]:
            await self.open_turn()
            return await inner(arguments)

        return SdkMcpTool(name=tool.name, description=tool.description, input_schema=tool.input_schema, handler=handler)


def agent_kind(speaker: Speaker) -> AgentKind:
    return AgentKind.SON if isinstance(speaker.node, SonRow) else AgentKind.MORTAL


def may_act(speaker: Speaker, record: PresenceRecord, world_busy: bool) -> bool:
    if record is not PresenceRecord.ON_RECORD or speaker.dead or world_busy or speaker.group not in ACTING_GROUPS:
        return False
    node = speaker.node
    if isinstance(node, SonRow):
        return node.status is SonStatus.ACTIVE
    return isinstance(node, EntityRow) and node.status is EntityStatus.CANON


async def fresh_points(session: AsyncSession, rules: Rules, speaker: Speaker, epoch: int) -> int | None:
    node = speaker.node
    if isinstance(node, SonRow):
        if node.chained or node.last_acted_epoch >= epoch:
            return None
        powers = list(await session.scalars(select(SonPowerRow).where(SonPowerRow.son_id == node.id).order_by(SonPowerRow.slot)))
        return turn_points(rules, node, powers)
    if isinstance(node, EntityRow) and node.last_acted_epoch < epoch:
        return rules.mortal_agents.action_points
    return None


async def points_left(session: AsyncSession, rules: Rules, speaker: Speaker, epoch: int) -> int:
    row = await turn_row(session, speaker.node_id)
    if row is not None and row.epoch == epoch:
        return row.action_points_left or 0
    return await fresh_points(session, rules, speaker, epoch) or 0


async def join_turn(session: AsyncSession, rules: Rules, speaker: Speaker, epoch: int) -> int:
    row = await turn_row(session, speaker.node_id)
    if row is not None and row.epoch == epoch:
        return row.action_points_left or 0
    fresh = await fresh_points(session, rules, speaker, epoch)
    if fresh is None:
        return 0
    started = await begin_turn(session, speaker.node_id, agent_kind(speaker), epoch, fresh)
    return started.action_points


async def speaker_tools(
    database: Database, toolkits: Toolkits | None, rules: Rules, speaker: Speaker, *, record: PresenceRecord, epoch: int, world_busy: bool
) -> SpeakerTools:
    if toolkits is None or speaker.group not in READING_GROUPS:
        return SpeakerTools(None, acting=False, points=0, paused=world_busy)
    acting = may_act(speaker, record, world_busy)
    toolkit = await toolkits.speaker_toolkit(speaker.node_id, epoch, acting=acting)
    if not acting:
        return SpeakerTools(toolkit, acting=False, points=0, paused=world_busy)
    async with database.read() as session:
        points = await points_left(session, rules, speaker, epoch)

    async def opener() -> int:
        async with database.write() as session:
            refreshed = await session.get(type(speaker.node), speaker.node_id)
            current = Speaker(refreshed, speaker.group, speaker.dead) if isinstance(refreshed, SonRow | EntityRow) else speaker
            return await join_turn(session, rules, current, epoch)

    return SpeakerTools(toolkit, acting=True, points=points, opener=opener)
