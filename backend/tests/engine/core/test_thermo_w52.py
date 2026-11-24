from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import Biochemistry
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.nature import Thermoregulation
from aerona.engine.ecology.profiles import born_regulation
from aerona.engine.ecology.w52_products import backfill_regulation
from aerona.engine.nature.seasons import activity
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, tuned_rules
from tests.engine.core.living_kinds import kind

RULES = Rules()


def test_four_regulations_and_heterotherms_switch_while_athermic_bodies_never_slow() -> None:
    assert len(Thermoregulation) == 5
    cold = TemperatureBand.FROZEN
    assert activity(RULES, Thermoregulation.ATHERMIC, cold) == activity(RULES, Thermoregulation.ATHERMIC, TemperatureBand.SEARING) == 1.0
    deep = tuned_rules(thermoregulation={"heterotherm_switch": 90})
    assert activity(deep, Thermoregulation.HETEROTHERM, cold) < activity(RULES, Thermoregulation.HETEROTHERM, cold) < 1.0
    assert activity(RULES, Thermoregulation.HETEROTHERM, TemperatureBand.TEMPERATE) == 1.0


def test_spirit_crystal_plasma_and_made_bodies_are_born_athermic() -> None:
    for chemistry in (Biochemistry.SPIRIT, Biochemistry.CRYSTAL, Biochemistry.PLASMA):
        assert born_regulation(chemistry, BodyPlan.QUADRUPED) is Thermoregulation.ATHERMIC
    assert born_regulation(Biochemistry.CARBON_WATER, BodyPlan.CONSTRUCT) is Thermoregulation.ATHERMIC
    assert born_regulation(Biochemistry.CARBON_WATER, BodyPlan.QUADRUPED) is Thermoregulation.ENDOTHERM


async def test_bodies_of_the_old_record_that_warmth_cannot_touch_become_athermic_once(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    golem = await kind(session, world, "Old Golem", region, 20, body_plan=BodyPlan.CONSTRUCT, thermoregulation=Thermoregulation.ENDOTHERM)
    wisp = await kind(session, world, "Old Wisp", region, 20, biochemistry=Biochemistry.SPIRIT, thermoregulation=Thermoregulation.ENDOTHERM)
    hare = await kind(session, world, "Old Hare", region, 20, thermoregulation=Thermoregulation.ENDOTHERM)
    ctx = await manual_context(session, "ecology")
    assert await backfill_regulation(ctx) == 2
    found = {
        row.species_entity_id: row.thermoregulation
        for row in [await session.get(SpeciesProfileRow, item.id) for item in (golem, wisp, hare)]
        if row is not None
    }
    assert found == {golem.id: Thermoregulation.ATHERMIC, wisp.id: Thermoregulation.ATHERMIC, hare.id: Thermoregulation.ENDOTHERM}
    assert await backfill_regulation(ctx) == 0
