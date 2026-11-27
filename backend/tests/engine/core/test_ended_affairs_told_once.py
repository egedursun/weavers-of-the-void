from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.lifecycle.affairs import AffairTally, close_affairs
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, mortal


async def test_affairs_of_someone_long_dead_close_quietly_while_a_fresh_end_is_told(session: AsyncSession, world: CoreWorld) -> None:
    cosmos = await session.scalar(select(CosmosRow).limit(1))
    assert cosmos is not None
    cosmos.epoch = 5
    long_dead = await mortal(session, "Old Bran", world, None)
    fresh = await mortal(session, "New Cal", world, None)
    friend = await mortal(session, "Dee", world, None)
    long_dead.status, long_dead.end_epoch = EntityStatus.DEAD, 1
    fresh.status, fresh.end_epoch = EntityStatus.DEAD, 5
    bonds = BondRepository(session)
    old_tie = await bonds.connect(BondDraft(long_dead.id, friend.id, BondKind.ALLY, 1))
    new_tie = await bonds.connect(BondDraft(fresh.id, friend.id, BondKind.ALLY, 4))
    await session.flush()
    await close_affairs(await manual_context(session, "affairs"), AffairTally())
    told = set(
        await session.scalars(
            select(IncidentParticipantRow.node_id)
            .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
            .where(IncidentRow.kind == "lifecycle.affairs_closed", IncidentParticipantRow.role == IncidentRole.SUBJECT)
        )
    )
    assert old_tie.state is not BondState.ACTIVE and new_tie.state is not BondState.ACTIVE
    assert told == {fresh.id}
