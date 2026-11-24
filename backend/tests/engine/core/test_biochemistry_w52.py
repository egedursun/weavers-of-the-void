from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.domestication import ATHERMIC_BIOCHEMISTRY, BIOCHEMISTRIES
from aerona.catalog.flora import world_life
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import Biochemistry, Diet, SpeciesClass
from aerona.domain.enums.nature import Thermoregulation
from aerona.domain.enums.world import Atmosphere, WorldType
from aerona.engine.ecology.living_ways import keep_living_ways
from aerona.engine.ecology.profiles import SpeciesSpec, biochemistry_of, born_regulation
from aerona.engine.ecology.w52_life import backfill_biochemistry
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, tuned_rules
from tests.engine.core.living_kinds import kind, land, range_of, told

SPEC = SpeciesSpec()


def test_nine_biochemistries_and_every_one_can_arise_from_a_kind_and_its_world() -> None:
    assert len(BIOCHEMISTRIES) == len(Biochemistry) == 9
    reached = {
        biochemistry_of(SPEC, BodyPlan.QUADRUPED, Diet.HERBIVORE, None, ()),
        biochemistry_of(SPEC, BodyPlan.QUADRUPED, Diet.HERBIVORE, None, (Biochemistry.CARBON_AMMONIA,)),
        biochemistry_of(SPEC, BodyPlan.CONSTRUCT, Diet.MINERAL, None, ()),
        biochemistry_of(SPEC, BodyPlan.QUADRUPED, Diet.HERBIVORE, None, (Biochemistry.CRYSTAL,)),
        biochemistry_of(SPEC, BodyPlan.QUADRUPED, Diet.VOID, None, ()),
        biochemistry_of(SPEC, BodyPlan.INCORPOREAL, Diet.SOUL, None, ()),
        biochemistry_of(SPEC, BodyPlan.QUADRUPED, Diet.HERBIVORE, None, world_life(WorldType.ICE_GIANT, Atmosphere.NONE)),
        biochemistry_of(SPEC, BodyPlan.AMORPHOUS, Diet.ENERGY, None, (), kind=SpeciesClass.ENERGY),
        biochemistry_of(SPEC, BodyPlan.QUADRUPED, Diet.HERBIVORE, None, world_life(WorldType.IRON, Atmosphere.NONE)),
    }
    assert reached == set(Biochemistry)
    assert Biochemistry.PLASMA in world_life(WorldType.HOT_GIANT, Atmosphere.DENSE)
    assert biochemistry_of(SPEC, BodyPlan.QUADRUPED, Diet.ENERGY, None, world_life(WorldType.HOT_GIANT, Atmosphere.DENSE)) is Biochemistry.PLASMA


def test_plasma_bodies_are_untouched_by_warmth() -> None:
    assert Biochemistry.PLASMA in ATHERMIC_BIOCHEMISTRY
    assert born_regulation(Biochemistry.PLASMA, BodyPlan.AMORPHOUS) is Thermoregulation.ATHERMIC
    assert born_regulation(Biochemistry.CARBON_METHANE, BodyPlan.SERPENTINE) is Thermoregulation.ECTOTHERM


async def test_life_taken_out_of_its_warmth_dwindles_and_the_loss_is_told(session: AsyncSession, world: CoreWorld) -> None:
    warm, cold = world.regions[0], world.regions[1]
    await land(session, world, warm, temperature=60)
    await land(session, world, cold, temperature=5)
    methane = await kind(session, world, "Frost Slime", warm, 50, biochemistry=Biochemistry.CARBON_METHANE)
    plasma = await kind(session, world, "Storm Wisp", cold, 50, biochemistry=Biochemistry.PLASMA)
    water = await kind(session, world, "Reed Hen", warm, 50, biochemistry=Biochemistry.CARBON_WATER)
    await keep_living_ways(await manual_context(session, "ecology", tuned_rules(biochemistry={"out_of_band_loss": 10})), set())
    assert (await range_of(session, methane, warm)).abundance == 40
    assert (await range_of(session, plasma, cold)).abundance == 40
    assert (await range_of(session, water, warm)).abundance == 50
    assert await told(session, "life.out_of_its_world")


async def test_kinds_of_power_are_rederived_as_plasma_once(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    power = await kind(session, world, "Old Spark", region, 30, species_class=SpeciesClass.ENERGY, biochemistry=Biochemistry.CARBON_WATER)
    held_kind = await kind(
        session, world, "Held Spark", region, 30, species_class=SpeciesClass.ENERGY, biochemistry=Biochemistry.CARBON_WATER, locked=["biochemistry"]
    )
    ctx = await manual_context(session, "ecology")
    assert await backfill_biochemistry(ctx) == 1
    first, second = await session.get(SpeciesProfileRow, power.id), await session.get(SpeciesProfileRow, held_kind.id)
    assert first is not None and first.biochemistry is Biochemistry.PLASMA
    assert second is not None and second.biochemistry is Biochemistry.CARBON_WATER
    assert await backfill_biochemistry(ctx) == 0
