import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from claude_agent_sdk import CLIConnectionError, ProcessError

from aerona.agents.ports import LanguageModel, Publish
from aerona.agents.turns.ports import DoneAction, TurnToolkit
from aerona.constants.agents import ERROR_REASON_CHARS
from aerona.domain.enums.node import ActorKind
from aerona.events.kinds import EventKind
from aerona.llm.errors import LlmError, LlmTimeoutError, LlmTransientError
from aerona.llm.stream import StreamActor, current_actor
from aerona.prompts.contexts.son_turn import DoneAction as PromptDoneAction
from aerona.prompts.contexts.son_turn import TurnInterruption
from aerona.rules.registry.model import ModelRules

LOGGER = logging.getLogger(__name__)
STEP_LIMIT_REASONS = frozenset({"error_max_turns", "max_turns"})


class SessionStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    STEP_LIMIT = "step_limit"
    ENDED = "ended"


class TurnFailedError(LlmError):
    pass


Continuation = Callable[[TurnInterruption, str | None, list[PromptDoneAction]], Awaitable[str | None]]


@dataclass(frozen=True)
class TurnPlan:
    label: str
    actor: str
    actor_kind: ActorKind
    actor_id: int
    system_prompt: str
    prompt: str
    max_turns: int
    timeout: int
    continuation: Continuation
    is_complete: Callable[[str], bool]


@dataclass
class SessionResult:
    text: str = ""
    status: SessionStatus = SessionStatus.ENDED
    error: str | None = None
    transient: bool = True


@dataclass
class TurnOutcome:
    text: str
    status: SessionStatus
    done: list[DoneAction] = field(default_factory=list)
    sessions: int = 0

    @property
    def world_changed(self) -> bool:
        return any(not action.read_only for action in self.done)


INTERRUPTIONS = {
    SessionStatus.ERROR: TurnInterruption.CONNECTION_ERROR,
    SessionStatus.TIMEOUT: TurnInterruption.TIMEOUT,
    SessionStatus.STEP_LIMIT: TurnInterruption.STEP_LIMIT,
    SessionStatus.SUCCESS: TurnInterruption.NO_FINAL_WORD,
    SessionStatus.ENDED: TurnInterruption.NO_FINAL_WORD,
}


async def one_session(model: LanguageModel, plan: TurnPlan, prompt: str, toolkit: TurnToolkit) -> SessionResult:
    token = current_actor.set(StreamActor(plan.actor_kind, plan.actor_id, plan.actor, toolkit.read_only_tools))
    try:
        run = await model.run_agent(plan.label, plan.system_prompt, prompt, tools=toolkit.tools(), max_turns=plan.max_turns, timeout_seconds=plan.timeout)
    except LlmTimeoutError as error:
        return SessionResult(status=SessionStatus.TIMEOUT, error=str(error))
    except (LlmTransientError, CLIConnectionError, ProcessError) as error:
        return SessionResult(status=SessionStatus.ERROR, error=str(error))
    except LlmError as error:
        return SessionResult(status=SessionStatus.ERROR, error=str(error), transient=False)
    finally:
        current_actor.reset(token)
    if run.completed:
        return SessionResult(text=run.text, status=SessionStatus.SUCCESS)
    if run.stop_reason in STEP_LIMIT_REASONS:
        return SessionResult(text=run.text, status=SessionStatus.STEP_LIMIT)
    return SessionResult(text=run.text, status=SessionStatus.ENDED, error=run.stop_reason)


def prompt_actions(done: Sequence[DoneAction], summary_chars: int) -> list[PromptDoneAction]:
    return [PromptDoneAction(tool=action.tool, summary=action.summary[:summary_chars]) for action in done if not action.read_only]


async def run_turn(model: LanguageModel, plan: TurnPlan, toolkit: TurnToolkit, rules: ModelRules, publish: Publish) -> TurnOutcome:
    restarts = 0
    continuations = 0
    prompt = plan.prompt
    result = SessionResult()
    sessions = 0
    for _ in range(rules.sessions_per_turn_cap):
        sessions += 1
        result = await one_session(model, plan, prompt, toolkit)
        await toolkit.settle_long_jobs()
        done = list(toolkit.done)
        if result.status is SessionStatus.SUCCESS and plan.is_complete(result.text):
            return TurnOutcome(result.text, result.status, done, sessions)
        changed = any(not action.read_only for action in done)
        if result.status is SessionStatus.ERROR and not result.transient:
            break
        reason = (result.error or "")[:ERROR_REASON_CHARS]
        if not changed and result.status is SessionStatus.ERROR and restarts < rules.restart_attempts:
            restarts += 1
            wait = rules.restart_wait * restarts
            publish(
                EventKind.AGENT_RETRY,
                {
                    "actor": plan.actor,
                    "kind": "restart",
                    "attempt": restarts + 1,
                    "total": rules.restart_attempts + 1,
                    "reason": reason,
                    "wait_s": wait,
                    "kept_steps": 0,
                },
            )
            await asyncio.sleep(wait)
            continue
        if continuations >= rules.max_continuations:
            break
        actions = prompt_actions(done, rules.continuation_action_summary_chars)
        following = await plan.continuation(INTERRUPTIONS[result.status], reason or None, actions)
        if following is None:
            break
        continuations += 1
        pause = rules.continuation_wait if result.status is SessionStatus.ERROR else 0
        publish(
            EventKind.AGENT_RETRY,
            {
                "actor": plan.actor,
                "kind": "continuation",
                "attempt": continuations,
                "total": rules.max_continuations,
                "reason": reason,
                "wait_s": pause,
                "kept_steps": len(actions),
            },
        )
        if pause:
            await asyncio.sleep(pause)
        prompt = following
    done = list(toolkit.done)
    outcome = TurnOutcome(result.text, result.status, done, sessions)
    if result.status is not SessionStatus.SUCCESS:
        detail = f": {result.error}" if result.error else ""
        LOGGER.warning(
            "Turn of %s ended half-done (%s%s) after %s session(s); step limit %s", plan.actor, result.status.value, detail, sessions, plan.max_turns
        )
    if result.status is not SessionStatus.SUCCESS and not outcome.world_changed:
        raise TurnFailedError(result.error or f"The turn ended without leaving a trace ({result.status}).")
    return outcome
