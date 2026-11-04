from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.lore import WEAPONS
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.mortal import MortalEquipmentRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.mortal import EquipmentSlot
from aerona.engine.lore.arms import best_weapon, grip, held_profiles, whole
from aerona.engine.mortal.profile import ensure_equipment, is_held
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.rules.registry import Rules

SLOT_COLUMNS: dict[EquipmentSlot, str] = {slot: f"{slot.value}_id" for slot in EquipmentSlot}
FOCUS_CLASSES = frozenset({ItemClass.STAFF, ItemClass.RING, ItemClass.IDOL, ItemClass.HOLY_RELIC, ItemClass.MIRROR})
SLOT_CLASSES: dict[EquipmentSlot, frozenset[ItemClass]] = {
    EquipmentSlot.WIELDED_MAIN: frozenset(WEAPONS),
    EquipmentSlot.WIELDED_OFF: frozenset({*WEAPONS, ItemClass.SHIELD}),
    EquipmentSlot.ARMOUR_BODY: frozenset({ItemClass.ARMOUR}),
    EquipmentSlot.ARMOUR_HEAD: frozenset({ItemClass.HELMET, ItemClass.CROWN}),
    EquipmentSlot.FOCUS: FOCUS_CLASSES,
}


def best_of(rows: list[ItemProfileRow], classes: frozenset[ItemClass], taken: set[int]) -> ItemProfileRow | None:
    fitting = [row for row in rows if row.item_class in classes and row.item_entity_id not in taken and row.condition >= 1]
    return max(fitting, key=lambda row: (row.coverage + row.quality, grip(row), row.item_entity_id), default=None)


async def mount_for(session: AsyncSession, mortal_id: int) -> int | None:
    for bond in await active_bonds(session, [BondKind.TAMED], sources=[mortal_id]):
        beast = await living_entity(session, bond.target_node_id)
        if beast is not None:
            return beast.id
    return None


async def auto_equip(session: AsyncSession, mortal_id: int) -> MortalEquipmentRow:
    row = await ensure_equipment(session, mortal_id)
    rows = await held_profiles(session, mortal_id)
    owned = {item.item_entity_id for item in rows}
    taken: set[int] = set()
    for slot in (EquipmentSlot.WIELDED_MAIN, EquipmentSlot.ARMOUR_BODY, EquipmentSlot.ARMOUR_HEAD, EquipmentSlot.FOCUS, EquipmentSlot.WIELDED_OFF):
        column = SLOT_COLUMNS[slot]
        current = getattr(row, column)
        if is_held(row, column):
            if current is not None:
                taken.add(current)
            continue
        if current is not None and current in owned:
            taken.add(current)
            continue
        chosen = (
            best_weapon([item for item in rows if item.item_entity_id not in taken])
            if slot is EquipmentSlot.WIELDED_MAIN
            else best_of(rows, SLOT_CLASSES[slot], taken)
        )
        setattr(row, column, chosen.item_entity_id if chosen is not None else None)
        if chosen is not None:
            taken.add(chosen.item_entity_id)
    if not is_held(row, SLOT_COLUMNS[EquipmentSlot.MOUNT]):
        row.mount_id = await mount_for(session, mortal_id)
    return row


async def slot_profile(session: AsyncSession, mortal_id: int | None, slot: EquipmentSlot) -> ItemProfileRow | None:
    if mortal_id is None:
        return None
    row = await session.get(MortalEquipmentRow, mortal_id)
    item_id = getattr(row, SLOT_COLUMNS[slot]) if row is not None else None
    return await session.get(ItemProfileRow, item_id) if item_id is not None else None


async def wielded(session: AsyncSession, mortal_id: int | None, broken: int = 1) -> ItemProfileRow | None:
    found = await slot_profile(session, mortal_id, EquipmentSlot.WIELDED_MAIN)
    return found if found is not None and whole(found, broken) else best_weapon(await held_profiles(session, mortal_id), broken)


async def has_slot(session: AsyncSession, mortal_id: int, slot: EquipmentSlot) -> bool:
    row = await session.get(MortalEquipmentRow, mortal_id)
    return row is not None and getattr(row, SLOT_COLUMNS[slot]) is not None


async def mount_pct(session: AsyncSession, rules: Rules, mortal_id: int) -> tuple[float, float]:
    if not await has_slot(session, mortal_id, EquipmentSlot.MOUNT):
        return 1.0, 1.0
    return rules.equipment.mount_mobility_pct / PERCENT, rules.equipment.mount_melee_pct / PERCENT


async def off_hand_pct(session: AsyncSession, rules: Rules, mortal_id: int) -> float:
    return rules.equipment.off_hand_melee_pct / PERCENT if await has_slot(session, mortal_id, EquipmentSlot.WIELDED_OFF) else 1.0


async def focus_pct(session: AsyncSession, rules: Rules, mortal_id: int) -> float:
    return rules.equipment.focus_magic_pct / PERCENT if await has_slot(session, mortal_id, EquipmentSlot.FOCUS) else 1.0


async def worn_coverage(session: AsyncSession, mortal_id: int) -> tuple[int, int] | None:
    row = await session.get(MortalEquipmentRow, mortal_id)
    if row is None:
        return None
    body = await session.get(ItemProfileRow, row.armour_body_id) if row.armour_body_id is not None else None
    head = await session.get(ItemProfileRow, row.armour_head_id) if row.armour_head_id is not None else None
    return (head.coverage if head is not None else 0), (body.coverage if body is not None else 0)
