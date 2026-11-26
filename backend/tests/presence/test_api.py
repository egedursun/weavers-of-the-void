from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.son import SonDeathCause, SonStatus
from aerona.prompts.schemas.presence import PresenceAnswer
from tests.api.conftest import ApiWorld, seeded
from tests.divine_will.scripted import Say, ScriptedWill
from tests.presence.beings import foreign_god
from tests.presence.conftest import say, summon

MISSING = 999999


async def test_the_speaker_list_pages_filters_and_marks_open_audiences(presence: ApiWorld) -> None:
    core = seeded(presence).core
    async with presence.services.database.write() as session:
        await foreign_god(session, core)
    first = (await presence.http.get("/api/presence/speakers", params={"limit": 1})).json()
    assert first["offset"] == 0 and first["limit"] == 1 and len(first["speakers"]) == 1
    assert first["total"] >= 3 and first["has_more"] is True
    everyone = (await presence.http.get("/api/presence/speakers", params={"limit": 200})).json()
    groups = {row["group"] for row in everyone["speakers"]}
    assert {"sons", "foreign_gods", "mortals", "spirits"} <= groups
    gods = (await presence.http.get("/api/presence/speakers", params={"group": "foreign_gods"})).json()
    assert [row["name"] for row in gods["speakers"]] == ["Ombrun"]
    assert gods["speakers"][0]["kind"] == "foreign_god" and gods["speakers"][0]["entity_type"] is None
    found = (await presence.http.get("/api/presence/speakers", params={"q": "Ilvane"})).json()
    assert [row["node_id"] for row in found["speakers"]] == [core.extra["sage"].id]
    assert found["speakers"][0]["open_session_id"] is None and found["speakers"][0]["cover"] is None
    opened = await summon(presence, core.extra["sage"].id)
    again = (await presence.http.get("/api/presence/speakers", params={"q": "Ilvane"})).json()
    assert again["speakers"][0]["open_session_id"] == opened["session"]["id"]
    bad = await presence.http.get("/api/presence/speakers", params={"group": "nobody"})
    assert bad.status_code == 400


async def test_the_dead_are_listed_on_request_and_their_card_tells_their_death(presence: ApiWorld) -> None:
    core = seeded(presence).core
    async with presence.services.database.write() as session:
        son = await session.get(SonRow, core.son.id)
        lover = await session.get(EntityRow, core.extra["lover"].id)
        assert son is not None and lover is not None
        son.status, son.death_epoch, son.death_cause = SonStatus.DEAD, 2, SonDeathCause.DEVOURED
        lover.status, lover.end_epoch = EntityStatus.DEAD, 1
        profile = await session.get(MortalProfileRow, lover.id)
        if profile is not None:
            profile.cause_of_death = DeathCause.OLD_AGE
    living = (await presence.http.get("/api/presence/speakers", params={"limit": 200})).json()
    assert core.son.id not in [row["node_id"] for row in living["speakers"]]
    dead = (await presence.http.get("/api/presence/speakers", params={"limit": 200, "dead": True})).json()
    assert {row["node_id"] for row in dead["speakers"] if row["dead"]} == {core.son.id, core.extra["lover"].id}
    card = (await presence.http.get(f"/api/presence/speakers/{core.son.id}")).json()["card"]
    assert card["dead"] is True and card["death_epoch"] == 2 and card["son_death_cause"] == "devoured"
    assert card["son_status"] == "dead" and card["entity_status"] is None and card["can_act"] is False
    mortal = (await presence.http.get(f"/api/presence/speakers/{core.extra['lover'].id}")).json()["card"]
    assert mortal["dead"] is True and mortal["death_epoch"] == 1 and mortal["entity_status"] == "dead"


async def test_a_speaker_card_names_place_world_patron_and_tongues(presence: ApiWorld) -> None:
    core = seeded(presence).core
    view = (await presence.http.get(f"/api/presence/speakers/{core.extra['sage'].id}")).json()
    card = view["card"]
    assert card["name"] == "Ilvane" and card["group"] == "mortals" and card["entity_type"] == "mortal"
    assert card["place_name"] == core.extra["town"].name and card["world_name"] == core.world.name
    assert card["can_act"] is True and card["dead"] is False
    assert view["open_session"] is None and view["past_sessions"] == []
    assert view["remembered_exchanges"] == presence.services.rules.current.presence.remembered_exchanges
    assert view["model_enabled"] is True
    son = (await presence.http.get(f"/api/presence/speakers/{core.son.id}")).json()["card"]
    assert son["faith"] is not None and son["epithet"] == core.son.title


async def test_only_beings_with_minds_can_be_summoned(presence: ApiWorld) -> None:
    core = seeded(presence).core
    silent = await presence.http.get(f"/api/presence/speakers/{core.people.id}")
    assert (silent.status_code, silent.json()) == (200, None)
    silent = await presence.http.get(f"/api/presence/speakers/{core.creator.id}")
    assert (silent.status_code, silent.json()) == (200, None)
    assert (await presence.http.get(f"/api/presence/speakers/{MISSING}")).status_code == 404
    refused = await presence.http.post("/api/presence/sessions", json={"node_id": core.people.id, "guise": "creator", "record": "on_record"})
    assert refused.status_code == 400
    unknown = await presence.http.post("/api/presence/sessions", json={"node_id": core.son.id, "guise": "nobody", "record": "on_record"})
    assert unknown.status_code == 400


async def test_a_session_is_read_with_its_exchanges_and_ends_for_good(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    core = seeded(presence).core
    opened = await summon(presence, core.son.id, guise="unnamed_power")
    session = opened["session"]
    assert session["guise"] == "unnamed_power" and session["record"] == "on_record" and session["status"] == "open"
    assert session["dead_when_summoned"] is False and session["exchange_count"] == 0
    assert opened["exchanges"] == [] and opened["running_exchange_id"] is None and opened["memory_boundary"] == 1
    presence_model.plan([Say("I hear a power.")])
    presence_model.script(PresenceAnswer, PresenceAnswer(reply="I hear a power.", remember="A power spoke.", feeling=10))
    exchange = await say(presence, session["id"], "Hear me, child of the world.")
    view = (await presence.http.get(f"/api/presence/sessions/{session['id']}")).json()
    assert view["session"]["title"] == "Hear me, child of the world."
    assert view["session"]["exchange_count"] == 1
    assert view["exchanges"][0]["id"] == exchange["id"] and view["exchanges"][0]["remember_text"] == "A power spoke."
    assert view["exchanges"][0]["input_tokens"] >= 0 and view["exchanges"][0]["model"]
    closed = await presence.http.post(f"/api/presence/sessions/{session['id']}/close")
    assert closed.json() == {"session_id": session["id"], "node_id": core.son.id, "kept": True}
    ended = (await presence.http.get(f"/api/presence/sessions/{session['id']}")).json()
    assert ended["session"]["status"] == "closed" and ended["session"]["closed_at"] is not None
    assert ended["memory_boundary"] == 2
    late = await presence.http.post(f"/api/presence/sessions/{session['id']}/exchanges", json={"text": "Still there?"})
    assert late.status_code == 409


async def test_missing_sessions_and_exchanges_answer_404(presence: ApiWorld) -> None:
    assert (await presence.http.get(f"/api/presence/sessions/{MISSING}")).status_code == 404
    assert (await presence.http.get(f"/api/presence/exchanges/{MISSING}")).status_code == 404
    assert (await presence.http.post(f"/api/presence/exchanges/{MISSING}/cancel")).status_code == 404
    assert (await presence.http.post(f"/api/presence/sessions/{MISSING}/close")).status_code == 404
    assert (await presence.http.post(f"/api/presence/sessions/{MISSING}/exchanges", json={"text": "Anyone?"})).status_code == 404
    empty = await presence.http.post(f"/api/presence/sessions/{MISSING}/exchanges", json={"text": ""})
    assert empty.status_code == 400


async def test_a_dead_speaker_is_summoned_from_death(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    core = seeded(presence).core
    async with presence.services.database.write() as session:
        son = await session.get(SonRow, core.son.id)
        assert son is not None
        son.status, son.death_epoch, son.death_cause = SonStatus.DEAD, 1, SonDeathCause.FADING
    opened = await summon(presence, core.son.id)
    assert opened["session"]["dead_when_summoned"] is True
    presence_model.plan([Say("I was gone.")])
    presence_model.script(PresenceAnswer, PresenceAnswer(reply="I was gone.", remember="I was called back.", feeling=0))
    await say(presence, opened["session"]["id"], "Come back.")
    seen = presence_model.seen[0]
    assert "YOUR DEATH" in seen.system and "fading" in seen.system
    assert set(seen.tools) <= {"world_summary", "inspect_entity", "search_entities", "my_memory", "inspect_sibling", "recall_event"}
