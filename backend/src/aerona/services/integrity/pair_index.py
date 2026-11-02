from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.domain.enums.bond import VISIBLE_BOND_STATES, BondKind

Pair = tuple[int, int]


def pair_of(first: int, second: int) -> Pair:
    return (first, second) if first <= second else (second, first)


@dataclass
class PairIndex:
    every: set[Pair] = field(default_factory=set)
    visible: set[Pair] = field(default_factory=set)
    kinds: set[tuple[Pair, BondKind]] = field(default_factory=set)
    degree: Counter[int] = field(default_factory=Counter)

    @classmethod
    async def load(cls, session: AsyncSession) -> "PairIndex":
        index = cls()
        rows = await session.execute(select(BondRow.source_node_id, BondRow.target_node_id, BondRow.kind, BondRow.state))
        for source, target, kind, state in rows:
            index.every.add(pair_of(source, target))
            if state in VISIBLE_BOND_STATES:
                index.add_visible(source, target, kind)
        return index

    def add_visible(self, source: int, target: int, kind: BondKind) -> None:
        pair = pair_of(source, target)
        self.every.add(pair)
        self.visible.add(pair)
        self.kinds.add((pair, kind))
        if source != target:
            self.degree[source] += 1
            self.degree[target] += 1

    def any_between(self, first: int, second: int) -> bool:
        return pair_of(first, second) in self.every

    def visible_between(self, first: int, second: int) -> bool:
        return pair_of(first, second) in self.visible

    def kind_between(self, first: int, second: int, kind: BondKind) -> bool:
        return (pair_of(first, second), kind) in self.kinds
