from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.reckoning import ReckoningCaseRow, ReckoningMeasureRow, ReckoningRow


async def mortal_reckoning_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    realms = (
        list(await session.scalars(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == me.location_id)))
        if me.location_id
        else []
    )
    accused = select(ReckoningCaseRow.reckoning_id).where(ReckoningCaseRow.accused_node_id == me.id)
    query = select(ReckoningRow).where(ReckoningRow.closed_epoch.is_(None), or_(ReckoningRow.polity_entity_id.in_(realms), ReckoningRow.id.in_(accused)))
    found: list[str] = []
    for row in await session.scalars(query.order_by(ReckoningRow.id)):
        measures = await session.scalars(select(ReckoningMeasureRow).where(ReckoningMeasureRow.reckoning_id == row.id).order_by(ReckoningMeasureRow.id))
        listed = ", ".join(f"{spoken(measure.measure)} {measure.strength} ({spoken(measure.stage)})" for measure in measures) or "no measures"
        fallen = await named(scope, row.fallen_node_id) if row.fallen_node_id is not None else "a fallen regime"
        found.append(f"reckoning {row.id} of {await named(scope, row.polity_entity_id)} with the servants of {fallen}: {listed}; resistance {row.resistance}")
        mine = await session.scalar(select(ReckoningCaseRow).where(ReckoningCaseRow.reckoning_id == row.id, ReckoningCaseRow.accused_node_id == me.id))
        if mine is not None:
            found.append(f"you stand in it under {spoken(mine.measure)}, {spoken(mine.outcome)}")
    return found
