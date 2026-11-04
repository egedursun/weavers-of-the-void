from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.settlement import DistrictDesignRow, DistrictRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.domain.models.entity_stats import SettlementStats
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import urban
from aerona.services.player.catalog import ACTIONS_BY_ID
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def _undo(session: AsyncSession, entry_id: int | None, epoch: int) -> list[str]:
    assert entry_id is not None
    changes = await changes_of(session, entry_id)
    names = label_names(changes, await node_names(session, changes))
    return (await UndoRun(session, epoch, changes, names).run()).conflicts


def test_every_settlement_control_is_in_the_catalog() -> None:
    for key in ("settlement:foreigners", "district:design", "district:design_edit", "district:design_delete", "district:edit", "district:build"):
        assert key in ACTIONS_BY_ID


async def test_a_district_design_is_created_built_reworked_and_undone(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(
        session, "Brightwater", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id, stats=SettlementStats(population=3000)
    )
    created = await urban.design_district(
        scope, urban.DesignDistrict(world_id=world.world.id, name="Sky Market", base_kind=DistrictKind.MARKET, values={"goods_store": 2000})
    )
    design = await session.scalar(select(DistrictDesignRow).where(DistrictDesignRow.name == "Sky Market"))
    assert design is not None and design.goods_store == 2000
    await urban.build_district(scope, urban.BuildDistrict(settlement_id=town.id, design_id=design.id, material=BuildMaterial.STONE))
    built = await session.scalar(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id, DistrictRow.design_id == design.id))
    assert built is not None and built.kind is DistrictKind.MARKET
    edit = await urban.edit_district(scope, urban.EditDistrict(district_id=built.id, condition=55))
    assert built.locked == ["condition"]
    assert await _undo(session, edit.ledger_entry_id, world.cosmos.epoch) == []
    await session.refresh(built)
    assert built.condition == 100 and built.locked == []
    await urban.edit_district(scope, urban.EditDistrict(district_id=built.id, condition=60))
    await urban.edit_district(scope, urban.EditDistrict(district_id=built.id, release=["condition"]))
    assert built.locked == []
    await urban.edit_design(scope, urban.EditDesign(design_id=design.id, values={"order": 4}, name="Sky Bazaar"))
    assert design.name == "Sky Bazaar" and design.order == 4
    await urban.delete_design(scope, urban.DesignTarget(design_id=design.id))
    assert await session.get(DistrictDesignRow, design.id) is None
    assert created.ledger_entry_id is not None
