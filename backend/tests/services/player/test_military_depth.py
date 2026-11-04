from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.military import FeudRow, UnitDesignRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import HullClass
from aerona.services.player import military_depth
from aerona.services.player.scope import PlayerScope
from tests.engine.warfare.factories import make
from tests.services.player.factories import PlayerWorld


async def test_a_unit_design_is_created_held_released_and_struck(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await military_depth.create(scope, military_depth.RecordCreate(kind="unit_design", values={"name": "Bone Wardens", "base_kind": "spearmen", "defence": 80}))
    design = await session.scalar(select(UnitDesignRow))
    assert design is not None and design.defence == 80
    await military_depth.edit(scope, military_depth.RecordEdit(kind="unit_design", record_id=design.id, values={"melee": 70}))
    assert design.melee == 70 and design.locked == ["melee"]
    await military_depth.release(scope, military_depth.RecordRelease(kind="unit_design", record_id=design.id))
    assert design.locked == []
    await military_depth.delete(scope, military_depth.RecordDelete(kind="unit_design", record_id=design.id))
    assert await session.scalar(select(UnitDesignRow)) is None


async def test_a_feud_is_started_by_decree(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world.world.id, population=900)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world.world.id, population=900)
    values = {"first_entity_id": first.id, "second_entity_id": second.id, "intensity": 70}
    await military_depth.create(scope, military_depth.RecordCreate(kind="feud", values=values))
    feud = await session.scalar(select(FeudRow))
    assert feud is not None and feud.intensity == 70


async def test_a_vessel_is_laid_down_and_refitted(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    port = await make(session, "Gull Harbour", EntityType.SETTLEMENT, world.world.id, population=900)
    effect = await military_depth.vessel_create(scope, military_depth.VesselOrder(owner_id=port.id, name="Grey Gull", hull_class=HullClass.COG))
    vessel_id = effect.created_ids[0]
    row = await session.get(VesselProfileRow, vessel_id)
    assert row is not None and row.hull_class is HullClass.COG
    await military_depth.vessel_refit(scope, military_depth.VesselRefit(vessel_id=vessel_id, hull_class=HullClass.CARRACK))
    assert row.hull_class is HullClass.CARRACK and row.cargo_capacity == scope.rules.seafaring.carrack_cargo


async def test_an_army_is_raised_in_peace(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    folk = await make(session, "Iron Folk", EntityType.PEOPLE, world.world.id, population=9000)
    effect = await military_depth.raise_army(scope, military_depth.RaiseArmy(community_id=folk.id, size=300))
    assert effect.created_ids
