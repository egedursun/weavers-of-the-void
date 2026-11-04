from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.economy import NodeMaterialRow, ResourceProfileRow, WorldMaterialRow
from aerona.domain.enums.economy import MaterialFamily, MaterialOrigin, MaterialSlot
from aerona.domain.enums.material import MaterialKind
from tests.tools.factories import DESCRIPTION, seed_realm, son_toolkit
from tests.tools.test_son_tools import ok, rejected

REASON = "so that the faithful may fight the dead"


async def test_a_son_forges_a_typed_material_with_a_vein(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    text = await ok(
        toolkit,
        "forge_material",
        {
            "world_id": realm.cosmos.world_id,
            "name": "Dawnsilver",
            "family": MaterialFamily.PRECIOUS.value,
            "base_kind": MaterialKind.SILVER.value,
            "sanctity": 98,
            "rarity": 90,
            "place_id": realm.cosmos.region_id,
            "reason": REASON,
        },
    )
    assert "Dawnsilver" in text
    async with database.read() as session:
        row = await session.scalar(select(WorldMaterialRow).where(WorldMaterialRow.name == "Dawnsilver"))
        assert row is not None and row.origin is MaterialOrigin.DIVINE and row.sanctity == 98 and row.deposit_entity_id is not None
        vein = await session.get(ResourceProfileRow, row.deposit_entity_id)
        assert vein is not None and vein.world_material_id == row.id
    assert "world" in await rejected(toolkit, "forge_material", {"world_id": 999, "name": "Nothing", "family": "metal", "reason": REASON})


async def test_a_son_sets_the_material_of_what_it_creates(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    link = [{"target_kind": "entity", "target_id": realm.people_id, "kind": "related", "description": "carried by them"}]
    await ok(
        toolkit,
        "forge_item",
        {"name": "Sunbrand", "description": DESCRIPTION, "power_level": 1, "links": link, "material": MaterialKind.GOLD.value},
    )
    async with database.read() as session:
        body = await session.get(NodeMaterialRow, (toolkit.created_entity_ids[-1], MaterialSlot.BODY))
        assert body is not None and body.material is MaterialKind.GOLD
