from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.war_w52 import DEFENCES
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.honours import NamedUnitRow, UnitHonourRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.settlement import SettlementInfrastructureRow
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.settlement import WaterSupply
from aerona.engine.military.engineering import RIVERS

UNKNOWN_PLACE = "an unrecorded field"


async def misplaced_moles(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(SpyNetworkRow).where(SpyNetworkRow.institution_entity_id.is_not(None)).order_by(SpyNetworkRow.id)):
        place = await session.get(EntityRow, row.institution_entity_id)
        if place is None or place.status is not EntityStatus.CANON or row.target_entity_id not in {place.id, place.location_id}:
            found.append(row.id)
    return found


async def unplace_mole(session: AsyncSession, key: int) -> None:
    row = await session.get(SpyNetworkRow, key)
    if row is not None:
        row.institution_entity_id = None


async def dry_floods(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for siege in await session.scalars(select(SiegeRow).where(SiegeRow.last_defence.is_not(None)).order_by(SiegeRow.id)):
        if siege.last_defence is None or not DEFENCES[siege.last_defence].needs_water:
            continue
        town = await session.get(EntityRow, siege.besieged_entity_id)
        ground = await session.get(RegionEnvironmentRow, town.location_id) if town is not None and town.location_id is not None else None
        walls = await session.get(SettlementInfrastructureRow, siege.besieged_entity_id)
        if (ground is None or ground.river_class not in RIVERS) and (walls is None or walls.water is not WaterSupply.AQUEDUCT):
            found.append(siege.id)
    return found


async def drop_flood(session: AsyncSession, key: int) -> None:
    siege = await session.get(SiegeRow, key)
    if siege is not None:
        siege.last_defence = None


async def unplaced_honours(session: AsyncSession) -> list[int]:
    return list(await session.scalars(select(UnitHonourRow.id).where(UnitHonourRow.note == "").order_by(UnitHonourRow.id)))


async def place_honour(session: AsyncSession, key: int) -> None:
    row = await session.get(UnitHonourRow, key)
    if row is None:
        return
    unit = await session.get(NamedUnitRow, row.named_unit_id)
    row.note = unit.name if unit is not None else UNKNOWN_PLACE
