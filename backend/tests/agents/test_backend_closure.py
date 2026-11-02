import copy
from pathlib import Path

from sqlalchemy import select

from aerona.agents.context.geography import geography_lines
from aerona.agents.context.scope import load_scope
from aerona.agents.genesis import GenesisRequest, genesis
from aerona.agents.mortal import Candidate, candidates, pick
from aerona.agents.runtime import AgentRuntime
from aerona.core.random import SeededRandom
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.entity import EngineKind
from aerona.domain.enums.world import LoreLanguage
from aerona.prompts import PromptId, output_model
from aerona.rules.registry import Rules
from tests.agents.fakes import FakeModel
from tests.agents.world import AgentWorld
from tests.conftest import OpenDatabase
from tests.prompts.payloads import PAYLOADS


async def test_geography_lines_list_each_known_region_with_its_neighbours(database: Database, rules: Rules, world: AgentWorld) -> None:
    async with database.read() as session:
        text = await geography_lines(await load_scope(session, rules), world.core.world.id)
        empty = await geography_lines(await load_scope(session, rules), None)
    names = [region.name for region in world.core.regions]
    assert text.startswith(f"{len(names)} known regions.")
    assert all(name in text for name in names)
    assert f"neighbours: #{world.core.regions[1].id} {names[1]}" in text
    assert "plain" in text and "medium" in text
    assert empty == ""


async def test_genesis_defines_the_cosmic_travel_resource_with_one_deposit(tmp_path: Path, rules: Rules, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "genesis.db")
    model = FakeModel()
    data = copy.deepcopy(PAYLOADS[PromptId.GENESIS_USER])
    data["sons"] = [{**data["sons"][index], "name": name} for index, name in enumerate(("Ozzeh", "Varum", "Kessa"))]
    model.script(output_model(PromptId.GENESIS_USER), output_model(PromptId.GENESIS_USER).model_validate(data))
    runtime = AgentRuntime(database=database, model=model, rules_override=rules)
    await genesis(runtime, GenesisRequest("Aeron", "a salt lake", LoreLanguage.ENGLISH, 7), rules)
    async with database.read() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        deposits = list(await session.scalars(select(EntityRow).where(EntityRow.engine_kind == EngineKind.COSMIC_TRAVEL_RESOURCE)))
    await database.dispose()
    assert cosmos.travel_resource is not None and cosmos.travel_resource.name == "Veilsalt"
    assert cosmos.travel_resource.side_effect == "Memory loss."
    assert [deposit.name for deposit in deposits] == ["Veilsalt Deposit"]


async def test_a_pending_dream_puts_its_dreamer_first_in_selection(database: Database, rules: Rules, world: AgentWorld) -> None:
    dreamer = world.creation
    async with database.write() as session:
        session.add(MessageRow(epoch=1, sender_node_id=world.core.creator.id, recipient_node_id=dreamer.id, intent=MessageIntent.DREAM, text="Rise."))
    async with database.read() as session:
        scope = await load_scope(session, rules)
        found = await candidates(scope)
    flagged = {candidate.entity.id: candidate.dreaming for candidate in found}
    assert flagged[dreamer.id] and not any(value for key, value in flagged.items() if key != dreamer.id)
    dreaming: list[Candidate] = [candidate for candidate in found if candidate.dreaming]
    others = [candidate for candidate in found if not candidate.dreaming]
    chosen = pick(rules, [*others, *dreaming], 1, scope.epoch, SeededRandom.for_epoch(1, scope.epoch, "test"))
    assert [candidate.entity.id for candidate in chosen] == [dreamer.id]
