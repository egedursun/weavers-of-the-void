from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.gatherings import CollectionIncidentRow
from aerona.db.tables.interconnect import IncidentParticipantRow
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.unions import UnionForm, UnionPurpose
from aerona.engine.history.collections import CollectionTally, gather_incidents, join_or_open
from aerona.engine.primitives.manual import manual_context
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, mortal, settlement


async def test_each_founding_keeps_its_own_story_though_one_people_founds_many(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "founding_collections", Rules())
    first = await settlement(session, "Reedholm", world, world.regions[0])
    second = await settlement(session, "Saltby", world, world.regions[1])
    tally = CollectionTally()

    async def founded(town_id: int) -> int:
        members = {world.people.id: CollectionRole.FOUNDER, town_id: CollectionRole.PRODUCT}
        row = await join_or_open(ctx, CollectionKind.FOUNDING, world_id=world.world.id, members=members, places=[], source_key="births.village", tally=tally)
        assert row is not None
        return row.id

    one, two, again = await founded(first.id), await founded(second.id), await founded(first.id)
    assert one != two and again == one


async def test_two_weddings_seen_by_the_same_witness_keep_their_own_stories(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "wedding_collections", Rules())
    town = await settlement(session, "Banns", world, world.regions[0])
    first, second, third, fourth, onlooker = [await mortal(session, name, world, town.id) for name in ("Ira", "Oda", "Uri", "Eda", "Ada")]
    weddings = []
    for pair in ((first, second), (third, fourth)):
        incident = await record(
            ctx,
            "kin.marriage",
            roles={IncidentRole.SPOUSE: [pair[0].id, pair[1].id]},
            facts={"form": UnionForm.PAIR, "purpose": UnionPurpose.LOVE},
            place=town.id,
        )
        assert incident is not None
        session.add(IncidentParticipantRow(incident_id=incident.incident_id, node_id=onlooker.id, role=IncidentRole.WITNESS))
        weddings.append(incident.incident_id)
    await session.flush()
    await gather_incidents(ctx, CollectionTally())
    await session.flush()
    homes: list[int | None] = []
    for wedding in weddings:
        homes.append(await session.scalar(select(CollectionIncidentRow.collection_id).where(CollectionIncidentRow.incident_id == wedding)))
    assert None not in homes and len(set(homes)) == 2
