from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.body_plans import BUDDING_PLANS
from aerona.catalog.life.cycles import COUSINS_FOR_KINSHIP_DESCENTS, LINE_FOR_KINSHIP_DESCENTS, RESIDENCES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.collective import RoleNormRow
from aerona.db.tables.cycles import KinshipSystemRow, PeopleReproductionRow
from aerona.db.tables.demography import PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import RoleEligibility, RoleKind
from aerona.domain.enums.cycles import (
    AdoptionKind,
    DescentGroup,
    KinshipDescent,
    KinTermSystem,
    ReproductiveSystem,
    ResidenceRule,
)
from aerona.domain.enums.demography import InheritanceCustom, NaturalTrait, SexKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.unions import KinMatch, PartnerScope, UnionExchange
from aerona.engine.context import TickContext
from aerona.engine.cycles.sides import drawn_side
from aerona.engine.mind.book import stored_values
from aerona.engine.unions.axes import Spousing, fresh_custom
from aerona.rules.registry import Rules

MALE_LINES = frozenset({RoleEligibility.BEGETTERS_ONLY, RoleEligibility.BEGETTERS_PREFERRED})
BEARER_LINES = frozenset({RoleEligibility.BEARERS_ONLY, RoleEligibility.BEARERS_PREFERRED})


@dataclass
class SeedTally:
    kinship: int = 0
    reproduction: int = 0


@dataclass(frozen=True)
class Spread:
    means: dict[ValueAxis, float]
    spreads: dict[ValueAxis, float]

    def standing(self, values: dict[ValueAxis, int], axis: ValueAxis) -> int:
        spread = max(1.0, self.spreads.get(axis, 1.0))
        return round((values.get(axis, 0) - self.means.get(axis, 0.0)) * PERCENT / spread)


def spread_of(samples: list[dict[ValueAxis, int]]) -> Spread:
    means: dict[ValueAxis, float] = {}
    spreads: dict[ValueAxis, float] = {}
    for axis in ValueAxis:
        found = [values.get(axis, 0) for values in samples]
        mean = sum(found) / len(found) if found else 0.0
        means[axis] = mean
        spreads[axis] = (sum((value - mean) ** 2 for value in found) / len(found)) ** 0.5 if found else 1.0
    return Spread(means, spreads)


@dataclass(frozen=True)
class Reading:
    kin: int
    family: int
    hierarchy: int
    tradition: int
    wealth: int
    perseverance: int


def reading_of(spread: Spread, values: dict[ValueAxis, int]) -> Reading:
    return Reading(
        kin=spread.standing(values, ValueAxis.KINSHIP),
        family=spread.standing(values, ValueAxis.FAMILY),
        hierarchy=spread.standing(values, ValueAxis.HIERARCHY),
        tradition=spread.standing(values, ValueAxis.TRADITION),
        wealth=spread.standing(values, ValueAxis.WEALTH),
        perseverance=spread.standing(values, ValueAxis.PERSEVERANCE),
    )


def line_for(people_id: int) -> KinshipDescent:
    return SeededRandom.for_epoch(people_id, 0, "descent").pick(LINE_FOR_KINSHIP_DESCENTS)


def line_of_sex(first: SexKind, sex: SexKind) -> KinshipDescent:
    return KinshipDescent.THROUGH_FIRST_LINE if first is sex else KinshipDescent.THROUGH_SECOND_LINE


def named_line(culture: PeopleCultureRow | None, heirs: RoleEligibility | None, first: SexKind) -> KinshipDescent | None:
    if culture is not None and culture.inheritance is InheritanceCustom.THROUGH_SECOND_LINE:
        return KinshipDescent.THROUGH_SECOND_LINE
    if heirs in BEARER_LINES:
        return line_of_sex(first, SexKind.BEARER)
    if heirs in MALE_LINES:
        return line_of_sex(first, SexKind.BEGETTER)
    return None


def descent_for(
    culture: PeopleCultureRow | None, heirs: RoleEligibility | None, reading: Reading, rules: Rules, *, people_id: int, first: SexKind
) -> KinshipDescent:
    table = rules.kinship_systems
    named = named_line(culture, heirs, first)
    if named is not None:
        return named
    if reading.kin >= table.double_at:
        return KinshipDescent.DOUBLE
    if reading.kin >= table.unilineal_at:
        return line_for(people_id)
    if reading.family <= table.ambilineal_at:
        return KinshipDescent.AMBILINEAL
    return KinshipDescent.BILATERAL


def residence_for(descent: KinshipDescent, reading: Reading, rules: Rules, people_id: int) -> ResidenceRule:
    if descent is KinshipDescent.THROUGH_SECOND_LINE and reading.kin >= rules.kinship_systems.first_line_kin_at:
        return ResidenceRule.WITH_KIN_OF_THE_FIRST_LINE
    if descent in RESIDENCES:
        return RESIDENCES[descent]
    if descent is KinshipDescent.BILATERAL:
        return ResidenceRule.NEW_HOUSEHOLD
    return SeededRandom.for_epoch(people_id, 0, "residence").pick(
        [ResidenceRule.WITH_FIRST_FAMILY, ResidenceRule.WITH_SECOND_FAMILY, ResidenceRule.NEW_HOUSEHOLD]
    )


def group_for(reading: Reading, rules: Rules) -> DescentGroup:
    table = rules.kinship_systems
    if reading.kin >= table.moiety_at and reading.tradition >= table.moiety_at:
        return DescentGroup.MOIETY
    if reading.kin >= table.clan_at:
        return DescentGroup.CLAN
    if reading.hierarchy >= table.house_at:
        return DescentGroup.HOUSE
    return DescentGroup.LINEAGE


def cousins_for(reading: Reading, rules: Rules, descent: KinshipDescent) -> KinTermSystem:
    table = rules.kinship_systems
    unilineal = descent in COUSINS_FOR_KINSHIP_DESCENTS
    if reading.kin >= table.all_siblings_at:
        return KinTermSystem.GENERATIONAL
    if reading.kin >= table.parallel_siblings_at:
        return KinTermSystem.BIFURCATE_MERGING if unilineal else KinTermSystem.CROSS_PARALLEL
    if reading.kin <= table.descriptive_at:
        return KinTermSystem.DESCRIPTIVE
    return KinTermSystem.BIFURCATE_COLLATERAL if unilineal else KinTermSystem.LINEAL


def adoption_for(reading: Reading, rules: Rules) -> AdoptionKind:
    table = rules.kinship_systems
    if reading.hierarchy >= table.heir_adoption_at:
        return AdoptionKind.HEIR
    if reading.kin >= table.chosen_kin_at:
        return AdoptionKind.CHOSEN_KIN
    if reading.wealth >= table.sponsor_at:
        return AdoptionKind.SPONSOR
    return AdoptionKind.FOSTER


def match_for(endogamous: bool, group: DescentGroup, reading: Reading, rules: Rules) -> tuple[PartnerScope, KinMatch]:
    cross = KinMatch.CROSS_COUSIN if reading.kin >= rules.kinship_systems.cross_cousin_at else KinMatch.NONE
    if endogamous:
        return PartnerScope.NONE, cross
    if group is DescentGroup.MOIETY:
        return PartnerScope.MOIETY, KinMatch.NONE
    if group is DescentGroup.CLAN:
        return PartnerScope.LINE, KinMatch.NONE
    return PartnerScope.NONE, cross


def exchange_for(reading: Reading, rules: Rules) -> UnionExchange:
    table = rules.kinship_systems
    if reading.wealth >= table.payment_at:
        return UnionExchange.FROM_ONE_FAMILY if reading.hierarchy >= 0 else UnionExchange.TO_ONE_FAMILY
    if reading.perseverance >= table.payment_at:
        return UnionExchange.SERVICE
    return UnionExchange.NONE


def set_matching(union: UnionCustomRow, group: DescentGroup, reading: Reading, rules: Rules) -> None:
    exogamy, kin_match = match_for(union.endogamy is PartnerScope.PEOPLE, group, reading, rules)
    values = {"exogamy": exogamy, "kin_match": kin_match, "exchange": exchange_for(reading, rules), "exchange_value": rules.kinship_systems.payment_value}
    for field, value in values.items():
        if field not in union.locked:
            setattr(union, field, value)


async def heir_rule(ctx: TickContext, people_id: int) -> RoleEligibility | None:
    row = await ctx.session.get(RoleNormRow, (people_id, RoleKind.INHERITANCE))
    return row.eligibility if row is not None else None


async def seed_kinship(ctx: TickContext, people: EntityRow, spread: Spread) -> KinshipSystemRow:
    table = ctx.rules.kinship_systems
    culture = await ctx.session.get(PeopleCultureRow, people.id)
    reading = reading_of(spread, await stored_values(ctx.session, ValueHolder.CULTURE, people.id))
    first = drawn_side(people.id)
    descent = descent_for(culture, await heir_rule(ctx, people.id), reading, ctx.rules, people_id=people.id, first=first)
    group = group_for(reading, ctx.rules)
    row = KinshipSystemRow(
        people_entity_id=people.id,
        descent=descent,
        first_side=first,
        residence=residence_for(descent, reading, ctx.rules, people.id),
        descent_group=group,
        kin_terms=cousins_for(reading, ctx.rules, descent),
        adoption=adoption_for(reading, ctx.rules),
        sibling_union_first=reading.kin >= table.first_side_sibling_union_at,
        sibling_union_second=reading.family >= table.second_side_sibling_union_at,
        locked=[],
    )
    ctx.session.add(row)
    union = await ctx.session.get(UnionCustomRow, people.id)
    if union is None:
        union = fresh_custom(people.id, Spousing(), row, ctx.rules.kinship.union_payment)
        ctx.session.add(union)
    set_matching(union, group, reading, ctx.rules)
    return row


def system_for(biology: PeopleBiologyRow | None) -> ReproductiveSystem:
    if biology is None:
        return ReproductiveSystem.TWO_SEX
    if NaturalTrait.HIVE_MINDED.value in biology.traits:
        return ReproductiveSystem.CASTE
    if biology.body_plan in BUDDING_PLANS:
        return ReproductiveSystem.ASEXUAL
    return ReproductiveSystem.TWO_SEX


async def seed_reproduction(ctx: TickContext, people: EntityRow) -> PeopleReproductionRow:
    table = ctx.rules.reproduction_systems
    biology = await ctx.session.get(PeopleBiologyRow, people.id)
    row = PeopleReproductionRow(
        people_entity_id=people.id,
        system=system_for(biology),
        change_age=biology.maturity_years + biology.adult_years // 2 if biology is not None else table.change_age,
        breeder_pct=table.breeder_norm_pct,
        soldier_pct=table.soldier_norm_pct,
        worker_pct=max(0, PERCENT - table.breeder_norm_pct - table.soldier_norm_pct),
        locked=[],
    )
    ctx.session.add(row)
    return row


async def seed_peoples(ctx: TickContext, tally: SeedTally) -> None:
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    found = list(peoples)
    spread = spread_of([await stored_values(ctx.session, ValueHolder.CULTURE, people.id) for people in found])
    for people in found:
        if held(people.id):
            continue
        if await ctx.session.get(KinshipSystemRow, people.id) is None:
            await seed_kinship(ctx, people, spread)
            tally.kinship += 1
        if await ctx.session.get(PeopleReproductionRow, people.id) is None:
            await seed_reproduction(ctx, people)
            tally.reproduction += 1
    await ctx.session.flush()
