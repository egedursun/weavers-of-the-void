from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.lore import WEAPONS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemEnchantmentRow, ItemHistoryRow, ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass, ItemDeed, RiteEffectKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faith import BindingKind, SpiritAlignment
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

GUARDS = frozenset({ItemClass.ARMOUR, ItemClass.SHIELD, ItemClass.HELMET, ItemClass.PADDING, ItemClass.CLOAK})
ARMED = frozenset({RiteEffectKind.DAMAGE, RiteEffectKind.CURSE})
WARDED = frozenset({RiteEffectKind.WARD, RiteEffectKind.BLESS})
NOTE = "worn in single combat"


async def held_profiles(session: AsyncSession, owner_id: int | None) -> list[ItemProfileRow]:
    if owner_id is None:
        return []
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == owner_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    living = select(EntityRow.id).where(EntityRow.id.in_(owned), EntityRow.status == EntityStatus.CANON)
    return list(await session.scalars(select(ItemProfileRow).where(ItemProfileRow.item_entity_id.in_(living)).order_by(ItemProfileRow.item_entity_id)))


def grip(row: ItemProfileRow) -> float:
    return (0.75 + row.quality / (4 * PERCENT)) * (0.75 + row.condition / (4 * PERCENT))


def whole(row: ItemProfileRow, broken: int) -> bool:
    return row.condition >= max(1, broken)


def best_weapon(rows: list[ItemProfileRow], broken: int = 1) -> ItemProfileRow | None:
    weapons = [row for row in rows if row.item_class in WEAPONS and whole(row, broken)]
    return max(weapons, key=lambda row: (grip(row), row.item_entity_id), default=None)


def guard_of(rows: list[ItemProfileRow], broken: int = 1) -> int:
    return sum(round_half_up(row.coverage * row.condition / PERCENT) for row in rows if row.item_class in GUARDS and whole(row, broken))


def burden_of(rows: list[ItemProfileRow], broken: int = 1) -> int:
    return sum(row.weight for row in rows if (row.item_class in WEAPONS or row.item_class in GUARDS) and whole(row, broken))


async def enchanted(session: AsyncSession, item_ids: list[int], kinds: frozenset[RiteEffectKind]) -> int:
    if not item_ids:
        return 0
    total = await session.scalar(
        select(func.coalesce(func.sum(ItemEnchantmentRow.strength), 0)).where(
            ItemEnchantmentRow.item_entity_id.in_(item_ids), ItemEnchantmentRow.effect.in_(list(kinds))
        )
    )
    return int(total or 0)


async def war_magic(session: AsyncSession, rules: Rules, blade: ItemProfileRow | None) -> float:
    if blade is None:
        return 1.0
    return 1 + await enchanted(session, [blade.item_entity_id], ARMED) * rules.enchantments.damage_pct / (PERCENT * PERCENT)


async def ward_magic(session: AsyncSession, rules: Rules, rows: list[ItemProfileRow]) -> int:
    ids = [row.item_entity_id for row in rows if whole(row, rules.item_wear.broken)]
    warded = round_half_up(await enchanted(session, ids, WARDED) * rules.enchantments.ward_pct / PERCENT)
    guardians = await session.scalar(
        select(func.count(SpiritProfileRow.spirit_entity_id)).where(
            SpiritProfileRow.binding == BindingKind.ITEM, SpiritProfileRow.bound_entity_id.in_(ids), SpiritProfileRow.alignment != SpiritAlignment.VENGEFUL
        )
    )
    return warded + int(guardians or 0) * rules.item_powers.spirit_guard


async def wear_in_duel(ctx: TickContext, fighter_id: int, exchanges: int) -> int:
    loss = ctx.rules.item_powers.duel_wear * exchanges
    if loss <= 0:
        return 0
    worn = 0
    for row in await held_profiles(ctx.session, fighter_id):
        if (row.item_class not in WEAPONS and row.item_class not in GUARDS) or "condition" in row.locked:
            continue
        before = row.condition
        row.condition = clamp_int(row.condition - loss, 0, PERCENT)
        worn += 1
        if before >= ctx.rules.item_wear.broken > row.condition:
            ctx.session.add(ItemHistoryRow(item_entity_id=row.item_entity_id, epoch=ctx.epoch, deed=ItemDeed.BROKEN, actor_entity_id=fighter_id, note=NOTE))
    return worn
