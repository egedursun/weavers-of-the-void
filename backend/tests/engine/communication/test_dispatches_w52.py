from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.communication import SignalLinkRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.domain.enums.communication import DispatchContent, DispatchState, EnvoyFate, Medium, SignalKind, SignalState
from aerona.engine.communication.dispatches import DispatchTally, deliver, expel
from aerona.engine.communication.post import send
from aerona.engine.communication.signals import SignalTally, jam, tend_stations
from aerona.engine.context import TickContext
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat_or
from tests.engine.core.conftest import ctx, database, rules, session, world
from tests.engine.core.factories import CoreWorld, mortal, settlement

__all__ = ["ctx", "database", "rules", "session", "world"]


async def test_a_forged_message_arrives_as_a_forgery_and_a_misread_one_as_misread(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    first = await settlement(session, "Reedhold", world, world.regions[0])
    second = await settlement(session, "Fenhold", world, world.regions[0])
    forged = await send(ctx, first.id, second.id, DispatchContent.ORDER, Medium.LETTER, forged=True)
    misread = await send(ctx, first.id, second.id, DispatchContent.REPORT, Medium.LETTER)
    assert forged is not None and misread is not None
    misread.misread, misread.locked = True, ["misread"]
    await deliver(ctx, forged, DispatchTally())
    await deliver(ctx, misread, DispatchTally())
    assert forged.state is DispatchState.FORGED and misread.state is DispatchState.MISREAD


async def test_a_warning_that_arrives_readies_the_town(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    seat = await settlement(session, "Reedhold", world, world.regions[0])
    town = await settlement(session, "Fenhold", world, world.regions[0])
    before = stat_or(town, "defense", 0)
    row = await send(ctx, seat.id, town.id, DispatchContent.WARNING, Medium.LETTER)
    assert row is not None
    tally = DispatchTally()
    await deliver(ctx, row, tally)
    assert tally.warned == 1 and stat_or(town, "defense", 0) > before


async def test_an_envoy_is_sent_home_short_of_war(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    sender = await settlement(session, "Reedhold", world, world.regions[0])
    host = await settlement(session, "Fenhold", world, world.regions[0])
    envoy = await mortal(session, "Tal Envoy", world, sender.id)
    row = await send(ctx, sender.id, host.id, DispatchContent.PROPOSAL, Medium.ENVOY, envoy_id=envoy.id)
    assert row is not None
    assert await expel(ctx, row, host.id)
    assert row.envoy_fate is EnvoyFate.EXPELLED


async def test_a_jammed_station_carries_nothing_for_a_season_and_then_resumes(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    owner = await settlement(session, "Reedhold", world, world.regions[0])
    link = SignalLinkRow(
        owner_node_id=owner.id,
        kind=SignalKind.BEACON_CHAIN,
        from_region_id=world.regions[0].id,
        to_region_id=world.regions[1].id,
        state=SignalState.ACTIVE,
        locked=[],
    )
    session.add(link)
    await session.flush()
    assert await jam(ctx, link, owner.id)
    assert link.state is SignalState.JAMMED and link.jammed_epoch == ctx.epoch
    cosmos = await session.get(CosmosRow, world.cosmos.id)
    assert cosmos is not None
    cosmos.epoch = ctx.epoch + 1
    await session.flush()
    later = await manual_context(session, "signals")
    await tend_stations(later, SignalTally())
    assert link.state is SignalState.ACTIVE
