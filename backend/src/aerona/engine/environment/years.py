from dataclasses import dataclass

from aerona.domain.models.calendar import epoch_start_year
from aerona.engine.context import TickEnvironment

SUB_STEPS_USED = "sub_steps.used"
SUB_STEPS_EXTRAPOLATED = "sub_steps.extrapolated"


@dataclass(frozen=True)
class SampledYear:
    offset: int
    year: int


def grant_sub_steps(environment: TickEnvironment, wanted: int) -> int:
    budget = environment.rules.engine_budget.max_sub_steps_per_epoch
    used = environment.stats.counters[SUB_STEPS_USED]
    granted = max(0, min(wanted, budget - used))
    environment.stats.count(SUB_STEPS_USED, granted)
    if granted < wanted:
        environment.stats.count(SUB_STEPS_EXTRAPOLATED, wanted - granted)
    return granted


def sampled_years(environment: TickEnvironment, world_id: int, count: int | None = None) -> list[SampledYear]:
    years = environment.rules.time.years_per_epoch
    wanted = min(years, count if count is not None else environment.rules.time.sampled_years)
    offsets = sorted(environment.rng(f"years.{world_id}").sample(list(range(years)), wanted))
    base = epoch_start_year(environment.epoch, years)
    return [SampledYear(offset, base + offset) for offset in offsets]


def world_years(environment: TickEnvironment, world_id: int, system: str) -> list[SampledYear]:
    years = sampled_years(environment, world_id)
    key = f"{system}.{world_id}"
    granted = environment.stats.grants.get(key)
    if granted is None:
        granted = max(1, grant_sub_steps(environment, len(years)))
        environment.stats.grants[key] = granted
    return years[:granted]


def season_of_year(year: SampledYear, count: int) -> int:
    return year.year % count if count > 0 else 0
