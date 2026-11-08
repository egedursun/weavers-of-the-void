from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonDeathCause, SonStatus
from aerona.engine.context import Publisher
from aerona.engine.gods.acts import kill_mortal_by_creator
from aerona.engine.gods.devotion import (
    DevotionResult,
    RiteKind,
    SchemeKind,
    resurrection_rite,
    scatter_bones,
    sibling_scheme,
)
from aerona.engine.gods.essence import spend
from aerona.engine.gods.god_death import FadingStatus, GodDeath, creator_kills_son, fading_status, god_death, resurrect_son
from aerona.engine.gods.mortality import KillChance, Killer, KillOutcome, attempt_kill, kill_chance, kill_cost
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import living_sons
from aerona.rules.registry import Rules
from aerona.services.gods.context import record_action, require, require_creator


@dataclass(frozen=True)
class KillPrice:
    son_cost: int
    chance: KillChance
    creator_cost: int


async def kill_price(session: AsyncSession, rules: Rules, entity_id: int, son_id: int | None = None) -> KillPrice:
    victim = require(await session.get(EntityRow, entity_id), "record")
    killer = await session.get(SonRow, son_id) if son_id is not None else None
    return KillPrice(await kill_cost(session, rules, victim), await kill_chance(session, rules, victim, killer), rules.death.creator_take_life_cost)


async def take_life(session: AsyncSession, rules: Rules, entity_id: int, how: str = "", publish: Publisher | None = None) -> KillOutcome:
    ctx = await manual_context(session, "take_life", rules, publish)
    victim = require(await session.get(EntityRow, entity_id), "record")
    outcome = await kill_mortal_by_creator(ctx, await require_creator(session), victim, how.strip()[: rules.god_actions.inspiration_max_chars])
    await record_action(ctx, ActionKind.TAKE_LIFE, entity_id, rules.death.creator_take_life_cost)
    return outcome


async def kill_son(session: AsyncSession, rules: Rules, son_id: int, reason: str = "", publish: Publisher | None = None) -> GodDeath:
    ctx = await manual_context(session, "kill_son", rules, publish)
    creator = await require_creator(session)
    son = require(await session.get(SonRow, son_id), "son")
    if son.status is SonStatus.DEAD:
        raise ValidationFailedError(f"{son.name} is already dead.")
    spend(creator, rules.death.creator_kill_son_cost, "death.creator_kill_son_cost")
    death = await creator_kills_son(ctx, son, reason.strip() or None)
    await record_action(ctx, ActionKind.KILL_SON, son_id, rules.death.creator_kill_son_cost)
    return death


async def son_dies(session: AsyncSession, rules: Rules, son_id: int, cause: str, death_cause: SonDeathCause) -> GodDeath:
    ctx = await manual_context(session, "son_dies", rules)
    son = require(await session.get(SonRow, son_id), "son")
    if son.status is SonStatus.DEAD:
        raise ValidationFailedError(f"{son.name} is already dead.")
    return await god_death(ctx, son, cause, death_cause)


async def resurrect(session: AsyncSession, rules: Rules, son_id: int, publish: Publisher | None = None) -> SonRow:
    ctx = await manual_context(session, "resurrect_son", rules, publish)
    creator = await require_creator(session)
    son = require(await session.get(SonRow, son_id), "son")
    if son.status is not SonStatus.DEAD:
        raise ValidationFailedError(f"{son.name} is not dead.")
    spend(creator, rules.balance.resurrection, "balance.resurrection")
    await resurrect_son(ctx, son, god_lines.RESURRECTION_BY_CREATOR.format(creator=creator.name))
    await record_action(ctx, ActionKind.RESURRECT_SON, son_id, rules.balance.resurrection)
    return son


async def fading_statuses(session: AsyncSession, rules: Rules) -> list[FadingStatus]:
    return [fading_status(rules, son) for son in await living_sons(session)]


async def order_rite(session: AsyncSession, rules: Rules, entity_id: int, son_id: int, kind: RiteKind, *, victim_id: int | None = None) -> DevotionResult:
    ctx = await manual_context(session, "order_rite", rules)
    worshipper = require(await session.get(EntityRow, entity_id), "record")
    son = require(await session.get(SonRow, son_id), "son")
    victim = require(await session.get(EntityRow, victim_id), "record") if victim_id is not None else None
    result = await resurrection_rite(ctx, worshipper, son, kind, victim)
    await record_action(ctx, ActionKind.RESURRECTION_RITE, entity_id)
    return result


async def order_scheme(session: AsyncSession, rules: Rules, sibling_id: int, son_id: int, kind: SchemeKind) -> DevotionResult:
    ctx = await manual_context(session, "order_scheme", rules)
    sibling = require(await session.get(SonRow, sibling_id), "son")
    son = require(await session.get(SonRow, son_id), "son")
    result = await sibling_scheme(ctx, sibling, son, kind)
    await record_action(ctx, ActionKind.SIBLING_SCHEME, sibling_id)
    return result


async def order_scatter(session: AsyncSession, rules: Rules, sibling_id: int, son_id: int) -> DevotionResult:
    ctx = await manual_context(session, "order_scatter", rules)
    sibling = require(await session.get(SonRow, sibling_id), "son")
    son = require(await session.get(SonRow, son_id), "son")
    result = await scatter_bones(ctx, sibling, son)
    await record_action(ctx, ActionKind.SCATTER_BONES, sibling_id)
    return result


async def grant_protection(session: AsyncSession, rules: Rules, entity_id: int, protected: bool = True) -> bool:
    ctx = await manual_context(session, "protect", rules)
    entity = require(await session.get(EntityRow, entity_id), "record")
    if entity.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a named mortal can be shielded from death.")
    entities = EntityRepository(session)
    changed = await entities.add_flag(entity.id, EntityFlag.PROTECTED, ctx.epoch) if protected else await entities.remove_flag(entity.id, EntityFlag.PROTECTED)
    await record_action(ctx, ActionKind.EDIT_RECORD, entity_id)
    return changed


async def order_foreign_strike(session: AsyncSession, rules: Rules, god_id: int, entity_id: int) -> KillOutcome:
    ctx = await manual_context(session, "foreign_strike", rules)
    god = require(await session.get(ForeignGodRow, god_id), "foreign god")
    if god.status is not ForeignGodStatus.AWAKE:
        raise ValidationFailedError(f"{god.name} is not awake.")
    victim = require(await session.get(EntityRow, entity_id), "record")
    if victim.world_id != god.world_id:
        raise ValidationFailedError(f"{victim.name} does not live in {god.name}'s world.")
    creator = await require_creator(session)
    return await attempt_kill(ctx, victim, Killer(ActorKind.FOREIGN_GOD, god.name, god.id), creator.name)


async def restore_existence(session: AsyncSession, rules: Rules, son_id: int, existence: int) -> SonRow:
    ctx = await manual_context(session, "restore_existence", rules)
    son = require(await session.get(SonRow, son_id), "son")
    if son.status is SonStatus.DEAD:
        raise ValidationFailedError(f"{son.name} is dead.")
    son.existence = clamp_percent(existence)
    if son.existence > rules.death.fading_threshold:
        son.fading_epochs = 0
    await record_action(ctx, ActionKind.BLESS_EXISTENCE, son_id)
    return son
