from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import InstanceState, ORMExecuteState, Session

from aerona.db.read_memo import register_index
from aerona.db.tables.belonging import HeldIdentityRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import CultureValueRow, MemoryRow, PersonalityValueRow, TraitRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.renown import ReputationRow, RulerCurrencyRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.domain.enums.entity import EntityType

OPINION_CACHE = "aerona.opinion_cache"
SHARED_KINDS = frozenset({EntityType.PEOPLE, EntityType.LANGUAGE})
STRUCTURE = ("entity_type", "status", "location_id", "world_id", "creator_son_id")
NODE_COLUMNS: dict[type[Any], tuple[str, ...]] = {
    BondRow: ("source_node_id", "target_node_id"),
    PersonalityValueRow: ("node_id",),
    TraitRow: ("node_id",),
    HeldIdentityRow: ("holder_entity_id",),
    RulerCurrencyRow: ("subject_node_id",),
}
PAIR_COLUMNS: dict[type[Any], tuple[str, str, bool]] = {
    MemoryRow: ("holder_node_id", "subject_node_id", False),
    RelationshipRow: ("holder_node_id", "subject_node_id", False),
    ReputationRow: ("community_node_id", "subject_node_id", False),
    CommunityRelationRow: ("entity_a_id", "entity_b_id", True),
}
FOLLOWED_ROWS = (*NODE_COLUMNS, *PAIR_COLUMNS)


class UnknownChangeError(Exception):
    pass


class OpinionCache:
    def __init__(self, rules: object, epoch: int) -> None:
        self.rules = rules
        self.epoch = epoch
        self.values: dict[tuple[int, int], Any] = {}
        self.nodes: dict[int, Any] = {}
        self.by_node: dict[int, set[tuple[int, int]]] = {}

    def put(self, holder_id: int, subject_id: int, value: Any) -> None:
        key = (holder_id, subject_id)
        self.values[key] = value
        self.by_node.setdefault(holder_id, set()).add(key)
        self.by_node.setdefault(subject_id, set()).add(key)

    def forget(self, node: int) -> None:
        self.nodes.pop(node, None)
        for key in self.by_node.pop(node, ()):
            self.values.pop(key, None)

    def forget_pair(self, holder_id: int, subject_id: int) -> None:
        self.values.pop((holder_id, subject_id), None)


def opinion_cache(sync: Session, rules: object, epoch: int) -> OpinionCache:
    found: OpinionCache | None = sync.info.get(OPINION_CACHE)
    if found is None or found.rules is not rules or found.epoch != epoch:
        found = sync.info[OPINION_CACHE] = OpinionCache(rules, epoch)
    return found


def column_values(state: InstanceState[Any], column: str) -> set[int]:
    history = state.attrs[column].history
    found = {value for value in (*history.added, *history.unchanged, *history.deleted) if value is not None}
    if not found and column not in state.dict and not history.deleted:
        raise UnknownChangeError(column)
    return found


def node_change(state: InstanceState[Any], new: bool) -> set[int]:
    if isinstance(state.obj(), EntityRow):
        if not new and not any(state.attrs[column].history.has_changes() for column in STRUCTURE):
            return set()
        if not column_values(state, "entity_type").isdisjoint(SHARED_KINDS):
            raise UnknownChangeError("entity_type")
    elif not new:
        return set()
    return column_values(state, "id")


@dataclass
class Touched:
    nodes: set[int] = field(default_factory=set)
    pairs: set[tuple[int, int]] = field(default_factory=set)

    def note(self, state: InstanceState[Any]) -> None:
        nodes = NODE_COLUMNS.get(state.class_)
        if nodes is not None:
            self.nodes.update(node for column in nodes for node in column_values(state, column))
            return
        pair = PAIR_COLUMNS.get(state.class_)
        if pair is None:
            return
        holder, subject, both = pair
        for first in column_values(state, holder):
            for second in column_values(state, subject):
                self.pairs.add((first, second))
                if both:
                    self.pairs.add((second, first))


def touched(sync: Session) -> Touched:
    found = Touched()
    for row in sync._deleted.values():
        if isinstance(row, NodeRow | CultureValueRow):
            raise UnknownChangeError(type(row).__name__)
        found.note(inspect(row))
    states = [*(inspect(row) for row in sync._new.values()), *(state for state in sync.identity_map._modified if state not in sync._deleted)]
    for state in states:
        row = state.obj()
        if row is None:
            continue
        if isinstance(row, CultureValueRow):
            raise UnknownChangeError("culture_values")
        if isinstance(row, NodeRow):
            found.nodes.update(node_change(state, state in sync._new))
            continue
        found.note(state)
    return found


def follow_opinions(sync: Session, *_: object) -> None:
    cache: OpinionCache | None = sync.info.get(OPINION_CACHE)
    if cache is None or not (cache.values or cache.nodes):
        return
    try:
        found = touched(sync)
    except UnknownChangeError:
        sync.info.pop(OPINION_CACHE, None)
        return
    for node in found.nodes:
        cache.forget(node)
    for holder_id, subject_id in found.pairs:
        cache.forget_pair(holder_id, subject_id)


def drop_opinions(sync: Session, *_: object) -> None:
    sync.info.pop(OPINION_CACHE, None)


def drop_opinions_on_write(state: ORMExecuteState) -> None:
    if not state.is_select:
        drop_opinions(state.session)


event.listen(Session, "after_flush", follow_opinions)
event.listen(Session, "after_soft_rollback", drop_opinions)
event.listen(Session, "do_orm_execute", drop_opinions_on_write)
register_index(OPINION_CACHE)
