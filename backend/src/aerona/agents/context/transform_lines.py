from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.transformations import TRANSFORMS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mythic import MantlingRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.transform import TransformProspectRow
from aerona.domain.enums.transform import ProspectStance
from aerona.rules.registry import Rules

STANCE_NOTES = {
    ProspectStance.OPEN: "",
    ProspectStance.BLOCKED: "; the Creator has blocked it",
    ProspectStance.FORCED: "; it has been ordered",
}


def prospect_text(name: str, row: TransformProspectRow) -> str:
    return f"{name}: {TRANSFORMS[row.kind].label.lower()}, {row.progress} of 100{STANCE_NOTES[row.stance]} (#{row.subject_node_id})"


async def prospect_lines(session: AsyncSession, rules: Rules, *, subjects: list[int] | None = None, world_id: int | None = None) -> list[str]:
    statement = select(TransformProspectRow, NodeRow.name).join(NodeRow, NodeRow.id == TransformProspectRow.subject_node_id)
    if subjects is not None:
        statement = statement.where(TransformProspectRow.subject_node_id.in_(subjects))
    if world_id is not None:
        in_world = select(EntityRow.id).where(EntityRow.world_id == world_id)
        statement = statement.where(TransformProspectRow.subject_node_id.in_(in_world) | TransformProspectRow.subject_node_id.in_(subjects or []))
    rows = await session.execute(statement.order_by(TransformProspectRow.progress.desc(), TransformProspectRow.id).limit(rules.transform.context_prospects))
    return [prospect_text(name, row) for row, name in rows]


async def mantling_line(session: AsyncSession, mortal_id: int) -> str | None:
    row = await session.get(MantlingRow, mortal_id)
    if row is None:
        return None
    god = await session.get(NodeRow, row.god_node_id) if row.god_node_id is not None else None
    whose = f" of {god.name}" if god is not None else ""
    return f"you walk a god's path toward the mantle{whose}: {row.progress} of 100" + ("; the Creator has blocked it" if row.blocked else "")
