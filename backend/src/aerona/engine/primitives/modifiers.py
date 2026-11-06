from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.write_guard import free_rows
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.rules.registry import Rules

NEUTRAL_MULTIPLIER = 1.0
GUARD_SOURCES = (ModifierSource.PIN, ModifierSource.SUPPRESSION)
UNMODIFIABLE_KEYS = frozenset({"population", "followers", "size"})
GROWTH_KEY = "growth"
VIRTUAL_KEYS: dict[str, float] = {GROWTH_KEY: 1.0}


@dataclass
class LiveModifiers:
    index: "ModifierIndex"
    epoch: int
    rules: Rules


LIVE_MODIFIERS: ContextVar[LiveModifiers | None] = ContextVar("live_modifiers", default=None)


@contextmanager
def live_modifiers(index: "ModifierIndex", epoch: int, rules: Rules) -> Iterator[None]:
    token = LIVE_MODIFIERS.set(LiveModifiers(index, epoch, rules))
    try:
        yield
    finally:
        LIVE_MODIFIERS.reset(token)


def live_contributions(node_id: int, key: str) -> list["Contribution"]:
    live = LIVE_MODIFIERS.get()
    if live is None or key in UNMODIFIABLE_KEYS or not live.index.has(node_id, key):
        return []
    return live.index.contributions(node_id, key)


@dataclass(frozen=True)
class ModifierDraft:
    target_node_id: int
    target_key: str
    op: ModifierOp
    magnitude: float
    source_kind: ModifierSource
    reason_key: str
    start_epoch: int
    source_node_id: int | None = None
    stacking_group: str | None = None
    end_epoch: int | None = None
    decay_pct: int | None = None


@dataclass(frozen=True)
class Contribution:
    modifier_id: int
    op: ModifierOp
    magnitude: float
    source_kind: ModifierSource
    source_node_id: int | None
    reason_key: str
    stacking_group: str | None
    held: bool = False


@dataclass(frozen=True)
class Breakdown:
    base: float
    applied: tuple[Contribution, ...]
    ignored: tuple[Contribution, ...]
    value: float


def _strongest(contributions: list[Contribution], op: ModifierOp) -> Contribution | None:
    candidates = [item for item in contributions if item.op is op]
    if not candidates:
        return None
    if op is ModifierOp.ADD:
        return max(candidates, key=lambda item: (abs(item.magnitude), -item.modifier_id))
    return max(candidates, key=lambda item: (abs(item.magnitude - NEUTRAL_MULTIPLIER), -item.modifier_id))


def combine(base: float, contributions: Iterable[Contribution]) -> Breakdown:
    grouped: dict[str, list[Contribution]] = {}
    applied: list[Contribution] = []
    for item in contributions:
        if item.stacking_group is None:
            applied.append(item)
        else:
            grouped.setdefault(item.stacking_group, []).append(item)
    ignored: list[Contribution] = []
    for members in grouped.values():
        kept = [winner for op in ModifierOp if (winner := _strongest(members, op)) is not None]
        applied.extend(kept)
        ignored.extend(item for item in members if item not in kept)
    total = base + sum(item.magnitude for item in applied if item.op is ModifierOp.ADD)
    for item in applied:
        if item.op is ModifierOp.MULTIPLY:
            total *= item.magnitude
    ordered = tuple(sorted(applied, key=lambda item: item.modifier_id))
    return Breakdown(base=base, applied=ordered, ignored=tuple(sorted(ignored, key=lambda item: item.modifier_id)), value=total)


def base_for(contributions: Iterable[Contribution], value: float) -> float | None:
    breakdown = combine(0.0, contributions)
    adds = sum(item.magnitude for item in breakdown.applied if item.op is ModifierOp.ADD)
    product = 1.0
    for item in breakdown.applied:
        if item.op is ModifierOp.MULTIPLY:
            product *= item.magnitude
    if product == 0:
        return None
    return value / product - adds


class ModifierIndex:
    def __init__(self, rows: Iterable[ModifierRow]) -> None:
        self._by_target: dict[tuple[int, str], list[Contribution]] = {}
        for row in rows:
            self._by_target.setdefault((row.target_node_id, row.target_key), []).append(
                Contribution(row.id, row.op, row.magnitude, row.source_kind, row.source_node_id, row.reason_key, row.stacking_group, row.held)
            )

    @classmethod
    async def load(cls, session: AsyncSession, epoch: int, node_ids: Iterable[int] | None = None) -> "ModifierIndex":
        statement = select(ModifierRow).where(
            ModifierRow.start_epoch <= epoch,
            or_(ModifierRow.end_epoch.is_(None), ModifierRow.end_epoch >= epoch),
            ModifierRow.source_kind.not_in(GUARD_SOURCES),
        )
        if node_ids is not None:
            statement = statement.where(ModifierRow.target_node_id.in_(list(node_ids)))
        return cls(await session.scalars(statement.order_by(ModifierRow.id)))

    def contributions(self, node_id: int, key: str) -> list[Contribution]:
        return list(self._by_target.get((node_id, key), ()))

    def breakdown(self, node_id: int, key: str, base: float) -> Breakdown:
        return combine(base, self.contributions(node_id, key))

    def effective(self, node_id: int, key: str, base: float) -> float:
        return self.breakdown(node_id, key, base).value

    def add(self, row: ModifierRow) -> None:
        if row.source_kind in GUARD_SOURCES:
            return
        self._by_target.setdefault((row.target_node_id, row.target_key), []).append(
            Contribution(row.id, row.op, row.magnitude, row.source_kind, row.source_node_id, row.reason_key, row.stacking_group, row.held)
        )

    def discard(self, node_ids: Iterable[int], sources: Iterable[ModifierSource]) -> None:
        nodes = set(node_ids)
        dropped = set(sources)
        for target in [target for target in self._by_target if target[0] in nodes]:
            self._by_target[target] = [item for item in self._by_target[target] if item.source_kind not in dropped]
            if not self._by_target[target]:
                del self._by_target[target]

    def has(self, node_id: int, key: str) -> bool:
        return (node_id, key) in self._by_target

    def keys_of(self, node_id: int) -> list[str]:
        return sorted(key for target, key in self._by_target if target == node_id)


def forget_live(node_ids: Iterable[int], sources: Iterable[ModifierSource]) -> None:
    live = LIVE_MODIFIERS.get()
    if live is not None:
        live.index.discard(node_ids, sources)


def virtual_value(node_id: int, key: str) -> float:
    return combine(VIRTUAL_KEYS[key], live_contributions(node_id, key)).value


def live_sources(node_id: int, key: str) -> frozenset[ModifierSource]:
    return frozenset(item.source_kind for item in live_contributions(node_id, key))


def row_of(draft: ModifierDraft, *, held: bool = False) -> ModifierRow:
    return ModifierRow(
        target_node_id=draft.target_node_id,
        target_key=draft.target_key,
        op=draft.op,
        magnitude=draft.magnitude,
        source_kind=draft.source_kind,
        source_node_id=draft.source_node_id,
        stacking_group=draft.stacking_group,
        start_epoch=draft.start_epoch,
        end_epoch=draft.end_epoch,
        decay_pct=draft.decay_pct,
        reason_key=draft.reason_key,
        held=held,
    )


async def add_modifiers(session: AsyncSession, drafts: Iterable[ModifierDraft]) -> list[ModifierRow]:
    rows = [row_of(draft) for draft in drafts if draft.target_key not in UNMODIFIABLE_KEYS or draft.source_kind in GUARD_SOURCES]
    if not rows:
        return []
    session.add_all(rows)
    await session.flush()
    live = LIVE_MODIFIERS.get()
    if live is not None:
        for row in rows:
            if row.start_epoch <= live.epoch and (row.end_epoch is None or row.end_epoch >= live.epoch):
                live.index.add(row)
    return rows


async def add_modifier(session: AsyncSession, draft: ModifierDraft, *, held: bool = False) -> ModifierRow:
    row = ModifierRow(
        target_node_id=draft.target_node_id,
        target_key=draft.target_key,
        op=draft.op,
        magnitude=draft.magnitude,
        source_kind=draft.source_kind,
        source_node_id=draft.source_node_id,
        stacking_group=draft.stacking_group,
        start_epoch=draft.start_epoch,
        end_epoch=draft.end_epoch,
        decay_pct=draft.decay_pct,
        reason_key=draft.reason_key,
        held=held,
    )
    if draft.target_key in UNMODIFIABLE_KEYS and draft.source_kind not in GUARD_SOURCES:
        raise ValueError(f"{draft.target_key} is a conserved count and cannot carry a modifier.")
    session.add(row)
    await session.flush()
    live = LIVE_MODIFIERS.get()
    if live is not None and row.start_epoch <= live.epoch and (row.end_epoch is None or row.end_epoch >= live.epoch):
        live.index.add(row)
    return row


async def remove_modifiers(
    session: AsyncSession, *, source_kind: ModifierSource | None = None, source_node_id: int | None = None, target_node_id: int | None = None
) -> int:
    statement = delete(ModifierRow).where(free_rows(ModifierRow.target_node_id))
    if source_kind is not None:
        statement = statement.where(ModifierRow.source_kind == source_kind)
    if source_node_id is not None:
        statement = statement.where(ModifierRow.source_node_id == source_node_id)
    if target_node_id is not None:
        statement = statement.where(ModifierRow.target_node_id == target_node_id)
    result = await session.execute(statement)
    return int(getattr(result, "rowcount", 0) or 0)


def decayed(row: ModifierRow) -> float:
    keep = 1 - (row.decay_pct or 0) / PERCENT
    if row.op is ModifierOp.ADD:
        return row.magnitude * keep
    return NEUTRAL_MULTIPLIER + (row.magnitude - NEUTRAL_MULTIPLIER) * keep
