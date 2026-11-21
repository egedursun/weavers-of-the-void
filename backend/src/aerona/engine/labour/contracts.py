from sqlalchemy import select

from aerona.catalog.labour import DEMAND_TERMS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.labour import HOURS_MAX, WAGE_MAX, LabourContractRow, WorkerBodyRow
from aerona.db.write_guard import held
from aerona.domain.enums.demography import Job
from aerona.domain.enums.labour import OPEN_CONTRACTS, ContractStatus, LabourDemand
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.labour.bodies import LabourTally, max_hours_at, place_of
from aerona.engine.labour.hirers import shift_contentment
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

CUSTOMARY_WAGE = 100
CUSTOMARY_HOURS = 60
CUSTOMARY_TERM = 40
DEMAND_BOOST = 10
HOURS_PER_STRENGTH = 5
WAGE_FLOOR = 50
CONDITION_TERMS = ("safety", "rest", "keep")


async def contract_for(ctx: TickContext, body_id: int, hirer_id: int, trade: Job) -> LabourContractRow | None:
    query = select(LabourContractRow).where(
        LabourContractRow.body_node_id == body_id,
        LabourContractRow.hirer_node_id == hirer_id,
        LabourContractRow.trade == trade,
        LabourContractRow.status.in_(sorted(OPEN_CONTRACTS)),
    )
    return await ctx.session.scalar(query.order_by(LabourContractRow.id.desc()).limit(1))


async def open_contract(ctx: TickContext, body: WorkerBodyRow, hirer: EntityRow, community: EntityRow, trade: Job) -> LabourContractRow:
    found = await contract_for(ctx, body.faction_node_id, hirer.id, trade)
    if found is not None:
        return found
    contract = LabourContractRow(
        hirer_node_id=hirer.id,
        body_node_id=body.faction_node_id,
        settlement_entity_id=community.id,
        trade=trade,
        wage=CUSTOMARY_WAGE,
        hours=CUSTOMARY_HOURS,
        term_epochs=ctx.rules.labour.contract_term_epochs,
        started_epoch=ctx.epoch,
        status=ContractStatus.PROPOSED,
        locked=[],
    )
    ctx.session.add(contract)
    await ctx.session.flush()
    return contract


def setting(contract: LabourContractRow, field: str, value: int | ContractStatus) -> None:
    if field not in (contract.locked or []):
        setattr(contract, field, value)


async def agree(ctx: TickContext, contract: LabourContractRow, gap: int, demands: list[LabourDemand]) -> None:
    asked = {DEMAND_TERMS[demand] for demand in demands}
    boost = DEMAND_BOOST + max(0, gap) // 2
    wage = CUSTOMARY_WAGE + round_half_up(gap * ctx.rules.labour.wage_per_strength / PERCENT) + (boost if "wage" in asked else 0)
    setting(contract, "wage", clamp_int(wage, WAGE_FLOOR, WAGE_MAX))
    cap = await max_hours_at(ctx.session, contract.settlement_entity_id) if contract.settlement_entity_id is not None else None
    hours = CUSTOMARY_HOURS - max(0, gap) // HOURS_PER_STRENGTH - (boost // HOURS_PER_STRENGTH if "hours" in asked else 0)
    setting(contract, "hours", clamp_int(min(hours, cap) if cap is not None else hours, 0, HOURS_MAX))
    for field in CONDITION_TERMS:
        setting(contract, field, clamp_int(CUSTOMARY_TERM + gap // 2 + (boost if field in asked else 0), 0, PERCENT))
    setting(contract, "status", ContractStatus.AGREED)
    setting(contract, "started_epoch", ctx.epoch)
    place = await place_of(ctx.session, contract.settlement_entity_id, contract.body_node_id, contract.hirer_node_id)
    await record(
        ctx,
        "labour.contract_agreed",
        roles={IncidentRole.ACTOR: contract.body_node_id or contract.worker_node_id, IncidentRole.CO_ACTOR: contract.hirer_node_id, IncidentRole.PLACE: place},
        facts={"trade": contract.trade, "wage": contract.wage, "hours": contract.hours},
        place=place,
    )


def term_score(contract: LabourContractRow) -> int:
    return (min(contract.wage, 2 * CUSTOMARY_WAGE) // 2 + contract.safety + contract.rest + contract.keep) // 4


async def break_contract(ctx: TickContext, contract: LabourContractRow, why: str) -> None:
    setting(contract, "status", ContractStatus.BROKEN)
    place = await place_of(ctx.session, contract.settlement_entity_id, contract.hirer_node_id, contract.body_node_id)
    await record(
        ctx,
        "labour.contract_broken",
        roles={
            IncidentRole.ACTOR: contract.hirer_node_id,
            IncidentRole.VICTIM: contract.body_node_id or contract.worker_node_id,
            IncidentRole.PLACE: place,
        },
        facts={"trade": contract.trade, "why": why},
        place=place,
    )


async def tend_contract(ctx: TickContext, contract: LabourContractRow, tally: LabourTally) -> None:
    parties = [contract.hirer_node_id, contract.body_node_id, contract.worker_node_id, contract.settlement_entity_id]
    if contract.status is not ContractStatus.AGREED or any(held(node) for node in parties if node is not None) or "status" in (contract.locked or []):
        return
    if ctx.epoch - contract.started_epoch >= contract.term_epochs:
        contract.status = ContractStatus.EXPIRED
        tally.expired += 1
        return
    hirer = await living_entity(ctx.session, contract.hirer_node_id)
    if hirer is None:
        await break_contract(ctx, contract, "the hirer is gone")
        tally.broken += 1
        return
    body = await ctx.session.get(WorkerBodyRow, contract.body_node_id) if contract.body_node_id is not None else None
    members = body.members if body is not None else 1
    cost = round_half_up(members * max(0, contract.wage - CUSTOMARY_WAGE) / PERCENT)
    if cost and not await take_coin(ctx.session, ctx.rules, hirer, cost):
        await break_contract(ctx, contract, "the hirer could not pay the agreed wage")
        tally.broken += 1
        return
    if contract.settlement_entity_id is not None:
        swing = round_half_up((term_score(contract) - PERCENT / 2) / (PERCENT / 2) * ctx.rules.labour.satisfaction_per_term)
        await shift_contentment(ctx, contract.settlement_entity_id, contract.trade, swing)
