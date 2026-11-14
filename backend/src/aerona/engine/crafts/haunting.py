from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import EmotionSpiritRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import Emotion
from aerona.rules.registry import Rules


async def spirit_feelings(session: AsyncSession, rules: Rules) -> list[tuple[list[int], Emotion, float]]:
    found: list[tuple[list[int], Emotion, float]] = []
    for row in list(await session.scalars(select(EmotionSpiritRow).order_by(EmotionSpiritRow.id))):
        towns = list(
            await session.scalars(
                select(EntityRow.id)
                .where(EntityRow.location_id == row.region_entity_id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
                .order_by(EntityRow.id)
            )
        )
        if towns:
            found.append((towns, row.emotion, row.strength * rules.emotion_spirits.feed_pct / PERCENT))
    return found


async def bind_spirit(session: AsyncSession, binder_id: int, region_id: int | None) -> bool:
    if region_id is None or held(binder_id):
        return False
    row = await session.scalar(
        select(EmotionSpiritRow)
        .where(EmotionSpiritRow.region_entity_id == region_id, EmotionSpiritRow.bound_by_node_id.is_(None))
        .order_by(EmotionSpiritRow.strength.desc(), EmotionSpiritRow.id)
        .limit(1)
    )
    if row is None or "bound_by_node_id" in row.locked:
        return False
    row.bound_by_node_id = binder_id
    return True
