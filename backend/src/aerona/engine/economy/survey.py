import re

from sqlalchemy import select

from aerona.catalog.backfill_words import MATERIAL_WORDS, RESOURCE_WORDS, WORKSHOP_WORDS
from aerona.catalog.production import EXTRACTION
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.economy import CurrencyRow, NodeMaterialRow, ResourceProfileRow, WorkshopRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, MaterialSlot, TradeRouteStatus, WorkshopKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityType
from aerona.domain.enums.environment import CoastKind
from aerona.domain.enums.material import MINERAL_KINDS, MaterialKind
from aerona.domain.enums.society import Commodity, KnowledgeBranch, SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.deposits import Deposit, open_deposit
from aerona.engine.economy.extraction import extraction_kind
from aerona.engine.economy.materials import set_node_material
from aerona.engine.economy.provenance import sweep_materials
from aerona.engine.economy.resources import default_material, ensure_profile
from aerona.engine.economy.routes import found_route, load_routes
from aerona.engine.economy.stocks import goods_of, lots_of
from aerona.engine.environment.control import world_seam_id
from aerona.engine.environment.works import works_by_region
from aerona.engine.primitives.queries import active_bonds

BACKFILL_FIXUP = "economy.w4_backfill"
DEPTH_FIXUP = "economy.depth_backfill"
C = CommodityKind
HIDDEN_SEAM_FLOOR = 70


def words_of(*texts: str | None) -> set[str]:
    return set(re.findall(r"[^\W\d_]+", " ".join(text for text in texts if text).lower()))


def guess_commodity(resource: EntityRow) -> CommodityKind | None:
    found = words_of(resource.name, resource.subtype, resource.description)
    for commodity, words in RESOURCE_WORDS.items():
        if any(word in found for word in words):
            return commodity
    return None


def guess_material(resource: EntityRow) -> MaterialKind | None:
    found = words_of(resource.name, resource.subtype, resource.description)
    for material, words in MATERIAL_WORDS.items():
        if any(word in found for word in words):
            return material
    return None


async def profile_resources(ctx: TickContext, book: EconomyBook) -> int:
    made = 0
    for resource in book.resources():
        region = book.ground.region_of(resource.id)
        profile = book.profiles.get(resource.id)
        if profile is None:
            commodity = guess_commodity(resource) or C.ORE
            material = guess_material(resource) if commodity is C.ORE else None
            profile = await ensure_profile(ctx.session, ctx.rules, resource, region, commodity=commodity, material=material)
            book.profiles[resource.id] = profile
            made += 1
        elif profile.material is None and profile.world_material_id is None and profile.commodity in (C.ORE, C.STONE, C.TIMBER):
            profile.material = guess_material(resource) or default_material(profile.commodity, region)
    return made


async def seed_communities(ctx: TickContext, book: EconomyBook) -> int:
    seeded = 0
    ledger = goods_of(ctx.session, ctx.epoch)
    for community in book.communities:
        row = book.societies.get(community.id)
        if row is None or await lots_of(ctx.session, community.id):
            continue
        for aggregate in Commodity:
            await ledger.shift_aggregate(ctx.rules, community, aggregate, row.stock(aggregate), flow=GoodsFlow.SEED)
        seeded += 1
    return seeded


def wanted_workshops(book: EconomyBook, community: EntityRow, structures: list[EntityRow], owned: list[ResourceProfileRow]) -> set[WorkshopKind]:
    wanted: set[WorkshopKind] = set()
    for structure in structures:
        found = words_of(structure.name, structure.subtype)
        for kind, words in WORKSHOP_WORDS.items():
            if any(word in found or any(token.startswith(word) for token in found) for word in words):
                wanted.add(kind)
    level = book.level
    if level(community.id, KnowledgeBranch.METALLURGY) >= 1:
        wanted |= {WorkshopKind.FORGE, WorkshopKind.CHARCOAL_KILN}
    if level(community.id, KnowledgeBranch.AGRICULTURE) >= 1:
        wanted |= {WorkshopKind.MILL, WorkshopKind.GRANARY}
    if level(community.id, KnowledgeBranch.MEDICINE) >= 1:
        wanted.add(WorkshopKind.ALCHEMIST)
    if level(community.id, KnowledgeBranch.WARFARE) >= 1:
        wanted.add(WorkshopKind.SIEGE_YARD)
    region = book.ground.region_of(community.id)
    if level(community.id, KnowledgeBranch.SEAFARING) >= 1 and region is not None and region.coast_kind is not CoastKind.NONE:
        wanted.add(WorkshopKind.SHIPYARD)
    row = book.societies.get(community.id)
    if (row is not None and row.share(SocialClass.MERCHANT) >= PERCENT // 10) or book.knowledge.knows(community.id, KnowledgeBranch.TRADE):
        wanted |= {WorkshopKind.MARKET, WorkshopKind.WAREHOUSE}
    wanted.add(WorkshopKind.WEAVERY)
    wanted.add(WorkshopKind.TANNERY)
    for profile in owned:
        site = EXTRACTION[extraction_kind(profile)].workshop
        if site is not None:
            wanted.add(site)
    return wanted


async def backfill_workshops(ctx: TickContext, book: EconomyBook) -> int:
    structures: dict[int, list[EntityRow]] = {}
    for entity in book.entities.values():
        if entity.entity_type is EntityType.STRUCTURE and entity.location_id is not None:
            structures.setdefault(entity.location_id, []).append(entity)
    made = 0
    for community in book.communities:
        owned = [
            book.profiles[resource]
            for resource, owners in book.owners.items()
            if resource in book.profiles and any(book.affiliated.get(owner) == community.id for owner in owners)
        ]
        anchors = structures.get(community.id, [])
        for kind in sorted(wanted_workshops(book, community, anchors, owned), key=lambda item: item.value):
            if book.workshop(community.id, kind) is not None:
                continue
            anchor = next(
                (structure for structure in anchors if any(word in words_of(structure.name, structure.subtype) for word in WORKSHOP_WORDS.get(kind, ()))), None
            )
            row = WorkshopRow(
                community_entity_id=community.id,
                kind=kind,
                level=1,
                built_epoch=max(1, ctx.epoch),
                structure_entity_id=anchor.id if anchor is not None else None,
            )
            ctx.session.add(row)
            book.workshops.setdefault(community.id, {})[kind] = row
            made += 1
    await ctx.session.flush()
    return made


async def backfill_currencies(ctx: TickContext, book: EconomyBook) -> int:
    made = 0
    coins = [entity for entity in book.entities.values() if entity.entity_type is EntityType.ITEM and entity.engine_kind is EngineKind.CURRENCY]
    known = set(await ctx.session.scalars(select(CurrencyRow.item_entity_id)))
    for coin in sorted(coins, key=lambda item: item.id):
        if coin.id in known:
            continue
        makers = await active_bonds(ctx.session, [BondKind.PRODUCED], targets=[coin.id])
        issuer = book.entities.get(makers[0].source_node_id) if makers else None
        if issuer is None:
            continue
        currency = CurrencyRow(
            issuer_entity_id=issuer.id,
            item_entity_id=coin.id,
            name=coin.name,
            metal=MaterialKind.SILVER,
            purity=ctx.rules.money.start_purity,
            supply=ctx.rules.money.coins_per_unit * ctx.rules.money.mint_ore_units,
            trust=ctx.rules.money.start_trust,
            minted_epoch=max(1, coin.birth_epoch),
        )
        ctx.session.add(currency)
        await ctx.session.flush()
        for bond in await active_bonds(ctx.session, [BondKind.OWNS], targets=[coin.id]):
            row = await ctx.session.get(CommunitySocietyRow, bond.source_node_id)
            if row is not None and row.currency_id is None:
                row.currency_id = currency.id
        made += 1
    return made


async def backfill_routes(ctx: TickContext, book: EconomyBook) -> int:
    existing = {frozenset(route.ends) for route in await load_routes(ctx, live_only=False)}
    works = await works_by_region(ctx, book.ground)
    made = 0
    statement = select(BondRow).where(BondRow.kind == BondKind.TRADES_WITH, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    for bond in await ctx.session.scalars(statement):
        first, second = book.entities.get(bond.source_node_id), book.entities.get(bond.target_node_id)
        if first is None or second is None or first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
            continue
        if frozenset((first.id, second.id)) in existing or book.societies.get(first.id) is None or book.societies.get(second.id) is None:
            continue
        for end in (first, second):
            if book.workshop(end.id, WorkshopKind.MARKET) is None:
                row = WorkshopRow(community_entity_id=end.id, kind=WorkshopKind.MARKET, level=1, built_epoch=max(1, ctx.epoch))
                ctx.session.add(row)
                book.workshops.setdefault(end.id, {})[WorkshopKind.MARKET] = row
        path = book.ground.atlas.region_path(book.ground.atlas.top_region(first.id), book.ground.atlas.top_region(second.id))
        if path is None:
            continue
        route = await found_route(ctx, book, first, second, path, works=works)
        route.profile.founded_epoch = max(1, bond.epoch)
        route.profile.last_traffic_epoch = ctx.epoch
        route.profile.traffic_epochs = ctx.rules.trade_routes.formation_epochs
        route.profile.status = TradeRouteStatus.OPEN
        route.entity.pending_name = True
        existing.add(frozenset((first.id, second.id)))
        made += 1
    return made


async def backfill_materials(ctx: TickContext, book: EconomyBook) -> int:
    known = {(row.node_id, row.slot) for row in await ctx.session.scalars(select(NodeMaterialRow))}
    made = 0
    for entity in sorted(book.entities.values(), key=lambda item: item.id):
        if entity.entity_type is EntityType.ITEM and (entity.id, MaterialSlot.BODY) not in known and entity.engine_kind is not EngineKind.CURRENCY:
            material = guess_material(entity) or _item_material(book, entity)
            await set_node_material(ctx.session, entity.id, MaterialSlot.BODY, material)
            made += 1
        elif entity.entity_type is EntityType.STRUCTURE and (entity.id, MaterialSlot.BODY) not in known:
            builder = book.entities.get(entity.location_id) if entity.location_id is not None else None
            stone = builder is not None and book.level(builder.id, KnowledgeBranch.ARCHITECTURE) >= 1
            await set_node_material(ctx.session, entity.id, MaterialSlot.BODY, MaterialKind.STONE if stone else MaterialKind.WOOD)
            made += 1
    for army in await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None))):
        if (army.entity_id, MaterialSlot.WEAPONS) in known:
            continue
        metal = MaterialKind.IRON if book.level(army.owner_entity_id, KnowledgeBranch.METALLURGY) >= 3 else MaterialKind.BRONZE
        await set_node_material(ctx.session, army.entity_id, MaterialSlot.WEAPONS, metal)
        await set_node_material(ctx.session, army.entity_id, MaterialSlot.ARMOUR, MaterialKind.LEATHER)
        made += 1
    return made


def _item_material(book: EconomyBook, item: EntityRow) -> MaterialKind:
    maker = item.maker_entity_id or item.location_id
    level = book.level(maker, KnowledgeBranch.METALLURGY) if maker is not None else 0
    if (item.subtype or "").lower() in ("weapon", "sword", "armour", "shield"):
        return MaterialKind.STEEL if level >= 5 else MaterialKind.IRON if level >= 3 else MaterialKind.BRONZE if level >= 2 else MaterialKind.BONE
    return MaterialKind.WOOD if level == 0 else MaterialKind.BRONZE


async def hide_world_seam(ctx: TickContext, place: EntityRow, world_material_id: int, depth: int) -> bool:
    material = await ctx.session.get(WorldMaterialRow, world_material_id)
    if material is None:
        return False
    label = material.name or (material.base_kind.value.replace("_", " ") if material.base_kind is not None else "strange stone")
    stony = material.base_kind in (MaterialKind.STONE, MaterialKind.CLAY)
    await open_deposit(
        ctx,
        Deposit(
            name=f"Hidden {label.title()} Seam of {place.name}",
            body=f"A rich seam of {label} lies under {place.name}, unknown to anyone who lives there.",
            place=place,
            commodity=C.STONE if stony else C.ORE,
            material=material.base_kind,
            world_material_id=material.id,
            richness=depth,
            quality=depth,
            revealed=False,
        ),
    )
    return True


async def hide_seams(ctx: TickContext, book: EconomyBook) -> int:
    hidden = 0
    worked = {book.ground.atlas.top_region(resource.id) for resource in book.resources()}
    rng = ctx.rng("hidden_seams")
    for region in sorted(book.ground.regions.values(), key=lambda row: row.entity_id):
        place = book.entities.get(region.entity_id)
        if place is None or region.entity_id in worked or not region.mineral_layers:
            continue
        name, depth = max(region.mineral_layers.items(), key=lambda item: (item[1], item[0]))
        world_id = world_seam_id(name)
        if world_id is not None:
            if depth >= HIDDEN_SEAM_FLOOR and rng.chance(ctx.rules.extraction.hidden_share_pct) and await hide_world_seam(ctx, place, world_id, depth):
                hidden += 1
            continue
        if depth < HIDDEN_SEAM_FLOOR or MaterialKind(name) not in MINERAL_KINDS or not rng.chance(ctx.rules.extraction.hidden_share_pct):
            continue
        await open_deposit(
            ctx,
            Deposit(
                name=f"Hidden {name.replace('_', ' ').title()} Seam of {place.name}",
                body=f"A rich seam of {name.replace('_', ' ')} lies under {place.name}, unknown to anyone who lives there.",
                place=place,
                commodity=C.STONE if MaterialKind(name) in (MaterialKind.STONE, MaterialKind.CLAY) else C.ORE,
                material=MaterialKind(name),
                richness=depth,
                quality=depth,
                revealed=False,
            ),
        )
        hidden += 1
    return hidden


async def economy_backfill(ctx: TickContext, book: EconomyBook) -> dict[str, int]:
    if await ctx.session.get(AppliedFixupRow, BACKFILL_FIXUP) is not None:
        return {}
    result = {
        "workshops": await backfill_workshops(ctx, book),
        "currencies": await backfill_currencies(ctx, book),
        "routes": await backfill_routes(ctx, book),
        "materials": await backfill_materials(ctx, book),
        "hidden_seams": await hide_seams(ctx, book),
    }
    ctx.session.add(AppliedFixupRow(key=BACKFILL_FIXUP, result=result))
    await ctx.session.flush()
    return result


async def debt_currencies(ctx: TickContext) -> int:
    bonds = BondRepository(ctx.session)
    statement = select(BondRow).where(BondRow.kind == BondKind.OWES, BondRow.debt_currency_id.is_(None)).order_by(BondRow.id)
    priced = 0
    for bond in await ctx.session.scalars(statement):
        coin = await bonds.debt_coin(bond.target_node_id, bond.source_node_id)
        if coin is not None:
            bond.debt_currency_id = coin
            priced += 1
    return priced


async def depth_backfill(ctx: TickContext) -> dict[str, int]:
    if await ctx.session.get(AppliedFixupRow, DEPTH_FIXUP) is not None:
        return {}
    result = {"materials": await sweep_materials(ctx.session, ctx.rules), "debt_currencies": await debt_currencies(ctx)}
    ctx.session.add(AppliedFixupRow(key=DEPTH_FIXUP, result=result))
    await ctx.session.flush()
    return result
