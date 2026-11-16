from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.cosmography import DIMENSION_LAWS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.divine import LawScope
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.models.entity_stats import EntityStats, KnowledgeStats
from aerona.engine.cosmos.placement import Cosmography, cosmography_of
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


def reach_of(ladder: Cosmography, worlds: list[int], home: int, scope: LawScope) -> list[int]:
    if scope is LawScope.COSMOS:
        return worlds
    if scope is LawScope.DIMENSION:
        dimension = ladder.place_world_id(home).dimension_id
        partner = ladder.convergences.get(dimension) if dimension is not None else None
        return [world for world in worlds if ladder.place_world_id(world).dimension_id in (dimension, partner)]
    return [home]


@dataclass(frozen=True)
class HeldLaw:
    law: NaturalLaw
    entity_id: int | None
    strength: int


async def laws_of_dimension(session: AsyncSession, dimension_id: int) -> list[HeldLaw]:
    ladder = await cosmography_of(session)
    dimension = ladder.dimensions.get(dimension_id)
    if dimension is None:
        return []
    held = [HeldLaw(law, None, PERCENT) for law in DIMENSION_LAWS.get(dimension.dimension_kind, ())]
    statement = (
        select(NaturalLawProfileRow)
        .join(EntityRow, EntityRow.id == NaturalLawProfileRow.law_entity_id)
        .where(NaturalLawProfileRow.scope == LawScope.DIMENSION, EntityRow.status == EntityStatus.CANON)
        .order_by(NaturalLawProfileRow.law_entity_id)
    )
    for row in await session.scalars(statement):
        if row.world_id is not None and ladder.place_world_id(row.world_id).dimension_id == dimension_id:
            held.append(HeldLaw(row.effect, row.law_entity_id, row.strength))
    return held


def footprint(ladder: Cosmography, worlds: list[int], row: NaturalLawProfileRow) -> set[int]:
    if row.scope is LawScope.COSMOS:
        return set(worlds)
    if row.world_id is None:
        return set()
    return set(reach_of(ladder, worlds, row.world_id, row.scope))


class LawBook:
    def __init__(
        self, laws: dict[int, set[NaturalLaw]], regions: dict[int, set[NaturalLaw]] | None = None, strengths: dict[tuple[int, NaturalLaw], int] | None = None
    ) -> None:
        self._laws = laws
        self._regions = regions or {}
        self._strengths = strengths or {}

    @classmethod
    async def load(cls, session: AsyncSession) -> "LawBook":
        statement = select(EntityRow.id, EntityRow.world_id, EntityRow.natural_law).where(
            EntityRow.entity_type == EntityType.NATURAL_LAW, EntityRow.status == EntityStatus.CANON, EntityRow.natural_law.is_not(None)
        )
        profiles = {row.law_entity_id: row for row in await session.scalars(select(NaturalLawProfileRow))}
        worlds = list(await session.scalars(select(WorldRow.id)))
        ladder = await cosmography_of(session)
        laws: dict[int, set[NaturalLaw]] = defaultdict(set)
        regions: dict[int, set[NaturalLaw]] = defaultdict(set)
        strengths: dict[tuple[int, NaturalLaw], int] = {}
        for entity_id, world_id, law in await session.execute(statement):
            if law is None or law is NaturalLaw.NONE:
                continue
            profile = profiles.get(entity_id)
            if profile is not None and (profile.contested or profile.suspended or profile.strength <= 0):
                continue
            strength = profile.strength if profile is not None else PERCENT
            if profile is not None and profile.scope is LawScope.REGION and profile.region_entity_id is not None:
                regions[profile.region_entity_id].add(law)
                continue
            home = profile.world_id if profile is not None and profile.world_id is not None else world_id
            for target in reach_of(ladder, worlds, home, profile.scope if profile is not None else LawScope.WORLD):
                laws[target].add(law)
                strengths[(target, law)] = max(strengths.get((target, law), 0), strength)
        for target in worlds:
            place = ladder.place_world_id(target)
            for dimension in (place.dimension, ladder.partner_of(place)):
                for law in DIMENSION_LAWS.get(dimension.dimension_kind, ()) if dimension is not None else ():
                    laws[target].add(law)
                    strengths[(target, law)] = max(strengths.get((target, law), 0), PERCENT)
        return cls(laws, regions, strengths)

    def has(self, law: NaturalLaw, world_id: int) -> bool:
        return law in self._laws.get(world_id, set())

    def has_at(self, law: NaturalLaw, world_id: int, region_id: int | None) -> bool:
        return self.has(law, world_id) or (region_id is not None and law in self._regions.get(region_id, set()))

    def strength(self, law: NaturalLaw, world_id: int) -> int:
        return self._strengths.get((world_id, law), 0)

    def anywhere(self, law: NaturalLaw) -> bool:
        return any(law in laws for laws in self._laws.values()) or any(law in laws for laws in self._regions.values())

    def of(self, world_id: int) -> set[NaturalLaw]:
        return set(self._laws.get(world_id, set()))
