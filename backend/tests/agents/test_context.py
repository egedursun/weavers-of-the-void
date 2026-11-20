from aerona.agents.context.chronicler import chronicler_context
from aerona.agents.context.entity_detail import entity_detail
from aerona.agents.context.recent_chronicle import recent_rows
from aerona.agents.context.scope import load_scope
from aerona.agents.context.son_memory import recollections, son_memory
from aerona.agents.context.son_turn import son_system_context, son_user_context
from aerona.agents.context.world_header import world_header
from aerona.agents.context.world_summary import world_summary
from aerona.agents.turns.ports import ToolCatalogue
from aerona.db.session import Database
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.world import TechnologyEra
from aerona.domain.models.genesis import GenesisSettings
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


async def test_every_prompt_header_tells_the_age_the_peoples_live_in(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.write() as session:
        cosmos = await session.get(CosmosRow, (await load_scope(session, rules)).cosmos.id)
        assert cosmos is not None
        cosmos.genesis_settings = GenesisSettings(magic=50, danger=50, peoples=2, technology=TechnologyEra.INFORMATION)
        await session.flush()
        text = await world_header(await load_scope(session, rules))
        short = await world_header(await load_scope(session, rules), short=True)
    line = "TECHNOLOGY: the peoples of this world live in the information age, when machines compute and messages cross the world at once."
    assert line in text
    assert line in short


async def test_agents_read_what_happened_but_not_the_words_others_chose(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.write() as session:
        session.add(ChronicleRow(epoch=1, kind=ChronicleKind.SPEECH, text="Ostvel: The shell holds where we hold it."))
        session.add(ChronicleRow(epoch=1, kind=ChronicleKind.WORLD, text="The vent field of Ostvel cooled."))
        await session.flush()
        rows = [row.text for row in await recent_rows(await load_scope(session, rules), 50)]
    assert "The vent field of Ostvel cooled." in rows
    assert not any("The shell holds" in text for text in rows)


async def test_a_son_recalls_its_deeds_but_not_its_own_sayings(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.write() as session:
        son = await session.get(type(world.core.son), world.core.son.id)
        assert son is not None
        session.add(ChronicleRow(epoch=1, kind=ChronicleKind.SPEECH, son_id=son.id, text=f'{son.name}: "The reef gives way to whoever dares."'))
        session.add(ChronicleRow(epoch=1, kind=ChronicleKind.WORLD, son_id=son.id, text=f"{son.name} raised the reef."))
        await session.flush()
        rows = [row.text for row in await recollections(await load_scope(session, rules), son)]
    assert f"{son.name} raised the reef." in rows
    assert not any("reef gives way" in text for text in rows)


async def test_one_kind_of_happening_never_crowds_out_the_rest_of_recent_events(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.write() as session:
        session.add(ChronicleRow(epoch=1, kind=ChronicleKind.WAR, template_key="battle.fought", text="Orrin Folk fought at the ford."))
        for index in range(20):
            session.add(ChronicleRow(epoch=1, kind=ChronicleKind.CULTURE, template_key="cuisine.invented", text=f"A dish came to be known, the {index}th."))
        await session.flush()
        rows = [row.text for row in await recent_rows(await load_scope(session, rules), 10)]
    assert "Orrin Folk fought at the ford." in rows
    assert sum("dish came to be known" in text for text in rows) == rules.context.recent_per_kind


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
