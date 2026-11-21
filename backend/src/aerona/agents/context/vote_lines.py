from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.referendums import ReferendumRow

RECENT = 3


async def mortal_vote_lines(scope: Scope, me: EntityRow) -> list[str]:
    if me.location_id is None:
        return []
    session = scope.session
    realms = list(await session.scalars(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == me.location_id)))
    holders = sorted({me.location_id, *realms})
    query = select(ReferendumRow).where(or_(ReferendumRow.holder_node_id.in_(holders), ReferendumRow.called_by_node_id == me.id))
    found: list[str] = []
    for row in await session.scalars(query.order_by(ReferendumRow.id.desc()).limit(RECENT)):
        about = f" on {await named(scope, row.target_node_id)}" if row.target_node_id is not None else ""
        binding = "binding" if row.binding else "not binding"
        found.append(
            f"vote {row.id} of {await named(scope, row.holder_node_id)} on {spoken(row.subject)}{about}, {binding}, open to {spoken(row.franchise)}: "
            f"{spoken(row.result)}, {row.yes_pct} in a hundred for it, turnout {row.turnout_pct}"
        )
    return found
