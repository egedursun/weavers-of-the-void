from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.settlement import DistrictDesignRow, DistrictRow
from aerona.domain.enums.settlement import DistrictKind
from tests.tools.factories import seed_realm, son_toolkit
from tests.tools.test_son_tools import REASON, ok, rejected


async def test_a_son_devises_a_district_design_and_raises_it_in_a_city(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id)
    designed = await ok(toolkit, "design_district", {"name": "Tide Hall", "base_kind": "harbour", "harbour": 700, "order": 2, "reason": REASON})
    assert "Tide Hall" in designed
    async with database.read() as session:
        design = await session.scalar(select(DistrictDesignRow).where(DistrictDesignRow.name == "Tide Hall"))
        assert design is not None and design.harbour == 700 and design.created_by_son_id == realm.son_id
        design_id = design.id
    raised = await ok(toolkit, "raise_district", {"settlement_id": realm.settlement_id, "design_id": design_id, "reason": REASON})
    assert "harbour" in raised
    async with database.read() as session:
        built = await session.scalar(select(DistrictRow).where(DistrictRow.design_id == design_id))
        assert built is not None and built.kind is DistrictKind.HARBOUR and built.built_by_son_id == realm.son_id
    assert "settlements" in await rejected(toolkit, "raise_district", {"settlement_id": realm.people_id, "kind": "market", "reason": REASON})
