from collections import Counter
from collections.abc import Mapping
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.demography import LabourRow, PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.demography import AgeBand, CohortCondition, Job
from aerona.domain.enums.disease import DiseaseTarget
from aerona.domain.enums.environment import CoastKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.engine.body.customs import culture_of, people_of
from aerona.engine.context import TickContext
from aerona.engine.demography.biology import job_factors, profiles_of
from aerona.engine.demography.cohorts import cohorts_of, seed
from aerona.engine.disease.harm import community_targets, sick_levy, sick_work
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

C = SocialClass
J = Job
FED = 100
LEVY_BASE = 10
SEASON_SICK_PCT = 50
AGE_WORK: Mapping[AgeBand, float] = MappingProxyType({AgeBand.CHILD: 0.2, AgeBand.ADULT: 1.0, AgeBand.ELDER: 0.5})
CONDITION_WORK: Mapping[CohortCondition, float] = MappingProxyType(
    {CohortCondition.NONE: 1.0, CohortCondition.VETERAN: 0.9, CohortCondition.ENSLAVED: 1.0, CohortCondition.CAPTIVE: 0.8}
)
CLASS_JOBS: Mapping[SocialClass, Mapping[Job, float]] = MappingProxyType(
    {
        C.FARMER: {J.FARMING: 1.0},
        C.SERF_OR_SLAVE: {J.FARMING: 0.6, J.MINING: 0.3, J.BUILDING: 0.1},
        C.ARTISAN: {J.CRAFTING: 0.7, J.BUILDING: 0.2, J.MINING: 0.1},
        C.MERCHANT: {J.TRADE: 1.0},
        C.PRIEST: {J.CLERGY: 1.0},
        C.MONASTIC: {J.CLERGY: 0.5, J.SCHOLARSHIP: 0.3, J.FARMING: 0.2},
        C.SCRIBE: {J.SCHOLARSHIP: 1.0},
        C.NOBLE: {J.IDLE: 0.8, J.SOLDIERING: 0.2},
    }
)
FOOD_JOBS = (J.FARMING, J.HERDING, J.FISHING)
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


def price_pull(rules: Rules, plan: Counter[Job], *, goods: int | None, food: int | None) -> None:
    pull = rules.labour.price_pull_pct / PERCENT
    farmers = sum(plan[job] for job in FOOD_JOBS)
    if goods is not None and food is not None and farmers > 0 and goods < FED <= food:
        moved = round_half_up(farmers * pull * (1 - goods / FED) * min(1.0, (food - FED) / FED + 0.5))
        moved = min(moved, plan[J.FARMING])
        plan[J.FARMING] -= moved
        plan[J.CRAFTING] += moved
    elif food is not None and food < FED:
        moved = round_half_up(plan[J.CRAFTING] * pull * (1 - food / FED))
        plan[J.CRAFTING] -= moved
        plan[J.FARMING] += moved


def satisfaction_factor(rules: Rules, society: CommunitySocietyRow | None, social_class: SocialClass) -> float:
    if society is None:
        return 1.0
    swing = rules.labour.satisfaction_pct / PERCENT
    return 1 + swing * (society.satisfaction(social_class) - PERCENT / 2) / (PERCENT / 2)


def illness_factor(rules: Rules, disease_load: int, wet_cold: bool) -> float:
    lost = rules.epidemiology.minor_illness_pct / PERCENT * disease_load / PERCENT * (1.0 if wet_cold else SEASON_SICK_PCT / PERCENT)
    return max(0.0, 1 - lost)


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
    plan: Counter[Job] = Counter()
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
                plan[target] += round_half_up(workers)
                boost = (rules.labour.slave_output_pct / PERCENT if bound and target in BOUND_JOBS else 1.0) * kin.get(target, 1.0)
                output[target] = output.get(target, 0.0) + workers * mood * boost
    price_pull(
        rules, plan, goods=society.stock(Commodity.GOODS) if society is not None else None, food=society.stock(Commodity.FOOD) if society is not None else None
    )
    sick = illness_factor(rules, region.disease_load if region is not None else 0, wet_cold)
    found = {row.job: row for row in await ctx.session.scalars(select(LabourRow).where(LabourRow.community_entity_id == community.id))}
    for job in Job:
        workers = max(0, plan.get(job, 0))
        planned = output.get(job, 0.0)
        pct = clamp_int(PERCENT * sick * (planned / workers if workers and planned else 1.0), 0, 1000)
        labour = found.get(job)
        if labour is None:
            if workers <= 0:
                continue
            labour = LabourRow(community_entity_id=community.id, job=job, workers=0, output_pct=PERCENT, epoch=ctx.epoch)
            ctx.session.add(labour)
            found[job] = labour
        labour.workers = workers
        labour.output_pct = pct
        labour.epoch = ctx.epoch
    return found


async def labour_of(session: AsyncSession, community_id: int) -> dict[Job, LabourRow]:
    return {row.job: row for row in await session.scalars(select(LabourRow).where(LabourRow.community_entity_id == community_id))}


def effective(rows: Mapping[Job, LabourRow], *jobs: Job) -> int | None:
    if not rows:
        return None
    return sum(round_half_up(rows[job].workers * rows[job].output_pct / PERCENT) for job in jobs if job in rows)


async def mobilisation(session: AsyncSession, rules: Rules, community: EntityRow, *, harvest_share: float) -> float:
    table = rules.peoples
    people = await people_of(session, community)
    if people is None:
        return 1.0
    values = await culture_of(session, people.id)
    culture = await session.get(PeopleCultureRow, people.id)
    martial = 1 + values.get(ValueAxis.MARTIAL, 0) / PERCENT * table.levy_martial_pct / PERCENT
    cohesion = 1 + ((culture.cohesion if culture is not None else table.cohesion_base) - table.cohesion_base) / PERCENT * table.levy_cohesion_pct / PERCENT
    season = 1 - harvest_share * (1 - table.harvest_levy_pct / PERCENT)
    laws = await LawBook.load(session)
    share = laws.param(community.id, LawKind.LEVY_LAW, "share")
    drafted = laws.param(community.id, LawKind.CONSCRIPTION, "share")
    law = 1.0
    if share is not None:
        law *= 1 + (int(share) - LEVY_BASE) / LEVY_BASE * rules.legislation.levy_share_pct / PERCENT * laws.weight(community.id, LawKind.LEVY_LAW)
    if drafted is not None:
        law *= 1 + int(drafted) / PERCENT * laws.weight(community.id, LawKind.CONSCRIPTION)
    return max(0.1, martial * cohesion * season * law)


async def fighting_age(session: AsyncSession, community_id: int, rules: Rules | None = None) -> int | None:
    rows = await cohorts_of(session, community_id)
    if not rows:
        return None
    adults = [
        (condition, row.count) for (band, _sex, _social, condition), row in rows.items() if band is AgeBand.ADULT and condition is not CohortCondition.MAIMED
    ]
    fit = sum(count for condition, count in adults if condition is not CohortCondition.SICK)
    sick = sum(count for condition, count in adults if condition is CohortCondition.SICK)
    if rules is None or sick <= 0:
        return fit
    return fit + round_half_up(sick * sick_levy(rules, await community_targets(session, community_id)))
