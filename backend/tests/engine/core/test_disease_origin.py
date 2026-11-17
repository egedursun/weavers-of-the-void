from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.engine.disease.origin import ORIGIN_LOCK, caused_by_origin, mark_strain_origin, origin_incident, origin_line
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, tell_history


async def incident_of(session: AsyncSession, chronicle_id: int) -> IncidentRow:
    found = await session.scalar(select(IncidentRow).where(IncidentRow.chronicle_id == chronicle_id))
    assert found is not None
    return found


async def test_a_strain_remembers_where_it_first_rose_and_later_tellings_point_back(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    profile = DiseaseProfileRow(locked=[])
    assert await origin_incident(ctx, profile) is None and await origin_line(ctx, None) == ""
    first = await tell_history(ctx, "A sickness changed in the valley.", ids=[world.regions[0].id])
    await mark_strain_origin(ctx, profile, first)
    origin = await incident_of(session, first.id)
    assert profile.origin_incident_id == origin.id
    assert str(origin.epoch) in await origin_line(ctx, profile)
    later = await tell_history(ctx, "The sickness stayed in the valley.", ids=[world.regions[0].id])
    await caused_by_origin(ctx, later, profile)
    assert (await incident_of(session, later.id)).cause_incident_id == origin.id
    await caused_by_origin(ctx, first, profile)
    assert origin.cause_incident_id is None


async def test_a_held_origin_is_kept(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    profile = DiseaseProfileRow(locked=[ORIGIN_LOCK])
    row = await tell_history(ctx, "A sickness changed in the valley.", ids=[world.regions[0].id])
    await mark_strain_origin(ctx, profile, row)
    await mark_strain_origin(ctx, None, row)
    assert profile.origin_incident_id is None
