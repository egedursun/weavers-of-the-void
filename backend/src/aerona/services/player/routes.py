from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.economy import TradeMode
from aerona.engine.economy import route_control
from aerona.engine.gods import pacts
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

RouteValue = int | str | bool | list[int] | None
TermValue = int | str | None


class FoundRoute(Command):
    first_id: int
    second_id: int
    mode: TradeMode | None = None
    controller_id: int | None = None
    toll_pct: int | None = Field(default=None, ge=0, le=100)


class EditRoute(Command):
    route_id: int
    values: dict[str, RouteValue] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class RouteTarget(Command):
    route_id: int


class TollStop(Command):
    route_id: int
    region_id: int
    controller_id: int | None = None
    rate: int | None = Field(default=None, ge=0, le=100)
    release: list[str] = Field(default_factory=list)


class TollTarget(Command):
    route_id: int
    region_id: int


class StrikePact(Command):
    resource_id: int
    owner_id: int
    terms: dict[str, TermValue] = Field(default_factory=dict)
    epochs: int | None = Field(default=None, ge=1, le=1000)


class PactTerms(Command):
    treaty_id: int
    terms: dict[str, TermValue] = Field(default_factory=dict)


class PactTarget(Command):
    treaty_id: int


@player_action("trade_route:found", ActionKind.CREATE_ENTITY)
async def found_route(scope: PlayerScope, command: FoundRoute) -> Effect:
    route = await route_control.found_by_hand(
        await scope.context("route_found"),
        command.first_id,
        command.second_id,
        mode=command.mode,
        controller_id=command.controller_id,
        toll_pct=command.toll_pct,
    )
    return Effect(f"{route.entity.name} is opened to merchants as you laid it out.", route.entity.id, created_ids=(route.entity.id,))


@player_action("trade_route:edit", ActionKind.EDIT_RECORD)
async def edit_route(scope: PlayerScope, command: EditRoute) -> Effect:
    route = await route_control.edit_route(await scope.context("route_edit"), command.route_id, command.values, released=command.release)
    held = ", ".join(key.replace("_entity_id", "").replace("_", " ") for key in route.profile.locked if not key.startswith(route_control.UNTOLLED))
    return Effect(f"{route.entity.name} now runs as you set it{f'; held: {held}' if held else ''}.", route.entity.id)


@player_action("trade_route:delete", ActionKind.OTHER)
async def delete_route(scope: PlayerScope, command: RouteTarget) -> Effect:
    route = await route_control.delete_route(await scope.context("route_delete"), command.route_id)
    return Effect(f"{route.name} is struck from the world.", route.id)


@player_action("trade_route:toll_stop", ActionKind.OTHER)
async def toll_stop(scope: PlayerScope, command: TollStop) -> Effect:
    toll = await route_control.set_toll_stop(
        await scope.context("route_toll_stop"),
        command.route_id,
        command.region_id,
        controller_id=command.controller_id,
        rate=command.rate,
        released=command.release,
    )
    return Effect(f"A toll of {toll.rate_pct}% is taken in that land.", command.route_id)


@player_action("trade_route:toll_remove", ActionKind.OTHER)
async def toll_remove(scope: PlayerScope, command: TollTarget) -> Effect:
    await route_control.remove_toll(await scope.context("route_toll_remove"), command.route_id, command.region_id)
    return Effect("No toll is taken in that land while your word stands.", command.route_id)


@player_action("resource:pact", ActionKind.CREATE_ENTITY)
async def strike_pact(scope: PlayerScope, command: StrikePact) -> Effect:
    treaty = await pacts.pact_by_hand(await scope.context("resource_pact"), command.resource_id, command.owner_id, command.terms, epochs=command.epochs)
    return Effect(f"{treaty.name} binds the resource and its keeper.", command.resource_id, created_ids=(treaty.id,))


@player_action("resource:pact_terms", ActionKind.EDIT_RECORD)
async def pact_terms(scope: PlayerScope, command: PactTerms) -> Effect:
    clause = await pacts.pact_terms(await scope.context("resource_pact_terms"), command.treaty_id, command.terms)
    return Effect(f"The pact now asks {clause.params.get('demand')}.", command.treaty_id)


@player_action("resource:pact_end", ActionKind.OTHER)
async def end_pact(scope: PlayerScope, command: PactTarget) -> Effect:
    await pacts.end_pact(await scope.context("resource_pact_end"), command.treaty_id)
    return Effect("The pact is released; the resource asks again as it pleases.", command.treaty_id)
