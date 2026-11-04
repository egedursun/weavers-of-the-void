from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.modifier_effects import StatEffect
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.primitives.modifiers import NEUTRAL_MULTIPLIER, UNMODIFIABLE_KEYS, VIRTUAL_KEYS, ModifierDraft, add_modifiers, forget_live
from aerona.engine.primitives.stats import has_stat
from aerona.rules.registry import Rules

Identity = tuple[int, str, ModifierSource, int | None, str | None]


@dataclass(frozen=True)
class Origin:
    source: ModifierSource
    reason: str
    epoch: int
    source_node_id: int | None = None
    group: str | None = None


def effect_draft(rules: Rules, target: EntityRow, effect: StatEffect, origin: Origin, *, factor: float = 1.0) -> ModifierDraft | None:
    return shaped_draft(target, effect.key, effect.op, effect.magnitude(rules), origin, factor=factor)


def shaped_draft(target: EntityRow, key: str, op: ModifierOp, size: float, origin: Origin, *, factor: float = 1.0) -> ModifierDraft | None:
    if key in UNMODIFIABLE_KEYS or not (has_stat(target, key) or key in VIRTUAL_KEYS):
        return None
    magnitude = round(size * factor, 3) if op is ModifierOp.ADD else round(NEUTRAL_MULTIPLIER + (size - NEUTRAL_MULTIPLIER) * factor, 4)
    if (op is ModifierOp.ADD and magnitude == 0) or (op is ModifierOp.MULTIPLY and magnitude == NEUTRAL_MULTIPLIER):
        return None
    return ModifierDraft(
        target.id, key, op, magnitude, origin.source, origin.reason, origin.epoch, source_node_id=origin.source_node_id, stacking_group=origin.group
    )


def identity_of(row: ModifierRow | ModifierDraft) -> Identity:
    return (row.target_node_id, row.target_key, row.source_kind, row.source_node_id, row.stacking_group)


async def replace_derived(
    session: AsyncSession, sources: Iterable[ModifierSource], drafts: Sequence[ModifierDraft], targets: Sequence[int] | None = None
) -> int:
    wanted = sorted(set(sources))
    statement = delete(ModifierRow).where(ModifierRow.source_kind.in_(wanted), ModifierRow.held.is_(False))
    kept_statement = select(ModifierRow).where(ModifierRow.source_kind.in_(wanted), ModifierRow.held.is_(True))
    if targets is not None:
        statement = statement.where(ModifierRow.target_node_id.in_(list(targets)))
        kept_statement = kept_statement.where(ModifierRow.target_node_id.in_(list(targets)))
        forget_live(targets, wanted)
    await session.execute(statement)
    held = {identity_of(row) for row in await session.scalars(kept_statement)}
    fresh = [draft for draft in drafts if identity_of(draft) not in held]
    await add_modifiers(session, fresh)
    return len(fresh)
