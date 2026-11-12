from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session

from aerona.db.read_memo import KEEP_KEY, pending_tables, register_index, touched_rows
from aerona.db.tables.bonds import BondRow
from aerona.domain.enums.bond import BondKind, BondState

INDEX_KEY = "aerona.bond_index"
BOND_TABLE = BondRow.__tablename__


@dataclass
class BondLookup:
    by_source: dict[int, list[BondRow]] = field(default_factory=lambda: defaultdict(list))
    by_target: dict[int, list[BondRow]] = field(default_factory=lambda: defaultdict(list))
    ends: dict[int, tuple[int, int, BondKind]] = field(default_factory=dict)
    by_kind: dict[BondKind, list[BondRow]] = field(default_factory=lambda: defaultdict(list))

    def add(self, row: BondRow) -> None:
        self.by_source[row.source_node_id].append(row)
        self.by_target[row.target_node_id].append(row)
        self.by_kind[row.kind].append(row)
        self.ends[row.id] = (row.source_node_id, row.target_node_id, row.kind)

    def remove(self, row: BondRow) -> None:
        source, target, kind = self.ends.pop(row.id, (row.source_node_id, row.target_node_id, row.kind))
        self.by_source[source] = [bond for bond in self.by_source.get(source, []) if bond is not row]
        self.by_target[target] = [bond for bond in self.by_target.get(target, []) if bond is not row]
        self.by_kind[kind] = [bond for bond in self.by_kind.get(kind, []) if bond is not row]

    def moved(self, row: BondRow) -> None:
        if self.ends.get(row.id) != (row.source_node_id, row.target_node_id, row.kind):
            self.remove(row)
            self.add(row)
            for bonds in (self.by_source[row.source_node_id], self.by_target[row.target_node_id], self.by_kind[row.kind]):
                bonds.sort(key=lambda bond: bond.id)

    def select(
        self,
        kinds: Iterable[BondKind] | None,
        states: Iterable[BondState],
        sources: Iterable[int] | None = None,
        targets: Iterable[int] | None = None,
    ) -> list[BondRow]:
        wanted_kinds = frozenset(kinds) if kinds is not None else None
        wanted_states = frozenset(states)
        wanted_targets = frozenset(targets) if targets is not None else None
        if sources is not None:
            pool = [bond for source in dict.fromkeys(sources) for bond in self.by_source.get(source, [])]
        elif wanted_targets is not None:
            pool = [bond for target in wanted_targets for bond in self.by_target.get(target, [])]
        elif wanted_kinds is not None:
            pool = [bond for kind in wanted_kinds for bond in self.by_kind.get(kind, [])]
        else:
            pool = [bond for bonds in self.by_source.values() for bond in bonds]
        found = [
            bond
            for bond in pool
            if bond.state in wanted_states
            and (wanted_kinds is None or bond.kind in wanted_kinds)
            and (wanted_targets is None or bond.target_node_id in wanted_targets)
        ]
        return sorted(found, key=lambda bond: bond.id)


async def bond_lookup(session: AsyncSession) -> BondLookup | None:
    sync = session.sync_session
    if KEEP_KEY not in sync.info:
        return None
    if BOND_TABLE in pending_tables(sync):
        await session.flush()
    lookup: BondLookup | None = sync.info.get(INDEX_KEY)
    if lookup is None:
        lookup = BondLookup()
        for row in await session.scalars(select(BondRow).order_by(BondRow.id)):
            lookup.add(row)
        sync.info[INDEX_KEY] = lookup
    return lookup


def follow_flush(sync: Session, *_: object) -> None:
    lookup: BondLookup | None = sync.info.get(INDEX_KEY)
    if lookup is None:
        return
    new, dirty, deleted = touched_rows(sync, BondRow)
    for row in new:
        lookup.add(row)
    for row in dirty:
        lookup.moved(row)
    for row in deleted:
        lookup.remove(row)


def drop_lookup(sync: Session, *_: object) -> None:
    sync.info.pop(INDEX_KEY, None)


def drop_on_write(state: ORMExecuteState) -> None:
    if state.is_select:
        return
    target = getattr(state.statement, "table", None)
    if target is None or getattr(target, "name", None) == BOND_TABLE:
        drop_lookup(state.session)


event.listen(Session, "after_flush", follow_flush)
event.listen(Session, "after_soft_rollback", drop_lookup)
event.listen(Session, "do_orm_execute", drop_on_write)
register_index(INDEX_KEY)
