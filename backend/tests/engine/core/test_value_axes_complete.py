from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.mind import CultureValueRow
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.mind.values import add_into, pull_toward
from aerona.services.integrity.value_axes import complete_value_axes
from tests.engine.core.factories import CoreWorld


def test_a_vector_stored_before_an_axis_existed_can_still_be_pulled() -> None:
    current = {ValueAxis.PIETY: 20}
    target: dict[ValueAxis, float] = dict(current)
    pull_toward(target, current, {ValueAxis.FREEDOM: 40, ValueAxis.PIETY: 10}, 50)
    add_into(target, {ValueAxis.EQUALITY: 10}, 1)
    assert target[ValueAxis.FREEDOM] == 20
    assert target[ValueAxis.PIETY] == 15
    assert target[ValueAxis.EQUALITY] == 10


async def test_the_repair_gives_every_stored_vector_every_axis(session: AsyncSession, world: CoreWorld) -> None:
    session.add(CultureValueRow(entity_id=world.people.id, axis=ValueAxis.PIETY, value=30))
    await session.flush()
    added = await complete_value_axes(session)
    axes = set(await session.scalars(select(CultureValueRow.axis).where(CultureValueRow.entity_id == world.people.id)))
    assert added >= len(ValueAxis) - 1
    assert axes == set(ValueAxis)
    assert await complete_value_axes(session) == 0
