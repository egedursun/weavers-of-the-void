from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.occupation_regimes import CollaborationRow, OccupationRegimeRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.occupation_regimes import CollaborationFate, CollaborationKind
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.lifecycle.wounds import slay
from aerona.engine.occupation_regime.book import RegimeTally, locals_of
from aerona.engine.occupation_regime.effects import serving
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

PARTISAN_DEATH = "was killed by partisans for serving the occupier"
CANDIDATES = 40


async def join(ctx: TickContext, regime: OccupationRegimeRow, node_id: int, kind: CollaborationKind, tally: RegimeTally) -> CollaborationRow:
    query = select(CollaborationRow).where(
        CollaborationRow.regime_id == regime.id, CollaborationRow.collaborator_node_id == node_id, CollaborationRow.fate == CollaborationFate.SERVING
    )
    found = await ctx.session.scalar(query.limit(1))
    if found is not None:
        return found
    row = CollaborationRow(regime_id=regime.id, collaborator_node_id=node_id, kind=kind, begun_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    if kind is CollaborationKind.ADMINISTRATION and "administrators" not in (regime.locked or []):
        regime.administrators = sorted({*(regime.administrators or []), node_id})
    await ctx.session.flush()
    tally.collaborators += 1
    await record(
        ctx,
        "occupation.collaborator_joined",
        roles={IncidentRole.ACTOR: node_id, IncidentRole.TARGET: regime.occupier_entity_id, IncidentRole.SUBJECT: regime.region_entity_id},
        facts={"kind": kind},
    )
    return row


async def recruit(ctx: TickContext, regime: OccupationRegimeRow, control: int, tally: RegimeTally) -> None:
    if not ctx.rng(f"occupation.recruit.{regime.id}.{ctx.epoch}").chance(ctx.rules.occupation.recruit_chance_pct * control / PERCENT):
        return
    taken = {row.collaborator_node_id for row in await serving(ctx.session, regime.id)}
    here = await present_among(ctx.session, [entity.id for entity in await locals_of(ctx, regime)])
    query = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, here)
    pool = [node for node in await ctx.session.scalars(query.order_by(EntityRow.id).limit(CANDIDATES)) if node not in taken and not held(node)]
    chosen = ctx.rng(f"occupation.recruit.who.{regime.id}.{ctx.epoch}").pick_or_none(pool)
    if chosen is not None:
        kind = ctx.rng(f"occupation.recruit.kind.{regime.id}.{ctx.epoch}").pick(list(CollaborationKind))
        await join(ctx, regime, chosen, kind, tally)


async def end_service(ctx: TickContext, row: CollaborationRow, fate: CollaborationFate) -> None:
    if "fate" not in (row.locked or []):
        row.fate, row.ended_epoch = fate, ctx.epoch


async def tend_collaborators(ctx: TickContext, regime: OccupationRegimeRow, resistance: int, tally: RegimeTally) -> None:
    table = ctx.rules.occupation
    occupier = await living_entity(ctx.session, regime.occupier_entity_id)
    for row in await serving(ctx.session, regime.id):
        node = await living_entity(ctx.session, row.collaborator_node_id)
        if node is None:
            await end_service(ctx, row, CollaborationFate.ENDED)
            continue
        if held(node.id):
            continue
        if occupier is not None and row.reward and await take_coin(ctx.session, ctx.rules, occupier, row.reward):
            await give_coin(ctx.session, ctx.rules, node, row.reward)
        if "exposure" not in (row.locked or []):
            row.exposure = clamp_int(row.exposure + table.exposure_gain * resistance // PERCENT, 0, PERCENT)
        doomed = ctx.rng(f"occupation.exposed.{row.id}.{ctx.epoch}").chance(table.exposure_kill_pct * row.exposure / PERCENT)
        if (
            doomed
            and node.entity_type is EntityType.MORTAL
            and await slay(ctx, node, Harm(ctx.rules.casualties.wound_hp, HarmCause.PUNISHMENT, PARTISAN_DEATH))
        ):
            await end_service(ctx, row, CollaborationFate.KILLED)
            tally.killed += 1
            await record(
                ctx,
                "occupation.collaborator_killed",
                roles={IncidentRole.VICTIM: node.id, IncidentRole.SUBJECT: regime.region_entity_id},
                facts={"kind": row.kind, "exposure": row.exposure},
            )
