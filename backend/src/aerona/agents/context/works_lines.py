from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import an, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.works import PublicWorksRow, StateEnterpriseRow
from aerona.domain.enums.works import WorksStatus
from aerona.engine.cycles.book import realm_of


async def mortal_works_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    places = [place for place in (me.location_id,) if place is not None]
    realm = await realm_of(session, me.location_id) if me.location_id is not None else None
    builders = [builder for builder in (realm,) if builder is not None]
    statement = select(PublicWorksRow).where(PublicWorksRow.status != WorksStatus.FAILED)
    statement = statement.where(PublicWorksRow.place_node_id.in_(places) | PublicWorksRow.polity_entity_id.in_(builders))
    for works in await session.scalars(statement.order_by(PublicWorksRow.id)):
        state = (
            f"stage {works.stage} of {works.stages}, budget {works.budget}"
            if works.status is WorksStatus.BUILDING
            else f"finished, condition {works.condition}"
        )
        found.append(
            f"{an(spoken(works.kind))} of {await named(scope, works.polity_entity_id)} (works {works.id}) at {await named(scope, works.place_node_id)}: "
            f"{state}, quality {works.quality}, built by {spoken(works.labour)} labour"
        )
    for enterprise in await session.scalars(
        select(StateEnterpriseRow).where(StateEnterpriseRow.polity_entity_id.in_(builders)).order_by(StateEnterpriseRow.id)
    ):
        sector = spoken(enterprise.sector) if enterprise.sector is not None else "no single good"
        found.append(
            f"your realm runs {an(spoken(enterprise.form))} in {sector}, managed by {spoken(enterprise.management)}; "
            f"output {enterprise.output}, revenue {enterprise.revenue}, corruption {enterprise.corruption}"
        )
    return found
