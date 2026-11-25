import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from claude_agent_sdk import CLIConnectionError, ProcessError
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ask import ask
from aerona.agents.ports import LanguageModel
from aerona.agents.turns.session import STEP_LIMIT_REASONS
from aerona.constants.llm import HAIKU_MODEL_ID
from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.constants.units import PERCENT
from aerona.core.errors import BusyError, ConflictError, NotFoundError, ValidationFailedError
from aerona.db.record_context import acting
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.presence import (
    events_by_exchange,
    exchange_counts,
    next_exchange_ordinal,
    open_session_of,
    running_exchange,
    window_exchanges,
)
from aerona.db.tables.presence import PresenceExchangeRow, PresenceSessionRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.presence import PresenceEventKind, PresenceExchangeStatus, PresenceGuise, PresenceRecord, PresenceStatus
from aerona.engine.mind.memories import remember
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.kinds import EventKind
from aerona.jobs.context import JOB_LABEL_KEY, JobContext
from aerona.llm.client import retry_wait_seconds
from aerona.llm.errors import LlmDisabledError, LlmTransientError
from aerona.llm.records import AgentRun, Usage
from aerona.llm.stream import StreamActor, current_actor
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.presence import PresenceSystemContext
from aerona.prompts.schemas.presence import PresenceAnswer
from aerona.rules.registry import Rules
from aerona.services.container import Services
from aerona.services.divine_will.language import player_language, strays_from
from aerona.services.presence.context import closing_context, guise_note, system_context, user_context
from aerona.services.presence.speakers import Speaker, require_speaker
from aerona.services.presence.tools import SpeakerTools, speaker_tools
from aerona.services.presence.trace import ExchangeTrace, ExchangeWatch
from aerona.tools.framework.runtime import LOGGER
from aerona.tools.toolkit import Toolkits

PRESENCE_GROUP = "presence"
CHANNEL_PREFIX = "presence:"
LABEL = "presence"
CLOSING_LABEL = "presence_closing"
EXCHANGE_KEY = "exchange_id"
SESSION_KEY = "session_id"
AUDIENCE_KEY = "presence.audience"
DISABLED_TEXT = "Summoning needs the language model, which is disabled or not connected."
BUSY_TEXT = "The summoned being is still answering; wait for it or stop it first."
EMPTY_TEXT = "Say something to the summoned being."
NO_WORLD_TEXT = "There is no world yet to summon anyone from."
NO_SESSION = "No such audience."
CLOSED_SESSION = "That audience has ended; begin a new one."
NO_EXCHANGE = "No such exchange of an audience."
NOT_RUNNING = "That exchange has already ended."
INTERRUPTED_TEXT = "The exchange stopped when the server was restarted before it finished."
STEP_LIMIT_TEXT = "The exchange used every model reply one exchange may take."


def now() -> datetime:
    return datetime.now(UTC)


def first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def exchange_payload(exchange: PresenceExchangeRow, node_id: int) -> dict[str, Any]:
    return {
        EXCHANGE_KEY: exchange.id,
        SESSION_KEY: exchange.session_id,
        "node_id": node_id,
        "ordinal": exchange.ordinal,
        "status": exchange.status.value,
    }


def finished_payload(exchange: PresenceExchangeRow, node_id: int) -> dict[str, Any]:
    counts = {"steps": exchange.steps, "input_tokens": exchange.input_tokens, "output_tokens": exchange.output_tokens}
    return {**exchange_payload(exchange, node_id), **counts, "error": exchange.error}


def session_payload(holder: PresenceSessionRow, *, kept: bool) -> dict[str, Any]:
    return {
        SESSION_KEY: holder.id,
        "node_id": holder.node_id,
        "guise": holder.guise.value,
        "record": holder.record.value,
        "status": holder.status.value,
        "kept": kept,
    }


def exchange_group(session_id: int) -> str:
    return f"{PRESENCE_GROUP}:{session_id}"


def feeling_size(rules: Rules, feeling: int) -> int:
    size = round(rules.presence.audience_magnitude * feeling / PERCENT)
    return size or (1 if feeling >= 0 else -1)


def actor_of(speaker: Speaker) -> ActorKind:
    if isinstance(speaker.node, SonRow):
        return ActorKind.SON
    return ActorKind.MORTAL if speaker.entity_type is not None else ActorKind.FOREIGN_GOD


@dataclass(frozen=True)
class Prepared:
    exchange: PresenceExchangeRow
    holder: PresenceSessionRow
    rules: Rules
    speaker: Speaker
    creator_id: int
    creator_name: str
    context: PresenceSystemContext
    prompt: str
    tools: SpeakerTools
    remaining: int


@dataclass(frozen=True)
class Closing:
    reply: str
    remember: str
    feeling: int


class PresenceRuntime:
    def __init__(self, services: Services) -> None:
        self.services = services

    @property
    def model(self) -> LanguageModel:
        return self.services.application.model

    def publish(self, kind: EventKind, payload: dict[str, Any]) -> None:
        self.services.bus.publish(kind, payload)

    def trace(self, exchange_id: int) -> ExchangeTrace:
        return ExchangeTrace(self.services.database, exchange_id)

    def running_exchange_id(self, session_id: int) -> int | None:
        job_id = self.services.jobs.busy_group(exchange_group(session_id))
        context = self.services.jobs.running_context(job_id) if job_id is not None else None
        found = context.params.get(EXCHANGE_KEY) if context is not None else None
        return int(found) if found is not None else None

    async def rules(self, session: AsyncSession) -> Rules:
        return await self.services.agents.rules(session)

    async def stop_job(self, session_id: int) -> None:
        job_id = self.services.jobs.busy_group(exchange_group(session_id))
        if job_id is not None:
            await self.services.jobs.cancel(job_id)

    async def open(self, node_id: int, guise: PresenceGuise, record: PresenceRecord) -> PresenceSessionRow:
        self.services.application.discovery.ensure_writable()
        async with self.services.database.read() as session:
            current = await open_session_of(session, node_id)
        if current is not None:
            await self.close(current.id)
        async with self.services.database.write() as session:
            cosmos = await CosmosRepository(session).get()
            if cosmos is None:
                raise NotFoundError(NO_WORLD_TEXT)
            speaker = await require_speaker(session, await self.rules(session), node_id)
            holder = PresenceSessionRow(
                node_id=node_id, guise=guise, record=record, status=PresenceStatus.OPEN, dead_when_summoned=speaker.dead, opened_epoch=cosmos.epoch
            )
            session.add(holder)
            await session.flush()
        self.publish(EventKind.PRESENCE_SESSION_CHANGED, session_payload(holder, kept=True))
        return holder

    async def close(self, session_id: int) -> tuple[PresenceSessionRow, bool]:
        self.services.application.discovery.ensure_writable()
        await self.stop_job(session_id)
        async with self.services.database.write() as session:
            holder = await session.get(PresenceSessionRow, session_id)
            if holder is None:
                raise NotFoundError(NO_SESSION)
            for exchange in await self.unsettled(session, holder.id):
                exchange.status = PresenceExchangeStatus.CANCELLED
                exchange.finished_at = now()
            spoken = (await exchange_counts(session, [holder.id])).get(holder.id, 0) > 0
            kept = holder.record is PresenceRecord.ON_RECORD and spoken
            holder.status = PresenceStatus.CLOSED
            holder.closed_at = holder.closed_at or now()
            if not kept:
                await session.delete(holder)
        self.publish(EventKind.PRESENCE_SESSION_CHANGED, session_payload(holder, kept=kept))
        return holder, kept

    async def unsettled(self, session: AsyncSession, session_id: int) -> list[PresenceExchangeRow]:
        found = await running_exchange(session, session_id)
        return [found] if found is not None else []

    async def submit(self, session_id: int, text: str) -> PresenceExchangeRow:
        if not self.model.enabled:
            raise LlmDisabledError(DISABLED_TEXT)
        said = text.strip()
        if not said:
            raise ValidationFailedError(EMPTY_TEXT)
        if self.services.jobs.busy_group(exchange_group(session_id)) is not None:
            raise BusyError(BUSY_TEXT)
        self.services.application.discovery.ensure_writable()
        async with self.services.database.write() as session:
            cosmos = await CosmosRepository(session).get()
            if cosmos is None:
                raise NotFoundError(NO_WORLD_TEXT)
            holder = await session.get(PresenceSessionRow, session_id)
            if holder is None:
                raise NotFoundError(NO_SESSION)
            if holder.status is not PresenceStatus.OPEN:
                raise ConflictError(CLOSED_SESSION)
            for stale in await self.unsettled(session, holder.id):
                stale.status = PresenceExchangeStatus.FAILED
                stale.error = INTERRUPTED_TEXT
                stale.finished_at = now()
            if not holder.title:
                holder.title = first_line(said)
            exchange = PresenceExchangeRow(
                session_id=holder.id,
                ordinal=await next_exchange_ordinal(session, holder.id),
                epoch=cosmos.epoch,
                player_text=said,
                status=PresenceExchangeStatus.RUNNING,
                model=HAIKU_MODEL_ID,
            )
            session.add(exchange)
            await session.flush()
            node_id = holder.node_id
        await self.launch(exchange, node_id)
        return exchange

    async def launch(self, exchange: PresenceExchangeRow, node_id: int) -> None:
        exchange_id = exchange.id

        async def handler(context: JobContext) -> dict[str, Any]:
            return await self.drive(exchange_id)

        params = {EXCHANGE_KEY: exchange_id, SESSION_KEY: exchange.session_id, JOB_LABEL_KEY: LABEL}
        try:
            await self.services.jobs.submit(JobKind.PRESENCE, handler, params, exclusive_group=exchange_group(exchange.session_id))
        except BusyError:
            await self.finish(exchange_id, PresenceExchangeStatus.FAILED, error=BUSY_TEXT)
            raise
        self.publish(EventKind.PRESENCE_EXCHANGE_STARTED, exchange_payload(exchange, node_id))

    async def drive(self, exchange_id: int) -> dict[str, Any]:
        try:
            status = await self.converse(exchange_id)
        except asyncio.CancelledError:
            await self.finish(exchange_id, PresenceExchangeStatus.CANCELLED)
            raise
        except Exception as error:
            text = str(error) or type(error).__name__
            await self.trace(exchange_id).add(PresenceEventKind.ERROR, payload={"text": text})
            await self.finish(exchange_id, PresenceExchangeStatus.FAILED, error=text)
            raise
        return {EXCHANGE_KEY: exchange_id, "status": status.value}

    async def converse(self, exchange_id: int) -> PresenceExchangeStatus:
        trace = self.trace(exchange_id)
        attempt = 1
        while True:
            prepared = await self.prepare(exchange_id)
            if prepared.remaining <= 0:
                await trace.add(PresenceEventKind.ERROR, payload={"text": STEP_LIMIT_TEXT})
                return await self.finish(exchange_id, PresenceExchangeStatus.DONE, reply=prepared.exchange.reply_text)
            watch = ExchangeWatch(trace)
            speaker = prepared.speaker
            actor = StreamActor(
                actor_of(speaker), speaker.node_id, speaker.name, read_only_tools=prepared.tools.read_only, channel=f"{CHANNEL_PREFIX}{exchange_id}"
            )
            token = current_actor.set(actor)
            try:
                run = await self.model.run_agent(
                    LABEL,
                    render(PromptId.PRESENCE_SYSTEM, prepared.context),
                    prepared.prompt,
                    tools=prepared.tools.tools(),
                    max_turns=prepared.remaining,
                    timeout_seconds=prepared.rules.model.agent_timeout,
                    watch=watch,
                )
            except (LlmTransientError, CLIConnectionError, ProcessError) as error:
                await self.count(exchange_id, watch.replies, Usage())
                total = prepared.rules.model.retry_attempts
                if attempt >= total:
                    raise
                wait = retry_wait_seconds(prepared.rules.model, attempt)
                attempt += 1
                reason = str(error) or type(error).__name__
                await trace.add(PresenceEventKind.RETRY, payload={"attempt": attempt, "total": total, "reason": reason, "wait_s": wait})
                await asyncio.sleep(wait)
                continue
            finally:
                current_actor.reset(token)
                if prepared.tools.toolkit is not None:
                    await prepared.tools.toolkit.settle_long_jobs()
            return await self.settle(prepared, run, watch)

    async def prepare(self, exchange_id: int) -> Prepared:
        async with self.services.database.read() as session:
            exchange = await session.get(PresenceExchangeRow, exchange_id)
            if exchange is None:
                raise NotFoundError(NOT_RUNNING)
            holder = await session.get(PresenceSessionRow, exchange.session_id)
            if holder is None:
                raise NotFoundError(NO_SESSION)
            rules = await self.rules(session)
            speaker = await require_speaker(session, rules, holder.node_id)
            creator = await CosmosRepository(session).require_creator()
        world_busy = self.services.jobs.busy_group(WORLD_GROUP) is not None
        found = self.services.agents.toolkits
        toolkits = found if isinstance(found, Toolkits) else None
        tools = await speaker_tools(self.services.database, toolkits, rules, speaker, record=holder.record, epoch=exchange.epoch, world_busy=world_busy)
        async with self.services.database.read() as session:
            speaker = await require_speaker(session, rules, holder.node_id)
            context = await system_context(session, rules, speaker, holder, tools)
            prompt = render(PromptId.PRESENCE_USER, await user_context(session, rules, holder, exchange, creator.name))
        remaining = rules.presence.max_steps - exchange.steps
        return Prepared(exchange, holder, rules, speaker, creator.id, creator.name, context, prompt, tools, remaining)

    async def settle(self, prepared: Prepared, run: AgentRun, watch: ExchangeWatch) -> PresenceExchangeStatus:
        exchange_id = prepared.exchange.id
        await self.count(exchange_id, run.usage.turns or watch.replies, run.usage)
        if run.stop_reason in STEP_LIMIT_REASONS:
            await self.trace(exchange_id).add(PresenceEventKind.ERROR, payload={"text": STEP_LIMIT_TEXT})
        reply = (watch.final_text or run.text).strip()
        closing = await self.closing(prepared, reply)
        if prepared.holder.record is PresenceRecord.ON_RECORD:
            await self.keep_memory(prepared, closing)
        return await self.finish(exchange_id, PresenceExchangeStatus.DONE, reply=closing.reply, kept=closing.remember)

    async def closing(self, prepared: Prepared, reply: str) -> Closing:
        holder = prepared.holder
        exchange = prepared.exchange
        rules = prepared.rules
        async with self.services.database.read() as session:
            window = await window_exchanges(session, holder.id, rules.presence.remembered_exchanges, before_ordinal=exchange.ordinal)
            events = (await events_by_exchange(session, [exchange.id]))[exchange.id]
        wanted = player_language(exchange.player_text, [row.player_text for row in window])
        strays = bool(reply) and bool(wanted) and strays_from(reply, wanted)
        if not reply or (holder.record is PresenceRecord.OFF_RECORD and not strays):
            return Closing(reply, "", 0)
        context = closing_context(rules, holder, exchange, creator_name=prepared.creator_name, reply=reply, language=wanted, events=events)
        try:
            answer = await ask(
                self.model,
                rules,
                label=CLOSING_LABEL,
                system=(PromptId.PRESENCE_SYSTEM, prepared.context),
                user=(PromptId.PRESENCE_CLOSING, context),
                output=PresenceAnswer,
            )
        except Exception:
            LOGGER.exception("The closing of presence exchange %s failed", exchange.id)
            return Closing(reply, "", 0)
        spoken_reply = answer.reply.strip() if strays and answer.reply.strip() else reply
        return Closing(spoken_reply, answer.remember.strip(), answer.feeling)

    async def keep_memory(self, prepared: Prepared, closing: Closing) -> None:
        rules = prepared.rules
        exchange = prepared.exchange
        note = guise_note(prepared.holder.guise, closing.remember or first_line(closing.reply), KEY_MAX_LENGTH)
        async with self.services.database.write() as session:
            with acting(ActorKind.CREATOR, prepared.creator_id, exchange.epoch, key=AUDIENCE_KEY):
                await remember(
                    session,
                    rules,
                    holder_id=prepared.speaker.node_id,
                    subject_id=prepared.creator_id,
                    kind=MemoryKind.AUDIENCE,
                    magnitude=feeling_size(rules, closing.feeling),
                    epoch=exchange.epoch,
                    note=note,
                    decay_pct=rules.presence.audience_decay_pct,
                    merge=False,
                )

    async def count(self, exchange_id: int, replies: int, usage: Usage) -> None:
        async with self.services.database.write() as session:
            exchange = await session.get(PresenceExchangeRow, exchange_id)
            if exchange is None:
                return
            exchange.steps += replies
            exchange.input_tokens += usage.input_tokens
            exchange.output_tokens += usage.output_tokens

    async def finish(
        self, exchange_id: int, status: PresenceExchangeStatus, *, reply: str | None = None, kept: str = "", error: str = ""
    ) -> PresenceExchangeStatus:
        async with self.services.database.write() as session:
            exchange = await session.get(PresenceExchangeRow, exchange_id)
            if exchange is None:
                return status
            if exchange.status is not PresenceExchangeStatus.RUNNING:
                return exchange.status
            holder = await session.get(PresenceSessionRow, exchange.session_id)
            exchange.status = status
            if reply is not None:
                exchange.reply_text = reply
            if kept:
                exchange.remember_text = kept
            if error:
                exchange.error = error
            exchange.finished_at = now()
            payload = finished_payload(exchange, holder.node_id if holder is not None else 0)
        self.publish(EventKind.PRESENCE_EXCHANGE_FINISHED, payload)
        return status

    async def cancel(self, exchange_id: int) -> PresenceExchangeRow:
        async with self.services.database.write() as session:
            exchange = await session.get(PresenceExchangeRow, exchange_id)
            if exchange is None:
                raise NotFoundError(NO_EXCHANGE)
            if exchange.status is not PresenceExchangeStatus.RUNNING:
                raise ConflictError(NOT_RUNNING)
            holder = await session.get(PresenceSessionRow, exchange.session_id)
            exchange.status = PresenceExchangeStatus.CANCELLED
            exchange.finished_at = now()
            payload = finished_payload(exchange, holder.node_id if holder is not None else 0)
        if self.running_exchange_id(exchange.session_id) == exchange_id:
            await self.stop_job(exchange.session_id)
        self.publish(EventKind.PRESENCE_EXCHANGE_FINISHED, payload)
        return exchange
