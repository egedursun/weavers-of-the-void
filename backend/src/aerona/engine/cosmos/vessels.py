from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.travel import VehicleKind


async def set_vessel_kind(session: AsyncSession, entity_id: int, kind: VehicleKind) -> None:
    row = await session.get(VesselProfileRow, entity_id)
    if row is None:
        session.add(VesselProfileRow(entity_id=entity_id, kind=kind))
    else:
        row.kind = kind
    await session.flush()


async def owned_vessels(session: AsyncSession, owner_id: int, kind: VehicleKind) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.target_node_id == EntityRow.id)
        .join(VesselProfileRow, VesselProfileRow.entity_id == EntityRow.id)
        .where(
            BondRow.source_node_id == owner_id,
            BondRow.kind == BondKind.OWNS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.entity_type == EntityType.VESSEL,
            EntityRow.status == EntityStatus.CANON,
            VesselProfileRow.kind == kind,
        )
        .order_by(EntityRow.id)
    )
    return list((await session.scalars(statement)).unique())
