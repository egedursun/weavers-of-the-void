from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement, SQLColumnExpression, String, case, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.telemetry.tables import LlmCallRow
from aerona.domain.enums.telemetry import LlmCallKind, LlmCallStatus, UsageBucket, UsageSort
from aerona.services.metrics import MORTAL_TURN_GROUP, MORTAL_TURN_PREFIX, SON_TURN_GROUP, SON_TURN_PREFIX, step_group

GROUP_PREFIXES = {SON_TURN_GROUP: SON_TURN_PREFIX, MORTAL_TURN_GROUP: MORTAL_TURN_PREFIX}
TIME_BUCKETS = {UsageBucket.DAY: (10, "%Y-%m-%d"), UsageBucket.HOUR: (13, "%Y-%m-%d %H")}

TOTAL_TOKENS = LlmCallRow.input_tokens + LlmCallRow.output_tokens
SORT_COLUMNS: dict[UsageSort, SQLColumnExpression[Any]] = {
    UsageSort.TIME: LlmCallRow.id,
    UsageSort.TOTAL_TOKENS: TOTAL_TOKENS,
    UsageSort.INPUT_TOKENS: LlmCallRow.input_tokens,
    UsageSort.OUTPUT_TOKENS: LlmCallRow.output_tokens,
    UsageSort.DURATION: LlmCallRow.duration_ms,
    UsageSort.EPOCH: LlmCallRow.epoch,
    UsageSort.MODEL: LlmCallRow.model,
    UsageSort.STEP: LlmCallRow.job,
}


@dataclass(frozen=True)
class UsageFilter:
    search: str | None = None
    models: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    steps: tuple[str, ...] = ()
    kinds: tuple[LlmCallKind, ...] = ()
    statuses: tuple[LlmCallStatus, ...] = ()
    epoch_from: int | None = None
    epoch_to: int | None = None
    since: datetime | None = None

    def conditions(self) -> list[ColumnElement[bool]]:
        found: list[ColumnElement[bool]] = []
        term = (self.search or "").strip().lower()
        if term:
            columns = (LlmCallRow.job, LlmCallRow.role, LlmCallRow.model, LlmCallRow.error)
            found.append(or_(*(func.lower(column).contains(term, autoescape=True) for column in columns)))
        if self.models:
            found.append(LlmCallRow.model.in_(self.models))
        if self.roles:
            found.append(LlmCallRow.role.in_(self.roles))
        if self.steps:
            found.append(or_(*(step_condition(step) for step in self.steps)))
        if self.kinds:
            found.append(LlmCallRow.kind.in_(self.kinds))
        if self.statuses:
            found.append(LlmCallRow.status.in_(self.statuses))
        if self.epoch_from is not None:
            found.append(LlmCallRow.epoch >= self.epoch_from)
        if self.epoch_to is not None:
            found.append(LlmCallRow.epoch <= self.epoch_to)
        if self.since is not None:
            found.append(LlmCallRow.created_at >= self.since)
        return found


@dataclass(frozen=True)
class UsageTotals:
    calls: int
    input_tokens: int
    output_tokens: int
    turns: int
    errors: int
    partial: int
    retried: int
    milliseconds: int
    largest_call: int
    epochs: int
    first_at: datetime | None
    last_at: datetime | None


@dataclass(frozen=True)
class UsagePoint:
    epoch: int | None
    start: datetime | None
    calls: int
    input_tokens: int
    output_tokens: int
    errors: int


@dataclass(frozen=True)
class UsageShare:
    name: str
    calls: int
    input_tokens: int
    output_tokens: int
    errors: int
    milliseconds: int


@dataclass(frozen=True)
class UsageKindShare:
    kind: LlmCallKind
    calls: int
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class UsageStatusShare:
    status: LlmCallStatus
    calls: int
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class UsageFacets:
    calls: int
    models: list[str]
    roles: list[str]
    steps: list[str]
    epoch_low: int | None
    epoch_high: int | None


@dataclass(frozen=True)
class UsageReport:
    totals: UsageTotals
    timeline: list[UsagePoint]
    models: list[UsageShare]
    roles: list[UsageShare]
    steps: list[UsageShare]
    kinds: list[UsageKindShare]
    statuses: list[UsageStatusShare]
    facets: UsageFacets


@dataclass(frozen=True)
class UsageCalls:
    rows: list[LlmCallRow]
    total: int


def step_condition(step: str) -> ColumnElement[bool]:
    prefix = GROUP_PREFIXES.get(step)
    return LlmCallRow.job.startswith(prefix, autoescape=True) if prefix is not None else LlmCallRow.job == step


def bucket_start(key: str, pattern: str) -> datetime:
    return datetime.strptime(key, pattern).replace(tzinfo=UTC)


def errors_count() -> ColumnElement[int]:
    return func.coalesce(func.sum(case((LlmCallRow.status == LlmCallStatus.ERROR, 1), else_=0)), 0)


def by_tokens(shares: Sequence[UsageShare]) -> list[UsageShare]:
    return sorted(shares, key=lambda share: (-(share.input_tokens + share.output_tokens), share.name))


async def usage_totals(session: AsyncSession, conditions: list[ColumnElement[bool]]) -> UsageTotals:
    row = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(LlmCallRow.input_tokens), 0),
                func.coalesce(func.sum(LlmCallRow.output_tokens), 0),
                func.coalesce(func.sum(LlmCallRow.turns), 0),
                errors_count(),
                func.coalesce(func.sum(case((LlmCallRow.status == LlmCallStatus.PARTIAL, 1), else_=0)), 0),
                func.coalesce(func.sum(case((LlmCallRow.attempts > 1, 1), else_=0)), 0),
                func.coalesce(func.sum(LlmCallRow.duration_ms), 0),
                func.coalesce(func.max(TOTAL_TOKENS), 0),
                func.count(distinct(LlmCallRow.epoch)),
                func.min(LlmCallRow.created_at),
                func.max(LlmCallRow.created_at),
            ).where(*conditions)
        )
    ).one()
    return UsageTotals(
        calls=int(row[0]),
        input_tokens=int(row[1]),
        output_tokens=int(row[2]),
        turns=int(row[3]),
        errors=int(row[4]),
        partial=int(row[5]),
        retried=int(row[6]),
        milliseconds=int(row[7]),
        largest_call=int(row[8]),
        epochs=int(row[9]),
        first_at=row[10],
        last_at=row[11],
    )


async def usage_timeline(session: AsyncSession, conditions: list[ColumnElement[bool]], bucket: UsageBucket) -> list[UsagePoint]:
    sums = (func.count(), func.sum(LlmCallRow.input_tokens), func.sum(LlmCallRow.output_tokens), errors_count())
    shape = TIME_BUCKETS.get(bucket)
    if shape is None:
        rows = await session.execute(
            select(LlmCallRow.epoch, *sums).where(*conditions, LlmCallRow.epoch.is_not(None)).group_by(LlmCallRow.epoch).order_by(LlmCallRow.epoch)
        )
        return [UsagePoint(row[0], None, int(row[1]), int(row[2] or 0), int(row[3] or 0), int(row[4])) for row in rows]
    length, pattern = shape
    key = func.substr(LlmCallRow.created_at, 1, length, type_=String)
    rows = await session.execute(select(key, *sums).where(*conditions).group_by(key).order_by(key))
    return [UsagePoint(None, bucket_start(str(row[0]), pattern), int(row[1]), int(row[2] or 0), int(row[3] or 0), int(row[4])) for row in rows]


async def usage_shares(session: AsyncSession, conditions: list[ColumnElement[bool]], column: SQLColumnExpression[Any]) -> list[UsageShare]:
    rows = await session.execute(
        select(
            column,
            func.count(),
            func.sum(LlmCallRow.input_tokens),
            func.sum(LlmCallRow.output_tokens),
            errors_count(),
            func.sum(LlmCallRow.duration_ms),
        )
        .where(*conditions, column.is_not(None))
        .group_by(column)
        .order_by(column)
    )
    return [UsageShare(str(row[0]), int(row[1]), int(row[2] or 0), int(row[3] or 0), int(row[4]), int(row[5] or 0)) for row in rows]


def fold_steps(jobs: list[UsageShare]) -> list[UsageShare]:
    folded: dict[str, UsageShare] = {}
    for share in jobs:
        name = step_group(share.name)
        held = folded.get(name)
        folded[name] = (
            UsageShare(
                name,
                held.calls + share.calls,
                held.input_tokens + share.input_tokens,
                held.output_tokens + share.output_tokens,
                held.errors + share.errors,
                held.milliseconds + share.milliseconds,
            )
            if held is not None
            else UsageShare(name, share.calls, share.input_tokens, share.output_tokens, share.errors, share.milliseconds)
        )
    return by_tokens(list(folded.values()))


async def usage_kinds(session: AsyncSession, conditions: list[ColumnElement[bool]]) -> list[UsageKindShare]:
    rows = await session.execute(
        select(LlmCallRow.kind, func.count(), func.sum(LlmCallRow.input_tokens), func.sum(LlmCallRow.output_tokens))
        .where(*conditions)
        .group_by(LlmCallRow.kind)
        .order_by(LlmCallRow.kind)
    )
    return [UsageKindShare(LlmCallKind(row[0]), int(row[1]), int(row[2] or 0), int(row[3] or 0)) for row in rows]


async def usage_statuses(session: AsyncSession, conditions: list[ColumnElement[bool]]) -> list[UsageStatusShare]:
    rows = await session.execute(
        select(LlmCallRow.status, func.count(), func.sum(LlmCallRow.input_tokens), func.sum(LlmCallRow.output_tokens))
        .where(*conditions)
        .group_by(LlmCallRow.status)
        .order_by(LlmCallRow.status)
    )
    return [UsageStatusShare(LlmCallStatus(row[0]), int(row[1]), int(row[2] or 0), int(row[3] or 0)) for row in rows]


async def usage_facets(session: AsyncSession) -> UsageFacets:
    span = (await session.execute(select(func.count(), func.min(LlmCallRow.epoch), func.max(LlmCallRow.epoch)))).one()
    models = list(await session.scalars(select(LlmCallRow.model).distinct().order_by(LlmCallRow.model)))
    roles = list(await session.scalars(select(LlmCallRow.role).distinct().where(LlmCallRow.role.is_not(None)).order_by(LlmCallRow.role)))
    jobs = list(await session.scalars(select(LlmCallRow.job).distinct().order_by(LlmCallRow.job)))
    return UsageFacets(
        calls=int(span[0]),
        models=[str(model) for model in models],
        roles=[str(role) for role in roles],
        steps=sorted({step_group(job) for job in jobs}),
        epoch_low=span[1],
        epoch_high=span[2],
    )


async def usage_report(session: AsyncSession, chosen: UsageFilter, bucket: UsageBucket) -> UsageReport:
    conditions = chosen.conditions()
    return UsageReport(
        totals=await usage_totals(session, conditions),
        timeline=await usage_timeline(session, conditions, bucket),
        models=by_tokens(await usage_shares(session, conditions, LlmCallRow.model)),
        roles=by_tokens(await usage_shares(session, conditions, LlmCallRow.role)),
        steps=fold_steps(await usage_shares(session, conditions, LlmCallRow.job)),
        kinds=await usage_kinds(session, conditions),
        statuses=await usage_statuses(session, conditions),
        facets=await usage_facets(session),
    )


async def usage_calls(session: AsyncSession, chosen: UsageFilter, *, sort: UsageSort, descending: bool, offset: int, limit: int) -> UsageCalls:
    conditions = chosen.conditions()
    column = SORT_COLUMNS[sort]
    order = (column.desc(), LlmCallRow.id.desc()) if descending else (column.asc(), LlmCallRow.id.asc())
    rows = list(await session.scalars(select(LlmCallRow).where(*conditions).order_by(*order).offset(offset).limit(limit)))
    total = int(await session.scalar(select(func.count()).select_from(LlmCallRow).where(*conditions)) or 0)
    return UsageCalls(rows=rows, total=total)
