import asyncio

from sqlalchemy import select

from aerona.agents.turns.state import finish_turn, turn_row
from aerona.db.tables.agency import AgentTurnRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.presence import PresenceSessionRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.presence import PresenceEventKind
from aerona.domain.models.turn import TurnContext
from aerona.events.bus import Event
from aerona.events.kinds import EventKind
from aerona.llm.errors import LlmTransientError
from aerona.prompts.schemas.presence import PresenceAnswer
from tests.api.conftest import ApiWorld, seeded
from tests.divine_will.conftest import set_rules
from tests.divine_will.scripted import Break, Hang, Say, ScriptedWill, Think, Use
from tests.polling import until
from tests.presence.conftest import say, settled_exchange, summon

K = PresenceEventKind
TOUCH_REASON = "to ease a long grief at last"


def answer(remember: str = "I spoke with my maker.", feeling: int = 50, reply: str = "So be it.") -> PresenceAnswer:
    return PresenceAnswer(reply=reply, remember=remember, feeling=feeling)


async def audience_memories(api: ApiWorld, holder_id: int) -> list[MemoryRow]:
    async with api.services.database.read() as session:
        rows = await session.scalars(
            select(MemoryRow).where(MemoryRow.holder_node_id == holder_id, MemoryRow.kind == MemoryKind.AUDIENCE).order_by(MemoryRow.id)
        )
        return list(rows)


async def points_of(api: ApiWorld, node_id: int) -> AgentTurnRow | None:
    async with api.services.database.read() as session:
        return await turn_row(session, node_id)


async def test_an_exchange_streams_and_records_its_events_in_order(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    published: list[Event] = []
    presence.services.bus.add_listener(published.append)
    son = seeded(presence).core.son
    opened = await summon(presence, son.id)
    presence_model.plan([Think("Who calls me?"), Say("I look."), Use("world_summary", {}), Say("I hear you.")])
    presence_model.script(PresenceAnswer, answer())
    exchange = await say(presence, opened["session"]["id"], "Speak to me.")
    assert exchange["status"] == "done", exchange
    assert exchange["reply_text"] == "I hear you."
    assert [K(event["kind"]) for event in exchange["events"]] == [K.THOUGHT, K.TEXT, K.TOOL_CALL, K.TOOL_RESULT, K.TEXT]
    assert [event["ordinal"] for event in exchange["events"]] == [1, 2, 3, 4, 5]
    assert exchange["events"][3]["payload"]["outcome"]
    seen = presence_model.seen[0]
    assert son.name in seen.system
    assert "Speak to me." in seen.prompt
    started = [event.payload for event in published if event.kind is EventKind.PRESENCE_EXCHANGE_STARTED]
    finished = [event.payload for event in published if event.kind is EventKind.PRESENCE_EXCHANGE_FINISHED]
    assert started[0]["exchange_id"] == exchange["id"]
    assert finished[-1]["exchange_id"] == exchange["id"] and finished[-1]["status"] == "done"
    assert any(event.kind is EventKind.PRESENCE_SESSION_CHANGED for event in published)


async def test_on_the_record_an_act_spends_the_sons_own_points_and_enters_the_ledger(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    world = seeded(presence)
    son = world.core.son
    sage = world.core.extra["sage"]
    opened = await summon(presence, son.id)
    presence_model.plan([Use("touch_mortal", {"mortal_id": sage.id, "touch": "ease_mind", "reason": TOUCH_REASON}), Say("It is done.")])
    presence_model.script(PresenceAnswer, answer())
    assert await points_of(presence, son.id) is None
    exchange = await say(presence, opened["session"]["id"], "Ease the mind of the sage.")
    assert exchange["status"] == "done", exchange
    assert "touch_mortal" in presence_model.seen[0].tools
    result = next(event for event in exchange["events"] if event["kind"] == "tool_result")
    assert not result["payload"]["is_error"], result
    row = await points_of(presence, son.id)
    assert row is not None and not row.finished
    async with presence.services.database.read() as session:
        acted = await session.scalar(select(SonRow.last_acted_epoch).where(SonRow.id == son.id))
        entries = list(await session.scalars(select(LedgerEntryRow).where(LedgerEntryRow.actor_node_id == son.id, LedgerEntryRow.tool == "touch_mortal")))
    assert entries
    assert acted is not None and acted < row.epoch
    full = row.action_points_left
    presence_model.plan([Use("touch_mortal", {"mortal_id": sage.id, "touch": "ease_mind", "reason": TOUCH_REASON}), Say("Again.")])
    presence_model.script(PresenceAnswer, answer())
    await say(presence, opened["session"]["id"], "Once more.")
    again = await points_of(presence, son.id)
    assert again is not None and again.action_points_left is not None and full is not None
    assert again.action_points_left == max(0, full - 1)


async def test_a_son_that_already_acted_this_epoch_has_no_points_and_keeps_its_finished_turn(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    world = seeded(presence)
    son = world.core.son
    sage = world.core.extra["sage"]
    async with presence.services.database.write() as session:
        epoch = world.core.cosmos.epoch
        session.add(AgentTurnRow(agent_node_id=son.id, agent_kind=AgentKind.SON, epoch=epoch, action_points_left=2, context=TurnContext(), finished=False))
        await session.flush()
        await finish_turn(session, son.id)
    opened = await summon(presence, son.id)
    presence_model.plan([Use("touch_mortal", {"mortal_id": sage.id, "touch": "ease_mind", "reason": TOUCH_REASON}), Say("I cannot.")])
    presence_model.script(PresenceAnswer, answer())
    exchange = await say(presence, opened["session"]["id"], "Act for me.")
    result = next(event for event in exchange["events"] if event["kind"] == "tool_result")
    assert result["payload"]["is_error"], result
    row = await points_of(presence, son.id)
    assert row is not None and row.finished and row.epoch == epoch
    async with presence.services.database.read() as session:
        assert list(await session.scalars(select(LedgerEntryRow).where(LedgerEntryRow.tool == "touch_mortal"))) == []


async def test_off_the_record_no_acting_tool_is_offered_and_nothing_is_remembered(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    son = seeded(presence).core.son
    opened = await summon(presence, son.id, record="off_record")
    presence_model.plan([Say("Words only.")])
    exchange = await say(presence, opened["session"]["id"], "Tell me a thing.")
    assert exchange["status"] == "done"
    offered = presence_model.seen[0].tools
    assert offered and all(name in {"world_summary", "inspect_entity", "search_entities", "my_memory", "inspect_sibling", "recall_event"} for name in offered)
    assert await audience_memories(presence, son.id) == []
    assert exchange["remember_text"] == ""
    assert "Nothing said here will be kept" in presence_model.seen[0].system


async def test_on_the_record_an_audience_memory_carries_the_guise(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    son = seeded(presence).core.son
    opened = await summon(presence, son.id, guise="dream_voice")
    presence_model.plan([Say("Is this a dream?")])
    presence_model.script(PresenceAnswer, answer(remember="A voice asked me of the river.", feeling=-50))
    exchange = await say(presence, opened["session"]["id"], "Remember the river.")
    assert exchange["remember_text"] == "A voice asked me of the river."
    memories = await audience_memories(presence, son.id)
    assert len(memories) == 1
    memory = memories[0]
    assert memory.subject_node_id == seeded(presence).core.creator.id
    assert memory.note is not None and memory.note.startswith("A voice spoke to me in a dream")
    rules = presence.services.rules.current
    assert memory.magnitude == round(rules.presence.audience_magnitude * -50 / 100)
    assert memory.decay_pct == rules.presence.audience_decay_pct
    assert "dream" in presence_model.seen[0].system


async def test_the_memory_window_holds_n_exchanges_and_forgets_the_one_before(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    await set_rules(presence, "presence", remembered_exchanges=2)
    son = seeded(presence).core.son
    opened = await summon(presence, son.id, record="off_record")
    words = ["Alpha words", "Beta words", "Gamma words", "Delta words"]
    for word in words:
        presence_model.plan([Say(f"Answer to {word}")])
        await say(presence, opened["session"]["id"], word)
    at_n = presence_model.seen[2].prompt
    assert "Alpha words" in at_n and "Beta words" in at_n and "Answer to Alpha words" in at_n
    assert "beyond your memory" not in at_n
    at_n_plus_one = presence_model.seen[3].prompt
    assert "Alpha words" not in at_n_plus_one
    assert "Beta words" in at_n_plus_one and "Gamma words" in at_n_plus_one
    assert "1 earlier exchange of this audience lies beyond your memory" in at_n_plus_one
    view = (await presence.http.get(f"/api/presence/sessions/{opened['session']['id']}")).json()
    assert view["memory_boundary"] == 3
    assert view["remembered_exchanges"] == 2
    assert [row["ordinal"] for row in view["exchanges"]] == [1, 2, 3, 4]


async def test_begin_anew_keeps_an_on_record_audience_and_deletes_an_off_record_one(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    son = seeded(presence).core.son
    kept = await summon(presence, son.id)
    presence_model.plan([Say("Kept words.")])
    presence_model.script(PresenceAnswer, answer())
    await say(presence, kept["session"]["id"], "Keep this.")
    closed = await presence.http.post(f"/api/presence/sessions/{kept['session']['id']}/close")
    assert closed.status_code == 200 and closed.json()["kept"] is True
    view = (await presence.http.get(f"/api/presence/speakers/{son.id}")).json()
    assert view["open_session"] is None
    assert [row["id"] for row in view["past_sessions"]] == [kept["session"]["id"]]
    assert view["past_sessions"][0]["exchange_count"] == 1
    loose = await summon(presence, son.id, record="off_record")
    presence_model.plan([Say("Lost words.")])
    await say(presence, loose["session"]["id"], "Forget this.")
    gone = await presence.http.post(f"/api/presence/sessions/{loose['session']['id']}/close")
    assert gone.json()["kept"] is False
    assert (await presence.http.get(f"/api/presence/sessions/{loose['session']['id']}")).status_code == 404
    assert (await presence.http.get(f"/api/presence/sessions/{kept['session']['id']}")).status_code == 200


async def test_opening_again_closes_the_open_audience_and_deletes_it_off_the_record(presence: ApiWorld) -> None:
    son = seeded(presence).core.son
    await summon(presence, son.id, record="off_record")
    second = await summon(presence, son.id, guise="ordinary")
    async with presence.services.database.read() as session:
        rows = list(await session.scalars(select(PresenceSessionRow).where(PresenceSessionRow.node_id == son.id)))
    assert [(row.id, row.guise.value, row.record.value, row.status.value) for row in rows] == [(second["session"]["id"], "ordinary", "on_record", "open")]


async def test_an_on_record_audience_with_nothing_said_is_not_kept(presence: ApiWorld) -> None:
    son = seeded(presence).core.son
    first = await summon(presence, son.id)
    closed = await presence.http.post(f"/api/presence/sessions/{first['session']['id']}/close")
    assert closed.json()["kept"] is False
    async with presence.services.database.read() as session:
        rows = list(await session.scalars(select(PresenceSessionRow).where(PresenceSessionRow.node_id == son.id)))
    assert rows == []


async def test_an_exchange_can_be_cancelled_and_a_second_waits_with_409(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    son = seeded(presence).core.son
    opened = await summon(presence, son.id, record="off_record")
    started = asyncio.Event()
    presence_model.plan([Hang(started)])
    response = await presence.http.post(f"/api/presence/sessions/{opened['session']['id']}/exchanges", json={"text": "Wait."})
    exchange_id = response.json()["exchange_id"]
    assert await until(started.is_set)
    busy = await presence.http.post(f"/api/presence/sessions/{opened['session']['id']}/exchanges", json={"text": "Again."})
    assert busy.status_code == 409
    cancelled = await presence.http.post(f"/api/presence/exchanges/{exchange_id}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    settled = await settled_exchange(presence, exchange_id)
    assert settled["status"] == "cancelled"
    again = await presence.http.post(f"/api/presence/exchanges/{exchange_id}/cancel")
    assert again.status_code == 409


async def test_a_broken_connection_is_retried_and_noted(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    son = seeded(presence).core.son
    opened = await summon(presence, son.id, record="off_record")
    presence_model.plan([Say("Half"), Break(LlmTransientError("cut"))], [Say("Whole answer.")])
    exchange = await say(presence, opened["session"]["id"], "Speak.")
    assert exchange["status"] == "done"
    assert exchange["reply_text"] == "Whole answer."
    assert K.RETRY in [K(event["kind"]) for event in exchange["events"]]
    assert "the connection broke" in presence_model.seen[1].prompt


async def test_a_mortal_acts_on_the_record_through_its_own_turn(presence: ApiWorld, presence_model: ScriptedWill) -> None:
    sage = seeded(presence).core.extra["sage"]
    opened = await summon(presence, sage.id)
    presence_model.plan([Use("pray_to_creator", {"prayer": "Keep the ford open for us."}), Say("I have prayed.")])
    presence_model.script(PresenceAnswer, answer())
    exchange = await say(presence, opened["session"]["id"], "Pray with me.")
    result = next(event for event in exchange["events"] if event["kind"] == "tool_result")
    assert not result["payload"]["is_error"], result
    row = await points_of(presence, sage.id)
    assert row is not None and row.action_points_left == presence.services.rules.current.mortal_agents.action_points
    async with presence.services.database.read() as session:
        entries = list(await session.scalars(select(LedgerEntryRow).where(LedgerEntryRow.actor_node_id == sage.id, LedgerEntryRow.tool == "pray_to_creator")))
    assert entries
