from aerona.catalog.dominion import DOMAIN_CURSES
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import Transmission
from aerona.engine.body.afflictions import afflict
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import god_of
from aerona.engine.faith.book import patron_node


async def curse_desecrator(ctx: TickContext, keeper_id: int, desecrator_id: int) -> None:
    god = await god_of(ctx.session, await patron_node(ctx.session, keeper_id))
    desecrator = await ctx.session.get(EntityRow, desecrator_id)
    if god is None or desecrator is None or held(desecrator.id):
        return
    await afflict(ctx, desecrator, DOMAIN_CURSES[god.domain_primary], Transmission.CURSE, source_node_id=god.id)
