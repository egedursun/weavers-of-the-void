from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.db.tables.demography import CohortRow, PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
from aerona.domain.enums.mortal import HarshnessScale
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import CohortKey, age_cohorts, row_for, seed, total
from aerona.engine.environment.years import world_years
from aerona.engine.primitives.harshness import harshness
from aerona.engine.primitives.numbers import apportion, round_half_up
from aerona.engine.primitives.society import class_shares
from aerona.engine.services.war import ongoing_wars
from aerona.rules.registry import Rules

A = AgeBand
DEATH_RATES = (A.CHILD, A.ADULT, A.ELDER)


@dataclass(frozen=True)
class Pressures:
    fertility: float
    hunger: float
    crowding: float
    disease: float
    stress: float
    mortality: float
    time: float = 1.0


@dataclass(frozen=True)
class VitalYear:
    births: int
    deaths: dict[AgeBand, int]


async def stress_of(ctx: TickContext, community: EntityRow) -> float:
    rules = ctx.rules
    war = 1.0 if await ongoing_wars(ctx.session, community.id) else 0.0
    profile = await ctx.session.get(SettlementProfileRow, community.id)
    unrest = (profile.unrest if profile is not None else 0) / PERCENT
    return max(war, min(1.0, unrest * rules.mobility.inequality_crime_pct / PERCENT))


def death_rate(rules: Rules, band: AgeBand) -> float:
    table = rules.demography
    return {A.CHILD: table.child_death_pct_per_year, A.ADULT: table.adult_death_pct_per_year, A.ELDER: table.elder_death_pct_per_year}[band] / PERCENT


def one_year(rules: Rules, rows: dict[CohortKey, CohortRow], biology: PeopleBiologyRow | None, pressures: Pressures) -> VitalYear:
    table = rules.demography
    fertility = (biology.fertility_pct if biology is not None else PERCENT) / PERCENT
    mothers = sum(row.count for key, row in rows.items() if key[0] is A.ADULT and key[1] is Sex.FEMALE and key[3] is not CohortCondition.SICK)
    birth_rate = table.birth_pct_per_year / PERCENT * fertility * pressures.fertility
    famine = pressures.hunger**2
    birth_rate *= max(0.0, 1 - famine * table.hunger_birth_pct / PERCENT) * max(0.0, 1 - pressures.stress * table.stress_birth_pct / PERCENT)
    extra = (
        1 + famine * table.hunger_death_pct / PERCENT * harshness(rules, HarshnessScale.FAMINE_DEATH) + pressures.crowding * table.crowding_death_pct / PERCENT
    )
    extra += pressures.disease * table.disease_death_pct / PERCENT * harshness(rules, HarshnessScale.DISEASE_DEATH)
    deaths = {}
    for band in DEATH_RATES:
        people = sum(row.count for key, row in rows.items() if key[0] is band)
        deaths[band] = round_half_up(people * min(1.0, death_rate(rules, band) * extra * pressures.mortality))
    return VitalYear(round_half_up(mothers * birth_rate), deaths)


def take(rows: dict[CohortKey, CohortRow], band: AgeBand, amount: int) -> int:
    keys = sorted((key for key in rows if key[0] is band and rows[key].count > 0), key=lambda key: (-rows[key].count, tuple(part.value for part in key)))
    parts = apportion(amount, {key: float(rows[key].count) for key in keys})
    done = 0
    for key in keys:
        taken = max(0, min(rows[key].count, parts.get(key, 0)))
        rows[key].count -= taken
        done += taken
    return done


async def give_births(ctx: TickContext, community: EntityRow, rows: dict[CohortKey, CohortRow], births: int) -> int:
    if births <= 0:
        return 0
    shares = await class_shares(ctx.session, ctx.rules, community.id)
    weight = sum(max(0.0, value) for value in shares.values()) or 1.0
    female = ctx.rules.cohorts.female_pct / PERCENT
    placed = 0
    slots = [
        (sex, social_class, max(0.0, share) / weight * (female if sex is Sex.FEMALE else 1 - female)) for sex in Sex for social_class, share in shares.items()
    ]
    slots = [slot for slot in slots if slot[2] > 0]
    counts = apportion(births, {(sex, social_class): part for sex, social_class, part in slots})
    for sex, social_class, _part in slots:
        count = max(0, min(counts.get((sex, social_class), 0), births - placed))
        row_for(ctx.session, rows, community.id, (A.CHILD, sex, social_class, CohortCondition.NONE), ctx.epoch).count += count
        placed += count
    return placed


async def demographic_step(ctx: TickContext, community: EntityRow, biology: PeopleBiologyRow | None, pressures: Pressures) -> int:
    rows = await seed(ctx.session, ctx.rules, community, ctx.epoch)
    if not rows:
        return 0
    before = total(rows)
    sampled = len(world_years(ctx.environment, community.world_id or 0, "births"))
    births = 0
    deaths = 0
    table = ctx.rules.peoples
    spans = (biology.maturity_years, biology.adult_years) if biology is not None else (table.maturity_years, table.adult_years)
    for _ in range(sampled):
        year = one_year(ctx.rules, rows, biology, pressures)
        births += await give_births(ctx, community, rows, year.births)
        deaths += sum(take(rows, band, amount) for band, amount in year.deaths.items())
        age_cohorts(ctx.session, community, rows, spans, ctx.epoch)
    remaining = round_half_up(ctx.rules.time.years_per_epoch * pressures.time) - sampled
    after = total(rows)
    if remaining > 0 and sampled > 0 and before > 0 and after > 0:
        yearly = (after / before) ** (1 / sampled)
        factor = yearly**remaining
        for row in rows.values():
            row.count = max(0, round_half_up(row.count * factor))
    return total(rows) - before
