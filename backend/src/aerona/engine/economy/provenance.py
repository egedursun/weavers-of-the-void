from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.goods_tables import FABRICS, HOLY_STOCK, HULLS, JEWEL_STOCK, STRUCTURE_STOCK
from aerona.catalog.goods_traits import materials_with
from aerona.catalog.materials import ARMOUR_MATERIALS, TOOL_MATERIALS, WEAPON_MATERIALS
from aerona.catalog.means import BUILDING
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.economy import CommunityStockRow, CurrencyRow, NodeMaterialRow, ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import SOCIETY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.goods_traits import MaterialTrait
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import VehicleKind
from aerona.engine.economy.materials import MaterialBook, set_node_material, workable
from aerona.engine.eras.effects import era_techniques
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

M = MaterialKind
MADE_TYPES = frozenset({EntityType.ITEM, EntityType.STRUCTURE, EntityType.VESSEL})
COMMON = frozenset(materials_with(MaterialTrait.COMMON))
HOLY_WORKS = frozenset({EngineKind.TEMPLE, EngineKind.WONDER})
STONE_WORKS = frozenset({EngineKind.WALL, EngineKind.LIBRARY, EngineKind.SCHOOL, EngineKind.OBSERVATORY, EngineKind.COSMIC_ARCHIVE})


@dataclass
class Workshop:
    community_id: int | None
    levels: dict[KnowledgeBranch, int] = field(default_factory=dict)
    supplies: set[MaterialKind] = field(default_factory=set)
    magic: int = 0
    techniques: frozenset[Technique] = frozenset()


async def maker_of(session: AsyncSession, entity: EntityRow) -> EntityRow | None:
    for node_id in (entity.maker_entity_id, entity.affiliated_entity_id, entity.location_id):
        if node_id is None:
            continue
        node = await session.get(EntityRow, node_id)
        if node is None:
            continue
        if node.entity_type in SOCIETY_TYPES:
            return node
        for hop in (node.affiliated_entity_id, node.location_id):
            home = await session.get(EntityRow, hop) if hop is not None else None
            if home is not None and home.entity_type in SOCIETY_TYPES:
                return home
    return None


async def supplies_of(session: AsyncSession, community: EntityRow) -> set[MaterialKind]:
    held = select(CommunityStockRow.material).where(
        CommunityStockRow.community_entity_id == community.id, CommunityStockRow.quantity > 0, CommunityStockRow.material.is_not(None)
    )
    found = {material for material in await session.scalars(held) if material is not None}
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == community.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    near = select(EntityRow.id).where(EntityRow.location_id.in_([node for node in (community.location_id, community.id) if node is not None]))
    deposits = select(ResourceProfileRow.material).where(ResourceProfileRow.material.is_not(None), ResourceProfileRow.resource_entity_id.in_(owned.union(near)))
    found |= {material for material in await session.scalars(deposits) if material is not None}
    return found


async def workshop_of(session: AsyncSession, entity: EntityRow) -> Workshop:
    community = await maker_of(session, entity)
    if community is None:
        return Workshop(None)
    levels = (await known_levels(session, [community.id])).get(community.id, {})
    region = await session.get(RegionEnvironmentRow, community.location_id) if community.location_id is not None else None
    magic = region.magic_density if region is not None else 0
    return Workshop(community.id, dict(levels), await supplies_of(session, community), magic, await era_techniques(session, community.id))


def supplied(kind: MaterialKind, shop: Workshop) -> bool:
    spec = BUILDING.get(kind)
    return kind in shop.supplies or (spec is not None and bool(set(spec.made_from) & shop.supplies))


def known_how(kind: MaterialKind, shop: Workshop) -> bool:
    spec = BUILDING.get(kind)
    return spec is None or spec.needs is None or spec.needs in shop.techniques


def pick(rules: Rules, book: MaterialBook, world_id: int | None, shop: Workshop, candidates: Iterable[MaterialKind]) -> MaterialKind:
    ordered = list(candidates)
    fit = [
        kind
        for kind in ordered
        if (props := book.props(world_id, kind)) is not None and workable(rules, props, shop.levels, shop.magic) and known_how(kind, shop)
    ]
    for kind in fit:
        if supplied(kind, shop):
            return kind
    for kind in fit:
        if kind in COMMON:
            return kind
    return ordered[-1]


async def coin_metal(session: AsyncSession, item: EntityRow) -> MaterialKind:
    metal = await session.scalar(select(CurrencyRow.metal).where(CurrencyRow.item_entity_id == item.id).limit(1))
    return metal if metal is not None else M.SILVER


def item_candidates(item: EntityRow) -> tuple[MaterialKind, ...]:
    damage, protection, might = stat(item, "damage") or 0, stat(item, "protection") or 0, stat(item, "might") or 0
    if damage > 0 and damage >= protection:
        return WEAPON_MATERIALS
    if protection > 0:
        return ARMOUR_MATERIALS
    if might > 0:
        return JEWEL_STOCK
    return TOOL_MATERIALS


def structure_candidates(structure: EntityRow) -> tuple[MaterialKind, ...]:
    if structure.engine_kind in HOLY_WORKS:
        return HOLY_STOCK
    if structure.engine_kind in STONE_WORKS:
        return STRUCTURE_STOCK[1:]
    return STRUCTURE_STOCK


async def wanted_slots(session: AsyncSession, entity: EntityRow) -> dict[MaterialSlot, tuple[MaterialKind, ...]]:
    if entity.entity_type is EntityType.ITEM:
        if entity.engine_kind is EngineKind.CURRENCY:
            return {MaterialSlot.BODY: (await coin_metal(session, entity),)}
        return {MaterialSlot.BODY: item_candidates(entity)}
    if entity.entity_type is EntityType.STRUCTURE:
        return {MaterialSlot.BODY: structure_candidates(entity)}
    if entity.entity_type is EntityType.VESSEL:
        row = await session.get(VesselProfileRow, entity.id)
        kind = row.kind if row is not None else VehicleKind.SHIP
        slots = {MaterialSlot.HULL: HULLS[kind]}
        if kind in FABRICS:
            slots[MaterialSlot.FABRIC] = FABRICS[kind]
        return slots
    return {}


async def rules_for(session: AsyncSession) -> Rules:
    cosmos = await CosmosRepository(session).get()
    return await CosmosRepository(session).rules() if cosmos is not None else Rules()


async def ensure_materials(session: AsyncSession, entity: EntityRow, *, rules: Rules | None = None, book: MaterialBook | None = None) -> int:
    if entity.entity_type not in MADE_TYPES or entity.status is not EntityStatus.CANON:
        return 0
    slots = await wanted_slots(session, entity)
    missing = [slot for slot in slots if await session.get(NodeMaterialRow, (entity.id, slot)) is None]
    if not missing:
        return 0
    table = rules if rules is not None else await rules_for(session)
    materials = book if book is not None else await MaterialBook.load(session)
    shop = await workshop_of(session, entity)
    for slot in missing:
        await set_node_material(session, entity.id, slot, pick(table, materials, entity.world_id, shop, slots[slot]))
    return len(missing)


async def missing_materials(session: AsyncSession) -> list[EntityRow]:
    filled = {(node, slot) for node, slot in await session.execute(select(NodeMaterialRow.node_id, NodeMaterialRow.slot))}
    statement = select(EntityRow).where(EntityRow.entity_type.in_(list(MADE_TYPES)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    first = {EntityType.ITEM: MaterialSlot.BODY, EntityType.STRUCTURE: MaterialSlot.BODY, EntityType.VESSEL: MaterialSlot.HULL}
    return [entity for entity in await session.scalars(statement) if (entity.id, first[entity.entity_type]) not in filled]


async def sweep_materials(session: AsyncSession, rules: Rules) -> int:
    book = await MaterialBook.load(session)
    made = 0
    for entity in await missing_materials(session):
        made += await ensure_materials(session, entity, rules=rules, book=book)
    return made
