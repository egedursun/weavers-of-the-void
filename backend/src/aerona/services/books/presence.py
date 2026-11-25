from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import several
from aerona.db.tables.presence import PresenceEventRow, PresenceExchangeRow, PresenceSessionRow
from aerona.domain.enums.presence import PresenceEventKind, PresenceExchangeStatus, PresenceGuise, PresenceRecord, PresenceStatus
from aerona.services.books.divine_will import WillFact, filled, payload_facts, readable, when

GUISE_LABELS: dict[PresenceGuise, str] = {
    PresenceGuise.CREATOR: "Its Creator, revealed",
    PresenceGuise.UNNAMED_POWER: "A divine presence that gave no name",
    PresenceGuise.DREAM_VOICE: "A voice in a dream",
    PresenceGuise.ORDINARY: "Someone of its own world, nothing divine",
}
RECORD_LABELS: dict[PresenceRecord, str] = {
    PresenceRecord.ON_RECORD: "On the record: kept for good and remembered",
    PresenceRecord.OFF_RECORD: "Off the record: nothing kept",
}
SESSION_LABELS: dict[PresenceStatus, str] = {PresenceStatus.OPEN: "Still open", PresenceStatus.CLOSED: "Closed"}
EXCHANGE_LABELS: dict[PresenceExchangeStatus, str] = {
    PresenceExchangeStatus.RUNNING: "Still running",
    PresenceExchangeStatus.DONE: "Answered",
    PresenceExchangeStatus.FAILED: "Failed",
    PresenceExchangeStatus.CANCELLED: "Stopped by the player",
}
STEP_LABELS: dict[PresenceEventKind, str] = {
    PresenceEventKind.TEXT: "Said",
    PresenceEventKind.THOUGHT: "Thought",
    PresenceEventKind.TOOL_CALL: "Tool call",
    PresenceEventKind.TOOL_RESULT: "Tool result",
    PresenceEventKind.ERROR: "Error",
    PresenceEventKind.RETRY: "Retry",
}
ACTING_KINDS = frozenset({PresenceEventKind.TOOL_CALL})


@dataclass(frozen=True)
class AudienceStep:
    ordinal: int
    label: str
    tool: str
    facts: list[WillFact]


@dataclass(frozen=True)
class AudienceExchange:
    ordinal: int
    epoch: int
    status: str
    player_text: str
    reply_text: str
    remember_text: str
    error: str
    facts: list[WillFact]
    steps: list[AudienceStep]
    tools: list[str]


@dataclass(frozen=True)
class Audience:
    id: int
    title: str
    speaker: str
    guise: str
    epoch: int
    from_death: bool
    facts: list[WillFact]
    exchanges: list[AudienceExchange]

    @property
    def heading(self) -> str:
        return self.title or f"Audience of epoch {self.epoch}"


@dataclass
class SpeakerAudiences:
    items: list[Audience] = field(default_factory=list)

    @property
    def shown(self) -> bool:
        return bool(self.items)

    @property
    def tally(self) -> str:
        exchanges = sum(len(item.exchanges) for item in self.items)
        return f"{several(len(self.items), 'audience', 'audiences')}, {several(exchanges, 'exchange', 'exchanges')}"


def step(row: PresenceEventRow) -> AudienceStep:
    return AudienceStep(row.ordinal, STEP_LABELS[row.kind], readable(row.tool), payload_facts(row.payload))


def exchange(row: PresenceExchangeRow, events: list[PresenceEventRow]) -> AudienceExchange:
    facts = filled(
        ("Status", EXCHANGE_LABELS[row.status]),
        ("Model", row.model),
        ("Tokens read", row.input_tokens),
        ("Tokens written", row.output_tokens),
        ("Model replies", row.steps),
        ("Began", when(row.started_at)),
        ("Ended", when(row.finished_at)),
    )
    tools = [readable(event.tool) for event in events if event.kind in ACTING_KINDS and event.tool]
    return AudienceExchange(
        row.ordinal,
        row.epoch,
        EXCHANGE_LABELS[row.status],
        row.player_text,
        row.reply_text,
        row.remember_text,
        row.error,
        facts,
        [step(event) for event in events],
        tools,
    )


async def audiences_by_speaker(session: AsyncSession, names: dict[int, str]) -> dict[int, SpeakerAudiences]:
    kept = list(
        await session.scalars(
            select(PresenceSessionRow).where(PresenceSessionRow.record == PresenceRecord.ON_RECORD).order_by(PresenceSessionRow.node_id, PresenceSessionRow.id)
        )
    )
    if not kept:
        return {}
    exchanges: dict[int, list[PresenceExchangeRow]] = defaultdict(list)
    found = select(PresenceExchangeRow).where(PresenceExchangeRow.session_id.in_([audience.id for audience in kept]))
    for said in await session.scalars(found.order_by(PresenceExchangeRow.session_id, PresenceExchangeRow.ordinal)):
        exchanges[said.session_id].append(said)
    events: dict[int, list[PresenceEventRow]] = defaultdict(list)
    wanted = [said.id for rows in exchanges.values() for said in rows]
    if wanted:
        traced = select(PresenceEventRow).where(PresenceEventRow.exchange_id.in_(wanted))
        for event in await session.scalars(traced.order_by(PresenceEventRow.exchange_id, PresenceEventRow.ordinal)):
            events[event.exchange_id].append(event)
    audiences: dict[int, SpeakerAudiences] = defaultdict(SpeakerAudiences)
    for row in kept:
        shaped = [exchange(item, events[item.id]) for item in exchanges[row.id]]
        facts = filled(
            ("Heard as", GUISE_LABELS[row.guise]),
            ("Record", RECORD_LABELS[row.record]),
            ("Opened in epoch", row.opened_epoch),
            ("Summoned from death", row.dead_when_summoned),
            ("Status", SESSION_LABELS[row.status]),
            ("Opened", when(row.opened_at)),
            ("Closed", when(row.closed_at)),
            ("Exchanges", len(shaped)),
        )
        speaker = names.get(row.node_id, "")
        audience = Audience(row.id, row.title, speaker, GUISE_LABELS[row.guise], row.opened_epoch, row.dead_when_summoned, facts, shaped)
        audiences[row.node_id].items.append(audience)
    return dict(audiences)
