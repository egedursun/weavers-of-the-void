import asyncio
import logging
from collections.abc import Awaitable, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.tool_inputs import ERROR_EXCERPT
from aerona.core.account_scope import detached
from aerona.core.errors import AeronaError
from aerona.core.grammar import spoken
from aerona.db.ledger_capture import RowChange
from aerona.db.record_context import acting
from aerona.db.session import Database
from aerona.db.tables.lore import ChronicleRow
from aerona.db.write_guard import chosen_bonds
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.epoch import EpochPhase
from aerona.domain.enums.world import LoreLanguage
from aerona.domain.models.turn import LongJobTrace, PendingJob
from aerona.engine.context import Publisher, TickContext, TickEnvironment, phase_window
from aerona.engine.interconnect.tool_holds import tool_holds
from aerona.engine.stats import TickStats
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.agent import PendingLongJobContext, ToolFailureContext, ToolRejectionContext
from aerona.prompts.tools.results import CommonResult, result
from aerona.rules.registry import Rules
from aerona.tools.framework.call import CallEnvironment, ToolCall
from aerona.tools.framework.errors import RejectionError
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.ledger import ActionEntry, change_capture, record_action, summarize
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.framework.schema import describe_validation_error
from aerona.tools.framework.spec import LongJob, ToolSpec
from aerona.tools.framework.turn import load_turn, peek_turn

LOGGER = logging.getLogger(__name__)


def silent_publisher(_kind: Any, _payload: dict[str, Any]) -> None:
    return None


def refuse_restored(restored: list[str]) -> None:
    if restored:
        fields = ", ".join(sorted({words_of(key) for key in restored}))
        raise RejectionError(result(CommonResult.HELD_FAST, fields=fields))


def words_of(key: str) -> str:
    table, _, column = key.partition(".")
    return f"the {column.replace('_', ' ')} of {table.replace('_', ' ')}"


@dataclass(frozen=True)
class ToolResult:
    text: str
    is_error: bool


@dataclass(frozen=True)
class DoneAction:
    tool: str
    read_only: bool
    summary: str


@dataclass(frozen=True)
class ToolCatalogue:
    names: list[str] = field(default_factory=list)
    paid: list[str] = field(default_factory=list)
    free: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RuntimeSettings:
    rules: Rules
    epoch: int
    world_seed: int
    lore_language: LoreLanguage
    actor_node_id: int
    publish: Publisher = silent_publisher


@dataclass(frozen=True)
class GateRejection:
    text: str
    exhaust: bool


@dataclass(frozen=True)
class PendingLongJob:
    spec: ToolSpec[Any, Any]
    job: LongJob[Any, Any]
    summary: str
    changes: list[RowChange]


async def chronicle_marker(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.coalesce(func.max(ChronicleRow.id), 0))) or 0)


async def attribute_lines(session: AsyncSession, marker: int, son_id: int) -> None:
    await session.execute(update(ChronicleRow).where(ChronicleRow.id > marker, ChronicleRow.son_id.is_(None)).values(son_id=son_id))


def rejected(reason: str) -> ToolResult:
    return ToolResult(render(PromptId.TOOL_REJECTION, ToolRejectionContext(reason=reason)), True)


def failed(error: BaseException) -> ToolResult:
    return ToolResult(render(PromptId.TOOL_FAILURE_REFUND, ToolFailureContext(error=str(error)[:ERROR_EXCERPT])), True)


def catalogue_of(specs: Sequence[ToolSpec[Any, Any]], rules: Rules) -> ToolCatalogue:
    paid = [spec.name for spec in specs if spec.meta.actions(rules) > 0]
    free = [spec.name for spec in specs if spec.meta.actions(rules) == 0]
    return ToolCatalogue(names=[spec.name for spec in specs], paid=paid, free=free)


class ToolRuntime[CallT: ToolCall]:
    agent: AgentKind

    def __init__(self, database: Database, settings: RuntimeSettings, specs: Sequence[ToolSpec[CallT, Any]], ports: ToolPorts) -> None:
        self._database = database
        self.settings = settings
        self._specs = {spec.name: spec for spec in specs}
        self._order = [spec.name for spec in specs]
        self.ports = ports
        self._lock = asyncio.Lock()
        self._calls = 0
        self._done: list[DoneAction] = []
        self._jobs: list[asyncio.Task[ToolResult]] = []
        self._created: list[int] = []

    @property
    def rules(self) -> Rules:
        return self.settings.rules

    @property
    def specs(self) -> list[ToolSpec[CallT, Any]]:
        return [self._specs[name] for name in self._order]

    @property
    def done(self) -> Sequence[DoneAction]:
        return list(self._done)

    @property
    def created_entity_ids(self) -> Sequence[int]:
        return list(dict.fromkeys(self._created))

    @property
    def catalogue(self) -> ToolCatalogue:
        return catalogue_of(self.specs, self.rules)

    def has(self, name: str) -> bool:
        return name in self._specs

    async def settle_long_jobs(self) -> None:
        pending = [task for task in self._jobs if not task.done()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    async def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        spec = self._specs.get(name)
        if spec is None:
            return rejected(result(CommonResult.NOT_AVAILABLE, tool=name))
        try:
            parsed = spec.input_model.model_validate(arguments)
        except ValidationError as error:
            return rejected(describe_validation_error(spec.input_model, error, self.rules.son_tools.choice_hints))
        async with self._lock:
            self._calls += 1
            if spec.meta.read_only:
                return await self._guarded(self._read(spec, parsed))
            outcome = await self._guarded(self._write(spec, parsed))
        if isinstance(outcome, PendingLongJob):
            task = detached(self._complete_long_job(outcome))
            self._jobs.append(task)
            return await asyncio.shield(task)
        return outcome

    async def _guarded[R](self, work: Awaitable[R]) -> R | ToolResult:
        try:
            value = await work
        except RejectionError as rejection:
            return rejected(rejection.reason)
        except AeronaError as error:
            return rejected(error.message)
        except Exception as error:
            LOGGER.exception("tool call failed")
            return failed(error)
        return value

    @property
    def epoch_phase(self) -> EpochPhase:
        return EpochPhase.GODS if self.agent is AgentKind.SON else EpochPhase.MORTALS

    def _tick(self, session: AsyncSession, spec: ToolSpec[CallT, Any]) -> TickContext:
        settings = self.settings
        environment = TickEnvironment(
            rules=settings.rules,
            epoch=settings.epoch,
            world_seed=settings.world_seed,
            lore_language=settings.lore_language,
            publish=settings.publish,
            stats=TickStats(),
            window=phase_window(settings.rules, self.epoch_phase),
            progress=1 - 1 / (self._calls + 2),
            phase=self.epoch_phase,
        )
        return TickContext(environment, session, f"tool.{spoken(self.agent)}.{settings.actor_node_id}.{self._calls}.{spec.name}")

    async def _environment(self, session: AsyncSession, spec: ToolSpec[CallT, Any], writable: bool) -> CallEnvironment:
        loader = load_turn if writable else peek_turn
        turn = await loader(session, self.settings.actor_node_id, self.agent, self.settings.epoch)
        return CallEnvironment(session, self.rules, self._tick(session, spec), turn, self.ports, spec.name)

    async def build_call(self, environment: CallEnvironment) -> CallT:
        raise NotImplementedError

    async def gate(self, call: CallT, spec: ToolSpec[CallT, Any]) -> GateRejection | None:
        raise NotImplementedError

    def precheck(self, call: CallT, spec: ToolSpec[CallT, Any]) -> None:
        raise NotImplementedError

    def epilogue(self, call: CallT, text: str) -> str:
        raise NotImplementedError

    async def attribute_chronicle(self, call: CallT, marker: int) -> None:
        return None

    async def _read(self, spec: ToolSpec[CallT, Any], parsed: ToolInput) -> ToolResult:
        async with self._database.read() as session:
            call = await self.build_call(await self._environment(session, spec, writable=False))
            async with tool_holds(session, self.settings.epoch, spec.name):
                outcome = await spec.handler(call, parsed)
            await session.rollback()
        text = outcome if isinstance(outcome, str) else ""
        self._done.append(DoneAction(spec.name, True, text))
        return ToolResult(text, False)

    async def _write(self, spec: ToolSpec[CallT, Any], parsed: ToolInput) -> ToolResult | PendingLongJob:
        async with self._database.write() as session:
            call = await self.build_call(await self._environment(session, spec, writable=True))
            with acting(call.actor_kind, call.actor_id, call.epoch, key=f"actor.{spec.name}"):
                blocked = await self.gate(call, spec)
                if blocked is not None:
                    if blocked.exhaust:
                        call.turn.exhaust()
                    await session.flush()
                    return ToolResult(blocked.text, True)
                self.precheck(call, spec)
                self._check_long_job(call, spec)
                marker = await chronicle_marker(session)
                recorder = change_capture(session)
                try:
                    with chosen_bonds():
                        async with tool_holds(session, self.settings.epoch, spec.name) as restored:
                            outcome = await spec.handler(call, parsed)
                            await session.flush()
                    refuse_restored(restored)
                    if isinstance(outcome, LongJob):
                        call.turn.set_pending_job(PendingJob(kind=outcome.kind, essence=outcome.essence, action_points=outcome.action_points, epoch=call.epoch))
                        await session.flush()
                        return PendingLongJob(spec, outcome, summarize(parsed.model_dump(mode="json", exclude_none=True)), await recorder.changes())
                    if call.log.actions_charged is None:
                        call.charge_actions(spec.meta.actions(self.rules))
                    await self.attribute_chronicle(call, marker)
                    await session.flush()
                finally:
                    recorder.stop()
                text = self.epilogue(call, outcome)
                await self._record(call, spec, summarize(parsed.model_dump(mode="json", exclude_none=True)), text, await recorder.changes())
                await session.flush()
                return ToolResult(text, False)

    def _check_long_job(self, call: CallT, spec: ToolSpec[CallT, Any]) -> None:
        if spec.meta.long_job is None:
            return
        running = any(not task.done() for task in self._jobs)
        if running or call.turn.context.pending_job is not None:
            pending = call.turn.context.pending_job
            raise RejectionError(render(PromptId.PENDING_LONG_JOB, PendingLongJobContext(job=pending.kind if pending else spec.meta.long_job)))

    async def _record(self, call: CallT, spec: ToolSpec[CallT, Any], summary: str, text: str, changes: list[RowChange]) -> None:
        entry = ActionEntry(
            epoch=call.epoch,
            actor_kind=call.actor_kind,
            actor_node_id=call.actor_id,
            actor_name=call.actor_name,
            tool=spec.name,
            action_kind=spec.meta.action_kind,
            summary=summary,
            target_node_id=call.log.target_node_id,
            essence_spent=call.log.essence_spent,
            detail=text,
        )
        await record_action(call.session, entry, changes)
        self._created.extend(call.turn.context.created_entity_ids)
        self._done.append(DoneAction(spec.name, False, text))

    async def _complete_long_job(self, pending: PendingLongJob) -> ToolResult:
        try:
            value = await pending.job.run()
        except Exception as error:
            LOGGER.exception("long tool job failed")
            return await self._refund(pending, error)
        try:
            return await self._finish_long_job(pending, value)
        except RejectionError as rejection:
            return await self._refund(pending, rejection)
        except Exception as error:
            LOGGER.exception("long tool job could not be finished")
            return await self._refund(pending, error)

    async def _finish_long_job(self, pending: PendingLongJob, value: Any) -> ToolResult:
        spec = pending.spec
        async with self._database.write() as session:
            call = await self.build_call(await self._environment(session, spec, writable=True))
            with acting(call.actor_kind, call.actor_id, call.epoch, key=f"actor.{spec.name}"):
                call.turn.set_pending_job(None)
                recorder = change_capture(session)
                try:
                    with chosen_bonds():
                        async with tool_holds(session, self.settings.epoch, spec.name) as restored:
                            body = await pending.job.finish(call, value)
                            await session.flush()
                    refuse_restored(restored)
                finally:
                    recorder.stop()
                call.turn.add_long_job_trace(LongJobTrace(tool=spec.name, key=pending.job.trace_key(value), summary=body))
                call.log.essence_spent = pending.job.essence
                text = self.epilogue(call, body)
                await self._record(call, spec, pending.summary, text, [*pending.changes, *await recorder.changes()])
                await session.flush()
        return ToolResult(text, False)

    async def refund_essence(self, call: CallT, amount: int) -> None:
        return None

    async def _refund(self, pending: PendingLongJob, error: BaseException) -> ToolResult:
        async with self._database.write() as session:
            call = await self.build_call(await self._environment(session, pending.spec, writable=True))
            call.turn.set_pending_job(None)
            call.turn.refund(pending.job.action_points)
            await self.refund_essence(call, pending.job.essence)
            await session.flush()
        return rejected(result(CommonResult.LONG_JOB_FAILED, label=pending.job.label, error=str(error)[:ERROR_EXCERPT]))
