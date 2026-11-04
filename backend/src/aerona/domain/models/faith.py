from collections.abc import Mapping, Set
from typing import Any

from pydantic import Field

from aerona.domain.enums.faith import FuneralRite, TenetKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.models.base import ValueObject

Percent = int | None
DEED_FLOORS = ("renown", "honour", "faith", "violence", "infamy")


class StratumCriteria(ValueObject):
    priority: int = Field(default=50, ge=0, le=1000)
    no_god: bool = False
    needs_rite: bool = False
    score_at_least: Percent = Field(default=None, ge=PERCENT_MIN, le=PERCENT_MAX)
    score_below: Percent = Field(default=None, ge=PERCENT_MIN, le=PERCENT_MAX + 1)
    renown_at_least: Percent = Field(default=None, ge=PERCENT_MIN, le=PERCENT_MAX)
    honour_at_least: Percent = Field(default=None, ge=PERCENT_MIN, le=PERCENT_MAX)
    faith_at_least: Percent = Field(default=None, ge=PERCENT_MIN, le=PERCENT_MAX)
    violence_at_least: Percent = Field(default=None, ge=PERCENT_MIN, le=PERCENT_MAX)
    infamy_at_least: Percent = Field(default=None, ge=PERCENT_MIN, le=PERCENT_MAX)
    rites: tuple[FuneralRite, ...] = ()
    tenets_any: tuple[TenetKind, ...] = ()

    @classmethod
    def read(cls, raw: Mapping[str, Any] | None) -> "StratumCriteria":
        return cls.model_validate(dict(raw or {}))

    def stored(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_defaults=True)

    def matches(self, *, score: int, deeds: Mapping[str, int], has_god: bool, rite: FuneralRite, tenets: Set[TenetKind]) -> bool:
        checks = (
            self.no_god == (not has_god),
            not self.needs_rite or rite is not FuneralRite.NONE,
            not self.rites or rite in self.rites,
            not self.tenets_any or bool(set(self.tenets_any) & set(tenets)),
            self.score_at_least is None or score >= self.score_at_least,
            self.score_below is None or score < self.score_below,
            *(getattr(self, f"{deed}_at_least") is None or deeds.get(deed, 0) >= getattr(self, f"{deed}_at_least") for deed in DEED_FLOORS),
        )
        return all(checks)
