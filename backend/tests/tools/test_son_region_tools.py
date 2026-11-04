from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.region import RegionDangerRow
from aerona.domain.enums.region import DangerOrigin, DangerSource
from aerona.rules.registry import Rules
from tests.services.player.test_regions import ground_for
from tests.tools.factories import seed_realm, son_toolkit
from tests.tools.test_son_tools import REASON, ok, rejected


async def test_a_son_sanctifies_curses_and_cannot_turn_a_river_into_a_far_land(database: Database) -> None:
    realm = await seed_realm(database)
    region = realm.cosmos.region_id
    async with database.write() as session:
        session.add(ground_for(region, realm.cosmos.world_id))
    toolkit = await son_toolkit(database, realm.son_id)
    hallowed = await ok(toolkit, "sanctify_region", {"region_id": region, "sacredness": 70, "reason": REASON})
    assert "sacredness is 70" in hallowed
    cursed = await ok(toolkit, "curse_region", {"region_id": region, "danger": "monsters", "strength": 100, "reason": REASON})
    assert "Monsters" in cursed
    async with database.read() as session:
        row = await session.scalar(select(RegionDangerRow))
        assert row is not None and row.source is DangerSource.MONSTERS and row.origin is DangerOrigin.DIVINE
        assert row.strength == Rules().terrain.curse_strength_max and row.son_id == realm.son_id
    refused = await rejected(toolkit, "redirect_river", {"from_region_id": region, "to_region_id": region, "reason": REASON})
    assert "cannot be turned" in refused
