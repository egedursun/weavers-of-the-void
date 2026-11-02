from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules


@dataclass
class WorldView:
    entities: dict[int, EntityRow]
    patrons: dict[int, int]
    patron_kinds: dict[int, NodeKind]
    flags: dict[int, set[EntityFlag]]
    knows: dict[int, set[int]]
    atlas: RegionAtlas
    seafaring_hops: int

    def canon(self, *types: EntityType, world_id: int | None = None) -> list[EntityRow]:
        return [
            entity
            for entity in self.entities.values()
            if entity.status is EntityStatus.CANON and (not types or entity.entity_type in types) and (world_id is None or entity.world_id == world_id)
        ]

    def has_flag(self, entity_id: int, flag: EntityFlag) -> bool:
        return flag in self.flags.get(entity_id, set())

    def top_region_id(self, entity_id: int) -> int | None:
        return self.atlas.top_region(entity_id)

    def patron_son(self, entity_id: int) -> int | None:
        patron = self.patrons.get(entity_id)
        return patron if patron is not None and self.patron_kinds.get(patron) is NodeKind.SON else None

    def knows_branch(self, entity_id: int, branch: KnowledgeBranch) -> bool:
        return any(self.entities[known].knowledge_branch is branch for known in self.knows.get(entity_id, set()) if known in self.entities)

    def near(self, first: EntityRow, second: EntityRow) -> bool:
        seafarers = self.knows_branch(first.id, KnowledgeBranch.SEAFARING) or self.knows_branch(second.id, KnowledgeBranch.SEAFARING)
        return self.atlas.near(first.id, second.id, self.seafaring_hops if seafarers else None)


async def load_world_view(session: AsyncSession, rules: Rules) -> WorldView:
    entities = {entity.id: entity for entity in await session.scalars(select(EntityRow).order_by(EntityRow.id))}
    worships = await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id, NodeRow.kind)
        .join(NodeRow, NodeRow.id == BondRow.target_node_id)
        .where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id)
    )
    patrons: dict[int, int] = {}
    kinds: dict[int, NodeKind] = {}
    for source, target, kind in worships:
        if kind in (NodeKind.SON, NodeKind.CREATOR, NodeKind.FOREIGN_GOD):
            patrons[source] = target
            kinds[target] = kind
    for entity in entities.values():
        if entity.id not in patrons and entity.creator_son_id is not None:
            patrons[entity.id] = entity.creator_son_id
            kinds[entity.creator_son_id] = NodeKind.SON
    flags: dict[int, set[EntityFlag]] = {}
    for entity_id, flag in await session.execute(select(EntityFlagRow.entity_id, EntityFlagRow.flag)):
        flags.setdefault(entity_id, set()).add(flag)
    knows: dict[int, set[int]] = {}
    statement = select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE)
    for source, target in await session.execute(statement):
        knows.setdefault(source, set()).add(target)
    return WorldView(entities, patrons, kinds, flags, knows, await RegionAtlas.load(session), rules.world_engine.seafaring_reach_hops)
