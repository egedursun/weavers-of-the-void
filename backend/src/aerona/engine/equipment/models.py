from collections.abc import Iterable
from types import MappingProxyType
from zlib import crc32

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.equipment import FAMILIES, SLOT_FAMILIES, FamilySpec
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.equipment import EquipmentModelRow
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.equipment import ArmamentSlot, EquipmentFamily
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.vehicles import MountKind
from aerona.engine.collective.embodied import embody
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import MaterialBook, MaterialProps, armour_protection, node_material, weapon_damage
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.made_names import made_name
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

E = EquipmentFamily
M = MountKind
GUN_ENGINES = (E.BEAM_CANNON, E.MISSILE_LAUNCHER, E.HOWITZER, E.CANNON, E.CARRONADE, E.BOMBARD, E.TREBUCHET_ENGINE, E.CATAPULT_ENGINE, E.BALLISTA)
MOUNT_FAMILIES: MappingProxyType[MountKind, tuple[EquipmentFamily, ...]] = total(
    MountKind,
    {
        M.BOW: (E.TORPEDO, E.CANNON, E.BALLISTA, E.HARPOON, E.RAM),
        M.STERN: (E.CANNON, E.CARRONADE, E.BALLISTA, E.MINE_LAYER),
        M.BROADSIDE: (E.CANNON, E.CARRONADE, E.BOMBARD, E.CATAPULT_ENGINE, E.BALLISTA),
        M.DECK: (*GUN_ENGINES, E.HEAVY_FLAMETHROWER, E.ROCKET_LAUNCHER),
        M.TURRET: (E.BEAM_CANNON, E.MISSILE_LAUNCHER, E.HOWITZER, E.CANNON, E.BALLISTA),
        M.SPINAL: (E.BEAM_CANNON, E.MISSILE_LAUNCHER, E.TORPEDO, E.FOCUS_ARRAY),
        M.HARDPOINT: (E.MISSILE_LAUNCHER, E.ROCKET_LAUNCHER, E.REPEATING_GUN, E.HEAVY_FLAMETHROWER, E.CANNON, E.BALLISTA),
        M.WING: (E.MISSILE_LAUNCHER, E.ROCKET_LAUNCHER, E.REPEATING_GUN),
        M.CREW_STATION: (E.REPEATING_GUN, E.RIFLE, E.MUSKET, E.CROSSBOW, E.LONGBOW, E.BOW, E.FOCUS),
        M.RIDER: (E.RIFLE, E.CROSSBOW, E.COMPOSITE_BOW, E.BOW, E.JAVELIN, E.LONGBLADE, E.SPEAR),
        M.RAM: (E.RAM, E.BOARDING_GEAR),
        M.BAY: (E.TORPEDO, E.MISSILE_LAUNCHER, E.MINE_LAYER, E.ROCKET_LAUNCHER),
        M.WARD_NODE: (E.FOCUS_ARRAY, E.FOCUS),
    },
)
SLOT_MATERIALS = MappingProxyType(
    {
        ArmamentSlot.HAND_WEAPON: MaterialSlot.WEAPONS,
        ArmamentSlot.MISSILE_WEAPON: MaterialSlot.WEAPONS,
        ArmamentSlot.VEHICLE_WEAPON: MaterialSlot.WEAPONS,
        ArmamentSlot.ARMOUR: MaterialSlot.ARMOUR,
        ArmamentSlot.SHIELD: MaterialSlot.ARMOUR,
        ArmamentSlot.HELMET: MaterialSlot.ARMOUR,
        ArmamentSlot.BARDING: MaterialSlot.ARMOUR,
        ArmamentSlot.SENSOR: MaterialSlot.WEAPONS,
        ArmamentSlot.IMPLANT: MaterialSlot.BODY,
        ArmamentSlot.SUPPORT: MaterialSlot.ARMOUR,
    }
)
NEAR_PCT = 80
GUARD_SLOTS = frozenset({ArmamentSlot.ARMOUR, ArmamentSlot.SHIELD, ArmamentSlot.HELMET, ArmamentSlot.BARDING})
GEAR_SLOTS = frozenset({ArmamentSlot.SENSOR, ArmamentSlot.IMPLANT, ArmamentSlot.SUPPORT})


def known(spec: FamilySpec, knowledge: KnowledgeMap, holder_id: int) -> bool:
    return spec.branch is None or knowledge.level(holder_id, spec.branch) >= spec.level


def worth(spec: FamilySpec) -> int:
    if spec.slot in GEAR_SLOTS:
        return spec.accuracy + spec.protection * 2 + spec.damage // 2
    return spec.protection * 3 + spec.coverage if spec.slot in GUARD_SLOTS else spec.damage + spec.piercing // 2 + spec.accuracy // 4 + spec.rate * 5


def taste(holder_id: int, slot: ArmamentSlot, family: EquipmentFamily) -> int:
    return crc32(f"{holder_id}.{slot.value}.{family.value}".encode())


def best_family(knowledge: KnowledgeMap, holder_id: int, slot: ArmamentSlot, allowed: tuple[EquipmentFamily, ...] | None = None) -> EquipmentFamily | None:
    pool = [FAMILIES[family] for family in (allowed or SLOT_FAMILIES[slot])]
    found = [spec for spec in pool if spec.slot is slot and known(spec, knowledge, holder_id)]
    if not found:
        return None
    if allowed is None:
        return max(found, key=lambda spec: (worth(spec), spec.family.value)).family
    top = max(worth(spec) for spec in found)
    near = [spec for spec in found if worth(spec) * PERCENT >= top * NEAR_PCT]
    return min(near, key=lambda spec: taste(holder_id, slot, spec.family)).family


def material_scale(rules: Rules, slot: ArmamentSlot, props: MaterialProps | None, quality: int) -> float:
    if props is None:
        return 0.5 + quality / (2 * PERCENT)
    middle = PERCENT // 2
    return (armour_protection(rules, props, quality) if slot in GUARD_SLOTS else weapon_damage(rules, props, quality)) / middle


def model_values(rules: Rules, family: EquipmentFamily, props: MaterialProps | None, quality: int) -> dict[str, int]:
    spec = FAMILIES[family]
    scale = material_scale(rules, spec.slot, props, quality)
    weight_scale = (props.weight if props is not None else PERCENT // 2) / (PERCENT // 2)
    return {
        "damage": clamp_int(round_half_up(spec.damage * scale), 0, PERCENT),
        "piercing": clamp_int(round_half_up(spec.piercing * scale), 0, PERCENT),
        "reach": spec.reach,
        "rate": spec.rate,
        "accuracy": clamp_int(spec.accuracy + (quality - PERCENT // 2) // 5, 0, PERCENT),
        "protection": clamp_int(round_half_up(spec.protection * scale), 0, PERCENT),
        "coverage": spec.coverage,
        "weight": max(0, round_half_up(spec.weight * weight_scale)),
        "crew": spec.crew,
        "cost": max(1, round_half_up((spec.damage + spec.protection * 2 + spec.crew * 5) / 10 * (0.5 + quality / PERCENT))),
    }


async def draw_model(
    ctx: TickContext,
    origin: EntityRow | None,
    family: EquipmentFamily,
    *,
    world_id: int | None,
    quality: int = PERCENT // 2,
    material: MaterialKind | None = None,
    parent: EquipmentModelRow | None = None,
    name: str | None = None,
) -> EquipmentModelRow:
    spec = FAMILIES[family]
    chosen = material
    world_material_id = None
    if chosen is None and origin is not None:
        held = await node_material(ctx.session, origin.id, SLOT_MATERIALS[spec.slot])
        chosen, world_material_id = (held.material, held.world_material_id) if held is not None else (None, None)
    props = (await MaterialBook.load(ctx.session)).props(world_id, chosen, world_material_id)
    row = EquipmentModelRow(
        world_id=world_id,
        name=name or await made_name(ctx.session, ctx.rules, origin, spec.label, family.value, ctx.epoch),
        origin_node_id=origin.id if origin is not None else None,
        slot=spec.slot,
        family=family,
        material=chosen,
        world_material_id=world_material_id,
        quality=clamp_int(quality, 0, PERCENT),
        technique=None,
        tech_level=spec.level,
        damage_type=spec.damage_type,
        ammunition=spec.ammunition,
        parent_model_id=parent.id if parent is not None else None,
        created_epoch=ctx.epoch,
        retired=False,
        renown=0,
        locked=[],
        **model_values(ctx.rules, family, props, quality),
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await embody(ctx.session, row)
    return row


@memoized(EquipmentModelRow)
async def kept_models(session: AsyncSession, holder_id: int, slot: ArmamentSlot | None) -> tuple[EquipmentModelRow, ...]:
    statement = select(EquipmentModelRow).where(EquipmentModelRow.origin_node_id == holder_id, EquipmentModelRow.retired.is_(False))
    if slot is not None:
        statement = statement.where(EquipmentModelRow.slot == slot)
    return tuple(await session.scalars(statement.order_by(EquipmentModelRow.created_epoch.desc(), EquipmentModelRow.id.desc())))


async def models_of(session: AsyncSession, holder_id: int, slot: ArmamentSlot | None = None) -> list[EquipmentModelRow]:
    return list(await kept_models(session, holder_id, slot))


async def current_model(
    session: AsyncSession, holder_id: int, slot: ArmamentSlot, allowed: tuple[EquipmentFamily, ...] | None = None
) -> EquipmentModelRow | None:
    return next((row for row in await models_of(session, holder_id, slot) if allowed is None or row.family in allowed), None)


async def model_for(
    ctx: TickContext, holder: EntityRow, slot: ArmamentSlot, knowledge: KnowledgeMap, allowed: tuple[EquipmentFamily, ...] | None = None
) -> EquipmentModelRow | None:
    current = await current_model(ctx.session, holder.id, slot, allowed)
    family = best_family(knowledge, holder.id, slot, allowed)
    if family is None:
        return current
    if current is not None and worth(FAMILIES[current.family]) >= worth(FAMILIES[family]):
        return current
    return await draw_model(ctx, holder, family, world_id=holder.world_id, parent=current)


def slot_order(slots: Iterable[ArmamentSlot]) -> list[ArmamentSlot]:
    return sorted(slots, key=lambda item: (item is not ArmamentSlot.VEHICLE_WEAPON, item.value))


async def mount_model(ctx: TickContext, holder: EntityRow | None, mount: MountKind, knowledge: KnowledgeMap) -> EquipmentModelRow | None:
    if holder is None:
        return None
    allowed = MOUNT_FAMILIES[mount]
    for slot in slot_order({FAMILIES[family].slot for family in allowed}):
        found = await model_for(ctx, holder, slot, knowledge, tuple(family for family in allowed if FAMILIES[family].slot is slot))
        if found is not None:
            return found
    return None
