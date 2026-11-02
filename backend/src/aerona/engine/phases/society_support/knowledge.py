from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.primitives.knowledge import raw_level
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import set_stats, stat_or


class KnowledgeHoldings:
    def __init__(self, known: dict[int, set[int]], knowledge: dict[int, EntityRow]) -> None:
        self._known = known
        self.knowledge = knowledge

    @classmethod
    async def load(cls, session: AsyncSession) -> "KnowledgeHoldings":
        rows = list(
            await session.scalars(
                select(EntityRow).where(EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        )
        knowledge = {row.id: row for row in rows}
        known: dict[int, set[int]] = defaultdict(set)
        statement = select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(list(knowledge))
        )
        for source, target in await session.execute(statement.order_by(BondRow.id)):
            known[source].add(target)
        return cls(known, knowledge)

    def known_by(self, entity_id: int) -> list[EntityRow]:
        return [self.knowledge[knowledge_id] for knowledge_id in sorted(self._known.get(entity_id, set())) if knowledge_id in self.knowledge]

    def knows(self, entity_id: int, knowledge_id: int) -> bool:
        return knowledge_id in self._known.get(entity_id, set())

    def knows_branch(self, entity_id: int, branch: KnowledgeBranch) -> bool:
        return any(self.knowledge[item].knowledge_branch is branch for item in self._known.get(entity_id, set()) if item in self.knowledge)

    def branch_level(self, entity_id: int, branch: KnowledgeBranch) -> int:
        levels = [
            raw_level(self.knowledge[item].stats)
            for item in self._known.get(entity_id, set())
            if item in self.knowledge and self.knowledge[item].knowledge_branch is branch
        ]
        return max(levels, default=0)

    def knowers(self, knowledge_id: int) -> set[int]:
        return {entity_id for entity_id, items in self._known.items() if knowledge_id in items}

    def record(self, entity_id: int, knowledge_id: int) -> None:
        self._known[entity_id].add(knowledge_id)

    def forget(self, entity_id: int, knowledge_id: int) -> None:
        self._known.get(entity_id, set()).discard(knowledge_id)


async def teach(ctx: TickContext, learner_id: int, knowledge: EntityRow, note: str | None, holdings: KnowledgeHoldings | None = None) -> bool:
    if knowledge.entity_type is not EntityType.KNOWLEDGE or learner_id == knowledge.id:
        return False
    bonds = BondRepository(ctx.session)
    existing = await ctx.session.scalar(
        select(BondRow.id).where(
            BondRow.source_node_id == learner_id,
            BondRow.target_node_id == knowledge.id,
            BondRow.kind == BondKind.KNOWS,
            BondRow.state == BondState.ACTIVE,
        )
    )
    if existing is not None:
        return False
    await bonds.connect(BondDraft(learner_id, knowledge.id, BondKind.KNOWS, ctx.epoch, note))
    spread = stat_or(knowledge, "spread", 0)
    set_stats(knowledge, spread=clamp_int(spread + ctx.rules.intervention_effects.knowledge_spread_gain, 0, PERCENT))
    if holdings is not None:
        holdings.record(learner_id, knowledge.id)
    return True
