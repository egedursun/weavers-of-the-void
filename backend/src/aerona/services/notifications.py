import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import ColumnElement, case, delete, exists, func, or_, select, true, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.chronicle import NOTIFICATION_CATEGORIES, chronicle_notification
from aerona.core.account_scope import current_account
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.notifications import NotificationDraft, NotificationRepository, effective_settings, fitted_texts, raw_title
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.job import JobRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.meta import NotificationRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.team import NotificationPreferenceRow, NotificationReadRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory, NotificationCategory
from aerona.domain.enums.node import NodeKind
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.manager import ITEMS_KEY as JOB_ITEMS_KEY
from aerona.rules.registry import Rules
from aerona.services.names import find_named_records, mentions_name

PROPHECY_PREFIX = "prophecy"
LEGENDARY_BIRTH = re.compile(r"\b(?:legendary|mythic|divine)\b", re.IGNORECASE)
EPOCH_FINISHED_TITLE = "Epoch {epoch} has ended"
SUMMARY_SEPARATOR = "\n"


NAMED_NODE_KINDS = frozenset(
    {NodeKind.WORLD, NodeKind.STAR, NodeKind.SON, NodeKind.FOREIGN_GOD, NodeKind.CREATOR, NodeKind.GALAXY, NodeKind.CLUSTER, NodeKind.DIMENSION}
)
WORK_SEPARATOR = " · "
WORK_LINE_SEPARATOR = "\n"


class ErrorClass(StrEnum):
    OVERLOAD = "overload"
    RATE_LIMIT = "rate_limit"
    BILLING = "billing"
    TIMEOUT = "timeout"
    NETWORK = "network"
    ABORTED = "aborted"
    FORMAT = "format"
    TURNS = "turns"
    BUDGET = "budget"
    OTHER = "other"


ERROR_PATTERNS: tuple[tuple[ErrorClass, re.Pattern[str]], ...] = (
    (ErrorClass.OVERLOAD, re.compile(r"overload|529|capacity", re.IGNORECASE)),
    (ErrorClass.RATE_LIMIT, re.compile(r"rate.?limit|429|too many requests", re.IGNORECASE)),
    (ErrorClass.BILLING, re.compile(r"billing|credit|quota|payment|usage limit|session limit|hit your (?:\w+ )?limit", re.IGNORECASE)),
    (ErrorClass.TIMEOUT, re.compile(r"time(?:d)?.?out|deadline", re.IGNORECASE)),
    (ErrorClass.NETWORK, re.compile(r"network|connect|ECONN|socket|unreachable|DNS", re.IGNORECASE)),
    (ErrorClass.ABORTED, re.compile(r"abort|cancel", re.IGNORECASE)),
    (ErrorClass.FORMAT, re.compile(r"json|schema|parse|invalid (?:input|output|argument)|validation", re.IGNORECASE)),
    (ErrorClass.TURNS, re.compile(r"max(?:imum)?.?turns|turn limit", re.IGNORECASE)),
    (ErrorClass.BUDGET, re.compile(r"budget|max.?tokens|context (?:window|length)", re.IGNORECASE)),
)

ERROR_TITLES: dict[ErrorClass, str] = {
    ErrorClass.OVERLOAD: "The model is overloaded right now; it will be retried later.",
    ErrorClass.RATE_LIMIT: "The model's rate limit was reached; waiting before trying again.",
    ErrorClass.BILLING: "The model subscription's usage limit was reached; calls resume when it resets.",
    ErrorClass.TIMEOUT: "The model call took too long and timed out.",
    ErrorClass.NETWORK: "The model could not be reached (network problem).",
    ErrorClass.ABORTED: "The model call was stopped.",
    ErrorClass.FORMAT: "The model answered in an unreadable format.",
    ErrorClass.TURNS: "The agent ran out of turns before finishing.",
    ErrorClass.BUDGET: "The request did not fit the model's budget.",
    ErrorClass.OTHER: "Something went wrong in the background.",
}

RETRYABLE_ERRORS = frozenset({ErrorClass.OVERLOAD, ErrorClass.RATE_LIMIT, ErrorClass.TIMEOUT, ErrorClass.NETWORK})


@dataclass(frozen=True)
class NotificationRequest:
    category: NotificationCategory
    title: str | None = None
    body: str | None = None
    target_node_id: int | None = None
    chronicle_id: int | None = None
    epoch: int | None = None
    severity: int | None = None
    forced: bool = False
    job_id: str | None = None


@dataclass(frozen=True)
class CategoryCount:
    category: NotificationCategory
    total: int
    unread: int


@dataclass(frozen=True)
class CategoryInfo:
    category: NotificationCategory
    label: str
    severity: int
    enabled_by_default: bool


@dataclass(frozen=True)
class NotificationPage:
    unread: int
    counts: list[CategoryCount]
    settings: dict[NotificationCategory, bool]
    categories: list[CategoryInfo]
    items: list[NotificationRow] = field(default_factory=list)
    read_ids: frozenset[int] = frozenset()

    def read(self, row: NotificationRow) -> bool:
        return row.id in self.read_ids if current_account() is not None else row.is_read


def classify_error(message: str) -> ErrorClass:
    return next((error_class for error_class, pattern in ERROR_PATTERNS if pattern.search(message)), ErrorClass.OTHER)


def friendly_error(message: str) -> str:
    return ERROR_TITLES[classify_error(message)]


def is_retryable_error(message: str) -> bool:
    return classify_error(message) in RETRYABLE_ERRORS


def classify_chronicle(
    kind: ChronicleKind, text: str, son_id: int | None, entity_ids: Sequence[int], feed_category: FeedCategory | None = None
) -> NotificationCategory | None:
    if kind is ChronicleKind.FATE and text.strip().casefold().startswith(PROPHECY_PREFIX):
        return NotificationCategory.PROPHECY
    if kind is ChronicleKind.BIRTH:
        if son_id is not None and not entity_ids:
            return NotificationCategory.BIRTH
        return NotificationCategory.BIRTH if LEGENDARY_BIRTH.search(text) else None
    return chronicle_notification(kind, feed_category)


def normalized_texts(category: NotificationCategory, title: str | None, body: str | None) -> tuple[str, str | None]:
    raw = raw_title(category, title, body)
    shown = friendly_error(raw) if category is NotificationCategory.ERROR else raw
    return fitted_texts(raw, shown, body)


class Notifier:
    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus

    async def notify(self, session: AsyncSession, rules: Rules, request: NotificationRequest) -> NotificationRow | None:
        spec = NOTIFICATION_CATEGORIES[request.category]
        title, body = normalized_texts(request.category, request.title, request.body)
        draft = NotificationDraft(
            category=request.category,
            title=title,
            body=body,
            severity=request.severity,
            epoch=request.epoch,
            target_node_id=request.target_node_id,
            chronicle_id=request.chronicle_id,
            forced=request.forced,
            job_id=request.job_id,
        )
        row = await NotificationRepository(session).add(draft)
        if row is None:
            return None
        if self._bus is not None:
            self._bus.publish(
                EventKind.NOTIFICATION_CREATED,
                {
                    "id": row.id,
                    "category": row.category.value,
                    "label": spec.label,
                    "severity": row.severity,
                    "title": row.title,
                    "body": row.body,
                    "target_node_id": row.target_node_id,
                    "chronicle_id": row.chronicle_id,
                    "epoch": row.epoch,
                    "toast": row.severity >= rules.notifications.toast_min_importance,
                },
            )
        return row

    async def from_chronicle(
        self,
        session: AsyncSession,
        rules: Rules,
        *,
        chronicle_id: int,
        epoch: int,
        kind: ChronicleKind,
        text: str,
        son_id: int | None,
        entity_ids: Sequence[int],
        feed_category: FeedCategory | None,
    ) -> NotificationRow | None:
        category = classify_chronicle(kind, text, son_id, entity_ids, feed_category)
        if category is None:
            return None
        target = entity_ids[0] if entity_ids else son_id
        request = NotificationRequest(category=category, title=text, body=text, target_node_id=target, chronicle_id=chronicle_id, epoch=epoch)
        return await self.notify(session, rules, request)

    async def pin_chronicle(self, session: AsyncSession, rules: Rules, chronicle_id: int) -> NotificationRow:
        line = await session.get(ChronicleRow, chronicle_id)
        if line is None:
            raise NotFoundError("No such chronicle line.")
        existing = await session.scalar(select(NotificationRow).where(NotificationRow.chronicle_id == chronicle_id))
        if existing is not None:
            existing.is_read = False
            return existing
        statement = select(ChronicleEntityRow.entity_id).where(ChronicleEntityRow.chronicle_id == chronicle_id).order_by(ChronicleEntityRow.position)
        entity_ids = list(await session.scalars(statement))
        category = classify_chronicle(line.kind, line.text, line.son_id, entity_ids, line.feed_category) or NotificationCategory.NOTE
        target = entity_ids[0] if entity_ids else line.son_id
        request = NotificationRequest(
            category=category, title=line.text, body=line.text, target_node_id=target, chronicle_id=line.id, epoch=line.epoch, forced=True
        )
        row = await self.notify(session, rules, request)
        if row is None:
            raise ValidationFailedError("The line could not be pinned.")
        return row

    async def creator_note(self, session: AsyncSession, rules: Rules, title: str, body: str | None, target_node_id: int | None) -> NotificationRow:
        if not title.strip():
            raise ValidationFailedError("A note cannot be empty.")
        request = NotificationRequest(category=NotificationCategory.NOTE, title=title, body=body, target_node_id=target_node_id, forced=True)
        row = await self.notify(session, rules, request)
        if row is None:
            raise ValidationFailedError("The note could not be stored.")
        return row

    async def epoch_finished(self, session: AsyncSession, rules: Rules, epoch: int, summary_lines: Sequence[str]) -> NotificationRow | None:
        lines = list(summary_lines)[: rules.epoch_flow.epoch_end_summary_lines]
        body = SUMMARY_SEPARATOR.join(lines) if lines else None
        request = NotificationRequest(category=NotificationCategory.EPOCH, title=EPOCH_FINISHED_TITLE.format(epoch=epoch), body=body, epoch=epoch)
        return await self.notify(session, rules, request)

    async def job_finished(self, session: AsyncSession, rules: Rules, job_id: str, label: str, items: Sequence[dict[str, Any]]) -> NotificationRow | None:
        if not items:
            return None
        grouped: dict[str, list[str]] = {}
        for item in items:
            action = str(item.get("action") or "")
            name = str(item.get("name") or "")
            if action and name and name not in grouped.setdefault(action, []):
                grouped[action].append(name)
        counts = WORK_SEPARATOR.join(f"{action} ({len(names)})" for action, names in grouped.items())
        title = f"{label[:1].upper()}{label[1:]}: {counts}"
        body = WORK_LINE_SEPARATOR.join(f"{action[:1].upper()}{action[1:]}: {', '.join(names)}" for action, names in grouped.items())
        nodes = {item.get("node_id") for item in items}
        target = next(iter(nodes)) if len(nodes) == 1 else None
        request = NotificationRequest(
            category=NotificationCategory.WORK,
            title=title,
            body=body,
            target_node_id=target if isinstance(target, int) else None,
            job_id=job_id,
        )
        return await self.notify(session, rules, request)

    async def agent_error(self, session: AsyncSession, rules: Rules, message: str, son_id: int | None) -> NotificationRow | None:
        if is_retryable_error(message):
            return None
        title = friendly_error(message)
        repeated = await session.scalar(
            select(NotificationRow.id)
            .where(NotificationRow.category == NotificationCategory.ERROR, NotificationRow.is_read.is_(False), NotificationRow.title == title)
            .limit(1)
        )
        if repeated is not None:
            return None
        request = NotificationRequest(category=NotificationCategory.ERROR, title=message, body=message, target_node_id=son_id)
        return await self.notify(session, rules, request)


def addressed() -> ColumnElement[bool]:
    account = current_account()
    if account is None:
        return true()
    return or_(NotificationRow.recipient_account_id.is_(None), NotificationRow.recipient_account_id == account.id)


def unread() -> ColumnElement[bool]:
    account = current_account()
    if account is None:
        return NotificationRow.is_read.is_(False)
    seen = select(NotificationReadRow.notification_id).where(
        NotificationReadRow.notification_id == NotificationRow.id, NotificationReadRow.account_id == account.id
    )
    return ~exists(seen)


async def read_among(session: AsyncSession, ids: list[int]) -> frozenset[int]:
    account = current_account()
    if account is None or not ids:
        return frozenset()
    found = await session.scalars(
        select(NotificationReadRow.notification_id).where(NotificationReadRow.account_id == account.id, NotificationReadRow.notification_id.in_(ids))
    )
    return frozenset(int(item) for item in found)


async def mark_read_for(session: AsyncSession, account_id: int, *, ids: Iterable[int], every: bool, category: NotificationCategory | None, unread: bool) -> int:
    statement = select(NotificationRow.id).where(addressed())
    if every:
        if category is not None:
            statement = statement.where(NotificationRow.category == category)
    else:
        chosen = list(ids)
        if not chosen:
            return 0
        statement = statement.where(NotificationRow.id.in_(chosen))
    targets = [int(found) for found in await session.scalars(statement.order_by(NotificationRow.id))]
    if not targets:
        return 0
    await session.execute(delete(NotificationReadRow).where(NotificationReadRow.account_id == account_id, NotificationReadRow.notification_id.in_(targets)))
    if not unread:
        moment = datetime.now(UTC)
        session.add_all(NotificationReadRow(notification_id=target, account_id=account_id, read_at=moment) for target in targets)
    await session.flush()
    return len(targets)


async def list_notifications(
    session: AsyncSession,
    *,
    limit: int,
    unread_only: bool = False,
    category: NotificationCategory | None = None,
    before_id: int | None = None,
    exclude: Iterable[NotificationCategory] = (),
) -> NotificationPage:
    mine = await own_preferences(session)
    statement = select(NotificationRow).where(addressed())
    excluded = [*exclude, *(found for found, enabled in mine.items() if not enabled)]
    if excluded and category is None:
        statement = statement.where(NotificationRow.category.not_in(excluded))
    if unread_only:
        statement = statement.where(unread())
    if category is not None:
        statement = statement.where(NotificationRow.category == category)
    if before_id is not None:
        statement = statement.where(NotificationRow.id < before_id)
    items = list(await session.scalars(statement.order_by(NotificationRow.id.desc()).limit(limit)))
    grouped = await session.execute(
        select(NotificationRow.category, func.count(), func.sum(case((unread(), 1), else_=0)))
        .where(addressed())
        .group_by(NotificationRow.category)
        .order_by(NotificationRow.category)
    )
    counts = [CategoryCount(category=row[0], total=int(row[1]), unread=int(row[2] or 0)) for row in grouped]
    cosmos = await session.get(CosmosRow, 1)
    return NotificationPage(
        unread=sum(count.unread for count in counts),
        counts=counts,
        settings={**effective_settings(cosmos.notification_prefs if cosmos else None), **mine},
        categories=[CategoryInfo(spec.category, spec.label, spec.severity, spec.enabled_by_default) for spec in NOTIFICATION_CATEGORIES.values()],
        items=items,
        read_ids=await read_among(session, [row.id for row in items]),
    )


async def unread_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(NotificationRow).where(addressed(), unread())) or 0)


async def mark_read(
    session: AsyncSession,
    *,
    ids: Iterable[int] = (),
    every: bool = False,
    category: NotificationCategory | None = None,
    unread: bool = False,
) -> int:
    account = current_account()
    if account is not None:
        return await mark_read_for(session, account.id, ids=ids, every=every, category=category, unread=unread)
    statement = update(NotificationRow).values(is_read=not unread)
    if every:
        if category is not None:
            statement = statement.where(NotificationRow.category == category)
    else:
        chosen = list(ids)
        if not chosen:
            return 0
        statement = statement.where(NotificationRow.id.in_(chosen))
    result = await session.execute(statement.execution_options(synchronize_session="fetch"))
    return int(getattr(result, "rowcount", 0) or 0)


async def own_preferences(session: AsyncSession) -> dict[NotificationCategory, bool]:
    account = current_account()
    if account is None:
        return {}
    rows = await session.scalars(
        select(NotificationPreferenceRow).where(NotificationPreferenceRow.account_id == account.id).order_by(NotificationPreferenceRow.category)
    )
    return {row.category: row.enabled for row in rows}


async def update_settings(session: AsyncSession, changes: dict[NotificationCategory, bool]) -> dict[NotificationCategory, bool]:
    account = current_account()
    cosmos = await CosmosRepository(session).require_cosmos()
    if account is not None:
        for category, value in changes.items():
            if category in NOTIFICATION_CATEGORIES:
                await session.merge(NotificationPreferenceRow(account_id=account.id, category=category, enabled=bool(value)))
        await session.flush()
        return {**effective_settings(cosmos.notification_prefs), **await own_preferences(session)}
    merged = dict(cosmos.notification_prefs or {})
    merged.update({category: bool(value) for category, value in changes.items() if category in NOTIFICATION_CATEGORIES})
    cosmos.notification_prefs = merged
    await session.flush()
    return effective_settings(merged)


async def prune_notifications(session: AsyncSession, rules: Rules) -> int:
    top = await session.scalar(select(func.max(NotificationRow.id)))
    removed = 0
    if top is not None:
        threshold = int(top) - rules.notifications.read_kept
        result = await session.execute(delete(NotificationRow).where(NotificationRow.is_read.is_(True), NotificationRow.id <= threshold))
        removed += int(getattr(result, "rowcount", 0) or 0)
    keep = select(NotificationRow.id).order_by(NotificationRow.severity.desc(), NotificationRow.id.desc()).limit(rules.notifications.total_cap)
    result = await session.execute(delete(NotificationRow).where(NotificationRow.id.not_in(keep)))
    removed += int(getattr(result, "rowcount", 0) or 0)
    return removed


async def linked_nodes(session: AsyncSession, rows: Sequence[NotificationRow], rules: Rules) -> dict[int, list[int]]:
    found: dict[int, list[int]] = {row.id: [row.target_node_id] if row.target_node_id is not None else [] for row in rows}
    by_chronicle = {row.chronicle_id: row.id for row in rows if row.chronicle_id is not None}
    if by_chronicle:
        lines = await session.execute(
            select(ChronicleEntityRow.chronicle_id, ChronicleEntityRow.entity_id)
            .where(ChronicleEntityRow.chronicle_id.in_(list(by_chronicle)))
            .order_by(ChronicleEntityRow.chronicle_id, ChronicleEntityRow.position)
        )
        for chronicle_id, entity_id in lines:
            found[by_chronicle[chronicle_id]].append(entity_id)
        sons = await session.execute(
            select(ChronicleRow.id, ChronicleRow.son_id).where(ChronicleRow.id.in_(list(by_chronicle)), ChronicleRow.son_id.is_not(None))
        )
        for chronicle_id, son_id in sons:
            if son_id is not None:
                found[by_chronicle[chronicle_id]].append(son_id)
    by_job = {row.job_id: row.id for row in rows if row.job_id is not None}
    if by_job:
        for job_id, result in await session.execute(select(JobRow.id, JobRow.result).where(JobRow.id.in_(list(by_job)))):
            items = result.get(JOB_ITEMS_KEY) if isinstance(result, dict) else None
            for item in items if isinstance(items, list) else []:
                for key in ("node_id", "other_id"):
                    value = item.get(key) if isinstance(item, dict) else None
                    if isinstance(value, int):
                        found[by_job[job_id]].append(value)
    minimum = rules.link_graph.name_min_chars
    named = await session.execute(select(NodeRow.id, NodeRow.name).where(NodeRow.kind.in_(list(NAMED_NODE_KINDS)), func.length(NodeRow.name) >= minimum))
    others = sorted(named, key=lambda node: -len(node[1]))
    for row in rows:
        text = f"{row.title} {row.body or ''}"
        found[row.id].extend(node_id for node_id, name in others if mentions_name(text, name))
        if not found[row.id]:
            found[row.id] = [entity.id for entity in await find_named_records(session, rules, text, limit=rules.link_graph.proposal_cap)]
    return {row_id: list(dict.fromkeys(ids)) for row_id, ids in found.items()}
