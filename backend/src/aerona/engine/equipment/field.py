from collections import defaultdict
from dataclasses import dataclass, replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.battle_depth import WeaponProfile
from aerona.catalog.equipment import FAMILIES, ROLE_ARMS, UNIT_SLOTS
from aerona.catalog.units import UnitSpec, weapon_of
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.equipment import ArmyUnitEquipmentRow, EquipmentModelRow, EquipmentStoreRow, UnitDesignEquipmentRow
from aerona.db.tables.military import ArmyUnitRow, UnitDesignRow
from aerona.db.write_guard import held
from aerona.domain.enums.equipment import ArmamentSlot
from aerona.engine.collective.makers import makers_of
from aerona.engine.context import TickContext
from aerona.engine.equipment.models import current_model
from aerona.engine.equipment.stores import add_pieces, take_pieces
from aerona.engine.primitives.numbers import clamp_int, round_half_up

S = ArmamentSlot


@dataclass(frozen=True)
class Carried:
    model: EquipmentModelRow
    count: int
    condition: int


async def carried_by_units(session: AsyncSession, unit_ids: list[int]) -> dict[int, list[Carried]]:
    found: dict[int, list[Carried]] = defaultdict(list)
    if not unit_ids:
        return found
    statement = (
        select(ArmyUnitEquipmentRow, EquipmentModelRow)
        .join(EquipmentModelRow, EquipmentModelRow.id == ArmyUnitEquipmentRow.model_id)
        .where(ArmyUnitEquipmentRow.unit_id.in_(unit_ids), ArmyUnitEquipmentRow.count > 0)
        .order_by(ArmyUnitEquipmentRow.unit_id, EquipmentModelRow.id)
    )
    for row, model in await session.execute(statement):
        found[row.unit_id].append(Carried(model, row.count, row.condition))
    return found


async def loadout_of(session: AsyncSession, design: UnitDesignRow | None) -> dict[int, int]:
    if design is None:
        return {}
    rows = await session.scalars(select(UnitDesignEquipmentRow).where(UnitDesignEquipmentRow.design_id == design.id))
    return {row.model_id: row.count for row in rows}


async def wanted_models(session: AsyncSession, unit: ArmyUnitRow, spec: UnitSpec, owner_id: int, design: UnitDesignRow | None) -> dict[int, int]:
    loadout = await loadout_of(session, design)
    if loadout:
        return {model_id: per * unit.count for model_id, per in loadout.items()}
    wanted: dict[int, int] = {}
    kit = ROLE_ARMS[unit.kind]
    for slot in UNIT_SLOTS[spec.family]:
        if slot not in kit or (slot is S.MISSILE_WEAPON and spec.missile <= 0):
            continue
        if slot is S.SHIELD and spec.shield.value == "none":
            continue
        model = await current_model(session, owner_id, slot, kit[slot])
        if model is not None:
            wanted[model.id] = unit.count
    return wanted


async def supplier_of(session: AsyncSession, owner: EntityRow) -> int:
    for candidate in await makers_of(session, owner):
        stocked = select(EquipmentStoreRow.model_id).where(EquipmentStoreRow.holder_node_id == candidate, EquipmentStoreRow.count > 0).limit(1)
        if await session.scalar(stocked) is not None:
            return candidate
    return owner.id


async def equip_stack(ctx: TickContext, unit: ArmyUnitRow, spec: UnitSpec, owner: EntityRow, design: UnitDesignRow | None) -> int:
    if held(unit.army_entity_id) or held(owner.id):
        return 0
    supplier = await supplier_of(ctx.session, owner)
    if held(supplier):
        return 0
    issued = 0
    for model_id, wanted in (await wanted_models(ctx.session, unit, spec, supplier, design)).items():
        row = await ctx.session.get(ArmyUnitEquipmentRow, (unit.id, model_id))
        have = row.count if row is not None else 0
        if row is not None and "count" in (row.locked or []):
            continue
        taken = await take_pieces(ctx.session, supplier, model_id, max(0, wanted - have))
        if taken <= 0:
            continue
        if row is None:
            row = ArmyUnitEquipmentRow(unit_id=unit.id, model_id=model_id, count=0, condition=PERCENT, locked=[])
            ctx.session.add(row)
        row.count += taken
        issued += taken
    return issued


def blend(base: int, model: int, share: float) -> int:
    return clamp_int(round_half_up(base + (model - base) * share), 0, PERCENT)


def field_spec(spec: UnitSpec, carried: list[Carried], soldiers: int) -> UnitSpec:
    if not carried or soldiers <= 0:
        return spec
    melee, missile, armour, shield, profile = spec.melee, spec.missile, spec.armour, spec.shield, weapon_of(spec)
    defence = spec.defence
    reach, accuracy, piercing = profile.reach, profile.accuracy, profile.piercing
    for item in carried:
        share = min(1.0, item.count / soldiers) * item.condition / PERCENT
        family = FAMILIES[item.model.family]
        if item.model.slot is S.HAND_WEAPON:
            melee = blend(melee, item.model.damage, share)
            reach = max(reach, item.model.reach) if share >= 0.5 else reach
            piercing = blend(piercing, item.model.piercing, share)
        elif item.model.slot is S.MISSILE_WEAPON:
            missile = blend(missile, item.model.damage, share)
            accuracy = blend(accuracy, item.model.accuracy, share)
            piercing = blend(piercing, item.model.piercing, share)
        elif item.model.slot in {S.ARMOUR, S.HELMET, S.BARDING}:
            defence = blend(defence, defence + item.model.protection // 2, share)
            armour = family.armour if family.armour is not None and share >= 0.5 else armour
        elif item.model.slot is S.SHIELD:
            defence = blend(defence, defence + item.model.protection // 2, share)
            shield = family.shield if family.shield is not None and share >= 0.5 else shield
        elif item.model.slot is S.SENSOR:
            accuracy = blend(accuracy, max(accuracy, item.model.accuracy), share)
        elif item.model.slot is S.IMPLANT:
            melee = blend(melee, max(melee, item.model.damage), share)
            accuracy = blend(accuracy, max(accuracy, item.model.accuracy), share)
            defence = blend(defence, defence + item.model.protection // 2, share)
        elif item.model.slot is S.SUPPORT:
            defence = blend(defence, defence + item.model.protection // 2, share)
            accuracy = blend(accuracy, max(accuracy, item.model.accuracy), share)
    return replace(
        spec,
        melee=melee,
        missile=missile,
        defence=defence,
        armour=armour,
        shield=shield,
        profile=WeaponProfile(reach, profile.volleys, accuracy, piercing),
    )


async def field_specs(session: AsyncSession, rows: list[ArmyUnitRow], specs: dict[int, UnitSpec]) -> dict[int, UnitSpec]:
    carried = await carried_by_units(session, [row.id for row in rows if row.count > 0])
    return {row.id: field_spec(specs[row.id], carried[row.id], row.count) for row in rows if row.id in carried and row.id in specs}


async def inventory(session: AsyncSession, army_id: int) -> list[tuple[EquipmentModelRow, int]]:
    statement = (
        select(EquipmentModelRow, ArmyUnitEquipmentRow.count)
        .join(ArmyUnitEquipmentRow, ArmyUnitEquipmentRow.model_id == EquipmentModelRow.id)
        .join(ArmyUnitRow, ArmyUnitRow.id == ArmyUnitEquipmentRow.unit_id)
        .where(ArmyUnitRow.army_entity_id == army_id, ArmyUnitEquipmentRow.count > 0)
    )
    totals: dict[int, int] = defaultdict(int)
    models: dict[int, EquipmentModelRow] = {}
    for model, count in await session.execute(statement):
        totals[model.id] += count
        models[model.id] = model
    return [(models[model_id], totals[model_id]) for model_id in sorted(totals)]


async def wear_after_battle(ctx: TickContext, rows: list[ArmyUnitRow]) -> int:
    worn = 0
    for row in await ctx.session.scalars(select(ArmyUnitEquipmentRow).where(ArmyUnitEquipmentRow.unit_id.in_([unit.id for unit in rows]))):
        if "condition" in (row.locked or []) or held(next((unit.army_entity_id for unit in rows if unit.id == row.unit_id), None)):
            continue
        row.condition = clamp_int(row.condition - ctx.rules.armament.battle_wear, 0, PERCENT)
        worn += 1
    return worn


async def acclaim_models(ctx: TickContext, rows: list[ArmyUnitRow]) -> int:
    carried = await carried_by_units(ctx.session, [row.id for row in rows])
    models = {item.model.id: item.model for items in carried.values() for item in items}
    raised = 0
    for model in models.values():
        if "renown" in (model.locked or []) or (model.origin_node_id is not None and held(model.origin_node_id)):
            continue
        model.renown = clamp_int(model.renown + ctx.rules.armament.victory_renown, 0, PERCENT)
        raised += 1
    return raised


async def drop_to_losses(ctx: TickContext, rows: list[ArmyUnitRow]) -> int:
    dropped = 0
    for unit in rows:
        if held(unit.army_entity_id):
            continue
        for row in await ctx.session.scalars(
            select(ArmyUnitEquipmentRow).where(ArmyUnitEquipmentRow.unit_id == unit.id, ArmyUnitEquipmentRow.count > unit.count)
        ):
            if "count" in (row.locked or []):
                continue
            dropped += row.count - unit.count
            row.count = unit.count
    return dropped


async def capture(ctx: TickContext, victor_id: int, dropped: int, models: list[EquipmentModelRow]) -> int:
    if dropped <= 0 or not models or held(victor_id):
        return 0
    share = round_half_up(dropped * ctx.rules.armament.capture_pct / PERCENT / len(models))
    taken = 0
    for model in models:
        taken += await add_pieces(ctx.session, victor_id, model.id, share)
    return taken
