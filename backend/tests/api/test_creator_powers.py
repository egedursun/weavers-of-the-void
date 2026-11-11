from sqlalchemy import select

from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.repositories.sons import PowerDraft, SonRepository
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.routes import JourneyRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.son import PowerEffect, SonStatus
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus, TravelMethod
from aerona.domain.enums.world import WorldType
from aerona.domain.models.stats import StatBlock
from tests.api.conftest import ApiWorld, fund_creator, seeded
from tests.engine.cosmos.factories import make_route, make_world


async def foreign_god(api: ApiWorld, power: int = 40) -> int:
    async with api.services.database.write() as session:
        god = await ForeignGodRepository(session).create(
            ForeignGodDraft(
                name="Ushmar",
                world_id=seeded(api).core.world.id,
                domain_primary=Domain.DEATH,
                power=power,
                stats=StatBlock(strength=50, endurance=50, agility=50, wisdom=50, cunning=50, will=50, creativity=50, charisma=50, might=50),
                created_epoch=1,
            )
        )
        return god.id


async def test_strip_power_removes_one_power_and_returns_essence(api: ApiWorld) -> None:
    await fund_creator(api)
    son_id = seeded(api).core.son.id
    async with api.services.database.write() as session:
        await SonRepository(session).set_powers(
            son_id,
            [
                PowerDraft("Salt Sight", "Sees through brine.", PowerEffect.SEER),
                PowerDraft("Tide Voice", "Speaks to tides.", PowerEffect.CURSER),
            ],
        )
        powers = await SonRepository(session).powers(son_id)
    response = await api.http.post(f"/api/sons/{son_id}/strip-power", json={"slot": powers[0].slot})
    assert response.status_code == 200, response.text
    assert response.json()["action"] == "strip_power"
    async with api.services.database.read() as session:
        remaining = await SonRepository(session).powers(son_id)
    assert [power.name for power in remaining] == ["Tide Voice"]
    assert (await api.http.post(f"/api/sons/{son_id}/strip-power", json={"slot": 99})).status_code == 400
    assert (await api.http.post("/api/sons/999999/strip-power", json={"slot": 1})).status_code == 404


async def test_manifest_leaves_a_dream_message_for_the_entity(api: ApiWorld) -> None:
    await fund_creator(api)
    town = seeded(api).core.extra["town"].id
    response = await api.http.post(f"/api/entities/{town}/manifest", json={"words": "Build the sea wall."})
    assert response.status_code == 200, response.text
    async with api.services.database.read() as session:
        messages = list(await session.scalars(select(MessageRow).where(MessageRow.recipient_node_id == town)))
    assert [message.text for message in messages] == ["Build the sea wall."]
    assert (await api.http.post(f"/api/entities/{town}/manifest", json={"words": "  "})).status_code == 400


async def test_convert_turns_a_community_to_the_creator(api: ApiWorld) -> None:
    await fund_creator(api)
    town = seeded(api).core.extra["town"].id
    response = await api.http.post(f"/api/entities/{town}/convert", json={})
    assert response.status_code == 200, response.text
    again = await api.http.post(f"/api/entities/{town}/convert", json={})
    assert again.status_code == 400
    assert "already worships only you" in again.text


async def test_rite_needs_a_dead_son_and_credits_devotion(api: ApiWorld) -> None:
    await fund_creator(api)
    town = seeded(api).core.extra["town"].id
    son_id = seeded(api).core.son.id
    living = await api.http.post(f"/api/entities/{town}/rite", json={"son_id": son_id, "kind": "prayer"})
    assert living.status_code == 400
    async with api.services.database.write() as session:
        son = await SonRepository(session).require_son(son_id)
        son.status = SonStatus.DEAD
        son.death_epoch = 1
    done = await api.http.post(f"/api/entities/{town}/rite", json={"son_id": son_id, "kind": "prayer"})
    assert done.status_code == 200, done.text
    assert done.json()["action"] == "rite"


async def test_drain_and_kill_a_foreign_god(api: ApiWorld) -> None:
    await fund_creator(api)
    god_id = await foreign_god(api)
    drained = await api.http.post(f"/api/foreign-gods/{god_id}/drain", json={})
    assert drained.status_code == 200, drained.text
    async with api.services.database.read() as session:
        assert (await session.get(ForeignGodRow, god_id)).power < 40
    killed = await api.http.post(f"/api/foreign-gods/{god_id}/kill", json={"reason": "It stole the sea.", "devour": True})
    assert killed.status_code == 200, killed.text
    assert (await api.http.post(f"/api/foreign-gods/{god_id}/kill", json={})).status_code == 400
    assert (await api.http.post(f"/api/foreign-gods/{god_id}/drain", json={})).status_code == 400
    assert (await api.http.post("/api/foreign-gods/999999/drain", json={})).status_code == 404


async def test_recall_returns_a_voyage_home(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        other = await make_world(session, "Velmor", WorldType.ASTEROID_BELT)
        route = await make_route(session, core.world.id, other.id, TravelMethod.ANCIENT_GATE)
        journey = JourneyRow(
            traveller_entity_id=core.people.id,
            route_id=route.id,
            origin_world_id=core.world.id,
            destination_world_id=other.id,
            intent=JourneyIntent.COLONY,
            population=100,
            epochs_left=2,
            status=JourneyStatus.UNDERWAY,
            start_epoch=1,
        )
        session.add(journey)
        await session.flush()
        journey_id = journey.id
    response = await api.http.post(f"/api/voyages/{journey_id}/recall", json={})
    assert response.status_code == 200, response.text
    async with api.services.database.read() as session:
        assert (await session.get(JourneyRow, journey_id)).status is JourneyStatus.RECALLED
    assert (await api.http.post(f"/api/voyages/{journey_id}/recall", json={})).status_code == 400
    assert (await api.http.post("/api/voyages/999999/recall", json={})).status_code in (400, 404)
