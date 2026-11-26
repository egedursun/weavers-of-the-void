import pytest
from sqlalchemy import select

from aerona.agents.runtime import AgentRuntime
from aerona.agents.son import continuation_prompt, run_son_turn, start_turn
from aerona.agents.turns.ports import DoneAction, ToolCatalogue
from aerona.agents.turns.session import TurnFailedError
from aerona.core.errors import ValidationFailedError
from aerona.db.session import Database
from aerona.db.tables.agency import AgentTurnRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.models.turn import LongJobTrace
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.llm.errors import LlmTransientError
from aerona.prompts.contexts.son_turn import TurnInterruption
from tests.agents.fakes import FAKE_MODEL, FakeModel, ScriptedToolkits, spoken
from tests.agents.world import AgentWorld


async def test_son_speaks_and_finishes_the_turn(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    model.runs.append(spoken("I shaped them. «Salt remembers what the sea forgets.»"))
    result = await run_son_turn(runtime, world.core.son.id)
    async with database.read() as session:
        son = await session.get(SonRow, world.core.son.id)
        words = list(await session.scalars(select(ChronicleRow).where(ChronicleRow.kind == ChronicleKind.SPEECH)))
        turn = await session.get(AgentTurnRow, world.core.son.id)
    assert result.word == "Salt remembers what the sea forgets."
    assert son is not None and son.last_acted_epoch == 1
    assert words[0].text == 'Ithren: "Salt remembers what the sea forgets."'
    assert turn is not None and turn.finished and turn.action_points_left is None
    with pytest.raises(ValidationFailedError):
        await run_son_turn(runtime, world.core.son.id)


async def test_traceless_crash_restarts_and_missing_word_continues(runtime: AgentRuntime, model: FakeModel, bus: EventBus, world: AgentWorld) -> None:
    model.runs.extend([LlmTransientError("socket closed"), spoken("I thought about it."), spoken("«The well is mine.»")])
    result = await run_son_turn(runtime, world.core.son.id)
    events = bus.replay_after(0)
    retries = [event.payload for event in events if event.kind is EventKind.AGENT_RETRY]
    assert result.word == "The well is mine."
    assert [retry["kind"] for retry in retries] == ["restart", "continuation"]
    assert all({"wait_s", "kept_steps"} <= set(retry) for retry in retries)
    assert retries[1]["kept_steps"] == 0
    started = next(event.payload for event in events if event.kind is EventKind.SON_TURN_STARTED)
    finished = next(event.payload for event in events if event.kind is EventKind.SON_TURN_FINISHED)
    assert started["model"] == finished["model"] == FAKE_MODEL
    assert started["rarity"] == finished["rarity"] == world.core.son.rarity.value
    assert "YOUR TURN WAS LEFT HALF-DONE (you finished without saying your word)" in model.calls[-1].prompt


async def test_failed_turn_without_trace_raises(runtime: AgentRuntime, model: FakeModel, world: AgentWorld) -> None:
    model.runs.extend([LlmTransientError("down")] * 6)
    with pytest.raises(TurnFailedError):
        await run_son_turn(runtime, world.core.son.id)


async def test_partial_turn_with_world_changes_still_finishes(database: Database, model: FakeModel, world: AgentWorld) -> None:
    toolkits = ScriptedToolkits()
    toolkits.son.actions.append(DoneAction("create_people", False, "created the Orrin Folk"))
    toolkits.son.created.append(world.creation.id)
    runtime = AgentRuntime(database=database, model=model, toolkits=toolkits)
    model.runs.extend([LlmTransientError("down")] * 6)
    result = await run_son_turn(runtime, world.core.son.id)
    assert result.word == ""
    assert result.creations == [world.creation.id]
    assert toolkits.requests[0][0] == "son"


async def test_continuation_prompt_carries_finished_long_job_traces(runtime: AgentRuntime, database: Database, world: AgentWorld) -> None:
    started = await start_turn(runtime, world.core.son.id)
    async with database.write() as session:
        row = await session.get(AgentTurnRow, world.core.son.id)
        assert row is not None
        row.context = row.context.model_copy(update={"long_jobs": (LongJobTrace(tool="write_epic", key="epic:1", summary="Epic written: The Salt Road"),)})
    assert started.son_id == world.core.son.id
    prompt = await continuation_prompt(runtime, world.core.son.id, ToolCatalogue(), TurnInterruption.TIMEOUT, detail=None, done=[])
    assert prompt is not None
    assert "LONG WORKS YOU SET IN MOTION" in prompt
    assert "write_epic → Epic written: The Salt Road" in prompt
