from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.bonds import BOND_KINDS
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.domain.enums.node import NodeKind
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import BondEndpoint, BondLine, BondLinesContext


async def bond_line_lists(session: AsyncSession, node_id: int) -> tuple[list[BondLine], list[BondLine]]:
    repository = BondRepository(session)
    outgoing = await repository.outgoing(node_id)
    incoming = await repository.incoming(node_id)
    others = [bond.target_node_id for bond in outgoing] + [bond.source_node_id for bond in incoming]
    nodes = NodeRepository(session)
    names = await nodes.names_of(others)
    kinds = await nodes.kinds_of(others)

    def line(bond: BondRow, other: int) -> BondLine:
        endpoint = BondEndpoint(kind=kinds.get(other, NodeKind.ENTITY), id=other, name=names.get(other, "?"))
        return BondLine(label=BOND_KINDS[bond.kind].label, other=endpoint, description=bond.description)

    return [line(bond, bond.target_node_id) for bond in outgoing], [line(bond, bond.source_node_id) for bond in incoming]


async def bond_lines(session: AsyncSession, node_id: int) -> str:
    outgoing, incoming = await bond_line_lists(session, node_id)
    return render(PromptId.BOND_LINES, BondLinesContext(outgoing=outgoing, incoming=incoming)) if outgoing or incoming else ""
