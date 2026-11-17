from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.place import PlaceSecretRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.place import DiscoveryMode
from tests.tools.every_setup import buried_secret
from tests.tools.factories import seed_realm, son_toolkit


async def test_a_son_brings_a_buried_secret_to_light_by_its_own_hand(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        ids = await buried_secret(session, realm)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    outcome = await toolkit.runtime.call("reveal_secret", {"place_id": realm.cosmos.place_id, "reason": "The relic should be known."})
    assert not outcome.is_error, outcome.text
    async with database.read() as session:
        secret = await session.get(PlaceSecretRow, ids["secret"])
        assert secret is not None
        assert secret.revealed_by is DiscoveryMode.SON
        incident = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "place.secret_buried_relic"))
        assert incident is not None
        actor = await session.scalar(
            select(IncidentParticipantRow.node_id).where(IncidentParticipantRow.incident_id == incident.id, IncidentParticipantRow.role == IncidentRole.ACTOR)
        )
        assert actor == realm.son_id
        mode = await session.scalar(select(IncidentFactRow.enum_value).where(IncidentFactRow.incident_id == incident.id, IncidentFactRow.key == "mode"))
        assert mode == DiscoveryMode.SON.value


async def test_a_son_finds_nothing_where_no_secret_lies(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    outcome = await toolkit.runtime.call("reveal_secret", {"place_id": realm.cosmos.place_id, "reason": "The relic should be known."})
    assert outcome.is_error
