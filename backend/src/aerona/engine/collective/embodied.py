from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.core.grammar import an
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.cuisine import DishRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.equipment import EquipmentModelRow
from aerona.db.tables.military import UnitDesignRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.structures import StructureDesignRow
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.models.entity_stats import BuildingTypeStats, DishStats, EntityStats, EquipmentModelStats, UnitTypeStats, VehicleTypeStats

KindRow = DesignRow | UnitDesignRow | EquipmentModelRow | DishRow | StructureDesignRow
KIND_TABLES: MappingProxyType[EntityType, type[KindRow]] = MappingProxyType(
    {
        EntityType.VEHICLE_TYPE: DesignRow,
        EntityType.UNIT_TYPE: UnitDesignRow,
        EntityType.EQUIPMENT_MODEL: EquipmentModelRow,
        EntityType.DISH: DishRow,
        EntityType.BUILDING_TYPE: StructureDesignRow,
    }
)
TABLE_KINDS: MappingProxyType[type[KindRow], EntityType] = MappingProxyType({table: kind for kind, table in KIND_TABLES.items()})
KIND_STATS: MappingProxyType[EntityType, type[EntityStats]] = MappingProxyType(
    {
        EntityType.VEHICLE_TYPE: VehicleTypeStats,
        EntityType.UNIT_TYPE: UnitTypeStats,
        EntityType.EQUIPMENT_MODEL: EquipmentModelStats,
        EntityType.DISH: DishStats,
        EntityType.BUILDING_TYPE: BuildingTypeStats,
    }
)
KIND_ROWS = (DesignRow, UnitDesignRow, EquipmentModelRow, DishRow, StructureDesignRow)


def ended(row: KindRow) -> bool:
    return bool(row.obsolete) if isinstance(row, DesignRow) else bool(row.retired)


def born(row: KindRow) -> int:
    return row.epoch if isinstance(row, DesignRow) else row.created_epoch


def made_status(row: KindRow) -> EntityStatus:
    return EntityStatus.DEAD if ended(row) else EntityStatus.CANON


async def mark(session: AsyncSession, entity: EntityRow, status: EntityStatus) -> None:
    if entity.status is status:
        return
    entity.status = status
    if status is EntityStatus.DEAD:
        cosmos = await CosmosRepository(session).require_cosmos()
        entity.end_epoch = max(entity.birth_epoch, cosmos.epoch) if entity.end_epoch is None else entity.end_epoch
    else:
        entity.end_epoch = None


async def maker_of(session: AsyncSession, row: KindRow) -> tuple[EntityRow | None, SonRow | None]:
    if row.origin_node_id is None:
        return None, None
    return await session.get(EntityRow, row.origin_node_id), await session.get(SonRow, row.origin_node_id)


async def embody(session: AsyncSession, row: KindRow) -> EntityRow:
    found = await session.get(EntityRow, row.entity_id) if row.entity_id is not None else None
    if found is not None:
        return found
    kind = TABLE_KINDS[type(row)]
    maker, son = await maker_of(session, row)
    noun = ENTITY_TYPES[kind].noun
    entity = await EntityRepository(session).create(
        EntityDraft(
            name=await NameRepository(session).unique_name(row.name),
            entity_type=kind,
            description=row.description or (f"{an(noun, capital=True)} of {maker.name}." if maker is not None else f"{an(noun, capital=True)}."),
            stats=KIND_STATS[kind](),
            power_level=1,
            origin=EntityOrigin.SON if son is not None else EntityOrigin.ENGINE,
            birth_epoch=born(row),
            world_id=row.world_id,
            creator_son_id=son.id if son is not None else None,
            maker_entity_id=maker.id if maker is not None else None,
        )
    )
    await mark(session, entity, made_status(row))
    row.entity_id = entity.id
    row.name = entity.name
    await session.flush()
    return entity


async def mirror(session: AsyncSession, row: KindRow) -> None:
    entity = await session.get(EntityRow, row.entity_id) if row.entity_id is not None else None
    if entity is None:
        await embody(session, row)
        return
    if entity.name != row.name:
        row.name = (await NameRepository(session).rename(entity.id, row.name)) if row.name.strip() else entity.name
    if entity.status in {EntityStatus.CANON, EntityStatus.DEAD}:
        await mark(session, entity, made_status(row))
    if row.description and entity.description != row.description:
        entity.description = row.description


async def kind_of(session: AsyncSession, entity: EntityRow) -> KindRow | None:
    table = KIND_TABLES.get(entity.entity_type)
    return await session.scalar(select(table).where(table.entity_id == entity.id)) if table is not None else None


async def follow_name(session: AsyncSession, node_id: int, name: str) -> None:
    entity = await session.get(EntityRow, node_id)
    row = await kind_of(session, entity) if entity is not None else None
    if row is not None:
        row.name = name


async def follow_status(session: AsyncSession, entity: EntityRow) -> None:
    row = await kind_of(session, entity)
    if row is None:
        return
    gone = entity.status is not EntityStatus.CANON
    if isinstance(row, DesignRow):
        row.obsolete = gone
    else:
        row.retired = gone


async def settle(session: AsyncSession, row: object) -> None:
    if isinstance(row, KIND_ROWS):
        await mirror(session, row)


async def unmake(session: AsyncSession, row: object) -> None:
    if not isinstance(row, KIND_ROWS) or row.entity_id is None:
        return
    entity = await session.get(EntityRow, row.entity_id)
    if entity is not None:
        await session.delete(entity)


async def align_made(session: AsyncSession) -> int:
    aligned = 0
    for table in KIND_ROWS:
        rows: list[KindRow] = list(await session.scalars(select(table).order_by(table.id)))
        for row in rows:
            entity = await session.get(EntityRow, row.entity_id) if row.entity_id is not None else None
            if entity is None:
                await embody(session, row)
                aligned += 1
            elif (entity.status is EntityStatus.CANON) == ended(row):
                await follow_status(session, entity)
                aligned += 1
    return aligned
