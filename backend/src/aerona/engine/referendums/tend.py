from aerona.db.write_guard import held
from aerona.engine.context import TickContext
from aerona.engine.referendums.book import ReferendumTally, pending
from aerona.engine.referendums.voting import assembly_questions, hold, petitions


async def tend_referendums(ctx: TickContext) -> ReferendumTally:
    tally = ReferendumTally()
    for row in await pending(ctx.session):
        if row.called_epoch < ctx.epoch and not held(row.holder_node_id) and "result" not in (row.locked or []):
            await hold(ctx, row, tally)
    await petitions(ctx, tally)
    await assembly_questions(ctx, tally)
    return tally
