from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.operations import PLACED_GROUNDS
from aerona.catalog.terrain import terrain_has
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmography import RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.mass_weapons import WarRemnantRow
from aerona.db.tables.operations import ExpeditionRow
from aerona.db.tables.sites import BattlefieldFeatureRow
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TerrainTrait
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.operations import ExpeditionGround, ExpeditionStatus
from aerona.domain.enums.site import BattlefieldFeature

UNDER_WAY = (ExpeditionStatus.UNDERWAY, ExpeditionStatus.CAMPED)


async def remnantless_ordnance(session: AsyncSession) -> list[int]:
    found: list[int] = []
    rows = await session.scalars(
        select(BattlefieldFeatureRow).where(BattlefieldFeatureRow.feature == BattlefieldFeature.ORDNANCE).order_by(BattlefieldFeatureRow.id)
    )
    for row in rows:
        if row.remnant_id is None or await session.get(WarRemnantRow, row.remnant_id) is None:
            found.append(row.id)
    return found


async def clear_ordnance(session: AsyncSession, key: int) -> None:
    row = await session.get(BattlefieldFeatureRow, key)
    if row is not None:
        await session.delete(row)


async def ground_fits(session: AsyncSession, row: ExpeditionRow) -> bool:
    target = await session.get(EntityRow, row.target_entity_id) if row.target_entity_id is not None else None
    if target is None or row.ground not in PLACED_GROUNDS:
        return True
    if row.ground is ExpeditionGround.DIMENSION:
        rift = await session.scalar(select(RiftRow.id).where(RiftRow.region_entity_id == target.id, RiftRow.state.in_(sorted(OPEN_RIFT_STATES))).limit(1))
        return rift is not None
    vessel = await session.get(VesselProfileRow, target.id)
    if row.ground is ExpeditionGround.SPACE:
        return vessel is not None and vessel.status is VesselStatus.WRECKED
    land = await session.get(RegionEnvironmentRow, target.id if target.entity_type is EntityType.REGION else (target.location_id or 0))
    return (land is not None and terrain_has(land.dominant_terrain, TerrainTrait.WATERY)) or (vessel is not None and vessel.status is VesselStatus.WRECKED)


async def misgrounded_expeditions(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(ExpeditionRow).where(ExpeditionRow.status.in_(UNDER_WAY)).order_by(ExpeditionRow.id))
    return [row.id for row in rows if "ground" not in row.locked and not await ground_fits(session, row)]


async def reground_expedition(session: AsyncSession, key: int) -> None:
    row = await session.get(ExpeditionRow, key)
    target = await session.get(EntityRow, row.target_entity_id) if row is not None and row.target_entity_id is not None else None
    if row is not None:
        row.ground = ExpeditionGround.WILDS if target is not None and target.entity_type is EntityType.REGION else ExpeditionGround.SITE
        row.air = 0
