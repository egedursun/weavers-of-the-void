from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.polity import OfficeRow


async def mortal_office_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for office in await session.scalars(select(OfficeRow).where(OfficeRow.holder_entity_id == me.id).order_by(OfficeRow.id)):
        realm = await named(scope, office.polity_entity_id)
        found.append(f"you hold the office of {spoken(office.kind)} (office {office.id}) in {realm} since epoch {office.since_epoch}")
    headed = select(OrgGovernanceRow).where(OrgGovernanceRow.head_node_id == me.id).order_by(OrgGovernanceRow.org_node_id)
    for org in await session.scalars(headed):
        found.append(f"you head {await named(scope, org.org_node_id)} (organisation {org.org_node_id}) since epoch {org.since_epoch}")
    for row in await session.scalars(select(DepartureRow).where(DepartureRow.holder_node_id == me.id).order_by(DepartureRow.id)):
        where = await named(scope, row.polity_entity_id or row.org_node_id) if (row.polity_entity_id or row.org_node_id) else "an office"
        back = f", came back in epoch {row.returned_epoch}" if row.returned_epoch is not None else ""
        found.append(f"you left {where} by {spoken(row.kind)} in epoch {row.epoch} (leaving {row.id}), standing {row.standing}{back}")
    return found
