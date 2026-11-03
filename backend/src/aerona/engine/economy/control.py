from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.materials import MATERIALS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.economy import (
    PROPERTY_COLUMNS,
    CurrencyRow,
    LoanRow,
    ResourceProfileRow,
    TradeRouteProfileRow,
    TradeRouteTollRow,
    WorkshopRow,
    WorldMaterialRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, LoanStatus, MaterialOrigin, TradeRouteStatus, WorkshopKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, SOCIETY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.extraction import write_reserve
from aerona.engine.economy.money import debase, forgive_loan, inject_hoard
from aerona.engine.economy.routes import found_route, load_routes
from aerona.engine.economy.stocks import goods_of, holding, sync_aggregates
from aerona.engine.phases.environment import works_by_region
from aerona.engine.primitives.numbers import clamp_int

PROFILE_FIELDS = ("richness", "extraction_difficulty", "quality", "regeneration", "byproduct_pct", "initial_reserve")


async def community(ctx: TickContext, community_id: int) -> EntityRow:
    entity = await ctx.session.get(EntityRow, community_id)
    if entity is None or entity.entity_type not in SOCIETY_TYPES or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such people or settlement.")
    return entity


async def resource(ctx: TickContext, resource_id: int) -> tuple[EntityRow, ResourceProfileRow]:
    entity = await ctx.session.get(EntityRow, resource_id)
    profile = await ctx.session.get(ResourceProfileRow, resource_id)
    if entity is None or entity.entity_type is not EntityType.RESOURCE or profile is None:
        raise NotFoundError("No such resource.")
    return entity, profile


async def edit_material(
    ctx: TickContext, world_id: int, *, material: MaterialKind | None, world_material_id: int | None, values: Mapping[str, int], name: str | None
) -> WorldMaterialRow:
    unknown = set(values) - set(PROPERTY_COLUMNS) - {"level"}
    if unknown:
        raise ValidationFailedError(f"Unknown material properties: {', '.join(sorted(unknown))}.")
    if any(not 0 <= value <= PERCENT for key, value in values.items() if key != "level"):
        raise ValidationFailedError(f"Material properties run from 0 to {PERCENT}.")
    if world_material_id is not None:
        row = await ctx.session.get(WorldMaterialRow, world_material_id)
        if row is None:
            raise NotFoundError("No such substance.")
    elif material is not None:
        row = await ctx.session.scalar(
            select(WorldMaterialRow).where(
                WorldMaterialRow.world_id == world_id, WorldMaterialRow.origin == MaterialOrigin.CATALOG, WorldMaterialRow.base_kind == material
            )
        )
        if row is None:
            spec = MATERIALS[material]
            row = WorldMaterialRow(
                world_id=world_id,
                origin=MaterialOrigin.CATALOG,
                base_kind=material,
                family=spec.family,
                branch=spec.branch,
                level=spec.level,
                created_epoch=ctx.epoch,
                **{column: getattr(spec, column) for column in PROPERTY_COLUMNS},
            )
            ctx.session.add(row)
    else:
        raise ValidationFailedError("Choose a material or a substance to edit.")
    for key, value in values.items():
        setattr(row, key, value)
    if name is not None:
        row.name = name.strip() or None
    await ctx.session.flush()
    return row


async def grant_stock(ctx: TickContext, community_id: int, commodity: CommodityKind, quantity: int, *, material: MaterialKind | None, quality: int) -> int:
    entity = await community(ctx, community_id)
    ledger = goods_of(ctx.session, ctx.epoch)
    if quantity >= 0:
        moved = await ledger.add(entity.id, commodity, quantity, GoodsFlow.PLAYER, material=material, quality=quality)
    else:
        if await holding(ctx.session, entity.id, commodity, material) <= 0:
            raise ValidationFailedError("There is none of that in the stores to take away.")
        moved = -await ledger.take_units(entity.id, commodity, -quantity, GoodsFlow.PLAYER)
    await sync_aggregates(ctx.session, ctx.rules, entity)
    return moved


async def set_resource(ctx: TickContext, resource_id: int, *, reserve: int | None, fields: Mapping[str, int]) -> ResourceProfileRow:
    entity, profile = await resource(ctx, resource_id)
    unknown = set(fields) - set(PROFILE_FIELDS)
    if unknown:
        raise ValidationFailedError(f"Unknown resource fields: {', '.join(sorted(unknown))}.")
    for key, value in fields.items():
        if key == "initial_reserve" and value < 1:
            raise ValidationFailedError("A resource's first reserve must be at least 1.")
        if key not in ("initial_reserve", "regeneration") and not 0 <= value <= PERCENT:
            raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from 0 to {PERCENT}.")
        setattr(profile, key, max(0, value))
    write_reserve(entity, profile, profile.reserve if reserve is None else max(0, reserve))
    await ctx.session.flush()
    return profile


async def set_owner(ctx: TickContext, resource_id: int, owner_id: int | None) -> EntityRow | None:
    entity, _ = await resource(ctx, resource_id)
    bonds = BondRepository(ctx.session)
    for bond in await bonds.incoming(resource_id, BondKind.OWNS):
        await bonds.deactivate(bond, ctx.epoch, "taken by the Creator's hand")
    if owner_id is None:
        return None
    owner = await ctx.session.get(EntityRow, owner_id)
    if owner is None or owner.status is not EntityStatus.CANON or owner.entity_type not in (*COMMUNITY_TYPES, EntityType.MORTAL):
        raise ValidationFailedError("A resource is owned by a people, settlement, faction, cult or mortal.")
    await bonds.connect(BondDraft(owner.id, entity.id, BondKind.OWNS, ctx.epoch, "given by the Creator"))
    return owner


async def reveal(ctx: TickContext, resource_id: int, revealed: bool) -> ResourceProfileRow:
    _, profile = await resource(ctx, resource_id)
    profile.revealed = revealed
    await ctx.session.flush()
    return profile


async def set_workshop(ctx: TickContext, community_id: int, kind: WorkshopKind, level: int) -> WorkshopRow | None:
    entity = await community(ctx, community_id)
    row = await ctx.session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == entity.id, WorkshopRow.kind == kind))
    if level <= 0:
        if row is not None:
            await ctx.session.delete(row)
        await ctx.session.flush()
        return None
    if row is None:
        row = WorkshopRow(community_entity_id=entity.id, kind=kind, level=level, built_epoch=ctx.epoch)
        ctx.session.add(row)
    row.level = clamp_int(level, 1, ctx.rules.refining.max_level)
    row.idle_epochs = 0
    await ctx.session.flush()
    return row


async def open_route(ctx: TickContext, *, route_id: int | None, first_id: int | None, second_id: int | None) -> EntityRow:
    if route_id is not None:
        profile = await ctx.session.get(TradeRouteProfileRow, route_id)
        entity = await ctx.session.get(EntityRow, route_id)
        if profile is None or entity is None:
            raise NotFoundError("No such trade route.")
        profile.status = TradeRouteStatus.OPEN
        profile.closed_by_player = False
        profile.last_traffic_epoch = ctx.epoch
        entity.status = EntityStatus.CANON
        await ctx.session.flush()
        return entity
    if first_id is None or second_id is None or first_id == second_id:
        raise ValidationFailedError("A route joins two different markets.")
    book = await EconomyBook.load(ctx)
    first, second = await community(ctx, first_id), await community(ctx, second_id)
    if any(frozenset(route.ends) == frozenset((first.id, second.id)) for route in await load_routes(ctx)):
        raise ValidationFailedError(f"{first.name} and {second.name} are already joined by a route.")
    path = book.ground.atlas.region_path(book.ground.atlas.top_region(first.id), book.ground.atlas.top_region(second.id))
    if path is None:
        raise ValidationFailedError(f"No way leads from {first.name} to {second.name}.")
    for end in (first, second):
        if book.workshop(end.id, WorkshopKind.MARKET) is None:
            ctx.session.add(WorkshopRow(community_entity_id=end.id, kind=WorkshopKind.MARKET, level=1, built_epoch=ctx.epoch))
    route = await found_route(ctx, book, first, second, path, works=await works_by_region(ctx, book.ground))
    route.profile.status = TradeRouteStatus.OPEN
    route.profile.last_traffic_epoch = ctx.epoch
    route.entity.pending_name = True
    await ctx.session.flush()
    return route.entity


async def close_route(ctx: TickContext, route_id: int) -> EntityRow:
    profile = await ctx.session.get(TradeRouteProfileRow, route_id)
    entity = await ctx.session.get(EntityRow, route_id)
    if profile is None or entity is None:
        raise NotFoundError("No such trade route.")
    profile.status = TradeRouteStatus.CLOSED
    profile.closed_by_player = True
    await ctx.session.flush()
    return entity


async def set_toll(ctx: TickContext, route_id: int, region_id: int, rate: int | None) -> TradeRouteTollRow | None:
    toll = await ctx.session.get(TradeRouteTollRow, (route_id, region_id))
    if rate is None:
        if toll is not None:
            toll.set_by_player = False
        await ctx.session.flush()
        return toll
    if not 0 <= rate <= PERCENT:
        raise ValidationFailedError(f"A toll runs from 0 to {PERCENT}%.")
    if toll is None:
        raise ValidationFailedError("No one takes a toll in that region of the route yet.")
    toll.rate_pct = rate
    toll.set_by_player = True
    await ctx.session.flush()
    return toll


async def currency_row(ctx: TickContext, currency_id: int) -> CurrencyRow:
    row = await ctx.session.get(CurrencyRow, currency_id)
    if row is None:
        raise NotFoundError("No such currency.")
    return row


async def edit_currency(ctx: TickContext, currency_id: int, *, purity: int | None, trust: int | None, supply: int | None) -> CurrencyRow:
    row = await currency_row(ctx, currency_id)
    for key, value in (("purity", purity), ("trust", trust)):
        if value is not None:
            if not 0 <= value <= PERCENT:
                raise ValidationFailedError(f"{key.capitalize()} runs from 0 to {PERCENT}.")
            setattr(row, key, value)
    if supply is not None:
        row.supply = max(0, supply)
    await ctx.session.flush()
    return row


async def debase_currency(ctx: TickContext, currency_id: int) -> CurrencyRow:
    row = await currency_row(ctx, currency_id)
    if not await debase(ctx, await EconomyBook.load(ctx), row, forced=True):
        raise ValidationFailedError(f"{row.name} has no silver left to take out.")
    return row


async def use_currency(ctx: TickContext, community_id: int, currency_id: int | None) -> None:
    entity = await community(ctx, community_id)
    row = await ctx.session.get(CommunitySocietyRow, entity.id)
    if row is None:
        raise ValidationFailedError(f"{entity.name} keeps no market accounts yet.")
    if currency_id is not None:
        await currency_row(ctx, currency_id)
    row.currency_id = currency_id
    await ctx.session.flush()


async def forgive(ctx: TickContext, loan_id: int) -> LoanRow:
    loan = await ctx.session.get(LoanRow, loan_id)
    if loan is None or loan.status is not LoanStatus.OPEN:
        raise ValidationFailedError("No open loan was found.")
    await forgive_loan(ctx, loan)
    await ctx.session.flush()
    return loan


async def hoard(ctx: TickContext, community_id: int, metal: MaterialKind, units: int | None) -> int:
    entity = await community(ctx, community_id)
    amount = units if units is not None else ctx.rules.money.hoard_luxury_units
    if amount <= 0:
        raise ValidationFailedError("A hoard holds at least one load of treasure.")
    added = await inject_hoard(ctx, entity, amount, metal)
    await sync_aggregates(ctx.session, ctx.rules, entity)
    return added
