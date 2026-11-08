from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import InsufficientResourcesError, ValidationFailedError
from aerona.db.base import Base
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType

PRESERVED_TABLES = frozenset({"jobs", "rule_overrides"})
NOT_ENOUGH_ESSENCE = "Not enough essence: {rule} costs {amount}, the Creator has {have}."
NEGATIVE_AMOUNT = "An essence amount cannot be negative."


async def spend_essence(session: AsyncSession, amount: int, rule: str) -> int:
    if amount < 0:
        raise ValidationFailedError(NEGATIVE_AMOUNT)
    creator = await CosmosRepository(session).require_creator()
    if creator.essence < amount:
        raise InsufficientResourcesError(NOT_ENOUGH_ESSENCE.format(rule=rule, amount=amount, have=creator.essence))
    creator.essence -= amount
    await session.flush()
    return amount


async def refund_essence(session: AsyncSession, amount: int) -> int:
    creator = await CosmosRepository(session).require_creator()
    creator.essence += max(0, amount)
    await session.flush()
    return creator.essence


async def gain_essence(session: AsyncSession, amount: float) -> int:
    creator = await CosmosRepository(session).require_creator()
    creator.essence = max(0, creator.essence + round(amount))
    await session.flush()
    return creator.essence


async def visible_laws(session: AsyncSession, world_id: int) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.NATURAL_LAW,
            EntityRow.status == EntityStatus.CANON,
            or_(EntityRow.world_id == world_id, EntityRow.origin == EntityOrigin.COSMOS),
        )
        .order_by(EntityRow.id)
    )
    return list(await session.scalars(statement))


async def reset_world(session: AsyncSession) -> int:
    await session.flush()
    await session.execute(text("PRAGMA defer_foreign_keys = ON"))
    removed = 0
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in PRESERVED_TABLES:
            continue
        result = await session.execute(table.delete())
        removed += int(getattr(result, "rowcount", 0) or 0)
    session.expunge_all()
    return removed
