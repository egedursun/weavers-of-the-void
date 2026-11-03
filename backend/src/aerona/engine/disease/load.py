from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.disease import EndemicDiseaseRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.disease import OutbreakStatus
from aerona.engine.primitives.distance import RegionAtlas


@dataclass(frozen=True)
class DiseaseLoads:
    atlas: RegionAtlas
    regions: dict[int, int]

    @classmethod
    async def load(cls, session: AsyncSession) -> "DiseaseLoads":
        atlas = await RegionAtlas.load(session)
        regions = {row.entity_id: row.disease_load for row in await session.scalars(select(RegionEnvironmentRow))}
        for row in await session.scalars(select(EndemicDiseaseRow)):
            regions[row.region_entity_id] = regions.get(row.region_entity_id, 0) + row.load
        for outbreak in await session.scalars(select(OutbreakRow).where(OutbreakRow.status != OutbreakStatus.ENDED)):
            regions[outbreak.region_entity_id] = regions.get(outbreak.region_entity_id, 0) + outbreak.severity // 2
        return cls(atlas, {region: min(PERCENT, value) for region, value in regions.items()})

    def of_region(self, region_id: int | None) -> int:
        return self.regions.get(region_id, 0) if region_id is not None else 0

    def of(self, community: EntityRow) -> float:
        return self.of_region(self.atlas.top_region(community.id)) / PERCENT


async def endemic_regions(session: AsyncSession) -> set[int]:
    return set(await session.scalars(select(EndemicDiseaseRow.region_entity_id).where(EndemicDiseaseRow.load > 0)))
