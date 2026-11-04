from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.environment import PlaceEnvironmentRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import PlaceCover, WaterSource
from aerona.domain.enums.place import PlaceKind, SecretKind, SecretOrigin
from aerona.rules.registry import Rules
from tests.tools.factories import DESCRIPTION, make_entity, seed_realm, son_toolkit
from tests.tools.test_son_tools import ok, rejected

REASON = "because the land asked for it"


async def test_a_son_creates_a_typed_place_hides_a_secret_sanctifies_it_and_raises_a_nexus(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=12)
    link = [{"target_id": realm.people_id, "kind": "related", "description": "near them"}]
    created = await ok(
        toolkit,
        "create_place",
        {"place_kind": "grove", "name": "Sunmoss", "description": DESCRIPTION, "power_level": 1, "links": link, "location_id": realm.cosmos.region_id},
    )
    async with database.write() as session:
        place = await make_entity(session, "Stillwater", EntityType.PLACE, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
        session.add(PlaceEnvironmentRow(entity_id=place.id, cover=PlaceCover.OPEN, water_source=WaterSource.NONE, height_advantage=0, soil_fertility=50))
        grove = await session.scalar(select(PlaceProfileRow).where(PlaceProfileRow.kind == PlaceKind.GROVE))
        assert grove is not None, created
        place_id = place.id
    hidden = await ok(
        await son_toolkit(database, realm.son_id, action_points=12),
        "hide_secret",
        {"place_id": place_id, "kind": "lost_rite", "strength": 30, "reason": REASON},
    )
    assert "Stillwater" in hidden
    sanctified = await ok(await son_toolkit(database, realm.son_id, action_points=12), "sanctify_place", {"place_id": place_id, "reason": REASON})
    assert "sacredness" in sanctified
    await ok(await son_toolkit(database, realm.son_id, action_points=12), "raise_nexus", {"place_id": place_id, "reason": REASON})
    assert "already" in await rejected(await son_toolkit(database, realm.son_id, action_points=12), "raise_nexus", {"place_id": place_id, "reason": REASON})
    async with database.read() as session:
        secret = await session.scalar(select(PlaceSecretRow).where(PlaceSecretRow.place_entity_id == place_id))
        profile = await session.get(PlaceProfileRow, place_id)
        ground = await session.get(PlaceEnvironmentRow, place_id)
    assert secret is not None and secret.kind is SecretKind.LOST_RITE and secret.origin is SecretOrigin.SON and secret.school is not None
    assert profile is not None and profile.sacredness >= Rules().places.sanctify_amount and "sacredness" in profile.locked
    assert ground is not None and ground.nexus and "nexus" in ground.locked
    assert "not a place" in await rejected(
        await son_toolkit(database, realm.son_id, action_points=12), "sanctify_place", {"place_id": realm.cosmos.region_id, "reason": REASON}
    )
