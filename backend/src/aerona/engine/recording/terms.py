from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast

from aerona.db.record_context import TermsCollector, add_term, collecting, current_terms, isolated
from aerona.domain.enums.modifier import ModifierOp
from aerona.rules.registry import Rules

RULES_FAMILY = "rules"


@contextmanager
def explaining() -> Iterator[TermsCollector]:
    with collecting() as collector:
        yield collector


@contextmanager
def explaining_alone() -> Iterator[TermsCollector]:
    with isolated() as collector:
        yield collector


def term(key: str, amount: float, op: ModifierOp = ModifierOp.ADD, *, source_node_id: int | None = None, source_incident_id: int | None = None) -> None:
    add_term(key, amount, op, source_node_id, source_incident_id)


class ExplainedNamespace:
    def __init__(self, name: str, namespace: Any) -> None:
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_namespace", namespace)

    def __getattr__(self, field: str) -> Any:
        value = getattr(object.__getattribute__(self, "_namespace"), field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            add_term(f"{RULES_FAMILY}.{object.__getattribute__(self, '_name')}.{field}", value)
        object.__setattr__(self, field, value)
        return value


class ExplainedRules:
    def __init__(self, rules: Rules) -> None:
        object.__setattr__(self, "_rules", rules)

    def __getattr__(self, name: str) -> Any:
        value = getattr(object.__getattribute__(self, "_rules"), name)
        found = ExplainedNamespace(name, value) if hasattr(value, "__dataclass_fields__") else value
        object.__setattr__(self, name, found)
        return found


def explained_rules(rules: Rules) -> Rules:
    return cast(Rules, ExplainedRules(rules))


def plain(rules: Rules) -> Rules:
    return cast(Rules, object.__getattribute__(rules, "_rules")) if isinstance(rules, ExplainedRules) else rules


def rules_for(rules: Rules) -> Rules:
    collector = current_terms()
    if collector is None:
        return rules
    if collector.view is None or plain(cast(Rules, collector.view)) is not rules:
        collector.view = explained_rules(rules)
    return cast(Rules, collector.view)
