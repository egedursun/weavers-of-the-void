from sqlalchemy import select
from sqlalchemy.orm.util import identity_key

from aerona.core.errors import NotFoundError
from aerona.db.read_memo import memo_of, table_names
from aerona.db.repositories.base import Repository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import ClusterRow, DimensionRow, GalaxyRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.node import NodeKind
from aerona.domain.models.node_ref import NodeRef

NODE_TABLES: dict[NodeKind, type[NodeRow]] = {
    NodeKind.ENTITY: EntityRow,
    NodeKind.SON: SonRow,
    NodeKind.CREATOR: CreatorRow,
    NodeKind.FOREIGN_GOD: ForeignGodRow,
    NodeKind.WORLD: WorldRow,
    NodeKind.STAR: StarRow,
    NodeKind.GALAXY: GalaxyRow,
    NodeKind.CLUSTER: ClusterRow,
    NodeKind.DIMENSION: DimensionRow,
}


NODE_KINDS = "aerona.nodes.kind_of"
KIND_TABLES = table_names([NodeRow])


class NodeRepository(Repository):
    async def kind_of(self, node_id: int) -> NodeKind | None:
        known = self.session.sync_session.identity_map.get(identity_key(NodeRow, node_id))
        if isinstance(known, NodeRow):
            return known.kind
        memo = memo_of(self.session, NODE_KINDS, KIND_TABLES)
        if memo is not None and node_id in memo:
            remembered: NodeKind | None = memo[node_id]
            return remembered
        kind: NodeKind | None = await self.session.scalar(select(NodeRow.kind).where(NodeRow.id == node_id))
        after = memo_of(self.session, NODE_KINDS, KIND_TABLES)
        if after is not None:
            after[node_id] = kind
        return kind

    async def require_kind(self, node_id: int) -> NodeKind:
        kind = await self.kind_of(node_id)
        if kind is None:
            raise NotFoundError("No such record.")
        return kind

    async def ref(self, node_id: int) -> NodeRef:
        return NodeRef(kind=await self.require_kind(node_id), id=node_id)

    async def load(self, node_id: int) -> NodeRow:
        kind = await self.require_kind(node_id)
        return await self.require(NODE_TABLES[kind], node_id, kind.value.replace("_", " "))

    async def name_of(self, node_id: int) -> str | None:
        name: str | None = await self.session.scalar(select(NodeRow.name).where(NodeRow.id == node_id))
        return name

    async def names_of(self, node_ids: list[int]) -> dict[int, str]:
        if not node_ids:
            return {}
        rows = await self.session.execute(select(NodeRow.id, NodeRow.name).where(NodeRow.id.in_(node_ids)))
        return {node_id: name for node_id, name in rows}

    async def kinds_of(self, node_ids: list[int]) -> dict[int, NodeKind]:
        found: dict[int, NodeKind] = {}
        missing: list[int] = []
        memo = memo_of(self.session, NODE_KINDS, KIND_TABLES)
        for node_id in dict.fromkeys(node_ids):
            known = self.session.sync_session.identity_map.get(identity_key(NodeRow, node_id))
            if isinstance(known, NodeRow):
                found[node_id] = known.kind
            elif memo is not None and node_id in memo:
                if memo[node_id] is not None:
                    found[node_id] = memo[node_id]
            else:
                missing.append(node_id)
        if not missing:
            return found
        rows: dict[int, NodeKind] = {
            node_id: kind for node_id, kind in await self.session.execute(select(NodeRow.id, NodeRow.kind).where(NodeRow.id.in_(missing)))
        }
        after = memo_of(self.session, NODE_KINDS, KIND_TABLES)
        for node_id in missing:
            if node_id in rows:
                found[node_id] = rows[node_id]
            if after is not None:
                after[node_id] = rows.get(node_id)
        return found

    async def creator_id(self) -> int | None:
        node_id: int | None = await self.session.scalar(select(NodeRow.id).where(NodeRow.kind == NodeKind.CREATOR))
        return node_id
