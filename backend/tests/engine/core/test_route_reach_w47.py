from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.cosmography import SCOPE_ORDER
from aerona.catalog.travel import METHOD_REACH
from aerona.domain.enums.travel import TravelMethod
from aerona.engine.cosmos import routes
from aerona.engine.cosmos.placement import within_reach
from tests.engine.core.factories import CoreWorld, add_empty_world


async def test_a_far_passage_takes_a_method_that_reaches_or_none(session: AsyncSession, world: CoreWorld, monkeypatch: pytest.MonkeyPatch) -> None:
    other, _ = await add_empty_world(session)
    farthest = SCOPE_ORDER[-1]

    async def far(_session: AsyncSession) -> SimpleNamespace:
        return SimpleNamespace(scope=lambda _first, _second: farthest)

    monkeypatch.setattr(routes, "cosmography_of", far)
    method = await routes.reaching(session, world.world, other, TravelMethod.ANCIENT_GATE)
    assert method is None or within_reach(farthest, METHOD_REACH[method])
    if not within_reach(farthest, METHOD_REACH[TravelMethod.ANCIENT_GATE]):
        assert method is not TravelMethod.ANCIENT_GATE


async def test_a_near_passage_keeps_the_method_its_worlds_prefer(session: AsyncSession, world: CoreWorld) -> None:
    other, _ = await add_empty_world(session)
    assert await routes.reaching(session, world.world, other, TravelMethod.ANCIENT_GATE) is TravelMethod.ANCIENT_GATE
