from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.network_repair import companion_ok, node_of
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.prompts.contexts.cosmos import GraphNode, GraphNodeKind
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules

REASON = "they travelled together across the hills for many long years"


async def test_a_companion_link_needs_a_full_reason_and_ends_that_can_travel(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(link_graph={"companion_reason_min_chars": 10, "companion_reason_min_words": 6})
    town = await settlement(session, "Brookhold", world, world.regions[0])
    assert companion_ok(rules, REASON, [world.people, world.son])
    assert not companion_ok(rules, "friends", [world.people, world.son])
    assert not companion_ok(rules, REASON, [world.people, town])
    assert town.entity_type is EntityType.SETTLEMENT


async def test_a_graph_node_resolves_to_its_son_or_its_record(session: AsyncSession, world: CoreWorld) -> None:
    son = await node_of(session, GraphNode(kind=GraphNodeKind.SON, id=world.son.id, name=world.son.name))
    found = await node_of(session, GraphNode(kind=GraphNodeKind.ENTITY, id=world.people.id, name=world.people.name))
    assert son is world.son and isinstance(found, EntityRow) and found.id == world.people.id
