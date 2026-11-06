from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog import god_lines
from aerona.catalog.interventions import DISASTERS
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.limits import RELATION_MIN
from aerona.domain.enums.node import ActorKind, NodeKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import Discovery
from aerona.engine.context import TickContext
from aerona.engine.gods.essence import gain, spend
from aerona.engine.gods.mortality import Killer, KillOutcome, attempt_kill
from aerona.engine.gods.queries import worship_targets
from aerona.engine.gods.stats import Trait, add_trait, headcount_floor, headcount_trait, set_trait, trait, trait_or
from aerona.engine.gods.worship import creator_node_id
from aerona.engine.phases.disasters import apply_disaster, disaster_phrase, record_disaster_event
from aerona.engine.primitives.faith import worship_creator
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon
from aerona.rules.registry import Rules

THINKING_TYPES = frozenset(COMMUNITY_TYPES | {EntityType.MORTAL})


@dataclass(frozen=True)
class KillCount:
    died: int


@dataclass(frozen=True)
class GainResult:
    gained: int
    text: str


def require_canon(entity: EntityRow | None, what: str = "This record") -> EntityRow:
    if entity is None or entity.status is not EntityStatus.CANON:
        raise ValidationFailedError(f"{what} is not in the world.")
    return entity


async def drain_mortal(ctx: TickContext, creator: CreatorRow, mortal: EntityRow, devour: bool) -> GainResult:
    rules = ctx.rules.god_power
    require_canon(mortal, "This mortal")
    if mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Life can only be drained from a named mortal.")
    life = trait_or(mortal, Trait.HP, 0)
    if devour:
        gained = gain(creator, life / rules.drain_mortal_hp_per_essence + mortal.power_level * rules.devour_mortal_essence_per_power)
        outcome = await attempt_kill(
            ctx, mortal, Killer(ActorKind.CREATOR, creator.name, creator.id), creator.name, certain=True, how=god_lines.DEVOUR_MORTAL_HOW
        )
        line = god_lines.DEVOUR_MORTAL
        text = line.render(creator=creator.name, mortal=mortal.name, gained=gained)
        await ctx.chronicle(ChronicleKind.CREATOR_HAND, text, template_key=line.key, entity_ids=[mortal.id])
        return GainResult(gained, f"{text} {outcome.text}")
    drawn = round(life * rules.drain_mortal_pct / PERCENT)
    if drawn <= 0:
        raise ValidationFailedError(f"{mortal.name} has no life to drain.")
    set_trait(mortal, Trait.HP, max(1, life - drawn))
    gained = gain(creator, drawn / rules.drain_mortal_hp_per_essence)
    await EntityRepository(ctx.session).add_flag(mortal.id, EntityFlag.ESSENCE_DRAINED, ctx.epoch)
    line = god_lines.DRAIN_MORTAL
    text = line.render(creator=creator.name, drawn=drawn, mortal=mortal.name, gained=gained)
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, text, template_key=line.key, entity_ids=[mortal.id])
    return GainResult(gained, text)


async def harvest_community(ctx: TickContext, creator: CreatorRow, community: EntityRow) -> GainResult:
    rules = ctx.rules.god_power
    require_canon(community, "This community")
    if community.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("Faith can only be harvested from a people, settlement, faction or order.")
    key = headcount_trait(community)
    victims = round(trait_or(community, key, 0) * rules.harvest_population_pct / PERCENT) if key is not None else 0
    faith_loss = min(trait_or(community, Trait.PIETY, 0), rules.harvest_piety_loss)
    if not victims and not faith_loss:
        raise ValidationFailedError(f"{community.name} carries nothing to harvest (no population and no faith).")
    if key is not None:
        set_trait(community, key, max(headcount_floor(ctx.rules, key) if victims else 0, trait_or(community, key, 0) - victims))
    add_trait(community, Trait.PIETY, -faith_loss)
    gained = gain(creator, victims / rules.harvest_victims_per_essence + faith_loss * rules.harvest_essence_per_piety)
    grudging: list[str] = []
    for node_id in await worship_targets(ctx.session, community.id):
        son = await ctx.session.get(SonRow, node_id)
        if son is not None and son.status is not SonStatus.DEAD:
            son.loyalty = clamp_percent(son.loyalty - rules.harvest_patron_loyalty_loss)
            grudging.append(son.name)
    line = god_lines.HARVEST
    text = line.render(
        creator=creator.name,
        community=community.name,
        victims=f": {victims} lives were sacrificed" if victims else "",
        faith=f", their faith dimmed by {faith_loss}" if faith_loss else "",
        gained=gained,
        grudge=f" {', '.join(grudging)} resented the reaping of their worshippers." if grudging else "",
    )
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, text, template_key=line.key, entity_ids=[community.id])
    return GainResult(gained, text)


async def foreign_god_is_immortal(ctx: TickContext, god: ForeignGodRow) -> bool:
    statement = select(ForeignGodPowerRow.slot).where(ForeignGodPowerRow.god_id == god.id, ForeignGodPowerRow.effect == ForeignGodPowerEffect.DEATHLESS)
    return await ctx.session.scalar(statement.limit(1)) is not None


def foreign_kill_cost_for(rules: Rules, power: int, immortal: bool) -> int:
    table = rules.god_power
    return round((table.kill_foreign_base_cost + power * table.kill_foreign_strength_pct / PERCENT) * (table.kill_immortal_foreign_mult if immortal else 1))


async def foreign_kill_cost(ctx: TickContext, god: ForeignGodRow) -> int:
    return foreign_kill_cost_for(ctx.rules, god.power, await foreign_god_is_immortal(ctx, god))


def foreign_drain_for(rules: Rules, power: int) -> int:
    return max(1 if power > 0 else 0, round(power * rules.god_power.drain_foreign_pct / PERCENT))


async def drain_foreign_god(ctx: TickContext, creator: CreatorRow, god: ForeignGodRow) -> GainResult:
    rules = ctx.rules.god_power
    if god.status is ForeignGodStatus.DEAD:
        raise ValidationFailedError(f"{god.name} is dead; their essence scattered long ago.")
    drawn = foreign_drain_for(ctx.rules, god.power)
    if not drawn:
        raise ValidationFailedError(f"{god.name} has no power left to drain.")
    remaining = god.power - drawn
    defeated = remaining <= 0 and god.status is not ForeignGodStatus.DEFEATED
    god.power = max(0, remaining)
    god.stance = max(RELATION_MIN, god.stance - rules.drain_foreign_attitude_loss)
    if remaining <= 0:
        god.status = ForeignGodStatus.DEFEATED
        if defeated:
            god.defeated_epoch = ctx.epoch
    gained = gain(creator, drawn * rules.foreign_essence_per_strength)
    line = god_lines.FOREIGN_DRAIN
    text = line.render(
        creator=creator.name, drawn=drawn, god=god.name, gained=gained, defeated=f"; {god.name} lost its power and fell defeated" if defeated else ""
    )
    await ctx.chronicle(ChronicleKind.FOREIGN_GOD, text, template_key=line.key)
    return GainResult(gained, text)


async def kill_foreign_god(ctx: TickContext, creator: CreatorRow, god: ForeignGodRow, reason: str = "", devour: bool = False) -> GainResult:
    rules = ctx.rules.god_power
    if god.status is ForeignGodStatus.DEAD:
        raise ValidationFailedError(f"{god.name} is already dead.")
    spend(creator, await foreign_kill_cost(ctx, god), "god_power.kill_foreign_base_cost")
    gained = gain(creator, god.power * rules.foreign_essence_per_strength) if devour else 0
    god.status = ForeignGodStatus.DEAD
    god.power = 0 if devour else god.power
    god.death_epoch = ctx.epoch
    god.awakening_pressure = 0
    god.defeated_epoch = None
    rng = ctx.rng("foreign_worshippers")
    converted = godless = 0
    bonds = BondRepository(ctx.session)
    entities = EntityRepository(ctx.session)
    for bond in await bonds.incoming(god.id, BondKind.WORSHIPS):
        await bonds.deactivate(bond, ctx.epoch, "god died")
        worshipper = await ctx.session.get(EntityRow, bond.source_node_id)
        if worshipper is None or worshipper.status is not EntityStatus.CANON:
            continue
        vow = god_lines.FOREIGN_CONVERT_VOW.format(god=god.name)
        if rng.chance(rules.foreign_worshipper_convert_pct) and await worship_creator(ctx.session, worshipper, ctx.epoch, vow):
            converted += 1
        else:
            await entities.add_flag(worshipper.id, EntityFlag.GODLESS, ctx.epoch)
            godless += 1
    line = god_lines.FOREIGN_KILL
    text = line.render(
        creator=creator.name,
        verb="devoured" if devour else "killed",
        god=god.name,
        reason=f" ({reason})" if reason else "",
        gain=f"; its power passed to the creator ({gained} essence)" if gained else "",
        converted=converted,
        godless=godless,
    )
    await ctx.chronicle(ChronicleKind.FOREIGN_GOD, text, template_key=line.key)
    return GainResult(gained, text)


def resurrect_mortal_cost(rules: Rules, mortal: EntityRow) -> int:
    return rules.god_power.resurrect_mortal_base_cost + mortal.power_level * rules.god_power.resurrect_mortal_cost_per_power


async def resurrect_mortal(ctx: TickContext, creator: CreatorRow, mortal: EntityRow) -> int:
    rules = ctx.rules.god_power
    if mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a named mortal can be resurrected.")
    if mortal.status is not EntityStatus.DEAD:
        raise ValidationFailedError(f"{mortal.name} is not dead.")
    entities = EntityRepository(ctx.session)
    if await entities.has_flag(mortal.id, EntityFlag.DEIFIED):
        raise ValidationFailedError(f"{mortal.name} lives not as a mortal but as a god.")
    cost = spend(creator, resurrect_mortal_cost(ctx.rules, mortal), "god_power.resurrect_mortal_base_cost")
    set_trait(mortal, Trait.HP, max(trait_or(mortal, Trait.HP, 0), rules.resurrect_mortal_hp))
    age = trait(mortal, Trait.AGE)
    lifespan = trait(mortal, Trait.LIFESPAN)
    if age is not None and lifespan is not None and age >= lifespan:
        set_trait(mortal, Trait.LIFESPAN, age + rules.resurrect_mortal_lifespan_years)
    mortal.status = EntityStatus.CANON
    mortal.end_epoch = None
    mortal.fate_note = (mortal.fate_note or "") + god_lines.RESURRECT_MORTAL_NOTE.format(epoch=ctx.epoch, creator=creator.name)
    await entities.add_flag(mortal.id, EntityFlag.RETURNED_FROM_DEATH, ctx.epoch)
    line = god_lines.RESURRECT_MORTAL
    await ctx.chronicle(ChronicleKind.CREATOR_HAND, line.render(creator=creator.name, mortal=mortal.name), template_key=line.key, entity_ids=[mortal.id])
    return cost


async def manifest(ctx: TickContext, creator: CreatorRow, target: EntityRow, words: str) -> bool:
    rules = ctx.rules.god_power
    require_canon(target)
    if target.entity_type not in THINKING_TYPES:
        raise ValidationFailedError("The god appears only to a mortal or a community.")
    text = words.strip()[: rules.manifest_message_max_chars]
    if not text:
        raise ValidationFailedError("Write what you will say to them.")
    spend(creator, rules.manifest_cost, "god_power.manifest_cost")
    ctx.session.add(MessageRow(epoch=ctx.epoch, sender_node_id=creator.id, recipient_node_id=target.id, intent=MessageIntent.DREAM, text=text))
    add_trait(target, Trait.PIETY, rules.manifest_piety)
    await EntityRepository(ctx.session).add_flag(target.id, EntityFlag.SAW_THE_CREATOR, ctx.epoch)
    worshipped = ctx.rng("manifest").chance(rules.manifest_worship_chance) and await worship_creator(ctx.session, target, ctx.epoch, god_lines.MANIFEST_VOW)
    line = god_lines.MANIFEST
    devotion = f" From that day {target.name} worships only {creator.name}." if worshipped else ""
    await ctx.chronicle(
        ChronicleKind.CREATOR_HAND,
        line.render(creator=creator.name, entity=target.name, words=text, worship=devotion),
        template_key=line.key,
        entity_ids=[target.id],
    )
    return worshipped


async def convert_to_creator(ctx: TickContext, creator: CreatorRow, target: EntityRow) -> list[str]:
    rules = ctx.rules.god_power
    require_canon(target)
    if target.entity_type not in THINKING_TYPES:
        raise ValidationFailedError("Only a community or a mortal can be turned to you.")
    creator_id = await creator_node_id(ctx.session)
    targets = await worship_targets(ctx.session, target.id)
    kinds = await NodeRepository(ctx.session).kinds_of(targets)
    gods = [node for node in targets if kinds.get(node) in (NodeKind.SON, NodeKind.FOREIGN_GOD)]
    if creator_id in targets and not gods:
        raise ValidationFailedError(f"{target.name} already worships only you.")
    spend(creator, rules.convert_cost, "god_power.convert_cost")
    bonds = BondRepository(ctx.session)
    names: list[str] = []
    for node in gods:
        await bonds.close_between(target.id, node, [BondKind.WORSHIPS], ctx.epoch, "converted")
        name = await NodeRepository(ctx.session).name_of(node)
        names.append(name or "")
        son = await ctx.session.get(SonRow, node)
        if son is not None and son.status is not SonStatus.DEAD:
            son.loyalty = clamp_percent(son.loyalty - rules.convert_patron_loyalty_loss)
    await worship_creator(ctx.session, target, ctx.epoch, god_lines.CONVERT_VOW.format(creator=creator.name))
    line = god_lines.CONVERT
    old = f"; {', '.join(names)} are no longer its gods" if names else ""
    await ctx.chronicle(
        ChronicleKind.CREATOR_HAND, line.render(creator=creator.name, entity=target.name, old=old), template_key=line.key, entity_ids=[target.id]
    )
    return names


def wrath_cost(rules: Rules, target: EntityRow) -> int:
    return rules.god_power.wrath_base_cost + target.power_level * rules.god_power.wrath_cost_per_power


async def _residents(ctx: TickContext, root: EntityRow) -> list[EntityRow]:
    entities = EntityRepository(ctx.session)
    found: list[EntityRow] = []
    frontier = [root]
    seen = {root.id}
    while frontier:
        current = frontier.pop()
        for item in await entities.contents(current.id):
            if item.id in seen:
                continue
            seen.add(item.id)
            frontier.append(item)
            if item.entity_type is EntityType.MORTAL:
                found.append(item)
    return found


async def wrath(ctx: TickContext, creator: CreatorRow, target: EntityRow, reason: str = "") -> KillCount:
    rules = ctx.rules.god_power
    require_canon(target)
    if target.entity_type is EntityType.REGION:
        raise ValidationFailedError("A region is not destroyed; send a disaster or a world wrath upon it.")
    if target.entity_type is EntityType.MORTAL:
        raise ValidationFailedError('Taking a mortal\'s life is a separate action ("Take their life").')
    spend(creator, wrath_cost(ctx.rules, target), "god_power.wrath_base_cost")
    rng = ctx.rng("wrath")
    died = 0
    for resident in await _residents(ctx, target):
        if rng.chance(rules.wrath_death_chance):
            outcome = await attempt_kill(
                ctx,
                resident,
                Killer(ActorKind.CREATOR, creator.name, creator.id),
                creator.name,
                certain=True,
                how=god_lines.WRATH_HOW.format(entity=target.name),
            )
            died += 1 if outcome.success else 0
    entities = EntityRepository(ctx.session)
    await entities.transfer_contents(target, ctx.epoch)
    clause = f" ({reason})" if reason else ""
    await entities.set_status(target, EntityStatus.DESTROYED, ctx.epoch, god_lines.WRATH_NOTE.format(epoch=ctx.epoch, creator=creator.name, reason=clause))
    line = god_lines.WRATH
    deaths = f"; the {died} named mortals inside also perished" if died else ""
    await ctx.chronicle(
        ChronicleKind.CREATOR_HAND,
        line.render(creator=creator.name, entity=target.name, reason=clause, deaths=deaths),
        template_key=line.key,
        entity_ids=[target.id],
    )
    return KillCount(died)


async def world_wrath(ctx: TickContext, creator: CreatorRow, world: WorldRow, kind: Disaster) -> list[int]:
    rules = ctx.rules.god_power
    if world.discovery is Discovery.FORGOTTEN:
        raise ValidationFailedError(f"{world.name} is forgotten; no hand reaches the world in the mist.")
    if kind not in DISASTERS:
        raise ValidationFailedError("Choose the form of wrath (earthquake, flood, plague, drought, storm).")
    regions = await canon(ctx.session, [EntityType.REGION], world.id)
    if not regions:
        raise ValidationFailedError(f"There is no region in {world.name} for the wrath to fall on.")
    spend(creator, rules.world_wrath_cost, "god_power.world_wrath_cost")
    events: list[int] = []
    for region in regions:
        impact = await apply_disaster(ctx, region, kind, rules.world_wrath_severity / PERCENT)
        events.append((await record_disaster_event(ctx, region, kind, rules.world_wrath_severity, impact)).id)
    line = god_lines.WORLD_WRATH
    await ctx.chronicle(
        ChronicleKind.CREATOR_HAND,
        line.render(creator=creator.name, disaster=disaster_phrase(kind), world=world.name, count=len(regions)),
        template_key=line.key,
        entity_ids=events,
    )
    return events


async def kill_mortal_by_creator(ctx: TickContext, creator: CreatorRow, mortal: EntityRow, how: str = "") -> KillOutcome:
    spend(creator, ctx.rules.death.creator_take_life_cost, "death.creator_take_life_cost")
    return await attempt_kill(
        ctx,
        mortal,
        Killer(ActorKind.CREATOR, creator.name, creator.id),
        creator.name,
        certain=True,
        how=how or god_lines.GOD_KILL_MORTAL_HOW.format(creator=creator.name),
    )
