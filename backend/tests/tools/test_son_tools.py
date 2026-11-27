from typing import Any

from sqlalchemy import func, select

from aerona.db.repositories.bonds import BondRepository
from aerona.db.session import Database
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import ForcedWeatherRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import CanonFactRow, ChronicleRow, LexemeRow, MessageRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType, LegendCategory
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import StarType
from aerona.engine.gods.progress import power_ceiling
from aerona.rules.registry import Rules
from aerona.tools.toolkit import TurnToolkit
from tests.tools.factories import DESCRIPTION, Realm, connect, make_entity, seed_realm, son_toolkit

LONG = DESCRIPTION
REASON = "because the tide demands it"


TYPED_DEFAULTS: dict[str, dict[str, str]] = {
    "tell_legend": {"archetype": "monster"},
    "create_artwork": {"medium": "musical"},
    "forge_item": {"item_class": "blade"},
    "found_tradition": {"tradition_kind": "festival"},
    "utter_prophecy": {"predicate": "sky_event"},
    "prophesy": {"predicate": "sky_event"},
}


def typed(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {**TYPED_DEFAULTS.get(name, {}), **arguments}


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


async def son(database: Database, son_id: int) -> SonRow:
    async with database.read() as session:
        row = await session.get(SonRow, son_id)
        assert row is not None
        return row


async def bonds_between(database: Database, first: int, second: int, kind: BondKind) -> int:
    async with database.read() as session:
        return len(await BondRepository(session).active_between(first, second, [kind]))


async def test_read_and_memory_tools(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    text = await ok(toolkit, "inspect_sibling", {"son_id": realm.sibling_id})
    assert "Veyra" in text and "Towards you" in text
    assert "world_summary" not in toolkit.catalogue.names
    await ok(toolkit, "write_plan", {"plan": "Raise a salt kingdom across the vale before the third age."})
    await ok(toolkit, "choose_anchor", {"entity_id": realm.resource_id, "reason": "the vein is my heart"})
    assert (await son(database, realm.son_id)).anchor_entity_id == realm.resource_id
    limit = await rejected(toolkit, "choose_anchor", {"entity_id": realm.resource_id, "reason": "once more for luck"})
    assert "son_tools.anchor_per_epoch" in limit


async def test_language_tool_coins_words(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    words = [{"word": "sel", "meaning": "salt"}, {"word": "varo", "meaning": "tide", "kind": "noun"}]
    text = await ok(toolkit, "coin_words", {"language_id": realm.language_id, "words": words})
    assert "sel" in text
    again = await ok(toolkit, "coin_words", {"language_id": realm.language_id, "words": words})
    assert "No word was added" in again
    async with database.read() as session:
        assert int(await session.scalar(select(func.count()).select_from(LexemeRow)) or 0) == 2


async def test_kin_tools(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=5)
    await ok(toolkit, "call_sibling", {"son_id": realm.sibling_id, "intent": "love", "message": "Your fire warms my sea"})
    await ok(toolkit, "call_sibling", {"son_id": realm.sibling_id, "intent": "alliance", "message": "Stand with me, sister"})
    covenant = await toolkit.runtime.call("swear_covenant", {"son_id": realm.sibling_id, "terms": "salt and fire forever"})
    if covenant.is_error:
        assert "does not trust you enough" in covenant.text
    async with database.write() as session:
        sibling = await session.get(SonRow, realm.sibling_id)
        assert sibling is not None
        sibling.essence = 10
    gift = await ok(toolkit, "give_gift", {"son_id": realm.sibling_id, "essence": 10, "words": "take this salt"})
    assert "10 essence" in gift
    duel = await ok(toolkit, "challenge", {"son_id": realm.sibling_id, "stat": "cunning", "reason": "to test her wits"})
    assert "Your relation" in duel
    async with database.read() as session:
        assert int(await session.scalar(select(func.count()).select_from(MessageRow)) or 0) == 2


async def test_prayer_and_rebellion(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    await ok(toolkit, "pray_to_creator", {"message": "Creator, grant me strength", "request": "essence"})
    await ok(toolkit, "rebel", {"proclamation": "Your silence is a chain; I break it today."})
    assert (await son(database, realm.son_id)).rebel
    assert "already in rebellion" in await rejected(toolkit, "rebel", {"proclamation": "Your silence is a chain; I break it again."})


async def test_creation_tools(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=2)
    link = [{"target_kind": "entity", "target_id": realm.people_id, "kind": "related", "description": "born of their songs"}]
    text = await ok(
        toolkit,
        "create_people",
        {"name": "Ormatai", "description": LONG, "power_level": 3, "domain": "sea", "location_id": realm.cosmos.region_id, "links": link},
    )
    assert "Created" in text
    created = await entity(database, toolkit.created_entity_ids[-1])
    assert created.entity_type is EntityType.PEOPLE
    assert created.creator_son_id == realm.son_id
    assert await bonds_between(database, created.id, realm.son_id, BondKind.WORSHIPS) == 0
    item = await ok(
        toolkit,
        "forge_item",
        {
            "name": "Brineknife",
            "item_class": "blade",
            "description": LONG,
            "power_level": 2,
            "links": [{"target_kind": "entity", "target_id": realm.resource_id, "kind": "source_of"}],
            "location_id": realm.settlement_id,
        },
    )
    assert "Brineknife" in item
    forged = await entity(database, toolkit.created_entity_ids[-1])
    async with database.read() as session:
        owners = await BondRepository(session).incoming(forged.id, BondKind.OWNS)
        assert owners
    taken = await rejected(toolkit, "create_place", {"place_kind": "cave", "name": "Brineknife", "description": LONG, "power_level": 1, "links": link})
    assert "already exists" in taken
    numbered = await rejected(toolkit, "create_place", {"place_kind": "cave", "name": "Hollow III", "description": LONG, "power_level": 1, "links": link})
    assert "numbered name" in numbered
    language = await ok(
        toolkit,
        "create_language",
        {"name": "Vellish", "description": LONG, "power_level": 1, "links": link, "words": [{"word": "vel", "meaning": "wave"}]},
    )
    assert "Vellish" in language
    async with database.write() as session:
        for index in range(Rules().exploration.crowded_communities_per_region):
            await make_entity(session, f"Shore Folk {index}", EntityType.PEOPLE, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
    crowded = await ok(
        toolkit,
        "create_place",
        {"place_kind": "cave", "name": "Lastshore", "description": LONG, "power_level": 1, "links": link, "location_id": realm.cosmos.region_id},
    )
    assert "Remaining actions: 0" in crowded
    spent = await rejected(
        toolkit,
        "create_place",
        {"place_kind": "cave", "name": "Farshore", "description": LONG, "power_level": 1, "links": link, "location_id": realm.cosmos.region_id},
    )
    assert "spent" in spent


async def test_power_ceiling_follows_rarity(database: Database) -> None:
    realm = await seed_realm(database, rarity=Rarity.COMMON)
    toolkit = await son_toolkit(database, realm.son_id)
    link = [{"target_id": realm.people_id, "kind": "related", "description": "near them"}]
    ceiling = await rejected(toolkit, "create_place", {"place_kind": "cave", "name": "Deepreach", "description": LONG, "power_level": 5, "links": link})
    assert "at most 2" in ceiling


async def test_mythic_son_creates_up_to_its_own_ceiling(database: Database) -> None:
    realm = await seed_realm(database, rarity=Rarity.MYTHIC)
    toolkit = await son_toolkit(database, realm.son_id)
    link = [{"target_id": realm.people_id, "kind": "related", "description": "near them"}]
    async with database.read() as session:
        son = await session.get(SonRow, realm.son_id)
        assert son is not None
        ceiling = power_ceiling(Rules(), son)
    assert ceiling > 10
    await ok(toolkit, "create_place", {"place_kind": "cave", "name": "Highreach", "description": LONG, "power_level": ceiling, "links": link})
    over = await rejected(toolkit, "create_place", {"place_kind": "cave", "name": "Overreach", "description": LONG, "power_level": ceiling + 1, "links": link})
    assert f"at most {ceiling}" in over


async def test_make_bond_and_harvest(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    await ok(toolkit, "make_bond", {"source_id": realm.people_id, "target": {"target_kind": "entity", "target_id": realm.species_id, "kind": "fears"}})
    assert await bonds_between(database, realm.people_id, realm.species_id, BondKind.FEARS) == 1
    mechanical = await rejected(toolkit, "make_bond", {"source_id": realm.people_id, "target": {"target_id": realm.species_id, "kind": "owns"}})
    assert "mechanical bond" in mechanical
    before = (await son(database, realm.son_id)).essence
    text = await ok(toolkit, "harvest_resource", {"resource_id": realm.resource_id})
    assert "+" in text
    assert (await son(database, realm.son_id)).essence >= before
    assert "already harvested" in await rejected(toolkit, "harvest_resource", {"resource_id": realm.resource_id})


async def test_influence_tools(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=5)
    await ok(toolkit, "affect_entity", {"entity_id": realm.settlement_id, "changes": [{"stat": "prosperity", "percent": 20}], "reason": "enrich the harbour"})
    assert (await entity(database, realm.settlement_id)).stats.model_dump()["prosperity"] == 70
    await ok(toolkit, "declare_chosen", {"mortal_id": realm.mortal_id, "boon": "the tide answers her"})
    assert await bonds_between(database, realm.mortal_id, realm.son_id, BondKind.WORSHIPS) == 1
    await ok(toolkit, "curse", {"entity_id": realm.faction_id, "curse": "may your oars rot"})
    assert "already cursed" in await rejected(toolkit, "curse", {"entity_id": realm.faction_id, "curse": "rot twice over"})
    await ok(toolkit, "send_dream", {"target_id": realm.faction_id, "dream": "A tide of salt rises beneath your ships"})
    taught = await ok(toolkit, "teach_knowledge", {"target_id": realm.people_id, "knowledge_id": realm.knowledge_id, "how": "through singing waves"})
    assert "now knows" in taught


async def test_intervention_tools(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=5)
    await ok(toolkit, "miracle", {"entity_id": realm.settlement_id, "kind": "protection", "how": "a ring of salt rises around the walls"})
    disaster = await ok(
        toolkit,
        "send_disaster",
        {"target_id": realm.cosmos.place_id, "kind": "flood", "name": "Brine Deluge", "description": "The sea climbs the hollow at night.", "reason": REASON},
    )
    assert "Brine Deluge" in disaster
    old_name = (await entity(database, realm.species_id)).name
    async with database.write() as session:
        people = await session.get(EntityRow, realm.people_id)
        assert people is not None
        people.description = f"They fear the {old_name} of the dunes."
    await ok(toolkit, "transform", {"entity_id": realm.species_id, "new_name": "Saltwolf", "new_description": LONG, "reason": REASON})
    assert (await entity(database, realm.species_id)).name == "Saltwolf"
    assert (await entity(database, realm.people_id)).description == "They fear the Saltwolf of the dunes."
    await ok(toolkit, "destroy", {"entity_id": realm.faction_id, "reason": REASON})
    assert (await entity(database, realm.faction_id)).status is EntityStatus.DESTROYED


async def test_war_tools(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=6)
    await toolkit.runtime.call("incite_war", {"a_id": realm.people_id, "b_id": realm.faction_id, "pretext": "a stolen net of pearls"})
    treaty = await ok(
        toolkit, "make_interworld_treaty", {"a_id": realm.settlement_id, "b_id": realm.other_people_id, "kind": "trade", "terms": "salt for sand-glass"}
    )
    assert "Treaty made" in treaty
    assert await bonds_between(database, realm.settlement_id, realm.other_people_id, BondKind.TRADES_WITH) == 1
    war = await ok(toolkit, "war_on_foreign_god", {"god_id": realm.god_id, "reason": "he drowned my faithful"})
    assert "Ombrun" in war


async def test_death_tools(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        dead = await session.get(SonRow, realm.sibling_id)
        assert dead is not None
        dead.status = SonStatus.DEAD
        dead.death_epoch = 1
    toolkit = await son_toolkit(database, realm.son_id, action_points=5)
    text = await ok(toolkit, "take_life", {"entity_id": realm.mortal_id, "how": "a wave at midnight"})
    assert "chance" in text
    plot = await ok(toolkit, "resurrect_sibling", {"son_id": realm.sibling_id, "path": "rite"})
    assert "devotion" in plot.lower()
    assert "already plotted" in await rejected(toolkit, "hinder_return", {"son_id": realm.sibling_id})


async def test_cosmic_tools(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        session.add(StarRow(name="Cinder Eye", star_type=StarType.DEAD_STAR, brightness=0, x=1.0, y=1.0, created_epoch=1))
        world = await session.get(WorldRow, realm.cosmos.world_id)
        assert world is not None
        world.leakage = 40
        outer = await make_entity(session, "The Unsaid", EntityType.OUTER_BEING, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
        spirit = await make_entity(session, "Drowned Whisper", EntityType.SPIRIT, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
        statue = await make_entity(session, "Tide Pillar", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
        await connect(session, realm.son_id, realm.other_people_id, BondKind.RELATED)
        star_id = await session.scalar(select(StarRow.id).where(StarRow.name == "Cinder Eye"))
    toolkit = await son_toolkit(database, realm.son_id, action_points=10)
    await ok(toolkit, "seal_leak", {"how": "with clay and prayer"})
    await ok(toolkit, "bind_spirit", {"spirit_id": spirit.id, "target_id": statue.id})
    await ok(toolkit, "rekindle_star", {"star_id": star_id})
    await ok(toolkit, "hang_star", {"name": "Pale Lantern", "description": "A small white star that hums at dusk."})
    talk = await ok(toolkit, "talk_to_foreign_god", {"god_id": realm.god_id, "intent": "bargain", "words": "let us share the storm"})
    assert "Ombrun" in talk
    gained = await ok(toolkit, "bargain_with_outsider", {"outsider_id": outer.id, "request": "eyes to see the far shore"})
    assert "essence" in gained
    await ok(toolkit, "declare_holy_world", {"world_id": realm.cosmos.world_id})
    moved = await ok(toolkit, "move_to_world", {"world_id": realm.other_world_id})
    assert "Velmor" in moved
    assert (await son(database, realm.son_id)).current_world_id == realm.other_world_id
    await ok(toolkit, "seal_gate", {"route_id": realm.route_id, "reason": "nothing more shall pass"})
    async with database.read() as session:
        route = await session.get(RouteRow, realm.route_id)
        assert route is not None and not route.active
        god = await session.get(ForeignGodRow, realm.god_id)
        assert god is not None
        lines = int(await session.scalar(select(func.count()).select_from(ChronicleRow).where(ChronicleRow.son_id == realm.son_id)) or 0)
        assert lines >= 5
        orphan = int(await session.scalar(select(func.count()).select_from(BondRow).where(BondRow.source_node_id == realm.son_id)) or 0)
        assert orphan >= 1
    del outer, spirit, statue


async def test_cross_world_reach(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        route = await session.get(RouteRow, realm.route_id)
        assert route is not None
        route.active = False
    toolkit = await son_toolkit(database, realm.son_id)
    text = await rejected(toolkit, "harvest_resource", {"resource_id": await _far_resource(database, realm)})
    assert "another world" in text


async def _far_resource(database: Database, realm: Realm) -> int:
    async with database.write() as session:
        far = await make_entity(session, "Dune Glass", EntityType.RESOURCE, world_id=realm.other_world_id, creator_son_id=realm.son_id)
        return far.id


async def test_creation_sets_legend_category_and_commodity(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    link = [{"target_kind": "entity", "target_id": realm.people_id, "kind": "related", "description": "told among them"}]
    await ok(
        toolkit,
        "tell_legend",
        {"name": "The Salt Wyrm", "description": LONG, "power_level": 1, "links": link, "legend_category": "creature", "archetype": "monster"},
    )
    legend = await entity(database, toolkit.created_entity_ids[-1])
    assert legend.legend_category is LegendCategory.CREATURE
    await ok(
        toolkit,
        "create_resource",
        {"name": "Ironbrine Vein", "description": LONG, "power_level": 1, "links": link, "location_id": realm.cosmos.region_id, "commodity": "ore"},
    )
    async with database.read() as session:
        row = await session.get(ResourceProfileRow, toolkit.created_entity_ids[-1])
    assert row is not None and row.commodity == Commodity.ORE.value


async def test_inspect_shows_society_and_canon_facts(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        session.add(CanonFactRow(subject_entity_id=realm.people_id, predicate="fears", object_text="the deep tide", epoch=1))
    toolkit = await son_toolkit(database, realm.son_id, action_points=1)
    text = await ok(toolkit, "inspect_entity", {"id": realm.people_id})
    assert "fears the deep tide" in text


async def test_a_sky_god_holds_the_weather_over_a_region(database: Database) -> None:
    realm = await seed_realm(database)
    region = realm.cosmos.region_id
    sea = await son_toolkit(database, realm.son_id)
    assert "not in your domains" in await rejected(sea, "shape_weather", {"region_id": region, "weather": "storm", "epochs": 2, "reason": REASON})
    async with database.write() as session:
        row = await session.get(SonRow, realm.son_id)
        assert row is not None
        row.domain_primary = Domain.STORM
    sky = await son_toolkit(database, realm.son_id)
    shaped = await ok(sky, "shape_weather", {"region_id": region, "weather": "storm", "epochs": 99, "reason": REASON})
    assert "Storm" in shaped
    async with database.read() as session:
        forced = await session.scalar(select(ForcedWeatherRow))
        assert forced is not None and forced.kind is WeatherKind.STORM and forced.son_id == realm.son_id
        assert forced.until_epoch - forced.from_epoch + 1 == Rules().son_tools.shape_weather_max_epochs
