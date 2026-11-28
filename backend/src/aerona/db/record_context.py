import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm.base import instance_state

from aerona.domain.enums.modifier import ModifierOp
from aerona.domain.enums.node import ActorKind
from aerona.domain.models.moment import Moment

PHASE_FAMILY = "phase"
UNCAPTURED = "aerona.uncaptured"
TERMS_FLOOD = 1000
ROW_STAMP = "record_row_stamp"
COLUMN_STAMPS = "record_column_stamps"
Stamp = tuple["RecordScope | None", tuple["Term", ...]]


@dataclass(frozen=True)
class Term:
    key: str
    amount: float
    op: ModifierOp = ModifierOp.ADD
    source_node_id: int | None = None
    source_incident_id: int | None = None


class TermFlood(UserWarning):
    pass


@dataclass
class TermsCollector:
    terms: list[Term] = field(default_factory=list)
    seen: set[tuple[str, float, int | None, int | None]] = field(default_factory=set)
    frozen: tuple[Term, ...] | None = None
    step: bool = False
    happening: bool = False
    view: object | None = None
    told: set[tuple[str, float, int | None, int | None]] = field(default_factory=set)

    def add(self, term: Term) -> None:
        marker = (term.key, term.amount, term.source_node_id, term.source_incident_id)
        if marker not in self.seen:
            self.seen.add(marker)
            self.terms.append(term)
            self.frozen = None
            if not self.step and len(self.terms) == TERMS_FLOOD:
                warnings.warn(TermFlood(f"{TERMS_FLOOD} terms gathered in one explaining scope; isolate the terms of each item"), stacklevel=3)

    def snapshot(self) -> tuple[Term, ...]:
        if self.frozen is None:
            self.frozen = tuple(self.terms)
        return self.frozen

    def untold(self) -> tuple[Term, ...]:
        fresh = tuple(term for term in self.terms if (term.key, term.amount, term.source_node_id, term.source_incident_id) not in self.told)
        self.told.update((term.key, term.amount, term.source_node_id, term.source_incident_id) for term in fresh)
        return fresh


@dataclass
class RecordScope:
    key: str
    epoch: int
    phase: str | None = None
    actor_kind: ActorKind = ActorKind.ENGINE
    actor_node_id: int | None = None
    world_id: int | None = None
    cause_incident_id: int | None = None
    moment: Moment | None = None
    incident_id: int | None = None
    step_id: int | None = None
    parent: "RecordScope | None" = None
    phase_incidents: dict[int | None, int] = field(default_factory=dict)

    @property
    def per_phase(self) -> bool:
        return self.incident_id is None and self.key.startswith(f"{PHASE_FAMILY}.")


SCOPE: ContextVar[RecordScope | None] = ContextVar("record_scope", default=None)
TERMS: ContextVar[TermsCollector | None] = ContextVar("record_terms", default=None)


def current_scope() -> RecordScope | None:
    return SCOPE.get()


@contextmanager
def scoped(scope: RecordScope) -> Iterator[RecordScope]:
    token = SCOPE.set(scope)
    try:
        yield scope
    finally:
        SCOPE.reset(token)


def change_terms(collector: TermsCollector | None) -> tuple[Term, ...]:
    return collector.snapshot() if collector is not None and not collector.step and not collector.happening else ()


@contextmanager
def happening() -> Iterator[TermsCollector]:
    collector = TermsCollector(happening=True)
    token = TERMS.set(collector)
    try:
        yield collector
    finally:
        TERMS.reset(token)


@contextmanager
def stepping() -> Iterator[TermsCollector]:
    collector = TermsCollector(step=True)
    token = TERMS.set(collector)
    try:
        yield collector
    finally:
        TERMS.reset(token)


@contextmanager
def isolated() -> Iterator[TermsCollector]:
    collector = TermsCollector()
    token = TERMS.set(collector)
    try:
        yield collector
    finally:
        TERMS.reset(token)


@contextmanager
def collecting() -> Iterator[TermsCollector]:
    found = TERMS.get()
    outer = found if found is not None and not found.step and not found.happening else None
    keeper = found if found is not None and found.happening else None
    collector = TermsCollector(list(outer.terms) if outer is not None else [], set(outer.seen) if outer is not None else set())
    if outer is not None:
        collector.told = set(outer.told) | {(term.key, term.amount, term.source_node_id, term.source_incident_id) for term in outer.terms}
    token = TERMS.set(collector)
    try:
        yield collector
    finally:
        TERMS.reset(token)
        for gatherer in (outer, keeper):
            if gatherer is not None:
                for term in collector.terms:
                    gatherer.add(term)
                gatherer.told |= collector.told


def add_term(key: str, amount: float, op: ModifierOp = ModifierOp.ADD, source_node_id: int | None = None, source_incident_id: int | None = None) -> None:
    collector = TERMS.get()
    if collector is not None:
        collector.add(Term(key, float(amount), op, source_node_id, source_incident_id))


def untold_terms() -> tuple[Term, ...]:
    collector = TERMS.get()
    return collector.untold() if collector is not None and not collector.step and not collector.happening else ()


def current_terms() -> TermsCollector | None:
    return TERMS.get()


def explaining_now() -> bool:
    return TERMS.get() is not None


def stamp() -> Stamp | None:
    scope = SCOPE.get()
    collector = TERMS.get()
    if scope is None and collector is None:
        return None
    return (scope, change_terms(collector))


def stamp_row(instance: Any) -> None:
    found = stamp()
    if found is not None:
        instance_state(instance).info[ROW_STAMP] = found


@contextmanager
def acting(actor_kind: ActorKind, actor_node_id: int | None, epoch: int, key: str = "actor", moment: Moment | None = None) -> Iterator[RecordScope]:
    outer = SCOPE.get()
    scope = RecordScope(key=key, epoch=epoch, actor_kind=actor_kind, actor_node_id=actor_node_id, parent=outer, moment=moment)
    with scoped(scope) as found:
        yield found
