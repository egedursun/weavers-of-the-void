from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.restoration import RestorationRow
from aerona.domain.enums.restoration import OPEN_STAGES


async def mortal_restoration_lines(scope: Scope, me: EntityRow) -> list[str]:
    query = select(RestorationRow).where(RestorationRow.stage.in_(sorted(OPEN_STAGES)))
    found: list[str] = []
    for row in await scope.session.scalars(query.order_by(RestorationRow.id)):
        if row.claimant_node_id != me.id and me.location_id not in (row.territories or []):
            continue
        grounds = ", ".join(spoken(basis) for basis in row.bases or []) or "memory"
        lead = "no one leads it"
        if row.claimant_node_id is not None:
            lead = "you lead it" if row.claimant_node_id == me.id else f"led by {await named(scope, row.claimant_node_id)}"
        realm = await named(scope, row.fallen_polity_id)
        found.append(f"restoration {row.id} of {realm} at its {spoken(row.stage)}, memory {row.memory}, on grounds of {grounds}; {lead}")
    return found
