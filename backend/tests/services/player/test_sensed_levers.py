import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.epochs import DeferredStepRow
from aerona.db.tables.routes import HorizonIntuitionRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.epoch import DeferredStepStatus
from aerona.domain.enums.travel import HorizonStatus
from aerona.engine.phases.exploration import pending_intuitions
from aerona.services.player import horizon
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_brings_holds_retries_and_calls_off_a_sensed_world(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    seer = await make_entity(session, "Skywatcher", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    intuition = HorizonIntuitionRow(mortal_entity_id=seer.id, world_id=world.world.id, epoch=1, how="a light beyond the stars", status=HorizonStatus.PENDING)
    session.add(intuition)
    await session.flush()
    made = await horizon.request_sensed(scope, horizon.IntuitionTarget(intuition_id=intuition.id))
    step = await session.get(DeferredStepRow, made.values["step_id"])
    assert step is not None and step.status is DeferredStepStatus.PENDING
    with pytest.raises(ValidationFailedError):
        await horizon.request_sensed(scope, horizon.IntuitionTarget(intuition_id=intuition.id))
    await horizon.hold_sensed(scope, horizon.HoldSensedStep(step_id=step.id))
    assert step.status is DeferredStepStatus.HELD
    assert intuition.id not in {row.id for row in await pending_intuitions(session)}
    await horizon.hold_sensed(scope, horizon.HoldSensedStep(step_id=step.id, hold=False))
    assert step.status is DeferredStepStatus.PENDING
    step.status = DeferredStepStatus.FAILED
    await horizon.retry_sensed(scope, horizon.SensedStepTarget(step_id=step.id))
    assert step.status is DeferredStepStatus.PENDING and step.attempts == 0
    await horizon.cancel_sensed(scope, horizon.SensedStepTarget(step_id=step.id))
    assert await session.get(DeferredStepRow, step.id) is None
