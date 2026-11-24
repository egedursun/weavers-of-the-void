from dataclasses import replace
from types import SimpleNamespace
from typing import cast

from aerona.catalog.creator import ACTION_PASSIONS
from aerona.catalog.life.divine import KEPT_OR_FREED_PASSIONS, MEMORY_WORKS, RESTORING_BOONS
from aerona.catalog.life.faith import CHURCH_WORKS, TENDED_ROUTES
from aerona.catalog.prehistory import SIMULATED_KINDS, WORLD_PREHISTORY
from aerona.catalog.vehicles import FRAMES
from aerona.catalog.world_views import BOUND_NEEDS, WORLD_VIEWS
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.creator import CreatorPassion
from aerona.domain.enums.demography import FuneralCustom
from aerona.domain.enums.dominion import CreatureDeed, CreatureLesson, Manifestation, PerceivedAlignment
from aerona.domain.enums.entity import EngineKind
from aerona.domain.enums.faith import HoldingKind, JudgementDoctrine, RebirthPath, TenetKind
from aerona.domain.enums.military import Stance
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.mythic import HeroquestBoon
from aerona.domain.enums.operations import EchelonOrder
from aerona.domain.enums.prehistory import PrehistoryKind
from aerona.domain.enums.vehicles import Propulsion, VehicleFamily, VehicleFrame
from aerona.domain.enums.world import WorldType
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause
from aerona.domain.enums.world_view import BindingNeed, SettleMode, WorldLight
from aerona.engine.collective.designs import catalogue_fields
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_ends import ending_of
from aerona.engine.dominion.creatures import START_WEIGHT, taught
from aerona.engine.dominion.image import manifestation_of
from aerona.engine.faith.book import Church
from aerona.engine.faith.doctrine import judgement_of, rebirth_path_of
from aerona.engine.faith.judgement import score_of
from aerona.engine.operations.command import wanted_order
from aerona.rules.registry import Rules


def ctx_of(rules: Rules) -> TickContext:
    return cast(TickContext, SimpleNamespace(rules=rules))


def test_a_god_neither_loved_nor_hated_shows_sorrow_when_mercy_leads_and_play_when_little_is_believed(rules: Rules) -> None:
    gap = rules.god_images.stern_gap
    assert manifestation_of(ctx_of(rules), PerceivedAlignment.AMBIVALENT, wrath=20, mercy=20 + gap) is Manifestation.SORROWFUL
    assert manifestation_of(ctx_of(rules), PerceivedAlignment.AMBIVALENT, wrath=1, mercy=1) is Manifestation.PLAYFUL
    assert manifestation_of(ctx_of(rules), PerceivedAlignment.AMBIVALENT, wrath=40, mercy=40) is Manifestation.SERENE


def test_a_warning_draws_a_creatures_habit_back_toward_its_start() -> None:
    pulled = taught(5, {CreatureDeed.HUNT_FOLK.value: START_WEIGHT + 10}, CreatureDeed.HUNT_FOLK, CreatureLesson.WARN, low=0, high=100)
    pushed = taught(5, {CreatureDeed.HUNT_FOLK.value: START_WEIGHT + 10}, CreatureDeed.HUNT_FOLK, CreatureLesson.REWARD, low=0, high=100)
    assert pulled[CreatureDeed.HUNT_FOLK.value] == START_WEIGHT + 5
    assert pushed[CreatureDeed.HUNT_FOLK.value] == START_WEIGHT + 15


def test_a_retreating_army_screens_its_withdrawal() -> None:
    retreating = ArmyProfileRow(stance=Stance.RETREAT)
    assert wanted_order(retreating, attacking=False, short=False) is EchelonOrder.SCREEN
    assert wanted_order(retreating, attacking=False, short=True) is EchelonOrder.RESUPPLY


def test_a_moon_struck_to_its_end_merges_with_its_planet(rules: Rules) -> None:
    moon = WorldRow(parent_world_id=1, terrain_sea=0)
    planet = WorldRow(parent_world_id=None, terrain_sea=0)
    assert ending_of(ctx_of(rules), moon, WorldEndCause.IMPACT) is WorldEnd.MERGED
    assert ending_of(ctx_of(rules), planet, WorldEndCause.IMPACT) is WorldEnd.SHATTERED


def test_godless_ancestor_churches_judge_by_remembrance_and_keep_their_dead_among_the_living(rules: Rules) -> None:
    church = cast(Church, SimpleNamespace(god=None))
    assert judgement_of(church, [TenetKind.ANCESTOR_VENERATION]) is JudgementDoctrine.REMEMBRANCE
    assert judgement_of(church, []) is JudgementDoctrine.NONE
    score = score_of(rules.afterlife, {"renown": 70}, JudgementDoctrine.REMEMBRANCE, rite=FuneralCustom.BURIAL, favoured=False, tenets=set())
    assert score == 70


def test_a_people_of_tradition_is_reborn_where_it_fell(rules: Rules) -> None:
    threshold = rules.doctrine.value_tenet
    assert rebirth_path_of(rules, {ValueAxis.TRADITION: threshold}, JudgementDoctrine.NONE) is RebirthPath.PLACE
    assert rebirth_path_of(rules, {}, JudgementDoctrine.NONE) is RebirthPath.PEOPLE


def test_made_worlds_remember_ruins_and_new_worlds_carry_their_own_ways() -> None:
    assert WORLD_PREHISTORY[WorldType.MEGASTRUCTURE] is PrehistoryKind.RUINED
    assert PrehistoryKind.RUINED in SIMULATED_KINDS
    assert WORLD_VIEWS[WorldType.ROGUE].light is WorldLight.BIOLUMINESCENCE
    assert WORLD_VIEWS[WorldType.ARCHIPELAGO].need is BindingNeed.PLACE
    assert WORLD_VIEWS[WorldType.ARCHIPELAGO].settle is SettleMode.CLIFF
    assert WORLD_VIEWS[WorldType.MEGASTRUCTURE].need is BindingNeed.NAME
    assert {BindingNeed.PLACE, BindingNeed.NAME} == BOUND_NEEDS


def test_pedal_craft_cost_half_the_upkeep_and_sledges_are_their_own_family() -> None:
    bicycle = FRAMES[VehicleFrame.BICYCLE]
    sledge = FRAMES[VehicleFrame.SLEDGE]
    assert bicycle.propulsion is Propulsion.PEDAL
    assert sledge.family is VehicleFamily.SLEDGE
    crewed = catalogue_fields(replace(bicycle, propulsion=Propulsion.CREW), 50)
    pedalled = catalogue_fields(bicycle, 50)
    assert cast(int, pedalled["upkeep"]) == max(1, cast(int, crewed["upkeep"]) // 2)


def test_memory_and_freedom_have_their_own_deeds_and_signs() -> None:
    assert CreatorPassion.MEMORY in ACTION_PASSIONS[ActionKind.REMEMBER_WORLD]
    assert CreatorPassion.FREEDOM in ACTION_PASSIONS[ActionKind.RELEASE_OATH]
    assert {CreatorPassion.MEMORY, CreatorPassion.FREEDOM} == KEPT_OR_FREED_PASSIONS
    assert EngineKind.LIBRARY in MEMORY_WORKS


def test_churches_hold_schools_and_houses_of_healing_that_tend_sickness_but_not_blessings() -> None:
    assert {holding for _, holding, _ in CHURCH_WORKS} == {HoldingKind.SCHOOL, HoldingKind.HOSPITAL}
    assert Transmission.CONTACT in TENDED_ROUTES
    assert Transmission.RITE not in TENDED_ROUTES
    assert {HeroquestBoon.KNOWLEDGE, HeroquestBoon.HEALING} == RESTORING_BOONS
