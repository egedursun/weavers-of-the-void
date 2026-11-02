from aerona.agents.celestial_deepener import deepen_celestial
from aerona.agents.runtime import AgentRuntime
from aerona.db.session import Database
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.prompts import PromptId
from aerona.prompts.contexts.narrative import CelestialKind
from tests.agents.fakes import FakeModel
from tests.agents.test_roles import payload
from tests.agents.world import AgentWorld


async def test_a_world_and_its_star_are_deepened(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    deep = payload(PromptId.DEEPEN_CELESTIAL_USER, history="The sea came first.")
    model.script(type(deep), deep)
    depth = await deepen_celestial(runtime, CelestialKind.WORLD, world.core.world.id)
    assert depth.history == "The sea came first."
    model.script(type(deep), deep)
    star_id = world.core.world.star_id
    assert star_id is not None
    await deepen_celestial(runtime, CelestialKind.STAR, star_id)
    async with database.read() as session:
        stored_world = await session.get(WorldRow, world.core.world.id)
        stored_star = await session.get(StarRow, star_id)
    assert stored_world is not None and stored_world.depth is not None
    assert stored_star is not None and stored_star.depth is not None and stored_star.depth.rumours
