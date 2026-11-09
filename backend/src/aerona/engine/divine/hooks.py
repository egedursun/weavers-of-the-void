from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.warfare import WarSideRow
from aerona.domain.enums.divine import DomainHook
from aerona.engine.context import TickContext


async def sides_of(ctx: TickContext, entity_id: int) -> set[int]:
    sides = {entity_id}
    row = await ctx.session.get(EntityRow, entity_id)
    if row is not None and row.affiliated_entity_id is not None:
        sides.add(row.affiliated_entity_id)
    sides |= set(await ctx.session.scalars(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == entity_id)))
    return sides


async def foes_of(ctx: TickContext, entity_id: int) -> set[int]:
    sides = await sides_of(ctx, entity_id)
    mine = list(await ctx.session.scalars(select(WarSideRow).where(WarSideRow.entity_id.in_(sides), WarSideRow.left_epoch.is_(None))))
    if not mine:
        return set()
    ours = {row.war_id: row.side for row in mine}
    rows = await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id.in_(list(ours)), WarSideRow.left_epoch.is_(None)))
    return {row.entity_id for row in rows if row.side is not ours[row.war_id]}


async def foe_pct(ctx: TickContext, entity_id: int, hook: DomainHook) -> float:
    return max([await ctx.hook_pct(foe, hook) for foe in await foes_of(ctx, entity_id)], default=0.0)
