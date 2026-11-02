from aerona.agents.context.chronicler import chronicler_context, opening_bigrams, piled_roots
from aerona.agents.context.entity_detail import entity_detail
from aerona.agents.context.scope import load_scope
from aerona.agents.context.son_memory import son_memory
from aerona.agents.context.son_turn import son_system_context, son_user_context
from aerona.agents.context.world_header import world_header
from aerona.agents.context.world_summary import world_summary
from aerona.agents.turns.ports import ToolCatalogue
from aerona.db.session import Database
from aerona.db.tables.cosmos import CosmosRow
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import SummarySection
from aerona.rules.registry import Rules
from tests.agents.world import AgentWorld


async def test_world_header_shows_doom_only_past_the_warning_share(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.write() as session:
        scope = await load_scope(session, rules)
        quiet = await world_header(scope)
        cosmos = await session.get(CosmosRow, scope.cosmos.id)
        assert cosmos is not None
        cosmos.doom_clock = rules.balance.apocalypse_threshold
        loud = await world_header(scope)
    assert "DOOM CLOCK" not in quiet
    assert "DOOM CLOCK" in loud
    assert "WORLD: Aerona" in quiet
    assert "contentment" in quiet


async def test_short_header_drops_the_creator_mood(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.read() as session:
        text = await world_header(await load_scope(session, rules), short=True)
    assert "CREATOR'S MOOD" not in text


async def test_world_summary_for_a_son_and_for_fate(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.read() as session:
        scope = await load_scope(session, rules)
        son = await session.get(type(world.core.son), world.core.son.id)
        assert son is not None
        for_son = await world_summary(scope, son)
        for_fate = await world_summary(scope)
        section = await world_summary(scope, son, SummarySection.LANGUAGES)
    assert "GEOGRAPHY AND INHABITANTS" in for_son
    assert "Velari" in section
    assert "Kethrani" in for_fate


async def test_entity_detail_and_son_memory(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.read() as session:
        scope = await load_scope(session, rules)
        detail = await entity_detail(scope, world.creation)
        son = await session.get(type(world.core.son), world.core.son.id)
        assert son is not None
        memory = await son_memory(scope, son)
    assert "Orrin Folk" in detail
    assert "Orrin Folk (People, P3)" in memory


async def test_son_turn_prompts_render(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.read() as session:
        scope = await load_scope(session, rules)
        son = await session.get(type(world.core.son), world.core.son.id)
        assert son is not None
        catalogue = ToolCatalogue(names=["create_people"], paid=["create_people"])
        system = render(PromptId.SON_TURN_SYSTEM, await son_system_context(scope, son, 3, catalogue))
        user = render(PromptId.SON_TURN_USER, await son_user_context(scope, son, 3, catalogue, resumed=True))
    assert "Ithren" in system
    assert "Age 1 has begun" in user


async def test_chronicler_context_lists_pending_records(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.read() as session:
        context = await chronicler_context(await load_scope(session, rules), 1, ["The rivers rose."])
    assert [item.name for item in context.pending] == ["Unnamed Tale"]
    assert "RESULTS OF THE WORLD ENGINE" in render(PromptId.CHRONICLER_USER, context)


def test_piled_roots_and_opening_bigrams() -> None:
    names = ["Age of Ember Rains", "Second Ember Winter", "Embers of Silence"]
    assert piled_roots(names, 3, 3) == ["ember"]
    assert opening_bigrams("The salt rains fell on the old roads") == {"salt rains", "rains fell", "old roads"}
