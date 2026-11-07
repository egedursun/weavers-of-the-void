from dataclasses import replace
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.session import Database
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import CreationVerdictRow, EntityRow
from aerona.db.tables.lore import LexemeRow, MessageRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.warfare import ArmyRow, CaptiveRow
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityOrigin, EntityType, LegendCategory
from aerona.domain.enums.society import Commodity, KnowledgeBranch
from aerona.domain.enums.war import CaptiveStatus
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules
from aerona.rules.snapshot import with_value
from aerona.tools.toolkit import TurnToolkit
from tests.tools.factories import DESCRIPTION, Realm, connect, make_entity, mortal_toolkit, seed_realm
from tests.tools.test_son_tools import typed

LONG = DESCRIPTION
REASON = "because the tide demands it"


async def ok(toolkit: TurnToolkit, name: str, arguments: dict[str, Any]) -> str:
    outcome = await toolkit.runtime.call(name, typed(name, arguments))
    assert not outcome.is_error, outcome.text
    return outcome.text


async def rejected(toolkit: TurnToolkit, name: str, arguments: dict[str, Any]) -> str:
    outcome = await toolkit.runtime.call(name, typed(name, arguments))
    assert outcome.is_error, outcome.text
    return outcome.text


async def entity(database: Database, entity_id: int) -> EntityRow:
    async with database.read() as session:
        row = await session.get(EntityRow, entity_id)
        assert row is not None
        return row


async def bonds_between(database: Database, first: int, second: int, kind: BondKind) -> int:
    async with database.read() as session:
        return len(await BondRepository(session).active_between(first, second, [kind]))


async def count(database: Database, table: Any) -> int:
    async with database.read() as session:
        return int(await session.scalar(select(func.count()).select_from(table)) or 0)


async def teach(database: Database, realm: Realm, learner: int, branch: KnowledgeBranch, name: str) -> int:
    async with database.write() as session:
        knowledge = await make_entity(session, name, EntityType.KNOWLEDGE, world_id=realm.cosmos.world_id, knowledge_branch=branch)
        await connect(session, learner, knowledge.id, BondKind.KNOWS)
        return knowledge.id


async def test_tool_availability_follows_actor_type(database: Database) -> None:
    realm = await seed_realm(database)
    people = await mortal_toolkit(database, realm.people_id)
    mortal = await mortal_toolkit(database, realm.mortal_id)
    cult = await mortal_toolkit(database, realm.cult_id)
    assert "found_settlement" in people.catalogue.names and "adopt" not in people.catalogue.names
    assert "adopt" in mortal.catalogue.names and "raise_army" not in mortal.catalogue.names
    assert "preach" in cult.catalogue.names and "preach" not in people.catalogue.names
    assert "find_route" not in people.catalogue.names
    assert "look_at_world" not in people.catalogue.names
    assert "worship" in people.catalogue.free


async def test_read_tools_respect_the_knowledge_horizon(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await mortal_toolkit(database, realm.people_id)
    assert "Brinewatch" in await ok(toolkit, "inspect_entity", {"id": realm.settlement_id})
    assert "beyond what you know" in await rejected(toolkit, "inspect_entity", {"id": realm.other_people_id})
    found = await ok(toolkit, "search_entities", {"query": "Kin"})
    assert "Dune Kin" not in found


async def test_language_and_production(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=5)
    born = await ok(toolkit, "found_language", {"name": "Morrish", "description": LONG, "words": [{"word": "mor", "meaning": "home"}]})
    assert "Morrish" in born
    language = await entity(database, toolkit.created_entity_ids[-1])
    assert language.origin is EntityOrigin.MORTAL
    assert await bonds_between(database, realm.mortal_id, language.id, BondKind.SPEAKS) == 1
    await ok(toolkit, "coin_words", {"words": [{"word": "sela", "meaning": "salt"}]})
    assert await count(database, LexemeRow) == 2
    async with database.write() as session:
        await connect(session, realm.mortal_id, realm.resource_id, BondKind.OWNS)
    made = await ok(toolkit, "produce_item", {"name": "Salt Spear", "category": "weapon", "description": LONG, "resource_ids": [realm.resource_id]})
    assert "Damage" in made
    await ok(toolkit, "build_structure", {"name": "Tide Shrine", "structure_kind": "shrine", "description": LONG, "dedicated_son_id": realm.son_id})
    await ok(
        toolkit,
        "create_culture",
        {"kind": "legend", "name": "The Drowned Bell", "description": LONG, "related_ids": [realm.species_id], "legend_category": "relic"},
    )
    legend = await entity(database, toolkit.created_entity_ids[-1])
    assert legend.legend_category is LegendCategory.RELIC
    async with database.read() as session:
        verdicts = list(await session.scalars(select(CreationVerdictRow)))
        assert len(verdicts) >= 4
        assert all(verdict.verdict is Verdict.UNJUDGED for verdict in verdicts)


async def test_discovery_claim_and_settlement(database: Database) -> None:
    realm = await seed_realm(database)
    sure = replace(Rules(), mortal_tools=replace(Rules().mortal_tools, seize_defense=0, seize_die=1))
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=5, rules=sure)
    await ok(
        toolkit, "discover_resource", {"name": "Pearl Bed", "description": LONG, "location_id": realm.cosmos.region_id, "domain": "sea", "commodity": "ore"}
    )
    async with database.read() as session:
        commodity = await session.get(ResourceProfileRow, toolkit.created_entity_ids[-1])
    assert commodity is not None and commodity.commodity == Commodity.ORE.value
    assert "son_tools" not in await rejected(toolkit, "discover_resource", {"name": "Second Bed", "description": LONG, "location_id": realm.cosmos.region_id})
    async with database.write() as session:
        await connect(session, realm.faction_id, realm.resource_id, BondKind.OWNS)
        await weaken(session, realm.faction_id)
    await ok(toolkit, "claim_resource", {"resource_id": realm.resource_id})
    assert await bonds_between(database, realm.people_id, realm.resource_id, BondKind.OWNS) == 1
    settled = await ok(toolkit, "found_settlement", {"name": "Newbrine", "description": LONG, "location_id": realm.cosmos.region_id})
    assert "migrants" in settled
    assert (await entity(database, realm.people_id)).stats.model_dump()["population"] < 6000


async def test_trade_war_and_diplomacy(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=6)
    await ok(toolkit, "establish_trade", {"target_id": realm.settlement_id, "goods": "salt for nets"})
    assert "already trading" in await rejected(toolkit, "establish_trade", {"target_id": realm.settlement_id, "goods": "salt again"})
    await ok(toolkit, "declare_war", {"target_id": realm.faction_id, "reason": REASON})
    assert await bonds_between(database, realm.people_id, realm.faction_id, BondKind.ENEMY) == 1
    assert "already at war" in await rejected(toolkit, "declare_war", {"target_id": realm.faction_id, "reason": REASON})
    peace = await ok(toolkit, "diplomacy", {"target_id": realm.faction_id, "kind": "peace", "terms": "let the oars rest"})
    assert peace
    await ok(toolkit, "diplomacy", {"target_id": realm.settlement_id, "kind": "tribute", "terms": "a tenth of your catch"})
    await ok(toolkit, "build_spy_network", {"target_id": realm.cult_id, "cover": "pilgrims bearing salt"})
    assert await bonds_between(database, realm.people_id, realm.cult_id, BondKind.SPY_NETWORK) == 1


async def test_sabotage(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await mortal_toolkit(database, realm.faction_id)
    text = await ok(toolkit, "sabotage", {"target_id": realm.settlement_id, "kind": "arson", "how": "torches at the granary"})
    assert text


async def test_religion_tools(database: Database) -> None:
    realm = await seed_realm(database)
    people = await mortal_toolkit(database, realm.people_id, action_points=4)
    await ok(people, "worship", {"son_id": realm.sibling_id, "offering": "fire on the shore"})
    assert await bonds_between(database, realm.people_id, realm.sibling_id, BondKind.WORSHIPS) == 1
    assert await bonds_between(database, realm.people_id, realm.son_id, BondKind.WORSHIPS) == 0
    await ok(people, "pray_to_creator", {"prayer": "Father of all, hear the salt folk", "request": "rain"})
    assert await count(database, MessageRow) == 1
    await ok(people, "deny_god", {"reason": "the fire burned our boats"})
    assert await bonds_between(database, realm.people_id, realm.sibling_id, BondKind.WORSHIPS) == 0
    cult = await mortal_toolkit(database, realm.cult_id, action_points=3)
    await ok(cult, "preach", {"target_id": realm.settlement_id, "sermon": "The tide-god gives and the tide-god keeps."})
    await ok(cult, "prophesy", {"name": "The Saltfall", "saying": "When the third moon bleeds white, the sea will rise over Brinewatch."})


async def test_knowledge_tools(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=3)
    developed = await ok(toolkit, "develop_knowledge", {"name": "Brine Reading", "branch": "astronomy", "description": LONG})
    assert "level" in developed
    async with database.write() as session:
        await connect(session, realm.people_id, realm.mortal_id, BondKind.TRADES_WITH)
    learned = await ok(toolkit, "learn_knowledge", {"knowledge_id": realm.knowledge_id, "from_id": realm.mortal_id})
    assert "Tidecraft" in learned


async def test_hero_tools(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        child = await make_entity(
            session, "Pell", EntityType.MORTAL, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=MortalStats(hp=20, age=5, lifespan=70)
        )
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=4)
    await ok(toolkit, "go_on_adventure", {"target_id": realm.species_id, "goal": "to bring back a pelt"})
    assert await bonds_between(database, realm.mortal_id, realm.species_id, BondKind.HUNTS) == 1
    await ok(toolkit, "adopt", {"child_id": child.id, "reason": "an orphan of the storm"})
    assert await bonds_between(database, realm.mortal_id, child.id, BondKind.PARENT_OF) == 1
    defied = await ok(toolkit, "challenge_god", {"son_id": realm.son_id, "reason": "he drowned my father"})
    assert defied


async def test_cosmic_tools(database: Database) -> None:
    realm = await seed_realm(database)
    rules = Rules()
    async with database.write() as session:
        people = await session.get(EntityRow, realm.people_id)
        assert people is not None
        people.civ_tier = 3
        route = await session.get(RouteRow, realm.route_id)
        assert route is not None
    await teach(database, realm, realm.people_id, KnowledgeBranch.SKY_NAVIGATION, "Star Sailing")
    await teach(database, realm, realm.people_id, KnowledgeBranch.SHIPBUILDING, "Hull Craft")
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=6, rules=rules)
    assert "find_route" in toolkit.catalogue.names
    found = await ok(toolkit, "find_route", {"how": "reading the old star charts"})
    assert found
    ship = await ok(toolkit, "build_ship", {"name": "Saltwing", "description": LONG})
    assert "Saltwing" in ship
    went = await ok(toolkit, "launch_expedition", {"route_id": realm.route_id, "intent": "trade", "percent": 5})
    assert "arrive" in went
    assert await count(database, JourneyRow) == 1
    assert "already have an expedition" in await rejected(toolkit, "launch_expedition", {"route_id": realm.route_id, "intent": "trade"})
    explored = await toolkit.runtime.call("explore_land", {"kind": "place", "name": "Glimmer Cave", "description": LONG})
    assert explored.text


async def test_creature_tools(database: Database) -> None:
    realm = await seed_realm(database)
    await teach(database, realm, realm.people_id, KnowledgeBranch.BIOMANCY, "Flesh Weaving")
    await teach(database, realm, realm.people_id, KnowledgeBranch.MAGIC, "Old Words")
    async with database.write() as session:
        other = await make_entity(session, "Reefcrab", EntityType.SPECIES, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
        spirit = await make_entity(session, "Lost Bell", EntityType.SPIRIT, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
        item = await make_entity(session, "Bell of Brine", EntityType.ITEM, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=4)
    await toolkit.runtime.call("tame_species", {"species_id": realm.species_id, "how": "with salted meat"})
    woven = await ok(toolkit, "merge_species", {"a_id": realm.species_id, "b_id": other.id, "name": "Houndcrab", "goal": "a guardian for the shore"})
    assert "chimera" in woven.lower()
    bound = await ok(toolkit, "bind_spirit", {"spirit_id": spirit.id, "target_id": item.id})
    assert "bound" in bound
    assert "not a ruin" in await rejected(toolkit, "search_ruins", {"target_id": realm.settlement_id, "how": "digging below"})


async def test_captivity_tools(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        session.add(CaptiveRow(captive_entity_id=realm.mortal_id, captor_entity_id=realm.faction_id, status=CaptiveStatus.HELD, taken_epoch=1))
    people = await mortal_toolkit(database, realm.people_id)
    paid = await ok(people, "pay_ransom", {"captive_id": realm.mortal_id})
    assert "returned home" in paid
    async with database.read() as session:
        row = await session.scalar(select(CaptiveRow))
        assert row is not None and row.status is CaptiveStatus.RANSOMED


async def test_army_tools(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.read() as session:
        people = await session.get(EntityRow, realm.people_id)
        assert people is not None
        before = stat(people, "population") or 0
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=3)
    raised = await ok(toolkit, "raise_army", {"name": "Salt Spears", "percent": 10})
    assert "soldiers" in raised
    assert await count(database, ArmyRow) == 1
    async with database.read() as session:
        people = await session.get(EntityRow, realm.people_id)
        row = await session.scalar(select(ArmyRow))
        assert people is not None and row is not None
        army = await session.get(EntityRow, row.entity_id)
        assert army is not None
        assert (stat(people, "population") or 0) + (stat(army, "size") or 0) == before
    assert "already have an army" in await rejected(toolkit, "raise_army", {"name": "Second Spears"})
    await ok(toolkit, "appoint_commander", {"mortal_id": realm.mortal_id})


async def test_barter_and_debt(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        await connect(session, realm.people_id, realm.resource_id, BondKind.OWNS)
    people = await mortal_toolkit(database, realm.people_id, action_points=3)
    await ok(people, "barter", {"target_id": realm.settlement_id, "give_ids": [realm.resource_id], "terms": "a gift of glass"})
    assert await bonds_between(database, realm.settlement_id, realm.resource_id, BondKind.OWNS) == 1
    lent = await ok(people, "lend", {"debtor_id": realm.faction_id, "amount": 5, "what": "silver"})
    assert "owes you 5 silver" in lent
    assert "already owes" in await rejected(people, "lend", {"debtor_id": realm.faction_id, "amount": 5, "what": "silver"})
    faction = await mortal_toolkit(database, realm.faction_id)
    repaid = await ok(faction, "repay_debt", {"creditor_id": realm.people_id})
    assert "paid" in repaid
    assert await bonds_between(database, realm.faction_id, realm.people_id, BondKind.OWES) == 0


async def test_explored_region_gets_a_map_position(database: Database) -> None:
    realm = await seed_realm(database)
    rules = with_value(Rules(), "exploration", "tool_success_threshold", 0)
    async with database.write() as session:
        region = await session.get(EntityRow, realm.cosmos.region_id)
        assert region is not None
        region.map_x, region.map_y = 0.5, 0.5
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=2, rules=rules)
    await ok(toolkit, "explore_land", {"kind": "region", "name": "Farbrine Reach", "description": LONG})
    land = await entity(database, toolkit.created_entity_ids[0])
    assert land.entity_type is EntityType.REGION
    assert land.map_x is not None and land.map_y is not None


async def weaken(session: AsyncSession, entity_id: int) -> None:
    faction = await session.get(EntityRow, entity_id)
    assert faction is not None
    set_stats(faction, strength=0, wealth=0, sway=0)
