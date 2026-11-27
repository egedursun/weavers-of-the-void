from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.world import Gravity
from aerona.engine.body.systems import BodySystemTally, harsher, keep_body_systems, settle_systems
from aerona.engine.body.tolerance import world_excess
from aerona.engine.context import TickContext
from aerona.rules.registry import Rules
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
    assert await world_excess(session, Rules(), world.people.id, world.world) > 0


async def test_a_system_fails_once_where_its_people_suffer_most_and_never_recovers_while_one_town_still_strains_it(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    session.add(BiologyRow(holder_entity_id=world.people.id, locked=[]))
    await session.flush()
    await keep_body_systems(ctx, BodySystemTally())
    rows = list(await session.scalars(select(BodySystemRow).where(BodySystemRow.holder_entity_id == world.people.id, BodySystemRow.present)))
    harsh, mild = world.regions[0].id, world.regions[1].id
    for _ in range(2):
        felt: dict[int, tuple[int, int]] = {}
        harsher(felt, {row.id: (0, mild) for row in rows})
        harsher(felt, {row.id: (80, harsh) for row in rows})
        tally = BodySystemTally()
        await settle_systems(ctx, world.people, rows, felt, tally)
    failed = list(await session.scalars(select(IncidentRow).where(IncidentRow.kind == "body.system_failed")))
    recovered = list(await session.scalars(select(IncidentRow).where(IncidentRow.kind.in_(["body.system_recovered", "body.adapted"]))))
    assert len(failed) == len(rows) and recovered == [] and tally.failed == 0
