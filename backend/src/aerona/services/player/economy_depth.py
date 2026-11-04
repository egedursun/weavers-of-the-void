from pydantic import Field

from aerona.catalog.commodities import commodity_label
from aerona.catalog.production import WORKSHOP_LABELS
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.economy import CommodityKind, LoanStatus, MaterialFamily, MaterialSlot, WorkshopKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.economy import control, control_depth, workshop_designs
from aerona.engine.economy.control_depth import NewCoin, NewDeposit, NewLoan, Substance
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME_MAX = 60
DESCRIPTION_MAX = 600
PURPOSE_MAX = 64


class CreateMaterial(Command):
    world_id: int
    name: str = Field(min_length=1, max_length=NAME_MAX)
    family: MaterialFamily
    base_kind: MaterialKind | None = None
    values: dict[str, int] = Field(default_factory=dict)
    branch: KnowledgeBranch | None = None
    level: int = Field(default=0, ge=0, le=20)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    place_id: int | None = None


class MaterialTarget(Command):
    world_id: int
    material: MaterialKind | None = None
    world_material_id: int | None = None


class SlotMaterial(Command):
    node_id: int
    slot: MaterialSlot = MaterialSlot.BODY
    material: MaterialKind | None = None
    world_material_id: int | None = None
    hold: bool = True


class SlotTarget(Command):
    node_id: int
    slot: MaterialSlot = MaterialSlot.BODY


class SetStock(Command):
    community_id: int
    commodity: CommodityKind
    material: MaterialKind | None = None
    world_material_id: int | None = None
    quantity: int = Field(ge=0)
    quality: int = Field(default=50, ge=0, le=100)
    hold: bool | None = None


class StockTarget(Command):
    lot_id: int


class EditWorkshop(Command):
    community_id: int
    kind: WorkshopKind
    fleet: int | None = Field(default=None, ge=0)
    idle_epochs: int | None = Field(default=None, ge=0)
    structure_id: int | None = Field(default=None, ge=0)
    design_id: int | None = Field(default=None, ge=0)
    hold: bool | None = None


class CreateWorkshopDesign(Command):
    world_id: int
    base_kind: WorkshopKind
    name: str = Field(min_length=1, max_length=NAME_MAX)
    values: dict[str, int] = Field(default_factory=dict)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)


class EditWorkshopDesign(Command):
    design_id: int
    values: dict[str, int] = Field(default_factory=dict)
    name: str | None = Field(default=None, max_length=NAME_MAX)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    hold: bool | None = None


class DesignTarget(Command):
    design_id: int


class WorkshopTarget(Command):
    community_id: int
    kind: WorkshopKind


class CreateResource(Command):
    place_id: int
    name: str = Field(min_length=1, max_length=NAME_MAX)
    commodity: CommodityKind
    material: MaterialKind | None = None
    world_material_id: int | None = None
    reserve: int = Field(default=1500, ge=1)
    richness: int = Field(default=60, ge=1, le=100)
    quality: int = Field(default=60, ge=0, le=100)
    revealed: bool = True
    required_branch: KnowledgeBranch | None = None
    required_level: int = Field(default=0, ge=0, le=20)


class EditResourceDepth(Command):
    resource_id: int
    required_level: int | None = Field(default=None, ge=0, le=20)
    byproduct_pct: int | None = Field(default=None, ge=0, le=100)
    sealed_until_epoch: int | None = Field(default=None, ge=0)
    unseal: bool = False
    required_branch: KnowledgeBranch | None = None
    clear_branch: bool = False
    byproduct_material: MaterialKind | None = None
    clear_byproduct: bool = False
    world_material_id: int | None = Field(default=None, ge=0)
    hold: bool | None = None


class ResourceTarget(Command):
    resource_id: int


class SetWorkers(Command):
    resource_id: int
    community_id: int
    workers: int | None = Field(default=None, ge=0)
    hold: bool = True


class HoldPrice(Command):
    market_id: int
    commodity: CommodityKind
    price: int | None = Field(default=None, ge=0)
    supply: int | None = Field(default=None, ge=0)


class PriceTarget(Command):
    market_id: int
    commodity: CommodityKind


class CreateCurrency(Command):
    issuer_id: int
    name: str = Field(min_length=1, max_length=NAME_MAX)
    metal: MaterialKind = MaterialKind.SILVER
    purity: int = Field(default=90, ge=0, le=100)
    trust: int = Field(default=70, ge=0, le=100)
    supply: int = Field(default=0, ge=0)


class CurrencyTarget(Command):
    currency_id: int


class GrantLoan(Command):
    lender_id: int
    borrower_id: int
    principal: int = Field(ge=1)
    interest_pct: int = Field(default=20, ge=0, le=100)
    term_epochs: int = Field(default=3, ge=1, le=100)
    currency_id: int | None = None
    purpose: str = Field(default="war", max_length=PURPOSE_MAX)


class EditLoan(Command):
    loan_id: int
    principal: int | None = Field(default=None, ge=1)
    interest_pct: int | None = Field(default=None, ge=0, le=100)
    due_epoch: int | None = Field(default=None, ge=0)
    repaid: int | None = Field(default=None, ge=0)
    status: LoanStatus | None = None
    hold: bool | None = None


class LoanTarget(Command):
    loan_id: int


def material_word(material: MaterialKind | None) -> str:
    return material.value.replace("_", " ") if material is not None else "a substance of this world"


@player_action("material:create", ActionKind.CREATE_ENTITY)
async def create_material(scope: PlayerScope, command: CreateMaterial) -> Effect:
    ctx = await scope.context("material_create")
    row = await control_depth.create_material(
        ctx,
        Substance(
            world_id=command.world_id,
            name=command.name,
            family=command.family,
            values=command.values,
            base_kind=command.base_kind,
            branch=command.branch,
            level=command.level,
            description=command.description,
            place_id=command.place_id,
        ),
    )
    created = (row.deposit_entity_id,) if row.deposit_entity_id is not None else ()
    return Effect(f"{row.name} was forged into the world.", row.deposit_entity_id, created_ids=created, values={"world_material_id": row.id})


@player_action("material:delete", ActionKind.EDIT_RECORD)
async def delete_material(scope: PlayerScope, command: MaterialTarget) -> Effect:
    label = await control_depth.delete_material(await scope.context("material_delete"), command.world_id, command.material, command.world_material_id)
    if command.world_material_id is None:
        return Effect(f"{label} follows the catalog again in this world.")
    return Effect(f"{label} was unmade; what was made of it took other stuff.")


@player_action("material:hold", ActionKind.EDIT_RECORD)
async def hold_material(scope: PlayerScope, command: MaterialTarget) -> Effect:
    row = await control_depth.hold_material(await scope.context("material_hold"), command.world_id, command.material, command.world_material_id, True)
    return Effect(f"{row.name or material_word(row.base_kind).capitalize()} is held as you set it.", values={"world_material_id": row.id})


@player_action("material:release", ActionKind.EDIT_RECORD)
async def release_material(scope: PlayerScope, command: MaterialTarget) -> Effect:
    row = await control_depth.hold_material(await scope.context("material_release"), command.world_id, command.material, command.world_material_id, False)
    return Effect(f"{row.name or material_word(row.base_kind).capitalize()} is no longer held.", values={"world_material_id": row.id})


@player_action("node_material:set", ActionKind.EDIT_RECORD)
async def set_slot(scope: PlayerScope, command: SlotMaterial) -> Effect:
    await control_depth.set_slot(
        await scope.context("node_material_set"), command.node_id, command.slot, command.material, command.world_material_id, hold=command.hold
    )
    held = " and held" if command.hold else ""
    return Effect(f"Its {command.slot.value} is now made of {material_word(command.material)}{held}.", command.node_id)


@player_action("node_material:release", ActionKind.EDIT_RECORD)
async def release_slot(scope: PlayerScope, command: SlotTarget) -> Effect:
    await control_depth.release_slot(await scope.context("node_material_release"), command.node_id, command.slot)
    return Effect(f"Its {command.slot.value} may change with the world again.", command.node_id)


@player_action("node_material:clear", ActionKind.EDIT_RECORD)
async def clear_slot(scope: PlayerScope, command: SlotTarget) -> Effect:
    await control_depth.clear_slot(await scope.context("node_material_clear"), command.node_id, command.slot)
    return Effect(f"Its {command.slot.value} is unmade; its makers will choose anew.", command.node_id)


@player_action("stock:set", ActionKind.EDIT_RECORD)
async def set_stock(scope: PlayerScope, command: SetStock) -> Effect:
    row = await control_depth.set_stock(
        await scope.context("stock_set"),
        command.community_id,
        command.commodity,
        material=command.material,
        world_material_id=command.world_material_id,
        quantity=command.quantity,
        quality=command.quality,
        hold=command.hold,
    )
    held = ", held" if row.held else ""
    return Effect(f"{row.quantity} {commodity_label(command.commodity).lower()} in the stores{held}.", command.community_id, values={"lot_id": row.id})


@player_action("stock:release", ActionKind.EDIT_RECORD)
async def release_stock(scope: PlayerScope, command: StockTarget) -> Effect:
    row = await control_depth.release_stock(await scope.context("stock_release"), command.lot_id)
    return Effect("The store may be eaten and filled again.", row.community_entity_id)


@player_action("workshop:edit", ActionKind.EDIT_RECORD)
async def edit_workshop(scope: PlayerScope, command: EditWorkshop) -> Effect:
    row = await control_depth.edit_workshop(
        await scope.context("workshop_edit"),
        command.community_id,
        command.kind,
        fleet=command.fleet,
        idle=command.idle_epochs,
        structure_id=command.structure_id,
        hold=command.hold,
        design_id=command.design_id,
    )
    held = ", held" if row.held else ""
    return Effect(f"{WORKSHOP_LABELS[command.kind]} set{held}.", command.community_id)


@player_action("workshop_design:create", ActionKind.CREATE_ENTITY)
async def create_design(scope: PlayerScope, command: CreateWorkshopDesign) -> Effect:
    row = await workshop_designs.create_design(
        await scope.context("workshop_design_create"),
        workshop_designs.NewDesign(command.world_id, command.base_kind, command.name, command.values, command.description),
    )
    return Effect(f"{row.name} is drawn as a new {WORKSHOP_LABELS[row.base_kind].lower()}.", values={"design_id": row.id})


@player_action("workshop_design:edit", ActionKind.EDIT_RECORD)
async def edit_design(scope: PlayerScope, command: EditWorkshopDesign) -> Effect:
    row = await workshop_designs.edit_design(
        await scope.context("workshop_design_edit"), command.design_id, command.values, name=command.name, description=command.description, hold=command.hold
    )
    return Effect(f"{row.name} is redrawn{', held' if row.held else ''}.", values={"design_id": row.id})


@player_action("workshop_design:release", ActionKind.EDIT_RECORD)
async def release_design(scope: PlayerScope, command: DesignTarget) -> Effect:
    row = await workshop_designs.edit_design(await scope.context("workshop_design_release"), command.design_id, {}, name=None, description=None, hold=False)
    return Effect(f"{row.name} is no longer held.", values={"design_id": row.id})


@player_action("workshop_design:delete", ActionKind.EDIT_RECORD)
async def delete_design(scope: PlayerScope, command: DesignTarget) -> Effect:
    name = await workshop_designs.delete_design(await scope.context("workshop_design_delete"), command.design_id)
    return Effect(f"{name} is torn up; its workshops work as plain ones again.")


@player_action("workshop:release", ActionKind.EDIT_RECORD)
async def release_workshop(scope: PlayerScope, command: WorkshopTarget) -> Effect:
    await control_depth.edit_workshop(
        await scope.context("workshop_release"), command.community_id, command.kind, fleet=None, idle=None, structure_id=None, hold=False
    )
    return Effect(f"{WORKSHOP_LABELS[command.kind]} may grow and decline again.", command.community_id)


@player_action("resource:create", ActionKind.CREATE_ENTITY)
async def create_resource(scope: PlayerScope, command: CreateResource) -> Effect:
    made = await control_depth.create_resource(
        await scope.context("resource_create"),
        NewDeposit(
            place_id=command.place_id,
            name=command.name,
            commodity=command.commodity,
            material=command.material,
            world_material_id=command.world_material_id,
            reserve=command.reserve,
            richness=command.richness,
            quality=command.quality,
            revealed=command.revealed,
            required_branch=command.required_branch,
            required_level=command.required_level,
        ),
    )
    return Effect(f"{made.name} lies in the earth now.", made.id, created_ids=(made.id,))


@player_action("resource:edit", ActionKind.EDIT_RECORD)
async def edit_resource(scope: PlayerScope, command: EditResourceDepth) -> Effect:
    fields: dict[str, int | None] = {
        key: value for key, value in (("required_level", command.required_level), ("byproduct_pct", command.byproduct_pct)) if value is not None
    }
    if command.unseal:
        fields["sealed_until_epoch"] = None
    elif command.sealed_until_epoch is not None:
        fields["sealed_until_epoch"] = command.sealed_until_epoch
    profile = await control_depth.edit_resource_depth(
        await scope.context("resource_edit"),
        command.resource_id,
        fields=fields,
        required_branch=command.required_branch,
        clear_branch=command.clear_branch,
        byproduct=command.byproduct_material,
        clear_byproduct=command.clear_byproduct,
        world_material_id=command.world_material_id,
        hold=command.hold,
    )
    held = " and held" if profile.held else ""
    return Effect(f"The resource is set{held}.", command.resource_id)


@player_action("resource:release", ActionKind.EDIT_RECORD)
async def release_resource(scope: PlayerScope, command: ResourceTarget) -> Effect:
    await control_depth.edit_resource_depth(
        await scope.context("resource_release"),
        command.resource_id,
        fields={},
        required_branch=None,
        clear_branch=False,
        byproduct=None,
        clear_byproduct=False,
        world_material_id=None,
        hold=False,
    )
    return Effect("The resource may be worked down and grow back again.", command.resource_id)


@player_action("resource:delete", ActionKind.EDIT_RECORD)
async def delete_resource(scope: PlayerScope, command: ResourceTarget) -> Effect:
    entity = await control_depth.delete_resource(await scope.context("resource_delete"), command.resource_id)
    return Effect(f"{entity.name} was unmade.", entity.id)


@player_action("resource:workers", ActionKind.EDIT_RECORD)
async def set_workers(scope: PlayerScope, command: SetWorkers) -> Effect:
    row = await control_depth.set_workers(await scope.context("resource_workers"), command.resource_id, command.community_id, command.workers, command.hold)
    held = ", held" if row.held else ", left to the labour of the community"
    return Effect(f"{row.workers} work the resource{held}.", command.resource_id)


@player_action("market:hold_price", ActionKind.EDIT_RECORD)
async def hold_price(scope: PlayerScope, command: HoldPrice) -> Effect:
    row = await control_depth.hold_price(await scope.context("market_price"), command.market_id, command.commodity, command.price, command.supply)
    label = commodity_label(command.commodity).lower()
    if row is None:
        return Effect(f"The price of {label} follows the market again.", command.market_id)
    return Effect(f"The price of {label} is held.", command.market_id)


@player_action("market:release_price", ActionKind.EDIT_RECORD)
async def release_price(scope: PlayerScope, command: PriceTarget) -> Effect:
    await control_depth.hold_price(await scope.context("market_release"), command.market_id, command.commodity, None, None)
    return Effect(f"The price of {commodity_label(command.commodity).lower()} follows the market again.", command.market_id)


@player_action("currency:create", ActionKind.CREATE_ENTITY)
async def create_currency(scope: PlayerScope, command: CreateCurrency) -> Effect:
    row = await control_depth.create_currency(
        await scope.context("currency_create"),
        NewCoin(issuer_id=command.issuer_id, name=command.name, metal=command.metal, purity=command.purity, trust=command.trust, supply=command.supply),
    )
    created = (row.item_entity_id,) if row.item_entity_id is not None else ()
    return Effect(f"{row.name} is struck.", row.item_entity_id, created_ids=created, values={"currency_id": row.id})


@player_action("currency:release", ActionKind.EDIT_RECORD)
async def release_currency(scope: PlayerScope, command: CurrencyTarget) -> Effect:
    ctx = await scope.context("currency_release")
    row = await control_depth.rename_currency(ctx, await control.currency_row(ctx, command.currency_id), None, None, False)
    return Effect(f"{row.name} may drift with trust and supply again.", row.item_entity_id)


@player_action("currency:delete", ActionKind.EDIT_RECORD)
async def delete_currency(scope: PlayerScope, command: CurrencyTarget) -> Effect:
    name = await control_depth.delete_currency(await scope.context("currency_delete"), command.currency_id)
    return Effect(f"{name} was melted down; its users trade in kind again.")


@player_action("loan:grant", ActionKind.OTHER)
async def grant_loan(scope: PlayerScope, command: GrantLoan) -> Effect:
    loan = await control_depth.grant_loan(
        await scope.context("loan_grant"),
        NewLoan(
            lender_id=command.lender_id,
            borrower_id=command.borrower_id,
            principal=command.principal,
            interest_pct=command.interest_pct,
            term_epochs=command.term_epochs,
            currency_id=command.currency_id,
            purpose=command.purpose,
        ),
    )
    return Effect(
        f"A loan of {loan.principal} at {loan.interest_pct}% falls due in Epoch {loan.due_epoch}.", loan.borrower_entity_id, values={"loan_id": loan.id}
    )


@player_action("loan:edit", ActionKind.EDIT_RECORD)
async def edit_loan(scope: PlayerScope, command: EditLoan) -> Effect:
    values = {"principal": command.principal, "interest_pct": command.interest_pct, "due_epoch": command.due_epoch, "repaid": command.repaid}
    loan = await control_depth.edit_loan(await scope.context("loan_edit"), command.loan_id, values, command.status, command.hold)
    held = ", held" if loan.held else ""
    return Effect(f"The loan stands at {loan.principal} and {loan.interest_pct}%, due Epoch {loan.due_epoch}{held}.", loan.borrower_entity_id)


@player_action("loan:release", ActionKind.EDIT_RECORD)
async def release_loan(scope: PlayerScope, command: LoanTarget) -> Effect:
    loan = await control_depth.edit_loan(await scope.context("loan_release"), command.loan_id, {}, None, False)
    return Effect("The loan runs its course again.", loan.borrower_entity_id)


@player_action("loan:delete", ActionKind.EDIT_RECORD)
async def delete_loan(scope: PlayerScope, command: LoanTarget) -> Effect:
    loan = await control_depth.delete_loan(await scope.context("loan_delete"), command.loan_id)
    return Effect("The loan was struck from the ledgers as if it never was.", loan.borrower_entity_id)
