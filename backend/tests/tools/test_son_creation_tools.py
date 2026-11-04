from typing import Any

import pytest

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.celestial import StarRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.world import StarType
from aerona.domain.models.profiles import TravelResource
from aerona.engine.cosmos.stars import EXTINGUISHED_STAR_TYPES
from aerona.tools.son.creation_inputs import CREATION_INPUTS
from aerona.tools.toolkit import TurnToolkit
from tests.tools.factories import DESCRIPTION, Realm, seed_realm, son_toolkit
from tests.tools.test_son_tools import entity, ok

CASES: dict[str, tuple[EntityType, dict[str, Any]]] = {
    "create_species": (EntityType.SPECIES, {"name": "Saltdrakes", "body_plan": "serpentine", "size_class": "large", "diet": "carnivore"}),
    "create_mortal": (EntityType.MORTAL, {"name": "Orsa Venn", "title": "the Keeper"}),
    "found_tradition": (EntityType.TRADITION, {"name": "Brine Rite"}),
    "found_cult": (EntityType.CULT, {"name": "Order of the Tide"}),
    "found_faction": (EntityType.FACTION, {"name": "Salt Guild"}),
    "hang_celestial": (EntityType.CELESTIAL, {"name": "Lantern Moon"}),
    "create_artwork": (EntityType.ARTWORK, {"name": "The Drowned Choir"}),
    "decree_law": (EntityType.LAW, {"name": "Law of Salt"}),
    "summon_spirit": (EntityType.SPIRIT, {"name": "Whisper of Brine"}),
    "inspire_knowledge": (EntityType.KNOWLEDGE, {"name": "Salt Smelting", "branch": "metallurgy"}),
    "utter_prophecy": (EntityType.PROPHECY, {"name": "The Seventh Tide"}),
    "start_event": (EntityType.EVENT, {"name": "The Long Drought"}),
    "create_vessel": (EntityType.VESSEL, {"name": "Saltwing"}),
    "decree_natural_law": (EntityType.NATURAL_LAW, {"name": "Law of Gentle Death", "mechanic": "short_life"}),
    "create_region": (EntityType.REGION, {"name": "The Whispering Marsh"}),
}


def _arguments(realm: Realm, extra: dict[str, Any]) -> dict[str, Any]:
    link = [{"target_kind": "entity", "target_id": realm.people_id, "kind": "related", "description": "born of their songs"}]
    return {"description": DESCRIPTION, "power_level": 2, "links": link, **extra}


@pytest.mark.parametrize("tool", sorted(CASES))
async def test_son_creation_tool_creates_the_entity(database: Database, tool: str) -> None:
    entity_type, extra = CASES[tool]
    realm = await seed_realm(database)
    toolkit: TurnToolkit = await son_toolkit(database, realm.son_id, action_points=3)
    if tool not in toolkit.catalogue.names:
        pytest.skip(f"{tool} is gated by world state in this realm")
    await ok(toolkit, tool, _arguments(realm, extra))
    created = await entity(database, toolkit.created_entity_ids[-1])
    assert created.entity_type is entity_type
    assert created.creator_son_id == realm.son_id
    assert created.name == extra["name"]


def test_every_creation_tool_has_an_input_model() -> None:
    assert {entity_type for entity_type, _ in CASES.values()} <= set(CREATION_INPUTS)


async def test_open_cosmic_bed_needs_a_travel_resource_then_opens_once(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=5)
    refused = await toolkit.runtime.call("open_cosmic_bed", {"region_id": realm.cosmos.region_id, "reason": "the star-salt must flow"})
    assert refused.is_error
    async with database.write() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        cosmos.travel_resource = TravelResource(name="Starsalt", rule="Folds space.")
    opened = await toolkit.runtime.call("open_cosmic_bed", {"region_id": realm.cosmos.region_id, "reason": "the star-salt must flow"})
    assert not opened.is_error, opened.text
    again = await toolkit.runtime.call("open_cosmic_bed", {"region_id": realm.cosmos.region_id, "reason": "the star-salt must flow"})
    assert again.is_error


async def test_extinguish_star_darkens_a_living_star(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        star = StarRow(name="Ember Eye", star_type=StarType.RED_GIANT, brightness=60, x=2.0, y=2.0, created_epoch=1)
        session.add(star)
        await session.flush()
        star_id = star.id
    toolkit = await son_toolkit(database, realm.son_id, action_points=5)
    result = await toolkit.runtime.call("extinguish_star", {"star_id": star_id, "reason": "the light has grown cruel"})
    assert not result.is_error, result.text
    async with database.read() as session:
        darkened = await session.get(StarRow, star_id)
        assert darkened is not None and darkened.star_type in EXTINGUISHED_STAR_TYPES
