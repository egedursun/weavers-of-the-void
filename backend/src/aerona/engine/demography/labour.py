from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.needs import GATED_JOBS, JOB_GOODS, MOVABLE_JOBS, WORKSHOP_JOBS
from aerona.constants.units import PERCENT
from aerona.core.total import partial
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.demography import LabourRow, PeopleCultureRow
from aerona.db.tables.economy import ResourceProfileRow, ResourceWorkerRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import CorveeRow, LabourReasonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.demography import AgeBand, CohortCondition, Job, Sex
from aerona.domain.enums.disease import DiseaseTarget
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import LabourReason
from aerona.engine.body.customs import culture_of, people_of
from aerona.engine.collective.demography import levy_factor
from aerona.engine.collective.roles import combat_sexes
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import solidarity
from aerona.engine.cycles.breeding import soldier_factor
from aerona.engine.demography.biology import job_factors, profiles_of
from aerona.engine.demography.cohorts import cohorts_of, seed
from aerona.engine.demography.prices import cheapest, dearest, local_prices
from aerona.engine.disease.harm import community_targets, sick_levy, sick_work
from aerona.engine.economy.extraction import KIND_JOBS, extraction_kind
from aerona.engine.polity.law_effects import feudal_levy
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

C = SocialClass
J = Job
LEVY_BASE = 10
SEASON_SICK_PCT = 50
AGE_WORK: Mapping[AgeBand, float] = MappingProxyType({AgeBand.CHILD: 0.2, AgeBand.ADULT: 1.0, AgeBand.ELDER: 0.5})
CONDITION_WORK: Mapping[CohortCondition, float] = MappingProxyType(
    {CohortCondition.NONE: 1.0, CohortCondition.VETERAN: 0.9, CohortCondition.ENSLAVED: 1.0, CohortCondition.CAPTIVE: 0.8}
)
CLASS_JOBS = partial(
    SocialClass,
    {
        C.FARMER: {J.FARMING: 1.0},
        C.SERF_OR_SLAVE: {J.FARMING: 0.6, J.MINING: 0.3, J.BUILDING: 0.1},
        C.ARTISAN: {J.CRAFTING: 0.7, J.BUILDING: 0.2, J.MINING: 0.1},
        C.MERCHANT: {J.TRADE: 1.0},
        C.PRIEST: {J.CLERGY: 1.0},
        C.MONASTIC: {J.CLERGY: 0.5, J.SCHOLARSHIP: 0.3, J.FARMING: 0.2},
        C.SCRIBE: {J.SCHOLARSHIP: 1.0},
        C.NOBLE: {J.IDLE: 0.8, J.SOLDIERING: 0.2},
    },
    without={SocialClass.OUTCAST, SocialClass.WARRIOR},
)
BOUND_JOBS = frozenset({J.FARMING, J.HERDING, J.MINING, J.BUILDING})


def condition_work(rules: Rules, condition: CohortCondition, job: Job, targets: frozenset[DiseaseTarget] = frozenset()) -> float:
    if condition is CohortCondition.SICK:
        return sick_work(rules, job, targets)
    if condition is CohortCondition.MAIMED:
        return max(0.0, 1 - rules.maimed.labour_loss_pct / PERCENT)
    return CONDITION_WORK[condition]


def jobs_for(rules: Rules, social_class: SocialClass) -> dict[Job, float]:
    table = rules.labour
    if social_class is C.WARRIOR:
        soldiers = table.soldier_pct / PERCENT
        return {J.SOLDIERING: soldiers, J.FARMING: 1 - soldiers}
    if social_class is C.OUTCAST:
        idle = table.idle_outcast_pct / PERCENT
        return {J.IDLE: idle, J.MINING: (1 - idle) / 2, J.BUILDING: (1 - idle) / 2}
    return dict(CLASS_JOBS[social_class])


def split_food(region: RegionEnvironmentRow | None) -> dict[Job, float]:
    if region is None:
        return {J.FARMING: 1.0}
    farmed, grazed = max(0, region.farmed), max(0, region.grazed)
    sea = 0.25 if region.coast_kind is not CoastKind.NONE else 0.0
    land = farmed + grazed
    if land <= 0:
        return {J.FISHING: 1.0} if sea else {J.FARMING: 1.0}
    rest = 1 - sea
    return {J.FARMING: rest * farmed / land, J.HERDING: rest * grazed / land, J.FISHING: sea}


def satisfaction_factor(rules: Rules, society: CommunitySocietyRow | None, social_class: SocialClass) -> float:
    if society is None:
        return 1.0
    swing = rules.labour.satisfaction_pct / PERCENT
    return 1 + swing * (society.satisfaction(social_class) - PERCENT / 2) / (PERCENT / 2)


def illness_factor(rules: Rules, disease_load: int, wet_cold: bool) -> float:
    lost = rules.epidemiology.minor_illness_pct / PERCENT * disease_load / PERCENT * (1.0 if wet_cold else SEASON_SICK_PCT / PERCENT)
    return max(0.0, 1 - lost)


@dataclass(frozen=True)
class Move:
    workers: int
    commodity: CommodityKind | None = None
    workshop: WorkshopKind | None = None
    price: int = PERCENT


@dataclass
class Plan:
    workers: Counter[Job] = field(default_factory=Counter)
    reasons: dict[tuple[Job, LabourReason], Move] = field(default_factory=dict)

    def move(
        self,
        source: Job,
        target: Job,
        count: int,
        reason: LabourReason,
        *,
        commodity: CommodityKind | None = None,
        workshop: WorkshopKind | None = None,
        price: int = PERCENT,
    ) -> int:
        moved = max(0, min(count, self.workers[source]))
        if moved <= 0 or source is target:
            return 0
        self.workers[source] -= moved
        self.workers[target] += moved
        self.note(source, reason, -moved, commodity=commodity, workshop=workshop, price=price)
        self.note(target, reason, moved, commodity=commodity, workshop=workshop, price=price)
        return moved

    def note(
        self, job: Job, reason: LabourReason, count: int, *, commodity: CommodityKind | None = None, workshop: WorkshopKind | None = None, price: int = PERCENT
    ) -> None:
        before = self.reasons.get((job, reason))
        total = count + (before.workers if before is not None else 0)
        kept_commodity = commodity or (before.commodity if before is not None else None)
        kept_workshop = workshop or (before.workshop if before is not None else None)
        self.reasons[(job, reason)] = Move(total, kept_commodity, kept_workshop, price)


@dataclass(frozen=True)
class Grounds:
    workshops: dict[WorkshopKind, int]
    resources: list[tuple[Job, CommodityKind]]
    coastal: bool


async def grounds_of(session: AsyncSession, community: EntityRow, region: RegionEnvironmentRow | None) -> Grounds:
    workshops = {
        row.kind: row.level for row in await session.scalars(select(WorkshopRow).where(WorkshopRow.community_entity_id == community.id)) if row.level > 0
    }
    owned = set(
        await session.scalars(
            select(BondRow.target_node_id).where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id == community.id)
        )
    )
    worked = set(await session.scalars(select(ResourceWorkerRow.resource_entity_id).where(ResourceWorkerRow.community_entity_id == community.id)))
    resources: list[tuple[Job, CommodityKind]] = []
    ids = sorted(owned | worked)
    if ids:
        statement = select(ResourceProfileRow).where(ResourceProfileRow.resource_entity_id.in_(ids)).order_by(ResourceProfileRow.resource_entity_id)
        for profile in await session.scalars(statement):
            if profile.revealed and profile.reserve > 0:
                resources.append((KIND_JOBS[extraction_kind(profile)], profile.commodity))
    return Grounds(workshops, resources, region is not None and region.coast_kind is not CoastKind.NONE)


def gate(plan: Plan, grounds: Grounds) -> None:
    for job, (fallback, structures) in GATED_JOBS.items():
        if plan.workers[job] <= 0:
            continue
        resourced = any(target is job for target, _ in grounds.resources)
        built = any(kind in grounds.workshops for kind in structures)
        if resourced or built or (job is J.FISHING and grounds.coastal):
            continue
        plan.move(job, fallback, plan.workers[job], LabourReason.NO_STRUCTURE)


def draw(rules: Rules, plan: Plan, grounds: Grounds) -> None:
    table = rules.labour
    for kind, level in sorted(grounds.workshops.items(), key=lambda item: item[0].value):
        plan.move(J.FARMING, WORKSHOP_JOBS[kind], level * table.workshop_workers_per_level, LabourReason.STRUCTURE, workshop=kind)
    for job, commodity in grounds.resources:
        plan.move(J.FARMING, job, table.resource_workers, LabourReason.RESOURCE, commodity=commodity)


def job_pull(prices: Mapping[CommodityKind, int], job: Job) -> int:
    goods = JOB_GOODS[job]
    if not goods:
        return 0
    return round_half_up(sum(prices.get(kind, PERCENT) for kind in goods) / len(goods)) - PERCENT


def price_pull(rules: Rules, plan: Plan, prices: Mapping[CommodityKind, int]) -> None:
    share = rules.labour.price_pull_pct / PERCENT
    pulls = {job: job_pull(prices, job) for job in sorted(MOVABLE_JOBS, key=lambda item: item.value)}
    gainers = {job: pull for job, pull in pulls.items() if pull > 0}
    whole = sum(gainers.values())
    if whole <= 0:
        return
    pool = [(job, round_half_up(plan.workers[job] * share * min(1.0, -pull / PERCENT))) for job, pull in pulls.items() if pull < 0 and plan.workers[job] > 0]
    for source, leaving in pool:
        low = cheapest(prices, JOB_GOODS[source])
        for target, pull in gainers.items():
            high = dearest(prices, JOB_GOODS[target])
            moved = plan.move(
                source, target, round_half_up(leaving * pull / whole), LabourReason.PRICE, commodity=high, price=prices.get(high, PERCENT) if high else PERCENT
            )
            if moved and low is not None:
                plan.reasons[(source, LabourReason.PRICE)] = replace(plan.reasons[(source, LabourReason.PRICE)], commodity=low, price=prices.get(low, PERCENT))


def corvee(plan: Plan, share_pct: int) -> int:
    if share_pct <= 0:
        return 0
    moved = 0
    for job in (J.FARMING, J.HERDING):
        moved += plan.move(job, J.BUILDING, round_half_up(plan.workers[job] * share_pct / PERCENT), LabourReason.CORVEE)
    return moved


def hold(plan: Plan, found: Mapping[Job, LabourRow]) -> None:
    held = {job for job, row in found.items() if row.held}
    for job in sorted(held, key=lambda item: item.value):
        gap = found[job].workers - plan.workers[job]
        if gap > 0:
            for source in sorted(MOVABLE_JOBS | {J.IDLE}, key=lambda item: (-plan.workers[item], item.value)):
                if source is job or source in held or gap <= 0:
                    continue
                gap -= plan.move(source, job, gap, LabourReason.HELD)
        elif gap < 0:
            plan.move(job, J.FARMING if job is not J.FARMING else J.IDLE, -gap, LabourReason.HELD)


async def corvee_unrest(ctx: TickContext, community: EntityRow, share_pct: int) -> None:
    if share_pct <= 0 or community.entity_type is not EntityType.SETTLEMENT:
        return
    profile = await ctx.session.get(SettlementProfileRow, community.id)
    if profile is None or "unrest" in profile.locked:
        return
    profile.unrest = clamp_int(profile.unrest + round_half_up(ctx.rules.labour.corvee_unrest * share_pct / PERCENT), 0, PERCENT)


async def save_reasons(ctx: TickContext, community: EntityRow, plan: Plan) -> None:
    statement = select(LabourReasonRow).where(LabourReasonRow.community_entity_id == community.id)
    found = {(row.job, row.reason): row for row in await ctx.session.scalars(statement)}
    for key, stale in found.items():
        if key not in plan.reasons:
            await ctx.session.delete(stale)
    for (job, reason), move in plan.reasons.items():
        row = found.get((job, reason))
        if row is None:
            row = LabourReasonRow(community_entity_id=community.id, job=job, reason=reason, workers=0, price_pct=PERCENT, epoch=ctx.epoch)
            ctx.session.add(row)
        row.workers = move.workers
        row.commodity = move.commodity
        row.workshop = move.workshop
        row.price_pct = max(0, move.price)
        row.epoch = ctx.epoch


async def allocate(
    ctx: TickContext, community: EntityRow, region: RegionEnvironmentRow | None, *, wet_cold: bool, targets: frozenset[DiseaseTarget] = frozenset()
) -> dict[Job, LabourRow]:
    rules = ctx.rules
    rows = await seed(ctx.session, rules, community, ctx.epoch)
    if not rows:
        rows = await cohorts_of(ctx.session, community.id)
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    biology, _ = await profiles_of(ctx.session, community)
    kin = job_factors(rules, biology)
    plan = Plan()
    output: dict[Job, float] = {}
    food = split_food(region)
    for (band, _sex, social_class, condition), row in rows.items():
        hands = row.count * AGE_WORK[band]
        bound = social_class is C.SERF_OR_SLAVE or condition in {CohortCondition.ENSLAVED, CohortCondition.CAPTIVE}
        mood = satisfaction_factor(rules, society, social_class)
        for job, share in jobs_for(rules, C.SERF_OR_SLAVE if bound else social_class).items():
            spread = food if job is J.FARMING else {job: 1.0}
            for target, part in spread.items():
                workers = hands * condition_work(rules, condition, target, targets) * share * part
                plan.workers[target] += round_half_up(workers)
                boost = (rules.labour.slave_output_pct / PERCENT if bound and target in BOUND_JOBS else 1.0) * kin.get(target, 1.0)
                output[target] = output.get(target, 0.0) + workers * mood * boost
    customary = dict(plan.workers)
    for job, count in sorted(plan.workers.items(), key=lambda item: item[0].value):
        if count:
            plan.note(job, LabourReason.CLASS, count)
    grounds = await grounds_of(ctx.session, community, region)
    gate(plan, grounds)
    draw(rules, plan, grounds)
    price_pull(rules, plan, await local_prices(ctx.session, rules, community.id, stat(community, "population") or 0))
    levy = await ctx.session.get(CorveeRow, community.id)
    share = levy.share_pct if levy is not None else 0
    corvee(plan, share)
    found = {row.job: row for row in await ctx.session.scalars(select(LabourRow).where(LabourRow.community_entity_id == community.id))}
    hold(plan, found)
    await corvee_unrest(ctx, community, share)
    sick = illness_factor(rules, region.disease_load if region is not None else 0, wet_cold)
    for job in Job:
        labour = found.get(job)
        workers = labour.workers if labour is not None and labour.held else max(0, plan.workers.get(job, 0))
        planned = output.get(job, 0.0)
        base = customary.get(job, 0)
        pct = clamp_int(PERCENT * sick * (planned / base if base and planned else 1.0), 0, 1000)
        if labour is None:
            if workers <= 0:
                continue
            labour = LabourRow(community_entity_id=community.id, job=job, workers=0, output_pct=PERCENT, epoch=ctx.epoch, held=False)
            ctx.session.add(labour)
            found[job] = labour
        labour.workers = workers
        labour.output_pct = pct
        labour.epoch = ctx.epoch
    await save_reasons(ctx, community, plan)
    return found


async def mobilisation(session: AsyncSession, rules: Rules, community: EntityRow, *, harvest_share: float) -> float:
    table = rules.peoples
    people = await people_of(session, community)
    if people is None:
        return 1.0
    values = await culture_of(session, people.id)
    culture = await session.get(PeopleCultureRow, people.id)
    martial = 1 + values.get(ValueAxis.MARTIAL, 0) / PERCENT * rules.levies.martial_pct / PERCENT
    cohesion = 1 + ((culture.cohesion if culture is not None else table.cohesion_base) - table.cohesion_base) / PERCENT * rules.levies.cohesion_pct / PERCENT
    season = 1 - harvest_share * (1 - rules.levies.harvest_pct / PERCENT)
    laws = await LawBook.load(session)
    share = laws.param(community.id, LawKind.LEVY_LAW, "share")
    drafted = laws.param(community.id, LawKind.CONSCRIPTION, "share")
    law = 1.0
    if share is not None:
        law *= 1 + (int(share) - LEVY_BASE) / LEVY_BASE * rules.legislation.levy_share_pct / PERCENT * laws.weight(community.id, LawKind.LEVY_LAW)
    if drafted is not None:
        law *= 1 + int(drafted) / PERCENT * laws.weight(community.id, LawKind.CONSCRIPTION)
    law *= feudal_levy(laws, community.id, rules)
    ageing = await levy_factor(session, rules, community.id)
    bond = await solidarity(session, community, rules.asabiyya.levy_weight) * await soldier_factor(session, rules, community)
    return max(0.1, martial * cohesion * season * law * ageing * bond)


async def fighting_age(session: AsyncSession, community_id: int, rules: Rules | None = None) -> int | None:
    rows = await cohorts_of(session, community_id)
    if not rows:
        return None
    community = await session.get(EntityRow, community_id)
    fighters = await combat_sexes(session, community) if community is not None else set(Sex)
    adults = [
        (condition, row.count)
        for (band, sex, _social, condition), row in rows.items()
        if band is AgeBand.ADULT and condition is not CohortCondition.MAIMED and sex in fighters
    ]
    fit = sum(count for condition, count in adults if condition is not CohortCondition.SICK)
    sick = sum(count for condition, count in adults if condition is CohortCondition.SICK)
    if rules is None or sick <= 0:
        return fit
    return fit + round_half_up(sick * sick_levy(rules, await community_targets(session, community_id)))
