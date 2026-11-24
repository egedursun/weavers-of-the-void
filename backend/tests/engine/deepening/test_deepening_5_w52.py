from types import SimpleNamespace

from aerona.catalog.command import AREAS, TRAIT_AREAS
from aerona.catalog.kinds.siege import STARVATION
from aerona.catalog.life.military import TRAIT_TACTICS
from aerona.catalog.pacts import BINDING_STATES, NEIGHBOUR_ACCORDS, PARTY_ROLES, STANDINGS, TERM_CLAUSES
from aerona.catalog.war_w52 import CAPTIVE_FATES, FALL_CHOICES, SIEGE_ACTION_SPECS, STANCES
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.cycles import ChallengeResponse
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.military import CaptiveFate, CommandArea, CommanderTrait, SackChoice, SiegeAction, SiegeWork, Stance, StarvationStage, Tactic
from aerona.domain.enums.polity import ClauseKind, PartyRole, RegionalStanding, TreatyKind, TreatyStatus
from aerona.engine.cycles.challenge import response_to
from aerona.engine.military.battle import Field, fire_weight
from aerona.engine.military.siege_w52 import burn_works, water_from_works
from aerona.rules.registry import Rules


def test_a_witness_sees_a_pact_kept_and_a_treaty_under_renegotiation_still_binds() -> None:
    assert PARTY_ROLES[PartyRole.WITNESS].witnesses and not PARTY_ROLES[PartyRole.WITNESS].principal
    assert TreatyStatus.RENEGOTIATING in BINDING_STATES
    assert not STANDINGS[RegionalStanding.ISOLATED].trades and not STANDINGS[RegionalStanding.ISOLATED].allies


def test_accords_and_their_clauses_are_kept_each_age() -> None:
    assert {TreatyKind.MUTUAL_AID, TreatyKind.BORDER_ACCORD} == NEIGHBOUR_ACCORDS
    assert {ClauseKind.RETURN_OF_REFUGEES, ClauseKind.SHARED_WATER, ClauseKind.CAPTIVE_EXCHANGE} <= TERM_CLAUSES


def test_a_crushing_trial_with_a_movement_stirring_brings_a_new_form() -> None:
    ctx = SimpleNamespace(rules=Rules())
    high = ctx.rules.challenge_response.band_high + 1
    assert response_to(ctx, high, True) is ChallengeResponse.TRANSFORMATION
    assert response_to(ctx, high, False) is ChallengeResponse.COLLAPSE


def test_fire_burns_on_dry_ground_and_fails_in_rain() -> None:
    dry = Field(terrain=TerrainKind.DESERT, weather=WeatherKind.CLEAR, night=False)
    wet = Field(terrain=TerrainKind.DESERT, weather=WeatherKind.RAIN, night=False)
    assert fire_weight(dry) > fire_weight(wet)


def test_new_commanders_fight_by_their_ground_and_command_reads_the_field() -> None:
    assert CommandArea.INTELLIGENCE in AREAS
    assert TRAIT_AREAS[CommanderTrait.RIVER_CROSSER]
    assert Tactic.RIVER_CROSSING in TRAIT_TACTICS[CommanderTrait.RIVER_CROSSER]


def test_a_garrison_burns_the_works_and_a_dam_cuts_the_water() -> None:
    ctx = SimpleNamespace(rules=Rules())
    siege = SiegeRow(works={SiegeWork.TOWERS.value: 60, SiegeWork.DAM.value: 100}, sallies=0, locked=[])
    burned = burn_works(ctx, siege)
    assert burned > 0 and siege.sallies == 1 and siege.works[SiegeWork.TOWERS.value] < 60
    siege.works = {SiegeWork.DAM.value: 100}
    assert water_from_works(ctx, siege, 100) == 100 + ctx.rules.siege.dam_effect


def test_siege_ends_and_hunger_stages_run_in_order() -> None:
    assert SIEGE_ACTION_SPECS[SiegeAction.DIVERT_RIVER].works == (SiegeWork.DAM,)
    assert FALL_CHOICES[SackChoice.RESETTLE].label
    assert CAPTIVE_FATES[CaptiveFate.ADOPTED].settles_captor
    assert STANCES[Stance.DISBAND].resting
    order = list(StarvationStage)
    assert order.index(StarvationStage.FAMINE) < order.index(StarvationStage.HUNGER_SICKNESS) < order.index(StarvationStage.TABOO_BROKEN)
    assert (
        STARVATION[StarvationStage.FAMINE].surrender_pct
        < STARVATION[StarvationStage.HUNGER_SICKNESS].surrender_pct
        < STARVATION[StarvationStage.TABOO_BROKEN].surrender_pct
    )
