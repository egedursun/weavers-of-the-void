from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.culture import LegendArchetype
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.lore.legends import drift_target
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import tick

VALUES = {ValueAxis.HONOUR: 60, ValueAxis.PIETY: 40, ValueAxis.DEATH: 30, ValueAxis.MARTIAL: 20}


async def test_legends_told_by_one_people_drift_to_every_shape_its_values_lean_to(session: AsyncSession) -> None:
    ctx = tick(session, Rules())
    shapes = {drift_target(ctx, EntityRow(id=number, name=f"Tale {number}"), VALUES, LegendArchetype.CREATION) for number in range(1, 80)}
    assert {LegendArchetype.BETRAYAL, LegendArchetype.CHOSEN_ONE, LegendArchetype.HAUNTED_PLACE, LegendArchetype.HERO_QUEST} <= shapes


async def test_a_legend_whose_shape_its_tellers_already_lean_to_keeps_it(session: AsyncSession) -> None:
    ctx = tick(session, Rules())
    assert drift_target(ctx, EntityRow(id=5, name="Tale"), VALUES, LegendArchetype.HAUNTED_PLACE) is None
