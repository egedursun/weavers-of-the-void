from aerona.agents.runtime import AgentRuntime
from aerona.agents.son import run_son_turn
from aerona.agents.tool_ports import attach_toolkits
from aerona.db.session import Database
from tests.agents.fakes import FakeModel, spoken
from tests.agents.world import AgentWorld


async def test_son_turn_with_the_real_toolkit(database: Database, world: AgentWorld) -> None:
    model = FakeModel()
    runtime = attach_toolkits(AgentRuntime(database=database, model=model))
    model.runs.append(spoken("«The furrows are mine.»"))
    result = await run_son_turn(runtime, world.core.son.id)
    assert result.word == "The furrows are mine."
    assert "world_summary" in model.calls[0].system or "create" in model.calls[0].system
