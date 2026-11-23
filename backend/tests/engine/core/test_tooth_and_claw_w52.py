from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.couplings import CARRION_RESTS, KEEPING_RESTS
from aerona.catalog.evolution import STAGE_DOCILITY, keystone_of, seeded_trait, trophic_level
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.couplings import CarrionRest
from aerona.domain.enums.ecology import Diet, DomesticationStage, SizeClass
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.evolution import EvolvedTrait, KeystoneRole, TrophicLevel
from aerona.domain.enums.nature import Dormancy, Thermoregulation
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.ecology.trophic import appetite, enduring
from aerona.engine.nature.seasons import activity, asleep, chilled
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld


def seed(trait: EvolvedTrait, *, tameability: int = 50, stage: DomesticationStage = DomesticationStage.WILD, lifespan: int = 10) -> int:
    return seeded_trait(
        trait, size=SizeClass.MEDIUM, traits=set(), cold_floor=0, intelligence=50, litter=2, fear=50, tameability=tameability, stage=stage, lifespan=lifespan
    )


def test_docility_starts_at_the_stage_of_keeping_and_longevity_follows_lifespan() -> None:
    wild = seed(EvolvedTrait.DOCILITY, tameability=10)
    kept = seed(EvolvedTrait.DOCILITY, tameability=10, stage=DomesticationStage.BREED)
    assert wild == 10 and kept == STAGE_DOCILITY[DomesticationStage.BREED]
    long_lived = seed(EvolvedTrait.LONGEVITY, lifespan=20)
    short_lived = seed(EvolvedTrait.LONGEVITY, lifespan=5)
    assert long_lived > short_lived


def test_decomposers_take_their_own_level_and_three_new_keystones_are_found() -> None:
    assert trophic_level(Diet.DECOMPOSER, SizeClass.TINY) is TrophicLevel.DECOMPOSER
    assert keystone_of(BodyPlan.QUADRUPED, Diet.CARNIVORE, SizeClass.HUGE, set()) is KeystoneRole.REGULATOR
    assert keystone_of(BodyPlan.AVIAN, Diet.OMNIVORE, SizeClass.MEDIUM, set()) is KeystoneRole.SEED_DISPERSER
    assert keystone_of(BodyPlan.AQUATIC, Diet.FILTER, SizeClass.TINY, {CreatureTrait.AQUATIC}) is KeystoneRole.REEF_BUILDER


def test_torpor_eats_less_cryptobiosis_endures_and_sleeps_only_in_extremes() -> None:
    rules = Rules()
    assert asleep(Dormancy.CRYPTOBIOSIS, TemperatureBand.FROZEN) and not asleep(Dormancy.CRYPTOBIOSIS, TemperatureBand.COLD)
    assert not asleep(Dormancy.TORPOR, TemperatureBand.FROZEN)
    assert appetite(rules, SpeciesProfileRow(dormancy=Dormancy.TORPOR)) < 1.0
    assert enduring(rules, SpeciesProfileRow(dormancy=Dormancy.CRYPTOBIOSIS)) < 1.0


def test_athermic_bodies_are_never_slowed_and_heterotherms_slow_only_partly() -> None:
    rules = Rules()
    cold = TemperatureBand.FROZEN
    assert activity(rules, Thermoregulation.ATHERMIC, cold) == 1.0
    assert activity(rules, Thermoregulation.ECTOTHERM, cold) < activity(rules, Thermoregulation.HETEROTHERM, cold) < 1.0
    assert chilled(Thermoregulation.HETEROTHERM, cold) and not chilled(Thermoregulation.ATHERMIC, cold)


async def test_the_carrion_catalogue_holds_every_rest_and_buried_dead_are_kept(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "carrion")
    assert set(CARRION_RESTS) == set(CarrionRest)
    assert CarrionRest.BURIED in KEEPING_RESTS and CarrionRest.BURNED not in KEEPING_RESTS
    assert CARRION_RESTS[CarrionRest.BURNED].disease(ctx.rules) == 0
    assert CARRION_RESTS[CarrionRest.BURIED].fossil(ctx.rules) > CARRION_RESTS[CarrionRest.ROTTING].fossil(ctx.rules)
