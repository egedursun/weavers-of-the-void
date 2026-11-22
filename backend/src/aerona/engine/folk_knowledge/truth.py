from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.goods_traits import commodities_with
from aerona.catalog.life.domain import GROWN
from aerona.catalog.life_traits import SPECIES_CLASS_TRAITS, having
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.ecology import SpeciesProductRow, SpeciesProfileRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.folk_knowledge import FolkClassRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.ecology import SpeciesClass
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass
from aerona.domain.enums.folk_knowledge import FolkDomain, FolkTaking
from aerona.domain.enums.goods_traits import CommodityTrait
from aerona.domain.enums.life_traits import SpeciesClassTrait
from aerona.domain.enums.node import NodeKind

KIND_DOMAINS = frozenset({FolkDomain.PLANTS, FolkDomain.ANIMALS, FolkDomain.ILLNESS, FolkDomain.MATTER, FolkDomain.SKY, FolkDomain.LAND, FolkDomain.WATERS})
BENIGN = frozenset({FolkTaking.FOOD, FolkTaking.MEDICINE, FolkTaking.HARMLESS})
HARMFUL = frozenset({FolkTaking.POISON, FolkTaking.DANGER, FolkTaking.CURSE})
MEANINGS = frozenset({FolkTaking.OMEN, FolkTaking.SACRED})
ROAMING = having(SPECIES_CLASS_TRAITS, SpeciesClassTrait.ROAMING)
SKY_KINDS = frozenset({NodeKind.STAR, NodeKind.WORLD, NodeKind.GALAXY, NodeKind.CLUSTER})
HEALING_GOODS = frozenset(commodities_with(CommodityTrait.HEALING))
DANGER_AT = 60
TAINT_AT = 60


async def species_class_of(session: AsyncSession, node_id: int) -> SpeciesClass | None:
    profile = await session.get(SpeciesProfileRow, node_id)
    return profile.species_class if profile is not None else None


async def watered(session: AsyncSession, region_id: int) -> bool:
    land = await session.get(RegionEnvironmentRow, region_id)
    return land is not None and (land.coast_kind is not CoastKind.NONE or land.river_class is not RiverClass.NONE)


async def node_fits(session: AsyncSession, domain: FolkDomain, node: NodeRow) -> bool:
    entity = node if isinstance(node, EntityRow) else None
    region = entity is not None and entity.entity_type is EntityType.REGION
    if domain in (FolkDomain.PLANTS, FolkDomain.ANIMALS):
        return await species_class_of(session, node.id) in (GROWN if domain is FolkDomain.PLANTS else ROAMING)
    if domain is FolkDomain.ILLNESS:
        return await session.get(DiseaseProfileRow, node.id) is not None
    if domain is FolkDomain.SKY:
        return node.kind in SKY_KINDS
    return region and (domain is FolkDomain.LAND or await watered(session, node.id))


async def fits(session: AsyncSession, row: FolkClassRow) -> bool:
    node = await session.get(NodeRow, row.grouped_node_id) if row.grouped_node_id is not None else None
    material = await session.get(WorldMaterialRow, row.material_id) if row.material_id is not None else None
    if row.domain not in KIND_DOMAINS:
        return node is None and material is None
    if row.domain is FolkDomain.MATTER:
        return material is not None and node is None
    return node is not None and material is None and await node_fits(session, row.domain, node)


async def plant_truth(session: AsyncSession, node_id: int) -> FolkTaking:
    goods = set(await session.scalars(select(SpeciesProductRow.commodity).where(SpeciesProductRow.species_entity_id == node_id)))
    if CommodityKind.POISON in goods:
        return FolkTaking.POISON
    return FolkTaking.MEDICINE if goods & HEALING_GOODS else FolkTaking.FOOD


async def truth_of(session: AsyncSession, row: FolkClassRow) -> FolkTaking | None:
    if row.domain is FolkDomain.MATTER and row.material_id is not None:
        material = await session.get(WorldMaterialRow, row.material_id)
        return None if material is None else FolkTaking.POISON if material.corruption >= TAINT_AT else FolkTaking.HARMLESS
    if row.grouped_node_id is None:
        return None
    if row.domain is FolkDomain.ILLNESS:
        return FolkTaking.DANGER if await session.get(DiseaseProfileRow, row.grouped_node_id) is not None else None
    if row.domain is FolkDomain.ANIMALS:
        profile = await session.get(SpeciesProfileRow, row.grouped_node_id)
        return None if profile is None else FolkTaking.DANGER if profile.aggression >= DANGER_AT else FolkTaking.HARMLESS
    if row.domain is FolkDomain.PLANTS:
        return await plant_truth(session, row.grouped_node_id)
    return None


def misjudged(taking: FolkTaking, truth: FolkTaking | None) -> bool:
    if truth is None or taking in MEANINGS:
        return False
    if truth in HARMFUL:
        return taking in BENIGN or taking is FolkTaking.CURSE
    return taking in HARMFUL


def hurts(taking: FolkTaking, truth: FolkTaking | None) -> bool:
    return truth in HARMFUL and taking in BENIGN


def blames(taking: FolkTaking, truth: FolkTaking | None) -> bool:
    return truth is FolkTaking.DANGER and taking is FolkTaking.CURSE


def mistaken(domain: FolkDomain, truth: FolkTaking | None) -> FolkTaking:
    if truth is None:
        return FolkTaking.OMEN
    if domain is FolkDomain.ILLNESS:
        return FolkTaking.CURSE
    if truth in HARMFUL:
        return FolkTaking.FOOD if domain is FolkDomain.PLANTS else FolkTaking.HARMLESS
    return FolkTaking.DANGER
