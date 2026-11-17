from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.quests import QuestAim
from aerona.engine.phases.factions import decree_faction, dissolve_faction
from aerona.engine.phases.heroes import assign_apprentice, raise_hero, recall_hero, resolve_quest, send_on_quest
from aerona.engine.phases.heroism import send_hero_to_hunt
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class CommunityTarget(Command):
    community_id: int


class Quest(Command):
    hero_id: int
    aim: QuestAim | None = None
    target_id: int | None = None


class QuestEnd(Command):
    hero_id: int
    succeed: bool | None = None


class HeroTarget(Command):
    hero_id: int


class Hunt(Command):
    hero_id: int
    monster_id: int


class Faction(Command):
    community_id: int
    kind: FactionKind


class FactionTarget(Command):
    faction_id: int


@player_action("hero:raise", ActionKind.RAISE_HERO)
async def hero(scope: PlayerScope, command: CommunityTarget) -> Effect:
    born = await raise_hero(await scope.context("raise_hero"), command.community_id)
    return Effect(f"{born.name} rose as a hero.", born.id, created_ids=(born.id,))


@player_action("hero:quest", ActionKind.ADVENTURE)
async def quest(scope: PlayerScope, command: Quest) -> Effect:
    row = await send_on_quest(await scope.context("hero_quest"), command.hero_id, command.aim, command.target_id)
    return Effect(f"The hero set out: {row.description}.", command.hero_id, values={"quest_id": row.id})


@player_action("hero:resolve", ActionKind.ADVENTURE)
async def resolve(scope: PlayerScope, command: QuestEnd) -> Effect:
    status = await resolve_quest(await scope.context("resolve_quest"), command.hero_id, command.succeed)
    return Effect(f"The quest ended: {status.value.replace('_', ' ')}.", command.hero_id, values={"status": status.value})


@player_action("hero:recall", ActionKind.RECALL_HERO)
async def recall(scope: PlayerScope, command: HeroTarget) -> Effect:
    row = await recall_hero(await scope.context("recall_hero"), command.hero_id)
    return Effect(f"The hero was called back from {row.description}.", command.hero_id)


@player_action("hero:apprentice", ActionKind.TRAIN_APPRENTICE)
async def apprentice(scope: PlayerScope, command: HeroTarget) -> Effect:
    pupil = await assign_apprentice(await scope.context("apprentice"), command.hero_id)
    return Effect(f"{pupil.name} became an apprentice.", pupil.id, created_ids=(pupil.id,))


@player_action("hero:hunt", ActionKind.HUNT)
async def hunt(scope: PlayerScope, command: Hunt) -> Effect:
    result = await send_hero_to_hunt(await scope.context("hunt"), command.hero_id, command.monster_id)
    created = (result.legend.id,) if result.legend is not None else ()
    return Effect(
        f"The hunt ended: {result.outcome.value.replace('_', ' ')}.", command.monster_id, created_ids=created, values={"outcome": result.outcome.value}
    )


@player_action("faction:found", ActionKind.FOUND_FACTION)
async def found_faction(scope: PlayerScope, command: Faction) -> Effect:
    faction = await decree_faction(await scope.context("found_faction"), command.community_id, command.kind)
    return Effect(f"{faction.name} was founded.", faction.id, created_ids=(faction.id,))


@player_action("faction:dissolve", ActionKind.DISSOLVE_FACTION)
async def dissolve(scope: PlayerScope, command: FactionTarget) -> Effect:
    faction = await dissolve_faction(await scope.context("dissolve_faction"), command.faction_id)
    return Effect(f"{faction.name} was dissolved.", faction.id)
