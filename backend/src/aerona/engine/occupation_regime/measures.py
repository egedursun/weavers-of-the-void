from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.military import CaptiveCohortRow, OccupationRow
from aerona.db.tables.occupation_regimes import OccupationMeasureRow, OccupationRegimeRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.occupation_regimes import CollaborationKind, OccupationMeasure
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import held_coin
from aerona.engine.military.occupation import pay_occupier
from aerona.engine.mind.memories import remember
from aerona.engine.occupation_regime.book import RegimeTally, locals_of, occupation_of, towns_of
from aerona.engine.occupation_regime.effects import active_measures, serving
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import record

M = OccupationMeasure
GRIEVANCE_WEIGHT = total(
    OccupationMeasure,
    {
        M.CURFEW: 40,
        M.HOSTAGES: 80,
        M.COLLECTIVE_PUNISHMENT: 100,
        M.DEPORTATION: 100,
        M.REQUISITION: 60,
        M.BAN_ON_GATHERING: 40,
        M.AMNESTY_OFFER: -100,
    },
)
ATROCITY = total(
    OccupationMeasure,
    {
        M.CURFEW: None,
        M.HOSTAGES: MemoryKind.FOUGHT_US,
        M.COLLECTIVE_PUNISHMENT: MemoryKind.KILLED_KIN,
        M.DEPORTATION: MemoryKind.KILLED_KIN,
        M.REQUISITION: None,
        M.BAN_ON_GATHERING: None,
        M.AMNESTY_OFFER: None,
    },
)
ENFORCERS = frozenset({CollaborationKind.POLICE, CollaborationKind.MILITIA})


async def deport(ctx: TickContext, regime: OccupationRegimeRow, strength: int, tally: RegimeTally) -> None:
    for town in await towns_of(ctx, regime):
        if held(town.id):
            continue
        carried = round_half_up((stat(town, "population") or 0) * ctx.rules.occupation.deport_pct / PERCENT * strength / PERCENT)
        if carried <= 0:
            continue
        shift_stat(town, "population", -carried)
        ctx.session.add(CaptiveCohortRow(captor_entity_id=regime.occupier_entity_id, origin_entity_id=town.id, count=carried, since_epoch=ctx.epoch, locked=[]))
        tally.deported += carried
        await record(
            ctx, "occupation.deportation", roles={IncidentRole.ACTOR: regime.occupier_entity_id, IncidentRole.VICTIM: town.id}, facts={"carried": carried}
        )


async def requisition(ctx: TickContext, regime: OccupationRegimeRow, strength: int) -> None:
    for town in await towns_of(ctx, regime):
        profile = await ctx.session.get(SettlementProfileRow, town.id)
        if profile is None or held(town.id) or "treasury" in (profile.locked or []):
            continue
        taken = held_coin(profile.treasury) * ctx.rules.occupation.requisition_pct * strength // (PERCENT * PERCENT)
        if taken > 0:
            profile.treasury -= taken
            await pay_occupier(ctx, regime.occupier_entity_id, taken)


async def grieve(ctx: TickContext, regime: OccupationRegimeRow, occupation: OccupationRow, measure: OccupationMeasure, strength: int) -> None:
    if "resistance" not in (occupation.locked or []):
        shift = GRIEVANCE_WEIGHT[measure] * ctx.rules.occupation.measure_grievance * strength // (PERCENT * PERCENT)
        occupation.resistance = clamp_int(occupation.resistance + shift, 0, PERCENT)
    kind = ATROCITY[measure]
    if kind is None:
        return
    for community in await locals_of(ctx, regime):
        await remember(ctx.session, ctx.rules, holder_id=community.id, subject_id=regime.occupier_entity_id, kind=kind, magnitude=-strength, epoch=ctx.epoch)
    for row in await serving(ctx.session, regime.id):
        if row.kind in ENFORCERS:
            await record(
                ctx,
                "occupation.oppression_enforced",
                roles={IncidentRole.ACTOR: row.collaborator_node_id, IncidentRole.SUBJECT: regime.region_entity_id},
                facts={"measure": measure},
            )


async def impose(
    ctx: TickContext, regime: OccupationRegimeRow, measure: OccupationMeasure, strength: int, tally: RegimeTally, *, by: int | None = None
) -> OccupationMeasureRow:
    strength = clamp_int(strength, 0, PERCENT)
    row = OccupationMeasureRow(regime_id=regime.id, region_entity_id=regime.region_entity_id, measure=measure, strength=strength, epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    tally.measures += 1
    await record(
        ctx,
        "occupation.measure_imposed",
        roles={IncidentRole.ACTOR: by or regime.occupier_entity_id, IncidentRole.SUBJECT: regime.region_entity_id},
        facts={"measure": measure, "strength": strength},
    )
    occupation = await occupation_of(ctx, regime)
    if occupation is not None:
        await grieve(ctx, regime, occupation, measure, strength)
    if measure is OccupationMeasure.DEPORTATION:
        await deport(ctx, regime, strength, tally)
    elif measure is OccupationMeasure.REQUISITION:
        await requisition(ctx, regime, strength)
    return row


async def tend_measures(ctx: TickContext, regime: OccupationRegimeRow, resistance: int, tally: RegimeTally) -> None:
    for row in await active_measures(ctx.session, regime.id):
        if "strength" in (row.locked or []) or row.epoch == ctx.epoch:
            continue
        row.strength = clamp_int(row.strength - ctx.rules.occupation.measure_decay, 0, PERCENT)
        if not row.strength:
            row.ended_epoch = ctx.epoch
    if ctx.rng(f"occupation.measure.{regime.id}.{ctx.epoch}").chance(ctx.rules.occupation.measure_chance_pct * resistance / PERCENT):
        measure = ctx.rng(f"occupation.measure.kind.{regime.id}.{ctx.epoch}").pick(list(OccupationMeasure))
        await impose(ctx, regime, measure, resistance, tally)
