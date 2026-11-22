from dataclasses import dataclass

from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.dominion import DivineCreatureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.intervention import Miracle
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.divine.avatars import avatars_of, manifest
from aerona.engine.divine.gods import domains_of
from aerona.engine.dominion.creatures import raise_creature
from aerona.engine.dominion.miracles import MIRACLE_DOMAINS, impress, witness_count
from aerona.engine.gods.interventions import apply_miracle
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.recording.record import record


@dataclass
class OldGodTally:
    miracles: int = 0
    avatars: int = 0
    creatures: int = 0


def miracle_for(god: ForeignGodRow) -> Miracle | None:
    domains = set(domains_of(god))
    return next((miracle for miracle in Miracle if MIRACLE_DOMAINS.get(miracle, frozenset()) & domains), None)


async def flock_of(ctx: TickContext, god: ForeignGodRow) -> EntityRow | None:
    worshippers = select(BondRow.source_node_id).where(BondRow.target_node_id == god.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    query = select(EntityRow).where(EntityRow.id.in_(worshippers), EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON)
    return await ctx.session.scalar(query.order_by(EntityRow.id).limit(1))


async def unbelievers_near(ctx: TickContext, god: ForeignGodRow) -> EntityRow | None:
    worshippers = select(BondRow.source_node_id).where(BondRow.target_node_id == god.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    query = select(EntityRow).where(
        EntityRow.world_id == god.world_id,
        EntityRow.entity_type.in_(list(COMMUNITY_TYPES)),
        EntityRow.status == EntityStatus.CANON,
        EntityRow.id.not_in(worshippers),
    )
    return await ctx.session.scalar(query.order_by(EntityRow.id).limit(1))


async def work_miracle(ctx: TickContext, god: ForeignGodRow, flock: EntityRow, kind: Miracle) -> None:
    await apply_miracle(ctx, flock, kind, f"a miracle of {god.name}")
    witnesses = await witness_count(ctx, flock)
    await impress(ctx, god.id, flock, kind=kind.value, magnitude=god.power, witnesses=witnesses)
    await record(
        ctx, "divine.old_god_miracle", roles={IncidentRole.ACTOR: god.id, IncidentRole.TARGET: flock.id}, facts={"miracle": kind, "witnesses": witnesses}
    )


async def walk_among(ctx: TickContext, god: ForeignGodRow) -> bool:
    place = await unbelievers_near(ctx, god)
    if place is None or held(place.id) or await avatars_of(ctx, god.id):
        return False
    try:
        await manifest(ctx, god, place)
    except ValidationFailedError:
        return False
    return True


async def raise_for(ctx: TickContext, god: ForeignGodRow, flock: EntityRow) -> bool:
    if await ctx.session.scalar(select(DivineCreatureRow.creature_entity_id).where(DivineCreatureRow.god_node_id == god.id).limit(1)) is not None:
        return False
    home = (await RegionAtlas.load(ctx.session)).top_region(flock.id)
    if home is None or held(home):
        return False
    row = await raise_creature(ctx, god.id, name=f"The Creature of {god.name}", description=f"Raised by {god.name} among {flock.name}.", home_id=home)
    await record(ctx, "divine.old_god_creature", roles={IncidentRole.ACTOR: god.id, IncidentRole.SUBJECT: row.creature_entity_id, IncidentRole.PLACE: home})
    return True


async def old_gods_act(ctx: TickContext) -> OldGodTally:
    table = ctx.rules.foreign_gods
    tally = OldGodTally()
    awake = select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id)
    for god in list(await ctx.session.scalars(awake)):
        flock = await flock_of(ctx, god)
        if held(god.id) or flock is None or held(flock.id):
            continue
        kind = miracle_for(god)
        if kind is not None and ctx.rng(f"old_god.miracle.{god.id}.{ctx.epoch}").chance(table.miracle_pct):
            await work_miracle(ctx, god, flock, kind)
            tally.miracles += 1
        if ctx.rng(f"old_god.avatar.{god.id}.{ctx.epoch}").chance(table.avatar_pct) and await walk_among(ctx, god):
            tally.avatars += 1
        if ctx.rng(f"old_god.creature.{god.id}.{ctx.epoch}").chance(table.creature_pct) and await raise_for(ctx, god, flock):
            tally.creatures += 1
    return tally
