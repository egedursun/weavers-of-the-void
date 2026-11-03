from dataclasses import dataclass
from enum import StrEnum

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import ResurrectionOrderRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.intervention import Miracle
from aerona.domain.enums.war import WarEnding
from aerona.engine.body.healing import mend, restore_body_senses
from aerona.engine.context import TickContext
from aerona.engine.gods.queries import THINKING_TYPES
from aerona.engine.gods.stats import Trait, add_trait, has_trait, set_trait, trait
from aerona.engine.phases.curses import lift_curse
from aerona.engine.phases.disasters import affected_entities
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.services.war import ongoing_wars
from aerona.engine.services.war_resolution import settle_peace


async def apply_abundance(ctx: TickContext, target: EntityRow) -> None:
    effects = ctx.rules.intervention_effects
    order = await ctx.session.get(ResurrectionOrderRow, target.id)
    if order is not None and order.completed_epoch is None and target.status is EntityStatus.CANON:
        add_trait(target, Trait.DEVOTION, effects.resurrection_cult_devotion_gain)
        devotion = trait(target, Trait.DEVOTION) or 0
        set_trait(target, Trait.DEVOTION, min(devotion, ctx.rules.death.devotion_cap))
    if has_trait(target, Trait.FERTILITY):
        add_trait(target, Trait.FERTILITY, effects.bounty_fertility_gain)
    elif has_trait(target, Trait.PROSPERITY):
        add_prosperity(ctx.rules, target, effects.bounty_prosperity_gain)
    elif has_trait(target, Trait.ABUNDANCE):
        add_trait(target, Trait.ABUNDANCE, effects.bounty_abundance_gain)
    await ctx.session.flush()


class MiracleEffect(StrEnum):
    GROWTH = "growth"
    HEALTH = "health"
    CURSE_LIFTED = "curse_lifted"
    SENSES = "senses"
    BOUNTY = "bounty"
    PEACE = "peace"
    DEFENSE = "defense"
    SHIELD = "shield"


@dataclass(frozen=True)
class MiracleOutcome:
    effects: tuple[MiracleEffect, ...]
    grown: tuple[Trait, ...] = ()
    restored: tuple[str, ...] = ()
    peace_made: int = 0


async def bump_devotion(ctx: TickContext, target: EntityRow) -> None:
    order = await ctx.session.get(ResurrectionOrderRow, target.id)
    if order is None or order.completed_epoch is not None or target.status is not EntityStatus.CANON or not has_trait(target, Trait.DEVOTION):
        return
    add_trait(target, Trait.DEVOTION, ctx.rules.intervention_effects.resurrection_cult_devotion_gain)
    set_trait(target, Trait.DEVOTION, min(trait(target, Trait.DEVOTION) or 0, ctx.rules.death.devotion_cap))


async def miracle_of_peace(ctx: TickContext, target: EntityRow, reason: str) -> int:
    others: set[int] = set()
    for bond in await BondRepository(ctx.session).touching(target.id, [BondState.ACTIVE]):
        if bond.kind is BondKind.ENEMY:
            others.add(bond.other_end(target.id))
    for war in await ongoing_wars(ctx.session, target.id):
        others.update(side for side in war.sides if side != target.id)
    for other in sorted(others):
        await settle_peace(ctx, target.id, other, WarEnding.MIRACLE, reason)
    return len(others)


async def restore_senses(ctx: TickContext, target: EntityRow) -> tuple[str, ...]:
    tools = ctx.rules.son_tools
    if tools.healing_sanity <= 0:
        return ()
    restored: list[str] = []
    for entity in await affected_entities(ctx.session, target):
        if entity.entity_type in THINKING_TYPES and entity.status is EntityStatus.CANON:
            current = entity.sanity if entity.sanity is not None else tools.default_sanity
            entity.sanity = max(0, min(PERCENT, current + tools.healing_sanity))
            if entity.entity_type is EntityType.MORTAL:
                await restore_body_senses(ctx, entity)
            restored.append(entity.name)
    return tuple(restored)


async def _healing(ctx: TickContext, target: EntityRow) -> MiracleOutcome:
    effects = ctx.rules.intervention_effects
    found: list[MiracleEffect] = []
    grown: list[Trait] = []
    for key in (Trait.POPULATION, Trait.FOLLOWERS):
        current = trait(target, key)
        if current is not None:
            set_trait(target, key, current * (1 + effects.healing_growth_pct / PERCENT))
            grown.append(key)
    if grown:
        found.append(MiracleEffect.GROWTH)
    hp = trait(target, Trait.HP)
    if target.entity_type is EntityType.MORTAL and hp is not None and hp < effects.healing_hp:
        set_trait(target, Trait.HP, effects.healing_hp)
        found.append(MiracleEffect.HEALTH)
    if target.entity_type is EntityType.MORTAL and await mend(ctx, target) and MiracleEffect.HEALTH not in found:
        found.append(MiracleEffect.HEALTH)
    if await lift_curse(ctx, target):
        found.append(MiracleEffect.CURSE_LIFTED)
    restored = await restore_senses(ctx, target)
    if restored:
        found.append(MiracleEffect.SENSES)
    return MiracleOutcome(tuple(found), grown=tuple(grown), restored=restored)


async def _protection(ctx: TickContext, target: EntityRow) -> MiracleOutcome:
    found: list[MiracleEffect] = []
    if add_trait(target, Trait.DEFENSE, ctx.rules.intervention_effects.protection_defense_gain):
        found.append(MiracleEffect.DEFENSE)
    if await EntityRepository(ctx.session).add_flag(target.id, EntityFlag.PROTECTED_FROM_DISASTER, ctx.epoch):
        found.append(MiracleEffect.SHIELD)
    return MiracleOutcome(tuple(found))


async def apply_miracle(ctx: TickContext, target: EntityRow, miracle: Miracle, peace_reason: str) -> MiracleOutcome:
    if miracle is Miracle.BOUNTY:
        await apply_abundance(ctx, target)
        return MiracleOutcome((MiracleEffect.BOUNTY,))
    if miracle is Miracle.HEALING:
        outcome = await _healing(ctx, target)
    elif miracle is Miracle.PEACE:
        made = await miracle_of_peace(ctx, target, peace_reason)
        outcome = MiracleOutcome((MiracleEffect.PEACE,) if made else (), peace_made=made)
    else:
        outcome = await _protection(ctx, target)
    await bump_devotion(ctx, target)
    await ctx.session.flush()
    return outcome
