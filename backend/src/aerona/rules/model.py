from dataclasses import Field, dataclass, field, fields
from math import ceil
from typing import Any, ClassVar

Number = int | float
RULE_METADATA_KEY = "rule"
EPOCH_YEARS = 50
YEARS_UNIT = "years"
FULL_PROGRESS = 100


@dataclass(frozen=True)
class RuleMeta:
    default: Number
    minimum: Number
    maximum: Number
    group: str
    label: str
    unit: str = ""


def rule(default: Number, minimum: Number, maximum: Number, group: str, label: str) -> Any:
    return field(default=default, metadata={RULE_METADATA_KEY: RuleMeta(default, minimum, maximum, group, label)})


def span(default: int, minimum: int, maximum: int, group: str, label: str) -> Any:
    return field(default=default, metadata={RULE_METADATA_KEY: RuleMeta(default, minimum, maximum, group, label, YEARS_UNIT)})


def epochs_in(years: int, years_per_epoch: int) -> int:
    return ceil(years / max(1, years_per_epoch)) if years > 0 else 0


def epoch_chance(yearly_pct: Number, years: int) -> float:
    share = min(1.0, max(0.0, float(yearly_pct) / FULL_PROGRESS))
    return FULL_PROGRESS * (1 - (1 - share) ** max(1, years))


class Spanned:
    years_per_epoch: ClassVar[int] = EPOCH_YEARS

    def epochs(self, years: int) -> int:
        return epochs_in(years, self.years_per_epoch)

    def over_epoch(self, yearly_pct: Number) -> float:
        return epoch_chance(yearly_pct, self.years_per_epoch)

    def per_epoch(self, yearly: Number) -> int:
        return round(float(yearly) * self.years_per_epoch)


def keyed(namespace: object, prefix: str, suffix: str) -> int:
    return int(getattr(namespace, f"{prefix}_{suffix}"))


def rule_meta(definition: Field[Any]) -> RuleMeta:
    meta: RuleMeta = definition.metadata[RULE_METADATA_KEY]
    return meta


@dataclass(frozen=True)
class RuleDescriptor:
    namespace: str
    key: str
    default: Number
    value: Number
    minimum: Number
    maximum: Number
    group: str
    label: str

    @property
    def warning(self) -> str | None:
        if self.value > self.maximum:
            return f"{self.namespace}.{self.key} is above its advised maximum of {self.maximum}."
        return None

    @property
    def path(self) -> str:
        return f"{self.namespace}.{self.key}"


def describe(namespace: str, instance: Any) -> list[RuleDescriptor]:
    descriptors = []
    for definition in fields(instance):
        meta = rule_meta(definition)
        descriptors.append(
            RuleDescriptor(
                namespace=namespace,
                key=definition.name,
                default=meta.default,
                value=getattr(instance, definition.name),
                minimum=meta.minimum,
                maximum=meta.maximum,
                group=meta.group,
                label=meta.label,
            )
        )
    return descriptors
