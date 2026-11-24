from collections import Counter
from collections.abc import Mapping
from types import MappingProxyType

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.demography import AGE_BANDS, AGE_ORDER, BEARING_BANDS, MINOR_BANDS
from aerona.catalog.reproduction import ROLE_WEIGHTS, SEX_SYSTEMS, SexSpec, sex_shares
from aerona.constants.units import PERCENT
from aerona.core.total import partial
from aerona.db.tables.collective import RoleNormRow
from aerona.db.tables.cycles import PeopleReproductionRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import RoleEligibility, RoleKind
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.demography import AgeBand, CohortCondition, SexKind
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.modifier import ModifierOp
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.interconnect.guards import AFTER_PHASE
from aerona.engine.primitives.kept import kept_rows
from aerona.engine.primitives.numbers import apportion, round_half_up
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.terms import explaining, term
from aerona.rules.registry import Rules

A = AgeBand
CohortKey = tuple[AgeBand, SexKind, SocialClass, CohortCondition]
FC = FlowCategory
AGE_PROFILES: Mapping[FlowCategory, Mapping[AgeBand, float]] = partial(
    FlowCategory,
    MappingProxyType(
        {
            FC.FAMINE: {A.INFANT: 3.0, A.CHILD: 2.0, A.YOUTH: 0.8, A.ELDER: 2.0, A.ADULT: 0.5, A.ANCIENT: 3.0},
            FC.CASUALTY: {A.YOUTH: 8.0, A.ADULT: 8.0, A.ELDER: 0.4},
            FC.LEVY: {A.YOUTH: 9.0, A.ADULT: 9.0, A.ELDER: 0.3},
            FC.PLAGUE: {A.INFANT: 2.5, A.CHILD: 1.5, A.YOUTH: 0.7, A.ELDER: 2.5, A.ADULT: 0.7, A.ANCIENT: 3.5},
            FC.DEATH: {A.INFANT: 2.0, A.ELDER: 3.0, A.ADULT: 0.7, A.YOUTH: 0.5, A.CHILD: 0.8, A.ANCIENT: 5.0},
            FC.BIRTH: {A.INFANT: 1.0},
            FC.GROWTH: {A.INFANT: 1.5, A.CHILD: 1.0, A.YOUTH: 1.0, A.ADULT: 1.0},
            FC.MIGRATION: {A.ADULT: 2.25, A.YOUTH: 2.0, A.CHILD: 0.8, A.INFANT: 0.5, A.ELDER: 0.3},
            FC.JOURNEY: {A.ADULT: 2.25, A.YOUTH: 2.0, A.CHILD: 0.5},
            FC.CAPTIVE: {A.ADULT: 2.0, A.CHILD: 1.0},
            FC.CONVERSION: {A.ADULT: 1.25, A.ELDER: 1.0},
        }
    ),
    without=(
        FlowCategory.DISASTER,
        FlowCategory.MERGE,
        FlowCategory.CREATION,
        FlowCategory.DIVINE,
        FlowCategory.PLAYER,
        FlowCategory.TRANSFORMATION,
        FlowCategory.UNSPECIFIED,
    ),
)
COMBAT_FLOWS = frozenset({FC.CASUALTY, FC.LEVY})
UNIFORM: Mapping[tuple[AgeBand, SexKind], float] = MappingProxyType({(age, sex): 1.0 for age in AgeBand for sex in SexKind})
PROFILES: Mapping[FlowCategory, Mapping[tuple[AgeBand, SexKind], float]] = MappingProxyType(
    {category: {(age, sex): weight for age, weight in ages.items() for sex in SexKind} for category, ages in AGE_PROFILES.items()}
)
FLOW_CONDITION: Mapping[FlowCategory, CohortCondition] = MappingProxyType({FC.CAPTIVE: CohortCondition.CAPTIVE})


async def cohort_rows(session: AsyncSession, community_id: int) -> list[CohortRow]:
    return await kept_rows(session, CohortRow, CohortRow.community_entity_id, community_id)


async def cohorts_of(session: AsyncSession, community_id: int) -> dict[CohortKey, CohortRow]:
    return {(row.age_band, row.sex_kind, row.social_class, row.condition): row for row in await cohort_rows(session, community_id)}


def total(rows: Mapping[CohortKey, CohortRow]) -> int:
    return sum(row.count for row in rows.values())


def pyramid(rules: Rules) -> dict[AgeBand, float]:
    table = rules.cohorts
    young, elder = table.child_pct / PERCENT, table.elder_pct / PERCENT
    shares = {band: spec.youth_share or 0.0 for band, spec in AGE_BANDS.items()}
    whole = sum(shares.values()) or 1.0
    ancient = min(elder, table.ancient_pct / PERCENT)
    return {
        **{band: young * share / whole for band, share in shares.items() if share},
        A.ELDER: elder - ancient,
        A.ANCIENT: ancient,
        A.ADULT: max(0.0, 1 - young - elder),
    }


def sexes(rules: Rules, spec: SexSpec = SEX_SYSTEMS[ReproductiveSystem.TWO_SEX]) -> dict[SexKind, float]:
    return sex_shares(spec, rules.cohorts.bearer_pct)


async def sex_spec(session: AsyncSession, community: EntityRow) -> SexSpec:
    folk = await people_of(session, community)
    row = await session.get(PeopleReproductionRow, folk.id) if folk is not None else None
    return SEX_SYSTEMS[row.system if row is not None else ReproductiveSystem.TWO_SEX]


async def combat_weights(session: AsyncSession, community: EntityRow) -> dict[SexKind, float]:
    folk = await people_of(session, community)
    holders = [community.id, *([folk.id] if folk is not None else [])]
    for holder in holders:
        norm = await session.get(RoleNormRow, (holder, RoleKind.COMBAT))
        if norm is not None:
            return dict(ROLE_WEIGHTS[norm.eligibility])
    return dict(ROLE_WEIGHTS[RoleEligibility.ANY])


def row_for(session: AsyncSession, rows: dict[CohortKey, CohortRow], community_id: int, key: CohortKey, epoch: int) -> CohortRow:
    row = rows.get(key)
    if row is None:
        age, sex, social_class, condition = key
        row = CohortRow(
            community_entity_id=community_id, age_band=age, sex_kind=sex, social_class=social_class, condition=condition, count=0, generation_epoch=epoch
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
    parts = apportion(amount, dict(ordered))
    for key, _score in ordered:
        part = parts.get(key, 0)
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
    kinds = sexes(rules, await sex_spec(session, community))
    for age, age_share in pyramid(rules).items():
        for sex, sex_share in kinds.items():
            for social_class, class_share in shares.items():
                count = round_half_up(population * age_share * sex_share * max(0.0, class_share) / weight)
                if count > 0:
                    with explaining():
                        term("cohorts.seed_population", population, source_node_id=community.id)
                        term(f"cohorts.age_share.{age.value}", age_share, ModifierOp.MULTIPLY)
                        term(f"cohorts.sex_share.{sex.value}", sex_share, ModifierOp.MULTIPLY)
                        term(f"society.class_share.{social_class.value}", class_share / weight, ModifierOp.MULTIPLY)
                        row_for(session, rows, community.id, (age, sex, social_class, CohortCondition.NONE), epoch).count += count
    await reconcile(session, rules, community, rows, epoch)
    return rows


def weights_for(
    rows: Mapping[CohortKey, CohortRow],
    category: FlowCategory,
    condition: CohortCondition | None = None,
    *,
    sick_weight: float = 1.0,
    combat: Mapping[SexKind, float] | None = None,
    bands: Mapping[AgeBand, float] | None = None,
) -> dict[CohortKey, float]:
    profile = PROFILES.get(category, UNIFORM)
    lean = sick_weight if category is FC.PLAGUE else 1.0
    lean_by_sex = combat if combat is not None and category in COMBAT_FLOWS else {}
    lean_by_band = bands or {}
    return {
        key: profile.get((key[0], key[1]), 0.0)
        * (lean if key[3] is CohortCondition.SICK else 1.0)
        * lean_by_sex.get(key[1], 1.0)
        * lean_by_band.get(key[0], 1.0)
        for key in rows
        if condition is None or key[3] is condition
    }


async def apply_flow(session: AsyncSession, rules: Rules, community: EntityRow, delta: int, *, category: FlowCategory, epoch: int) -> None:
    kept = bool(await cohorts_of(session, community.id))
    rows = await seed(session, rules, community, epoch)
    if not rows or not kept:
        return
    with explaining():
        term(f"flows.{category.value}", delta, source_node_id=community.id)
        await place_flow(session, rules, community, rows, delta, category=category, epoch=epoch)


async def place_flow(
    session: AsyncSession, rules: Rules, community: EntityRow, rows: dict[CohortKey, CohortRow], delta: int, *, category: FlowCategory, epoch: int
) -> None:
    combat = await combat_weights(session, community) if category in COMBAT_FLOWS else None
    if delta < 0:
        adults = sum(row.count for key, row in rows.items() if key[0] in BEARING_BANDS)
        place(
            rows,
            weights_for(rows, category, sick_weight=rules.epidemiology.sick_death_weight_pct / PERCENT, combat=combat, bands=band_leans(rules, category)),
            -delta,
            add=False,
        )
        if category in ORPHANING_FLOWS:
            orphan(session, community, rows, adults - sum(row.count for key, row in rows.items() if key[0] in BEARING_BANDS), adults, epoch=epoch)
        return
    shares = await class_shares(session, rules, community.id)
    condition = FLOW_CONDITION.get(category, CohortCondition.NONE)
    profile = PROFILES.get(category, UNIFORM)
    kinds = (await sex_spec(session, community)).sexes
    for age in AgeBand:
        for sex in kinds:
            for social_class, share in shares.items():
                if profile.get((age, sex), 0.0) > 0 and share > 0:
                    row_for(session, rows, community.id, (age, sex, social_class, condition), epoch)
    place(rows, {key: profile.get((key[0], key[1]), 0.0) * max(0.0, shares.get(key[2], 0.0)) for key in rows if key[3] is condition}, delta, add=True)


def band_leans(rules: Rules, category: FlowCategory) -> dict[AgeBand, float]:
    if category in COMBAT_FLOWS:
        return {A.YOUTH: rules.demography.youth_levy_pct / PERCENT}
    if category in INFANT_PERILS:
        return {A.INFANT: 1 + rules.demography.infant_mortality_pct / PERCENT}
    return {}


INFANT_PERILS = frozenset({FC.FAMINE, FC.PLAGUE, FC.DEATH})
ORPHANING_FLOWS = frozenset({FC.CASUALTY, FC.FAMINE, FC.PLAGUE, FC.DISASTER})
ORPHANS_KEY = "orphaned_this_epoch"


def orphan(session: AsyncSession, community: EntityRow, rows: dict[CohortKey, CohortRow], lost: int, adults: int, *, epoch: int) -> int:
    if lost <= 0 or adults <= 0:
        return 0
    moved = 0
    for key in sorted((key for key in rows if key[0] in MINOR_BANDS and key[3] is CohortCondition.NONE), key=lambda key: tuple(part.value for part in key)):
        moving = min(rows[key].count, round_half_up(rows[key].count * lost / adults))
        if moving > 0:
            move_amount(rows[key], row_for(session, rows, community.id, (key[0], key[1], key[2], CohortCondition.ORPHANED), epoch), "count", moving)
            moved += moving
    found: dict[int, int] = session.info.setdefault(ORPHANS_KEY, {})
    found[community.id] = found.get(community.id, 0) + moved
    return moved


def displace(session: AsyncSession, community: EntityRow, rows: dict[CohortKey, CohortRow], count: int, epoch: int) -> int:
    free = sorted((key for key in rows if key[3] is CohortCondition.NONE and rows[key].count > 0), key=lambda key: -rows[key].count)
    moved = 0
    for key in free:
        if moved >= count:
            break
        moving = min(rows[key].count, count - moved)
        move_amount(rows[key], row_for(session, rows, community.id, (key[0], key[1], key[2], CohortCondition.DISPLACED), epoch), "count", moving)
        moved += moving
    return moved


def settle_displaced(session: AsyncSession, community: EntityRow, rows: dict[CohortKey, CohortRow], share_pct: int, epoch: int) -> int:
    settled = 0
    for key in sorted((key for key in rows if key[3] is CohortCondition.DISPLACED), key=lambda key: tuple(part.value for part in key)):
        moving = round_half_up(rows[key].count * share_pct / PERCENT)
        if moving > 0:
            move_amount(rows[key], row_for(session, rows, community.id, (key[0], key[1], key[2], CohortCondition.NONE), epoch), "count", moving)
            settled += moving
    return settled


async def reconcile(session: AsyncSession, rules: Rules, community: EntityRow, rows: dict[CohortKey, CohortRow], epoch: int) -> int:
    population = stat(community, "population") or 0
    gap = population - total(rows)
    with explaining():
        term("cohorts.population_gap", gap, source_node_id=community.id)
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
        if community is None or community.entity_type not in SOCIETY_TYPES or held(node_id):
            continue
        await apply_flow(ctx.session, ctx.rules, community, delta, category=FlowCategory(category), epoch=ctx.epoch)
    moved.clear()


AFTER_PHASE.append(settle_moved)


def band_years(band: AgeBand, spans: tuple[int, int]) -> float:
    maturity, adult_span = spans
    share = AGE_BANDS[band].youth_share
    return max(1.0, maturity * share) if share is not None else max(1.0, adult_span)


def age_cohorts(session: AsyncSession, community: EntityRow, rows: dict[CohortKey, CohortRow], spans: tuple[int, int], epoch: int) -> None:
    maturity, adult_span = spans
    moves: list[tuple[CohortKey, CohortKey, int]] = []
    for key, row in sorted(rows.items(), key=lambda item: tuple(part.value for part in item[0])):
        band, sex, social_class, condition = key
        if row.count <= 0 or band is AGE_ORDER[-1]:
            continue
        moving = round_half_up(row.count / band_years(band, spans))
        if moving > 0:
            older = AGE_ORDER[AGE_ORDER.index(band) + 1]
            grown = CohortCondition.NONE if condition is CohortCondition.ORPHANED and older not in MINOR_BANDS else condition
            moves.append((key, (older, sex, social_class, grown), moving))
    with explaining():
        term("cohorts.maturity_years", maturity, source_node_id=community.id)
        term("cohorts.adult_years", adult_span, source_node_id=community.id)
        for source, target, moving in moves:
            move_amount(rows[source], row_for(session, rows, community.id, target, epoch), "count", moving)


async def rebalance_classes(session: AsyncSession, rules: Rules, community: EntityRow, rows: dict[CohortKey, CohortRow], epoch: int) -> None:
    shares = await class_shares(session, rules, community.id)
    with explaining():
        for social_class, share in sorted(shares.items(), key=lambda item: item[0].value):
            term(f"society.class_share.{social_class.value}", share, ModifierOp.MULTIPLY, source_node_id=community.id)
        place_classes(session, community, rows, shares, epoch)


def place_classes(session: AsyncSession, community: EntityRow, rows: dict[CohortKey, CohortRow], shares: Mapping[SocialClass, float], epoch: int) -> None:
    present = {key[1] for key in rows}
    for band in AgeBand:
        for sex in sorted(present, key=lambda item: item.value):
            free = [key for key in rows if key[0] is band and key[1] is sex and key[3] is CohortCondition.NONE and key[2] is not SocialClass.SERF_OR_SLAVE]
            people = sum(rows[key].count for key in free)
            if people <= 0:
                continue
            for key in free:
                rows[key].count = 0
            classes = [social_class for social_class in shares if social_class is not SocialClass.SERF_OR_SLAVE]
            weights = {social_class: max(0.0, shares[social_class]) for social_class in classes}
            parts = apportion(people, weights if sum(weights.values()) > 0 else dict.fromkeys(classes, 1.0))
            placed = 0
            for social_class in classes:
                part = max(0, min(parts.get(social_class, 0), people - placed))
                row_for(session, rows, community.id, (band, sex, social_class, CohortCondition.NONE), epoch).count += part
                placed += part
