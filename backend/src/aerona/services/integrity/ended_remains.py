from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.military.command_ends import lay_down_command
from aerona.engine.primitives.stats import set_stats, stat

EMPTIED_FLAGS = (EntityFlag.RUIN, EntityFlag.ABANDONED)


async def dead_with_health(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.DEAD).order_by(EntityRow.id)
    )
    return [row.id for row in rows if (stat(row, "hp") or 0) > 0 and not held(row.id)]


async def still_the_dead(session: AsyncSession, mortal_id: int) -> None:
    row = await session.get(EntityRow, mortal_id)
    if row is not None and row.status is EntityStatus.DEAD:
        set_stats(row, hp=0)


async def armies_led_by_the_dead(session: AsyncSession) -> list[int]:
    commander = EntityRow.__table__.alias("commander")
    rows = await session.execute(
        select(ArmyRow.commander_entity_id)
        .join(commander, commander.c.id == ArmyRow.commander_entity_id)
        .where(ArmyRow.disbanded_epoch.is_(None), commander.c.status != EntityStatus.CANON)
        .order_by(ArmyRow.commander_entity_id)
    )
    found: list[int] = []
    for (mortal_id,) in rows:
        if mortal_id is not None and mortal_id not in found:
            found.append(mortal_id)
    return found


async def release_their_commands(session: AsyncSession, mortal_id: int) -> None:
    row = await session.get(EntityRow, mortal_id)
    if row is not None and row.status is not EntityStatus.CANON:
        await lay_down_command(session, mortal_id, row.end_epoch or 0)


async def ruins_still_peopled(session: AsyncSession) -> list[int]:
    emptied = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag.in_(EMPTIED_FLAGS))
    rows = await session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status != EntityStatus.CANON, EntityRow.id.in_(emptied))
        .order_by(EntityRow.id)
    )
    return [row.id for row in rows if (stat(row, "population") or 0) > 0 and not held(row.id)]


async def empty_the_ruin(session: AsyncSession, settlement_id: int) -> None:
    row = await session.get(EntityRow, settlement_id)
    if row is not None and row.status is not EntityStatus.CANON:
        with flowing(FlowCategory.TRANSFORMATION):
            set_stats(row, population=0)
