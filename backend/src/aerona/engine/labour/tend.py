from sqlalchemy import select

from aerona.db.tables.labour import LabourContractRow, LabourDisputeRow, WorkerBodyRow
from aerona.db.write_guard import held
from aerona.domain.enums.labour import ContractStatus, DisputeOutcome, LabourDemand
from aerona.engine.context import TickContext
from aerona.engine.labour.bargaining import bargain
from aerona.engine.labour.bodies import LabourTally, Parties, ensure_rows, home_of, tend_body, trades_of
from aerona.engine.labour.contracts import contract_for, tend_contract
from aerona.engine.labour.cooperatives import tend_works
from aerona.engine.labour.disputes import tend_dispute
from aerona.engine.labour.founding import maybe_found
from aerona.engine.labour.hirers import hirer_of, own_side
from aerona.engine.labour.legacy import apply_legacy
from aerona.engine.labour.spread import spread_from
from aerona.engine.primitives.standing import ended_ids

SETTLED_STATUSES = frozenset({ContractStatus.AGREED})


async def bargain_round(ctx: TickContext, body: WorkerBodyRow, tally: LabourTally) -> None:
    home = await home_of(ctx.session, body)
    if home is None or held(body.faction_node_id) or held(home.id) or not body.members:
        return
    for trade in trades_of(body):
        hirer = await hirer_of(ctx.session, home, trade)
        if held(hirer.id) or await own_side(ctx.session, body.faction_node_id, hirer.id):
            continue
        contract = await contract_for(ctx, body.faction_node_id, hirer.id, trade)
        if contract is not None and contract.status in SETTLED_STATUSES:
            continue
        await bargain(ctx, Parties(body, hirer, home, trade), [LabourDemand.WAGE], tally)


async def tend_labour(ctx: TickContext) -> LabourTally:
    tally = LabourTally()
    await apply_legacy(ctx)
    await ensure_rows(ctx)
    standing = select(WorkerBodyRow).where(WorkerBodyRow.faction_node_id.not_in(ended_ids())).order_by(WorkerBodyRow.faction_node_id)
    bodies = list(await ctx.session.scalars(standing))
    for body in bodies:
        await tend_body(ctx, body, tally)
        await tend_works(ctx, body, tally)
    contracts = await ctx.session.scalars(select(LabourContractRow).where(LabourContractRow.status == ContractStatus.AGREED).order_by(LabourContractRow.id))
    for contract in list(contracts):
        await tend_contract(ctx, contract, tally)
    disputes = await ctx.session.scalars(select(LabourDisputeRow).where(LabourDisputeRow.outcome == DisputeOutcome.ONGOING).order_by(LabourDisputeRow.id))
    for dispute in list(disputes):
        if await tend_dispute(ctx, dispute, tally) is DisputeOutcome.WON:
            await spread_from(ctx, dispute, tally)
    for body in bodies:
        await bargain_round(ctx, body, tally)
    await maybe_found(ctx, tally)
    return tally
