from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import Select, case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.team import AUTHOR_NAME_MAX_LENGTH
from aerona.core.account_scope import current_account
from aerona.core.act_note import current_note
from aerona.core.errors import BusyError, ConflictError, NotFoundError
from aerona.db.ledger_capture import LedgerDraft
from aerona.db.ledger_rows import Change, compacted, to_change
from aerona.db.ledger_undo import changes_of, creating_entry_id, undo_entry
from aerona.db.record_context import acting
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.ledger import LedgerChangeRow, LedgerEntryRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.engine.primitives.manual import manual_context
from aerona.engine.recording.record import record
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.services.ledger_narration import label_names, narrate, node_names
from aerona.services.player.journal import RowJournal
from aerona.services.player.ports import ActionLedger

SUMMARY_FIELDS = ("name", "type", "target_name", "text", "description", "reason", "inspiration")
SUMMARY_FIELD_LIMIT = 80
SUMMARY_SEPARATOR = " · "
NARRATED_ROWS = 30
EPOCH_RUNNING_MESSAGE = "A ledger page cannot be undone while an epoch is running."


@dataclass
class LedgerHandle:
    entry_id: int | None = None


@dataclass(frozen=True)
class EpochCount:
    epoch: int
    entries: int
    undone: int


@dataclass(frozen=True)
class LedgerFilters:
    author_account_id: int | None = None
    action_kind: ActionKind | None = None
    since: datetime | None = None
    until: datetime | None = None

    def applied(self, statement: Select[LedgerEntryRow]) -> Select[LedgerEntryRow]:
        if self.author_account_id is not None:
            statement = statement.where(LedgerEntryRow.author_account_id == self.author_account_id)
        if self.action_kind is not None:
            statement = statement.where(LedgerEntryRow.action_kind == self.action_kind)
        if self.since is not None:
            statement = statement.where(LedgerEntryRow.created_at >= self.since)
        if self.until is not None:
            statement = statement.where(LedgerEntryRow.created_at <= self.until)
        return statement


@dataclass(frozen=True)
class EntryView:
    entry: LedgerEntryRow
    change_count: int
    rows: list[str]
    dependents: list[LedgerEntryRow]


@dataclass(frozen=True)
class LedgerView:
    current_epoch: int
    epochs: list[EpochCount]
    entries: list[EntryView]


@dataclass(frozen=True)
class UndoResult:
    entry_id: int
    applied: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


UPKEEP_FAMILY = "maintenance"


def summarize_inputs(inputs: Mapping[str, Any] | None) -> str | None:
    if not inputs:
        return None
    parts = [str(inputs[key])[:SUMMARY_FIELD_LIMIT] for key in SUMMARY_FIELDS if inputs.get(key) not in (None, "")]
    joined = SUMMARY_SEPARATOR.join(parts)
    return joined or None


def action_label(tool: str, kind: ActionKind | None = None) -> str:
    raw = tool or (kind.value if kind is not None else "")
    family, _, task = raw.partition(":")
    if family == UPKEEP_FAMILY and task:
        return f"ran the upkeep of {' '.join(task.replace('_', ' ').split())}"
    return " ".join(raw.replace(":", " ").replace("_", " ").split())


async def compact_entry(session: AsyncSession, entry_id: int) -> None:
    for row in await session.scalars(select(LedgerChangeRow).where(LedgerChangeRow.entry_id == entry_id)):
        before, after = compacted(to_change(row))
        if before != row.before or after != row.after:
            row.before, row.after = before, after
    await session.flush()


def _inserted_entity_ids(changes: list[Change]) -> set[int]:
    return {change.row_id for change in changes if change.table == "entities" and change.operation is LedgerOperation.INSERT and change.row_id is not None}


def _touches(change: Change, entity_ids: set[int]) -> bool:
    if change.table == "entities" and change.operation is LedgerOperation.UPDATE:
        return change.row_id in entity_ids
    if change.table == "bonds":
        row = change.after or change.before or {}
        return row.get("source_node_id") in entity_ids or row.get("target_node_id") in entity_ids
    return False


class Ledger:
    def __init__(self, bus: EventBus | None = None, journal: ActionLedger | None = None) -> None:
        self._bus = bus
        self._journal: ActionLedger = journal or RowJournal()

    @asynccontextmanager
    async def record(
        self,
        session: AsyncSession,
        *,
        epoch: int,
        actor_kind: ActorKind,
        actor_node_id: int | None,
        actor_name: str,
        tool: str,
        action_kind: ActionKind,
        inputs: Mapping[str, Any] | None = None,
    ) -> AsyncIterator[LedgerHandle]:
        handle = LedgerHandle()
        async with self._journal.capture(session) as capture:
            with acting(actor_kind, actor_node_id, epoch, key=f"actor.{tool}"):
                yield handle
            draft = LedgerDraft(
                epoch=epoch,
                actor_kind=actor_kind,
                actor_node_id=actor_node_id,
                actor_name=actor_name,
                tool=tool,
                action_kind=action_kind,
                input_summary=summarize_inputs(inputs),
            )
            handle.entry_id = await capture.seal(draft)
        if handle.entry_id is not None:
            await compact_entry(session, handle.entry_id)

    @asynccontextmanager
    async def creator_action(
        self, session: AsyncSession, tool: str, action_kind: ActionKind, inputs: Mapping[str, Any] | None = None
    ) -> AsyncIterator[LedgerHandle]:
        repository = CosmosRepository(session)
        cosmos = await repository.require_cosmos()
        creator = await repository.require_creator()
        async with (
            session.begin_nested(),
            self.record(
                session,
                epoch=cosmos.epoch,
                actor_kind=ActorKind.CREATOR,
                actor_node_id=creator.id,
                actor_name=creator.name,
                tool=tool,
                action_kind=action_kind,
                inputs=inputs,
            ) as handle,
        ):
            yield handle

    async def read(
        self,
        session: AsyncSession,
        *,
        limit: int,
        epoch: int | None = None,
        actor_kind: ActorKind | None = None,
        actor_node_id: int | None = None,
        filters: LedgerFilters | None = None,
    ) -> LedgerView:
        cosmos = await CosmosRepository(session).require_cosmos()
        statement = select(LedgerEntryRow)
        if epoch is not None:
            statement = statement.where(LedgerEntryRow.epoch == epoch)
        if actor_kind is not None:
            statement = statement.where(LedgerEntryRow.actor_kind == actor_kind)
        if actor_node_id is not None:
            statement = statement.where(LedgerEntryRow.actor_node_id == actor_node_id)
        if filters is not None:
            statement = filters.applied(statement)
        entries = list(await session.scalars(statement.order_by(LedgerEntryRow.id.desc()).limit(limit)))
        counts = await session.execute(
            select(LedgerEntryRow.epoch, func.count(), func.sum(case((LedgerEntryRow.undone.is_(True), 1), else_=0)))
            .group_by(LedgerEntryRow.epoch)
            .order_by(LedgerEntryRow.epoch.desc())
        )
        views = [await self._view(session, entry) for entry in entries]
        epochs = [EpochCount(epoch=int(row[0]), entries=int(row[1]), undone=int(row[2] or 0)) for row in counts]
        return LedgerView(current_epoch=cosmos.epoch, epochs=epochs, entries=views)

    async def dependents(self, session: AsyncSession, entry: LedgerEntryRow) -> list[LedgerEntryRow]:
        inserted = _inserted_entity_ids(await changes_of(session, entry.id))
        if not inserted:
            return []
        later = await session.scalars(select(LedgerEntryRow).where(LedgerEntryRow.id > entry.id, LedgerEntryRow.undone.is_(False)).order_by(LedgerEntryRow.id))
        found: list[LedgerEntryRow] = []
        for candidate in later:
            if any(_touches(change, inserted) for change in await changes_of(session, candidate.id)):
                found.append(candidate)
        return found

    async def undo(self, session: AsyncSession, rules: Rules, entry_id: int, *, epoch_running: bool, chronicle: bool = True) -> UndoResult:
        if epoch_running:
            raise BusyError(EPOCH_RUNNING_MESSAGE)
        entry = await session.get(LedgerEntryRow, entry_id)
        if entry is None:
            raise NotFoundError("No such entry in the ledger.")
        if entry.undone:
            raise ConflictError("This entry was already undone.")
        cosmos = await CosmosRepository(session).require_cosmos()
        changes = await changes_of(session, entry.id)
        report = await undo_entry(session, entry.id, cosmos.epoch, label_names(changes, await node_names(session, changes)))
        undoer = current_account()
        entry.undone_by_account_id = undoer.id if undoer is not None else None
        entry.undone_by_name = undoer.name[:AUTHOR_NAME_MAX_LENGTH] if undoer is not None else None
        if chronicle:
            creator = await CosmosRepository(session).require_creator()
            ctx = await manual_context(session, "ledger.undo", rules, key=f"undo.{entry.id}")
            written = await record(
                ctx,
                "creator.hand",
                roles={IncidentRole.AUTHORITY: creator.id, IncidentRole.ACTOR: entry.actor_node_id},
                facts={"act": action_label(entry.tool, entry.action_kind), "doer": entry.actor_name},
            )
            session.add(
                ActionRecordRow(
                    epoch=cosmos.epoch,
                    actor_kind=ActorKind.CREATOR,
                    actor_node_id=creator.id,
                    kind=ActionKind.LEDGER_UNDO,
                    summary=written.text,
                    reason=current_note().reason,
                    author_account_id=undoer.id if undoer is not None else None,
                    author_name=undoer.name[:AUTHOR_NAME_MAX_LENGTH] if undoer is not None else None,
                )
            )
            await session.flush()
        if self._bus is not None:
            self._bus.publish(EventKind.LEDGER_UNDONE, {"entry_id": entry.id, "applied": len(report.applied), "conflicts": len(report.conflicts)})
        return UndoResult(entry_id=entry.id, applied=report.applied, conflicts=report.conflicts)

    async def undo_creation(self, session: AsyncSession, rules: Rules, entity_id: int) -> UndoResult | None:
        entry_id = await creating_entry_id(session, entity_id)
        if entry_id is None:
            return None
        return await self.undo(session, rules, entry_id, epoch_running=False, chronicle=False)

    async def prune(self, session: AsyncSession, rules: Rules, current_epoch: int) -> int:
        threshold = current_epoch - rules.ledger.keep_epochs
        result = await session.execute(delete(LedgerEntryRow).where(LedgerEntryRow.epoch < threshold))
        await session.execute(delete(LedgerChangeRow).where(LedgerChangeRow.entry_id.not_in(select(LedgerEntryRow.id))))
        return int(getattr(result, "rowcount", 0) or 0)

    async def _view(self, session: AsyncSession, entry: LedgerEntryRow) -> EntryView:
        changes = [change for change in await changes_of(session, entry.id) if change.visible]
        names = await node_names(session, changes)
        rows = [narrate(change, names) for change in changes[:NARRATED_ROWS]]
        return EntryView(entry=entry, change_count=len(changes), rows=rows, dependents=await self.dependents(session, entry))
