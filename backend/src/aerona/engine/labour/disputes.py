from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.labour import ACT_HIRER_COST_PCT, ACT_PAID_PCT
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.labour import LabourDisputeRow, WorkerBodyRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.labour import DisputeAct, DisputeOutcome, LabourDemand
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.labour.bodies import LabourTally, Parties, place_of
from aerona.engine.labour.contracts import agree, contract_for
from aerona.engine.labour.hirers import substitutes_pct
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

OUTCOME_LOCK = "outcome"
STRIKEBREAKER_DAMAGE = 3.0
BEGUN_KIND = {DisputeAct.LOCKOUT: "labour.lockout_begun"}
WON_GAP = 20
LOST_MEMBERS_PCT = 70


async def dispute_between(session: AsyncSession, body_id: int, hirer_id: int) -> LabourDisputeRow | None:
    query = select(LabourDisputeRow).where(
        LabourDisputeRow.body_node_id == body_id, LabourDisputeRow.hirer_node_id == hirer_id, LabourDisputeRow.outcome == DisputeOutcome.ONGOING
    )
    return await session.scalar(query.order_by(LabourDisputeRow.id).limit(1))


async def open_dispute(ctx: TickContext, parties: Parties, act: DisputeAct, demand: LabourDemand, tally: LabourTally) -> LabourDisputeRow:
    body, hirer, community, trade = parties.body, parties.hirer, parties.community, parties.trade
    found = await dispute_between(ctx.session, body.faction_node_id, hirer.id)
    if found is not None:
        return found
    dispute = LabourDisputeRow(
        name=f"the {spoken(act)} at {community.name}",
        body_node_id=body.faction_node_id,
        hirer_node_id=hirer.id,
        settlement_entity_id=community.id,
        trade=trade,
        demand=demand,
        act=act,
        workers_out=body.members,
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(dispute)
    await ctx.session.flush()
    if act is DisputeAct.LOCKOUT:
        tally.lockouts += 1
    else:
        tally.strikes += 1
    await record(
        ctx,
        BEGUN_KIND.get(act, "labour.strike_begun"),
        roles={
            IncidentRole.ACTOR: hirer.id if act is DisputeAct.LOCKOUT else body.faction_node_id,
            IncidentRole.TARGET: body.faction_node_id if act is DisputeAct.LOCKOUT else hirer.id,
            IncidentRole.PLACE: community.id,
        },
        facts={"act": act, "demand": demand, "trade": trade, "workers": dispute.workers_out},
        place=community.id,
    )
    return dispute


async def bring_strikebreakers(ctx: TickContext, dispute: LabourDisputeRow) -> None:
    table = ctx.rules.labour
    dispute.strikebreakers = True
    dispute.workers_out //= 2
    hurt = 0
    query = (
        select(EntityRow)
        .join(FactionMembershipRow, FactionMembershipRow.mortal_entity_id == EntityRow.id)
        .where(FactionMembershipRow.faction_entity_id == dispute.body_node_id, EntityRow.status == EntityStatus.CANON)
    )
    for member in await ctx.session.scalars(query.order_by(EntityRow.id).limit(table.strikebreaker_hits)):
        harm = Harm(STRIKEBREAKER_DAMAGE, HarmCause.PUNISHMENT, f"beaten by strikebreakers in {dispute.name}", killer_id=dispute.hirer_node_id)
        wound = await apply_hits(ctx, member, harm, lethal=False)
        hurt += 1 if wound.outcome is not None else 0
    dispute.injured += hurt
    place = await place_of(ctx.session, dispute.settlement_entity_id, dispute.body_node_id, dispute.hirer_node_id)
    await record(
        ctx,
        "labour.strikebreakers_used",
        roles={IncidentRole.ACTOR: dispute.hirer_node_id, IncidentRole.TARGET: dispute.body_node_id, IncidentRole.PLACE: place},
        facts={"injured": hurt, "workers": dispute.workers_out},
        place=place,
    )


async def end_dispute(ctx: TickContext, dispute: LabourDisputeRow, outcome: DisputeOutcome, tally: LabourTally) -> None:
    dispute.outcome, dispute.ended_epoch = outcome, ctx.epoch
    tally.ended += 1
    body = await ctx.session.get(WorkerBodyRow, dispute.body_node_id) if dispute.body_node_id is not None else None
    locked = body.locked or [] if body is not None else []
    won = outcome is DisputeOutcome.WON
    if body is not None and outcome is not DisputeOutcome.SETTLED:
        swing = ctx.rules.labour.solidarity_won if won else -ctx.rules.labour.solidarity_won
        if "solidarity" not in locked:
            body.solidarity = clamp_int(body.solidarity + swing, 0, PERCENT)
        if not won and "members" not in locked:
            body.members = round_half_up(body.members * LOST_MEMBERS_PCT / PERCENT)
    if body is not None and dispute.hirer_node_id is not None:
        contract = await contract_for(ctx, body.faction_node_id, dispute.hirer_node_id, dispute.trade)
        if contract is not None:
            await agree(ctx, contract, WON_GAP if won else (0 if outcome is DisputeOutcome.SETTLED else -WON_GAP), [dispute.demand] if won else [])
    place = await place_of(ctx.session, dispute.settlement_entity_id, dispute.body_node_id, dispute.hirer_node_id)
    await record(
        ctx,
        "labour.dispute_ended",
        roles={IncidentRole.SUBJECT: dispute.body_node_id, IncidentRole.OPPONENT: dispute.hirer_node_id, IncidentRole.PLACE: place},
        facts={"act": dispute.act, "outcome": outcome, "body_losses": dispute.body_losses, "hirer_losses": dispute.hirer_losses},
        place=place,
    )


async def tend_dispute(ctx: TickContext, dispute: LabourDisputeRow, tally: LabourTally) -> DisputeOutcome | None:
    table = ctx.rules.labour
    parties = [dispute.body_node_id, dispute.hirer_node_id, dispute.settlement_entity_id]
    if OUTCOME_LOCK in (dispute.locked or []) or any(held(node) for node in parties if node is not None):
        return None
    body = await ctx.session.get(WorkerBodyRow, dispute.body_node_id) if dispute.body_node_id is not None else None
    hirer = await living_entity(ctx.session, dispute.hirer_node_id)
    if body is None or hirer is None:
        await end_dispute(ctx, dispute, DisputeOutcome.SETTLED, tally)
        return DisputeOutcome.SETTLED
    pay = round_half_up(dispute.workers_out * table.strike_pay * ACT_PAID_PCT[dispute.act] / PERCENT)
    if pay > body.fund:
        await end_dispute(ctx, dispute, DisputeOutcome.LOST, tally)
        return DisputeOutcome.LOST
    if "fund" not in (body.locked or []):
        body.fund -= pay
    dispute.body_losses += pay
    cost = round_half_up(dispute.workers_out * table.lockout_cost_pct / PERCENT * ACT_HIRER_COST_PCT[dispute.act] / PERCENT)
    if cost and not await take_coin(ctx.session, ctx.rules, hirer, cost):
        await end_dispute(ctx, dispute, DisputeOutcome.WON, tally)
        return DisputeOutcome.WON
    dispute.hirer_losses += cost
    walkout = dispute.act in {DisputeAct.STRIKE, DisputeAct.OCCUPATION_OF_WORKS}
    town = dispute.settlement_entity_id
    if walkout and not dispute.strikebreakers and town is not None and await substitutes_pct(ctx.session, town) >= table.strikebreaker_substitutes_pct:
        await bring_strikebreakers(ctx, dispute)
    if ctx.epoch - dispute.started_epoch >= table.dispute_max_epochs:
        await end_dispute(ctx, dispute, DisputeOutcome.SETTLED, tally)
        return DisputeOutcome.SETTLED
    return None
