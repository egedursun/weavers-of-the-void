from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import FavourRow, HookRow, SecretRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.intrigue import HookStrength
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.context import TickContext
from aerona.engine.mind.book import values_for
from aerona.engine.primitives.numbers import clamp_int, round_half_up


@dataclass
class DecayTally:
    favours_faded: int = 0
    favours_gone: int = 0
    secrets_staled: int = 0
    hooks_weakened: int = 0


async def gone(ctx: TickContext, node_id: int | None) -> bool:
    if node_id is None:
        return True
    entity = await ctx.session.get(EntityRow, node_id)
    return entity is not None and entity.status is not EntityStatus.CANON


async def fade_favours(ctx: TickContext, tally: DecayTally) -> None:
    table = ctx.rules.intrigue
    for row in list(await ctx.session.scalars(select(FavourRow).where(FavourRow.called_epoch.is_(None)).order_by(FavourRow.id))):
        if row.locked or held(row.owed_by_node_id) or held(row.owed_to_node_id):
            continue
        values = await values_for(ctx.session, row.owed_by_node_id)
        if await gone(ctx, row.owed_by_node_id) and values.get(ValueAxis.FAMILY, 0) < table.inherited_from:
            await ctx.session.delete(row)
            tally.favours_gone += 1
            continue
        weak = max(0, -values.get(ValueAxis.FRIENDSHIP, 0)) / PERCENT * table.weak_reciprocity_pct / PERCENT
        loss = max(1, round_half_up(row.magnitude * table.favour_decay_pct / PERCENT * (1 + weak)))
        row.magnitude = clamp_int(row.magnitude - loss, 0, PERCENT)
        tally.favours_faded += 1
        if row.magnitude <= 0:
            await ctx.session.delete(row)
            tally.favours_gone += 1


async def stale(ctx: TickContext, secret: SecretRow) -> bool:
    return secret.exposed_epoch is not None or (secret.about_node_id is not None and await gone(ctx, secret.about_node_id))


async def obsolete_secrets(ctx: TickContext, tally: DecayTally) -> None:
    table = ctx.rules.intrigue
    for secret in list(await ctx.session.scalars(select(SecretRow).where(SecretRow.severity > 0).order_by(SecretRow.id))):
        if "severity" in secret.locked or held(secret.holder_node_id) or not await stale(ctx, secret):
            continue
        secret.severity = clamp_int(secret.severity - max(1, round_half_up(secret.severity * table.obsolete_pct / PERCENT)), 0, PERCENT)
        tally.secrets_staled += 1
        for hook in list(await ctx.session.scalars(select(HookRow).where(HookRow.secret_id == secret.id))):
            if hook.locked or held(hook.holder_node_id) or held(hook.target_node_id):
                continue
            if secret.severity <= 0:
                await ctx.session.delete(hook)
                tally.hooks_weakened += 1
            elif hook.strength is HookStrength.STRONG and secret.severity < table.strong_at:
                hook.strength = HookStrength.WEAK
                tally.hooks_weakened += 1


async def keep_decays(ctx: TickContext, tally: DecayTally) -> None:
    await fade_favours(ctx, tally)
    await obsolete_secrets(ctx, tally)
    await ctx.session.flush()
