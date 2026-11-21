from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.reckoning import ReckoningRow
from aerona.db.write_guard import held
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.reckoning import HARSH_MEASURES, MeasureStage
from aerona.engine.context import TickContext
from aerona.engine.departures.leave import exile
from aerona.engine.phases.factions import found_faction
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.reckoning.book import ReckoningTally, measures_of, realm_of, servants
from aerona.engine.reckoning.measures import APPLY, victims_grieve
from aerona.engine.reckoning.opening import after_coups, apply_legacy
from aerona.engine.recording.record import record
from aerona.engine.services.war import declare_war


async def rise(ctx: TickContext, row: ReckoningRow, tally: ReckoningTally) -> None:
    realm = await realm_of(ctx.session, row)
    capital = await ctx.session.get(EntityRow, realm.capital_entity_id) if realm is not None and realm.capital_entity_id is not None else None
    old = await servants(ctx.session, row)
    if capital is None or not old or held(capital.id):
        return
    rebels = await found_faction(ctx, capital, FactionKind.REBELS)
    for holder, _office in old:
        ctx.session.add(
            FactionMembershipRow(faction_entity_id=rebels.id, mortal_entity_id=holder.id, rank=FactionRank.MEMBER, joined_epoch=ctx.epoch, locked=[])
        )
    if realm is not None and realm.core_entity_id is not None:
        await declare_war(ctx, rebels.id, realm.core_entity_id, "the servants of the fallen regime rose against the reckoning", world_cap=False)
    tally.revolts += 1


async def weigh_harshness(ctx: TickContext, row: ReckoningRow, tally: ReckoningTally) -> None:
    table = ctx.rules.reckoning
    active = await measures_of(ctx.session, row.id, MeasureStage.ACTIVE)
    harshness = sum(measure.strength for measure in active if measure.measure in HARSH_MEASURES)
    if harshness >= table.harsh_from:
        if ctx.rng(f"reckoning.revolt.{row.id}.{ctx.epoch}").chance(table.harsh_revolt_chance_pct):
            await rise(ctx, row, tally)
        for holder, _office in await servants(ctx.session, row):
            fleeing = not held(holder.id) and ctx.rng(f"reckoning.flight.{row.id}.{holder.id}.{ctx.epoch}").chance(table.flight_chance_pct)
            if fleeing and await exile(ctx, holder, row.polity_entity_id) is not None:
                tally.fled += 1
    elif active and harshness <= table.weak_below:
        await victims_grieve(ctx, row, table.weak_unrest)
    if "resistance" not in (row.locked or []):
        row.resistance = clamp_int(len(await servants(ctx.session, row)) * table.servant_resistance, 0, PERCENT)


async def tend_reckoning(ctx: TickContext, row: ReckoningRow, tally: ReckoningTally) -> None:
    for measure in await measures_of(ctx.session, row.id):
        if "stage" in (measure.locked or []) or measure.stage is MeasureStage.DONE:
            continue
        if measure.stage is MeasureStage.PLANNED:
            measure.stage, measure.started_epoch = MeasureStage.ACTIVE, ctx.epoch
        await APPLY[measure.measure](ctx, row, measure, tally)
        if ctx.epoch - measure.started_epoch + 1 >= ctx.rules.reckoning.measure_epochs:
            measure.stage = MeasureStage.DONE
            realm = await realm_of(ctx.session, row)
            if measure.admin_taken and realm is not None and "administration" not in (realm.locked or []):
                realm.administration += measure.admin_taken
                measure.admin_taken = 0
    await weigh_harshness(ctx, row, tally)
    if not await measures_of(ctx.session, row.id, MeasureStage.PLANNED) and not await measures_of(ctx.session, row.id, MeasureStage.ACTIVE):
        row.closed_epoch = ctx.epoch
        tally.closed += 1
        await record(
            ctx,
            "reckoning.closed",
            roles={IncidentRole.SUBJECT: row.polity_entity_id, IncidentRole.PREDECESSOR: row.fallen_node_id},
            facts={"resistance": row.resistance},
        )


async def tend_reckonings(ctx: TickContext) -> ReckoningTally:
    tally = ReckoningTally()
    await apply_legacy(ctx, tally)
    await after_coups(ctx, tally)
    for row in list(await ctx.session.scalars(select(ReckoningRow).where(ReckoningRow.closed_epoch.is_(None)).order_by(ReckoningRow.id))):
        if held(row.polity_entity_id) or "closed_epoch" in (row.locked or []):
            continue
        await tend_reckoning(ctx, row, tally)
    return tally
