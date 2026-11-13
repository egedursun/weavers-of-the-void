from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.equipment import FAMILIES
from aerona.catalog.units import UNITS
from aerona.catalog.vehicles import FRAMES
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.cuisine import CommunityDishRow, DishRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.equipment import EquipmentModelRow
from aerona.db.tables.integrity import MegastructureRow, StructureSectionRow
from aerona.db.tables.military import UnitDesignRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.structures import StructureDesignRow
from aerona.db.tables.vehicles import VehicleGroupSectionRow, VesselSectionRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.integrity import SectionState
from aerona.engine.body.decline import SEVERITY_MAX, decline_severity
from aerona.engine.equipment.field import inventory
from aerona.engine.equipment.stores import stores_of
from aerona.engine.vehicles.groups import groups_of

SHOWN = 6


def words(value: str) -> str:
    return value.replace("_", " ")


def listed(items: list[str]) -> str:
    shown = items[:SHOWN]
    rest = len(items) - len(shown)
    return ", ".join(shown) + (f" and {rest} more" if rest > 0 else "")


async def vehicle_lines(session: AsyncSession, holder_id: int) -> list[str]:
    parts: list[str] = []
    for group in await groups_of(session, holder_id):
        design = await session.get(DesignRow, group.design_id)
        if design is None:
            continue
        frame = words(FRAMES[design.frame].label.lower()) if design.frame is not None else "vehicle"
        hits = list(await session.scalars(select(VehicleGroupSectionRow).where(VehicleGroupSectionRow.group_id == group.id)))
        broken = [f"{words(row.section.value)} {row.disabled + row.destroyed} out" for row in hits if row.disabled + row.destroyed > 0]
        damage = f"; {', '.join(broken)}" if broken else ""
        parts.append(f"{group.count} {design.name} ({frame}, {words(group.status.value)}, condition {group.condition}{damage})")
    return [f"Vehicles: {listed(parts)}"] if parts else []


async def store_lines(session: AsyncSession, holder_id: int) -> list[str]:
    parts: list[str] = []
    for row in await stores_of(session, holder_id):
        model = await session.get(EquipmentModelRow, row.model_id)
        if model is not None:
            parts.append(f"{row.count} {model.name} ({FAMILIES[model.family].label.lower()})")
    return [f"Equipment in store: {listed(parts)}"] if parts else []


async def own_kind_lines(session: AsyncSession, holder_id: int) -> list[str]:
    vehicles = await session.scalars(select(DesignRow).where(DesignRow.origin_node_id == holder_id, DesignRow.obsolete.is_(False)).order_by(DesignRow.name))
    units = await session.scalars(
        select(UnitDesignRow).where(UnitDesignRow.origin_node_id == holder_id, UnitDesignRow.retired.is_(False)).order_by(UnitDesignRow.name)
    )
    models = await session.scalars(
        select(EquipmentModelRow).where(EquipmentModelRow.origin_node_id == holder_id, EquipmentModelRow.retired.is_(False)).order_by(EquipmentModelRow.name)
    )
    dishes = await session.scalars(select(DishRow).where(DishRow.origin_node_id == holder_id, DishRow.retired.is_(False)).order_by(DishRow.name))
    buildings = await session.scalars(
        select(StructureDesignRow)
        .where(StructureDesignRow.origin_node_id == holder_id, StructureDesignRow.retired.is_(False))
        .order_by(StructureDesignRow.name)
    )
    groups = [
        ("vehicle types", [f"{row.name} ({FRAMES[row.frame].label.lower() if row.frame is not None else 'vehicle'})" for row in vehicles]),
        ("kinds of soldier", [f"{row.name} ({UNITS[row.base_kind].label.lower()})" for row in units]),
        ("equipment", [f"{row.name} ({FAMILIES[row.family].label.lower()})" for row in models]),
        ("dishes", [f"{row.name} ({words(row.course.value)})" for row in dishes]),
        ("building types", [f"{row.name} ({words(row.base_kind.value)})" for row in buildings]),
    ]
    found = [f"{label}: {listed(items)}" for label, items in groups if items]
    return [f"Its own kinds: {'; '.join(found)}"] if found else []


async def kitchen_lines(session: AsyncSession, community_id: int) -> list[str]:
    rows = await session.execute(
        select(CommunityDishRow, DishRow)
        .join(DishRow, DishRow.id == CommunityDishRow.dish_id)
        .where(CommunityDishRow.community_entity_id == community_id)
        .order_by(CommunityDishRow.popularity.desc())
    )
    parts = [f"{dish.name} ({words(dish.course.value)}, {words(dish.method.value)}, liked {row.popularity})" for row, dish in rows]
    return [f"Dishes cooked here: {listed(parts)}"] if parts else []


async def section_lines(session: AsyncSession, entity: EntityRow) -> list[str]:
    if entity.entity_type is EntityType.VESSEL:
        damaged = list(
            await session.scalars(select(VesselSectionRow).where(VesselSectionRow.vessel_entity_id == entity.id, VesselSectionRow.state != SectionState.SOUND))
        )
        parts = [f"{words(row.section.value)} {words(row.state.value)}" for row in damaged]
        return [f"Damaged sections: {listed(parts)}"] if parts else []
    if entity.entity_type is not EntityType.STRUCTURE:
        return []
    rows = list(
        await session.scalars(select(StructureSectionRow).where(StructureSectionRow.structure_entity_id == entity.id).order_by(StructureSectionRow.section))
    )
    lines: list[str] = []
    hurt = [f"{words(row.section.value)} {words(row.state.value)}" for row in rows if row.state is not SectionState.SOUND]
    if hurt:
        lines.append(f"Damaged sections: {listed(hurt)}")
    mega = await session.get(MegastructureRow, entity.id)
    if mega is not None:
        orbit = f", steering toward orbit {mega.target_orbit}" if mega.target_orbit is not None else ""
        lines.append(f"Megastructure output {mega.output}{orbit}")
    return lines


async def mind_lines(session: AsyncSession, entity: EntityRow) -> list[str]:
    if entity.entity_type is not EntityType.MORTAL:
        return []
    lines: list[str] = []
    profile = await session.get(MortalProfileRow, entity.id)
    if profile is not None and profile.drawn_to is not None:
        drawn = ", ".join(words(item) for item in profile.drawn_to) or "no one"
        lines.append(f"Drawn to {drawn} (strength {profile.attraction})")
    severity = await decline_severity(session, entity.id)
    if severity > 0:
        lines.append(f"Memory failing with age ({severity} of {SEVERITY_MAX})")
    return lines


async def made_facts(session: AsyncSession, entity: EntityRow, *, private: bool) -> list[str]:
    lines = [
        *await vehicle_lines(session, entity.id),
        *await store_lines(session, entity.id),
        *await own_kind_lines(session, entity.id),
        *await section_lines(session, entity),
        *(await mind_lines(session, entity) if private else []),
    ]
    if entity.entity_type in {EntityType.SETTLEMENT, EntityType.PEOPLE}:
        lines.extend(await kitchen_lines(session, entity.id))
    return lines


async def kit_line(session: AsyncSession, army_id: int) -> str:
    carried = [f"{count} {model.name}" for model, count in await inventory(session, army_id)]
    vehicles = await vehicle_lines(session, army_id)
    parts = ([f"carries {listed(carried)}"] if carried else []) + [line.lower() for line in vehicles]
    return f"; {'; '.join(parts)}" if parts else ""
