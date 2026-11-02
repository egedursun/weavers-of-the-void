from sqlalchemy import select

from aerona.core.errors import NotFoundError
from aerona.db.repositories.base import Repository
from aerona.db.tables.celestial import StarRow, WorldRow
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
}


class NodeRepository(Repository):
    async def kind_of(self, node_id: int) -> NodeKind | None:
        kind: NodeKind | None = await self.session.scalar(select(NodeRow.kind).where(NodeRow.id == node_id))
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
        if not node_ids:
            return {}
        rows = await self.session.execute(select(NodeRow.id, NodeRow.kind).where(NodeRow.id.in_(node_ids)))
        return {node_id: kind for node_id, kind in rows}

    async def creator_id(self) -> int | None:
        node_id: int | None = await self.session.scalar(select(NodeRow.id).where(NodeRow.kind == NodeKind.CREATOR))
        return node_id
