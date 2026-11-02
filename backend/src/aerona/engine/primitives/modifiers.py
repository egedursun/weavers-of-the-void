from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.interconnect import ModifierRow
from aerona.domain.enums.modifier import ModifierOp, ModifierSource

NEUTRAL_MULTIPLIER = 1.0
GUARD_SOURCES = (ModifierSource.PIN, ModifierSource.SUPPRESSION)


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


class ModifierIndex:
    def __init__(self, rows: Iterable[ModifierRow]) -> None:
        self._by_target: dict[tuple[int, str], list[Contribution]] = {}
        for row in rows:
            self._by_target.setdefault((row.target_node_id, row.target_key), []).append(
                Contribution(row.id, row.op, row.magnitude, row.source_kind, row.source_node_id, row.reason_key, row.stacking_group)
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

    def keys_of(self, node_id: int) -> list[str]:
        return sorted(key for target, key in self._by_target if target == node_id)


async def add_modifier(session: AsyncSession, draft: ModifierDraft) -> ModifierRow:
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
    )
    session.add(row)
    await session.flush()
    return row


async def remove_modifiers(
    session: AsyncSession, *, source_kind: ModifierSource | None = None, source_node_id: int | None = None, target_node_id: int | None = None
) -> int:
    statement = delete(ModifierRow)
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
