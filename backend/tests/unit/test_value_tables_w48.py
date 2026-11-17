from aerona.catalog.kinds.trade_modes import TRADE_LOSS_CULPRITS, TRADE_MODES
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.cosmography import StarAge
from aerona.domain.enums.economy import TradeLoss, TradeMode
from aerona.domain.enums.faith import StratumValence
from aerona.domain.enums.operations import EchelonOrder
from aerona.domain.enums.storyteller import TensionBand
from aerona.domain.enums.world import ClimateEra
from aerona.engine.body.hits import cause_mix
from aerona.engine.body.strike import heat_of
from aerona.engine.cosmos.starlife import stage_radiation, stage_stability
from aerona.engine.cosmos.stellar import stage_length
from aerona.engine.faith.judgement import valence_bounds
from aerona.engine.operations.command import cost_of
from aerona.engine.phases.climate import plague_pct, population_loss_pct
from aerona.engine.storyteller.pace import boost_of
from aerona.rules.registry import Rules


def test_echelon_orders_cost_by_their_rule() -> None:
    rules = Rules()
    table = rules.order_of_battle
    assert cost_of(rules, EchelonOrder.ATTACK) == table.attack_cost
    assert {cost_of(rules, order) for order in EchelonOrder if order is not EchelonOrder.ATTACK} == {table.order_cost}


def test_harm_causes_burn_and_mix_by_their_rules() -> None:
    rules = Rules()
    assert heat_of(rules, HarmCause.MONSTER, DamageType.FIRE, None) == rules.strike.dragon_heat
    assert heat_of(rules, HarmCause.DISASTER, DamageType.FIRE, None) == rules.strike.magma_heat
    assert heat_of(rules, HarmCause.BATTLE, DamageType.FIRE, None) == rules.strike.fire_heat
    assert heat_of(rules, HarmCause.MONSTER, DamageType.CUT, None) == 0
    assert all(cause_mix(rules.injury, cause) for cause in HarmCause)


def test_star_ages_read_their_rules() -> None:
    rules = Rules()
    assert stage_radiation(rules, StarAge.DEAD) == 0
    assert stage_radiation(rules, StarAge.OLD) == rules.star_life.main_radiation
    assert stage_stability(rules, StarAge.REBORN) == rules.star_life.young_stability
    assert stage_length(rules, 1.0, StarAge.DEAD) is None
    assert all(stage_length(rules, 1.0, stage) for stage in StarAge if stage is not StarAge.DEAD)


def test_climate_eras_carry_their_plague_and_loss() -> None:
    rules = Rules()
    assert plague_pct(rules, ClimateEra.SCORCHING) == rules.climate_effects.scorching_age_plague_freq
    assert plague_pct(rules, ClimateEra.TEMPERATE) == 100
    assert population_loss_pct(rules, ClimateEra.ICE_AGE) == rules.climate_effects.ice_age_population_loss
    assert population_loss_pct(rules, ClimateEra.RAIN) == 0


def test_afterlife_bounds_and_tension_pushes() -> None:
    rules = Rules()
    table = rules.afterlife
    assert valence_bounds(table, StratumValence.MIXED) == {"score_at_least": table.torment_score, "score_below": table.paradise_score}
    assert valence_bounds(table, StratumValence.NEUTRAL) == {}
    far = 50 + rules.storyteller.band + 10
    assert boost_of(rules, 50, far, TensionBand.QUIET) > 0
    assert boost_of(rules, far, 50, TensionBand.HEATED) < 0
    assert boost_of(rules, 50, 50, TensionBand.IN_BAND) == 0


def test_trade_modes_and_losses_are_defined_for_every_value() -> None:
    assert TRADE_MODES[TradeMode.SEA].seagoing and TRADE_MODES[TradeMode.RIVER].waterborne
    assert not TRADE_MODES[TradeMode.ROAD].waterborne
    assert TRADE_LOSS_CULPRITS[TradeLoss.BANDITS] == "bandit_id"
