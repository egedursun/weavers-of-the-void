from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.engine.body.variants import HOLDER_TYPES, holders, rederive, seed_biology, variants_of
from aerona.rules.registry import Rules


async def seed_missing_biology(session: AsyncSession, rules: Rules, epoch: int) -> int:
    del rules
    rows = {row.holder_entity_id: row for row in await session.scalars(select(BiologyRow))}
    mended = 0
    for holder_id, row in list(rows.items()):
        holder = await session.get(EntityRow, holder_id)
        if holder is None or holder.entity_type not in HOLDER_TYPES:
            await session.delete(row)
            del rows[holder_id]
            mended += 1
            continue
        known = [variant.value for variant in variants_of(row.variants)]
        if known != list(row.variants):
            row.variants = known
            mended += 1
        mended += rederive(row)
    for holder_id in await holders(session):
        if holder_id not in rows:
            await seed_biology(session, holder_id, epoch)
            mended += 1
    await session.flush()
    return mended
