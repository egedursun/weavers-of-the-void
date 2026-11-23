from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.goods_traits import commodities_with
from aerona.catalog.life.folkways import CHARM_EFFECTS
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memo_of
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import CharmRow, LuckBeliefRow, NutritionScoreRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.folkways import CharmPower, LuckReach
from aerona.domain.enums.goods_traits import CommodityTrait
from aerona.engine.body.customs import people_of
from aerona.rules.registry import Rules

SCORE_TABLES = frozenset({NutritionScoreRow.__tablename__})
KEEPING_FOODS = frozenset(commodities_with(CommodityTrait.KEEPING))
CHARM_TABLES = frozenset({CharmRow.__tablename__, BondRow.__tablename__})
CHARM_BASE = 50


async def scores(session: AsyncSession) -> dict[int, int]:
    memo = memo_of(session, "nutrition_scores", SCORE_TABLES)
    if memo is not None and "all" in memo:
        known: dict[int, int] = memo["all"]
        return known
    found = {int(holder): int(score) for holder, score in await session.execute(select(NutritionScoreRow.holder_node_id, NutritionScoreRow.score))}
    if memo is not None:
        memo["all"] = found
    return found


async def underfed(session: AsyncSession, rules: Rules, node_id: int) -> int:
    score = (await scores(session)).get(node_id)
    return max(0, rules.nutrition.well_fed - score) if score is not None else 0


async def charm_powers(session: AsyncSession) -> dict[int, dict[CharmPower, tuple[bool, int]]]:
    memo = memo_of(session, "charm_powers", CHARM_TABLES)
    if memo is not None and "all" in memo:
        known: dict[int, dict[CharmPower, tuple[bool, int]]] = memo["all"]
        return known
    rows = await session.execute(
        select(BondRow.source_node_id, CharmRow.power, CharmRow.real, CharmRow.strength)
        .join(CharmRow, CharmRow.item_entity_id == BondRow.target_node_id)
        .where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    )
    found: dict[int, dict[CharmPower, tuple[bool, int]]] = {}
    for bearer, power, real, strength in rows:
        mine = found.setdefault(int(bearer), {})
        was = mine.get(power)
        mine[power] = (bool(real) or (was is not None and was[0]), max(int(strength), was[1] if was is not None else 0))
    if memo is not None:
        memo["all"] = found
    return found


async def real_charm(session: AsyncSession, rules: Rules, bearer_id: int | None, powers: frozenset[CharmPower]) -> int:
    if bearer_id is None:
        return 0
    held_charms = (await charm_powers(session)).get(bearer_id, {})
    return max(
        (round(strength * CHARM_EFFECTS[power](rules) / CHARM_BASE) for power, (real, strength) in held_charms.items() if real and power in powers), default=0
    )


async def battle_luck(session: AsyncSession, rules: Rules, community: EntityRow) -> int:
    people = await people_of(session, community)
    if people is None:
        return 0
    rows = await session.scalars(select(LuckBeliefRow.lucky).where(LuckBeliefRow.people_entity_id == people.id, LuckBeliefRow.reach == LuckReach.BATTLE))
    return sum(rules.mishaps.lucky_morale if lucky else -rules.mishaps.lucky_morale for lucky in rows)


async def fed_fertility(session: AsyncSession, rules: Rules, node_id: int) -> float:
    hunger = await underfed(session, rules, node_id)
    charm = await real_charm(session, rules, node_id, frozenset({CharmPower.FERTILITY}))
    return max(0.0, 1 - hunger * rules.nutrition.fertility_pct / PERCENT / PERCENT) * (1 + charm * rules.mishaps.charm_fertility / PERCENT / PERCENT)


async def healing_charm(session: AsyncSession, rules: Rules, node_id: int) -> int:
    return await real_charm(session, rules, node_id, frozenset({CharmPower.HEALING})) * rules.mishaps.charm_heal // PERCENT
