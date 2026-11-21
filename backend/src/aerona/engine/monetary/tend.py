from sqlalchemy import select

from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.monetary import MonetaryAuthorityRow
from aerona.db.write_guard import held
from aerona.engine.context import TickContext
from aerona.engine.monetary.authorities import MonetaryTally, authority_of, establish
from aerona.engine.monetary.policy import tend_authority

LEGACY_FIXUP = "monetary.legacy_authorities"


async def apply_legacy(ctx: TickContext, tally: MonetaryTally) -> None:
    if await ctx.session.get(AppliedFixupRow, LEGACY_FIXUP) is not None:
        return
    for currency in await ctx.session.scalars(select(CurrencyRow).order_by(CurrencyRow.id)):
        if held(currency.issuer_entity_id) or await authority_of(ctx.session, currency.id) is not None:
            continue
        await establish(ctx, currency)
        tally.founded += 1
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result={"authorities": tally.founded}))
    await ctx.session.flush()


async def tend_money_policy(ctx: TickContext) -> MonetaryTally:
    tally = MonetaryTally()
    await apply_legacy(ctx, tally)
    for authority in list(await ctx.session.scalars(select(MonetaryAuthorityRow).order_by(MonetaryAuthorityRow.id))):
        await tend_authority(ctx, authority, tally)
    return tally
