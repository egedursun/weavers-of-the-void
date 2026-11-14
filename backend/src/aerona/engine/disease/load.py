from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.disease import EndemicDiseaseRow, ImmunityRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.disease import OutbreakStatus
from aerona.engine.crafts.works import soap_relief
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class DiseaseLoads:
    atlas: RegionAtlas
    regions: dict[int, int]

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "DiseaseLoads":
        atlas = await RegionAtlas.load(session)
        regions = {row.entity_id: row.disease_load for row in await session.scalars(select(RegionEnvironmentRow))}
        for row in await session.scalars(select(EndemicDiseaseRow)):
            regions[row.region_entity_id] = regions.get(row.region_entity_id, 0) + row.load
        for outbreak in await session.scalars(select(OutbreakRow).where(OutbreakRow.status != OutbreakStatus.ENDED)):
            regions[outbreak.region_entity_id] = regions.get(outbreak.region_entity_id, 0) + outbreak.severity // 2
        for region, relief in (await soap_relief(session, rules)).items():
            regions[region] = regions.get(region, 0) - relief
        return cls(atlas, {region: max(0, min(PERCENT, value)) for region, value in regions.items()})

    def of_region(self, region_id: int | None) -> int:
        return self.regions.get(region_id, 0) if region_id is not None else 0

    def of(self, community: EntityRow) -> float:
        return self.of_region(self.atlas.top_region(community.id)) / PERCENT


async def endemic_regions(session: AsyncSession) -> set[int]:
    return set(await session.scalars(select(EndemicDiseaseRow.region_entity_id).where(EndemicDiseaseRow.load > 0)))


async def endemic_repel(session: AsyncSession, rules: Rules, region_id: int, origin_id: int | None) -> float:
    met = (
        set(await session.scalars(select(ImmunityRow.disease_entity_id).where(ImmunityRow.community_entity_id == origin_id)))
        if origin_id is not None
        else set()
    )
    loads = await session.scalars(select(EndemicDiseaseRow).where(EndemicDiseaseRow.region_entity_id == region_id, EndemicDiseaseRow.load > 0))
    load = min(PERCENT, sum(row.load for row in loads if row.disease_entity_id not in met))
    return max(0.0, 1 - load / PERCENT * rules.epidemiology.endemic_settler_pct / PERCENT)
