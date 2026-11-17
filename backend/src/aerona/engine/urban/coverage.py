from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.urban import HOME_DISTRICT, NUISANCES, REACH_RULE, SERVICE_OF
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.urban import DistrictServiceRow, TurfRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.settlement import DistrictKind, WaterSupply
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import STANDING_STATES
from aerona.domain.enums.urban import Morphology, UrbanService
from aerona.engine.context import TickContext
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat_or
from aerona.engine.settlement.districts import density_pct
from aerona.engine.urban.layout import falloff
from aerona.engine.urban.morphology import grow_rings, modernise
from aerona.engine.urban.planning import plan_town
from aerona.rules.registry import Rules

WATER_OF = {WaterSupply.NONE: 0, WaterSupply.WELL: 50, WaterSupply.CISTERN: 70, WaterSupply.AQUEDUCT: PERCENT}


@dataclass
class UrbanState:
    coverage: dict[UrbanService, float] = field(default_factory=dict)
    homeless_share: float = 0.0
    morphology: Morphology = Morphology.ORGANIC
    turf: float = 0.0

    def covered(self, service: UrbanService) -> float:
        return self.coverage.get(service, 0.0)


@dataclass
class CoverageTally:
    placed: int = 0
    covered: int = 0
    ringed: int = 0
    modernised: int = 0


def reach_of(rules: Rules, morphology: Morphology) -> float:
    return int(getattr(rules.coverage, REACH_RULE[morphology])) / PERCENT


async def services_in(session: AsyncSession, settlement_id: int) -> list[tuple[EntityRow, StructureProfileRow]]:
    return list(await service_rows(session, settlement_id))


@memoized(EntityRow, NodeRow, StructureProfileRow)
async def service_rows(session: AsyncSession, settlement_id: int) -> tuple[tuple[EntityRow, StructureProfileRow], ...]:
    rows = await session.execute(
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(
            EntityRow.location_id == settlement_id,
            EntityRow.status == EntityStatus.CANON,
            StructureProfileRow.construction_state.in_(list(STANDING_STATES)),
        )
        .order_by(EntityRow.id)
    )
    return tuple((entity, profile) for entity, profile in rows.all())


def home_of(profile: StructureProfileRow, districts: list[DistrictRow]) -> DistrictRow | None:
    if not districts:
        return None
    wanted = HOME_DISTRICT.get(profile.kind)
    by_value = sorted(districts, key=lambda district: (district.land_value, district.id), reverse=profile.kind not in NUISANCES)
    return next((district for district in districts if district.kind is wanted), by_value[0])


def place(profile: StructureProfileRow, districts: list[DistrictRow]) -> bool:
    if profile.district_id is not None or "district_id" in profile.locked:
        return False
    home = home_of(profile, districts)
    if home is None:
        return False
    profile.district_id = home.id
    return True


def people_of_districts(rules: Rules, population: float, districts: list[DistrictRow]) -> dict[int, float]:
    weights = {district.id: district.level * density_pct(rules, district.kind) for district in districts}
    if not any(weights.values()):
        weights = {district.id: district.level for district in districts}
    total = sum(weights.values())
    return {district.id: population * weights[district.id] / max(1, total) for district in districts}


def served(rules: Rules, profile: StructureProfileRow) -> float:
    return profile.level * rules.coverage.serves_per_level * min(PERCENT, profile.staff_pct or PERCENT) / PERCENT


async def cover_town(ctx: TickContext, settlement: EntityRow, tally: CoverageTally) -> None:
    profile = await ctx.session.get(SettlementProfileRow, settlement.id)
    infrastructure = await ctx.session.get(SettlementInfrastructureRow, settlement.id)
    districts = list(await ctx.session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == settlement.id).order_by(DistrictRow.id)))
    if profile is None or not districts:
        return
    reach = reach_of(ctx.rules, profile.morphology)
    layout = await plan_town(ctx, settlement.id)
    civic = {district.id for district in districts if district.kind is DistrictKind.CIVIC_QUARTER}
    supply: dict[UrbanService, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for _, structure in await services_in(ctx.session, settlement.id):
        tally.placed += int(place(structure, districts))
        service = SERVICE_OF.get(structure.kind)
        if service is None:
            continue
        for district in districts:
            stretch = min(1.0, reach * ctx.rules.city_plan.civic_reach_pct / PERCENT) if structure.district_id in civic else reach
            apart = layout.apart(structure.district_id, district.id) if structure.district_id is not None else 1
            supply[service][district.id] += served(ctx.rules, structure) * falloff(stretch, apart)
    people = people_of_districts(ctx.rules, stat_or(settlement, "population", 0), districts)
    stored = {
        (row.district_id, row.service): row
        for row in await ctx.session.scalars(select(DistrictServiceRow).where(DistrictServiceRow.district_id.in_([d.id for d in districts])))
    }
    for district in districts:
        for service in UrbanService:
            share = supply[service][district.id] / max(1.0, people[district.id]) * PERCENT
            if service is UrbanService.WATER and infrastructure is not None:
                share = max(share, WATER_OF[infrastructure.water])
            row = stored.get((district.id, service))
            if row is None:
                row = DistrictServiceRow(district_id=district.id, service=service, coverage=0, locked=[])
                ctx.session.add(row)
            if "coverage" not in row.locked:
                row.coverage = clamp_int(round_half_up(share), 0, PERCENT)
            row.epoch = ctx.epoch
            tally.covered += 1
    await ctx.session.flush()


async def cover_towns(ctx: TickContext, tally: CoverageTally) -> None:
    knowledge = await KnowledgeMap.load(ctx.session)
    for settlement in await canon(ctx.session, [EntityType.SETTLEMENT]):
        if held(settlement.id):
            continue
        profile = await ctx.session.get(SettlementProfileRow, settlement.id)
        if profile is not None:
            tally.ringed += int(grow_rings(ctx.rules, profile, await ctx.session.get(SettlementInfrastructureRow, settlement.id)))
            homes = list(await ctx.session.scalars(select(DistrictRow.housing).where(DistrictRow.settlement_entity_id == settlement.id)))
            architecture = knowledge.level(settlement.id, KnowledgeBranch.ARCHITECTURE)
            metallurgy = knowledge.level(settlement.id, KnowledgeBranch.METALLURGY)
            tally.modernised += int(
                modernise(ctx.rules, profile, homes, architecture=architecture, metallurgy=metallurgy, population=stat_or(settlement, "population", 0))
            )
        await cover_town(ctx, settlement, tally)


@memoized(DistrictServiceRow)
async def district_services(session: AsyncSession, district_ids: tuple[int, ...]) -> tuple[DistrictServiceRow, ...]:
    return tuple(await session.scalars(select(DistrictServiceRow).where(DistrictServiceRow.district_id.in_(list(district_ids)))))


@memoized(TurfRow)
async def district_turf(session: AsyncSession, district_ids: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(row.strength for row in await session.scalars(select(TurfRow).where(TurfRow.district_id.in_(list(district_ids)))))


async def urban_state(
    session: AsyncSession, rules: Rules, settlement_id: int, profile: SettlementProfileRow, districts: list[DistrictRow], *, population: int
) -> UrbanState:
    state = UrbanState(morphology=profile.morphology, homeless_share=min(1.0, profile.homeless / max(1, population)))
    if not districts:
        return state
    weights = people_of_districts(rules, population, districts)
    total = max(1.0, sum(weights.values()))
    sums: dict[UrbanService, float] = defaultdict(float)
    for row in await district_services(session, tuple(weights)):
        sums[row.service] += row.coverage / PERCENT * weights[row.district_id] / total
    state.coverage = dict(sums)
    turf = list(await district_turf(session, tuple(weights)))
    state.turf = min(1.0, sum(turf) / PERCENT / len(districts)) if turf else 0.0
    return state
