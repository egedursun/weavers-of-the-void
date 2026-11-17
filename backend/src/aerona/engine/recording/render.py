from collections.abc import Mapping, Sequence
from enum import Enum
from string import Formatter
from typing import Any

from aerona.catalog.incident_kinds.spec import IncidentKindSpec
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import ARTICLES, spoken
from aerona.domain.enums.modifier import IncidentRole

FIELDS = Formatter()


class Named(list[str]):
    def __str__(self) -> str:
        if len(self) <= 1:
            return "".join(self)
        return f"{', '.join(self[:-1])} and {self[-1]}"

    def __format__(self, spec: str) -> str:
        return format(str(self), spec)

    def __getitem__(self, index: Any) -> Any:
        if isinstance(index, int) and index >= len(self):
            return ""
        return super().__getitem__(index)


def told(value: object) -> object:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, Enum):
        return spoken(value)
    if isinstance(value, float):
        return int(value) if value.is_integer() else round(value, 2)
    return value


def fields_of(spec: IncidentKindSpec, names: Mapping[IncidentRole, Sequence[str]], facts: Mapping[str, object]) -> dict[str, Any]:
    fields: dict[str, Any] = {role.value: Named(given) for role, given in names.items()}
    for role in spec.roles:
        fields.setdefault(role.role.value, Named())
    for fact in spec.facts:
        if not fact.required:
            fields.setdefault(fact.key, Named())
    for key, value in facts.items():
        fields[key] = Named(str(told(item)) for item in value) if isinstance(value, (list, tuple)) else told(value)
    return fields


def placeholders(template: str) -> list[str]:
    return [name.split("[")[0].split(".")[0] for _, name, _, _ in FIELDS.parse(template) if name]


def indexed(template: str) -> dict[str, int]:
    needed: dict[str, int] = {}
    for _, name, _, _ in FIELDS.parse(template):
        if name and "[" in name:
            base, _, rest = name.partition("[")
            position = rest.split("]")[0]
            if position.isdigit():
                needed[base] = max(needed.get(base, 0), int(position) + 1)
    return needed


def render_incident(spec: IncidentKindSpec, names: Mapping[IncidentRole, Sequence[str]], facts: Mapping[str, object]) -> str:
    fields = fields_of(spec, names, facts)
    missing = sorted({name for name in placeholders(spec.template) if name not in fields})
    if missing:
        raise ValidationFailedError(f"The happening {spec.key} cannot be told without {', '.join(missing)}.")
    text = " ".join(ARTICLES.format(spec.template, **fields).split())
    return text[:1].upper() + text[1:] if text else text
