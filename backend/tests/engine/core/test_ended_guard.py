from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mortal import LifeStage
from aerona.engine.context import TickContext
from aerona.engine.interconnect.ended import RESTORED_COUNTER
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.phase import Phase
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, mortal


async def test_a_step_cannot_change_the_profile_of_one_who_ended_in_an_earlier_age_but_their_renown_lives_on(session: AsyncSession, world: CoreWorld) -> None:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = 3
    gone = await mortal(session, "Long Gone", world, None)
    gone.status, gone.end_epoch = EntityStatus.DEAD, 1
    session.add(MortalProfileRow(entity_id=gone.id, life_stage=LifeStage.ADULT, stress=10, renown=10))
    await session.flush()
    ctx = await manual_context(session, "ended_probe")

    async def stir(step: TickContext) -> None:
        profile = await step.session.get(MortalProfileRow, gone.id)
        assert profile is not None
        profile.stress, profile.renown = 60, 30

    await run_guarded(Phase("ended_probe_step", stir), TickContext(ctx.environment, session, "ended_probe_step"))
    profile = await session.get(MortalProfileRow, gone.id)
    assert profile is not None and profile.stress == 10 and profile.renown == 30
    assert ctx.environment.stats.counters[f"ended_probe_step.{RESTORED_COUNTER}.mortal_profiles.stress"] == 1


async def test_an_ending_step_may_settle_the_affairs_of_the_ended(session: AsyncSession, world: CoreWorld) -> None:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = 3
    gone = await mortal(session, "Settled", world, None)
    gone.status, gone.end_epoch = EntityStatus.DEAD, 1
    session.add(MortalProfileRow(entity_id=gone.id, life_stage=LifeStage.ADULT, stress=10))
    await session.flush()
    ctx = await manual_context(session, "ended_probe")

    async def settle(step: TickContext) -> None:
        profile = await step.session.get(MortalProfileRow, gone.id)
        assert profile is not None
        profile.stress = 0

    await run_guarded(Phase("affairs_of_the_ended", settle), TickContext(ctx.environment, session, "affairs_of_the_ended"))
    profile = await session.get(MortalProfileRow, gone.id)
    assert profile is not None and profile.stress == 0
