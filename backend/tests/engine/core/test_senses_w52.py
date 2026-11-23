from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.senses import AMBUSH, PURPOSES, SENSES, TRACKING
from aerona.db.tables.nature import SenseProfileRow
from aerona.domain.enums.nature import SenseKind
from aerona.engine.nature.senses import in_water, leading_sense, reach_of, sense_score
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, tuned_rules
from tests.engine.core.living_kinds import kind, land

RULES = Rules()


def test_eleven_senses_and_the_new_two_serve_ambush_and_tracking() -> None:
    assert len(SENSES) == len(SenseKind) == 11
    assert SenseKind.ELECTRIC in PURPOSES[AMBUSH] and SenseKind.ULTRAVIOLET in PURPOSES[TRACKING]


async def test_an_electric_sense_reaches_further_in_water_and_ultraviolet_by_its_rule(session: AsyncSession, world: CoreWorld) -> None:
    wet, dry = world.regions[0], world.regions[1]
    await land(session, world, wet, wetland=90)
    await land(session, world, dry, wetland=0)
    eel = await kind(session, world, "Marsh Eel", wet, 50)
    mole = await kind(session, world, "Dust Mole", dry, 50)
    assert await in_water(session, eel.id) and not await in_water(session, mole.id)
    rules = tuned_rules(senses={"electric_range": 2, "electric_water_pct": 200, "ultraviolet_track_pct": 60})
    assert await reach_of(session, rules, eel.id, SenseKind.ELECTRIC) == 2.0
    assert await reach_of(session, rules, mole.id, SenseKind.ELECTRIC) == 1.0
    assert await reach_of(session, rules, mole.id, SenseKind.ULTRAVIOLET) == 2.0
    assert await reach_of(session, rules, mole.id, SenseKind.SIGHT) == 1.0


async def test_the_strongest_weighted_sense_leads_and_reach_weighs_the_score(session: AsyncSession, world: CoreWorld) -> None:
    wet, dry = world.regions[0], world.regions[1]
    await land(session, world, wet, wetland=90)
    await land(session, world, dry, wetland=0)
    eel = await kind(session, world, "Shock Eel", wet, 50)
    twin = await kind(session, world, "Shock Mole", dry, 50)
    for holder in (eel, twin):
        session.add(SenseProfileRow(holder_entity_id=holder.id, sense=SenseKind.ELECTRIC, acuity=80, locked=[]))
    await session.flush()
    assert await leading_sense(session, eel.id, AMBUSH) is SenseKind.ELECTRIC
    assert await sense_score(session, RULES, eel.id, AMBUSH) > await sense_score(session, RULES, twin.id, AMBUSH) > 0
