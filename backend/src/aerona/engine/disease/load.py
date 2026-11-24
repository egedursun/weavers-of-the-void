from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.disease import EndemicDiseaseRow, ImmunityRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.disease import OutbreakStatus
from aerona.engine.crafts.works import soap_relief
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules


def joined(loads: list[int]) -> int:
    spared = 1.0
    for load in loads:
        spared *= 1 - max(0, min(PERCENT, load)) / PERCENT
    return round_half_up(PERCENT * (1 - spared))


@dataclass(frozen=True)
class DiseaseLoads:
    atlas: RegionAtlas
    regions: dict[int, int]
    acute: dict[int, int] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "DiseaseLoads":
        atlas = await RegionAtlas.load(session)
        lasting: dict[int, list[int]] = {row.entity_id: [row.disease_load] for row in await session.scalars(select(RegionEnvironmentRow))}
        for row in await session.scalars(select(EndemicDiseaseRow)):
            lasting.setdefault(row.region_entity_id, []).append(row.load)
        acute: dict[int, list[int]] = {}
        for outbreak in await session.scalars(select(OutbreakRow).where(OutbreakRow.status != OutbreakStatus.ENDED)):
            acute.setdefault(outbreak.region_entity_id, []).append(outbreak.severity // 2)
        relief = await soap_relief(session, rules)
        regions: dict[int, int] = {}
        sudden: dict[int, int] = {}
        for region in sorted(set(lasting) | set(acute)):
            kept = joined(lasting.get(region, []))
            whole = joined([kept, *acute.get(region, [])])
            eased = relief.get(region, 0)
            regions[region] = max(0, whole - eased)
            if whole > kept:
                sudden[region] = min(regions[region], whole - kept)
        return cls(atlas, regions, sudden)

    def of_region(self, region_id: int | None) -> int:
        return self.regions.get(region_id, 0) if region_id is not None else 0

    def of(self, community: EntityRow) -> float:
        return self.of_region(self.atlas.top_region(community.id)) / PERCENT

    def lasting(self, community: EntityRow) -> float:
        region = self.atlas.top_region(community.id)
        return (self.of_region(region) - (self.acute.get(region, 0) if region is not None else 0)) / PERCENT


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
