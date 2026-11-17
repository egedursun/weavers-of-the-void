import math
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.life_stages import LIFE_STAGES
from aerona.catalog.mind_split import INHERITED_SUMMARIES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.body import BodyRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.demography import Sex
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat, stat_or
from aerona.rules.registry import Rules

SEXES = (Sex.FEMALE, Sex.MALE)
SEX_HASH = 2654435761
STAGE_ORDER = tuple(LifeStage)


@dataclass(frozen=True)
class StageBounds:
    infant: float
    child: float
    youth: float
    elder: float
    ancient: float


def stage_bounds(rules: Rules, biology: PeopleBiologyRow | None, lifespan: int) -> StageBounds:
    table = rules.aging
    span = max(1, lifespan)
    if biology is not None:
        youth = float(biology.maturity_years)
        elder = float(biology.maturity_years + biology.adult_years)
        ancient = max(elder + 1, float(biology.maturity_years + biology.adult_years + biology.elder_years))
        return StageBounds(youth * table.infant_end_pct / table.youth_end_pct, youth * table.child_end_pct / table.youth_end_pct, youth, elder, ancient)
    return StageBounds(
        span * table.infant_end_pct / PERCENT,
        span * table.child_end_pct / PERCENT,
        span * table.youth_end_pct / PERCENT,
        span * table.elder_start_pct / PERCENT,
        span * table.ancient_start_pct / PERCENT,
    )


def stage_for(bounds: StageBounds, age: int) -> LifeStage:
    if age < bounds.infant:
        return LifeStage.INFANT
    if age < bounds.child:
        return LifeStage.CHILD
    if age < bounds.youth:
        return LifeStage.YOUTH
    if age < bounds.elder:
        return LifeStage.ADULT
    if age < bounds.ancient:
        return LifeStage.ELDER
    return LifeStage.ANCIENT


def sex_of_stats(mortal: EntityRow) -> Sex:
    stats = mortal.stats
    if isinstance(stats, MortalStats) and stats.sex is not None:
        return Sex(stats.sex)
    return SEXES[(mortal.id * SEX_HASH) % len(SEXES)]


def assign_sex(mortal: EntityRow, sex: Sex | None = None) -> Sex:
    chosen = sex or sex_of_stats(mortal)
    if isinstance(mortal.stats, MortalStats) and mortal.stats.sex != chosen.value:
        mortal.stats = mortal.stats.model_copy(update={"sex": chosen.value})
    return chosen


def window_end_pct(rules: Rules, sex: Sex) -> int:
    table = rules.fertility
    return {Sex.FEMALE: table.female_window_end_pct, Sex.MALE: table.male_window_end_pct, Sex.OTHER: table.other_window_end_pct}[sex]


def fertility_window(rules: Rules, biology: PeopleBiologyRow | None, sex: Sex, lifespan: int) -> tuple[float, float]:
    span = max(1, lifespan)
    start = float(biology.maturity_years) if biology is not None else span * rules.fertility.window_start_pct / PERCENT
    end = span * window_end_pct(rules, sex) / PERCENT
    return start, max(start + 1, end)


def fertility_level(rules: Rules, biology: PeopleBiologyRow | None, sex: Sex, *, age: int, lifespan: int, body: BodyRow | None) -> int:
    start, end = fertility_window(rules, biology, sex, lifespan)
    if age < start or age >= end:
        return 0
    people = (biology.fertility_pct if biology is not None else PERCENT) / PERCENT
    capacity = (body.fertility if body is not None else PERCENT) / PERCENT
    return clamp_int(PERCENT * min(1.0, people) * capacity, 0, PERCENT)


def hazard_chance(rules: Rules, age: int, lifespan: int, health: int, medicine: bool) -> float:
    table = rules.aging
    span = max(1, lifespan)
    if age * PERCENT < span * table.hazard_start_pct:
        return 0.0
    base = table.hazard_base_pct * math.exp(table.hazard_steepness * (age / span - 1))
    frail = (PERCENT + (PERCENT - max(0, min(PERCENT, health)))) / PERCENT
    healed = table.hazard_medicine_pct / PERCENT if medicine else 1.0
    return max(0.0, min(float(PERCENT), base * frail * healed))


async def biology_of(session: AsyncSession, mortal: EntityRow) -> PeopleBiologyRow | None:
    people = await people_of(session, mortal)
    return await session.get(PeopleBiologyRow, people.id) if people is not None else None


def held(profile: MortalProfileRow, column: str) -> bool:
    return column in (profile.locked or [])


async def refresh_life(session: AsyncSession, rules: Rules, mortal: EntityRow, profile: MortalProfileRow) -> LifeStage:
    biology = await biology_of(session, mortal)
    lifespan = stat_or(mortal, "lifespan", rules.world_effects.default_lifespan)
    age = stat(mortal, "age") or 0
    stage = stage_for(stage_bounds(rules, biology, lifespan), age)
    if not held(profile, "life_stage"):
        profile.life_stage = stage
    if not held(profile, "fertility"):
        body = await session.get(BodyRow, mortal.id)
        profile.fertility = fertility_level(rules, biology, sex_of_stats(mortal), age=age, lifespan=lifespan, body=body)
    return profile.life_stage


def inherited_summaries(rules: Rules, first: EntityRow, second: EntityRow, rng: SeededRandom) -> dict[str, int]:
    deviation = rules.fertility.ability_deviation
    middle = PERCENT // 2
    return {
        name: clamp_int((stat_or(first, name, middle) + stat_or(second, name, middle)) / 2 + rng.integer(-deviation, deviation), 0, PERCENT)
        for name in INHERITED_SUMMARIES
    }


def stage_rank(stage: LifeStage) -> int:
    return STAGE_ORDER.index(stage)


def adult(stage: LifeStage) -> bool:
    return LIFE_STAGES[stage].counts_as_adult
