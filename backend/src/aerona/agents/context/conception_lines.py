from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.divine_conceptions import DivineConceptionRow, GodReadingRow
from aerona.db.tables.entities import EntityRow
from aerona.engine.sacred.places import church_of


async def mortal_conception_lines(scope: Scope, me: EntityRow) -> list[str]:
    town = await scope.session.get(EntityRow, me.location_id) if me.location_id is not None else None
    cult = await church_of(scope.session, town) if town is not None else None
    row = await scope.session.get(DivineConceptionRow, cult.id) if cult is not None else None
    if cult is None or row is None:
        return []
    found = [
        f"{await named(scope, cult.id)} (faith {cult.id}) holds the divine {spoken(row.count)}, {spoken(row.nearness)}, as {spoken(row.personhood)}; "
        f"the Creator {spoken(row.creator_place)}; strain {row.strain}"
    ]
    for reading in await scope.session.scalars(select(GodReadingRow).where(GodReadingRow.cult_entity_id == cult.id).order_by(GodReadingRow.god_node_id)):
        found.append(f"it holds {await named(scope, reading.god_node_id)} {spoken(reading.reading)}")
    return found
