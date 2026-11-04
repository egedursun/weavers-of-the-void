from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civilization import capabilities_at, unlocked
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.foreign_gods import GodConflictRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import CivilizationTier, EngineKind, EntityFlag, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.son import Stat
from aerona.domain.enums.war import DebtStatus, WarCause
from aerona.domain.models.entity_stats import MortalStats, OuterBeingStats, PeopleStats, SettlementStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.duels import son_duel
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.cosmos.routes import RouteBook
from aerona.engine.phases.civilization import (
    adopt,
    apply_tier,
    colony_independence,
    late_debts,
    lend,
    repayments,
    set_tier,
    spontaneous_treaty,
    update_tiers,
)
from aerona.engine.phases.pantheon import (
    attract,
    auto_holy_worlds,
    defeated_waking,
    first_contact,
    hostile_act,
    outer_gnaw,
    rival_soften,
    sleep_waking,
)
from aerona.engine.primitives.queries import BondIndex
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_route, make_son, make_world, teach, tick, tuned


async def test_defeated_god_wakes_after_its_time(ctx: TickContext, cosmos: Cosmos) -> None:
    god = await add_foreign_god(ctx.session, ctx.rules, ctx.rng(), 1, NewForeignGod("Vesmorn", cosmos.home.id, (Domain.GLASS, None), power=10, stance=0))
    god.status = ForeignGodStatus.DEFEATED
    god.defeated_epoch = ctx.epoch - 100
    assert await defeated_waking(ctx) == 1
    assert god.status is ForeignGodStatus.AWAKE and god.power == ctx.rules.pantheon.foreign_wake_min_strength
    assert god.stance == -ctx.rules.pantheon.foreign_wake_grudge


async def test_sleeping_god_wakes_from_noise(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "pantheon", sleep_wake_threshold=1))
    god = await add_foreign_god(session, rules, ctx.rng(), 1, NewForeignGod("Dreamer", cosmos.home.id, (Domain.SLEEP, None), status=ForeignGodStatus.ASLEEP))
    other = await make_world(session, "Velmor")
    await make_route(session, other.id, cosmos.home.id)
    route = (await RouteBook.load(session, rules, ctx.epoch)).routes[0]
    route.created_epoch = ctx.epoch
    assert await sleep_waking(ctx) == 1 and god.status is ForeignGodStatus.AWAKE


async def test_awake_god_contact_attraction_and_theft(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(
        session,
        tuned(tuned(rules, "pantheon", foreign_attract_chance=100, foreign_attack_base_pct=100, foreign_sacrifice_chance=100), "foreign_gods", stat_neutral=50),
    )
    god = await add_foreign_god(session, rules, ctx.rng(), 1, NewForeignGod("Vesmorn", cosmos.home.id, (Domain.GLASS, None), stance=-50, power=100))
    god.faith = rules.foreign_gods.action_full_faith
    son = await make_son(session, "Velan", cosmos.home.id)
    native = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    believer = await make_entity(session, "Vesk", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    await BondRepository(session).connect(BondDraft(believer.id, son.id, BondKind.WORSHIPS, 1))
    book = await RouteBook.load(session, rules, ctx.epoch)
    assert await first_contact(ctx, god, book) and god.contacted
    drawn = await attract(ctx, god, [native, believer], set(), await BondIndex.load(session, [BondKind.WORSHIPS]))
    assert drawn == 1 and await BondRepository(session).exists_between(native.id, god.id, BondKind.WORSHIPS)
    text = await hostile_act(ctx, god, set())
    assert text is not None and "turned" in text
    assert await BondRepository(session).exists_between(believer.id, god.id, BondKind.WORSHIPS)
    assert not await BondRepository(session).exists_between(believer.id, son.id, BondKind.WORSHIPS)


async def test_hostile_god_drives_its_worshippers_to_holy_war(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "pantheon", foreign_attack_base_pct=100, foreign_sacrifice_chance=0, foreign_holy_war_chance=100))
    god = await add_foreign_god(session, rules, ctx.rng(), 1, NewForeignGod("Vesmorn", cosmos.home.id, (Domain.GLASS, None), stance=-50, power=100))
    god.faith = rules.foreign_gods.action_full_faith
    son = await make_son(session, "Velan", cosmos.home.id)
    zealot = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    believer = await make_entity(session, "Vesk", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    await BondRepository(session).connect(BondDraft(believer.id, son.id, BondKind.WORSHIPS, 1))
    await BondRepository(session).connect(BondDraft(zealot.id, god.id, BondKind.WORSHIPS, 1))
    text = await hostile_act(ctx, god, set())
    assert text is not None and "to war against" in text
    enemy = await session.scalar(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.source_node_id == zealot.id))
    assert enemy is not None and enemy.target_node_id == believer.id and enemy.war_cause is WarCause.FOREIGN_GOD


async def test_hostile_god_destroys_temples(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "pantheon", foreign_attack_base_pct=100))
    god = await add_foreign_god(session, rules, ctx.rng(), 1, NewForeignGod("Vesmorn", cosmos.home.id, (Domain.GLASS, None), stance=-50, power=100))
    god.faith = rules.foreign_gods.action_full_faith
    temple = await make_entity(session, "Sun Shrine", EntityType.STRUCTURE, StructureStats(), world_id=cosmos.home.id, engine_kind=EngineKind.TEMPLE)
    await hostile_act(ctx, god, set())
    destroyed = await session.scalar(select(BondRow).where(BondRow.kind == BondKind.DESTROYED, BondRow.target_node_id == temple.id))
    assert destroyed is not None and destroyed.source_node_id == god.id


async def test_auto_holy_world_and_outer_gnaw(ctx: TickContext, cosmos: Cosmos) -> None:
    await make_world(ctx.session, "Velmor")
    son = await make_son(ctx.session, "Velan", cosmos.home.id)
    for index in range(ctx.rules.pantheon.auto_holy_world_worshippers):
        believer = await make_entity(ctx.session, f"Folk {index}", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
        await BondRepository(ctx.session).connect(BondDraft(believer.id, son.id, BondKind.WORSHIPS, 1))
    assert await auto_holy_worlds(ctx) == 1 and cosmos.home.patron_son_id == son.id and cosmos.home.patron_automatic
    await make_entity(ctx.session, "Unspoken", EntityType.OUTER_BEING, OuterBeingStats(influence=50), world_id=cosmos.home.id)
    essence = cosmos.creator.essence
    gnaw = await outer_gnaw(ctx)
    assert gnaw == round(50 / ctx.rules.pantheon.outer_gnaw_divisor) and cosmos.creator.essence == essence - gnaw


async def test_duels_are_recorded_and_rivals_soften(ctx: TickContext, cosmos: Cosmos) -> None:
    first = await make_son(ctx.session, "Velan", cosmos.home.id, stats=90)
    second = await make_son(ctx.session, "Morak", cosmos.home.id, stats=10)
    result = await son_duel(ctx, first, second, Stat.STRENGTH, "old feud")
    assert result.winner_id == first.id and await ctx.session.scalar(select(GodConflictRow).where(GodConflictRow.duel.is_(True))) is not None
    assert await SonRepository(ctx.session).relation(first.id, second.id) == -ctx.rules.son_tools.challenge_relation
    threshold = -ctx.rules.pantheon.rival_relation
    assert rival_soften(ctx.rules, threshold - 10) == threshold - 10 + ctx.rules.pantheon.rival_soften
    assert rival_soften(ctx.rules, threshold - 1) == threshold


def test_tier_unlock_table(rules: Rules) -> None:
    assert not unlocked(rules, CivilizationTier.TRIBE, TierCapability.EXPEDITION)
    assert unlocked(rules, CivilizationTier.CITY_STATE, TierCapability.EXPEDITION)
    assert TierCapability.FEDERATION in capabilities_at(rules, CivilizationTier.KINGDOM)


async def test_tiers_rise_with_hysteresis_and_dwell(ctx: TickContext, cosmos: Cosmos) -> None:
    people = await make_entity(
        ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=ctx.rules.civilization.city_state_population), world_id=cosmos.home.id
    )
    await teach(ctx.session, people, KnowledgeBranch.WRITING)
    assert await update_tiers(ctx) == 1 and people.civ_tier == CivilizationTier.CITY_STATE
    people.stats = people.stats.model_copy(update={"population": round(ctx.rules.civilization.city_state_population * 0.9)})
    assert await update_tiers(ctx) == 0 and people.civ_tier == CivilizationTier.CITY_STATE
    assert not await apply_tier(ctx, people, CivilizationTier.TRIBE)
    locked = await set_tier(ctx.session, ctx.rules, people.id, CivilizationTier.KINGDOM, lock=True)
    assert locked.civ_tier == CivilizationTier.KINGDOM
    assert EntityFlag.EMPIRE not in await EntityRepository(ctx.session).flags(people.id)


async def test_colony_declares_independence(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "civilization", colony_far_independence_chance=100, independence_war_chance=0))
    other = await make_world(session, "Velmor")
    mother = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    colony = await make_entity(
        session, "Tarnhold", EntityType.SETTLEMENT, SettlementStats(population=500, prosperity=40), world_id=other.id, flags=[EntityFlag.COLONY]
    )
    await BondRepository(session).connect(BondDraft(mother.id, colony.id, BondKind.RULES, 1))
    assert await colony_independence(ctx) == 1
    assert EntityFlag.INDEPENDENT in await EntityRepository(session).flags(colony.id)
    assert not await BondRepository(session).exists_between(mother.id, colony.id, BondKind.RULES)


async def test_loans_fall_due_and_get_paid(ctx: TickContext, cosmos: Cosmos) -> None:
    lender = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000, wealth=80), world_id=cosmos.home.id)
    borrower = await make_entity(ctx.session, "Vesk", EntityType.PEOPLE, PeopleStats(population=5000, wealth=20), world_id=cosmos.home.id)
    await lend(ctx, lender, borrower, 10)
    assert lender.stats.wealth == 70 and borrower.stats.wealth == 30
    debt = await ctx.session.scalar(select(BondRow).where(BondRow.kind == BondKind.OWES))
    assert debt is not None and debt.debt_status is DebtStatus.OPEN
    late = tick(ctx.session, ctx.rules, epoch=(debt.debt_due_epoch or 0) + 1)
    assert await late_debts(late) == 1 and debt.debt_status is DebtStatus.OVERDUE
    paying = tick(ctx.session, tuned(ctx.rules, "civilization", loan_repay_chance=100))
    assert await repayments(paying) == 1 and debt.debt_status is DebtStatus.REPAID and lender.stats.wealth == 80


async def test_adoption_and_treaty(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "civilization", treaty_chance=100))
    elder = await make_entity(session, "Orrin", EntityType.MORTAL, MortalStats(age=50, lifespan=80), world_id=cosmos.home.id)
    child = await make_entity(session, "Pell", EntityType.MORTAL, MortalStats(age=8, lifespan=80), world_id=cosmos.home.id)
    await adopt(ctx, elder, child)
    assert await BondRepository(session).exists_between(child.id, elder.id, BondKind.FOSTERED_BY)
    other = await make_world(session, "Velmor")
    await make_route(session, cosmos.home.id, other.id)
    first = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    second = await make_entity(session, "Velfolk", EntityType.PEOPLE, PeopleStats(population=5000), world_id=other.id)
    first.civ_tier = second.civ_tier = CivilizationTier.CITY_STATE
    await spontaneous_treaty(ctx)
    assert await BondRepository(session).exists_between(first.id, second.id, BondKind.TRADES_WITH)
