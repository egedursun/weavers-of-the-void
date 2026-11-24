from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.schemas.entities import EntityLevel, LevelChoice
from aerona.api.views.common import node_ref
from aerona.catalog.strata import STRATA
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.geology import RegionStratumRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import ModifierSource
from aerona.engine.environment.levels import unfit_below


async def level_of(session: AsyncSession, entity: EntityRow) -> EntityLevel | None:
    region = await session.get(EntityRow, entity.location_id) if entity.location_id is not None else None
    if region is None or region.entity_type is not EntityType.REGION:
        return None
    reference = await node_ref(session, region.id)
    if reference is None:
        return None
    cells = sorted(
        await session.scalars(select(RegionStratumRow).where(RegionStratumRow.region_entity_id == region.id).order_by(RegionStratumRow.id)),
        key=lambda row: list(STRATA).index(row.stratum),
    )
    pinned = await session.scalar(
        select(ModifierRow.id)
        .where(ModifierRow.target_node_id == entity.id, ModifierRow.target_key == "stratum", ModifierRow.source_kind == ModifierSource.PIN)
        .limit(1)
    )
    return EntityLevel(
        region=reference,
        stratum=entity.stratum,
        held=pinned is not None,
        choices=[
            LevelChoice(
                stratum=cell.stratum,
                name=cell.name,
                dwellable=STRATA[cell.stratum].dwellable,
                reason=f"no one can dwell in the {STRATA[cell.stratum].label.lower()}; placing a dweller there holds it"
                if unfit_below(cell.stratum, entity.entity_type)
                else None,
            )
            for cell in cells
        ],
    )
