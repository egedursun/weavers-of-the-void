from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.warfare import ArmyRow, BattleRow, CaptiveRow, SiegeRow, TributeRow, WarRow, WarSideRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.war import BattleOutcome, CaptiveStatus, SiegeStatus, TributeStatus, WarCause, WarSide, WarStatus
from aerona.domain.models.entity_stats import EventStats
from tests.api.conftest import ApiWorld
from tests.services.player.factories import PlayerWorld, make_entity, seed_player_world


async def _world(api: ApiWorld) -> tuple[PlayerWorld, int, int]:
    async with api.services.database.write() as session:
        world = await seed_player_world(session)
        first = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
        second = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
        return world, first.id, second.id


async def _war(session: AsyncSession, world: PlayerWorld, first: int, second: int) -> int:
    event = await make_entity(session, "The Salt War", EntityType.EVENT, world_id=world.world.id, location_id=world.region.id, stats=EventStats())
    war = WarRow(event_entity_id=event.id, world_id=world.world.id, status=WarStatus.ONGOING, cause=WarCause.DECLARED, started_epoch=1, battles=1)
    session.add(war)
    await session.flush()
    session.add_all(
        [
            WarSideRow(war_id=war.id, entity_id=first, side=WarSide.ATTACKER, joined_epoch=1),
            WarSideRow(war_id=war.id, entity_id=second, side=WarSide.DEFENDER, joined_epoch=1),
            ArmyRow(entity_id=first, war_id=war.id, owner_entity_id=first, raised_epoch=1),
            SiegeRow(war_id=war.id, besieged_entity_id=second, besieger_entity_id=first, status=SiegeStatus.ONGOING, started_epoch=1),
            BattleRow(war_id=war.id, epoch=1, sequence=1, winner_entity_id=first, loser_entity_id=second, outcome=BattleOutcome.FIELD_VICTORY, gap=1.5),
            CaptiveRow(captive_entity_id=second, captor_entity_id=first, war_id=war.id, status=CaptiveStatus.HELD, taken_epoch=1),
            TributeRow(payer_entity_id=second, receiver_entity_id=first, war_id=war.id, status=TributeStatus.ACTIVE, since_epoch=1),
        ]
    )
    await session.flush()
    return war.id


async def test_phase_listing_and_manual_run(empty_api: ApiWorld) -> None:
    await _world(empty_api)
    listing = (await empty_api.http.get("/api/engine/phases")).json()["phases"]
    assert {"diplomacy", "advance_epoch", "campaigns"} <= {item["name"] for item in listing}
    diplomacy = next(item for item in listing if item["name"] == "diplomacy")
    assert diplomacy["enabled"] and diplomacy["runnable"]
    ran = await empty_api.http.post("/api/actions/engine:run_phase", json={"phase": "diplomacy"})
    assert ran.status_code == 200, ran.text
    assert ran.json()["action"] == "engine:run_phase"
    assert (await empty_api.http.post("/api/actions/engine:run_phase", json={"phase": "advance_epoch"})).status_code == 400
    assert (await empty_api.http.post("/api/actions/engine:run_phase", json={"phase": "not_a_step"})).status_code == 404


async def test_integrity_tasks_can_be_listed_and_run(empty_api: ApiWorld) -> None:
    await _world(empty_api)
    tasks = (await empty_api.http.get("/api/integrity/tasks")).json()["tasks"]
    assert {item["task"] for item in tasks} == {"dead_bonds", "checkpoint", "schema_checks"}
    swept = await empty_api.http.post("/api/integrity/dead_bonds")
    assert swept.status_code == 200, swept.text
    assert set(swept.json()["counters"]) == {"closed", "transferred"}
    folded = await empty_api.http.post("/api/integrity/checkpoint")
    assert folded.status_code == 200
    assert (await empty_api.http.post("/api/integrity/unknown")).status_code == 400


async def test_relations_can_be_set_read_and_feuded_over_http(empty_api: ApiWorld) -> None:
    _, first, second = await _world(empty_api)
    http = empty_api.http
    set_value = await http.put(f"/api/entities/{first}/relations/{second}", json={"value": 55})
    assert set_value.status_code == 200, set_value.text
    pair = (await http.get(f"/api/entities/{first}/relations/{second}")).json()
    assert pair["value"] == 55 and pair["blood_feud_since_epoch"] is None
    assert pair["history"][-1]["delta"] != 0
    feud = await http.post(f"/api/entities/{first}/relations/{second}/feud")
    assert feud.status_code == 200, feud.text
    listing = (await http.get(f"/api/entities/{first}/relations")).json()
    assert listing["relations"][0]["other"]["id"] == second
    assert listing["relations"][0]["blood_feud_since_epoch"] is not None
    ended = await http.delete(f"/api/entities/{first}/relations/{second}/feud")
    assert ended.status_code == 200
    assert (await http.get(f"/api/entities/{first}/relations/999999")).status_code == 404


async def test_war_read_model_lists_every_part_of_a_war(empty_api: ApiWorld) -> None:
    world, first, second = await _world(empty_api)
    async with empty_api.services.database.write() as session:
        war_id = await _war(session, world, first, second)
    http = empty_api.http
    wars = (await http.get("/api/wars", params={"status": "ongoing"})).json()
    assert wars["total"] == 1
    summary = wars["items"][0]
    assert summary["event"]["name"] == "The Salt War"
    assert {side["side"] for side in summary["sides"]} == {"attacker", "defender"}
    assert (await http.get("/api/wars", params={"status": "ended"})).json()["total"] == 0
    assert (await http.get(f"/api/wars/{war_id}")).json()["id"] == war_id
    for part in ("armies", "battles", "sieges"):
        page = (await http.get(f"/api/wars/{war_id}/{part}")).json()
        assert page["total"] == 1, part
    captives = (await http.get("/api/captives", params={"community_id": first})).json()
    assert captives["items"][0]["captive"]["id"] == second
    tributes = (await http.get("/api/tributes", params={"war_id": war_id})).json()
    assert tributes["items"][0]["payer"]["id"] == second
    community = (await http.get(f"/api/entities/{first}/wars")).json()
    assert community["total"] == 1
    assert (await http.get(f"/api/entities/{first}/heroes")).json() == []
    assert (await http.get("/api/wars/999999")).status_code == 404
