from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.strata import STRATA
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.geology import RegionStratumRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.geology import UndergroundStratum

DWELLERS = COMMUNITY_TYPES | {EntityType.MORTAL}


async def cell_at(session: AsyncSession, region_id: int, stratum: UndergroundStratum) -> RegionStratumRow | None:
    return await session.scalar(
        select(RegionStratumRow).where(RegionStratumRow.region_entity_id == region_id, RegionStratumRow.stratum == stratum).order_by(RegionStratumRow.id)
    )


def unfit_below(stratum: UndergroundStratum | None, entity_type: EntityType) -> bool:
    return stratum is not None and entity_type in DWELLERS and not STRATA[stratum].dwellable


async def level_fault(
    session: AsyncSession, location: EntityRow | None, stratum: UndergroundStratum | None, entity_type: EntityType, *, dwelling: bool = True
) -> str | None:
    if stratum is None:
        return None
    label = STRATA[stratum].label.lower()
    if location is None or location.entity_type is not EntityType.REGION:
        return f"a level beneath the land names the {label} of a region, so the place must be a region"
    if await cell_at(session, location.id, stratum) is None:
        return f"no {label} lies beneath {location.name}"
    if dwelling and unfit_below(stratum, entity_type):
        return f"no one can dwell in the {label} beneath {location.name}"
    return None
