from pydantic import Field

from aerona.catalog.commodities import commodity_label
from aerona.catalog.production import WORKSHOP_LABELS
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.economy import CommodityKind, MaterialFamily, WorkshopKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.economy import control, control_depth
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME_MAX = 60
DESCRIPTION_MAX = 600


class EditMaterial(Command):
    world_id: int
    material: MaterialKind | None = None
    world_material_id: int | None = None
    values: dict[str, int] = Field(default_factory=dict)
    name: str | None = Field(default=None, max_length=NAME_MAX)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    family: MaterialFamily | None = None
    branch: KnowledgeBranch | None = None
    clear_branch: bool = False
    hold: bool | None = None


class GrantStock(Command):
    community_id: int
    commodity: CommodityKind
    quantity: int
    material: MaterialKind | None = None
    world_material_id: int | None = None
    quality: int = Field(default=50, ge=0, le=100)


class SetResource(Command):
    resource_id: int
    reserve: int | None = Field(default=None, ge=0)
    fields: dict[str, int] = Field(default_factory=dict)


class SetOwner(Command):
    resource_id: int
    owner_id: int | None = None


class Reveal(Command):
    resource_id: int
    revealed: bool = True


class SetWorkshop(Command):
    community_id: int
    kind: WorkshopKind
    level: int = Field(ge=0, le=20)


class OpenRoute(Command):
    route_id: int | None = None
    first_id: int | None = None
    second_id: int | None = None


class RouteTarget(Command):
    route_id: int


class SetToll(Command):
    route_id: int
    region_id: int
    rate: int | None = Field(default=None, ge=0, le=100)


class EditCurrency(Command):
    currency_id: int
    purity: int | None = Field(default=None, ge=0, le=100)
    trust: int | None = Field(default=None, ge=0, le=100)
    supply: int | None = Field(default=None, ge=0)
    name: str | None = Field(default=None, max_length=NAME_MAX)
    metal: MaterialKind | None = None
    hold: bool | None = None


class CurrencyTarget(Command):
    currency_id: int


class UseCurrency(Command):
    community_id: int
    currency_id: int | None = None


class LoanTarget(Command):
    loan_id: int


class InjectHoard(Command):
    community_id: int
    metal: MaterialKind = MaterialKind.GOLD
    world_material_id: int | None = None
    units: int | None = Field(default=None, ge=1)


@player_action("material:edit", ActionKind.EDIT_RECORD)
async def edit_material(scope: PlayerScope, command: EditMaterial) -> Effect:
    ctx = await scope.context("material_edit")
    text = control.MaterialText(
        description=command.description, family=command.family, branch=command.branch, clear_branch=command.clear_branch, hold=command.hold
    )
    row = await control.edit_material(
        ctx, command.world_id, material=command.material, world_material_id=command.world_material_id, values=command.values, name=command.name, text=text
    )
    label = row.name or (command.material.value.replace("_", " ") if command.material else "the substance")
    return Effect(f"{label.capitalize()} now holds the properties you set in this world.", values={"world_material_id": row.id})


@player_action("stock:grant", ActionKind.EDIT_RECORD)
async def grant_stock(scope: PlayerScope, command: GrantStock) -> Effect:
    ctx = await scope.context("stock_grant")
    moved = await control.grant_stock(
        ctx,
        command.community_id,
        command.commodity,
        command.quantity,
        material=command.material,
        quality=command.quality,
        world_material_id=command.world_material_id,
    )
    verb = "added to" if moved >= 0 else "taken from"
    return Effect(f"{abs(moved)} {commodity_label(command.commodity).lower()} {verb} the stores.", command.community_id, values={"moved": moved})


@player_action("resource:set", ActionKind.EDIT_RECORD)
async def set_resource(scope: PlayerScope, command: SetResource) -> Effect:
    ctx = await scope.context("resource_set")
    profile = await control.set_resource(ctx, command.resource_id, reserve=command.reserve, fields=command.fields)
    return Effect(f"The resource now holds {profile.reserve} of {profile.initial_reserve}.", command.resource_id, values={"reserve": profile.reserve})


@player_action("resource:owner", ActionKind.EDIT_RECORD)
async def set_owner(scope: PlayerScope, command: SetOwner) -> Effect:
    owner = await control.set_owner(await scope.context("resource_owner"), command.resource_id, command.owner_id)
    return Effect(f"The resource now belongs to {owner.name}." if owner is not None else "The resource belongs to no one.", command.resource_id)


@player_action("resource:reveal", ActionKind.EDIT_RECORD)
async def reveal(scope: PlayerScope, command: Reveal) -> Effect:
    await control.reveal(await scope.context("resource_reveal"), command.resource_id, command.revealed)
    return Effect("The deposit is known to those who live near it." if command.revealed else "The deposit is hidden again.", command.resource_id)


@player_action("workshop:set", ActionKind.BUILD)
async def set_workshop(scope: PlayerScope, command: SetWorkshop) -> Effect:
    row = await control.set_workshop(await scope.context("workshop_set"), command.community_id, command.kind, command.level)
    label = WORKSHOP_LABELS[command.kind]
    return Effect(f"{label} raised to level {row.level}." if row is not None else f"{label} pulled down.", command.community_id)


@player_action("trade_route:open", ActionKind.OTHER)
async def open_route(scope: PlayerScope, command: OpenRoute) -> Effect:
    route = await control.open_route(await scope.context("route_open"), route_id=command.route_id, first_id=command.first_id, second_id=command.second_id)
    return Effect(f"{route.name} is open to merchants.", route.id, created_ids=() if command.route_id is not None else (route.id,))


@player_action("trade_route:close", ActionKind.OTHER)
async def close_route(scope: PlayerScope, command: RouteTarget) -> Effect:
    route = await control.close_route(await scope.context("route_close"), command.route_id)
    return Effect(f"{route.name} is closed; no caravan passes until you open it.", route.id)


@player_action("trade_route:toll", ActionKind.OTHER)
async def set_toll(scope: PlayerScope, command: SetToll) -> Effect:
    toll = await control.set_toll(await scope.context("route_toll"), command.route_id, command.region_id, command.rate)
    if command.rate is None:
        return Effect("The toll is left to the master of the region again.", command.route_id)
    return Effect(f"The toll is held at {toll.rate_pct if toll is not None else command.rate}%.", command.route_id)


@player_action("currency:edit", ActionKind.EDIT_RECORD)
async def edit_currency(scope: PlayerScope, command: EditCurrency) -> Effect:
    ctx = await scope.context("currency_edit")
    row = await control.edit_currency(ctx, command.currency_id, purity=command.purity, trust=command.trust, supply=command.supply)
    await control_depth.rename_currency(ctx, row, command.name, command.metal, command.hold)
    return Effect(f"{row.name}: purity {row.purity}, trust {row.trust}, {row.supply} coins abroad.", row.item_entity_id)


@player_action("currency:debase", ActionKind.OTHER)
async def debase(scope: PlayerScope, command: CurrencyTarget) -> Effect:
    row = await control.debase_currency(await scope.context("currency_debase"), command.currency_id)
    return Effect(f"{row.name} was debased to purity {row.purity}.", row.item_entity_id)


@player_action("currency:use", ActionKind.EDIT_RECORD)
async def use_currency(scope: PlayerScope, command: UseCurrency) -> Effect:
    await control.use_currency(await scope.context("currency_use"), command.community_id, command.currency_id)
    return Effect("The community now counts in that coin." if command.currency_id is not None else "The community trades in kind again.", command.community_id)


@player_action("loan:forgive", ActionKind.OTHER)
async def forgive_loan(scope: PlayerScope, command: LoanTarget) -> Effect:
    loan = await control.forgive(await scope.context("loan_forgive"), command.loan_id)
    return Effect("The loan is forgiven.", loan.borrower_entity_id)


@player_action("hoard:inject", ActionKind.OTHER)
async def inject_hoard(scope: PlayerScope, command: InjectHoard) -> Effect:
    added = await control.hoard(await scope.context("hoard_inject"), command.community_id, command.metal, command.units, command.world_material_id)
    what = "a substance of this world" if command.world_material_id is not None else command.metal.value.replace("_", " ")
    return Effect(f"A hoard of {added} loads of {what} flooded the market.", command.community_id, values={"added": added})
