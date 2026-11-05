from aerona.db.session import Database
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.primitives.holds import ANCHOR_KEY, set_held
from aerona.rules.registry import Rules
from aerona.rules.snapshot import with_value
from tests.tools.factories import EPOCH, connect, make_entity, seed_realm, son_toolkit


async def test_a_son_anchors_to_a_structure_dedicated_to_him_unless_the_anchor_is_held(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        temple = await make_entity(session, "Salt Temple", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, stats=StructureStats(splendor=40))
        stranger = await make_entity(session, "Ash Shrine", EntityType.STRUCTURE, world_id=realm.cosmos.world_id, stats=StructureStats(splendor=40))
        await connect(session, temple.id, realm.son_id, BondKind.WORSHIPS)
        await connect(session, stranger.id, realm.sibling_id, BondKind.WORSHIPS)
        temple_id, stranger_id = temple.id, stranger.id
    toolkit = await son_toolkit(database, realm.son_id)
    refused = await toolkit.runtime.call("choose_anchor", {"entity_id": stranger_id, "reason": "a shrine of my sister"})
    assert refused.is_error and "dedicated to you" in refused.text
    chosen = await toolkit.runtime.call("choose_anchor", {"entity_id": temple_id, "reason": "the temple keeps my name"})
    assert not chosen.is_error, chosen.text
    async with database.read() as session:
        son = await session.get(SonRow, realm.son_id)
        assert son is not None and son.anchor_entity_id == temple_id
    async with database.write() as session:
        await set_held(session, realm.son_id, ANCHOR_KEY, EPOCH, True)
    held_kit = await son_toolkit(database, realm.son_id, rules=with_value(Rules(), "son_tools", "anchor_per_epoch", 2))
    held = await held_kit.runtime.call("choose_anchor", {"entity_id": temple_id, "reason": "again and for ever"})
    assert held.is_error and "holds your anchor" in held.text
