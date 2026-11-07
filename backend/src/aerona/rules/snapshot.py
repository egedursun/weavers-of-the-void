import math
from dataclasses import Field, fields, replace
from typing import Any

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.rules.constraints import ASCENDING_CHAINS, AscendingChain
from aerona.rules.model import Number, RuleDescriptor, describe, rule_meta
from aerona.rules.registry import Rules
from aerona.rules.renames import canonical_overrides

OverrideMap = dict[tuple[str, str], float]
MAX_SAFE_INTEGER = 2**53 - 1
HALF = 0.5


FIELD_INDEX: dict[str, dict[str, Field[Any]]] = {}


def _fields_of(kind: type[Any]) -> dict[str, Field[Any]]:
    key = f"{kind.__module__}.{kind.__qualname__}"
    found = FIELD_INDEX.get(key)
    if found is None:
        found = FIELD_INDEX[key] = {item.name: item for item in fields(kind)}
    return found


def _namespace_definitions(rules: Rules) -> dict[str, Any]:
    return {name: getattr(rules, name) for name in _fields_of(type(rules))}


def catalog(rules: Rules) -> list[RuleDescriptor]:
    return [descriptor for name, instance in _namespace_definitions(rules).items() for descriptor in describe(name, instance)]


def _definition(rules: Rules, namespace: str, key: str) -> Field[Any]:
    instance = getattr(rules, namespace, None) if namespace in _fields_of(type(rules)) else None
    if instance is None:
        raise NotFoundError(f"Unknown rule namespace {namespace}.")
    definition = _fields_of(type(instance)).get(key)
    if definition is None:
        raise NotFoundError(f"Unknown rule {namespace}.{key}.")
    return definition


def coerce(rules: Rules, namespace: str, key: str, value: float) -> Number:
    meta = rule_meta(_definition(rules, namespace, key))
    if not math.isfinite(value) or abs(value) > MAX_SAFE_INTEGER:
        raise ValidationFailedError(f"{namespace}.{key} must be a finite number within the safe integer range.")
    if isinstance(meta.default, int) and not isinstance(meta.default, bool):
        number: Number = math.floor(value + HALF)
    else:
        number = float(value)
    if number < meta.minimum:
        raise ValidationFailedError(f"{namespace}.{key} must be at least {meta.minimum}.")
    return number


def is_default(rules: Rules, namespace: str, key: str, value: float) -> bool:
    meta = rule_meta(_definition(rules, namespace, key))
    return float(value) == float(meta.default)


def apply_overrides(rules: Rules, overrides: OverrideMap) -> Rules:
    grouped: dict[str, dict[str, Number]] = {}
    for (namespace, key), value in canonical_overrides(overrides).items():
        try:
            grouped.setdefault(namespace, {})[key] = coerce(rules, namespace, key, value)
        except (NotFoundError, ValidationFailedError):
            continue
    namespaces = _namespace_definitions(rules)
    changes = {name: replace(namespaces[name], **values) for name, values in grouped.items()}
    return replace(rules, **changes)


def value_at(rules: Rules, path: str) -> Number:
    namespace, key = path.split(".", 1)
    value: Number = getattr(getattr(rules, namespace), key)
    return value


def chain_violation(rules: Rules, chain: AscendingChain) -> str | None:
    values = [value_at(rules, path) for path in chain.paths]
    for (left_path, left), (right_path, right) in zip(zip(chain.paths, values, strict=True), zip(chain.paths[1:], values[1:], strict=True), strict=False):
        if left > right or (chain.strict and left == right):
            relation = "below" if chain.strict else "at most"
            return f"{left_path} ({left}) must be {relation} {right_path} ({right})."
    return None


def constraint_violations(rules: Rules) -> list[str]:
    return [message for chain in ASCENDING_CHAINS if (message := chain_violation(rules, chain)) is not None]


def with_value(rules: Rules, namespace: str, key: str, value: Number) -> Rules:
    instance = _namespace_definitions(rules)[namespace]
    return replace(rules, **{namespace: replace(instance, **{key: value})})
