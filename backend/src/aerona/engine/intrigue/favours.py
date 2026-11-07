from sqlalchemy import select

from aerona.db.tables.intrigue import FavourRow, HookRow
from aerona.db.write_guard import held
from aerona.domain.enums.intrigue import FavourOrigin, HookDemand, HookStrength
from aerona.engine.context import TickContext
from aerona.engine.mortal.standing import add_honour
from aerona.engine.relations.book import ensure_relation, shift


async def owe(ctx: TickContext, owed_by: int, owed_to: int, origin: FavourOrigin, magnitude: int) -> FavourRow | None:
    if owed_by == owed_to or held(owed_by) or magnitude <= 0:
        return None
    found = await ctx.session.scalar(
        select(FavourRow).where(FavourRow.owed_by_node_id == owed_by, FavourRow.owed_to_node_id == owed_to, FavourRow.called_epoch.is_(None)).limit(1)
    )
    if found is not None:
        if not found.locked:
            found.magnitude = min(100, found.magnitude + magnitude)
        return found
    row = FavourRow(owed_by_node_id=owed_by, owed_to_node_id=owed_to, magnitude=min(100, magnitude), origin=origin, created_epoch=ctx.epoch)
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def owed_to(ctx: TickContext, creditor: int, debtor: int) -> FavourRow | None:
    found: FavourRow | None = await ctx.session.scalar(
        select(FavourRow)
        .where(FavourRow.owed_by_node_id == debtor, FavourRow.owed_to_node_id == creditor, FavourRow.called_epoch.is_(None))
        .order_by(FavourRow.magnitude.desc())
        .limit(1)
    )
    return found


async def call_favour(ctx: TickContext, favour: FavourRow, *, honour: bool) -> bool:
    if favour.called_epoch is not None or favour.locked or held(favour.owed_by_node_id):
        return False
    table = ctx.rules.intrigue
    favour.called_epoch, favour.honoured = ctx.epoch, honour
    view = await ensure_relation(ctx.session, favour.owed_to_node_id, favour.owed_by_node_id, ctx.epoch)
    if view is not None:
        shift(ctx.rules, view, ctx.epoch, friendship=table.favour_trust if honour else -table.favour_refusal)
    if not honour:
        await add_honour(ctx.session, favour.owed_by_node_id, -table.favour_refusal, ctx.epoch)
    return honour


async def use_hook(ctx: TickContext, hook: HookRow, demand: HookDemand) -> bool:
    if hook.used_epoch is not None or held(hook.target_node_id):
        return False
    complied = hook.strength is HookStrength.STRONG or ctx.rng(f"intrigue.hook.{hook.id}.{ctx.epoch}").chance(ctx.rules.intrigue.hook_comply_pct)
    hook.last_demand = demand
    if hook.strength is HookStrength.WEAK and not hook.locked:
        hook.used_epoch = ctx.epoch
    return complied


async def hook_on(ctx: TickContext, holder_id: int, target_id: int) -> HookRow | None:
    found: HookRow | None = await ctx.session.scalar(
        select(HookRow).where(HookRow.holder_node_id == holder_id, HookRow.target_node_id == target_id, HookRow.used_epoch.is_(None)).limit(1)
    )
    return found
