from aerona.catalog.equipment import FAMILIES
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.equipment import (
    MODEL_FIELDS,
    ArmyUnitEquipmentRow,
    EquipmentModelRow,
    EquipmentStoreRow,
    UnitDesignEquipmentRow,
    UnitDesignTechniqueRow,
)
from aerona.db.tables.military import ArmyUnitRow, UnitDesignRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.equipment import EquipmentFamily
from aerona.domain.enums.military import UnitKind
from aerona.engine.collective.embodied import settle, unmake
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.equipment.models import draw_model
from aerona.engine.gatherings.control import Values, allowed, entity, found, node
from aerona.engine.military.unit_types import draw_type
from aerona.engine.primitives.knowledge import KnowledgeMap

UNIT_TYPE_FIELDS = (
    "name",
    "description",
    "world_id",
    "origin_node_id",
    "owner_entity_id",
    "base_kind",
    "family",
    "melee",
    "missile",
    "defence",
    "speed",
    "mass",
    "cost",
    "upkeep",
    "armour",
    "shield",
    "terror",
    "counters_charge",
    "flying",
    "social_class",
    "retired",
    "reach",
    "volleys",
    "accuracy",
    "piercing",
    "doctrine",
    "formation",
    "discipline",
    "training_epochs",
    "mount_species_id",
    "vehicle_design_id",
    "crew_per_vehicle",
)
EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "equipment_model": (EquipmentModelRow, MODEL_FIELDS, "equipment model"),
    "equipment_store": (EquipmentStoreRow, ("count",), "store of equipment"),
    "army_equipment": (ArmyUnitEquipmentRow, ("count", "condition"), "carried equipment"),
    "unit_type": (UnitDesignRow, UNIT_TYPE_FIELDS, "kind of soldier"),
    "unit_loadout": (UnitDesignEquipmentRow, ("count",), "piece of a loadout"),
}


async def new_model(
    ctx: TickContext, origin_id: int | None, family: EquipmentFamily, *, world_id: int | None, name: str | None, quality: int
) -> EquipmentModelRow:
    origin = await entity(ctx, origin_id, "maker") if origin_id is not None else None
    if origin is None and world_id is None:
        raise ValidationFailedError("A model needs a maker or a world.")
    return await draw_model(
        ctx, origin, family, world_id=world_id if world_id is not None else (origin.world_id if origin else None), quality=quality, name=name
    )


async def set_store(ctx: TickContext, holder_id: int, model_id: int, count: int) -> EquipmentStoreRow:
    await node(ctx, holder_id, "holder")
    await found(ctx, EquipmentModelRow, model_id, "equipment model")
    row = await ctx.session.get(EquipmentStoreRow, (holder_id, model_id))
    if row is None:
        row = EquipmentStoreRow(holder_node_id=holder_id, model_id=model_id, count=0, locked=[])
        ctx.session.add(row)
    apply(row, {"count": count}, [])
    await ctx.session.flush()
    return row


async def set_carried(ctx: TickContext, unit_id: int, model_id: int, count: int, condition: int) -> ArmyUnitEquipmentRow:
    await found(ctx, ArmyUnitRow, unit_id, "army stack")
    await found(ctx, EquipmentModelRow, model_id, "equipment model")
    row = await ctx.session.get(ArmyUnitEquipmentRow, (unit_id, model_id))
    if row is None:
        row = ArmyUnitEquipmentRow(unit_id=unit_id, model_id=model_id, count=0, condition=100, locked=[])
        ctx.session.add(row)
    apply(row, {"count": count, "condition": condition}, [])
    await ctx.session.flush()
    return row


async def new_unit_type(ctx: TickContext, owner_id: int, role: UnitKind, name: str | None) -> UnitDesignRow:
    owner = await entity(ctx, owner_id, "maker")
    return await draw_type(ctx, owner, role, await KnowledgeMap.load(ctx.session), name=name)


async def set_loadout(ctx: TickContext, design_id: int, model_id: int, count: int) -> UnitDesignEquipmentRow:
    await found(ctx, UnitDesignRow, design_id, "kind of soldier")
    model = await found(ctx, EquipmentModelRow, model_id, "equipment model")
    if FAMILIES[model.family].slot.value == "vehicle_weapon":
        raise ValidationFailedError("A soldier cannot carry a vehicle's weapon.")
    row = await ctx.session.get(UnitDesignEquipmentRow, (design_id, model_id))
    if row is None:
        row = UnitDesignEquipmentRow(design_id=design_id, model_id=model_id, count=1)
        ctx.session.add(row)
    row.count = max(1, min(10, count))
    await ctx.session.flush()
    return row


async def add_unit_technique(ctx: TickContext, design_id: int, technique: Technique) -> UnitDesignTechniqueRow:
    await found(ctx, UnitDesignRow, design_id, "kind of soldier")
    if await ctx.session.get(UnitDesignTechniqueRow, (design_id, technique)) is not None:
        raise ValidationFailedError("That kind of soldier already needs this technique.")
    row = UnitDesignTechniqueRow(design_id=design_id, technique=technique)
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def remove_unit_technique(ctx: TickContext, design_id: int, technique: Technique) -> None:
    await ctx.session.delete(await found(ctx, UnitDesignTechniqueRow, (design_id, technique), "technique of a kind of soldier"))
    await ctx.session.flush()


async def remove_loadout(ctx: TickContext, design_id: int, model_id: int) -> None:
    await ctx.session.delete(await found(ctx, UnitDesignEquipmentRow, (design_id, model_id), "piece of a loadout"))
    await ctx.session.flush()


async def drop_carried(ctx: TickContext, unit_id: int, model_id: int) -> None:
    await ctx.session.delete(await found(ctx, ArmyUnitEquipmentRow, (unit_id, model_id), "carried equipment"))
    await ctx.session.flush()


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    await ctx.session.flush()
    await settle(ctx.session, row)
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    row = await found(ctx, table, key, label)
    await unmake(ctx.session, row)
    await ctx.session.delete(row)
    await ctx.session.flush()
