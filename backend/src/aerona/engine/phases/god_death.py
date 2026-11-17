import logging

from sqlalchemy import select

from aerona.catalog import god_lines
from aerona.constants.units import PERCENT
from aerona.core.errors import AeronaError
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.gods.devotion import (
    BLOOD_TYPES,
    RiteKind,
    SchemeKind,
    awake_foreign_gods,
    can_afford_offering,
    hinder_return,
    resurrection_rite,
    resurrection_state,
    scheme_cost,
    sibling_scheme,
    worships_node,
)
from aerona.engine.gods.god_death import gods_fate
from aerona.engine.gods.mortality import Killer, attempt_kill
from aerona.engine.gods.queries import creator_row, sons
from aerona.engine.gods.stats import Trait, trait_or
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase

logger = logging.getLogger(__name__)
SCHEME_PREFERENCE = (SchemeKind.DESCENT, SchemeKind.RITE, SchemeKind.BARGAIN)


async def _faithful_rites(ctx: TickContext, son: SonRow) -> None:
    rules = ctx.rules.death
    rng = ctx.rng(f"rites.{son.id}")
    state = await resurrection_state(ctx.session, ctx.rules, son, ctx.epoch)
    if state is None:
        return
    for community in unheld(state.faithful):
        try:
            async with ctx.session.begin_nested():
                if rng.chance(rules.sacrifice_chance) and community.entity_type in BLOOD_TYPES:
                    await resurrection_rite(ctx, community, son, RiteKind.BLOOD)
                elif rng.chance(rules.rite_chance):
                    kind = RiteKind.RITE if can_afford_offering(ctx.rules, community) else RiteKind.PRAYER
                    await resurrection_rite(ctx, community, son, kind)
        except AeronaError as error:
            logger.debug("Rite skipped for community %s: %s", community.id, error)


async def _sibling_moves(ctx: TickContext, son: SonRow, active: list[SonRow]) -> None:
    rules = ctx.rules.death
    if rules.sibling_intrigues_per_epoch <= 0:
        return
    rng = ctx.rng(f"siblings.{son.id}")
    relations = SonRepository(ctx.session)
    has_foreign = bool(await awake_foreign_gods(ctx.session))
    for sibling in active:
        if sibling.id == son.id or sibling.status is not SonStatus.ACTIVE or held(sibling.id, son.id):
            continue
        relation = await relations.relation(sibling.id, son.id)
        try:
            async with ctx.session.begin_nested():
                if relation >= rules.auto_intrigue_min_relation and rng.chance(rules.auto_intrigue_chance):
                    budget = sibling.essence * rules.auto_intrigue_essence_share / PERCENT
                    options = [kind for kind in SCHEME_PREFERENCE if kind is not SchemeKind.BARGAIN or has_foreign]
                    kind = next((option for option in options if scheme_cost(ctx.rules, option) <= budget), None)
                    if kind is not None:
                        await sibling_scheme(ctx, sibling, son, kind)
                elif relation <= -rules.auto_hinder_relation and sibling.essence >= rules.hinder_return_cost:
                    state = await resurrection_state(ctx.session, ctx.rules, son, ctx.epoch)
                    if state is not None and state.devotion > 0 and rng.chance(rules.auto_hinder_chance):
                        await hinder_return(ctx, sibling, son)
        except AeronaError as error:
            logger.debug("Sibling move skipped for son %s: %s", sibling.id, error)


async def _foreign_strikes(ctx: TickContext) -> None:
    rules = ctx.rules.death
    if rules.foreign_god_smite_chance <= 0:
        return
    rng = ctx.rng("foreign_strike")
    creator = await creator_row(ctx.session)
    for god in unheld(await awake_foreign_gods(ctx.session)):
        if not rng.chance(rules.foreign_god_smite_chance):
            continue
        statement = select(EntityRow).where(
            EntityRow.world_id == god.world_id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
        )
        mortals = [
            mortal for mortal in unheld(await ctx.session.scalars(statement.order_by(EntityRow.id))) if not await worships_node(ctx.session, mortal.id, god.id)
        ]
        if not mortals:
            continue
        target = max(mortals, key=lambda mortal: (trait_or(mortal, Trait.CHARISMA, 0), -mortal.id))
        world = await ctx.session.get(WorldRow, god.world_id)
        try:
            async with ctx.session.begin_nested():
                await attempt_kill(
                    ctx,
                    target,
                    Killer(ActorKind.FOREIGN_GOD, god.name, god.id),
                    creator.name if creator else "",
                    how=god_lines.FOREIGN_STRIKE_HOW.format(world=world.name if world else ""),
                )
        except AeronaError as error:
            logger.debug("Foreign strike skipped for god %s: %s", god.id, error)


@reads("table.bonds", "table.creator", "table.entities", "table.foreign_gods", "table.nodes", "table.sons")
@writes("table.bonds", "table.chronicle", "table.entities", "table.incidents", "table.sons")
async def death_engine(ctx: TickContext) -> None:
    everyone = await sons(ctx.session)
    active = [son for son in everyone if son.status is SonStatus.ACTIVE]
    for son in everyone:
        if son.status is not SonStatus.DEAD:
            continue
        await _faithful_rites(ctx, son)
        await _sibling_moves(ctx, son, active)
    await _foreign_strikes(ctx)
    await ctx.session.flush()


PHASES = (Phase("death_engine", death_engine), Phase("gods_fate", gods_fate))
