from sqlalchemy import select

from aerona.db.tables.collective import AccountRow, AccountStanceRow
from aerona.db.tables.entities import EntityRow
from aerona.engine.context import TickContext
from aerona.engine.notes import note


async def memory_dies(ctx: TickContext, beast: EntityRow) -> int:
    rows = list(await ctx.session.scalars(select(AccountRow).where(AccountRow.holder_entity_id == beast.id)))
    if not rows:
        return 0
    for row in rows:
        for stance in await ctx.session.scalars(select(AccountStanceRow).where(AccountStanceRow.account_id == row.id)):
            await ctx.session.delete(stance)
        await ctx.session.delete(row)
    await note(ctx, f"The memory of an age died with {beast.name}; only what it taught or told is left.", key="lore.memory_died", ids=[beast.id])
    await ctx.session.flush()
    return len(rows)
