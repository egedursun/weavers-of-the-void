from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.disease import (
    DiseaseCureRow,
    DiseaseProfileRow,
    EndemicDiseaseRow,
    ImmunityRow,
    OutbreakRow,
    QuarantineRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

HOSPITAL = "hospital"
COLONY = "colony of the sick"


async def hospital_regions(session: AsyncSession, atlas: RegionAtlas) -> dict[int, list[EntityRow]]:
    hospitals: dict[int, list[EntityRow]] = defaultdict(list)
    structures = await session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.STRUCTURE, EntityRow.status == EntityStatus.CANON, EntityRow.subtype == HOSPITAL)
    )
    for structure in structures:
        region = atlas.top_region(structure.id)
        if region is not None:
            hospitals[region].append(structure)
    return hospitals


@dataclass
class DiseaseBook:
    rules: Rules
    epoch: int
    atlas: RegionAtlas
    diseases: dict[int, EntityRow]
    profiles: dict[int, DiseaseProfileRow]
    outbreaks: list[OutbreakRow]
    immunity: dict[tuple[int, int], dict[AgeBand, ImmunityRow]]
    endemic: dict[int, list[EndemicDiseaseRow]]
    cures: set[tuple[int, int]]
    quarantines: dict[int, QuarantineRow]
    hospitals: dict[int, list[EntityRow]]
    bands: dict[int, dict[AgeBand, int]] = field(default_factory=dict)
    sanitation: dict[int, int] = field(default_factory=dict)
    inoculated: set[int] = field(default_factory=set)

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules, epoch: int) -> "DiseaseBook":
        atlas = await RegionAtlas.load(session)
        diseases = {
            row.id: row
            for row in await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.DISEASE, EntityRow.status == EntityStatus.CANON))
        }
        profiles = {row.disease_entity_id: row for row in await session.scalars(select(DiseaseProfileRow))}
        outbreaks = list(await session.scalars(select(OutbreakRow).where(OutbreakRow.status != OutbreakStatus.ENDED).order_by(OutbreakRow.id)))
        immunity: dict[tuple[int, int], dict[AgeBand, ImmunityRow]] = defaultdict(dict)
        for row in await session.scalars(select(ImmunityRow)):
            immunity[(row.community_entity_id, row.disease_entity_id)][row.age_band] = row
        endemic: dict[int, list[EndemicDiseaseRow]] = defaultdict(list)
        for endemic_row in await session.scalars(select(EndemicDiseaseRow).order_by(EndemicDiseaseRow.region_entity_id, EndemicDiseaseRow.disease_entity_id)):
            endemic[endemic_row.region_entity_id].append(endemic_row)
        cures = {(row.disease_entity_id, row.community_entity_id) for row in await session.scalars(select(DiseaseCureRow))}
        quarantines = {row.region_entity_id: row for row in await session.scalars(select(QuarantineRow).where(QuarantineRow.until_epoch >= epoch))}
        hospitals = await hospital_regions(session, atlas)
        book = cls(rules, epoch, atlas, diseases, profiles, outbreaks, immunity, endemic, cures, quarantines, hospitals)
        for cohort in await session.scalars(select(CohortRow)):
            book.bands.setdefault(cohort.community_entity_id, defaultdict(int))[cohort.age_band] += cohort.count
        weighted: dict[int, float] = defaultdict(float)
        totals: dict[int, int] = defaultdict(int)
        for profile, settlement in await session.execute(
            select(SettlementProfileRow, EntityRow).join(EntityRow, EntityRow.id == SettlementProfileRow.settlement_entity_id)
        ):
            region = atlas.top_region(settlement.id)
            people = stat(settlement, "population") or 0
            if region is not None and people > 0:
                weighted[region] += profile.sanitation * people
                totals[region] += people
        book.sanitation = {region: round_half_up(weighted[region] / totals[region]) for region in totals}
        book.inoculated = set(await session.scalars(select(HolderTechniqueRow.holder_entity_id).where(HolderTechniqueRow.technique == Technique.INOCULATION)))
        return book

    def outbreaks_in(self, region_id: int | None) -> list[OutbreakRow]:
        return [outbreak for outbreak in self.outbreaks if outbreak.region_entity_id == region_id]

    def active_of(self, disease_id: int, region_id: int | None) -> OutbreakRow | None:
        return next((item for item in self.outbreaks if item.disease_entity_id == disease_id and item.region_entity_id == region_id), None)

    def of_event(self, event_id: int) -> OutbreakRow | None:
        return next((item for item in self.outbreaks if item.event_entity_id == event_id), None)

    def quarantined(self, region_id: int | None) -> bool:
        return region_id is not None and region_id in self.quarantines

    def band_weights(self, community_id: int) -> dict[AgeBand, float]:
        counts = self.bands.get(community_id)
        total = sum(counts.values()) if counts else 0
        if not counts or total <= 0:
            table = self.rules.cohorts
            child, elder = table.child_pct / PERCENT, table.elder_pct / PERCENT
            return {AgeBand.CHILD: child, AgeBand.ELDER: elder, AgeBand.ADULT: max(0.0, 1 - child - elder)}
        return {band: counts.get(band, 0) / total for band in AgeBand}

    def immune_share(self, community_id: int, disease_id: int) -> float:
        rows = self.immunity.get((community_id, disease_id), {})
        weights = self.band_weights(community_id)
        return sum(weights[band] * (rows[band].immune_pct if band in rows else 0) / PERCENT for band in AgeBand)

    def met_before(self, community_id: int, disease_id: int) -> bool:
        if (community_id, disease_id) in self.immunity:
            return True
        region = self.atlas.top_region(community_id)
        return any(row.disease_entity_id == disease_id for row in self.endemic.get(region or -1, []))

    def cured(self, disease_id: int, community_id: int) -> bool:
        return (disease_id, community_id) in self.cures

    def endemic_load(self, region_id: int | None) -> int:
        return sum(row.load for row in self.endemic.get(region_id or -1, []))

    def herd_threshold(self, disease_id: int) -> float:
        profile = self.profiles.get(disease_id)
        floor = self.rules.epidemiology.herd_floor_pct / PERCENT
        if profile is None:
            return 1.0
        reproduction = 1 + 4 * profile.virulence / PERCENT
        return max(floor, 1 - 1 / reproduction)
