from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import wraps

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.schema import LEDGER_SUMMARY_MAX_LENGTH
from aerona.core.errors import ValidationFailedError
from aerona.db.ledger_capture import LedgerDraft
from aerona.db.record_context import acting
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.write_guard import chosen_bonds
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.node import ActorKind
from aerona.engine.context import Publisher, TickContext
from aerona.engine.primitives.manual import manual_context, silent
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.services.ledger import compact_entry, summarize_inputs
from aerona.services.player.journal import RowJournal
from aerona.services.player.ports import ActionLedger


class Command(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class ActionOutcome(BaseModel):
    action: str
    message: str
    essence_spent: int = 0
    essence_gained: int = 0
    target_node_id: int | None = None
    created_ids: list[int] = []
    ledger_entry_id: int | None = None
    values: dict[str, int | float | str | bool | None] = {}


@dataclass(frozen=True)
class Effect:
    message: str
    target_node_id: int | None = None
    essence_spent: int = 0
    essence_gained: int = 0
    created_ids: tuple[int, ...] = ()
    kind: ActionKind | None = None
    tool: str | None = None
    values: dict[str, int | float | str | bool | None] = field(default_factory=dict)


@dataclass
class PlayerScope:
    session: AsyncSession
    rules: Rules
    publish: Publisher = silent
    ledger: ActionLedger = field(default_factory=RowJournal)

    async def context(self, action: str) -> TickContext:
        return await manual_context(self.session, action, self.rules, self.publish)

    async def cosmos(self) -> CosmosRow:
        return await CosmosRepository(self.session).require_cosmos()

    async def creator(self) -> CreatorRow:
        return await CosmosRepository(self.session).require_creator()

    async def epoch(self) -> int:
        return (await self.cosmos()).epoch


async def _last_action_id(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.max(ActionRecordRow.id))) or 0)


def refusal(error: IntegrityError) -> str:
    reason = str(error.orig)
    if "FOREIGN KEY" in reason:
        return "That change points at something that does not exist."
    if "UNIQUE" in reason:
        return "That change would make a second copy of something that can exist only once."
    if "NOT NULL" in reason:
        return "That change leaves a value empty that cannot be empty."
    return "That change takes a value outside what the record allows."


async def perform(scope: PlayerScope, action: str, kind: ActionKind, command: BaseModel, body: Callable[[], Awaitable[Effect]]) -> ActionOutcome:
    session = scope.session
    try:
        async with session.begin_nested(), scope.ledger.capture(session) as capture:
            marker = await _last_action_id(session)
            acting_creator = await scope.creator()
            essence_before = acting_creator.essence
            with chosen_bonds(), acting(ActorKind.CREATOR, acting_creator.id, await scope.epoch(), key=f"actor.{action}"):
                effect = await body()
            creator = await scope.creator()
            delta = creator.essence - essence_before
            spent = effect.essence_spent or max(0, -delta)
            gained = effect.essence_gained or max(0, delta + spent)
            epoch = await scope.epoch()
            recorded_kind = effect.kind or kind
            if await _last_action_id(session) == marker:
                session.add(
                    ActionRecordRow(
                        epoch=epoch,
                        actor_kind=ActorKind.CREATOR,
                        actor_node_id=creator.id,
                        kind=recorded_kind,
                        target_node_id=effect.target_node_id,
                        essence_spent=spent,
                        summary=effect.message[:LEDGER_SUMMARY_MAX_LENGTH] or None,
                    )
                )
                await session.flush()
            draft = LedgerDraft(
                epoch=epoch,
                actor_kind=ActorKind.CREATOR,
                actor_node_id=creator.id,
                actor_name=creator.name,
                tool=effect.tool or action,
                action_kind=recorded_kind,
                input_summary=summarize_inputs(command.model_dump(mode="json")) or effect.message[:LEDGER_SUMMARY_MAX_LENGTH],
            )
            entry_id = await capture.seal(draft)
            if entry_id is not None:
                await compact_entry(session, entry_id)
    except IntegrityError as error:
        raise ValidationFailedError(refusal(error)) from error
    outcome = ActionOutcome(
        action=action,
        message=effect.message,
        essence_spent=spent,
        essence_gained=gained,
        target_node_id=effect.target_node_id,
        created_ids=list(effect.created_ids),
        ledger_entry_id=entry_id,
        values=dict(effect.values),
    )
    scope.publish(EventKind.WORLD_CHANGED, {"action": action, "target_node_id": effect.target_node_id, "ledger_entry_id": entry_id})
    return outcome


type Body[C] = Callable[[PlayerScope, C], Awaitable[Effect]]
type Handler[C] = Callable[[PlayerScope, C], Awaitable[ActionOutcome]]


def player_action[C: BaseModel](action: str, kind: ActionKind) -> Callable[[Body[C]], Handler[C]]:
    def decorate(body: Body[C]) -> Handler[C]:
        @wraps(body)
        async def handler(scope: PlayerScope, command: C) -> ActionOutcome:
            return await perform(scope, action, kind, command, lambda: body(scope, command))

        return handler

    return decorate
