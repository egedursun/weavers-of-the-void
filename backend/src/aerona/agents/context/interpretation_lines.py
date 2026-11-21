from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interpretation import InterpretationRow
from aerona.domain.enums.interpretation import InterpretationFault

RECENT = 2


async def mortal_interpretation_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    near = [node for node in (me.id, me.location_id) if node is not None]
    mine = or_(InterpretationRow.interpreter_node_id == me.id, InterpretationRow.first_party_id.in_(near), InterpretationRow.second_party_id.in_(near))
    query = select(InterpretationRow).where(mine, InterpretationRow.epoch >= scope.epoch - RECENT).order_by(InterpretationRow.id)
    found: list[str] = []
    for row in await session.scalars(query):
        sides = f"{await named(scope, row.first_party_id)} and {await named(scope, row.second_party_id)}"
        by = "you" if row.interpreter_node_id == me.id else await named(scope, row.interpreter_node_id) if row.interpreter_node_id is not None else "no one"
        known = f", found to carry {spoken(row.fault)}" if row.found and row.fault is not InterpretationFault.NONE else ""
        own = f", carried with {spoken(row.fault)}" if row.interpreter_node_id == me.id and row.fault is not InterpretationFault.NONE else ""
        found.append(f"exchange {row.id}: the {spoken(row.event)} between {sides}, carried by {by} at fidelity {row.fidelity}{known}{own}")
    return found
