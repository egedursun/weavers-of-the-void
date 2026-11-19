from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import ACT_READINGS
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.standing import ProfessionOfValueRow
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.context import TickContext
from aerona.engine.standing.hypocrisy import HypocrisyTally, keep_hypocrisy, professed_act
from tests.engine.core.factories import CoreWorld, mortal, tuned_rules


def certain(ctx: TickContext) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(standing={"exposure_pct": 100})))


async def test_an_act_against_a_professed_value_widens_the_gap(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    act, axis = next((act, axis) for act, readings in ACT_READINGS.items() for axis, weight in readings.items() if weight < 0)
    doer = await mortal(session, "Ostra", world, world.regions[0].id)
    session.add(ProfessionOfValueRow(holder_node_id=doer.id, axis=axis, strength=70, locked=[]))
    await session.flush()
    await professed_act(ctx, doer.id, act, 2)
    row = await session.scalar(select(ProfessionOfValueRow).where(ProfessionOfValueRow.holder_node_id == doer.id))
    assert row is not None and row.gap == ctx.rules.standing.gap_per_act and row.acts_against == 1 and row.knowers == 2


async def test_a_wide_known_gap_comes_out_and_is_forgiven_once_it_closes(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    doer = await mortal(session, "Brenn", world, world.regions[0].id)
    session.add(ProfessionOfValueRow(holder_node_id=doer.id, axis=ValueAxis.HONOUR, strength=70, gap=80, knowers=3, locked=[]))
    await session.flush()
    await keep_hypocrisy(certain(ctx), HypocrisyTally())
    row = await session.scalar(select(ProfessionOfValueRow).where(ProfessionOfValueRow.holder_node_id == doer.id))
    assert row is not None and row.exposed
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "standing.hypocrisy_exposed")) is not None
    row.gap = 0
    await session.flush()
    await keep_hypocrisy(certain(ctx), HypocrisyTally())
    assert not row.exposed
