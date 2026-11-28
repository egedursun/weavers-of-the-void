from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.disease import DiseaseProfileRow, EndemicDiseaseRow, ImmunityRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.disease import OutbreakStatus
from aerona.engine.crafts.works import soap_relief
from aerona.engine.demography.cohorts import pyramid
from aerona.engine.environment.profile import climate_disease
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules


def by_lineage(loads: list[tuple[int, int]], lineage: dict[int, int]) -> list[int]:
    strongest: dict[int, int] = {}
    for disease_id, load in loads:
        root = lineage.get(disease_id, disease_id)
        strongest[root] = max(strongest.get(root, 0), load)
    return [strongest[root] for root in sorted(strongest)]


def roots_of(parents: dict[int, int | None]) -> dict[int, int]:
    found: dict[int, int] = {}
    for disease_id in sorted(parents):
        seen: list[int] = []
        current = disease_id
        while current not in found and parents.get(current) is not None and current not in seen:
            seen.append(current)
            current = parents[current] or current
        root = found.get(current, current)
        for member in [*seen, disease_id]:
            found[member] = root
    return found


def joined(loads: list[int]) -> int:
    spared = 1.0
    for load in loads:
        spared *= 1 - max(0, min(PERCENT, load)) / PERCENT
    return round_half_up(PERCENT * (1 - spared))


NO_COMMUNITY = -1


def native_disease(rules: Rules, ground: RegionEnvironmentRow) -> int:
    return min(PERCENT, round_half_up(climate_disease(rules, temperature=ground.temperature, wetland=ground.wetland)))


@dataclass(frozen=True)
class DiseaseLoads:
    atlas: RegionAtlas
    grounds: dict[int, int]
    acute: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    endemic: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    relief: dict[int, int] = field(default_factory=dict)
    guarded: dict[tuple[int, int], float] = field(default_factory=dict)
    carried_loads: dict[int, int] = field(default_factory=dict)
    baseline: int = 0
    lineage: dict[int, int] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "DiseaseLoads":
        atlas = await RegionAtlas.load(session)
        ground_rows = list(await session.scalars(select(RegionEnvironmentRow)))
        grounds = {row.entity_id: row.disease_load for row in ground_rows}
        endemic: dict[int, list[tuple[int, int]]] = {}
        for row in await session.scalars(select(EndemicDiseaseRow)):
            endemic.setdefault(row.region_entity_id, []).append((row.disease_entity_id, row.load))
        acute: dict[int, list[tuple[int, int]]] = {}
        for outbreak in await session.scalars(select(OutbreakRow).where(OutbreakRow.status != OutbreakStatus.ENDED, OutbreakRow.event_entity_id.is_(None))):
            acute.setdefault(outbreak.region_entity_id, []).append((outbreak.disease_entity_id, outbreak.severity // 2))
        parents = await session.execute(select(DiseaseProfileRow.disease_entity_id, DiseaseProfileRow.parent_disease_id))
        lineage = roots_of({disease_id: parent for disease_id, parent in parents})
        weights = pyramid(rules)
        strength = rules.epidemiology.immunity_strength_pct / PERCENT
        guarded: dict[tuple[int, int], float] = {}
        for immunity in await session.scalars(select(ImmunityRow)):
            key = (immunity.community_entity_id, immunity.disease_entity_id)
            guarded[key] = guarded.get(key, 0.0) + weights.get(immunity.age_band, 0.0) * immunity.immune_pct / PERCENT * strength
        baseline = rules.demography.endemic_baseline
        carried = {row.entity_id: max(baseline, native_disease(rules, row)) for row in ground_rows}
        return cls(atlas, grounds, acute, endemic, await soap_relief(session, rules), guarded, carried, baseline, lineage)

    def exposed(self, community_id: int, region_id: int) -> list[tuple[int, int]]:
        return [
            (disease_id, round_half_up(load * max(0.0, 1 - self.guarded.get((community_id, disease_id), 0.0))))
            for disease_id, load in self.endemic.get(region_id, [])
        ]

    def kept(self, community_id: int, region_id: int) -> int:
        return joined([self.grounds.get(region_id, 0), *by_lineage(self.exposed(community_id, region_id), self.lineage)])

    def struck(self, community_id: int, region_id: int) -> int:
        loads = [*self.exposed(community_id, region_id), *self.acute.get(region_id, [])]
        return joined([self.grounds.get(region_id, 0), *by_lineage(loads, self.lineage)])

    def of_region(self, region_id: int | None) -> int:
        if region_id is None:
            return 0
        return max(0, self.struck(NO_COMMUNITY, region_id) - self.relief.get(region_id, 0))

    @property
    def regions(self) -> dict[int, int]:
        return {region_id: self.of_region(region_id) for region_id in sorted(set(self.grounds) | set(self.endemic) | set(self.acute))}

    def parts(self, community: EntityRow) -> tuple[int, int]:
        region = self.atlas.top_region(community.id)
        if region is None:
            return 0, 0
        kept = self.kept(community.id, region)
        whole = max(kept, self.struck(community.id, region))
        eased = max(0, whole - self.relief.get(region, 0))
        return eased, min(eased, max(0, whole - kept))

    def of(self, community: EntityRow) -> float:
        return self.parts(community)[0] / PERCENT

    def carried(self, community: EntityRow) -> float:
        region = self.atlas.top_region(community.id)
        return (self.carried_loads.get(region, self.baseline) if region is not None else self.baseline) / PERCENT

    def lasting(self, community: EntityRow) -> float:
        whole, sudden = self.parts(community)
        return (whole - sudden) / PERCENT


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
