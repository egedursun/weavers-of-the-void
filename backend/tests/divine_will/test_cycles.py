import asyncio
from typing import Any

from sqlalchemy import select

from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.divine_will import CycleEventKind
from aerona.domain.enums.son import SonStatus
from aerona.events.bus import Event
from aerona.events.kinds import EventKind
from aerona.llm.errors import LlmTransientError
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from tests.api.conftest import ApiWorld, seeded
from tests.divine_will.conftest import ask, set_rules, settled_cycle
from tests.divine_will.scripted import Break, Hang, Say, ScriptedWill, Think, Use
from tests.polling import until

K = CycleEventKind


def kinds(cycle: dict[str, Any]) -> list[CycleEventKind]:
    return [CycleEventKind(event["kind"]) for event in cycle["events"]]


async def contentment(api: ApiWorld) -> int:
    async with api.services.database.read() as session:
        return (await session.scalars(select(CreatorRow))).one().mood_contentment


async def son_status(api: ApiWorld) -> SonStatus:
    async with api.services.database.read() as session:
        son = await session.get(SonRow, seeded(api).core.son.id)
        assert son is not None
        return son.status


async def test_a_cycle_records_thoughts_calls_results_and_its_answer_in_order(will: ApiWorld, will_model: ScriptedWill) -> None:
    published: list[Event] = []
    will.services.bus.add_listener(published.append)
    wanted = 3 if await contentment(will) != 3 else 7
    will_model.plan(
        [
            Think("The player wants a calmer Creator."),
            Say("I look for the act."),
            Use("search_actions", {"query": "mood"}),
            Use("perform_action", {"action_id": "creator:mood", "input": {"contentment": wanted}}),
            Say("The mood is set."),
        ]
    )
    cycle = await ask(will, "Calm me down.")
    assert cycle["status"] == "done", cycle
    assert cycle["final_text"] == "The mood is set."
    assert kinds(cycle) == [K.PLAYER, K.THOUGHT, K.TEXT, K.TOOL_CALL, K.TOOL_RESULT, K.TOOL_CALL, K.TOOL_RESULT, K.TEXT]
    assert [event["ordinal"] for event in cycle["events"]] == list(range(1, 9))
    calls = [event for event in cycle["events"] if event["kind"] == "tool_call"]
    results = [event for event in cycle["events"] if event["kind"] == "tool_result"]
    assert [event["tool"] for event in calls] == ["search_actions", "perform_action"]
    assert [event["payload"]["call_id"] for event in calls] == [event["payload"]["call_id"] for event in results]
    assert all(event["payload"]["outcome"] for event in results)
    assert results[1]["payload"]["details"]["ledger_entry_id"] is not None
    assert cycle["steps"] == 5
    assert await contentment(will) == wanted
    seen = will_model.seen[0]
    assert "MODE: Command" in seen.system
    assert DivineWillToolId.PERFORM_ACTION.value in seen.tools
    assert DivineWillToolId.SUGGEST_MODE.value in seen.tools
    assert "Calm me down." in seen.prompt
    started = [event.payload for event in published if event.kind is EventKind.DIVINE_WILL_CYCLE_STARTED]
    finished = [event.payload for event in published if event.kind is EventKind.DIVINE_WILL_CYCLE_FINISHED]
    assert started[0]["cycle_id"] == cycle["id"]
    assert finished[-1]["cycle_id"] == cycle["id"]
    assert finished[-1]["status"] == "done"


async def test_ask_lore_offers_no_acting_tool(will: ApiWorld, will_model: ScriptedWill) -> None:
    will_model.plan([Say("Nothing changes here.")])
    cycle = await ask(will, "Tell me of the world.", mode="ask_lore")
    assert cycle["status"] == "done"
    assert DivineWillToolId.PERFORM_ACTION.value not in will_model.seen[0].tools
    assert "MODE: Ask Lore" in will_model.seen[0].system


async def test_a_suggested_mode_is_kept_as_a_notice(will: ApiWorld, will_model: ScriptedWill) -> None:
    will_model.plan([Use("suggest_mode", {"mode": "plan", "reason": "Many stages."}), Say("This is better as a plan.")])
    cycle = await ask(will, "Remake the whole world in stages.")
    notices = [event for event in cycle["events"] if event["kind"] == "notice"]
    assert notices and notices[0]["payload"]["mode"] == "plan"
    assert notices[0]["payload"]["text"] == "Many stages."


async def test_the_memory_window_holds_n_cycles_and_forgets_the_one_before(will: ApiWorld, will_model: ScriptedWill) -> None:
    await set_rules(will, "divine_will", remembered_cycles=2)
    words = ["Alpha request", "Beta request", "Gamma request", "Delta request"]
    for word in words:
        will_model.plan([Say(f"Answer to {word}")])
        await ask(will, word)
    at_n = will_model.seen[2].prompt
    assert "Alpha request" in at_n and "Beta request" in at_n
    assert "Answer to Alpha request" in at_n
    assert "beyond your memory" not in at_n
    at_n_plus_one = will_model.seen[3].prompt
    assert "Alpha request" not in at_n_plus_one
    assert "Beta request" in at_n_plus_one and "Gamma request" in at_n_plus_one
    assert "1 earlier exchange of this session" in at_n_plus_one
    view = (await will.http.get("/api/divine-will/session")).json()
    assert view["memory_boundary"] == 3
    assert [cycle["ordinal"] for cycle in view["cycles"]] == [1, 2, 3, 4]
    assert view["remembered_cycles"] == 2


async def test_reset_closes_the_session_and_keeps_it_in_the_record(will: ApiWorld, will_model: ScriptedWill) -> None:
    will_model.plan([Say("First answer.")])
    first = await ask(will, "Old words.")
    reset = await will.http.post("/api/divine-will/session/reset")
    assert reset.status_code == 200, reset.text
    fresh = reset.json()
    assert fresh["session"]["id"] != first["session_id"]
    assert fresh["cycles"] == []
    closed = (await will.http.get("/api/divine-will/sessions")).json()["sessions"]
    assert [item["id"] for item in closed] == [first["session_id"]]
    assert closed[0]["cycle_count"] == 1
    assert closed[0]["closed_at"] is not None
    kept = (await will.http.get(f"/api/divine-will/sessions/{first['session_id']}")).json()
    assert kept["cycles"][0]["final_text"] == "First answer."
    assert kept["cycles"][0]["events"]
    will_model.plan([Say("New answer.")])
    await ask(will, "New words.")
    assert "Old words." not in will_model.seen[-1].prompt


async def test_an_approved_act_resumes_the_same_cycle(will: ApiWorld, will_model: ScriptedWill) -> None:
    son_id = seeded(will).core.son.id
    will_model.plan(
        [Use("perform_action", {"action_id": "kill:son", "input": {"son_id": son_id, "reason": "A test."}}), Say("The killing waits for you.")],
        [Say("The son is dead.")],
    )
    waiting = await ask(will, "Kill my son.")
    assert waiting["status"] == "awaiting_confirmation", waiting
    assert waiting["final_text"] == "The killing waits for you."
    assert await son_status(will) is not SonStatus.DEAD
    confirmation = waiting["confirmations"][0]
    assert confirmation["status"] == "pending"
    assert confirmation["preview"]["destructive"] is True
    assert K.CONFIRMATION_REQUEST in kinds(waiting)
    decided = await will.http.post(f"/api/divine-will/confirmations/{confirmation['id']}", json={"decision": "approve"})
    assert decided.status_code == 200, decided.text
    done = await settled_cycle(will, waiting["id"])
    assert done["status"] == "done"
    assert done["final_text"] == "The son is dead."
    assert await son_status(will) is SonStatus.DEAD
    assert done["confirmations"][0]["status"] == "approved"
    assert done["confirmations"][0]["ledger_entry_id"] is not None
    reply = next(event for event in done["events"] if event["kind"] == "confirmation_reply")
    assert reply["payload"]["decision"] == "approve" and reply["payload"]["ok"] is True
    assert kinds(done)[-1] is K.TEXT
    assert "the player's decision" in will_model.seen[1].prompt
    assert len(will_model.seen) == 2


async def test_a_declined_act_resumes_the_same_cycle_with_the_refusal(will: ApiWorld, will_model: ScriptedWill) -> None:
    son_id = seeded(will).core.son.id
    will_model.plan(
        [Use("perform_action", {"action_id": "kill:son", "input": {"son_id": son_id}}), Say("It waits.")],
        [Say("I left the son alive.")],
    )
    waiting = await ask(will, "Kill my son.")
    confirmation = waiting["confirmations"][0]
    decided = await will.http.post(f"/api/divine-will/confirmations/{confirmation['id']}", json={"decision": "decline"})
    assert decided.status_code == 200, decided.text
    done = await settled_cycle(will, waiting["id"])
    assert done["status"] == "done"
    assert done["final_text"] == "I left the son alive."
    assert done["confirmations"][0]["status"] == "declined"
    assert await son_status(will) is not SonStatus.DEAD
    again = await will.http.post(f"/api/divine-will/confirmations/{confirmation['id']}", json={"decision": "approve"})
    assert again.status_code == 409


async def test_a_running_cycle_can_be_cancelled(will: ApiWorld, will_model: ScriptedWill) -> None:
    started = asyncio.Event()
    will_model.plan([Say("Starting."), Hang(started)])
    response = await will.http.post("/api/divine-will/cycles", json={"text": "Think forever.", "mode": "ask_lore"})
    cycle_id = response.json()["cycle_id"]
    await asyncio.wait_for(started.wait(), timeout=30)
    busy = await will.http.post("/api/divine-will/cycles", json={"text": "Another.", "mode": "ask_lore"})
    assert busy.status_code == 409
    cancelled = await will.http.post(f"/api/divine-will/cycles/{cycle_id}/cancel")
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert await until(lambda: will.services.jobs.busy_group("divine_will") is None)
    final = (await will.http.get(f"/api/divine-will/cycles/{cycle_id}")).json()
    assert final["status"] == "cancelled"
    assert final["finished_at"] is not None


async def test_a_broken_connection_restarts_the_cycle_from_its_trace(will: ApiWorld, will_model: ScriptedWill) -> None:
    will_model.plan([Use("search_actions", {"query": "mood"}), Break(LlmTransientError("connection lost"))], [Say("Recovered.")])
    cycle = await ask(will, "Find the mood act.")
    assert cycle["status"] == "done", cycle
    assert cycle["final_text"] == "Recovered."
    assert kinds(cycle) == [K.PLAYER, K.TOOL_CALL, K.TOOL_RESULT, K.RETRY, K.TEXT]
    assert "you called search_actions" in will_model.seen[1].prompt
    assert "connection lost" in cycle["events"][3]["payload"]["reason"]


async def test_a_cycle_fails_when_every_attempt_breaks(will: ApiWorld, will_model: ScriptedWill) -> None:
    await set_rules(will, "model", retry_attempts=1)
    will_model.plan([Break(LlmTransientError("gone"))])
    cycle = await ask(will, "Anything.")
    assert cycle["status"] == "failed"
    assert "gone" in cycle["error"]
    assert kinds(cycle)[-1] is K.ERROR


async def test_a_break_after_an_act_asks_first_keeps_the_cycle_waiting(will: ApiWorld, will_model: ScriptedWill) -> None:
    son_id = seeded(will).core.son.id
    will_model.plan([Use("perform_action", {"action_id": "kill:son", "input": {"son_id": son_id}}), Break(LlmTransientError("lost"))])
    cycle = await ask(will, "Kill my son.")
    assert cycle["status"] == "awaiting_confirmation", cycle
    assert K.RETRY not in kinds(cycle)
    assert cycle["confirmations"][0]["status"] == "pending"
    assert len(will_model.seen) == 1
