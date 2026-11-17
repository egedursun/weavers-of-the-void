from pydantic import Field

from aerona.domain.models.base import ValueObject


class YearWindow(ValueObject):
    start: int = Field(ge=0)
    end: int = Field(ge=0)


def epoch_start_year(epoch: int, years_per_epoch: int) -> int:
    return (max(1, epoch) - 1) * years_per_epoch


def epoch_end_year(epoch: int, years_per_epoch: int) -> int:
    return max(1, epoch) * years_per_epoch
