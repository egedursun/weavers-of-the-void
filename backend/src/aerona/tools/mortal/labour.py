from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.labour import WorkerBodyRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.demography import Job
from aerona.domain.enums.faction import FactionRank
from aerona.domain.enums.labour import DisputeAct, LabourDemand, LegalStanding, WorkerAct, WorkerBodyForm
from aerona.engine.labour.bargaining import bargain
from aerona.engine.labour.bodies import LabourTally, Parties, body_covering, home_of, standing_at, trade_workers, trades_of
from aerona.engine.labour.disputes import dispute_between, open_dispute
from aerona.engine.labour.founding import found_body
from aerona.engine.labour.hirers import hirer_of
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

TRADES_MAX = 4
DEMANDS_MAX = 6
LEADING_RANKS = (FactionRank.LEADER, FactionRank.OFFICER)


class FoundWorkerBodyInput(ToolInput):
    form: WorkerBodyForm
    trades: list[Job] = Field(min_length=1, max_length=TRADES_MAX)
    settlement_id: int


class BargainContractInput(ToolInput):
    worker_body_id: int
    hirer_id: int
    demands: list[LabourDemand] = Field(min_length=1, max_length=DEMANDS_MAX)


class CallDisputeInput(ToolInput):
    worker_body_id: int
    act: WorkerAct
    demand: LabourDemand


class LockOutInput(ToolInput):
    hirer_id: int
    worker_body_id: int
    demand: LabourDemand


async def heads(call: MortalCall, node_id: int) -> bool:
    if node_id == call.me.id:
        return True
    query = select(OrgGovernanceRow.org_node_id).where(OrgGovernanceRow.org_node_id == node_id, OrgGovernanceRow.head_node_id == call.me.id)
    return await call.session.scalar(query) is not None


async def leads_body(call: MortalCall, body_id: int) -> bool:
    if await heads(call, body_id):
        return True
    rank = await call.session.scalar(
        select(FactionMembershipRow.rank).where(FactionMembershipRow.faction_entity_id == body_id, FactionMembershipRow.mortal_entity_id == call.me.id)
    )
    return rank in LEADING_RANKS


async def led_body(call: MortalCall, body_id: int) -> tuple[WorkerBodyRow, EntityRow]:
    body = await call.session.get(WorkerBodyRow, body_id)
    home = await home_of(call.session, body) if body is not None else None
    if body is None or home is None:
        fail(MortalResult.LABOUR_REFUSED, why="there is no such worker body with a home")
    if held(body.faction_node_id) or held(home.id):
        fail(MortalResult.LABOUR_REFUSED, why="a god holds that body as it is")
    return body, home


async def hiring(call: MortalCall, body: WorkerBodyRow, home: EntityRow, hirer_id: int) -> tuple[EntityRow, Job]:
    for trade in trades_of(body):
        hirer = await hirer_of(call.session, home, trade)
        if hirer.id == hirer_id:
            if held(hirer.id):
                fail(MortalResult.LABOUR_REFUSED, why="a god holds that hirer as it is")
            return hirer, trade
    fail(MortalResult.LABOUR_REFUSED, why=f"that hirer does not employ the trades of the body at {home.name}")


async def found_worker_body_tool(call: MortalCall, args: FoundWorkerBodyInput) -> str:
    town = await living_entity(call.session, args.settlement_id)
    if town is None or call.me.location_id != town.id:
        fail(MortalResult.LABOUR_REFUSED, why="a worker body is founded where its founder lives")
    if held(town.id):
        fail(MortalResult.LABOUR_REFUSED, why="a god holds that town as it is")
    trades = sorted(set(args.trades), key=lambda trade: trade.value)
    if not await trade_workers(call.session, town.id, trades):
        fail(MortalResult.LABOUR_REFUSED, why=f"no one works those trades at {town.name}")
    taken = [trade for trade in trades if await body_covering(call.session, town.id, trade) is not None]
    if len(taken) == len(trades):
        fail(MortalResult.LABOUR_REFUSED, why="a body already speaks for those trades there")
    body = await found_body(call.tick, town, [trade for trade in trades if trade not in taken], args.form, founder=call.me.id)
    faction = await call.session.get(EntityRow, body.faction_node_id)
    call.target(town.id)
    standing = await standing_at(call.session, town.id)
    return result(
        MortalResult.WORKER_BODY_FOUNDED,
        body=faction.name if faction is not None else "the body",
        form=spoken(args.form),
        standing=spoken(standing),
        secret="; the law bans it, so it meets in secret" if standing is LegalStanding.BANNED else "",
    )


async def bargain_contract_tool(call: MortalCall, args: BargainContractInput) -> str:
    body, home = await led_body(call, args.worker_body_id)
    if not await leads_body(call, body.faction_node_id):
        fail(MortalResult.LABOUR_REFUSED, why="only those who lead a worker body bargain for it")
    hirer, trade = await hiring(call, body, home, args.hirer_id)
    outcome = await bargain(call.tick, Parties(body, hirer, home, trade), list(dict.fromkeys(args.demands)), LabourTally())
    call.target(home.id)
    if outcome.dispute is not None:
        return result(MortalResult.DISPUTE_BEGUN, act=spoken(outcome.dispute.act), hirer=hirer.name, demand=spoken(outcome.dispute.demand))
    contract = outcome.contract
    return result(MortalResult.CONTRACT_AGREED, hirer=hirer.name, trade=spoken(trade), wage=contract.wage, hours=contract.hours)


async def call_dispute_tool(call: MortalCall, args: CallDisputeInput) -> str:
    body, home = await led_body(call, args.worker_body_id)
    if not await leads_body(call, body.faction_node_id):
        fail(MortalResult.LABOUR_REFUSED, why="only those who lead a worker body call its members out")
    if not body.members:
        fail(MortalResult.LABOUR_REFUSED, why="the body has no members to call out")
    trades = trades_of(body)
    if not trades:
        fail(MortalResult.LABOUR_REFUSED, why="the body speaks for no trade")
    hirer = await hirer_of(call.session, home, trades[0])
    if hirer.id == body.faction_node_id or held(hirer.id):
        fail(MortalResult.LABOUR_REFUSED, why="there is no hirer to stand against")
    if await dispute_between(call.session, body.faction_node_id, hirer.id) is not None:
        fail(MortalResult.LABOUR_REFUSED, why="a dispute with that hirer already runs")
    dispute = await open_dispute(call.tick, Parties(body, hirer, home, trades[0]), DisputeAct(args.act.value), args.demand, LabourTally())
    call.target(home.id)
    return result(MortalResult.DISPUTE_BEGUN, act=spoken(dispute.act), hirer=hirer.name, demand=spoken(dispute.demand))


async def lock_out_tool(call: MortalCall, args: LockOutInput) -> str:
    if not await heads(call, args.hirer_id):
        fail(MortalResult.LABOUR_REFUSED, why="only the hirer or the head of the hirer locks its workers out")
    body, home = await led_body(call, args.worker_body_id)
    hirer, trade = await hiring(call, body, home, args.hirer_id)
    if await dispute_between(call.session, body.faction_node_id, hirer.id) is not None:
        fail(MortalResult.LABOUR_REFUSED, why="a dispute with that body already runs")
    dispute = await open_dispute(call.tick, Parties(body, hirer, home, trade), DisputeAct.LOCKOUT, args.demand, LabourTally())
    call.target(home.id)
    return result(MortalResult.DISPUTE_BEGUN, act=spoken(dispute.act), hirer=hirer.name, demand=spoken(dispute.demand))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    work = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.FOUND_WORKER_BODY, AgentKind.MORTAL, FoundWorkerBodyInput, work, found_worker_body_tool),
        ToolSpec(MortalToolId.BARGAIN_CONTRACT, AgentKind.MORTAL, BargainContractInput, work, bargain_contract_tool),
        ToolSpec(MortalToolId.CALL_DISPUTE, AgentKind.MORTAL, CallDisputeInput, work, call_dispute_tool),
        ToolSpec(MortalToolId.LOCK_OUT, AgentKind.MORTAL, LockOutInput, work, lock_out_tool),
    ]
