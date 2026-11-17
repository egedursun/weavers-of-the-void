from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.total import total
from aerona.db.tables.outer_agency import OuterHeraldRow, OuterIncursionRow, OuterPactRow, OuterPlanRow, OuterRelationRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.outer import OuterGoal, OuterPrice
from aerona.domain.models.entity_stats import OuterBeingStats
from aerona.engine.divine.outer import found_outer_cult, outer_profile
from aerona.engine.divine.outer_agency import FULFIL, choose_goal, cults_of, fulfil_enter, fulfil_worship, outer_agency, strike_bargain, tempt
from aerona.engine.primitives.queries import connect
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement
from tests.engine.core.test_minds_w44 import at


async def test_an_aim_to_be_worshipped_founds_a_cult_the_being_counts(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4)
    await settlement(session, "Oddmere", world, world.regions[0])
    being = await entity(session, "The Far Listener", EntityType.OUTER_BEING, OuterBeingStats(size=40, interest=50, influence=30), world_id=world.world.id)
    plan = OuterPlanRow(outer_entity_id=being.id, goal=OuterGoal.BE_WORSHIPPED, started_epoch=ctx.epoch, locked=[])
    await fulfil_worship(ctx, being, plan)
    assert len(await cults_of(ctx, being.id)) == 1
    await fulfil_worship(ctx, being, plan)
    assert len(await cults_of(ctx, being.id)) == 1


async def test_a_member_of_an_outer_cult_strikes_a_pact_and_service_binds_a_herald(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4, outer_beings={"bargain_pct": 100})
    town = await settlement(session, "Oddmere", world, world.regions[0])
    being = await entity(session, "The Far Listener", EntityType.OUTER_BEING, OuterBeingStats(size=40, interest=50, influence=30), world_id=world.world.id)
    cult = await found_outer_cult(ctx, town)
    await connect(session, cult.id, being.id, BondKind.WORSHIPS, ctx.epoch, description="serves")
    member = await mortal(session, "Wren", world, town.id)
    await connect(session, member.id, cult.id, BondKind.MEMBER_OF, ctx.epoch, description="sworn")
    assert await tempt(ctx, being) == 1
    assert await session.scalar(select(OuterPactRow.id).where(OuterPactRow.holder_node_id == member.id)) is not None
    servant = await mortal(session, "Ash", world, town.id)
    await strike_bargain(ctx, being, servant, OuterPrice.SERVICE)
    await session.flush()
    assert await session.scalar(select(OuterHeraldRow.outer_entity_id).where(OuterHeraldRow.herald_node_id == servant.id)) == being.id


async def test_an_aim_to_enter_opens_an_incursion_and_two_beings_take_a_stance(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4)
    first = await entity(session, "The Far Listener", EntityType.OUTER_BEING, OuterBeingStats(size=40, interest=50, influence=30), world_id=world.world.id)
    second = await entity(session, "The Near Hunger", EntityType.OUTER_BEING, OuterBeingStats(size=30, interest=50, influence=30), world_id=world.world.id)
    await fulfil_enter(ctx, first, OuterPlanRow(outer_entity_id=first.id, goal=OuterGoal.ENTER, started_epoch=ctx.epoch, locked=[]))
    assert await session.scalar(select(OuterIncursionRow.id).where(OuterIncursionRow.outer_entity_id == first.id)) is not None
    await outer_agency(ctx)
    pair = (min(first.id, second.id), max(first.id, second.id))
    found = await session.scalars(select(OuterRelationRow))
    assert pair in {(min(row.outer_entity_id, row.other_entity_id), max(row.outer_entity_id, row.other_entity_id)) for row in found}


FILLS_A_LACK: Mapping[OuterGoal, bool] = total(
    OuterGoal,
    {
        OuterGoal.FEED: True,
        OuterGoal.OPEN_RIFT: True,
        OuterGoal.BE_WORSHIPPED: True,
        OuterGoal.UNMAKE_LAW: False,
        OuterGoal.GAIN_NAME: False,
        OuterGoal.ENTER: False,
    },
)


async def test_every_aim_that_fills_a_lack_is_not_chosen_again_once_fulfilled(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 4)
    await settlement(session, "Oddmere", world, world.regions[0])
    being = await entity(session, "The Far Listener", EntityType.OUTER_BEING, OuterBeingStats(size=40, interest=50, influence=60), world_id=world.world.id)
    profile = await outer_profile(ctx, being)
    profile.fed = 0
    chosen: list[OuterGoal] = []
    for _ in OuterGoal:
        goal, target = await choose_goal(ctx, being, profile)
        chosen.append(goal)
        if not FILLS_A_LACK[goal]:
            break
        await FULFIL[goal](ctx, being, OuterPlanRow(outer_entity_id=being.id, goal=goal, target_node_id=target, started_epoch=ctx.epoch, locked=[]))
        await session.flush()
        assert (await choose_goal(ctx, being, profile))[0] is not goal
    assert [goal for goal in chosen if FILLS_A_LACK[goal]] == [OuterGoal.FEED, OuterGoal.OPEN_RIFT, OuterGoal.BE_WORSHIPPED]
    assert not FILLS_A_LACK[chosen[-1]]
