from collections import defaultdict

from sqlalchemy import select

from aerona.agents.context.entity_line import line_item
from aerona.agents.context.scope import Scope
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import LocationTreeContext, TreeNode

LOCATIONLESS_TYPES = frozenset(kind for kind, spec in ENTITY_TYPES.items() if not spec.placeable and kind is not EntityType.REGION)
LAW_TYPES = frozenset({EntityType.LAW, EntityType.NATURAL_LAW})
TREE_STATUSES = (EntityStatus.CANON, EntityStatus.DEAD)


async def world_records(scope: Scope, world_id: int | None) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.status.in_(TREE_STATUSES)).order_by(EntityRow.id)
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    return list(await scope.session.scalars(statement))


def tree_nodes(records: list[EntityRow], limit: int) -> tuple[list[TreeNode], int]:
    placed = [record for record in records if record.entity_type not in LOCATIONLESS_TYPES]
    known = {record.id for record in placed}
    children: dict[int, list[EntityRow]] = defaultdict(list)
    roots: list[EntityRow] = []
    for record in placed:
        if record.location_id is not None and record.location_id in known:
            children[record.location_id].append(record)
        else:
            roots.append(record)
    nodes: list[TreeNode] = []
    stack = [(root, 0) for root in reversed(roots)]
    seen: set[int] = set()
    while stack and len(nodes) < limit:
        record, depth = stack.pop()
        if record.id in seen:
            continue
        seen.add(record.id)
        nodes.append(TreeNode(depth=depth, entity=line_item(record)))
        stack.extend((child, depth + 1) for child in reversed(children[record.id]))
    return nodes, len(placed)


async def location_tree(scope: Scope, world_id: int | None, limit: int) -> tuple[str, int, bool]:
    records = await world_records(scope, world_id)
    nodes, total = tree_nodes(records, limit)
    text = render(PromptId.LOCATION_TREE, LocationTreeContext(nodes=nodes)) if nodes else ""
    canon = sum(1 for record in records if record.status is EntityStatus.CANON)
    return text, canon, len(nodes) < total


async def legends(scope: Scope, world_id: int | None, limit: int) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(LOCATIONLESS_TYPES - LAW_TYPES))
        .order_by(EntityRow.id.desc())
        .limit(limit)
    )
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    return list(await scope.session.scalars(statement))
