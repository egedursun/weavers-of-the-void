from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import CivilizationTier as T
from aerona.engine.cosmos.tiers import stepped
from aerona.engine.gods.mood import MoodInputs, MoodState, compute_mood_update
from aerona.engine.phases.diplomacy import alliance_lifetimes
from aerona.engine.primitives.doom import step_doom
from aerona.engine.primitives.faith import faith_dominance, saturated_followers
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import scaled_cap, stochastic_round
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules

QUIET = MoodInputs(wars=0, godless=0, communities=0, rebels=0, doom_clock=0, cult=0, new_life=0, actions=0, active_sons=5, unanswered_weight=0.0)


async def test_doom_clock_keeps_fractions_at_slow_speed(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(balance={"apocalypse_speed": 50})
    cosmos = await CosmosRepository(session).require_cosmos()
    for _ in range(4):
        step_doom(rules, cosmos, 1)
    assert cosmos.doom_clock == 2
    assert cosmos.doom_fraction == 0


def test_balance_formulas_saturate_and_scale() -> None:
    rules = Rules()
    knee = rules.faith.cult_saturation
    assert saturated_followers(rules, knee * rules.faith.followers_per_faith, rules.faith.followers_per_faith) == knee
    assert saturated_followers(rules, 4 * knee * rules.faith.followers_per_faith, rules.faith.followers_per_faith) < 4 * knee
    assert faith_dominance(rules, 1, {1: 100.0}) == 0
    assert faith_dominance(rules, 1, {1: 10.0}) == 1
    assert scaled_cap(4, 40, 120) == 7
    assert scaled_cap(4, 0, 120) == 4
    assert stochastic_round(2.3, 0.2) == 3
    assert stochastic_round(2.3, 0.5) == 2


def test_upper_tiers_are_climbed_in_order() -> None:
    assert stepped(T.CITY_STATE, T.COSMIC_POWER) == T.KINGDOM
    assert stepped(T.KINGDOM, T.COSMIC_POWER) == T.WORLD_EMPIRE
    assert stepped(T.WORLD_EMPIRE, T.TRIBE) == T.TRIBE


def test_temperament_swings_wrath_and_contentment() -> None:
    rules = Rules()
    calm = MoodState(contentment=50, anger=20, interest=60, loneliness=10)
    stormy = compute_mood_update(rules, calm, replace(QUIET, temperament_roll=1.0, battles=6, killings=6))
    still = compute_mood_update(rules, calm, replace(QUIET, temperament_roll=0.5))
    assert stormy.state.anger > still.state.anger
    assert stormy.state.temperament == rules.creator.temperament_wave


async def test_old_alliances_without_a_common_enemy_lapse(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(diplomacy={"alliance_lifetime": 1, "alliance_end_chance": 100})
    first = await settlement(session, "Oakfold", world, world.regions[0])
    second = await settlement(session, "Reedmouth", world, world.regions[1])
    alliance = await BondRepository(session).connect(BondDraft(first.id, second.id, BondKind.ALLY, 0))
    ctx = await manual_context(session, "test", rules)
    assert await alliance_lifetimes(ctx, 2) == 1
    assert alliance.state is BondState.PAST
