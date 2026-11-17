from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.rarity import Rarity
from aerona.engine.context import Publisher
from aerona.engine.gods import acts, lineage, power
from aerona.engine.gods.essence import spend
from aerona.engine.gods.god_death import GodDeath
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.rules.registry import Rules
from aerona.services.gods.context import record_action, require, require_creator


async def _son(session: AsyncSession, son_id: int) -> SonRow:
    return power.living(await session.get(SonRow, son_id))


async def _entity(session: AsyncSession, entity_id: int) -> EntityRow:
    return require(await session.get(EntityRow, entity_id), "record")


async def _foreign(session: AsyncSession, god_id: int) -> ForeignGodRow:
    return require(await session.get(ForeignGodRow, god_id), "foreign god")


async def drain_son(session: AsyncSession, rules: Rules, son_id: int, publish: Publisher | None = None) -> power.DrainResult:
    ctx = await manual_context(session, "drain_son", rules, publish)
    result = await power.drain_son(ctx, await require_creator(session), await _son(session, son_id))
    await record_action(ctx, ActionKind.DRAIN_ESSENCE, son_id)
    return result


async def devour_son(session: AsyncSession, rules: Rules, son_id: int, reason: str = "", publish: Publisher | None = None) -> tuple[GodDeath, int]:
    ctx = await manual_context(session, "devour_son", rules, publish)
    result = await power.devour_son(ctx, await require_creator(session), await _son(session, son_id), reason)
    await record_action(ctx, ActionKind.DEVOUR, son_id)
    return result


async def demote_son(session: AsyncSession, rules: Rules, son_id: int) -> Rarity:
    ctx = await manual_context(session, "demote_son", rules)
    creator = await require_creator(session)
    son = await _son(session, son_id)
    if son.rarity.rank <= 0:
        raise ValidationFailedError(f"{son.name} is already in the lowest class ({spoken(son.rarity)}).")
    spend(creator, rules.god_power.demote_cost, "god_power.demote_cost")
    result = await power.demote_son(ctx, creator, son)
    await record_action(ctx, ActionKind.DEMOTE, son_id, rules.god_power.demote_cost)
    return result


async def strip_power(session: AsyncSession, rules: Rules, son_id: int, slot: int) -> int:
    ctx = await manual_context(session, "strip_power", rules)
    creator = await require_creator(session)
    son = await _son(session, son_id)
    spend(creator, rules.god_power.strip_power_cost, "god_power.strip_power_cost")
    gained = await power.strip_power(ctx, creator, son, slot)
    await record_action(ctx, ActionKind.OTHER, son_id, rules.god_power.strip_power_cost)
    return gained


async def absolute_command(session: AsyncSession, rules: Rules, son_id: int, command: str) -> str:
    ctx = await manual_context(session, "absolute_command", rules)
    creator = await require_creator(session)
    son = await _son(session, son_id)
    if not command.strip():
        raise ValidationFailedError("Write the command.")
    spend(creator, rules.god_power.absolute_command_cost, "god_power.absolute_command_cost")
    text = await power.absolute_command(ctx, creator, son, command)
    await record_action(ctx, ActionKind.ABSOLUTE_COMMAND, son_id, rules.god_power.absolute_command_cost)
    return text


async def force_rebellion(session: AsyncSession, rules: Rules, son_id: int, manifesto: str) -> SonRow:
    ctx = await manual_context(session, "force_rebellion", rules)
    son = await _son(session, son_id)
    if son.rebel:
        raise ValidationFailedError(f"{son.name} is already a rebel.")
    if not manifesto.strip():
        raise ValidationFailedError("Write the rebel's manifesto.")
    await power.declare_rebellion(ctx, await require_creator(session), son, manifesto.strip(), spontaneous=False)
    return son


async def pardon_rebel(session: AsyncSession, rules: Rules, son_id: int) -> SonRow:
    ctx = await manual_context(session, "pardon_rebel", rules)
    son = await _son(session, son_id)
    if not son.rebel:
        raise ValidationFailedError(f"{son.name} is not a rebel.")
    await power.end_rebellion(ctx, await require_creator(session), son)
    await record_action(ctx, ActionKind.FORGIVE, son_id)
    return son


async def drain_mortal(session: AsyncSession, rules: Rules, entity_id: int, devour: bool = False) -> acts.GainResult:
    ctx = await manual_context(session, "drain_mortal", rules)
    result = await acts.drain_mortal(ctx, await require_creator(session), await _entity(session, entity_id), devour)
    await record_action(ctx, ActionKind.DEVOUR if devour else ActionKind.DRAIN_ESSENCE, entity_id)
    return result


async def harvest_community(session: AsyncSession, rules: Rules, entity_id: int) -> acts.GainResult:
    ctx = await manual_context(session, "harvest", rules)
    result = await acts.harvest_community(ctx, await require_creator(session), await _entity(session, entity_id))
    await record_action(ctx, ActionKind.HARVEST_COMMUNITY, entity_id)
    return result


async def drain_foreign_god(session: AsyncSession, rules: Rules, god_id: int) -> acts.GainResult:
    ctx = await manual_context(session, "drain_foreign", rules)
    result = await acts.drain_foreign_god(ctx, await require_creator(session), await _foreign(session, god_id))
    await record_action(ctx, ActionKind.DRAIN_ESSENCE, god_id)
    return result


async def kill_foreign_god(session: AsyncSession, rules: Rules, god_id: int, reason: str = "", devour: bool = False) -> acts.GainResult:
    ctx = await manual_context(session, "kill_foreign", rules)
    god = await _foreign(session, god_id)
    cost = await acts.foreign_kill_cost(ctx, god)
    result = await acts.kill_foreign_god(ctx, await require_creator(session), god, reason, devour)
    await record_action(ctx, ActionKind.KILL_FOREIGN_GOD, god_id, cost)
    return result


async def resurrect_mortal(session: AsyncSession, rules: Rules, entity_id: int) -> int:
    ctx = await manual_context(session, "resurrect_mortal", rules)
    cost = await acts.resurrect_mortal(ctx, await require_creator(session), await _entity(session, entity_id))
    await record_action(ctx, ActionKind.RESURRECT_MORTAL, entity_id, cost)
    return cost


async def choose_prophet(session: AsyncSession, rules: Rules, entity_id: int) -> EntityRow | None:
    ctx = await manual_context(session, "prophet", rules)
    creator = await require_creator(session)
    mortal = acts.require_canon(await session.get(EntityRow, entity_id), "This mortal")
    if mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("A prophet can only be a named mortal.")
    if await has_flag(session, mortal.id, EntityFlag.PROPHET):
        raise ValidationFailedError(f"{mortal.name} is already your prophet.")
    spend(creator, rules.god_power.prophet_cost, "god_power.prophet_cost")
    community = await lineage.make_prophet(ctx, creator, mortal)
    await record_action(ctx, ActionKind.CHOOSE_PROPHET, entity_id, rules.god_power.prophet_cost)
    return community


async def manifest(session: AsyncSession, rules: Rules, entity_id: int, words: str) -> bool:
    ctx = await manual_context(session, "manifest", rules)
    worshipped = await acts.manifest(ctx, await require_creator(session), await _entity(session, entity_id), words)
    await record_action(ctx, ActionKind.MANIFESTATION, entity_id, rules.god_power.manifest_cost)
    return worshipped


async def curse_bloodline(session: AsyncSession, rules: Rules, entity_id: int) -> list[EntityRow]:
    ctx = await manual_context(session, "bloodline_curse", rules)
    creator = await require_creator(session)
    root = acts.require_canon(await session.get(EntityRow, entity_id))
    if await has_flag(session, root.id, EntityFlag.BLOODLINE_CURSE):
        raise ValidationFailedError(f"{root.name}'s bloodline is already cursed.")
    spend(creator, rules.god_power.bloodline_curse_cost, "god_power.bloodline_curse_cost")
    members = await lineage.curse_bloodline(ctx, creator, root)
    await record_action(ctx, ActionKind.LINEAGE_CURSE, entity_id, rules.god_power.bloodline_curse_cost)
    return members


async def lift_bloodline_curse(session: AsyncSession, rules: Rules, entity_id: int) -> int:
    ctx = await manual_context(session, "bloodline_lift", rules)
    creator = await require_creator(session)
    root = await _entity(session, entity_id)
    members = await lineage.cursed_members(ctx, root)
    if not members:
        raise ValidationFailedError(f"There is no bloodline curse in {root.name}'s line.")
    spend(creator, rules.god_power.bloodline_curse_lift_cost, "god_power.bloodline_curse_lift_cost")
    count = await lineage.lift_bloodline_curse(ctx, creator, root, members)
    await record_action(ctx, ActionKind.LIFT_LINEAGE_CURSE, entity_id, rules.god_power.bloodline_curse_lift_cost)
    return count


async def convert_to_creator(session: AsyncSession, rules: Rules, entity_id: int) -> list[str]:
    ctx = await manual_context(session, "convert", rules)
    names = await acts.convert_to_creator(ctx, await require_creator(session), await _entity(session, entity_id))
    await record_action(ctx, ActionKind.CONVERT, entity_id, rules.god_power.convert_cost)
    return names


async def wrath(session: AsyncSession, rules: Rules, entity_id: int, reason: str = "") -> acts.KillCount:
    ctx = await manual_context(session, "wrath", rules)
    target = await _entity(session, entity_id)
    cost = acts.wrath_cost(rules, target)
    result = await acts.wrath(ctx, await require_creator(session), target, reason)
    await record_action(ctx, ActionKind.WRATH, entity_id, cost)
    return result


async def world_wrath(session: AsyncSession, rules: Rules, world_id: int, kind: Disaster) -> list[int]:
    ctx = await manual_context(session, "world_wrath", rules)
    world = require(await session.get(WorldRow, world_id), "world")
    events = await acts.world_wrath(ctx, await require_creator(session), world, kind)
    await record_action(ctx, ActionKind.WORLD_WRATH, world_id, rules.god_power.world_wrath_cost)
    return events
