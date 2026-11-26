import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from weakref import WeakKeyDictionary

from sqlalchemy import select

from aerona.agents.ask import ask
from aerona.agents.ports import LanguageModel
from aerona.agents.turns.session import STEP_LIMIT_REASON
from aerona.core.errors import AeronaError, BusyError, ConflictError, NotFoundError, ValidationFailedError
from aerona.db.record_context import acting
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.divine_will import active_session, add_event, window_cycles
from aerona.db.tables.divine_will import DivineWillAttachmentRow, DivineWillConfirmationRow, DivineWillCycleRow, DivineWillSessionRow
from aerona.domain.enums.divine_will import ConfirmationReason, ConfirmationStatus, CycleEventKind, CycleNotice, CycleStatus, DivineWillMode
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.providers import ModelRole
from aerona.events.audience import addressed_to, private_audience
from aerona.events.kinds import EventKind
from aerona.jobs.context import JOB_LABEL_KEY, JobContext
from aerona.jobs.manager import JobManager
from aerona.llm.client import retry_wait_seconds
from aerona.llm.content import ImagePart, ModelCapabilities
from aerona.llm.errors import LlmDisabledError, LlmTransientError
from aerona.llm.records import AgentRun, Usage
from aerona.llm.stream import StreamActor, current_actor
from aerona.llm.tools import AgentTool
from aerona.media.store import read_all
from aerona.prompts import PromptId
from aerona.prompts.contexts.divine_will import DivineWillTranslateContext
from aerona.prompts.schemas.divine_will import WillAnswerInLanguage
from aerona.rules.registry import Rules
from aerona.services.container import Services
from aerona.services.divine_will.context import Speaker, pictures, speaker, system_prompt, user_prompt
from aerona.services.divine_will.host import will_host
from aerona.services.divine_will.language import player_language, strays_from
from aerona.services.divine_will.player import CatalogPlayer
from aerona.services.divine_will.sessions import (
    STEP_LIMIT_NOTICE,
    VISION_NOTICE,
    bind_attachments,
    close_session,
    end_cycle,
    judge_pictures,
    new_cycle,
    now,
    open_session,
    settle_stale,
)
from aerona.services.divine_will.trace import CycleTrace, CycleWatch, OutcomeBook
from aerona.tools.divine_will.framework import WillCall, WillResult, WillTool, invoke, will_agent_tool
from aerona.tools.divine_will.registry import mode_tools, tool_text
from aerona.tools.framework.runtime import LOGGER as TOOL_LOGGER

DIVINE_WILL_GROUP = "divine_will"
CHANNEL_PREFIX = "divine_will:"
LABEL = "divine_will"
TRANSLATE_LABEL = "divine_will_language"
TRANSLATED_NOTICE = CycleNotice.TRANSLATED.value
CYCLE_KEY = "cycle_id"
APPROVE = "approve"
DECLINE = "decline"
DISABLED_TEXT = "The Divine Will needs the language model, which is disabled or not connected."
BUSY_TEXT = "The Divine Will is still answering the last request; wait for it or stop it first."
EMPTY_TEXT = "Say something to the Divine Will."
NO_WORLD_TEXT = "There is no world yet for the Divine Will to act on."
WAITING_TEXT = "An act already waits for the player's decision. Call no more tools: tell the player which act waits and what it will change."
STEP_LIMIT_TEXT = "The exchange used every model reply one exchange may take."
VISION_TEXT = "The player attached a picture the model cannot see; it was kept with the request."
FAILED_TOOL = "The tool failed inside the server: {error}"
WAITING_FOR = "That act is not waiting for a decision."
NOT_WAITING = "That exchange is not waiting for a decision."
NOT_RUNNING = "That exchange has already ended."


TURN_LOCKS: WeakKeyDictionary[JobManager, asyncio.Lock] = WeakKeyDictionary()


def turn_lock(jobs: JobManager) -> asyncio.Lock:
    found = TURN_LOCKS.get(jobs)
    if found is None:
        found = TURN_LOCKS[jobs] = asyncio.Lock()
    return found


@dataclass(frozen=True)
class Prepared:
    cycle: DivineWillCycleRow
    rules: Rules
    who: Speaker
    system: str
    prompt: str
    images: list[ImagePart]
    tools: list[WillTool[Any]]
    remaining: int


def cycle_payload(cycle: DivineWillCycleRow) -> dict[str, Any]:
    return {"cycle_id": cycle.id, "session_id": cycle.session_id, "ordinal": cycle.ordinal, "mode": cycle.mode.value, "status": cycle.status.value}


def finished_payload(cycle: DivineWillCycleRow) -> dict[str, Any]:
    counts = {"steps": cycle.steps, "input_tokens": cycle.input_tokens, "output_tokens": cycle.output_tokens}
    return {**cycle_payload(cycle), **counts, "error": cycle.error}


def request_details(row: DivineWillConfirmationRow) -> dict[str, Any]:
    return {"confirmation_id": row.id, "action_id": row.action_id, "reason": row.reason.value, "input": dict(row.input), "preview": dict(row.preview)}


class DivineWillRuntime:
    def __init__(self, services: Services) -> None:
        self.services = services
        self.player = CatalogPlayer(services)

    @property
    def model(self) -> LanguageModel:
        return self.services.application.model

    def publish(self, kind: EventKind, payload: dict[str, Any], audience: int | None = None) -> None:
        self.services.bus.publish(kind, payload, audience=audience)

    async def audience_of(self, session_id: int) -> int | None:
        async with self.services.database.read() as session:
            holder = await session.get(DivineWillSessionRow, session_id)
        return private_audience(holder.author_account_id, holder.shared) if holder is not None else None

    def trace(self, cycle_id: int) -> CycleTrace:
        return CycleTrace(self.services.database, cycle_id)

    def running_cycle_id(self) -> int | None:
        job_id = self.services.jobs.busy_group(DIVINE_WILL_GROUP)
        context = self.services.jobs.running_context(job_id) if job_id is not None else None
        found = context.params.get(CYCLE_KEY) if context is not None else None
        return int(found) if found is not None else None

    async def capabilities(self) -> ModelCapabilities:
        return await self.model.capabilities(ModelRole.CONVERSATION)

    def require_idle(self) -> None:
        if self.services.jobs.busy_group(DIVINE_WILL_GROUP) is not None:
            raise BusyError(BUSY_TEXT)

    async def submit(self, text: str, mode: DivineWillMode, attachment_ids: Sequence[int]) -> DivineWillCycleRow:
        if not self.model.ready(ModelRole.CONVERSATION):
            raise LlmDisabledError(DISABLED_TEXT)
        said = text.strip()
        if not said:
            raise ValidationFailedError(EMPTY_TEXT)
        async with turn_lock(self.services.jobs):
            return await self.begin(said, mode, attachment_ids)

    async def begin(self, said: str, mode: DivineWillMode, attachment_ids: Sequence[int]) -> DivineWillCycleRow:
        self.require_idle()
        self.services.application.discovery.ensure_writable()
        settled: list[DivineWillCycleRow] = []
        async with self.services.database.write() as session:
            cosmos = await CosmosRepository(session).get()
            if cosmos is None:
                raise NotFoundError(NO_WORLD_TEXT)
            holder = await open_session(session, cosmos.epoch)
            settled = await settle_stale(session, holder.id)
            cycle = await new_cycle(session, holder, mode=mode, epoch=cosmos.epoch, text=said, model=self.model.model_of(ModelRole.CONVERSATION))
            files = await bind_attachments(session, cycle.id, attachment_ids, self.services.settings.divine_will_upload_max_files)
            await add_event(
                session,
                cycle.id,
                CycleEventKind.PLAYER,
                payload={"text": said, "mode": mode.value, "attachment_ids": [row.id for row in files]},
            )
        for row in settled:
            self.publish(
                EventKind.DIVINE_WILL_CYCLE_FINISHED, {**cycle_payload(row), "error": row.error}, private_audience(holder.author_account_id, holder.shared)
            )
        await self.launch(cycle)
        return cycle

    async def launch(self, cycle: DivineWillCycleRow) -> None:
        cycle_id = cycle.id

        async def handler(context: JobContext) -> dict[str, Any]:
            return await self.drive(cycle_id)

        audience = await self.audience_of(cycle.session_id)
        with addressed_to(audience):
            try:
                await self.services.jobs.submit(
                    JobKind.DIVINE_WILL, handler, {CYCLE_KEY: cycle_id, JOB_LABEL_KEY: LABEL}, exclusive_group=DIVINE_WILL_GROUP, as_person=True
                )
            except BusyError:
                await self.finish(cycle_id, CycleStatus.FAILED, error=BUSY_TEXT)
                raise
            self.publish(EventKind.DIVINE_WILL_CYCLE_STARTED, cycle_payload(cycle))

    async def drive(self, cycle_id: int) -> dict[str, Any]:
        try:
            status = await self.converse(cycle_id)
        except asyncio.CancelledError:
            await self.finish(cycle_id, CycleStatus.CANCELLED)
            raise
        except Exception as error:
            text = str(error) or type(error).__name__
            await self.trace(cycle_id).add(CycleEventKind.ERROR, payload={"text": text})
            await self.finish(cycle_id, CycleStatus.FAILED, error=text)
            raise
        return {CYCLE_KEY: cycle_id, "status": status.value}

    async def converse(self, cycle_id: int) -> CycleStatus:
        trace = self.trace(cycle_id)
        attempt = 1
        while True:
            prepared = await self.prepare(cycle_id)
            if prepared.remaining <= 0:
                await trace.add(CycleEventKind.NOTICE, payload={"notice": STEP_LIMIT_NOTICE, "text": STEP_LIMIT_TEXT})
                return await self.finish(cycle_id, CycleStatus.DONE, final_text=prepared.cycle.final_text)
            book = OutcomeBook()
            watch = CycleWatch(trace, book, lambda tool, result: self.paused(cycle_id, result))
            token = current_actor.set(StreamActor(ActorKind.CREATOR, prepared.who.creator_id, prepared.who.creator_name, channel=f"{CHANNEL_PREFIX}{cycle_id}"))
            try:
                run = await self.model.run_agent(
                    LABEL,
                    prepared.system,
                    prepared.prompt,
                    tools=self.agent_tools(prepared, book),
                    max_turns=prepared.remaining,
                    timeout_seconds=prepared.rules.model.agent_timeout,
                    images=prepared.images,
                    watch=watch,
                    role=ModelRole.CONVERSATION,
                )
            except LlmTransientError as error:
                await watch.flush()
                await self.count(cycle_id, watch.replies, Usage())
                if book.paused:
                    return await self.finish(cycle_id, CycleStatus.AWAITING_CONFIRMATION, final_text=watch.final_text)
                total = prepared.rules.model.retry_attempts
                if attempt >= total:
                    raise
                wait = retry_wait_seconds(prepared.rules.model, attempt)
                attempt += 1
                reason = str(error) or type(error).__name__
                await trace.add(CycleEventKind.RETRY, payload={"attempt": attempt, "total": total, "reason": reason, "wait_s": wait})
                await asyncio.sleep(wait)
                continue
            finally:
                current_actor.reset(token)
            await watch.flush()
            return await self.settle_run(cycle_id, run, watch, book)

    async def settle_run(self, cycle_id: int, run: AgentRun, watch: CycleWatch, book: OutcomeBook) -> CycleStatus:
        await self.count(cycle_id, run.usage.turns or watch.replies, run.usage)
        final = await self.in_players_language(cycle_id, watch.final_text or run.text)
        if book.paused:
            return await self.finish(cycle_id, CycleStatus.AWAITING_CONFIRMATION, final_text=final)
        if run.stop_reason == STEP_LIMIT_REASON:
            await self.trace(cycle_id).add(CycleEventKind.NOTICE, payload={"notice": STEP_LIMIT_NOTICE, "text": STEP_LIMIT_TEXT})
        return await self.finish(cycle_id, CycleStatus.DONE, final_text=final)

    async def in_players_language(self, cycle_id: int, text: str) -> str:
        rules = self.services.rules.current
        async with self.services.database.read() as session:
            cycle = await session.get(DivineWillCycleRow, cycle_id)
            if cycle is None or not text.strip():
                return text
            window = await window_cycles(session, cycle.session_id, rules.divine_will.remembered_cycles, before_ordinal=cycle.ordinal)
            wanted = player_language(cycle.player_text, [row.player_text for row in window])
        if not wanted or not strays_from(text, wanted):
            return text
        context = DivineWillTranslateContext(rules=rules, language=wanted, text=text)
        try:
            answer = await ask(
                self.model,
                rules,
                label=TRANSLATE_LABEL,
                system=(PromptId.DIVINE_WILL_TRANSLATE_SYSTEM, context),
                user=(PromptId.DIVINE_WILL_TRANSLATE_USER, context),
                output=WillAnswerInLanguage,
            )
        except Exception:
            TOOL_LOGGER.exception("The answer of exchange %s could not be written again in %s", cycle_id, wanted)
            return text
        await self.trace(cycle_id).add(
            CycleEventKind.NOTICE, payload={"notice": TRANSLATED_NOTICE, "text": f"The answer was written again in {wanted}.", "language": wanted}
        )
        return answer.text

    async def prepare(self, cycle_id: int) -> Prepared:
        capabilities = await self.capabilities()
        async with self.services.database.write() as session:
            cycle = await session.get(DivineWillCycleRow, cycle_id)
            if cycle is None:
                raise NotFoundError(NOT_RUNNING)
            rules = await self.player.rules(session)
            who = await speaker(session)
            shown, unseen = await judge_pictures(session, cycle_id, capabilities)
            if unseen:
                await add_event(session, cycle_id, CycleEventKind.NOTICE, payload={"notice": VISION_NOTICE, "text": VISION_TEXT})
            attachments = list(
                await session.scalars(select(DivineWillAttachmentRow).where(DivineWillAttachmentRow.cycle_id == cycle_id).order_by(DivineWillAttachmentRow.id))
            )
            tools = mode_tools(cycle.mode)
            system = system_prompt(rules, who, cycle.mode, [tool.name for tool in tools])
            prompt = await user_prompt(session, rules, who, cycle, attachments)
            remaining = rules.divine_will.max_steps - cycle.steps
        media = self.services.application.media
        images = pictures([(row, await read_all(media, row.media_key)) for row in shown])
        return Prepared(cycle, rules, who, system, prompt, images, tools, remaining)

    def agent_tools(self, prepared: Prepared, book: OutcomeBook) -> list[AgentTool]:
        cycle = prepared.cycle
        call = WillCall(
            self.services.database,
            prepared.rules,
            cycle_id=cycle.id,
            session_id=cycle.session_id,
            epoch=cycle.epoch,
            mode=cycle.mode,
            lore_language=prepared.who.lore_language,
            player=self.player,
            services=will_host(self.services),
        )

        async def run(tool: WillTool[Any], arguments: dict[str, Any]) -> WillResult:
            if book.paused:
                book.refused = True
                result = WillResult(text=WAITING_TEXT, is_error=True)
            else:
                result = await self.guarded(call, prepared.who.creator_id, tool, arguments)
            book.stash(tool.name, arguments, result)
            return result

        found: list[AgentTool] = []
        for tool in prepared.tools:
            text = tool_text(tool.tool_id)
            found.append(will_agent_tool(call, tool, text.description, text.fields, run))
        return found

    async def guarded(self, call: WillCall, creator_id: int, tool: WillTool[Any], arguments: dict[str, Any]) -> WillResult:
        try:
            with acting(ActorKind.CREATOR, creator_id, call.epoch, key=f"{LABEL}.{tool.name}"):
                return await invoke(call, tool, arguments)
        except AeronaError as error:
            return WillResult(text=error.message, is_error=True)
        except Exception as error:
            TOOL_LOGGER.exception("tool call failed")
            return WillResult(text=FAILED_TOOL.format(error=str(error) or type(error).__name__), is_error=True)

    async def paused(self, cycle_id: int, result: WillResult) -> None:
        payload = dict(result.payload)
        async with self.services.database.write() as session:
            known = payload.get("confirmation_id")
            row = await session.get(DivineWillConfirmationRow, int(known)) if known is not None else None
            if row is None:
                row = DivineWillConfirmationRow(
                    cycle_id=cycle_id,
                    action_id=str(payload.get("action_id", "")),
                    input=dict(payload.get("input") or {}),
                    reason=ConfirmationReason(str(payload.get("reason", ConfirmationReason.DESTRUCTIVE.value))),
                    preview=dict(payload.get("preview") or {}),
                )
                session.add(row)
                await session.flush()
            details = request_details(row)
            await add_event(session, cycle_id, CycleEventKind.CONFIRMATION_REQUEST, tool=row.action_id, payload=details)
        announced = {key: details[key] for key in ("confirmation_id", "action_id", "reason", "preview")}
        self.publish(EventKind.DIVINE_WILL_CONFIRMATION_REQUESTED, {"cycle_id": cycle_id, **announced})

    async def count(self, cycle_id: int, replies: int, usage: Usage) -> None:
        async with self.services.database.write() as session:
            cycle = await session.get(DivineWillCycleRow, cycle_id)
            if cycle is None:
                return
            cycle.steps += replies
            cycle.input_tokens += usage.input_tokens
            cycle.output_tokens += usage.output_tokens

    async def finish(self, cycle_id: int, status: CycleStatus, *, final_text: str | None = None, error: str = "") -> CycleStatus:
        async with self.services.database.write() as session:
            cycle = await session.get(DivineWillCycleRow, cycle_id)
            if cycle is None:
                return status
            if cycle.status is not CycleStatus.RUNNING:
                return cycle.status
            cycle.status = status
            if final_text is not None:
                cycle.final_text = final_text
            if error:
                cycle.error = error
            if status is not CycleStatus.AWAITING_CONFIRMATION:
                cycle.finished_at = now()
            payload = finished_payload(cycle)
            session_id = cycle.session_id
        self.publish(EventKind.DIVINE_WILL_CYCLE_FINISHED, payload, await self.audience_of(session_id))
        return status

    async def cancel(self, cycle_id: int) -> DivineWillCycleRow:
        async with self.services.database.write() as session:
            cycle = await session.get(DivineWillCycleRow, cycle_id)
            if cycle is None:
                raise NotFoundError(NOT_RUNNING)
            if cycle.status not in (CycleStatus.RUNNING, CycleStatus.AWAITING_CONFIRMATION):
                raise ConflictError(NOT_RUNNING)
            await end_cycle(session, cycle, CycleStatus.CANCELLED)
            payload = finished_payload(cycle)
            session_id = cycle.session_id
        if self.running_cycle_id() == cycle_id:
            job_id = self.services.jobs.busy_group(DIVINE_WILL_GROUP)
            if job_id is not None:
                await self.services.jobs.cancel(job_id)
        self.publish(EventKind.DIVINE_WILL_CYCLE_FINISHED, payload, await self.audience_of(session_id))
        return cycle

    async def decide(self, confirmation_id: int, decision: str) -> DivineWillConfirmationRow:
        async with turn_lock(self.services.jobs):
            return await self.decided(confirmation_id, decision)

    async def decided(self, confirmation_id: int, decision: str) -> DivineWillConfirmationRow:
        self.require_idle()
        async with self.services.database.read() as session:
            row = await session.get(DivineWillConfirmationRow, confirmation_id)
            if row is None:
                raise NotFoundError(WAITING_FOR)
            cycle = await session.get(DivineWillCycleRow, row.cycle_id)
        if row.status is not ConfirmationStatus.PENDING:
            raise ConflictError(WAITING_FOR)
        if cycle is None or cycle.status is not CycleStatus.AWAITING_CONFIRMATION:
            raise ConflictError(NOT_WAITING)
        approved = decision == APPROVE
        outcome: dict[str, Any] = {}
        if approved:
            outcome = await self.player.perform(row.action_id, row.input)
            if outcome.get("busy"):
                raise BusyError(str(outcome.get("error", "")))
        async with self.services.database.write() as session:
            row = await session.get(DivineWillConfirmationRow, confirmation_id) or row
            cycle = await session.get(DivineWillCycleRow, row.cycle_id) or cycle
            row.status = ConfirmationStatus.APPROVED if approved else ConfirmationStatus.DECLINED
            row.decided_at = now()
            entry = outcome.get("ledger_entry_id")
            row.ledger_entry_id = int(entry) if entry is not None else None
            reply: dict[str, Any] = {"confirmation_id": row.id, "decision": APPROVE if approved else DECLINE}
            if approved:
                reply.update(
                    {
                        "ok": bool(outcome.get("ok")),
                        "text": str(outcome.get("message") or outcome.get("error") or ""),
                        "ledger_entry_id": row.ledger_entry_id,
                        "job_id": str(outcome.get("job_id") or ""),
                        "essence": int(outcome.get("essence") or 0),
                    }
                )
            await add_event(session, row.cycle_id, CycleEventKind.CONFIRMATION_REPLY, tool=row.action_id, payload=reply)
            cycle.status = CycleStatus.RUNNING
        await self.launch(cycle)
        return row

    async def reset(self) -> DivineWillSessionRow:
        async with turn_lock(self.services.jobs):
            return await self.renewed()

    async def renewed(self) -> DivineWillSessionRow:
        self.require_idle()
        closed: list[DivineWillCycleRow] = []
        async with self.services.database.write() as session:
            cosmos = await CosmosRepository(session).get()
            epoch = cosmos.epoch if cosmos is not None else 0
            current = await active_session(session)
            audience = private_audience(current.author_account_id, current.shared) if current is not None else None
            if current is not None:
                closed = await close_session(session, current, epoch)
            fresh = DivineWillSessionRow(opened_epoch=epoch)
            session.add(fresh)
            await session.flush()
        for cycle in closed:
            self.publish(EventKind.DIVINE_WILL_CYCLE_FINISHED, {**cycle_payload(cycle), "error": cycle.error}, audience)
        return fresh
