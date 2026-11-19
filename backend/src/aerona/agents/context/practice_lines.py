from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.catalog.facets import FACETS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.facets import FacetPracticeRow
from aerona.engine.body.customs import people_of


async def mortal_practice_lines(scope: Scope, me: EntityRow) -> list[str]:
    homes = [node for node in (me.location_id, (await people_of(scope.session, me) or me).id) if node is not None and node != me.id]
    if not homes:
        return []
    rows = await scope.session.scalars(
        select(FacetPracticeRow)
        .where(FacetPracticeRow.community_entity_id.in_(homes), FacetPracticeRow.level > 0)
        .order_by(FacetPracticeRow.level.desc(), FacetPracticeRow.id)
    )
    return [f"{FACETS[row.facet].label.lower()} kept at {row.level} of 100" for row in rows]
