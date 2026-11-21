from dataclasses import dataclass

from aerona.db.tables.labour import LabourContractRow, LabourDisputeRow
from aerona.domain.enums.labour import ContractStatus, DisputeAct, LabourDemand, LegalStanding
from aerona.engine.context import TickContext
from aerona.engine.labour.bodies import LabourTally, Parties
from aerona.engine.labour.contracts import agree, open_contract, setting
from aerona.engine.labour.disputes import dispute_between, open_dispute
from aerona.engine.labour.hirers import hirer_strength, worker_strength

DISPUTE_SOLIDARITY = 50


@dataclass(frozen=True)
class Bargain:
    contract: LabourContractRow
    dispute: LabourDisputeRow | None
    gap: int


async def bargain(ctx: TickContext, parties: Parties, demands: list[LabourDemand], tally: LabourTally) -> Bargain:
    table = ctx.rules.labour
    body, hirer, community, trade = parties.body, parties.hirer, parties.community, parties.trade
    contract = await open_contract(ctx, body, hirer, community, trade)
    gap = await worker_strength(ctx, body, community.id, trade) - await hirer_strength(ctx, hirer, community.id)
    asked = demands or [LabourDemand.WAGE]
    if await dispute_between(ctx.session, body.faction_node_id, hirer.id) is not None:
        return Bargain(contract, None, gap)
    if gap <= -table.lockout_gap and ctx.rng(f"labour.lockout.{body.faction_node_id}.{hirer.id}.{ctx.epoch}").chance(table.lockout_chance_pct):
        setting(contract, "status", ContractStatus.BARGAINING)
        return Bargain(contract, await open_dispute(ctx, parties, DisputeAct.LOCKOUT, asked[0], tally), gap)
    if gap <= -table.dispute_gap and body.solidarity >= DISPUTE_SOLIDARITY and body.standing is not LegalStanding.BANNED:
        setting(contract, "status", ContractStatus.BARGAINING)
        return Bargain(contract, await open_dispute(ctx, parties, DisputeAct.STRIKE, asked[0], tally), gap)
    await agree(ctx, contract, gap, asked)
    tally.agreed += 1
    return Bargain(contract, None, gap)
