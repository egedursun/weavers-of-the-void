from collections import Counter
from collections.abc import Mapping
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.interconnect.guards import AFTER_PHASE
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

A = AgeBand
X = Sex
CohortKey = tuple[AgeBand, Sex, SocialClass, CohortCondition]
FC = FlowCategory
UNIFORM: Mapping[tuple[AgeBand, Sex], float] = MappingProxyType({(age, sex): 1.0 for age in AgeBand for sex in Sex})
PROFILES: Mapping[FlowCategory, Mapping[tuple[AgeBand, Sex], float]] = MappingProxyType(
    {
        FC.FAMINE: {
            (A.CHILD, X.FEMALE): 2.0,
            (A.CHILD, X.MALE): 2.0,
            (A.ELDER, X.FEMALE): 2.0,
            (A.ELDER, X.MALE): 2.0,
            (A.ADULT, X.FEMALE): 0.5,
            (A.ADULT, X.MALE): 0.5,
        },
        FC.CASUALTY: {(A.ADULT, X.MALE): 8.0, (A.ADULT, X.FEMALE): 0.6, (A.ELDER, X.MALE): 0.4},
        FC.LEVY: {(A.ADULT, X.MALE): 9.0, (A.ADULT, X.FEMALE): 0.6, (A.ELDER, X.MALE): 0.3},
        FC.PLAGUE: {
            (A.CHILD, X.FEMALE): 1.5,
            (A.CHILD, X.MALE): 1.5,
            (A.ELDER, X.FEMALE): 2.5,
            (A.ELDER, X.MALE): 2.5,
            (A.ADULT, X.FEMALE): 0.7,
            (A.ADULT, X.MALE): 0.7,
        },
        FC.DEATH: {
            (A.ELDER, X.FEMALE): 3.0,
            (A.ELDER, X.MALE): 3.0,
            (A.ADULT, X.FEMALE): 0.6,
            (A.ADULT, X.MALE): 0.8,
            (A.CHILD, X.FEMALE): 0.8,
            (A.CHILD, X.MALE): 0.8,
        },
        FC.BIRTH: {(A.CHILD, X.FEMALE): 1.0, (A.CHILD, X.MALE): 1.0},
        FC.GROWTH: {(A.CHILD, X.FEMALE): 1.5, (A.CHILD, X.MALE): 1.5, (A.ADULT, X.FEMALE): 1.0, (A.ADULT, X.MALE): 1.0},
        FC.MIGRATION: {
            (A.ADULT, X.FEMALE): 2.0,
            (A.ADULT, X.MALE): 2.5,
            (A.CHILD, X.FEMALE): 0.8,
            (A.CHILD, X.MALE): 0.8,
            (A.ELDER, X.FEMALE): 0.3,
            (A.ELDER, X.MALE): 0.3,
        },
        FC.JOURNEY: {(A.ADULT, X.FEMALE): 2.0, (A.ADULT, X.MALE): 2.5, (A.CHILD, X.FEMALE): 0.5, (A.CHILD, X.MALE): 0.5},
        FC.CAPTIVE: {(A.ADULT, X.FEMALE): 2.0, (A.ADULT, X.MALE): 2.0, (A.CHILD, X.FEMALE): 1.0, (A.CHILD, X.MALE): 1.0},
        FC.CONVERSION: {(A.ADULT, X.FEMALE): 1.5, (A.ADULT, X.MALE): 1.0, (A.ELDER, X.FEMALE): 1.0, (A.ELDER, X.MALE): 1.0},
    }
)
FLOW_CONDITION: Mapping[FlowCategory, CohortCondition] = MappingProxyType({FC.CAPTIVE: CohortCondition.CAPTIVE})


async def cohorts_of(session: AsyncSession, community_id: int) -> dict[CohortKey, CohortRow]:
    rows = await session.scalars(select(CohortRow).where(CohortRow.community_entity_id == community_id))
    return {(row.age_band, row.sex, row.social_class, row.condition): row for row in rows}


def total(rows: Mapping[CohortKey, CohortRow]) -> int:
    return sum(row.count for row in rows.values())


def pyramid(rules: Rules) -> dict[AgeBand, float]:
    table = rules.cohorts
    child, elder = table.child_pct / PERCENT, table.elder_pct / PERCENT
    return {A.CHILD: child, A.ELDER: elder, A.ADULT: max(0.0, 1 - child - elder)}


def sexes(rules: Rules) -> dict[Sex, float]:
    female = rules.cohorts.female_pct / PERCENT
    return {X.FEMALE: female, X.MALE: 1 - female}


def row_for(session: AsyncSession, rows: dict[CohortKey, CohortRow], community_id: int, key: CohortKey, epoch: int) -> CohortRow:
    row = rows.get(key)
    if row is None:
        age, sex, social_class, condition = key
        row = CohortRow(
            community_entity_id=community_id, age_band=age, sex=sex, social_class=social_class, condition=condition, count=0, generation_epoch=epoch
        )
        session.add(row)
        rows[key] = row
    return row


def place(rows: dict[CohortKey, CohortRow], weights: Mapping[CohortKey, float], amount: int, add: bool) -> int:
    if amount <= 0:
        return 0
    filled = any(rows[key].count > 0 for key in weights if key in rows)
    scored = {
        key: weight * (rows[key].count if not add or filled else 1.0)
        for key, weight in weights.items()
        if key in rows and (rows[key].count > 0 or (add and not filled))
    }
    mass = sum(scored.values())
    if mass <= 0:
        return 0
    done = 0
    ordered = sorted(scored.items(), key=lambda item: (-item[1], tuple(part.value for part in item[0])))
    for index, (key, score) in enumerate(ordered):
        part = amount - done if index == len(ordered) - 1 else round_half_up(amount * score / mass)
        if add:
            rows[key].count += max(0, part)
            done += max(0, part)
        else:
            taken = min(rows[key].count, max(0, part))
            rows[key].count -= taken
            done += taken
    if not add and done < amount:
        for key in sorted(rows, key=lambda item: -rows[item].count):
            taken = min(rows[key].count, amount - done)
            rows[key].count -= taken
            done += taken
            if done >= amount:
                break
    return done


async def seed(session: AsyncSession, rules: Rules, community: EntityRow, epoch: int) -> dict[CohortKey, CohortRow]:
    rows = await cohorts_of(session, community.id)
    population = stat(community, "population") or 0
    if rows or population <= 0:
        return rows
    shares = await class_shares(session, rules, community.id)
    weight = sum(max(0.0, value) for value in shares.values()) or 1.0
    for age, age_share in pyramid(rules).items():
        for sex, sex_share in sexes(rules).items():
            for social_class, class_share in shares.items():
                count = round_half_up(population * age_share * sex_share * max(0.0, class_share) / weight)
                if count > 0:
                    row_for(session, rows, community.id, (age, sex, social_class, CohortCondition.NONE), epoch).count += count
    await reconcile(session, rules, community, rows, epoch)
    return rows


def weights_for(rows: Mapping[CohortKey, CohortRow], category: FlowCategory, condition: CohortCondition | None = None) -> dict[CohortKey, float]:
    profile = PROFILES.get(category, UNIFORM)
    return {key: profile.get((key[0], key[1]), 0.0) for key in rows if condition is None or key[3] is condition}


async def apply_flow(session: AsyncSession, rules: Rules, community: EntityRow, delta: int, *, category: FlowCategory, epoch: int) -> None:
    rows = await seed(session, rules, community, epoch)
    if not rows:
        return
    if delta < 0:
        place(rows, weights_for(rows, category), -delta, add=False)
        return
    shares = await class_shares(session, rules, community.id)
    condition = FLOW_CONDITION.get(category, CohortCondition.NONE)
    profile = PROFILES.get(category, UNIFORM)
    for age in AgeBand:
        for sex in Sex:
            for social_class, share in shares.items():
                if profile.get((age, sex), 0.0) > 0 and share > 0:
                    row_for(session, rows, community.id, (age, sex, social_class, condition), epoch)
    place(rows, {key: profile.get((key[0], key[1]), 0.0) * max(0.0, shares.get(key[2], 0.0)) for key in rows if key[3] is condition}, delta, add=True)


async def reconcile(session: AsyncSession, rules: Rules, community: EntityRow, rows: dict[CohortKey, CohortRow], epoch: int) -> int:
    population = stat(community, "population") or 0
    gap = population - total(rows)
    if gap > 0:
        place(rows, {key: 1.0 for key in rows if key[3] is CohortCondition.NONE} or {key: 1.0 for key in rows}, gap, add=True)
    elif gap < 0:
        place(rows, {key: 1.0 for key in rows}, -gap, add=False)
    return gap


async def settle_moved(ctx: TickContext, moved: Counter[tuple[int, str]]) -> None:
    for (node_id, category), delta in sorted(moved.items()):
        if not delta:
            continue
        community = await ctx.session.get(EntityRow, node_id)
        if community is None or community.entity_type not in SOCIETY_TYPES:
            continue
        await apply_flow(ctx.session, ctx.rules, community, delta, category=FlowCategory(category), epoch=ctx.epoch)
    moved.clear()


AFTER_PHASE.append(settle_moved)


def counts(rows: Mapping[CohortKey, CohortRow]) -> dict[str, int]:
    found: Counter[str] = Counter()
    for (age, sex, social_class, condition), row in rows.items():
        found[f"age.{age.value}"] += row.count
        found[f"sex.{sex.value}"] += row.count
        found[f"class.{social_class.value}"] += row.count
        found[f"condition.{condition.value}"] += row.count
    return dict(found)


def age_cohorts(session: AsyncSession, community: EntityRow, rows: dict[CohortKey, CohortRow], spans: tuple[int, int], epoch: int) -> None:
    maturity, adult_span = spans
    moves: list[tuple[CohortKey, CohortKey, int]] = []
    for key, row in sorted(rows.items(), key=lambda item: tuple(part.value for part in item[0])):
        band, sex, social_class, condition = key
        if row.count <= 0 or band is A.ELDER:
            continue
        share = 1 / max(1, maturity) if band is A.CHILD else 1 / max(1, adult_span)
        moving = round_half_up(row.count * share)
        if moving > 0:
            moves.append((key, (A.ADULT if band is A.CHILD else A.ELDER, sex, social_class, condition), moving))
    for source, target, moving in moves:
        rows[source].count -= moving
        row_for(session, rows, community.id, target, epoch).count += moving


async def rebalance_classes(session: AsyncSession, rules: Rules, community: EntityRow, rows: dict[CohortKey, CohortRow], epoch: int) -> None:
    shares = await class_shares(session, rules, community.id)
    weight = sum(max(0.0, value) for value in shares.values()) or 1.0
    for band in AgeBand:
        for sex in Sex:
            free = [key for key in rows if key[0] is band and key[1] is sex and key[3] is CohortCondition.NONE and key[2] is not SocialClass.SERF_OR_SLAVE]
            people = sum(rows[key].count for key in free)
            if people <= 0:
                continue
            for key in free:
                rows[key].count = 0
            classes = [social_class for social_class in shares if social_class is not SocialClass.SERF_OR_SLAVE]
            free_weight = sum(max(0.0, shares[social_class]) for social_class in classes) or weight
            placed = 0
            for index, social_class in enumerate(classes):
                part = people - placed if index == len(classes) - 1 else round_half_up(people * max(0.0, shares[social_class]) / free_weight)
                part = max(0, min(part, people - placed))
                row_for(session, rows, community.id, (band, sex, social_class, CohortCondition.NONE), epoch).count += part
                placed += part
