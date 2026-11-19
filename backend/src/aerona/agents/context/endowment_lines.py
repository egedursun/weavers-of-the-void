from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.tables.entities import EntityRow


async def mortal_endowment_lines(scope: Scope, me: EntityRow) -> list[str]:
    places = [place for place in (me.location_id,) if place is not None]
    found: list[str] = []
    for row in await scope.session.scalars(
        select(EndowmentRow)
        .where(
            or_(
                EndowmentRow.founder_node_id == me.id,
                EndowmentRow.trustee_node_id == me.id,
                EndowmentRow.beneficiary_node_id == me.id,
                EndowmentRow.beneficiary_node_id.in_(places),
            )
        )
        .order_by(EndowmentRow.id)
    ):
        founder = "you" if row.founder_node_id == me.id else await named(scope, row.founder_node_id)
        beneficiary = "you" if row.beneficiary_node_id == me.id else await named(scope, row.beneficiary_node_id)
        trustee = "you" if row.trustee_node_id == me.id else await named(scope, row.trustee_node_id) if row.trustee_node_id is not None else "no one"
        found.append(
            f"endowment {row.id} that {founder} founded serves {beneficiary} for {spoken(row.purpose)}: capital {row.capital} in {spoken(row.capital_kind)}, "
            f"income {row.income} each epoch, trustee {trustee}, {spoken(row.state)}, {spoken(row.terms)}"
        )
    return found
