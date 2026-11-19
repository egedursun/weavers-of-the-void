from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.body_systems import BodySystemRow
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.world import Gravity
from aerona.engine.body.systems import BodySystemTally, keep_body_systems
from aerona.engine.body.tolerance import world_excess
from aerona.engine.context import TickContext
from tests.engine.core.factories import CoreWorld


async def test_a_people_gains_its_systems_and_a_breathless_body_has_no_breath(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(BiologyRow(holder_entity_id=world.people.id, breathes=False, locked=[]))
    await session.flush()
    await keep_body_systems(ctx, BodySystemTally())
    rows = {row.system: row for row in await session.scalars(select(BodySystemRow).where(BodySystemRow.holder_entity_id == world.people.id))}
    assert set(rows) == set(BodySystem) - {BodySystem.NONE}
    assert not rows[BodySystem.BREATH].present and rows[BodySystem.NERVES].present


async def test_a_world_heavier_than_a_body_bears_strains_it(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(BiologyRow(holder_entity_id=world.people.id, locked=[]))
    await session.flush()
    await keep_body_systems(ctx, BodySystemTally())
    world.world.gravity = Gravity.HIGH
    for row in await session.scalars(select(BodySystemRow).where(BodySystemRow.holder_entity_id == world.people.id)):
        row.gravity_max = 30
    await session.flush()
    assert await world_excess(session, world.people.id, world.world) > 0
