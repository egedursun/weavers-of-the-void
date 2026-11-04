from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.faith import CultTenetRow, ReincarnationRow, SpiritProfileRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import ReincarnationGate, TenetKind
from aerona.domain.models.entity_stats import SpiritStats
from aerona.prompts.tools.ids import SonToolId
from aerona.tools.son.availability import CONDITIONS
from tests.tools.factories import DESCRIPTION, connect, make_entity, seed_realm, son_toolkit
from tests.tools.test_son_tools import ok, rejected


async def test_a_god_reveals_a_tenet_to_its_own_cult(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    assert "reveal_tenet" in toolkit.catalogue.names
    text = await ok(toolkit, "reveal_tenet", {"cult_id": realm.cult_id, "tenet": "monastic_learning", "name": "The Salt Scrolls"})
    assert "The Salt Scrolls" in text
    async with database.read() as session:
        row = await session.get(CultTenetRow, (realm.cult_id, TenetKind.MONASTIC_LEARNING))
        assert row is not None and row.revealed_by_son_id == realm.son_id and row.name == "The Salt Scrolls"
        son = await session.get(SonRow, realm.son_id)
        assert son is not None
    again = await rejected(toolkit, "reveal_tenet", {"cult_id": realm.cult_id, "tenet": "proselytism"})
    assert "already" in again


async def test_a_god_cannot_reveal_to_another_gods_cult(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.sibling_id)
    text = await rejected(toolkit, "reveal_tenet", {"cult_id": realm.cult_id, "tenet": "proselytism"})
    assert "does not worship you" in text


async def test_a_god_opens_the_gate_of_rebirth_for_its_own(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        dead = await make_entity(session, "Old Mara", EntityType.MORTAL, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
        dead.status, dead.end_epoch = EntityStatus.DEAD, 1
        soul = await make_entity(
            session, "Shade of Mara", EntityType.SPIRIT, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id, stats=SpiritStats(unrest=10)
        )
        await connect(session, soul.id, dead.id, BondKind.DESCENDS_FROM)
        session.add(
            SpiritProfileRow(spirit_entity_id=soul.id, origin_mortal_id=dead.id, imprint={}, traits=[], deeds={}, patron_son_id=realm.son_id, locked=[])
        )
        sealed = await make_entity(session, "Sealed Shade", EntityType.SPIRIT, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
        session.add(
            SpiritProfileRow(spirit_entity_id=sealed.id, imprint={}, traits=[], deeds={}, patron_son_id=realm.son_id, sealed=True, seal_strength=90, locked=[])
        )
        await session.flush()
        soul_id, sealed_id = soul.id, sealed.id
    toolkit = await son_toolkit(database, realm.son_id)
    assert CONDITIONS[SonToolId.OPEN_REBIRTH_GATE]
    text = await ok(toolkit, "open_rebirth_gate", {"spirit_id": soul_id, "community_id": realm.settlement_id})
    assert "born again" in text
    async with database.read() as session:
        reborn = await session.scalar(select(ReincarnationRow).where(ReincarnationRow.spirit_entity_id == soul_id))
        assert reborn is not None and reborn.gate is ReincarnationGate.GOD
    refused = await rejected(toolkit, "open_rebirth_gate", {"spirit_id": sealed_id, "community_id": realm.settlement_id})
    assert "sealed" in refused


async def test_a_new_cult_is_founded_with_the_gods_tenets(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    link = [{"target_kind": "entity", "target_id": realm.people_id, "kind": "related", "description": "born of their songs"}]
    arguments = {
        "name": "Wardens of the Brine",
        "description": DESCRIPTION,
        "power_level": 2,
        "links": link,
        "tenets": ["pilgrimage_duty", "proselytism"],
        "judgement": "faith",
        "rebirth_path": "house",
    }
    text = await ok(toolkit, "found_cult", arguments)
    assert "doctrine is written" in text
    cult_id = toolkit.created_entity_ids[-1]
    async with database.read() as session:
        held = set(await session.scalars(select(CultTenetRow.tenet).where(CultTenetRow.cult_entity_id == cult_id)))
        assert {TenetKind.PILGRIMAGE_DUTY, TenetKind.PROSELYTISM} <= held
