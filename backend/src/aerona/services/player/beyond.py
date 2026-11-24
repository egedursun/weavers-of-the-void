from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.horror import HorrorEffect, HorrorScope, HorrorSense, HorrorSource, HorrorTarget
from aerona.engine.cosmos.horror_model import HorrorSpec
from aerona.engine.phases.afterlife import (
    abandon_legendary_quest,
    force_soul_descent,
    order_archive,
    order_archive_reading,
    order_cosmic_plague,
    order_mirror_birth,
    order_planet_act,
    order_soul_harvest,
    set_immortal,
)
from aerona.engine.phases.doom import set_doom_clock, trigger_apocalypse
from aerona.engine.phases.horror import order_horror_event, set_son_sanity, spawn_outer_cult, suppress_outer_cult
from aerona.engine.phases.sky import order_time_echo
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class MortalTarget(Command):
    mortal_id: int


class SoulHarvest(Command):
    cult_id: int
    soul_id: int


class WorldTarget(Command):
    world_id: int


class CommunityTarget(Command):
    community_id: int


class PlaceTarget(Command):
    place_id: int


class ThreadTarget(Command):
    thread_id: int


class Immortality(Command):
    mortal_id: int
    immortal: bool = True


class HorrorEvent(Command):
    world_id: int
    target: HorrorTarget = HorrorTarget.MINDS
    effect: HorrorEffect = HorrorEffect.MARK
    scope: HorrorScope = HorrorScope.WORLD
    sense: HorrorSense = HorrorSense.SEEN
    source: HorrorSource = HorrorSource.UNKNOWN


class EntityTarget(Command):
    entity_id: int


class CultTarget(Command):
    cult_id: int


class Sanity(Command):
    son_id: int
    value: int


class Apocalypse(Command):
    calling: bool = False


class DoomClock(Command):
    value: int


class Empty(Command):
    pass


@player_action("soul:descend", ActionKind.SOUL_DESCENT)
async def descend(scope: PlayerScope, command: MortalTarget) -> Effect:
    soul = await force_soul_descent(scope.session, scope.rules, command.mortal_id)
    return Effect(f"{soul.name} descended to the realm of the dead.", soul.id, created_ids=(soul.id,))


@player_action("soul:harvest", ActionKind.SOUL_HARVEST)
async def harvest(scope: PlayerScope, command: SoulHarvest) -> Effect:
    await order_soul_harvest(scope.session, scope.rules, command.cult_id, command.soul_id)
    return Effect("The cult harvested the soul.", command.cult_id)


@player_action("world:planet_stirs", ActionKind.PLANET_ACT)
async def planet_stirs(scope: PlayerScope, command: WorldTarget) -> Effect:
    text = await order_planet_act(scope.session, scope.rules, command.world_id)
    if text is None:
        raise ValidationFailedError("The planet did not stir.")
    return Effect(text)


@player_action("archive:raise", ActionKind.COSMIC_ARCHIVE)
async def raise_archive(scope: PlayerScope, command: Empty) -> Effect:
    archive = await order_archive(scope.session, scope.rules)
    if archive is None:
        raise ValidationFailedError("No place in the cosmos could hold the Cosmic Archive.")
    return Effect(f"{archive.name} rose.", archive.id, created_ids=(archive.id,))


@player_action("archive:read", ActionKind.COSMIC_ARCHIVE)
async def read_archive(scope: PlayerScope, command: CommunityTarget) -> Effect:
    learned = await order_archive_reading(scope.session, scope.rules, command.community_id)
    if learned is None:
        raise ValidationFailedError("The Archive had nothing left to teach them.")
    return Effect(f"The Archive taught {learned.name}.", command.community_id, values={"learned_id": learned.id})


@player_action("plague:cosmic", ActionKind.COSMIC_PLAGUE)
async def plague(scope: PlayerScope, command: PlaceTarget) -> Effect:
    await order_cosmic_plague(scope.session, scope.rules, command.place_id)
    return Effect("The cosmic plague took hold.", command.place_id)


@player_action("soul:mirror", ActionKind.MIRROR_BIRTH)
async def mirror(scope: PlayerScope, command: MortalTarget) -> Effect:
    reflected = await order_mirror_birth(scope.session, scope.rules, command.mortal_id)
    return Effect(f"{reflected.name} was born in the mirror world.", reflected.id, created_ids=(reflected.id,))


@player_action("mortal:immortal", ActionKind.SET_IMMORTAL)
async def immortality(scope: PlayerScope, command: Immortality) -> Effect:
    mortal = await set_immortal(scope.session, scope.rules, command.mortal_id, immortal=command.immortal)
    state = "no longer ages" if command.immortal else "is mortal again"
    return Effect(f"{mortal.name} {state}.", mortal.id)


@player_action("quest:abandon", ActionKind.LEGENDARY_QUEST)
async def abandon_quest(scope: PlayerScope, command: ThreadTarget) -> Effect:
    creator = await scope.creator()
    return Effect(await abandon_legendary_quest(scope.session, scope.rules, command.thread_id, creator.name))


@player_action("sky:time_echo", ActionKind.TIME_ECHO)
async def time_echo(scope: PlayerScope, command: ThreadTarget) -> Effect:
    echo = await order_time_echo(scope.session, scope.rules, command.thread_id)
    if echo is None:
        raise ValidationFailedError("That story leaves no echo in time.")
    return Effect(f"{echo.name} echoed through time.", echo.id, created_ids=(echo.id,))


@player_action("horror:event", ActionKind.HORROR_EVENT)
async def horror_event(scope: PlayerScope, command: HorrorEvent) -> Effect:
    spec = HorrorSpec(command.target, command.effect, command.scope, command.sense, command.source)
    row, text = await order_horror_event(scope.session, scope.rules, command.world_id, spec)
    return Effect(text, command.world_id, values={"horror_id": row.id})


@player_action("horror:cult", ActionKind.OUTER_CULT)
async def outer_cult(scope: PlayerScope, command: EntityTarget) -> Effect:
    cult = await spawn_outer_cult(scope.session, scope.rules, command.entity_id)
    return Effect(f"{cult.name} arose.", cult.id, created_ids=(cult.id,))


@player_action("horror:suppress_cult", ActionKind.DESTROY)
async def suppress_cult(scope: PlayerScope, command: CultTarget) -> Effect:
    cult = await suppress_outer_cult(scope.session, scope.rules, command.cult_id)
    return Effect(f"{cult.name} was scattered.", cult.id)


@player_action("son:sanity", ActionKind.SET_SANITY)
async def sanity(scope: PlayerScope, command: Sanity) -> Effect:
    son = await set_son_sanity(scope.session, command.son_id, command.value)
    return Effect(f"{son.name}'s sanity is now {son.sanity}.", son.id, values={"sanity": son.sanity})


@player_action("doom:apocalypse", ActionKind.APOCALYPSE)
async def apocalypse(scope: PlayerScope, command: Apocalypse) -> Effect:
    clock = await trigger_apocalypse(await scope.context("apocalypse"), command.calling)
    return Effect(f"The apocalypse came; the doom clock stands at {clock}.", values={"doom_clock": clock})


@player_action("doom:clock", ActionKind.SET_DOOM_CLOCK)
async def doom_clock(scope: PlayerScope, command: DoomClock) -> Effect:
    clock = await set_doom_clock(await scope.context("doom_clock"), command.value)
    return Effect(f"The doom clock was set to {clock}.", values={"doom_clock": clock})
