from dataclasses import Field, dataclass, field, fields
from typing import Any

Number = int | float
RULE_METADATA_KEY = "rule"


@dataclass(frozen=True)
class RuleMeta:
    default: Number
    minimum: Number
    maximum: Number
    group: str
    label: str


def rule(default: Number, minimum: Number, maximum: Number, group: str, label: str) -> Any:
    return field(default=default, metadata={RULE_METADATA_KEY: RuleMeta(default, minimum, maximum, group, label)})


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
