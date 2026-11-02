from pydantic import Field

from aerona.domain.models.base import ValueObject


class YearWindow(ValueObject):
    start: int = Field(ge=0)
    end: int = Field(ge=0)


def epoch_start_year(epoch: int, years_per_epoch: int) -> int:
    return (max(1, epoch) - 1) * years_per_epoch


def epoch_end_year(epoch: int, years_per_epoch: int) -> int:
    return max(1, epoch) * years_per_epoch


def chronicle_year(*, epoch: int, years_per_epoch: int, window: YearWindow, last_year: int | None, roll: float, pace_divisor: int) -> int:
    base = epoch_start_year(epoch, years_per_epoch)
    span = max(1, window.end - window.start)
    proposed = base + window.start + int(roll * span / max(1, pace_divisor))
    floor = last_year if last_year is not None and last_year >= base else base
    return min(base + max(0, years_per_epoch - 1), max(floor, proposed))
