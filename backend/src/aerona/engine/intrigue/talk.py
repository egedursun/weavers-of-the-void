from sqlalchemy import select

from aerona.db.tables.intrigue import SecretRow
from aerona.domain.enums.intrigue import BeliefSource, FavourOrigin, IntrigueSecret
from aerona.engine.context import TickContext
from aerona.engine.intrigue.beliefs import believe
from aerona.engine.intrigue.favours import call_favour, owe, owed_to
from aerona.engine.intrigue.secrets import keep_secret, learn, secrets_of
from aerona.engine.primitives.naming import seed_of
from aerona.engine.relations.book import relation

HONOUR_AT = 0
SECRET_SEVERITY = "secret_severity"


async def known_secrets(ctx: TickContext, knower_id: int, *, besides: int) -> list[SecretRow]:
    rows = await ctx.session.scalars(
        select(SecretRow)
        .where(SecretRow.exposed_epoch.is_(None), SecretRow.holder_node_id != knower_id, SecretRow.holder_node_id != besides)
        .order_by(SecretRow.id)
    )
    return [row for row in rows if knower_id in row.known_by]


async def gossip_secret(ctx: TickContext, actor: int, target: int) -> bool:
    if not ctx.rng(seed_of("intrigue.gossip", actor, target, ctx.epoch)).chance(ctx.rules.intrigue.gossip_pct):
        return False
    for secret in await known_secrets(ctx, actor, besides=target):
        if target not in secret.known_by and await learn(ctx, secret, target):
            await believe(
                ctx,
                target,
                secret.holder_node_id,
                SECRET_SEVERITY,
                secret.severity,
                source=BeliefSource.RUMOUR,
                confidence=ctx.rules.belief_state.rumour_confidence,
            )
            return True
    return False


async def confide_own(ctx: TickContext, actor: int, target: int) -> bool:
    if not ctx.rng(seed_of("intrigue.confide", actor, target, ctx.epoch)).chance(ctx.rules.intrigue.confide_pct):
        return False
    for secret in await secrets_of(ctx.session, actor):
        if secret.exposed_epoch is None and target not in secret.known_by and await learn(ctx, secret, target):
            return True
    return False


async def gift_earns(ctx: TickContext, giver: int, taker: int) -> None:
    await owe(ctx, taker, giver, FavourOrigin.GIFT, ctx.rules.intrigue.gift_favour)


async def ask_back(ctx: TickContext, asker: int, giver: int) -> bool | None:
    favour = await owed_to(ctx, asker, giver)
    if favour is None:
        return None
    back = await relation(ctx.session, giver, asker)
    return await call_favour(ctx, favour, honour=back is not None and back.friendship >= HONOUR_AT)


async def affair_secret(ctx: TickContext, first: int, second: int) -> None:
    await keep_secret(ctx, first, IntrigueSecret.AFFAIR, about_id=second, known_by=(second,), source="affair")
    await keep_secret(ctx, second, IntrigueSecret.AFFAIR, about_id=first, known_by=(first,), source="affair")
