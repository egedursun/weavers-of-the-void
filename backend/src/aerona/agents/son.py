from dataclasses import dataclass, field

from sqlalchemy import select, update

from aerona.agents.chronicle import ChroniclePhase, record_line
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.son_turn import son_system_context, son_user_context
from aerona.agents.metrics import metrics_turn
from aerona.agents.roles import AgentRole, turn_label
from aerona.agents.runtime import AgentRuntime
from aerona.agents.son_state import action_points, max_turns
from aerona.agents.text import extract_word
from aerona.agents.turns.long_jobs import resolve_orphaned_jobs, resolve_pending_job
from aerona.agents.turns.ports import SpeechOnlyToolkit, ToolCatalogue, TurnToolkit
from aerona.agents.turns.session import TurnOutcome, TurnPlan, run_turn
from aerona.agents.turns.state import begin_turn, finish_turn, long_job_notes, turn_row
from aerona.constants.agents import WORD_CHRONICLE_CHARS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import SonStatus
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.son_turn import DoneAction, TurnContinuationContext, TurnInterruption
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class SonTurnResult:
    son_id: int
    son_name: str
    word: str
    creations: list[int] = field(default_factory=list)
    status: str = ""
    resumed: bool = False


@dataclass(frozen=True)
class StartedTurn:
    son_id: int
    son_name: str
    epoch: int
    resumed: bool
    action_points: int
    max_turns: int
    unread: list[int]
    rarity: Rarity


@dataclass(frozen=True)
class PreparedTurn:
    started: StartedTurn
    system_prompt: str
    prompt: str


def check_preconditions(son: SonRow | None, epoch: int) -> SonRow:
    if son is None:
        raise NotFoundError("No such son.")
    if son.status is not SonStatus.ACTIVE:
        raise ValidationFailedError(f"{son.name} is {spoken(son.status)}; cannot act.")
    if son.chained:
        raise ValidationFailedError(f"{son.name} is chained this epoch.")
    if son.last_acted_epoch >= epoch:
        raise ValidationFailedError(f"{son.name} has already acted this epoch.")
    return son


def turn_points(rules: Rules, son: SonRow, powers: list[SonPowerRow]) -> int:
    points = action_points(rules, son, powers)
    if son.sanity is not None and son.sanity < rules.cosmic_horror.son_madness_threshold:
        points = max(0, points - rules.agents.mad_son_action_loss)
    return points


async def unread_messages(scope: Scope, son_id: int) -> list[int]:
    statement = select(MessageRow.id).where(MessageRow.recipient_node_id == son_id, MessageRow.is_read.is_(False))
    return list(await scope.session.scalars(statement))


async def start_turn(runtime: AgentRuntime, son_id: int) -> StartedTurn:
    async with runtime.database.write() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        await resolve_orphaned_jobs(session, rules, scope.epoch)
        son = check_preconditions(await session.get(SonRow, son_id), scope.epoch)
        powers = list(await session.scalars(select(SonPowerRow).where(SonPowerRow.son_id == son.id)))
        start = await begin_turn(session, son.id, AgentKind.SON, scope.epoch, turn_points(rules, son, powers))
        if not start.resumed and start.action_points <= 0:
            raise ValidationFailedError(f"{son.name} is being forgotten; has no strength to act.")
        points = start.action_points
        if start.resumed:
            row = await turn_row(session, son.id)
            if row is not None:
                await resolve_pending_job(session, rules, son, row, scope.epoch)
                points = row.action_points_left if row.action_points_left is not None else points
        unread = await unread_messages(scope, son.id)
        return StartedTurn(son.id, son.name, scope.epoch, start.resumed, points, max_turns(rules, son), unread, son.rarity)


async def prepare_prompts(runtime: AgentRuntime, started: StartedTurn, catalogue: ToolCatalogue) -> PreparedTurn:
    async with runtime.database.read() as session:
        scope = await load_scope(session, await runtime.rules(session))
        son = await session.get(SonRow, started.son_id)
        if son is None:
            raise NotFoundError("No such son.")
        system = render(PromptId.SON_TURN_SYSTEM, await son_system_context(scope, son, started.action_points, catalogue))
        prompt = render(PromptId.SON_TURN_USER, await son_user_context(scope, son, started.action_points, catalogue, resumed=started.resumed))
        return PreparedTurn(started, system, prompt)


async def continuation_prompt(
    runtime: AgentRuntime, son_id: int, catalogue: ToolCatalogue, reason: TurnInterruption, *, detail: str | None, done: list[DoneAction]
) -> str | None:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        son = await session.get(SonRow, son_id)
        if son is None or son.status is not SonStatus.ACTIVE:
            return None
        row = await turn_row(session, son_id)
        points = row.action_points_left if row is not None and row.action_points_left is not None else 0
        jobs = await long_job_notes(session, son_id, rules.model.continuation_action_summary_chars)
        note = render(PromptId.SON_TURN_CONTINUATION, TurnContinuationContext(reason=reason, error_detail=detail, done=done, long_jobs=jobs))
        return render(PromptId.SON_TURN_USER, await son_user_context(scope, son, points, catalogue, resumed=True, continuation=note))


async def finish_son_turn(runtime: AgentRuntime, started: StartedTurn, outcome: TurnOutcome, creations: list[int]) -> SonTurnResult:
    word = extract_word(outcome.text)
    async with runtime.database.write() as session:
        rules = await runtime.rules(session)
        son = await session.get(SonRow, started.son_id)
        if son is None:
            raise NotFoundError("No such son.")
        epoch = started.epoch
        son.last_acted_epoch = epoch
        son.standing_order = None
        son.order_absolute = False
        await finish_turn(session, son.id)
        if started.unread:
            await session.execute(update(MessageRow).where(MessageRow.id.in_(started.unread)).values(is_read=True))
        if word:
            await record_line(
                session,
                rules,
                "son.word",
                roles={IncidentRole.ACTOR: son.id, IncidentRole.PRODUCT: list(creations)},
                facts={"words": word[:WORD_CHRONICLE_CHARS]},
                phase=ChroniclePhase.GODS,
                kind=ChronicleKind.SPEECH,
                son_id=son.id,
            )
    return SonTurnResult(started.son_id, started.son_name, word, creations, outcome.status.value, started.resumed)


async def son_toolkit(runtime: AgentRuntime, started: StartedTurn) -> TurnToolkit:
    if runtime.toolkits is None:
        return SpeechOnlyToolkit()
    return await runtime.toolkits.son_toolkit(started.son_id, started.epoch, started.action_points)


async def run_son_turn(runtime: AgentRuntime, son_id: int) -> SonTurnResult:
    runtime.require_llm("son turn")
    started = await start_turn(runtime, son_id)
    toolkit = await son_toolkit(runtime, started)
    catalogue = toolkit.catalogue
    prepared = await prepare_prompts(runtime, started, catalogue)
    rules = await runtime.current_rules()
    runtime.publish(
        EventKind.SON_TURN_STARTED,
        {"son_id": son_id, "son_name": started.son_name, "resumed": started.resumed, "model": runtime.world_model, "rarity": started.rarity.value},
    )

    async def follow_up(reason: TurnInterruption, detail: str | None, done: list[DoneAction]) -> str | None:
        return await continuation_prompt(runtime, son_id, catalogue, reason, detail=detail, done=done)

    plan = TurnPlan(
        label=turn_label(AgentRole.SON_TURN, started.son_name),
        actor=started.son_name,
        actor_kind=ActorKind.SON,
        actor_id=son_id,
        system_prompt=prepared.system_prompt,
        prompt=prepared.prompt,
        max_turns=started.max_turns,
        timeout=rules.fate.son_turn_timeout,
        continuation=follow_up,
        is_complete=lambda text: bool(extract_word(text)),
    )
    try:
        with metrics_turn(started.epoch, started.action_points):
            outcome = await run_turn(runtime.model, plan, toolkit, rules.model, runtime.publish)
    finally:
        await toolkit.settle_long_jobs()
    result = await finish_son_turn(runtime, started, outcome, list(toolkit.created_entity_ids))
    runtime.publish(
        EventKind.SON_TURN_FINISHED,
        {
            "son_id": son_id,
            "son_name": result.son_name,
            "word": result.word,
            "creations": result.creations,
            "status": result.status,
            "model": runtime.world_model,
            "rarity": started.rarity.value,
        },
    )
    return result
