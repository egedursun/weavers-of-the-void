from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.models.entity_stats import EntityStats, KnowledgeStats
from aerona.rules.registry import Rules
from aerona.rules.registry.knowledge import KnowledgeRules

BranchLevels = dict[KnowledgeBranch, int]


def raw_level(stats: EntityStats) -> int:
    level = stats.level if isinstance(stats, KnowledgeStats) else None
    return max(1, level if level is not None else 1)


def knowledge_level(rules: Rules, knowledge: EntityRow) -> int:
    return min(rules.knowledge.level_cap, raw_level(knowledge.stats))


def level_multiplier(table: KnowledgeRules, level: int) -> float:
    if level <= 0:
        return 0.0
    capped = min(level, table.level_cap)
    return min(table.level_multiplier_cap_pct / PERCENT, 1 + (capped - 1) * table.level_step_pct / PERCENT)


def ratio_of(table: KnowledgeRules, level: int, percent: float) -> float:
    effect = level_multiplier(table, level)
    if not effect:
        return 1.0
    value = 1 + (percent / PERCENT - 1) * effect
    return max(table.ratio_floor_pct / PERCENT, value) if percent < PERCENT else value


def times_of(table: KnowledgeRules, level: int, times: float) -> float:
    effect = level_multiplier(table, level)
    return 1 + (times - 1) * effect if effect else 1.0


async def known_levels(session: AsyncSession, entity_ids: Iterable[int] | None = None) -> dict[int, BranchLevels]:
    statement = (
        select(BondRow.source_node_id, EntityRow.knowledge_branch, EntityRow.stats)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(
            BondRow.kind == BondKind.KNOWS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.entity_type == EntityType.KNOWLEDGE,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.knowledge_branch.is_not(None),
        )
    )
    if entity_ids is not None:
        statement = statement.where(BondRow.source_node_id.in_(list(entity_ids)))
    known: dict[int, BranchLevels] = defaultdict(dict)
    for source, branch, stats in await session.execute(statement):
        if branch is not None:
            known[source][branch] = max(known[source].get(branch, 0), raw_level(stats))
    held = select(HolderLevelRow).where(HolderLevelRow.level > 0)
    if entity_ids is not None:
        held = held.where(HolderLevelRow.holder_entity_id.in_(list(entity_ids)))
    for row in await session.scalars(held):
        frontier = known.get(row.holder_entity_id, {}).get(row.branch)
        if frontier is not None:
            known[row.holder_entity_id][row.branch] = min(frontier, row.level)
    return known


async def known_branches(session: AsyncSession, entity_ids: Iterable[int] | None = None) -> dict[int, set[KnowledgeBranch]]:
    return {source: set(levels) for source, levels in (await known_levels(session, entity_ids)).items()}


async def knows(session: AsyncSession, entity_id: int, branch: KnowledgeBranch) -> bool:
    return branch in (await known_branches(session, [entity_id])).get(entity_id, set())


async def branch_level(session: AsyncSession, entity_id: int, branch: KnowledgeBranch) -> int:
    return (await known_levels(session, [entity_id])).get(entity_id, {}).get(branch, 0)


class KnowledgeMap:
    def __init__(self, known: dict[int, set[KnowledgeBranch]], levels: dict[int, BranchLevels] | None = None) -> None:
        self._known = known
        self._levels = levels or {}

    @classmethod
    async def load(cls, session: AsyncSession) -> "KnowledgeMap":
        levels = await known_levels(session)
        return cls({source: set(branches) for source, branches in levels.items()}, levels)

    def knows(self, entity_id: int, branch: KnowledgeBranch) -> bool:
        return branch in self._known.get(entity_id, set())

    def branches(self, entity_id: int) -> set[KnowledgeBranch]:
        return set(self._known.get(entity_id, set()))

    def level(self, entity_id: int, branch: KnowledgeBranch) -> int:
        if not self.knows(entity_id, branch):
            return 0
        return self._levels.get(entity_id, {}).get(branch, 1)

    def effect(self, rules: Rules, entity_id: int, branch: KnowledgeBranch) -> float:
        return level_multiplier(rules.knowledge, self.level(entity_id, branch))

    def ratio(self, rules: Rules, entity_id: int, branch: KnowledgeBranch, percent: float) -> float:
        return ratio_of(rules.knowledge, self.level(entity_id, branch), percent)

    def times(self, rules: Rules, entity_id: int, branch: KnowledgeBranch, times: float) -> float:
        return times_of(rules.knowledge, self.level(entity_id, branch), times)


class LawBook:
    def __init__(self, laws: dict[int, set[NaturalLaw]]) -> None:
        self._laws = laws

    @classmethod
    async def load(cls, session: AsyncSession) -> "LawBook":
        statement = select(EntityRow.world_id, EntityRow.natural_law).where(
            EntityRow.entity_type == EntityType.NATURAL_LAW, EntityRow.status == EntityStatus.CANON, EntityRow.natural_law.is_not(None)
        )
        laws: dict[int, set[NaturalLaw]] = defaultdict(set)
        for world_id, law in await session.execute(statement):
            if law is not None and law is not NaturalLaw.NONE:
                laws[world_id].add(law)
        return cls(laws)

    def has(self, law: NaturalLaw, world_id: int) -> bool:
        return law in self._laws.get(world_id, set())

    def anywhere(self, law: NaturalLaw) -> bool:
        return any(law in laws for laws in self._laws.values())

    def of(self, world_id: int) -> set[NaturalLaw]:
        return set(self._laws.get(world_id, set()))
