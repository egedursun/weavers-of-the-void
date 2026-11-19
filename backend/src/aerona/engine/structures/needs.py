from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.structures import BRANCH_LEVELS, STRUCTURES, WORKSHOP_STRUCTURES
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass
from aerona.domain.enums.settlement import TIER_ORDER, SizeTier
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.lore.research import lacks, techniques_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat, stat_or
from aerona.rules.registry import Rules

K = StructureKind
B = KnowledgeBranch


@dataclass
class SiteFacts:
    site: EntityRow
    town: SettlementProfileRow | None
    shares: dict[SocialClass, float]
    knowledge: KnowledgeMap
    at_war: bool
    patron: bool
    coastal: bool
    river: bool
    literacy: int
    capital: bool
    outbreak: bool
    present: Counter[StructureKind]
    workshops: set[StructureKind]
    barred: set[StructureKind]
    techniques: frozenset[Technique] = frozenset()
    harvest: int = PERCENT

    def tier(self) -> int:
        return TIER_ORDER.index(self.town.size_tier) if self.town is not None else 0

    def at_least(self, tier: SizeTier) -> bool:
        return self.tier() >= TIER_ORDER.index(tier)

    def value(self, key: str) -> int:
        return stat(self.site, key) or 0

    def knows(self, branch: KnowledgeBranch) -> bool:
        return self.knowledge.knows(self.site.id, branch)

    def has(self, kind: StructureKind) -> bool:
        return self.present[kind] > 0

    def civic(self, key: str) -> int:
        return int(getattr(self.town, key)) if self.town is not None else 0

    def reaches(self, kind: StructureKind) -> bool:
        branch = STRUCTURES[kind].branch
        return branch is not None and self.knowledge.level(self.site.id, branch) >= BRANCH_LEVELS.get(kind, 0)


Need = tuple[StructureKind, Callable[[Rules, SiteFacts], bool]]


def homeless_share(facts: SiteFacts) -> float:
    if facts.town is None:
        return 0.0
    return facts.town.homeless * PERCENT / max(1, facts.value("population"))


def share(facts: SiteFacts, social_class: SocialClass, rules: Rules) -> bool:
    return facts.shares.get(social_class, 0) * facts.value("population") / PERCENT >= rules.construction.need_class_people


NEEDS: tuple[Need, ...] = (
    (K.WALL, lambda rules, f: f.at_war),
    (K.HOSPITAL, lambda rules, f: f.outbreak and f.knows(B.MEDICINE)),
    (K.POWER_PLANT, lambda rules, f: f.reaches(K.POWER_PLANT)),
    (K.REFINERY, lambda rules, f: f.reaches(K.REFINERY) and f.at_least(SizeTier.TOWN)),
    (K.GRANARY, lambda rules, f: f.knows(B.AGRICULTURE)),
    (K.MARKET, lambda rules, f: share(f, SocialClass.MERCHANT, rules) or f.knows(B.TRADE)),
    (
        K.TEMPLE,
        lambda rules, f: (
            f.patron and f.value("piety") >= rules.deep_life.temple_min_piety and f.shares.get(SocialClass.PRIEST, 0) >= rules.deep_life.temple_min_priest_pct
        ),
    ),
    (K.SHRINE, lambda rules, f: f.patron and not f.has(K.TEMPLE)),
    (K.PALACE, lambda rules, f: f.capital),
    (K.FORT, lambda rules, f: f.at_war),
    (K.CITADEL, lambda rules, f: f.at_war and f.at_least(SizeTier.TOWN)),
    (
        K.WALL,
        lambda rules, f: (
            f.site.entity_type is EntityType.SETTLEMENT
            and stat_or(f.site, "defense", rules.deep_life.wall_default_defense) < rules.deep_life.wall_defense_threshold
        ),
    ),
    (K.LIBRARY, lambda rules, f: f.shares.get(SocialClass.SCRIBE, 0) >= rules.deep_life.library_min_scribe_pct or f.knows(B.WRITING)),
    (K.SCHOOL, lambda rules, f: f.knows(B.WRITING) and f.literacy < rules.construction.need_literacy),
    (
        K.PRINTING_HOUSE,
        lambda rules, f: f.knows(B.WRITING) and f.reaches(K.PRINTING_HOUSE) and f.at_least(SizeTier.TOWN) and f.literacy >= rules.construction.press_literacy,
    ),
    (K.QUARANTINE_HOUSE, lambda rules, f: f.outbreak and f.knows(B.MEDICINE) and f.reaches(K.QUARANTINE_HOUSE) and f.at_least(SizeTier.TOWN)),
    (K.ROAD, lambda rules, f: f.at_least(SizeTier.VILLAGE) and f.knows(B.ARCHITECTURE)),
    (K.COURT, lambda rules, f: f.civic("crime") >= rules.construction.need_crime),
    (K.PRISON, lambda rules, f: f.civic("crime") >= rules.construction.need_prison_crime),
    (K.WATCHTOWER, lambda rules, f: f.civic("crime") >= rules.construction.need_crime),
    (K.HARBOUR, lambda rules, f: f.coastal and f.knows(B.SEAFARING)),
    (K.MONASTERY, lambda rules, f: share(f, SocialClass.MONASTIC, rules)),
    (K.AQUEDUCT, lambda rules, f: f.at_least(SizeTier.TOWN) and f.civic("sanitation") < rules.construction.need_sanitation and f.knows(B.ARCHITECTURE)),
    (K.SEWER, lambda rules, f: f.at_least(SizeTier.TOWN) and f.civic("sanitation") < rules.construction.need_sanitation and f.has(K.AQUEDUCT)),
    (K.GATE, lambda rules, f: f.has(K.WALL)),
    (K.TOWER, lambda rules, f: f.has(K.WALL)),
    (K.WAREHOUSE, lambda rules, f: f.has(K.MARKET)),
    (K.CARAVANSERAI, lambda rules, f: f.has(K.MARKET) and share(f, SocialClass.MERCHANT, rules)),
    (K.OBSERVATORY, lambda rules, f: f.knows(B.ASTRONOMY)),
    (K.HOSPITAL, lambda rules, f: f.knows(B.MEDICINE) and f.at_least(SizeTier.TOWN)),
    (K.IRRIGATION, lambda rules, f: f.knows(B.AGRICULTURE) and f.river),
    (K.BRIDGE, lambda rules, f: f.river and f.knows(B.ARCHITECTURE)),
    (K.ARENA, lambda rules, f: f.at_least(SizeTier.TOWN) and f.civic("unrest") >= rules.construction.need_unrest),
    (K.THEATRE, lambda rules, f: f.at_least(SizeTier.TOWN) and f.civic("prestige") < f.civic("unrest")),
    (K.BANK, lambda rules, f: f.at_least(SizeTier.TOWN) and f.value("wealth") >= rules.construction.need_wealth_bank and f.knows(B.TRADE)),
    (K.ACADEMY, lambda rules, f: f.has(K.LIBRARY) and f.has(K.SCHOOL)),
    (K.NECROPOLIS, lambda rules, f: f.at_least(SizeTier.TOWN) and f.has(K.TEMPLE)),
    (K.CANAL, lambda rules, f: f.river and f.knows(B.TRADE) and f.knows(B.ARCHITECTURE)),
    (K.DAM, lambda rules, f: f.river and f.has(K.IRRIGATION)),
    (K.MONUMENT, lambda rules, f: f.value("prosperity") >= rules.construction.need_prosperity_monument),
    (K.TOMB, lambda rules, f: f.patron and f.value("piety") >= rules.deep_life.temple_min_piety),
    (K.WONDER, lambda rules, f: f.at_least(SizeTier.CITY) and f.value("prosperity") >= rules.construction.need_prosperity_wonder),
    (K.FIREHOUSE, lambda rules, f: f.at_least(SizeTier.TOWN) and f.knows(B.ARCHITECTURE)),
    (K.BATHHOUSE, lambda rules, f: f.at_least(SizeTier.TOWN) and f.civic("sanitation") < rules.construction.need_sanitation),
    (K.FOUNTAIN, lambda rules, f: f.has(K.AQUEDUCT) or f.value("prosperity") >= rules.city_plan.gardens_prosperity),
    (K.PARK, lambda rules, f: f.at_least(SizeTier.TOWN) and f.value("prosperity") >= rules.city_plan.gardens_prosperity),
    (K.SLAUGHTERHOUSE, lambda rules, f: f.at_least(SizeTier.TOWN) and f.has(K.MARKET)),
    (K.ALMSHOUSE, lambda rules, f: homeless_share(f) >= rules.city_plan.almshouse_need_pct),
    (K.TAVERN, lambda rules, f: f.at_least(SizeTier.VILLAGE) and f.has(K.MARKET)),
    (K.TOWN_HALL, lambda rules, f: f.at_least(SizeTier.TOWN) and not f.capital),
    (K.GUILDHALL, lambda rules, f: f.at_least(SizeTier.TOWN) and share(f, SocialClass.ARTISAN, rules)),
    (K.BARRACKS, lambda rules, f: f.at_war and f.at_least(SizeTier.VILLAGE)),
    (K.ORPHANAGE, lambda rules, f: f.at_least(SizeTier.TOWN) and (f.outbreak or homeless_share(f) >= rules.city_plan.almshouse_need_pct)),
    (K.APOTHECARY, lambda rules, f: f.knows(B.MEDICINE) and not f.has(K.HOSPITAL)),
    (K.TRAINING_GROUND, lambda rules, f: f.at_least(SizeTier.TOWN) and share(f, SocialClass.WARRIOR, rules)),
    (K.MUSEUM, lambda rules, f: f.at_least(SizeTier.CITY) and f.literacy >= rules.construction.need_literacy),
    (K.PLAZA, lambda rules, f: f.at_least(SizeTier.TOWN) and f.has(K.MARKET)),
    (K.FACTORY, lambda rules, f: f.reaches(K.FACTORY) and f.at_least(SizeTier.TOWN) and share(f, SocialClass.WORKER, rules)),
    (K.DATA_CENTRE, lambda rules, f: f.reaches(K.DATA_CENTRE) and f.at_least(SizeTier.CITY)),
    (K.OFFICE_TOWER, lambda rules, f: f.reaches(K.OFFICE_TOWER) and f.at_least(SizeTier.CITY) and share(f, SocialClass.PROFESSIONAL, rules)),
    (K.APARTMENT_BLOCK, lambda rules, f: f.reaches(K.APARTMENT_BLOCK) and homeless_share(f) >= rules.city_plan.almshouse_need_pct),
    (K.MALL, lambda rules, f: f.reaches(K.MALL) and f.at_least(SizeTier.CITY) and f.value("prosperity") >= rules.construction.need_prosperity_monument),
    (K.BROADCAST_TOWER, lambda rules, f: f.reaches(K.BROADCAST_TOWER) and f.at_least(SizeTier.TOWN)),
    (K.SATELLITE_ARRAY, lambda rules, f: f.reaches(K.SATELLITE_ARRAY) and f.has(K.OBSERVATORY)),
    (K.MILITARY_BASE, lambda rules, f: f.reaches(K.MILITARY_BASE) and f.at_war and f.at_least(SizeTier.TOWN)),
    (K.MISSILE_SILO, lambda rules, f: f.reaches(K.MISSILE_SILO) and f.at_war and f.has(K.MILITARY_BASE)),
    (K.SHIELD_GENERATOR, lambda rules, f: f.reaches(K.SHIELD_GENERATOR) and f.at_war and f.at_least(SizeTier.CITY)),
    (K.TERRAFORMER, lambda rules, f: f.reaches(K.TERRAFORMER) and f.harvest < rules.construction.need_terraform_harvest),
    (K.VERTICAL_FARM, lambda rules, f: f.reaches(K.VERTICAL_FARM) and f.at_least(SizeTier.CITY)),
    (K.RECYCLING_PLANT, lambda rules, f: f.reaches(K.RECYCLING_PLANT) and f.civic("sanitation") < rules.construction.need_sanitation),
    (K.WATER_PURIFICATION, lambda rules, f: f.reaches(K.WATER_PURIFICATION) and f.civic("sanitation") < rules.construction.need_sanitation),
    (K.CLONING_FACILITY, lambda rules, f: f.reaches(K.CLONING_FACILITY) and f.has(K.HOSPITAL)),
    (K.ROBOTICS_WORKS, lambda rules, f: f.reaches(K.ROBOTICS_WORKS) and f.has(K.FACTORY)),
    (K.AI_CORE, lambda rules, f: f.reaches(K.AI_CORE) and f.has(K.DATA_CENTRE)),
    (K.TELEPORTER, lambda rules, f: f.reaches(K.TELEPORTER) and f.at_least(SizeTier.CITY)),
    *((kind, lambda rules, f, kind=kind: kind in f.workshops) for kind in sorted(set(WORKSHOP_STRUCTURES.values()), key=lambda item: item.value)),
)
KIND_TECHNIQUES = {
    K.POWER_PLANT: Technique.ELECTRICITY,
    K.REFINERY: Technique.COMBUSTION_ENGINE,
    K.FACTORY: Technique.FACTORY_PRODUCTION,
    K.DATA_CENTRE: Technique.COMPUTATION,
    K.OFFICE_TOWER: Technique.COMPUTATION,
    K.MALL: Technique.MASS_MEDIA,
    K.BROADCAST_TOWER: Technique.RADIO,
    K.SATELLITE_ARRAY: Technique.ROCKETRY,
    K.MILITARY_BASE: Technique.FIREARMS,
    K.MISSILE_SILO: Technique.ROCKETRY,
    K.VERTICAL_FARM: Technique.GREEN_REVOLUTION,
    K.RECYCLING_PLANT: Technique.INDUSTRIAL_CHEMISTRY,
    K.WATER_PURIFICATION: Technique.INDUSTRIAL_CHEMISTRY,
    K.CLONING_FACILITY: Technique.GENETIC_ENGINEERING,
    K.ROBOTICS_WORKS: Technique.ARTIFICIAL_MINDS,
    K.AI_CORE: Technique.ARTIFICIAL_MINDS,
}
TECHNIQUE_GATES = {K.AQUEDUCT: Technique.AQUEDUCT, K.SEWER: Technique.ARCH, K.CITADEL: Technique.FORTIFICATION, K.WONDER: Technique.DOME}
COUNTED_STATES = frozenset({ConstructionState.PLANNED, ConstructionState.BUILDING, ConstructionState.COMPLETE, ConstructionState.DAMAGED})


async def present_at(ctx: TickContext, host_id: int) -> Counter[StructureKind]:
    rows = await ctx.session.scalars(
        select(StructureProfileRow.kind).where(StructureProfileRow.host_entity_id == host_id, StructureProfileRow.construction_state.in_(list(COUNTED_STATES)))
    )
    return Counter(rows)


async def facts_for(ctx: TickContext, site: EntityRow, knowledge: KnowledgeMap, atlas: RegionAtlas) -> SiteFacts:
    session = ctx.session
    region_id = atlas.top_region(site.id)
    ground = await session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    people = await people_of(session, site)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    at_war = bool(await active_bonds(session, [BondKind.ENEMY], sources=[site.id]) or await active_bonds(session, [BondKind.ENEMY], targets=[site.id]))
    capital = await session.scalar(select(PolityProfileRow.polity_entity_id).where(PolityProfileRow.capital_entity_id == site.id).limit(1))
    outbreak = (
        region_id is not None
        and await session.scalar(select(OutbreakRow.id).where(OutbreakRow.region_entity_id == region_id, OutbreakRow.status != OutbreakStatus.ENDED).limit(1))
        is not None
    )
    workshops = {
        WORKSHOP_STRUCTURES[row.kind]
        for row in await session.scalars(select(WorkshopRow).where(WorkshopRow.community_entity_id == site.id, WorkshopRow.structure_entity_id.is_(None)))
        if row.kind in WORKSHOP_STRUCTURES
    }
    barred = {kind for kind, technique in TECHNIQUE_GATES.items() if await lacks(session, site.id, technique)}
    return SiteFacts(
        site=site,
        town=await session.get(SettlementProfileRow, site.id),
        shares=await class_shares(session, ctx.rules, site.id),
        knowledge=knowledge,
        at_war=at_war,
        patron=await living_patron(session, site) is not None,
        coastal=ground is not None and ground.coast_kind is not CoastKind.NONE,
        river=ground is not None and ground.river_class is not RiverClass.NONE,
        literacy=culture.literacy if culture is not None else 0,
        capital=capital is not None,
        outbreak=outbreak,
        present=await present_at(ctx, site.id),
        workshops=workshops,
        barred=barred,
        techniques=frozenset(await techniques_of(session, site.id)),
        harvest=ground.harvest_pct if ground is not None else PERCENT,
    )


def founding_order(kinds: list[StructureKind]) -> list[StructureKind]:
    return sorted((kind for kind in kinds if kind in KIND_TECHNIQUES), key=lambda kind: -BRANCH_LEVELS.get(kind, 0))


def wanted(rules: Rules, facts: SiteFacts) -> list[StructureKind]:
    found: list[StructureKind] = []
    for kind, test in NEEDS:
        if kind in found or facts.has(kind) or kind in facts.barred or (kind in KIND_TECHNIQUES and KIND_TECHNIQUES[kind] not in facts.techniques):
            continue
        if test(rules, facts):
            found.append(kind)
    return found
