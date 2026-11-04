from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.lore import WEAPONS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.primitives.numbers import round_half_up

GUARDS = frozenset({ItemClass.ARMOUR, ItemClass.SHIELD, ItemClass.HELMET})


async def held_profiles(session: AsyncSession, owner_id: int | None) -> list[ItemProfileRow]:
    if owner_id is None:
        return []
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == owner_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    living = select(EntityRow.id).where(EntityRow.id.in_(owned), EntityRow.status == EntityStatus.CANON)
    return list(await session.scalars(select(ItemProfileRow).where(ItemProfileRow.item_entity_id.in_(living)).order_by(ItemProfileRow.item_entity_id)))


def grip(row: ItemProfileRow) -> float:
    return (0.75 + row.quality / (4 * PERCENT)) * (0.75 + row.condition / (4 * PERCENT))


def best_weapon(rows: list[ItemProfileRow]) -> ItemProfileRow | None:
    weapons = [row for row in rows if row.item_class in WEAPONS and row.condition >= 1]
    return max(weapons, key=lambda row: (grip(row), row.item_entity_id), default=None)


def guard_of(rows: list[ItemProfileRow]) -> int:
    return sum(round_half_up(row.coverage * row.condition / PERCENT) for row in rows if row.item_class in GUARDS)
