from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.engine.cosmos.maps import regenerate_world_map
from aerona.engine.cosmos.stars import set_epoch_star
from aerona.engine.phases.exploration import order_foreign_god_land
from aerona.engine.phases.travel import teach_route_knowledge
from aerona.services.gods import cosmic_economy
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action
from aerona.services.wiki import take_snapshot


class WorldTarget(Command):
    world_id: int


class EpochStar(Command):
    world_id: int
    entity_id: int | None = None


class RouteLesson(Command):
    community_id: int
    route_id: int


class ForeignGodTarget(Command):
    god_id: int


class DepositOwner(Command):
    deposit_id: int
    owner_id: int | None = None


class RegionTarget(Command):
    region_id: int


class FactionTarget(Command):
    faction_id: int


class Empty(Command):
    pass


class AddictionCure(Command):
    entity_id: int
    resource_id: int


class RouteDanger(Command):
    route_id: int
    danger: int


@player_action("world:map", ActionKind.REGENERATE_MAP)
async def regenerate_map(scope: PlayerScope, command: WorldTarget) -> Effect:
    world = await guards.world(scope.session, command.world_id)
    atlas = await regenerate_world_map(scope.session, scope.rules, world.id, await scope.epoch())
    return Effect(f"The map of {world.name} was drawn anew.", world.id, values={"regions": len(atlas.regions)})


@player_action("world:epoch_star", ActionKind.EPOCH_STAR)
async def epoch_star(scope: PlayerScope, command: EpochStar) -> Effect:
    world = await set_epoch_star(scope.session, command.world_id, command.entity_id)
    message = f"{world.name} has a new star of the epoch." if command.entity_id is not None else f"{world.name} has no star of the epoch."
    return Effect(message, world.id, values={"entity_id": command.entity_id})


@player_action("route:teach", ActionKind.TEACH_KNOWLEDGE)
async def teach_route(scope: PlayerScope, command: RouteLesson) -> Effect:
    learned = await teach_route_knowledge(scope.session, scope.rules, command.community_id, command.route_id)
    if learned is None:
        raise ValidationFailedError("They already know how to travel this road.")
    return Effect(f"The community learned {learned.name}.", command.community_id, values={"knowledge_id": learned.id})


@player_action("foreign_god:raise_land", ActionKind.FOREIGN_GOD_LAND)
async def raise_land(scope: PlayerScope, command: ForeignGodTarget) -> Effect:
    god = await guards.foreign_god(scope.session, command.god_id)
    results = await order_foreign_god_land(scope.session, scope.rules, god.id)
    if not results:
        raise ValidationFailedError(f"{god.name} raised no land; only an awake god can.")
    return Effect(" ".join(item.text for item in results), god.id, created_ids=tuple(item.land.id for item in results))


@player_action("deposit:owner", ActionKind.CLAIM)
async def deposit_owner(scope: PlayerScope, command: DepositOwner) -> Effect:
    await cosmic_economy.set_deposit_owner(scope.session, scope.rules, command.deposit_id, command.owner_id)
    message = "The deposit changed hands." if command.owner_id is not None else "The deposit belongs to no one now."
    return Effect(message, command.deposit_id, values={"owner_id": command.owner_id})


@player_action("market:found", ActionKind.FOUND_MARKET)
async def wandering_market(scope: PlayerScope, command: RegionTarget) -> Effect:
    market = await cosmic_economy.found_wandering_market(scope.session, scope.rules, command.region_id)
    return Effect(f"{market.name} began to wander.", market.id, created_ids=(market.id,))


@player_action("pirates:spawn", ActionKind.SPAWN_PIRATES)
async def void_pirates(scope: PlayerScope, command: RegionTarget) -> Effect:
    band = await cosmic_economy.spawn_void_pirates(scope.session, scope.rules, command.region_id)
    return Effect(f"{band.name} took to the void.", band.id, created_ids=(band.id,))


@player_action("market:disband", ActionKind.DESTROY)
async def disband(scope: PlayerScope, command: FactionTarget) -> Effect:
    faction = await cosmic_economy.disband_faction(scope.session, scope.rules, command.faction_id)
    return Effect(f"{faction.name} was disbanded.", faction.id)


@player_action("route:danger", ActionKind.SET_ROUTE_DANGER)
async def route_danger(scope: PlayerScope, command: RouteDanger) -> Effect:
    route = await cosmic_economy.set_route_danger(scope.session, scope.rules, command.route_id, command.danger)
    return Effect(f"The road's danger is now {route.danger}.", values={"danger": route.danger, "route_id": route.id})


@player_action("economy:resources", ActionKind.OTHER)
async def run_resource_mechanics(scope: PlayerScope, command: Empty) -> Effect:
    await cosmic_economy.run_resource_mechanics(scope.session, scope.rules, scope.publish)
    return Effect("The resource mechanics ran out of turn.")


@player_action("economy:cosmic", ActionKind.OTHER)
async def run_cosmic_economy(scope: PlayerScope, command: Empty) -> Effect:
    await cosmic_economy.run_cosmic_economy(scope.session, scope.rules, scope.publish)
    return Effect("The cosmic economy ran out of turn.")


@player_action("addiction:cure", ActionKind.MIRACLE)
async def cure_addiction(scope: PlayerScope, command: AddictionCure) -> Effect:
    community = await guards.entity(scope.session, command.entity_id)
    resource = await guards.entity(scope.session, command.resource_id)
    cured = await cosmic_economy.cure_addiction(scope.session, scope.rules, community.id, resource.id)
    message = f"{community.name} was freed from its craving for {resource.name}." if cured else f"{community.name} was not addicted to {resource.name}."
    return Effect(message, community.id, values={"cured": cured})


@player_action("map:snapshot", ActionKind.OTHER)
async def snapshot_now(scope: PlayerScope, command: Empty) -> Effect:
    del command
    epoch = await scope.epoch()
    worlds = await take_snapshot(scope.session, scope.rules, epoch)
    return Effect(f"The maps of {worlds} worlds were recorded for epoch {epoch}.", values={"worlds": worlds, "epoch": epoch})
