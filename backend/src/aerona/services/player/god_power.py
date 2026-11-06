from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.intervention import Disaster
from aerona.engine.gods.deification import deify
from aerona.events.kinds import EventKind
from aerona.services.gods import god_power
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class SonTarget(Command):
    son_id: int


class DevourSon(Command):
    son_id: int
    reason: str = ""


class DrainMortal(Command):
    entity_id: int
    devour: bool = False


class EntityTarget(Command):
    entity_id: int


class ForeignGodTarget(Command):
    god_id: int


class KillForeignGod(Command):
    god_id: int
    reason: str = ""
    devour: bool = False


class StripPower(Command):
    son_id: int
    slot: int


class AbsoluteCommand(Command):
    son_id: int
    text: str


class ForceRebellion(Command):
    son_id: int
    manifesto: str


class Manifest(Command):
    entity_id: int
    words: str


class BloodlineCurse(Command):
    entity_id: int
    lift: bool = False


class Wrath(Command):
    entity_id: int
    reason: str = ""


class WorldWrath(Command):
    world_id: int
    disaster: Disaster = Disaster.EARTHQUAKE


def _clip(scope: PlayerScope, text: str) -> str:
    return guards.clip(text, scope.rules.god_actions.inspiration_max_chars)


@player_action("drain:son", ActionKind.DRAIN_ESSENCE)
async def drain_son(scope: PlayerScope, command: SonTarget) -> Effect:
    result = await god_power.drain_son(scope.session, scope.rules, command.son_id, scope.publish)
    return Effect(f"{result.son.name} lost {result.drawn} essence; {result.gained} flowed to the Creator.", result.son.id, values={"drawn": result.drawn})


@player_action("devour:son", ActionKind.DEVOUR)
async def devour_son(scope: PlayerScope, command: DevourSon) -> Effect:
    son = await guards.living_son(scope.session, command.son_id)
    name = son.name
    _, gained = await god_power.devour_son(scope.session, scope.rules, son.id, _clip(scope, command.reason), scope.publish)
    return Effect(f"{name} was devoured; the Creator gained {gained} essence.", son.id)


@player_action("drain:mortal", ActionKind.DRAIN_ESSENCE)
async def drain_mortal(scope: PlayerScope, command: DrainMortal) -> Effect:
    result = await god_power.drain_mortal(scope.session, scope.rules, command.entity_id, command.devour)
    return Effect(
        result.text,
        command.entity_id,
        kind=ActionKind.DEVOUR if command.devour else ActionKind.DRAIN_ESSENCE,
        tool="devour:mortal" if command.devour else "drain:mortal",
    )


@player_action("harvest", ActionKind.HARVEST_COMMUNITY)
async def harvest(scope: PlayerScope, command: EntityTarget) -> Effect:
    result = await god_power.harvest_community(scope.session, scope.rules, command.entity_id)
    return Effect(result.text, command.entity_id)


@player_action("drain:foreign_god", ActionKind.DRAIN_ESSENCE)
async def drain_foreign_god(scope: PlayerScope, command: ForeignGodTarget) -> Effect:
    await guards.foreign_god(scope.session, command.god_id)
    result = await god_power.drain_foreign_god(scope.session, scope.rules, command.god_id)
    return Effect(result.text, command.god_id)


@player_action("kill:foreign_god", ActionKind.KILL_FOREIGN_GOD)
async def kill_foreign_god(scope: PlayerScope, command: KillForeignGod) -> Effect:
    await guards.foreign_god(scope.session, command.god_id)
    result = await god_power.kill_foreign_god(scope.session, scope.rules, command.god_id, _clip(scope, command.reason), command.devour)
    return Effect(result.text, command.god_id, tool="devour:foreign_god" if command.devour else "kill:foreign_god")


@player_action("resurrect:mortal", ActionKind.RESURRECT_MORTAL)
async def resurrect_mortal(scope: PlayerScope, command: EntityTarget) -> Effect:
    mortal = await guards.entity(scope.session, command.entity_id)
    cost = await god_power.resurrect_mortal(scope.session, scope.rules, mortal.id)
    return Effect(f"{mortal.name} walks again.", mortal.id, essence_spent=cost)


@player_action("deify", ActionKind.DEIFY)
async def deify_mortal(scope: PlayerScope, command: EntityTarget) -> Effect:
    mortal = await guards.canon_entity(scope.session, command.entity_id, "This mortal")
    creator = await scope.creator()
    guards.charge(creator, scope.rules.god_power.deify_cost, "god_power.deify_cost")
    ctx = await scope.context("deify")
    result = await deify(ctx, creator, mortal)
    scope.publish(EventKind.NEW_SON, {"son_id": result.son.id, "name": result.son.name, "rarity": result.son.rarity.value})
    return Effect(
        f"{mortal.name} joined the pantheon as a {result.son.rarity.value} son.",
        mortal.id,
        created_ids=(result.son.id,),
        values={"son_id": result.son.id, "followers": len(result.followers)},
    )


@player_action("demote", ActionKind.DEMOTE)
async def demote_son(scope: PlayerScope, command: SonTarget) -> Effect:
    son = await guards.living_son(scope.session, command.son_id)
    rarity = await god_power.demote_son(scope.session, scope.rules, son.id)
    return Effect(f"{son.name} fell to the {rarity.value} class.", son.id)


@player_action("strip_power", ActionKind.GRANT_POWER)
async def strip_power(scope: PlayerScope, command: StripPower) -> Effect:
    son = await guards.living_son(scope.session, command.son_id)
    gained = await god_power.strip_power(scope.session, scope.rules, son.id, command.slot)
    return Effect(f"A power was torn from {son.name}; {gained} essence returned to the Creator.", son.id, essence_spent=scope.rules.god_power.strip_power_cost)


@player_action("absolute_command", ActionKind.ABSOLUTE_COMMAND)
async def absolute_command(scope: PlayerScope, command: AbsoluteCommand) -> Effect:
    son = await guards.living_son(scope.session, command.son_id)
    text = await god_power.absolute_command(scope.session, scope.rules, son.id, _clip(scope, command.text))
    return Effect(text, son.id)


@player_action("prophet", ActionKind.CHOOSE_PROPHET)
async def choose_prophet(scope: PlayerScope, command: EntityTarget) -> Effect:
    mortal = await guards.entity(scope.session, command.entity_id)
    community = await god_power.choose_prophet(scope.session, scope.rules, mortal.id)
    tail = f"; {community.name} grew in faith" if community is not None else ""
    return Effect(f"{mortal.name} became the Creator's prophet{tail}.", mortal.id)


@player_action("manifest", ActionKind.MANIFESTATION)
async def manifest(scope: PlayerScope, command: Manifest) -> Effect:
    target = await guards.entity(scope.session, command.entity_id)
    words = _clip(scope, command.words)
    if not words:
        raise ValidationFailedError("The manifestation needs words.")
    worshipped = await god_power.manifest(scope.session, scope.rules, target.id, words)
    tail = " and turned to worship the creator" if worshipped else ""
    return Effect(f"{target.name} saw the Creator{tail}.", target.id, values={"worships": worshipped})


@player_action("bloodline_curse", ActionKind.LINEAGE_CURSE)
async def bloodline_curse(scope: PlayerScope, command: BloodlineCurse) -> Effect:
    root = await guards.entity(scope.session, command.entity_id)
    if command.lift:
        count = await god_power.lift_bloodline_curse(scope.session, scope.rules, root.id)
        return Effect(f"The curse was lifted from {count} of {root.name}'s line.", root.id, kind=ActionKind.LIFT_LINEAGE_CURSE, tool="bloodline_curse:lift")
    members = await god_power.curse_bloodline(scope.session, scope.rules, root.id)
    return Effect(f"{root.name}'s bloodline was cursed ({len(members)} members).", root.id, values={"members": len(members)})


@player_action("convert", ActionKind.CONVERT)
async def convert(scope: PlayerScope, command: EntityTarget) -> Effect:
    target = await guards.entity(scope.session, command.entity_id)
    abandoned = await god_power.convert_to_creator(scope.session, scope.rules, target.id)
    tail = f", leaving {', '.join(abandoned)}" if abandoned else ""
    return Effect(f"{target.name} now worships the Creator{tail}.", target.id)


@player_action("wrath", ActionKind.WRATH)
async def wrath(scope: PlayerScope, command: Wrath) -> Effect:
    target = await guards.entity(scope.session, command.entity_id)
    result = await god_power.wrath(scope.session, scope.rules, target.id, _clip(scope, command.reason))
    return Effect(f"{target.name} was destroyed; {result.died} named mortals died with it.", target.id, values={"died": result.died})


@player_action("wrath:world", ActionKind.WORLD_WRATH)
async def world_wrath(scope: PlayerScope, command: WorldWrath) -> Effect:
    world = await guards.open_world(scope.session, command.world_id)
    events = await god_power.world_wrath(scope.session, scope.rules, world.id, command.disaster)
    return Effect(f"Wrath fell on every region of {world.name}.", world.id, created_ids=tuple(events))


@player_action("rebellion:force", ActionKind.REBEL)
async def force_rebellion(scope: PlayerScope, command: ForceRebellion) -> Effect:
    son = await god_power.force_rebellion(scope.session, scope.rules, command.son_id, _clip(scope, command.manifesto))
    return Effect(f"{son.name} rose in rebellion.", son.id)
