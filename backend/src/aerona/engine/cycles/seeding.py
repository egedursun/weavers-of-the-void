from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.collective import RoleNormRow
from aerona.db.tables.cycles import KinshipSystemRow, PeopleReproductionRow
from aerona.db.tables.demography import PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.collective import RoleEligibility, RoleKind
from aerona.domain.enums.cycles import (
    CousinTerms,
    DescentGroup,
    KinshipDescent,
    MarriagePayment,
    MarriagePreference,
    ReproductiveSystem,
    ResidenceRule,
)
from aerona.domain.enums.demography import InheritanceCustom, NaturalTrait
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values
from aerona.rules.registry import Rules

MALE_LINES = frozenset({RoleEligibility.MALE_ONLY, RoleEligibility.MALE_PREFERRED})
FEMALE_LINES = frozenset({RoleEligibility.FEMALE_ONLY, RoleEligibility.FEMALE_PREFERRED})
RESIDENCES = {KinshipDescent.PATRILINEAL: ResidenceRule.PATRILOCAL, KinshipDescent.MATRILINEAL: ResidenceRule.MATRILOCAL}
BUDDING_PLANS = frozenset({BodyPlan.AMORPHOUS, BodyPlan.CONSTRUCT})


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
    return SeededRandom.for_epoch(people_id, 0, "descent").pick([KinshipDescent.PATRILINEAL, KinshipDescent.MATRILINEAL])


def descent_for(culture: PeopleCultureRow | None, heirs: RoleEligibility | None, reading: Reading, rules: Rules, people_id: int) -> KinshipDescent:
    table = rules.kinship_systems
    if (culture is not None and culture.inheritance is InheritanceCustom.MATRILINEAL) or heirs in FEMALE_LINES:
        return KinshipDescent.MATRILINEAL
    if heirs in MALE_LINES:
        return KinshipDescent.PATRILINEAL
    if reading.kin >= table.double_at:
        return KinshipDescent.DOUBLE
    if reading.kin >= table.unilineal_at:
        return line_for(people_id)
    if reading.family <= table.ambilineal_at:
        return KinshipDescent.AMBILINEAL
    return KinshipDescent.BILATERAL


def residence_for(descent: KinshipDescent, reading: Reading, rules: Rules, people_id: int) -> ResidenceRule:
    if descent is KinshipDescent.MATRILINEAL and reading.kin >= rules.kinship_systems.avunculocal_at:
        return ResidenceRule.AVUNCULOCAL
    if descent in RESIDENCES:
        return RESIDENCES[descent]
    if descent is KinshipDescent.BILATERAL:
        return ResidenceRule.NEOLOCAL
    return SeededRandom.for_epoch(people_id, 0, "residence").pick([ResidenceRule.PATRILOCAL, ResidenceRule.MATRILOCAL, ResidenceRule.NEOLOCAL])


def group_for(reading: Reading, rules: Rules) -> DescentGroup:
    table = rules.kinship_systems
    if reading.kin >= table.moiety_at and reading.tradition >= table.moiety_at:
        return DescentGroup.MOIETY
    if reading.kin >= table.clan_at:
        return DescentGroup.CLAN
    if reading.hierarchy >= table.house_at:
        return DescentGroup.HOUSE
    return DescentGroup.LINEAGE


def cousins_for(reading: Reading, rules: Rules) -> CousinTerms:
    table = rules.kinship_systems
    if reading.kin >= table.all_siblings_at:
        return CousinTerms.ALL_AS_SIBLINGS
    if reading.kin >= table.parallel_siblings_at:
        return CousinTerms.PARALLEL_AS_SIBLINGS
    return CousinTerms.DISTINCT


def preference_for(culture: PeopleCultureRow | None, group: DescentGroup, reading: Reading, rules: Rules) -> MarriagePreference:
    cross = reading.kin >= rules.kinship_systems.cross_cousin_at
    if culture is not None and culture.endogamous:
        return MarriagePreference.CROSS_COUSIN if cross else MarriagePreference.NONE
    if group is DescentGroup.MOIETY:
        return MarriagePreference.MOIETY_EXOGAMY
    if group is DescentGroup.CLAN:
        return MarriagePreference.CLAN_EXOGAMY
    return MarriagePreference.CROSS_COUSIN if cross else MarriagePreference.NONE


def payment_for(reading: Reading, rules: Rules) -> MarriagePayment:
    table = rules.kinship_systems
    if reading.wealth >= table.payment_at:
        return MarriagePayment.DOWRY if reading.hierarchy >= 0 else MarriagePayment.BRIDE_PRICE
    if reading.perseverance >= table.payment_at:
        return MarriagePayment.BRIDE_SERVICE
    return MarriagePayment.NONE


async def heir_rule(ctx: TickContext, people_id: int) -> RoleEligibility | None:
    row = await ctx.session.get(RoleNormRow, (people_id, RoleKind.INHERITANCE))
    return row.eligibility if row is not None else None


async def seed_kinship(ctx: TickContext, people: EntityRow, spread: Spread) -> KinshipSystemRow:
    table = ctx.rules.kinship_systems
    culture = await ctx.session.get(PeopleCultureRow, people.id)
    reading = reading_of(spread, await stored_values(ctx.session, ValueHolder.CULTURE, people.id))
    descent = descent_for(culture, await heir_rule(ctx, people.id), reading, ctx.rules, people.id)
    group = group_for(reading, ctx.rules)
    row = KinshipSystemRow(
        people_entity_id=people.id,
        descent=descent,
        residence=residence_for(descent, reading, ctx.rules, people.id),
        descent_group=group,
        cousin_terms=cousins_for(reading, ctx.rules),
        preference=preference_for(culture, group, reading, ctx.rules),
        payment=payment_for(reading, ctx.rules),
        payment_value=table.payment_value,
        levirate=reading.kin >= table.levirate_at,
        sororate=reading.family >= table.sororate_at,
        locked=[],
    )
    ctx.session.add(row)
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
