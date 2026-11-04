from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select, update

from aerona.catalog.materials import MATERIALS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import (
    PROPERTY_COLUMNS,
    CommunityStockRow,
    CurrencyRow,
    LoanRow,
    MarketPriceHoldRow,
    NodeMaterialRow,
    ResourceProfileRow,
    ResourceWorkerRow,
    WorkshopRow,
    WorldMaterialRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, LoanStatus, MaterialFamily, MaterialOrigin, MaterialSlot, WorkshopKind
from aerona.domain.enums.entity import SOCIETY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.context import TickContext
from aerona.engine.economy.control import community, edit_material, resource
from aerona.engine.economy.deposits import Deposit, describe, open_deposit
from aerona.engine.economy.extraction import write_reserve
from aerona.engine.economy.materials import set_node_material
from aerona.engine.economy.provenance import ensure_materials
from aerona.engine.economy.stocks import goods_of, sync_aggregates
from aerona.engine.economy.workshop_designs import assign_design
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in

NODE_TYPES = frozenset({EntityType.ITEM, EntityType.STRUCTURE, EntityType.VESSEL, EntityType.ARMY})
LENDERS = frozenset({EntityType.FACTION, *SOCIETY_TYPES, EntityType.POLITY})
BORROWERS = frozenset({*SOCIETY_TYPES, EntityType.POLITY, EntityType.FACTION})
ISSUERS = frozenset({*SOCIETY_TYPES, EntityType.FACTION, EntityType.POLITY})
RESOURCE_FIELDS = ("required_level", "byproduct_pct", "sealed_until_epoch")


@dataclass(frozen=True)
class Substance:
    world_id: int
    name: str
    family: MaterialFamily
    values: Mapping[str, int]
    base_kind: MaterialKind | None = None
    branch: KnowledgeBranch | None = None
    level: int = 0
    description: str | None = None
    place_id: int | None = None


def percent(key: str, value: int) -> int:
    if not 0 <= value <= PERCENT:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from 0 to {PERCENT}.")
    return value


def substance_values(base_kind: MaterialKind | None, values: Mapping[str, int]) -> dict[str, int]:
    unknown = set(values) - set(PROPERTY_COLUMNS)
    if unknown:
        raise ValidationFailedError(f"Unknown material properties: {', '.join(sorted(unknown))}.")
    spec = MATERIALS[base_kind] if base_kind is not None else None
    return {column: percent(column, values.get(column, getattr(spec, column) if spec is not None else PERCENT // 2)) for column in PROPERTY_COLUMNS}


async def world_material(ctx: TickContext, world_material_id: int) -> WorldMaterialRow:
    row = await ctx.session.get(WorldMaterialRow, world_material_id)
    if row is None:
        raise NotFoundError("No such substance.")
    return row


async def create_material(ctx: TickContext, substance: Substance) -> WorldMaterialRow:
    if not substance.name.strip():
        raise ValidationFailedError("A new material needs a name.")
    if substance.level < 0:
        raise ValidationFailedError("The craft level cannot fall below 0.")
    values = substance_values(substance.base_kind, substance.values)
    row = WorldMaterialRow(
        world_id=substance.world_id,
        origin=MaterialOrigin.DIVINE,
        base_kind=substance.base_kind,
        name=substance.name.strip(),
        description=(substance.description or "").strip() or describe(values),
        family=substance.family,
        branch=substance.branch,
        level=substance.level,
        created_epoch=ctx.epoch,
        **values,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    if substance.place_id is not None:
        place = await ctx.session.get(EntityRow, substance.place_id)
        if place is None or place.status is not EntityStatus.CANON or place.entity_type not in (EntityType.REGION, EntityType.PLACE):
            raise ValidationFailedError("A vein lies in a land or a place.")
        deposit = await open_deposit(
            ctx,
            Deposit(
                name=f"Vein of {row.name}",
                body=f"The Creator set a vein of {row.name} into {place.name}. {row.description}",
                place=place,
                commodity=CommodityKind.ORE,
                world_material_id=row.id,
                richness=clamp_int(values["rarity"], 1, PERCENT),
                quality=values["base_value"],
            ),
        )
        profile = await ctx.session.get(ResourceProfileRow, deposit.id)
        if profile is not None:
            profile.required_branch, profile.required_level = row.branch, row.level
        row.deposit_entity_id = deposit.id
    await ctx.session.flush()
    return row


async def hold_material(ctx: TickContext, world_id: int, material: MaterialKind | None, world_material_id: int | None, held: bool) -> WorldMaterialRow:
    if world_material_id is not None:
        row = await world_material(ctx, world_material_id)
    elif material is not None:
        from_catalog = await ctx.session.scalar(
            select(WorldMaterialRow).where(
                WorldMaterialRow.world_id == world_id, WorldMaterialRow.origin == MaterialOrigin.CATALOG, WorldMaterialRow.base_kind == material
            )
        )
        row = from_catalog if from_catalog is not None else await edit_material(ctx, world_id, material=material, world_material_id=None, values={}, name=None)
    else:
        raise ValidationFailedError("Choose a material or a substance.")
    row.held = held
    await ctx.session.flush()
    return row


async def delete_material(ctx: TickContext, world_id: int, material: MaterialKind | None, world_material_id: int | None) -> str:
    if world_material_id is None and material is not None:
        row = await ctx.session.scalar(
            select(WorldMaterialRow).where(
                WorldMaterialRow.world_id == world_id, WorldMaterialRow.origin == MaterialOrigin.CATALOG, WorldMaterialRow.base_kind == material
            )
        )
        if row is None:
            raise ValidationFailedError("That material already follows the catalog.")
        await ctx.session.delete(row)
        await ctx.session.flush()
        return MATERIALS[material].label
    if world_material_id is None:
        raise ValidationFailedError("Choose a material or a substance.")
    row = await world_material(ctx, world_material_id)
    label = row.name or "the substance"
    reshaped: list[int] = []
    for node in list(await ctx.session.scalars(select(NodeMaterialRow).where(NodeMaterialRow.world_material_id == row.id))):
        reshaped.append(node.node_id)
        await ctx.session.delete(node)
    for lot in list(await ctx.session.scalars(select(CommunityStockRow).where(CommunityStockRow.world_material_id == row.id))):
        await ctx.session.delete(lot)
    for profile in await ctx.session.scalars(select(ResourceProfileRow).where(ResourceProfileRow.world_material_id == row.id)):
        profile.world_material_id = None
        profile.material = row.base_kind
    await ctx.session.delete(row)
    await ctx.session.flush()
    for node_id in reshaped:
        entity = await ctx.session.get(EntityRow, node_id)
        if entity is not None:
            await ensure_materials(ctx.session, entity, rules=ctx.rules)
    return label


async def made_thing(ctx: TickContext, node_id: int) -> EntityRow:
    entity = await ctx.session.get(EntityRow, node_id)
    if entity is None or entity.entity_type not in NODE_TYPES or entity.status is not EntityStatus.CANON:
        raise NotFoundError("Only an item, a structure, a vessel or an army is made of a material.")
    return entity


async def set_slot(
    ctx: TickContext, node_id: int, slot: MaterialSlot, material: MaterialKind | None, world_material_id: int | None, *, hold: bool
) -> NodeMaterialRow:
    await made_thing(ctx, node_id)
    if material is None and world_material_id is None:
        raise ValidationFailedError("Choose the material to make it of.")
    if world_material_id is not None:
        await world_material(ctx, world_material_id)
    await set_node_material(ctx.session, node_id, slot, material, world_material_id, force=True)
    row = await ctx.session.get(NodeMaterialRow, (node_id, slot))
    if row is None:
        raise ValidationFailedError("The material could not be set.")
    row.held = hold
    await ctx.session.flush()
    return row


async def release_slot(ctx: TickContext, node_id: int, slot: MaterialSlot) -> NodeMaterialRow:
    row = await ctx.session.get(NodeMaterialRow, (node_id, slot))
    if row is None:
        raise ValidationFailedError("Nothing is set in that slot.")
    row.held = False
    await ctx.session.flush()
    return row


async def clear_slot(ctx: TickContext, node_id: int, slot: MaterialSlot) -> None:
    await made_thing(ctx, node_id)
    await set_node_material(ctx.session, node_id, slot, None, None, force=True)
    await ctx.session.flush()


async def lot(
    ctx: TickContext, community_id: int, commodity: CommodityKind, material: MaterialKind | None, world_material_id: int | None
) -> CommunityStockRow | None:
    statement = select(CommunityStockRow).where(CommunityStockRow.community_entity_id == community_id, CommunityStockRow.commodity == commodity)
    for row in await ctx.session.scalars(statement):
        if row.material == material and row.world_material_id == world_material_id:
            return row
    return None


async def set_stock(
    ctx: TickContext,
    community_id: int,
    commodity: CommodityKind,
    *,
    material: MaterialKind | None,
    world_material_id: int | None,
    quantity: int,
    quality: int,
    hold: bool | None,
) -> CommunityStockRow:
    entity = await community(ctx, community_id)
    if world_material_id is not None:
        await world_material(ctx, world_material_id)
    if quantity < 0:
        raise ValidationFailedError("A store cannot hold less than nothing.")
    row = await lot(ctx, entity.id, commodity, material if world_material_id is None else None, world_material_id)
    ledger = goods_of(ctx.session, ctx.epoch)
    if row is None:
        await ledger.add(entity.id, commodity, max(1, quantity), GoodsFlow.PLAYER, material=material, world_material_id=world_material_id, quality=quality)
        row = await lot(ctx, entity.id, commodity, material if world_material_id is None else None, world_material_id)
        if row is None:
            raise ValidationFailedError("The store could not be set.")
    await ledger.record(entity.id, commodity, GoodsFlow.PLAYER, quantity - row.quantity)
    row.quantity = quantity
    row.quality = percent("quality", quality)
    if hold is not None:
        row.held = hold
    await ctx.session.flush()
    await sync_aggregates(ctx.session, ctx.rules, entity)
    return row


async def release_stock(ctx: TickContext, lot_id: int) -> CommunityStockRow:
    row = await ctx.session.get(CommunityStockRow, lot_id)
    if row is None:
        raise NotFoundError("No such store.")
    row.held = False
    await ctx.session.flush()
    return row


async def edit_workshop(
    ctx: TickContext,
    community_id: int,
    kind: WorkshopKind,
    *,
    fleet: int | None,
    idle: int | None,
    structure_id: int | None,
    hold: bool | None,
    design_id: int | None = None,
) -> WorkshopRow:
    entity = await community(ctx, community_id)
    row = await ctx.session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == entity.id, WorkshopRow.kind == kind))
    if row is None:
        raise ValidationFailedError("Raise the workshop first.")
    if fleet is not None:
        row.fleet = max(0, fleet)
    if idle is not None:
        row.idle_epochs = max(0, idle)
    if structure_id is not None:
        structure = await ctx.session.get(EntityRow, structure_id) if structure_id > 0 else None
        if structure_id > 0 and (structure is None or structure.entity_type is not EntityType.STRUCTURE):
            raise ValidationFailedError("A workshop stands in a structure.")
        row.structure_entity_id = structure.id if structure is not None else None
    if design_id is not None:
        await assign_design(ctx, row, design_id)
    if hold is not None:
        row.held = hold
    await ctx.session.flush()
    return row


@dataclass(frozen=True)
class NewDeposit:
    place_id: int
    name: str
    commodity: CommodityKind
    material: MaterialKind | None
    world_material_id: int | None
    reserve: int
    richness: int
    quality: int
    revealed: bool
    required_branch: KnowledgeBranch | None
    required_level: int


async def create_resource(ctx: TickContext, spec: NewDeposit) -> EntityRow:
    place = await ctx.session.get(EntityRow, spec.place_id)
    if place is None or place.status is not EntityStatus.CANON or place.entity_type not in (EntityType.REGION, EntityType.PLACE, *SOCIETY_TYPES):
        raise ValidationFailedError("A deposit lies in a land, a place or a settlement.")
    if not spec.name.strip():
        raise ValidationFailedError("A deposit needs a name.")
    if spec.world_material_id is not None:
        await world_material(ctx, spec.world_material_id)
    made = await open_deposit(
        ctx,
        Deposit(
            name=spec.name.strip(),
            body=f"The Creator set {spec.name.strip()} into {place.name}.",
            place=place,
            commodity=spec.commodity,
            material=spec.material if spec.world_material_id is None else None,
            world_material_id=spec.world_material_id,
            reserve=max(1, spec.reserve),
            richness=clamp_int(spec.richness, 1, PERCENT),
            quality=percent("quality", spec.quality),
            revealed=spec.revealed,
        ),
    )
    profile = await ctx.session.get(ResourceProfileRow, made.id)
    if profile is not None and (spec.required_branch is not None or spec.required_level):
        profile.required_branch, profile.required_level = spec.required_branch, max(0, spec.required_level)
    await ctx.session.flush()
    return made


async def edit_resource_depth(
    ctx: TickContext,
    resource_id: int,
    *,
    fields: Mapping[str, int | None],
    required_branch: KnowledgeBranch | None,
    clear_branch: bool,
    byproduct: MaterialKind | None,
    clear_byproduct: bool,
    world_material_id: int | None,
    hold: bool | None,
) -> ResourceProfileRow:
    entity, profile = await resource(ctx, resource_id)
    unknown = set(fields) - set(RESOURCE_FIELDS)
    if unknown:
        raise ValidationFailedError(f"Unknown resource fields: {', '.join(sorted(unknown))}.")
    for key, value in fields.items():
        if key == "sealed_until_epoch":
            profile.sealed_until_epoch = value
            continue
        if value is None or value < 0:
            raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} cannot be empty or below 0.")
        setattr(profile, key, percent(key, value) if key == "byproduct_pct" else value)
    if required_branch is not None or clear_branch:
        profile.required_branch = None if clear_branch else required_branch
    if byproduct is not None or clear_byproduct:
        profile.byproduct_material = None if clear_byproduct else byproduct
    if world_material_id is not None:
        if world_material_id > 0:
            await world_material(ctx, world_material_id)
            profile.world_material_id, profile.material = world_material_id, None
        else:
            profile.world_material_id = None
    if hold is not None:
        profile.held = hold
    write_reserve(entity, profile, profile.reserve, force=True)
    await ctx.session.flush()
    return profile


async def delete_resource(ctx: TickContext, resource_id: int) -> EntityRow:
    entity, _ = await resource(ctx, resource_id)
    await retire_in(ctx, entity, "unmade by the Creator", status=EntityStatus.DESTROYED, close_bonds=True)
    await ctx.session.flush()
    return entity


async def set_workers(ctx: TickContext, resource_id: int, community_id: int, workers: int | None, hold: bool) -> ResourceWorkerRow:
    await resource(ctx, resource_id)
    entity = await community(ctx, community_id)
    row = await ctx.session.get(ResourceWorkerRow, (resource_id, entity.id))
    if row is None:
        row = ResourceWorkerRow(resource_entity_id=resource_id, community_entity_id=entity.id, workers=0)
        ctx.session.add(row)
    if workers is not None:
        if workers < 0:
            raise ValidationFailedError("Workers cannot fall below 0.")
        row.workers = workers
    row.held = hold
    await ctx.session.flush()
    return row


async def hold_price(ctx: TickContext, market_id: int, commodity: CommodityKind, price: int | None, supply: int | None) -> MarketPriceHoldRow | None:
    market = await community(ctx, market_id)
    row = await ctx.session.get(MarketPriceHoldRow, (market.id, commodity))
    if price is None and supply is None:
        if row is not None:
            await ctx.session.delete(row)
        await ctx.session.flush()
        return None
    if (price is not None and price < 0) or (supply is not None and supply < 0):
        raise ValidationFailedError("A price or a supply cannot fall below 0.")
    if row is None:
        row = MarketPriceHoldRow(market_entity_id=market.id, commodity=commodity, set_epoch=ctx.epoch)
        ctx.session.add(row)
    row.price, row.supply, row.set_epoch = price, supply, ctx.epoch
    await ctx.session.flush()
    return row


async def issuer(ctx: TickContext, issuer_id: int) -> EntityRow:
    entity = await ctx.session.get(EntityRow, issuer_id)
    if entity is None or entity.status is not EntityStatus.CANON or entity.entity_type not in ISSUERS:
        raise ValidationFailedError("Coins are struck by a people, a settlement, a faction or a realm.")
    return entity


@dataclass(frozen=True)
class NewCoin:
    issuer_id: int
    name: str
    metal: MaterialKind
    purity: int
    trust: int
    supply: int


async def create_currency(ctx: TickContext, coin: NewCoin) -> CurrencyRow:
    entity = await issuer(ctx, coin.issuer_id)
    if not coin.name.strip():
        raise ValidationFailedError("A coin needs a name.")
    item = await create_record(
        ctx,
        RecordSpec(
            name=coin.name.strip(),
            entity_type=EntityType.ITEM,
            stats=ItemStats(damage=0, protection=0, might=0, curse=0),
            body=f"The Creator gave {entity.name} a coin of {coin.metal.value.replace('_', ' ')}.",
            power=ctx.rules.trade.currency_power,
            world_id=entity.world_id,
            location_id=entity.id if entity.entity_type is EntityType.SETTLEMENT else entity.location_id,
            subtype="currency",
            engine_kind=EngineKind.CURRENCY,
        ),
    )
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(entity.id, item.id, BondKind.PRODUCED, ctx.epoch, "given by the Creator"))
    await bonds.connect(BondDraft(entity.id, item.id, BondKind.OWNS, ctx.epoch, "given by the Creator"))
    row = CurrencyRow(
        issuer_entity_id=entity.id,
        item_entity_id=item.id,
        name=item.name,
        metal=coin.metal,
        purity=percent("purity", coin.purity),
        trust=percent("trust", coin.trust),
        supply=max(0, coin.supply),
        minted_epoch=ctx.epoch,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await set_node_material(ctx.session, item.id, MaterialSlot.BODY, coin.metal, force=True)
    society = await ctx.session.get(CommunitySocietyRow, entity.id)
    if society is not None and society.currency_id is None:
        society.currency_id = row.id
    await ctx.session.flush()
    return row


async def rename_currency(ctx: TickContext, row: CurrencyRow, name: str | None, metal: MaterialKind | None, hold: bool | None) -> CurrencyRow:
    if name is not None:
        if not name.strip():
            raise ValidationFailedError("A coin needs a name.")
        row.name = name.strip()
    if metal is not None:
        row.metal = metal
        if row.item_entity_id is not None:
            await set_node_material(ctx.session, row.item_entity_id, MaterialSlot.BODY, metal, force=True)
    if hold is not None:
        row.held = hold
    await ctx.session.flush()
    return row


async def delete_currency(ctx: TickContext, currency_id: int) -> str:
    row = await ctx.session.get(CurrencyRow, currency_id)
    if row is None:
        raise NotFoundError("No such currency.")
    name = row.name
    await ctx.session.execute(update(CommunitySocietyRow).where(CommunitySocietyRow.currency_id == row.id).values(currency_id=None))
    for loan in await ctx.session.scalars(select(LoanRow).where(LoanRow.currency_id == row.id)):
        loan.currency_id = None
    for bond in await ctx.session.scalars(select(BondRow).where(BondRow.debt_currency_id == row.id)):
        bond.debt_currency_id = None
    item = await ctx.session.get(EntityRow, row.item_entity_id) if row.item_entity_id is not None else None
    await ctx.session.delete(row)
    if item is not None and item.status is EntityStatus.CANON:
        await retire_in(ctx, item, "melted down by the Creator", status=EntityStatus.DESTROYED)
    await ctx.session.flush()
    return name


@dataclass(frozen=True)
class NewLoan:
    lender_id: int
    borrower_id: int
    principal: int
    interest_pct: int
    term_epochs: int
    currency_id: int | None
    purpose: str


async def party(ctx: TickContext, node_id: int, allowed: frozenset[EntityType], what: str) -> EntityRow:
    entity = await ctx.session.get(EntityRow, node_id)
    if entity is None or entity.status is not EntityStatus.CANON or entity.entity_type not in allowed:
        raise ValidationFailedError(what)
    return entity


async def grant_loan(ctx: TickContext, terms: NewLoan) -> LoanRow:
    lender = await party(ctx, terms.lender_id, LENDERS, "A loan is made by a guild, a people, a settlement or a realm.")
    borrower = await party(ctx, terms.borrower_id, BORROWERS, "A loan is owed by a people, a settlement, a faction or a realm.")
    if lender.id == borrower.id:
        raise ValidationFailedError("No one lends to itself.")
    if terms.principal < 1 or terms.term_epochs < 1:
        raise ValidationFailedError("A loan lends at least 1 and runs at least 1 epoch.")
    if terms.currency_id is not None and await ctx.session.get(CurrencyRow, terms.currency_id) is None:
        raise NotFoundError("No such currency.")
    loan = LoanRow(
        lender_entity_id=lender.id,
        borrower_entity_id=borrower.id,
        currency_id=terms.currency_id,
        principal=terms.principal,
        interest_pct=percent("interest", terms.interest_pct),
        issued_epoch=ctx.epoch,
        due_epoch=ctx.epoch + terms.term_epochs,
        status=LoanStatus.OPEN,
        purpose=terms.purpose.strip()[:64] or "war",
    )
    ctx.session.add(loan)
    await ctx.session.flush()
    return loan


async def loan_row(ctx: TickContext, loan_id: int) -> LoanRow:
    row = await ctx.session.get(LoanRow, loan_id)
    if row is None:
        raise NotFoundError("No such loan.")
    return row


async def edit_loan(ctx: TickContext, loan_id: int, values: Mapping[str, int | None], status: LoanStatus | None, hold: bool | None) -> LoanRow:
    row = await loan_row(ctx, loan_id)
    for key in ("principal", "interest_pct", "due_epoch", "repaid"):
        value = values.get(key)
        if value is None:
            continue
        if key == "interest_pct":
            value = percent("interest", value)
        if value < (1 if key == "principal" else 0):
            raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is too low.")
        setattr(row, key, value)
    if status is not None:
        row.status = status
    if hold is not None:
        row.held = hold
    await ctx.session.flush()
    return row


async def delete_loan(ctx: TickContext, loan_id: int) -> LoanRow:
    row = await loan_row(ctx, loan_id)
    await ctx.session.delete(row)
    await ctx.session.flush()
    return row
