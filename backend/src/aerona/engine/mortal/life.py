import math
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.life_stages import LIFE_STAGES
from aerona.catalog.life_traits import LIFE_STAGE_TRAITS
from aerona.catalog.mind_split import INHERITED_SUMMARIES
from aerona.catalog.reproduction import SEX_KINDS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.body import BodyRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.life_traits import LifeStageTrait
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import MortalStats, revised
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickEnvironment
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat, stat_or
from aerona.engine.recording.scope import phase_moment
from aerona.rules.registry import Rules
from aerona.rules.registry.mortal_life import AgingRules

YOUNG_TRAITS = frozenset({LifeStageTrait.YOUNG, LifeStageTrait.UNDER_AGE})

SEXES = (SexKind.BEARER, SexKind.BEGETTER)
SEX_HASH = 2654435761
STAGE_ORDER = tuple(LifeStage)


@dataclass(frozen=True)
class StageBounds:
    infant: float
    child: float
    youth: float
    elder: float
    ancient: float
    mature: float


def stage_bounds(rules: Rules, biology: PeopleBiologyRow | None, lifespan: int) -> StageBounds:
    table = rules.aging
    span = max(1, lifespan)
    if biology is not None:
        youth = float(biology.maturity_years)
        elder = float(biology.maturity_years + biology.adult_years)
        ancient = max(elder + 1, float(biology.maturity_years + biology.adult_years + biology.elder_years))
        return StageBounds(
            youth * table.infant_end_pct / table.youth_end_pct,
            youth * table.child_end_pct / table.youth_end_pct,
            youth,
            elder,
            ancient,
            mature_from(table, youth, elder),
        )
    return StageBounds(
        span * table.infant_end_pct / PERCENT,
        span * table.child_end_pct / PERCENT,
        span * table.youth_end_pct / PERCENT,
        span * table.elder_start_pct / PERCENT,
        span * table.ancient_start_pct / PERCENT,
        mature_from(table, span * table.youth_end_pct / PERCENT, span * table.elder_start_pct / PERCENT),
    )


def mature_from(table: AgingRules, youth: float, elder: float) -> float:
    return youth + (elder - youth) * table.mature_end_pct / PERCENT


def stage_for(bounds: StageBounds, age: int) -> LifeStage:
    ladder = (
        (bounds.infant, LifeStage.INFANT),
        (bounds.child, LifeStage.CHILD),
        (bounds.youth, LifeStage.YOUTH),
        (bounds.mature, LifeStage.ADULT),
        (bounds.elder, LifeStage.MATURE),
        (bounds.ancient, LifeStage.ELDER),
    )
    return next((stage for bound, stage in ladder if age < bound), LifeStage.ANCIENT)


def sex_of_stats(mortal: EntityRow) -> SexKind:
    stats = mortal.stats
    if isinstance(stats, MortalStats) and stats.sex is not None:
        return SexKind(stats.sex)
    return SEXES[(mortal.id * SEX_HASH) % len(SEXES)]


def assign_sex(mortal: EntityRow, sex: SexKind | None = None) -> SexKind:
    chosen = sex or sex_of_stats(mortal)
    if isinstance(mortal.stats, MortalStats) and mortal.stats.sex != chosen.value:
        mortal.stats = revised(mortal.stats, {"sex": chosen.value})
    return chosen


def window_end_pct(rules: Rules, sex: SexKind) -> int:
    window = SEX_KINDS[sex].window
    return window(rules) if window is not None else 0


def folk_span(biology: PeopleBiologyRow | None, lifespan: int) -> int:
    if biology is None:
        return max(1, lifespan)
    return max(1, biology.maturity_years + biology.adult_years + biology.elder_years)


def folk_lifespan(biology: PeopleBiologyRow | None, base: int, roll: int, die: int) -> int:
    typical = base + (die + 1) / 2
    if biology is None:
        return base + roll
    return max(1, round_half_up((base + roll) * folk_span(biology, round_half_up(typical)) / typical))


def fertility_window(rules: Rules, biology: PeopleBiologyRow | None, sex: SexKind, lifespan: int) -> tuple[float, float]:
    span = folk_span(biology, lifespan)
    start = float(biology.maturity_years) if biology is not None else span * rules.fertility.window_start_pct / PERCENT
    end = span * window_end_pct(rules, sex) / PERCENT
    return start, max(start + 1, end)


def fertility_level(rules: Rules, biology: PeopleBiologyRow | None, sex: SexKind, *, age: int, lifespan: int, body: BodyRow | None) -> int:
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


CHILD_SUBTYPE = "child"


def adult(stage: LifeStage) -> bool:
    return LIFE_STAGES[stage].counts_as_adult


def young(stage: LifeStage) -> bool:
    return bool(LIFE_STAGE_TRAITS[stage] & YOUNG_TRAITS)


async def young_through(session: AsyncSession, rules: Rules, epoch: int, mortals: list[EntityRow], *, aged: bool) -> set[int]:
    years = rules.time.years_per_epoch
    start = epoch_start_year(epoch, years)
    found: set[int] = set()
    for mortal in mortals:
        age = stat(mortal, "age")
        if mortal.entity_type is not EntityType.MORTAL or age is None:
            continue
        born = (start + years if aged else start) - age
        bounds = stage_bounds(rules, await biology_of(session, mortal), stat_or(mortal, "lifespan", rules.world_effects.default_lifespan))
        if born + bounds.child > start:
            found.add(mortal.id)
    return found


def years_to_step(environment: TickEnvironment) -> int:
    years = environment.rules.time.years_per_epoch
    start = epoch_start_year(environment.epoch, years)
    aged = environment.aging is not None and environment.aging.done
    return (phase_moment(environment).year or start) - (start + years - 1 if aged else start)


async def stage_now(session: AsyncSession, rules: Rules, mortal: EntityRow) -> LifeStage:
    bounds = stage_bounds(rules, await biology_of(session, mortal), stat_or(mortal, "lifespan", rules.world_effects.default_lifespan))
    return stage_for(bounds, stat(mortal, "age") or 0)
