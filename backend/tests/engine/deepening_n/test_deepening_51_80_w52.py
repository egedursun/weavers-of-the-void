from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.arcana import LIFETIME_DURATIONS, RANGES, TARGETS
from aerona.catalog.cosmography import PHENOMENON_RHYTHMS, RHYTHMS
from aerona.catalog.genesis import TURNING_CYCLES
from aerona.catalog.kinds.terraform import TERRAFORM_AIMS
from aerona.catalog.life.cosmos import CAUSE_END
from aerona.catalog.life.divine import PUNISHMENTS, SERVITOR_ORIGINS, WOUND_CAUSES
from aerona.catalog.life.sacred import LATER_SACRAMENTS, TARGETED_PETITIONS
from aerona.catalog.sacred import PLACE_SPIRITS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.mythic import GeasRow
from aerona.domain.enums.ages import AgeCycle
from aerona.domain.enums.arcana import SpellDuration, SpellRange, SpellTarget
from aerona.domain.enums.cosmography import PhenomenonKind, PhenomenonRhythm
from aerona.domain.enums.divine import SonPunishment, WoundCause
from aerona.domain.enums.military import PeaceTermKind, WarAimKind
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.mythic import GeasLayer, GeasMode, ServitorOrigin
from aerona.domain.enums.operations import EchelonLevel
from aerona.domain.enums.physics import SURVEY_ORDER, SurveyLevel, TerraformAim
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.sacred import GeniusLocusKind, PetitionKind, SacramentKind
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause
from aerona.engine.context import TickContext
from aerona.engine.cosmos.terraform import seed_life, steady_seasons
from aerona.engine.gods.mood import MoodInputs, MoodState, compute_mood_update
from aerona.engine.military.peace import AIM_TERMS
from aerona.engine.mythic.geas_acts import geas_acted
from aerona.engine.mythic.geasa import lay_geas
from aerona.engine.operations.command import needed
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, mortal, tuned_rules


async def at(session: AsyncSession, epoch: int = 3) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "deepening_n", rules=tuned_rules())


def quiet_inputs(killings: int = 0, ended_worlds: int = 0, lost_peoples: int = 0) -> MoodInputs:
    return MoodInputs(
        wars=0,
        godless=0,
        communities=10,
        rebels=0,
        doom_clock=0,
        cult=0,
        new_life=0,
        actions=0,
        active_sons=1,
        unanswered_weight=0.0,
        killings=killings,
        ended_worlds=ended_worlds,
        lost_peoples=lost_peoples,
    )


def test_sorrow_at_deaths_and_ended_worlds_softens_the_creators_wrath() -> None:
    rules = Rules()
    state = MoodState(contentment=40, anger=60, interest=50, loneliness=30)
    calm = compute_mood_update(rules, state, quiet_inputs())
    grieved = compute_mood_update(rules, state, quiet_inputs(killings=40, ended_worlds=1, lost_peoples=3))
    assert grieved.state.anger < calm.state.anger
    assert any(item.axis.value == "sorrow" for item in grieved.breakdown)


def test_a_large_army_sets_a_detachment_apart_and_a_small_one_does_not() -> None:
    rules = Rules()
    assert needed(rules, rules.order_of_battle.detachment_stacks)[EchelonLevel.DETACHMENT] == 1
    assert needed(rules, 1)[EchelonLevel.DETACHMENT] == 0


def test_water_and_refugee_wars_end_in_their_own_terms() -> None:
    assert AIM_TERMS[WarAimKind.SECURE_WATER] is PeaceTermKind.BORDER_ACCORD
    assert AIM_TERMS[WarAimKind.RETURN_REFUGEES] is PeaceTermKind.RETURN_OF_REFUGEES


def test_charts_from_others_sit_between_rumour_and_sight() -> None:
    assert SURVEY_ORDER.index(SurveyLevel.RUMOURED) < SURVEY_ORDER.index(SurveyLevel.CHARTED_BY_OTHERS) < SURVEY_ORDER.index(SurveyLevel.DETECTED)


def test_spiral_turns_its_ages_and_linear_does_not() -> None:
    assert AgeCycle.SPIRAL in TURNING_CYCLES
    assert AgeCycle.LINEAR not in TURNING_CYCLES


def test_marsh_desert_and_glacier_spirits_arise_on_their_ground() -> None:
    assert PLACE_SPIRITS[PlaceKind.SWAMP] is GeniusLocusKind.MARSH
    assert PLACE_SPIRITS[PlaceKind.DUNES] is GeniusLocusKind.DESERT
    assert PLACE_SPIRITS[PlaceKind.GLACIER] is GeniusLocusKind.GLACIER


def test_new_workings_reach_across_dimensions_last_a_lifetime_and_touch_whole_kinds() -> None:
    assert RANGES[SpellRange.DIMENSION].across_dimension
    assert SpellDuration.LIFETIME in LIFETIME_DURATIONS
    assert TARGETS[SpellTarget.SPECIES].members and TARGETS[SpellTarget.PEOPLE].members


def test_wandering_and_once_phenomena_carry_their_rhythm() -> None:
    assert RHYTHMS[PHENOMENON_RHYTHMS[PhenomenonKind.MOVING_FOG]].wanders
    assert RHYTHMS[PHENOMENON_RHYTHMS[PhenomenonKind.POWER_SURGE]].once
    assert RHYTHMS[PhenomenonRhythm.CYCLIC].period > 0


def test_plague_empties_a_world_and_runaway_making_consumes_it() -> None:
    assert CAUSE_END[WorldEndCause.PLAGUE] is WorldEnd.EMPTIED
    assert CAUSE_END[WorldEndCause.RUNAWAY_MAKING] is WorldEnd.CONSUMED


def test_new_divine_wounds_punishments_and_servitors_carry_their_terms() -> None:
    assert WOUND_CAUSES[WoundCause.SCHISM].severity is not None
    assert PUNISHMENTS[SonPunishment.BOUND_TO_WORLD].lasting
    assert SERVITOR_ORIGINS[ServitorOrigin.BARGAINED].loyalty is not None


def test_penance_and_communion_are_taught_later_and_justice_names_its_wrongdoer() -> None:
    assert {SacramentKind.PENANCE, SacramentKind.COMMUNION} <= LATER_SACRAMENTS
    assert PetitionKind.JUSTICE in TARGETED_PETITIONS


async def test_seeding_life_heals_a_world_and_steadying_lowers_its_tilt(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    assert TERRAFORM_AIMS[TerraformAim.SEED_LIFE].reshaping == "seed"
    world.world.biosphere_health, world.world.axial_tilt = 40, 30
    assert seed_life(rules, world.world, 10)
    assert steady_seasons(world.world, 5)
    assert world.world.biosphere_health > 40
    assert world.world.axial_tilt == 25


async def test_a_conditional_geas_binds_only_once_its_trigger_happens(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session)
    bearer = await mortal(session, "Bearer", world, world.regions[0].id)
    row = await lay_geas(ctx, bearer, layer_node_id=None, layer=GeasLayer.LAW, mode=GeasMode.CONDITION, act=ActKind.HOSPITALITY, trigger=ActKind.THEFT)
    assert row.armed_epoch is None
    await geas_acted(ctx, bearer.id, ActKind.THEFT)
    refreshed = await session.get(GeasRow, row.id)
    assert refreshed is not None and refreshed.armed_epoch == ctx.epoch
