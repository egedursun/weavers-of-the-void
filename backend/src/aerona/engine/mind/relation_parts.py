from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from sqlalchemy import func, select

from aerona.catalog.life.mind import REMEMBERED
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.fast_session import prime_prefixes, prime_rows
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import FeudRow
from aerona.db.tables.mind import CultureValueRow, MemoryRow, PersonalityValueRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.thin_sections import RelationComponentRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.military import FeudStatus
from aerona.domain.enums.mind import MemoryKind, RelationComponent
from aerona.engine.context import TickContext
from aerona.engine.mind.book import Values, values_for
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds

C = RelationComponent


@dataclass(frozen=True)
class Pair:
    first: int
    second: int


@dataclass
class Facts:
    memories: dict[tuple[int, int, MemoryKind], int] = field(default_factory=dict)
    bonds: dict[tuple[int, BondKind], set[int]] = field(default_factory=dict)
    feuds: set[tuple[int, int]] = field(default_factory=set)
    values: dict[int, Values] = field(default_factory=dict)
    trade_value: int = 0
    faith_value: int = 0
    language_value: int = 0
    rivalry_value: int = 0
    values_pct: int = 0

    def remembered(self, pair: Pair, kinds: tuple[MemoryKind, ...]) -> int:
        low, high = sorted((pair.first, pair.second))
        return sum(self.memories.get((low, high, kind), 0) for kind in kinds) // 2

    def held_by(self, node: int, kind: BondKind) -> set[int]:
        return self.bonds.get((node, kind), set())


BOND_KINDS = (BondKind.TRADES_WITH, BondKind.WORSHIPS, BondKind.SPEAKS)


async def gather(ctx: TickContext, nodes: set[int]) -> Facts:
    table = ctx.rules.community_relations
    facts = Facts(
        trade_value=table.trade_value,
        faith_value=table.faith_value,
        language_value=table.language_value,
        rivalry_value=table.rivalry_value,
        values_pct=table.values_pct,
    )
    kinds = sorted({kind for group in REMEMBERED.values() for kind in group})
    rows = await ctx.session.execute(
        select(MemoryRow.holder_node_id, MemoryRow.subject_node_id, MemoryRow.kind, func.sum(MemoryRow.magnitude))
        .where(MemoryRow.holder_node_id.in_(nodes), MemoryRow.subject_node_id.in_(nodes), MemoryRow.kind.in_(kinds))
        .group_by(MemoryRow.holder_node_id, MemoryRow.subject_node_id, MemoryRow.kind)
    )
    for holder, subject, kind, total_magnitude in rows.all():
        low, high = sorted((holder, subject))
        facts.memories[(low, high, kind)] = facts.memories.get((low, high, kind), 0) + int(total_magnitude or 0)
    for bond in await active_bonds(ctx.session, list(BOND_KINDS), sources=sorted(nodes)):
        facts.bonds.setdefault((bond.source_node_id, bond.kind), set()).add(bond.target_node_id)
    feuds = await ctx.session.execute(select(FeudRow.first_entity_id, FeudRow.second_entity_id).where(FeudRow.status == FeudStatus.ACTIVE))
    facts.feuds = {(min(first, second), max(first, second)) for first, second in feuds.all()}
    await prime_rows(ctx.session, EntityRow, nodes)
    await prime_prefixes(ctx.session, CultureValueRow, nodes)
    await prime_prefixes(ctx.session, PersonalityValueRow, nodes)
    for node in sorted(nodes):
        facts.values[node] = await values_for(ctx.session, node)
    return facts


def by_trade(facts: Facts, pair: Pair) -> int:
    road = facts.trade_value if pair.second in facts.held_by(pair.first, BondKind.TRADES_WITH) else 0
    return road + facts.remembered(pair, REMEMBERED[C.TRADE])


def by_faith(facts: Facts, pair: Pair) -> int:
    first, second = facts.held_by(pair.first, BondKind.WORSHIPS), facts.held_by(pair.second, BondKind.WORSHIPS)
    base = facts.faith_value if first & second else -facts.faith_value if first and second else 0
    return base + facts.remembered(pair, REMEMBERED[C.FAITH])


def by_language(facts: Facts, pair: Pair) -> int:
    return facts.language_value if facts.held_by(pair.first, BondKind.SPEAKS) & facts.held_by(pair.second, BondKind.SPEAKS) else 0


def by_rivalry(facts: Facts, pair: Pair) -> int:
    feud = (min(pair.first, pair.second), max(pair.first, pair.second)) in facts.feuds
    return (-facts.rivalry_value if feud else 0) + facts.remembered(pair, REMEMBERED[C.RIVALRY])


def by_values(facts: Facts, pair: Pair) -> int:
    first, second = facts.values.get(pair.first, {}), facts.values.get(pair.second, {})
    axes = set(first) & set(second)
    if not axes:
        return 0
    gap = sum(abs(first[axis] - second[axis]) for axis in axes) // len(axes)
    return -gap * facts.values_pct // PERCENT


Reader = Callable[[Facts, Pair], int]


def kinship(facts: Facts, pair: Pair) -> int:
    return facts.remembered(pair, REMEMBERED[C.KINSHIP])


def war_memory(facts: Facts, pair: Pair) -> int:
    return facts.remembered(pair, REMEMBERED[C.WAR_MEMORY])


def help_received(facts: Facts, pair: Pair) -> int:
    return facts.remembered(pair, REMEMBERED[C.HELP])


def insult(facts: Facts, pair: Pair) -> int:
    return facts.remembered(pair, REMEMBERED[C.INSULT])


READERS: Mapping[RelationComponent, Reader] = total(
    RelationComponent,
    {
        C.TRADE: by_trade,
        C.KINSHIP: kinship,
        C.FAITH: by_faith,
        C.WAR_MEMORY: war_memory,
        C.HELP: help_received,
        C.INSULT: insult,
        C.RIVALRY: by_rivalry,
        C.LANGUAGE: by_language,
        C.VALUES: by_values,
    },
)


async def keep_relation_components(ctx: TickContext) -> int:
    relations = list(await ctx.session.scalars(select(CommunityRelationRow).order_by(CommunityRelationRow.entity_a_id, CommunityRelationRow.entity_b_id)))
    live = [row for row in relations if not held(row.entity_a_id, row.entity_b_id)]
    if not live:
        return 0
    nodes = {node for row in live for node in (row.entity_a_id, row.entity_b_id)}
    facts = await gather(ctx, nodes)
    known = {(part.entity_a_id, part.entity_b_id, part.component): part for part in await ctx.session.scalars(select(RelationComponentRow))}
    kept = 0
    for row in live:
        pair = Pair(row.entity_a_id, row.entity_b_id)
        for component, reader in READERS.items():
            part = known.get((pair.first, pair.second, component))
            value = clamp_int(reader(facts, pair), -PERCENT, PERCENT)
            if part is None:
                if value == 0:
                    continue
                part = RelationComponentRow(entity_a_id=pair.first, entity_b_id=pair.second, component=component, locked=[])
                ctx.session.add(part)
            if "value" not in part.locked:
                part.value = value
            part.updated_epoch = ctx.epoch
            kept += 1
    await ctx.session.flush()
    return kept
