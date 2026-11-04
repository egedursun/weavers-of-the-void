from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.body import BodyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import TraitRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import TraitKind
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.body.book import STAT_CAPACITY, temperament_factor
from aerona.engine.primitives.derivation import Origin, shaped_draft
from aerona.engine.primitives.modifiers import ModifierDraft
from aerona.rules.registry import Rules

INJURY_REASON = "modifier.injury"
TRAIT_REASON = "modifier.trait"


async def _mortals(session: AsyncSession, node_ids: Sequence[int] | None) -> dict[int, EntityRow]:
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    if node_ids is not None:
        statement = statement.where(EntityRow.id.in_(list(node_ids)))
    return {row.id: row for row in await session.scalars(statement.order_by(EntityRow.id))}


async def body_drafts(session: AsyncSession, rules: Rules, epoch: int, node_ids: Sequence[int] | None = None) -> list[ModifierDraft]:
    mortals = await _mortals(session, node_ids)
    if not mortals:
        return []
    drafts: list[ModifierDraft] = []
    for body in await session.scalars(select(BodyRow).where(BodyRow.node_id.in_(list(mortals))).order_by(BodyRow.node_id)):
        mortal = mortals[body.node_id]
        for key, capacity in STAT_CAPACITY.items():
            value: int = getattr(body, capacity.value)
            origin = Origin(ModifierSource.INJURY, INJURY_REASON, epoch, group=f"injury.{key}")
            if value < PERCENT and (draft := shaped_draft(mortal, key, ModifierOp.MULTIPLY, value / PERCENT, origin)) is not None:
                drafts.append(draft)
    held: dict[int, list[TraitKind]] = defaultdict(list)
    for row in await session.scalars(select(TraitRow).where(TraitRow.node_id.in_(list(mortals))).order_by(TraitRow.node_id, TraitRow.trait)):
        held[row.node_id].append(row.trait)
    for node_id, traits in held.items():
        for key, capacity in STAT_CAPACITY.items():
            origin = Origin(ModifierSource.TRAIT, TRAIT_REASON, epoch, group=f"trait.{key}")
            if (draft := shaped_draft(mortals[node_id], key, ModifierOp.MULTIPLY, temperament_factor(rules, traits, capacity), origin)) is not None:
                drafts.append(draft)
    return drafts
