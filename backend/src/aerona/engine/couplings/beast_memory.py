from sqlalchemy import select

from aerona.db.tables.collective import AccountRow, AccountStanceRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.recording.record import record


async def memory_dies(ctx: TickContext, beast: EntityRow) -> int:
    rows = list(await ctx.session.scalars(select(AccountRow).where(AccountRow.holder_entity_id == beast.id)))
    if not rows:
        return 0
    for row in rows:
        for stance in await ctx.session.scalars(select(AccountStanceRow).where(AccountStanceRow.account_id == row.id)):
            await ctx.session.delete(stance)
        await ctx.session.delete(row)
    await record(ctx, "lore.memory_died", roles={IncidentRole.SUBJECT: beast.id})
    await ctx.session.flush()
    return len(rows)
