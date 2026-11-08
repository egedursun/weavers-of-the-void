from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.constants.engine import SURVIVAL_STORY_CHANCE
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import HERO_ROLES, EntityFlag, EntityOrigin, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.models.entity_stats import LegendStats
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.gods.stats import Trait, add_trait, trait_or
from aerona.engine.gods.worship import worships_creator
from aerona.engine.lifecycle.wounds import slay
from aerona.engine.primitives.faith import patron_son
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import has_flag
from aerona.rules.registry import Rules

NOTABLE_ROLES = frozenset(HERO_ROLES | {MortalRole.RULER})
UNKILLABLE_FLAGS = (EntityFlag.IMMORTAL,)


class ProtectorKind(StrEnum):
    PATRON = "patron"
    CREATOR = "creator"
    PROTECTED = "protected"
    CHOSEN = "chosen"
    ITEM = "item"


@dataclass(frozen=True)
class Protector:
    kind: ProtectorKind
    name: str | None = None
    node_id: int | None = None


@dataclass(frozen=True)
class KillChance:
    percent: int
    importance: int
    protectors: tuple[Protector, ...] = ()


@dataclass(frozen=True)
class Killer:
    kind: ActorKind
    name: str
    node_id: int | None = None
    might: int = 0


@dataclass(frozen=True)
class KillOutcome:
    success: bool
    text: str
    percent: int
    legend_id: int | None = None
    immortal: bool = False
    extra_ids: tuple[int, ...] = field(default=())


def importance_of(victim: EntityRow) -> int:
    return victim.importance or 0


async def is_notable_mortal(session: AsyncSession, victim: EntityRow) -> bool:
    if victim.mortal_role in NOTABLE_ROLES or victim.title:
        return True
    if await has_flag(session, victim.id, EntityFlag.CHOSEN):
        return True
    return bool(await BondRepository(session).outgoing(victim.id, BondKind.RULES))


async def kill_cost(session: AsyncSession, rules: Rules, victim: EntityRow) -> int:
    death = rules.death
    notable = death.take_life_notable_surcharge if await is_notable_mortal(session, victim) else 0
    return round(
        death.take_life_base_cost
        + max(1, victim.power_level) * death.take_life_cost_per_power
        + importance_of(victim) / death.take_life_cost_importance_divisor
        + notable
    )


def failed_kill_refund(rules: Rules, cost: int) -> int:
    return round(cost * rules.death.take_life_refund_pct / PERCENT)


async def _protecting_item(session: AsyncSession, rules: Rules, victim: EntityRow) -> EntityRow | None:
    best: EntityRow | None = None
    for bond in await BondRepository(session).outgoing(victim.id, BondKind.OWNS):
        item = await session.get(EntityRow, bond.target_node_id)
        if item is None or item.entity_type is not EntityType.ITEM or item.status is not EntityStatus.CANON:
            continue
        protection = trait_or(item, Trait.PROTECTION, 0)
        if protection >= rules.death.take_life_item_protection and (best is None or protection > trait_or(best, Trait.PROTECTION, 0)):
            best = item
    return best


async def kill_chance(session: AsyncSession, rules: Rules, victim: EntityRow, killer_son: SonRow | None = None) -> KillChance:
    death = rules.death
    importance = importance_of(victim)
    protectors: list[Protector] = []
    percent = (
        death.take_life_base_success + (killer_son.might if killer_son else 0) / death.take_life_might_divisor - importance / death.take_life_importance_resist
    )
    patron = await patron_son(session, victim)
    devoted = await worships_creator(session, victim.id)
    if patron is not None and patron.status is not SonStatus.DEAD and (killer_son is None or patron.id != killer_son.id) and not devoted:
        percent -= death.take_life_patron_resist
        protectors.append(Protector(ProtectorKind.PATRON, patron.name, patron.id))
    if devoted:
        percent -= death.take_life_creator_resist
        protectors.append(Protector(ProtectorKind.CREATOR))
    for flag, kind in ((EntityFlag.PROTECTED, ProtectorKind.PROTECTED), (EntityFlag.CHOSEN, ProtectorKind.CHOSEN)):
        if await has_flag(session, victim.id, flag):
            percent -= death.take_life_protected_resist
            protectors.append(Protector(kind))
            break
    item = await _protecting_item(session, rules, victim)
    if item is not None:
        protectors.append(Protector(ProtectorKind.ITEM, item.name, item.id))
    return KillChance(clamp_int(percent, death.take_life_min_chance, death.take_life_max_chance), importance, tuple(protectors))


def survival_story(rng: SeededRandom, victim: str, killer: str, creator: str, chance: KillChance) -> str:
    by_kind = {protector.kind: protector for protector in chance.protectors}
    if ProtectorKind.CREATOR in by_kind and rng.chance(SURVIVAL_STORY_CHANCE):
        return god_lines.STORY_CREATOR.format(killer=killer, victim=victim, creator=creator)
    patron = by_kind.get(ProtectorKind.PATRON)
    if patron is not None and rng.chance(SURVIVAL_STORY_CHANCE):
        return god_lines.STORY_PATRON.format(patron=patron.name, victim=victim, killer=killer)
    item = by_kind.get(ProtectorKind.ITEM)
    if item is not None and rng.chance(SURVIVAL_STORY_CHANCE):
        return god_lines.STORY_ITEM.format(item=item.name, victim=victim)
    if ProtectorKind.CHOSEN in by_kind:
        return god_lines.STORY_CHOSEN.format(victim=victim)
    if ProtectorKind.PROTECTED in by_kind:
        return god_lines.STORY_PROTECTED.format(victim=victim)
    return rng.pick(god_lines.STORY_FATES).format(victim=victim, killer=killer)


async def mortal_dies(ctx: TickContext, victim: EntityRow, reason: str, killer_node_id: int | None, *, harm: HarmCause = HarmCause.GOD) -> None:
    killer = killer_node_id if killer_node_id is not None and killer_node_id != victim.id else None
    if await slay(ctx, victim, Harm(ctx.rules.casualties.wound_hp, harm, reason, killer_id=killer)):
        ctx.count("mortal_deaths")


async def _sour_relation(ctx: TickContext, killer_id: int, other_id: int | None, note: str) -> None:
    if other_id is None or other_id == killer_id:
        return
    other = await ctx.session.get(SonRow, other_id)
    if other is not None:
        await SonRepository(ctx.session).change_relation(killer_id, other_id, -ctx.rules.death.take_life_relation_loss, note)


async def attempt_kill(ctx: TickContext, victim: EntityRow, killer: Killer, creator_name: str, *, certain: bool = False, how: str = "") -> KillOutcome:
    if victim.entity_type is not EntityType.MORTAL or victim.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only a living, named mortal's life can be taken.")
    killer_son = await ctx.session.get(SonRow, killer.node_id) if killer.kind is ActorKind.SON and killer.node_id is not None else None
    chance = await kill_chance(ctx.session, ctx.rules, victim, killer_son)
    if not certain and any([await has_flag(ctx.session, victim.id, flag) for flag in UNKILLABLE_FLAGS]):
        return KillOutcome(False, god_lines.KILL_IMMORTAL.render(victim=victim.name), chance.percent, immortal=True)
    rng = ctx.rng("take_life")
    if certain or rng.chance(chance.percent):
        reason = god_lines.KILL_REASON.format(killer=killer.name, how=f" ({how})" if how else "")
        patron = await patron_son(ctx.session, victim)
        await mortal_dies(
            ctx,
            victim,
            reason,
            None if killer.kind is ActorKind.CREATOR else killer.node_id,
            harm=HarmCause.PLAYER if killer.kind is ActorKind.CREATOR else HarmCause.GOD,
        )
        if killer_son is not None:
            note = god_lines.KILL_RELATION_NOTE.format(victim=victim.name)
            await _sour_relation(ctx, killer_son.id, victim.creator_son_id, note)
            if patron is not None and patron.id != victim.creator_son_id:
                await _sour_relation(ctx, killer_son.id, patron.id, note)
        return KillOutcome(True, god_lines.KILL_DIED.render(victim=victim.name, reason=reason), chance.percent)
    story = survival_story(rng, victim.name, killer.name, creator_name, chance)
    add_trait(victim, Trait.CHARISMA, ctx.rules.death.survivor_charisma_gain)
    entities = EntityRepository(ctx.session)
    await entities.add_flag(victim.id, EntityFlag.RETURNED_FROM_DEATH, ctx.epoch)
    legend = await entities.create(
        EntityDraft(
            name=await NameRepository(ctx.session).unique_name(god_lines.LEGEND_NAME.format(victim=victim.name)),
            entity_type=EntityType.LEGEND,
            description=god_lines.LEGEND_DESCRIPTION.format(story=story),
            stats=LegendStats(spread=clamp_int(ctx.rules.death.survivor_charisma_gain, 0, PERCENT)),
            power_level=ctx.rules.death.survivor_legend_power,
            origin=EntityOrigin.ENGINE,
            birth_epoch=ctx.epoch,
            world_id=victim.world_id,
            subtype=god_lines.LEGEND_SUBTYPE,
            pending_name=True,
            split_title=False,
        )
    )
    await BondRepository(ctx.session).connect(BondDraft(legend.id, victim.id, BondKind.TELLS_OF, ctx.epoch))
    patron_protector = next((protector for protector in chance.protectors if protector.kind is ProtectorKind.PATRON), None)
    if killer_son is not None and patron_protector is not None:
        await _sour_relation(ctx, killer_son.id, patron_protector.node_id, god_lines.KILL_PROTECT_NOTE.format(victim=victim.name))
    line = god_lines.KILL_FAILED
    text = line.render(killer=killer.name, victim=victim.name, story=story)
    await ctx.chronicle(ChronicleKind.ESCAPE, text, template_key=line.key, entity_ids=[victim.id, legend.id], son_id=killer_son.id if killer_son else None)
    ctx.count("failed_kills")
    return KillOutcome(False, text, chance.percent, legend.id)
