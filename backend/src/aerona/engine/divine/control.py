from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine import (
    AvatarRow,
    BreachPointRow,
    CouncilRulingRow,
    CreatorTabooRow,
    DivineStandingRow,
    DivineWoundRow,
    GodGoalRow,
    NaturalLawProfileRow,
    OuterBeingProfileRow,
    WorldAttentionRow,
    WorldDomainHookRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.divine import CouncilMotion, DivineWoundKind, DomainHook, GoalSource, GoalState, GodGoalKind, SonPunishment, VotingRule, WoundCause
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.lifecycle_end import LifecycleState
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.context import TickContext
from aerona.engine.divine.avatars import manifest, withdraw
from aerona.engine.divine.creator import attention_row
from aerona.engine.divine.foreign import seal_pact
from aerona.engine.divine.goals import SON_ONLY, TARGET_TYPES
from aerona.engine.divine.gods import God, divine_of, god_of
from aerona.engine.divine.laws import profile_for
from aerona.engine.divine.motions import Motion
from aerona.engine.divine.outer import outer_profile
from aerona.engine.divine.rulings import enact, record
from aerona.engine.divine.standing import standing_row
from aerona.engine.divine.wounds import gather, inflict
from aerona.engine.lifecycle.states import state_of
from aerona.engine.polity.control import lock
from aerona.engine.primitives.edits import bounds, coerce
from aerona.engine.primitives.queries import living_entity


def apply[Row: Base](row: Row, values: Mapping[str, Any], release: list[str]) -> Row:
    limits = bounds(row)
    for key, value in values.items():
        setattr(row, key, coerce(row, key, value, limits))
        if hasattr(row, "locked"):
            row.locked = lock(row.locked, key)
    if hasattr(row, "locked"):
        row.locked = [item for item in row.locked if item not in release]
    return row


async def require_god(ctx: TickContext, god_id: int) -> God:
    god = await god_of(ctx.session, god_id)
    if god is None:
        raise NotFoundError("No such son or foreign god.")
    return god


async def require_world(ctx: TickContext, world_id: int) -> WorldRow:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    return world


async def set_hook(ctx: TickContext, world_id: int, domain: Domain, hook: DomainHook, pct: int) -> WorldDomainHookRow:
    await require_world(ctx, world_id)
    row = await ctx.session.get(WorldDomainHookRow, (world_id, domain, hook))
    if row is None:
        row = WorldDomainHookRow(world_id=world_id, domain=domain, hook=hook, pct=pct)
        ctx.session.add(row)
    apply(row, {"pct": pct}, [])
    await ctx.session.flush()
    return row


async def clear_hook(ctx: TickContext, world_id: int, domain: Domain, hook: DomainHook) -> None:
    row = await ctx.session.get(WorldDomainHookRow, (world_id, domain, hook))
    if row is None:
        raise NotFoundError("That world keeps the usual strength of this hook.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def check_target(ctx: TickContext, kind: GodGoalKind, target_id: int | None) -> None:
    wanted = TARGET_TYPES.get(kind)
    if wanted is None or target_id is None:
        return
    thing = await living_entity(ctx.session, target_id)
    if thing is None or thing.entity_type not in wanted:
        raise ValidationFailedError(f"That aim names one of these: {', '.join(item.value for item in wanted)}.")


async def set_goal(
    ctx: TickContext,
    god_id: int,
    kind: GodGoalKind,
    *,
    target_id: int | None = None,
    world_id: int | None = None,
    domain: Domain | None = None,
    amount: int = 0,
    source: GoalSource = GoalSource.CREATOR,
) -> GodGoalRow:
    god = await require_god(ctx, god_id)
    if kind in SON_ONLY and not isinstance(god, SonRow):
        raise ValidationFailedError(f"Only a son can aim to {kind.value.replace('_', ' ')}.")
    await check_target(ctx, kind, target_id)
    if world_id is not None:
        await require_world(ctx, world_id)
    row = GodGoalRow(
        god_node_id=god.id,
        kind=kind,
        target_node_id=target_id,
        world_id=world_id,
        domain=domain,
        amount=max(0, amount),
        progress=0,
        state=GoalState.ACTIVE,
        source=source,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def goal(ctx: TickContext, goal_id: int) -> GodGoalRow:
    row = await ctx.session.get(GodGoalRow, goal_id)
    if row is None:
        raise NotFoundError("No such aim.")
    return row


async def edit_goal(ctx: TickContext, goal_id: int, values: Mapping[str, Any], release: list[str]) -> GodGoalRow:
    row = apply(await goal(ctx, goal_id), values, release)
    if row.state is not GoalState.ACTIVE and row.closed_epoch is None:
        row.closed_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def drop_goal(ctx: TickContext, goal_id: int) -> None:
    await ctx.session.delete(await goal(ctx, goal_id))
    await ctx.session.flush()


async def set_standing(ctx: TickContext, community_id: int, god_id: int, values: Mapping[str, Any], release: list[str]) -> DivineStandingRow:
    community = await living_entity(ctx.session, community_id)
    if community is None or community.entity_type not in COMMUNITY_TYPES:
        raise NotFoundError("Only a living people, settlement or community holds a god in regard.")
    if await divine_of(ctx.session, god_id) is None:
        raise NotFoundError("No such god.")
    row = apply(await standing_row(ctx, community_id, god_id), values, release)
    row.epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def clear_standing(ctx: TickContext, community_id: int, god_id: int) -> None:
    row = await ctx.session.get(DivineStandingRow, (community_id, god_id))
    if row is None:
        raise NotFoundError("That people holds no regard of this god yet.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def wound_god(ctx: TickContext, god_id: int, kind: DivineWoundKind, severity: int, domain: Domain | None) -> DivineWoundRow:
    god = await require_god(ctx, god_id)
    row = await inflict(ctx, god, kind, WoundCause.CREATOR, severity=severity, domain=domain)
    if row is None:
        raise ValidationFailedError(f"{god.name} has no domain left to sever." if kind is DivineWoundKind.SEVERED_DOMAIN else f"{god.name} is held.")
    return row


async def wound(ctx: TickContext, wound_id: int) -> DivineWoundRow:
    row = await ctx.session.get(DivineWoundRow, wound_id)
    if row is None:
        raise NotFoundError("No such divine wound.")
    return row


async def edit_wound(ctx: TickContext, wound_id: int, values: Mapping[str, Any], release: list[str]) -> DivineWoundRow:
    row = apply(await wound(ctx, wound_id), values, release)
    await ctx.session.flush()
    if row.healed >= PERCENT:
        await gather(ctx.session, row)
        await ctx.session.flush()
    return row


async def remove_wound(ctx: TickContext, wound_id: int) -> None:
    row = await wound(ctx, wound_id)
    await gather(ctx.session, row)
    await ctx.session.delete(row)
    await ctx.session.flush()


async def manifest_avatar(ctx: TickContext, god_id: int, place_id: int) -> EntityRow:
    place = await living_entity(ctx.session, place_id)
    if place is None:
        raise NotFoundError("No such living place.")
    return await manifest(ctx, await require_god(ctx, god_id), place)


async def edit_avatar(ctx: TickContext, avatar_id: int, values: Mapping[str, Any], release: list[str]) -> AvatarRow:
    row = await ctx.session.get(AvatarRow, avatar_id)
    if row is None:
        raise NotFoundError("No such avatar.")
    apply(row, values, release)
    await ctx.session.flush()
    return row


async def withdraw_avatar(ctx: TickContext, avatar_id: int) -> None:
    await withdraw(ctx, avatar_id)


async def set_taboo(ctx: TickContext, act: ActKind, severity: int) -> CreatorTabooRow:
    row = await ctx.session.get(CreatorTabooRow, act)
    if row is None:
        creator = await ctx.session.scalar(select(CreatorRow.id).limit(1))
        if creator is None:
            raise NotFoundError("There is no Creator to hold a taboo.")
        row = CreatorTabooRow(act=act, creator_node_id=creator, severity=severity, since_epoch=ctx.epoch, broken=0)
        ctx.session.add(row)
    apply(row, {"severity": severity}, [])
    await ctx.session.flush()
    return row


async def remove_taboo(ctx: TickContext, act: ActKind) -> None:
    row = await ctx.session.get(CreatorTabooRow, act)
    if row is None:
        raise NotFoundError("The Creator holds no such taboo.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def set_attention(ctx: TickContext, world_id: int, values: Mapping[str, Any], release: list[str]) -> WorldAttentionRow:
    await require_world(ctx, world_id)
    row = apply(await attention_row(ctx, world_id), values, release)
    await ctx.session.flush()
    return row


async def clear_attention(ctx: TickContext, world_id: int) -> None:
    row = await ctx.session.get(WorldAttentionRow, world_id)
    if row is None:
        raise NotFoundError("The Creator has not yet turned its eye to that world.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def pact(ctx: TickContext, son_id: int, god_id: int, epochs: int | None) -> EntityRow:
    son = await ctx.session.get(SonRow, son_id)
    god = await ctx.session.get(ForeignGodRow, god_id)
    if son is None or god is None:
        raise NotFoundError("A divine pact binds a son and a foreign god.")
    return await seal_pact(ctx, son, god, epochs)


async def decree(
    ctx: TickContext,
    motion: CouncilMotion,
    *,
    target_id: int | None = None,
    world_id: int | None = None,
    school: MagicSchool | None = None,
    punishment: SonPunishment | None = None,
    voting_rule: VotingRule | None = None,
) -> tuple[CouncilRulingRow, list[str]]:
    if motion is CouncilMotion.NONE:
        raise ValidationFailedError("Choose a decision for the council to carry.")
    row = await record(ctx, Motion(motion, target_id, world_id, school, punishment, voting_rule), council_id=None, note_text="by the Creator's word")
    members = list(await ctx.session.scalars(select(SonRow).order_by(SonRow.id)))
    return row, await enact(ctx, row, members)


async def ruling(ctx: TickContext, ruling_id: int) -> CouncilRulingRow:
    row = await ctx.session.get(CouncilRulingRow, ruling_id)
    if row is None:
        raise NotFoundError("No such ruling.")
    return row


async def edit_ruling(ctx: TickContext, ruling_id: int, values: Mapping[str, Any], release: list[str]) -> CouncilRulingRow:
    row = apply(await ruling(ctx, ruling_id), values, release)
    await ctx.session.flush()
    return row


async def revoke_ruling(ctx: TickContext, ruling_id: int) -> None:
    await ctx.session.delete(await ruling(ctx, ruling_id))
    await ctx.session.flush()


async def edit_law(ctx: TickContext, law_id: int, values: Mapping[str, Any], release: list[str]) -> NaturalLawProfileRow:
    law = await living_entity(ctx.session, law_id)
    if law is None or law.entity_type is not EntityType.NATURAL_LAW:
        raise NotFoundError("No such living natural law.")
    if "effect" in values and (law.natural_law is None or law.natural_law is NaturalLaw.NONE):
        try:
            law.natural_law = NaturalLaw(str(values["effect"]))
        except ValueError as error:
            raise ValidationFailedError(f"{values['effect']} is not a known natural law.") from error
    row = await profile_for(ctx, law)
    if row is None:
        raise ValidationFailedError(f"{law.name} has no working yet; give it one first.")
    apply(row, values, release)
    if "effect" in values:
        law.natural_law = row.effect
    await ctx.session.flush()
    return row


async def edit_outer(ctx: TickContext, being_id: int, values: Mapping[str, Any], release: list[str]) -> OuterBeingProfileRow:
    being = await living_entity(ctx.session, being_id)
    if being is None or being.entity_type is not EntityType.OUTER_BEING:
        raise NotFoundError("No such outer being.")
    row = apply(await outer_profile(ctx, being), values, release)
    await ctx.session.flush()
    return row


async def open_breach(ctx: TickContext, being_id: int, region_id: int | None, strength: int) -> BreachPointRow:
    being = await living_entity(ctx.session, being_id)
    if being is None or being.entity_type is not EntityType.OUTER_BEING:
        raise NotFoundError("No such outer being.")
    if await state_of(ctx.session, being.id) is LifecycleState.DESTROYED:
        raise ValidationFailedError("That outer being is destroyed for good; no breach can open for it.")
    if region_id is not None:
        region = await living_entity(ctx.session, region_id)
        if region is None or region.entity_type is not EntityType.REGION:
            raise NotFoundError("A breach opens in a land.")
    row = BreachPointRow(outer_entity_id=being.id, world_id=being.world_id, region_entity_id=region_id, strength=strength, opened_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    apply(row, {"strength": strength}, [])
    await ctx.session.flush()
    return row


async def breach(ctx: TickContext, breach_id: int) -> BreachPointRow:
    row = await ctx.session.get(BreachPointRow, breach_id)
    if row is None:
        raise NotFoundError("No such breach point.")
    return row


async def edit_breach(ctx: TickContext, breach_id: int, values: Mapping[str, Any], release: list[str]) -> BreachPointRow:
    row = apply(await breach(ctx, breach_id), values, release)
    await ctx.session.flush()
    return row


async def close_breach(ctx: TickContext, breach_id: int) -> None:
    await ctx.session.delete(await breach(ctx, breach_id))
    await ctx.session.flush()
