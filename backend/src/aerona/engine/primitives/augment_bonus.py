from collections.abc import Mapping

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.made import AugmentEffectRow, AugmentRow
from aerona.domain.enums.made import AugmentKind, AugmentSlot, EffectTarget

Lift = tuple[EffectTarget, str] | None
KIND_LIFT: Mapping[AugmentKind, Lift] = total(
    AugmentKind,
    {
        AugmentKind.REPLACEMENT: None,
        AugmentKind.ENHANCEMENT: None,
        AugmentKind.INTERFACE: (EffectTarget.CAPACITY, "cognition"),
        AugmentKind.WEAPON: (EffectTarget.ATTRIBUTE, "strength"),
        AugmentKind.REGULATOR: (EffectTarget.RESISTANCE, "will"),
        AugmentKind.SENSE: (EffectTarget.SENSE, "sight"),
        AugmentKind.STORAGE: (EffectTarget.ATTRIBUTE, "memory"),
        AugmentKind.COSMETIC: (EffectTarget.ATTRIBUTE, "social_awareness"),
    },
)
SLOT_LIFT: Mapping[AugmentSlot, Lift] = total(
    AugmentSlot,
    {
        AugmentSlot.PART: None,
        AugmentSlot.MIND: (EffectTarget.ATTRIBUTE, "focus"),
        AugmentSlot.SENSES: (EffectTarget.SENSE, "hearing"),
        AugmentSlot.SKIN: (EffectTarget.RESISTANCE, "material"),
        AugmentSlot.BLOOD: (EffectTarget.ATTRIBUTE, "disease_resistance"),
        AugmentSlot.WHOLE_BODY: (EffectTarget.ATTRIBUTE, "endurance"),
    },
)
LIFT_SHARE = 10


async def bonus(session: AsyncSession, node_id: int | None, target: EffectTarget, key: str) -> int:
    if node_id is None:
        return 0
    statement = (
        select(func.coalesce(func.sum(AugmentEffectRow.amount), 0))
        .join(AugmentRow, AugmentRow.id == AugmentEffectRow.augment_id)
        .where(AugmentRow.bearer_node_id == node_id, AugmentEffectRow.target == target, AugmentEffectRow.target_key == key)
    )
    explicit = int(await session.scalar(statement) or 0)
    implied = 0
    for row in await session.scalars(select(AugmentRow).where(AugmentRow.bearer_node_id == node_id)):
        for lift in (KIND_LIFT[row.kind], SLOT_LIFT[row.slot]):
            if lift == (target, key):
                implied += row.quality * row.integration // PERCENT // LIFT_SHARE
    return explicit + implied


async def lifts_of(session: AsyncSession, node_id: int, target: EffectTarget) -> dict[str, int]:
    found: dict[str, int] = {}
    rows = await session.execute(
        select(AugmentEffectRow.target_key, AugmentEffectRow.amount)
        .join(AugmentRow, AugmentRow.id == AugmentEffectRow.augment_id)
        .where(AugmentRow.bearer_node_id == node_id, AugmentEffectRow.target == target)
    )
    for key, amount in rows.all():
        found[key] = found.get(key, 0) + amount
    for row in await session.scalars(select(AugmentRow).where(AugmentRow.bearer_node_id == node_id)):
        for lift in (KIND_LIFT[row.kind], SLOT_LIFT[row.slot]):
            if lift is not None and lift[0] is target:
                found[lift[1]] = found.get(lift[1], 0) + row.quality * row.integration // PERCENT // LIFT_SHARE
    return found
