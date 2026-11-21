from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import several, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.labour import LabourContractRow, LabourDisputeRow, WorkerBodyRow
from aerona.domain.enums.labour import ContractStatus, DisputeOutcome
from aerona.engine.labour.bodies import bodies_at, trades_of


def body_line(name: str, body: WorkerBodyRow) -> str:
    trades = ", ".join(spoken(trade) for trade in trades_of(body)) or "no trade"
    return (
        f"{name} (worker body {body.faction_node_id}), {spoken(body.form)} for {trades}, {spoken(body.standing)} in law: "
        f"{several(body.members, 'member', 'members')}, fund {body.fund}, solidarity {body.solidarity}"
    )


async def mortal_labour_lines(scope: Scope, me: EntityRow) -> list[str]:
    town = me.location_id
    if town is None:
        return []
    session = scope.session
    mine = set(await session.scalars(select(FactionMembershipRow.faction_entity_id).where(FactionMembershipRow.mortal_entity_id == me.id)))
    found: list[str] = []
    for body in await bodies_at(session, town):
        member = " (one you belong to)" if body.faction_node_id in mine else ""
        found.append(body_line(await named(scope, body.faction_node_id), body) + member)
    contracts = select(LabourContractRow).where(LabourContractRow.settlement_entity_id == town, LabourContractRow.status == ContractStatus.AGREED)
    for contract in await session.scalars(contracts.order_by(LabourContractRow.id)):
        found.append(
            f"{await named(scope, contract.hirer_node_id)} (hirer {contract.hirer_node_id}) pays its {spoken(contract.trade)} workers {contract.wage} "
            f"in a hundred of the customary for {several(contract.hours, 'hour', 'hours')}, "
            f"safety {contract.safety}, rest {contract.rest}, keep {contract.keep}"
        )
    disputes = select(LabourDisputeRow).where(
        or_(LabourDisputeRow.settlement_entity_id == town, LabourDisputeRow.body_node_id.in_(sorted(mine))), LabourDisputeRow.outcome == DisputeOutcome.ONGOING
    )
    for dispute in await session.scalars(disputes.order_by(LabourDisputeRow.id)):
        found.append(
            f"{dispute.name}: {dispute.workers_out} out over {spoken(dispute.demand)}, the workers have lost {dispute.body_losses} and "
            f"{await named(scope, dispute.hirer_node_id)} {dispute.hirer_losses}"
        )
    return found
