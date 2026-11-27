import copy
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select, update

from aerona.agents.awakening import awaken_peoples
from aerona.agents.bard import voices_of_peoples, write_son_epic
from aerona.agents.context.scope import load_scope
from aerona.agents.council import convene_council
from aerona.agents.creative import agent_creative_ports
from aerona.agents.deepener import creator_deepen, creator_epic, deepen_entity, deepen_foreign_god, refresh_awakened_god
from aerona.agents.genesis import GenesisRequest, creator_portrait, genesis
from aerona.agents.image_prompter import missing_cosmos_prompts, missing_image_prompts
from aerona.agents.localiser import localise_epoch
from aerona.agents.mortal import choose_mortal_agents, run_mortal_turn, world_shares
from aerona.agents.network_repair import network_fate_repair, network_rule_repair, node_key
from aerona.agents.revelation import reveal
from aerona.agents.runtime import AgentRuntime
from aerona.agents.summoner import birth_child, child_rarity, complete_son_powers, summon_son
from aerona.agents.translator import translate
from aerona.agents.world_birth import BirthPlan, birth_world
from aerona.core.random import SeededRandom
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.session import Database
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleRow, CouncilRow, FolkBeliefRow, HistorianViewRow, LexemeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.world import LoreLanguage
from aerona.domain.models.stats import StatBlock
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.manual import manual_context
from aerona.engine.recording.record import record
from aerona.llm.errors import LlmDisabledError
from aerona.prompts import PromptId, output_model
from aerona.prompts.schemas.base import OutputModel
from aerona.rules.registry import Rules
from aerona.services.player.ports import CreativePorts
from tests.agents.fakes import FakeModel, spoken
from tests.agents.world import AgentWorld
from tests.conftest import OpenDatabase
from tests.prompts.payloads import PAYLOADS


def payload(prompt: PromptId, **changes: Any) -> OutputModel:
    data = copy.deepcopy(PAYLOADS[prompt])
    data.update(changes)
    return output_model(prompt).model_validate(data)


def son_profile(name: str) -> OutputModel:
    return payload(PromptId.SUMMON_SON_USER, name=name)


async def test_summon_birth_and_lowest_rarity_floor(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld, rules: Rules) -> None:
    model.script(type(son_profile("x")), son_profile("Ozzeh"), son_profile("Ozzeh"))
    summoned = await summon_son(runtime, rarity=Rarity.COMMON)
    child = await birth_child(runtime, summoned.id, "born of salt")
    assert child.rarity is Rarity.COMMON
    assert child.parent_son_id == summoned.id
    assert child.name != summoned.name
    assert child_rarity(rules, SeededRandom.for_epoch(1, 1, "t"), Rarity.LEGENDARY).rank < Rarity.LEGENDARY.rank


async def test_son_powers_completion(runtime: AgentRuntime, model: FakeModel, world: AgentWorld) -> None:
    model.script(type(payload(PromptId.SON_POWERS_USER)), payload(PromptId.SON_POWERS_USER))
    son = await complete_son_powers(runtime, world.core.son.id)
    assert son.existence_profile is not None


async def test_revelation_creates_and_links(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    model.script(type(payload(PromptId.REVELATION_USER)), payload(PromptId.REVELATION_USER, links=[]))
    entity = await reveal(runtime, "A new light over the salt.", EntityType.CELESTIAL)
    assert entity.entity_type is EntityType.CELESTIAL
    with pytest.raises(Exception, match="content"):
        await reveal(runtime, "  ")


async def test_awakening_writes_six_records(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    data = copy.deepcopy(PAYLOADS[PromptId.AWAKEN_PEOPLES_USER])
    data["peoples"][0]["region_id"] = world.core.regions[0].id
    data["peoples"][0]["worshipped_son_id"] = world.core.son.id
    model.script(output_model(PromptId.AWAKEN_PEOPLES_USER), output_model(PromptId.AWAKEN_PEOPLES_USER).model_validate(data))
    ids = await awaken_peoples(runtime, 1)
    async with database.read() as session:
        people = await session.get(EntityRow, ids[0])
        words = int(await session.scalar(select(func.count()).select_from(LexemeRow).where(LexemeRow.word == "vesh")) or 0)
        towns = await towns_of_people(session, ids[0])
    assert people is not None and people.entity_type is EntityType.PEOPLE
    assert words == 1
    assert len(towns) == 1


async def test_world_birth_creates_a_world(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    model.script(output_model(PromptId.NEW_WORLD_USER), payload(PromptId.NEW_WORLD_USER, star_id=None))
    born = await birth_world(runtime, BirthPlan(inspiration="a wet world"))
    async with database.read() as session:
        count = int(await session.scalar(select(func.count()).select_from(WorldRow)) or 0)
    assert born.name and count == 2


async def test_council_applies_votes_and_peace(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    model.script(type(son_profile("x")), son_profile("Ozzeh"))
    second = await summon_son(runtime, rarity=Rarity.COMMON)
    first = world.core.son.id
    output = payload(
        PromptId.COUNCIL_SESSION_USER,
        speeches=[{"son_id": first, "words": "Peace."}],
        votes=[{"son_id": first, "vote": "yes", "reason": "Tired."}, {"son_id": second.id, "vote": "yes", "reason": "Yes."}],
        alliances=[{"a": first, "b": second.id, "kind": "covenant", "reason": "Fear."}],
        decision="joint_blessing",
    )
    model.script(type(output), output)
    result = await convene_council(runtime)
    async with database.read() as session:
        councils = int(await session.scalar(select(func.count()).select_from(CouncilRow)) or 0)
    assert result.passed and councils == 1
    assert any("covenant" in note for note in result.notes)


async def test_voices_write_views_and_beliefs(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    people = world.core.people.id
    output = payload(
        PromptId.VOICES_USER,
        views=[{"people_id": people, "text": "We were first."}],
        beliefs=[{"people_id": people, "son_id": world.core.son.id, "name": "Ithrenu", "story": "He walks the furrows.", "wrong": "They think he sleeps."}],
    )
    model.script(type(output), output)
    result = await voices_of_peoples(runtime, 1)
    async with database.read() as session:
        views = int(await session.scalar(select(func.count()).select_from(HistorianViewRow)) or 0)
        beliefs = int(await session.scalar(select(func.count()).select_from(FolkBeliefRow)) or 0)
    assert result.views == views == 1
    assert beliefs >= 1


async def test_deepening_roles(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    deep = payload(PromptId.DEEPEN_ENTITY_USER, history="It was old.\nRumours:\n- it sings at night")
    model.script(type(deep), deep)
    depth = await deepen_entity(runtime, world.creation.id)
    assert depth.history == "It was old."
    for prompt in (PromptId.CREATOR_EPIC_USER, PromptId.CREATOR_DEEPEN_USER, PromptId.SON_EPIC_USER):
        model.script(output_model(prompt), payload(prompt))
    assert (await creator_epic(runtime)).title
    assert (await creator_deepen(runtime)).epoch == 1
    assert (await write_son_epic(runtime, world.core.son.id)).title == "The Weeper"
    async with database.write() as session:
        god = await ForeignGodRepository(session).create(
            ForeignGodDraft(
                name="Ulmar",
                world_id=world.core.world.id,
                domain_primary=Domain.SEA,
                power=30,
                stats=StatBlock.uniform(40),
                created_epoch=1,
                title="the sleeping one",
            )
        )
        god_id = god.id
    model.script(output_model(PromptId.FOREIGN_GOD_DEEPEN_USER), payload(PromptId.FOREIGN_GOD_DEEPEN_USER))
    assert (await deepen_foreign_god(runtime, god_id)).history
    async with database.read() as session:
        stored = await session.get(ForeignGodRow, god_id)
    assert stored is not None and stored.depth is not None


async def test_an_awakened_god_keeps_the_description_the_player_wrote(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    written = "Ulmar is the drowned bell the player rang."
    ids: list[int] = []
    async with database.write() as session:
        for name in ("Ulmar", "Oskal"):
            draft = ForeignGodDraft(name=name, world_id=world.core.world.id, domain_primary=Domain.SEA, power=30, stats=StatBlock.uniform(40), created_epoch=1)
            god = await ForeignGodRepository(session).create(draft)
            god.description = written
            ids.append(god.id)
        ctx = await manual_context(session, "test_roles")
        roles = {IncidentRole.AUTHORITY: world.core.creator.id, IncidentRole.SUBJECT: ids[0]}
        await record(ctx, "player.foreign_god.edited", roles=roles, facts={"fields": "description"}, kind=ChronicleKind.FOREIGN_GOD)
    for god_id in ids:
        model.script(output_model(PromptId.FOREIGN_GOD_DEEPEN_USER), payload(PromptId.FOREIGN_GOD_DEEPEN_USER))
        await refresh_awakened_god(runtime, god_id)
    async with database.read() as session:
        kept, told = [await session.get(ForeignGodRow, god_id) for god_id in ids]
    assert kept is not None and kept.description == written and kept.depth is not None
    assert told is not None and told.description != written


async def test_image_prompts_and_portrait(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    image = output_model(PromptId.ENTITY_IMAGE_PROMPTS_USER)
    model.script(image, image.model_validate({"prompts": [{"id": world.creation.id, "prompt": "A salt-crusted people at dawn, cracked hands, wide lens"}]}))
    assert await missing_image_prompts(runtime, ids=[world.creation.id]) == 1
    model.script(output_model(PromptId.COSMOS_IMAGE_PROMPTS_USER), payload(PromptId.COSMOS_IMAGE_PROMPTS_USER))
    assert await missing_cosmos_prompts(runtime) == 1
    model.script(output_model(PromptId.CREATOR_PORTRAIT_USER), payload(PromptId.CREATOR_PORTRAIT_USER))
    await creator_portrait(runtime)
    async with database.read() as session:
        creator = (await session.scalars(select(CreatorRow))).one()
    assert creator.title == "the Salt"


async def test_translation(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    model.script(output_model(PromptId.TRANSLATE_USER), payload(PromptId.TRANSLATE_USER))
    result = await translate(runtime, world.core.language.id, "salt remembers")
    async with database.read() as session:
        added = int(await session.scalar(select(func.count()).select_from(LexemeRow).where(LexemeRow.word == "ka")) or 0)
    assert added == 1 and len(result.new_words) == 1


async def test_network_repair(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    suggestion = output_model(PromptId.BOND_SUGGEST_USER)
    model.fallback[suggestion] = lambda _prompt: suggestion.model_validate({"bonds": []})
    related = output_model(PromptId.BOND_NAME_RELATED_USER)
    model.fallback[related] = lambda _prompt: related.model_validate({"decisions": []})
    summary = await network_fate_repair(runtime)
    assert summary.looked >= 1
    assert await network_rule_repair(runtime, 1) >= 0


async def test_localisation_translates_engine_lines(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    async with database.write() as session:
        await session.execute(update(CosmosRow).values(lore_language=LoreLanguage.TURKISH))
        row = ChronicleRow(epoch=1, kind=ChronicleKind.WORLD, text="The river rose.", template_key="engine.flood")
        session.add(row)
        await session.flush()
        line_id = row.id
    localised = output_model(PromptId.LOCALISE_USER)
    model.script(localised, localised.model_validate({"lines": [{"id": line_id, "text": "Nehir yukseldi."}]}))
    assert await localise_epoch(runtime, 1) >= 1


async def test_mortal_selection_and_turn(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld, rules: Rules) -> None:
    assert world_shares({1: 5, 2: 1}, {1: None, 2: None}, 3) == {1: 2, 2: 1}
    async with database.write() as session:
        await EntityRepository(session).add_flag(world.creation.id, EntityFlag.AGENT_SELECTED, 1)
    async with database.read() as session:
        picked = await choose_mortal_agents(await load_scope(session, rules), 1)
    assert picked[0].id == world.creation.id
    model.runs.append(spoken("«We dig.»"))
    result = await run_mortal_turn(runtime, world.creation.id)
    async with database.read() as session:
        flagged = await EntityRepository(session).has_flag(world.creation.id, EntityFlag.AGENT_SELECTED)
    assert result.word == "We dig." and not flagged


async def test_creative_ports_match_the_player_services(runtime: AgentRuntime) -> None:
    ports = agent_creative_ports(runtime)
    wired = CreativePorts(summoner=ports.summoner, revelations=ports.revelations, worlds=ports.worlds, awakener=ports.awakener, writer=ports.writer)
    assert wired.summoner is ports.summoner


async def test_disabled_model_refuses_every_role(database: Database, world: AgentWorld) -> None:
    runtime = AgentRuntime(database=database, model=FakeModel(enabled=False))
    with pytest.raises(LlmDisabledError):
        await summon_son(runtime)
    with pytest.raises(LlmDisabledError):
        await genesis(runtime, GenesisRequest("Aeron", "salt", LoreLanguage.ENGLISH, 1), Rules())


async def test_genesis_builds_world_and_three_sons(tmp_path: Path, rules: Rules, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "genesis.db")
    model = FakeModel()
    data = copy.deepcopy(PAYLOADS[PromptId.GENESIS_USER])
    data["sons"] = [{**data["sons"][index], "name": name} for index, name in enumerate(("Ozzeh", "Varum", "Kessa"))]
    model.script(output_model(PromptId.GENESIS_USER), output_model(PromptId.GENESIS_USER).model_validate(data))
    runtime = AgentRuntime(database=database, model=model, rules_override=rules)
    outcome = await genesis(runtime, GenesisRequest("Aeron", "a salt lake", LoreLanguage.ENGLISH, 7), rules)
    async with database.read() as session:
        sons = list(await session.scalars(select(SonRow).order_by(SonRow.id)))
        world = await session.get(WorldRow, outcome.world_id)
    await database.dispose()
    assert [son.rarity for son in sons] == [Rarity.COMMON, Rarity.RARE, Rarity.LEGENDARY]
    assert world is not None and world.epoch_star_entity_id is not None


def test_network_repair_tolerates_bare_numeric_keys() -> None:
    known = {"e12", "s3"}
    assert node_key("12", known) == "e12"
    assert node_key(" #3 ", known) == "s3"
    assert node_key("E12", known) == "e12"
    assert node_key("99", known) == "99"
