from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository
from aerona.db.tables.interconnect import IncidentParticipantRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from tests.services.app.factories import Cosmos


async def son_role(session: AsyncSession, incident_id: int | None, son_id: int) -> IncidentRole | None:
    query = select(IncidentParticipantRow.role).where(IncidentParticipantRow.incident_id == incident_id, IncidentParticipantRow.node_id == son_id)
    return await session.scalar(query)


async def test_a_son_attached_to_a_record_that_has_its_own_actor_joins_as_an_ally(session: AsyncSession, world: Cosmos) -> None:
    repository = ChronicleRepository(session)
    fought = await repository.append(
        ChronicleDraft(
            epoch=1,
            kind=ChronicleKind.WAR,
            text="A town won.",
            entity_ids=[world.people.id],
            participants=[(world.people.id, IncidentRole.ACTOR)],
            son_id=world.son.id,
        )
    )
    alone = await repository.append(ChronicleDraft(epoch=1, kind=ChronicleKind.WAR, text="The son acted.", son_id=world.son.id))
    assert await son_role(session, fought.incident_id, world.son.id) is IncidentRole.ALLY
    assert await son_role(session, alone.incident_id, world.son.id) is IncidentRole.ACTOR
