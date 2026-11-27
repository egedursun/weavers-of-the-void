from aerona.catalog.methods import PROCESS_OUTPUT, PROCESS_WORKSHOP, SEEDED_PROCESSES
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import GoodsFlow
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.stocks import epoch_need, goods_of, holding
from aerona.engine.primitives.stats import headcount

GOODS_FIXUP = "goods.w52"
HALF = 2


async def seed_new_goods(ctx: TickContext, book: EconomyBook) -> int:
    if not await fixup_due(ctx.session, GOODS_FIXUP):
        return 0
    seeded = 0
    ledger = goods_of(ctx.session, ctx.epoch)
    for community in book.communities:
        if held(community.id):
            continue
        for process in SEEDED_PROCESSES:
            if book.workshop(community.id, PROCESS_WORKSHOP[process]) is None:
                continue
            good = PROCESS_OUTPUT[process]
            amount = epoch_need(ctx.rules, headcount(community), good) // HALF
            if amount > 0 and await holding(ctx.session, community.id, good) == 0:
                await ledger.add(community.id, good, amount, GoodsFlow.SEED)
                seeded += 1
    ctx.session.add(AppliedFixupRow(key=GOODS_FIXUP, result={"stocks": seeded}))
    await ctx.session.flush()
    return seeded
