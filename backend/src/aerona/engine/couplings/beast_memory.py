from sqlalchemy import select

from aerona.catalog.knowledge import DYING_KNOWLEDGE
from aerona.db.tables.collective import AccountRow, AccountStanceRow
from aerona.db.tables.couplings import TeachingRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.recording.record import record
from aerona.engine.renown.lore import holdings


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


async def knowledge_dies(ctx: TickContext, holder: EntityRow) -> int:
    taught = set(await ctx.session.scalars(select(TeachingRow.kind).where(TeachingRow.teacher_node_id == holder.id)))
    lost = 0
    for kind in sorted(DYING_KNOWLEDGE - taught):
        if not await holdings(ctx.session, holder.id, kind):
            continue
        await record(ctx, "knowledge.lost_with_holder", roles={IncidentRole.SUBJECT: holder.id}, facts={"knowledge": kind})
        lost += 1
    return lost
