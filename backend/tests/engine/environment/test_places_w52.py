from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.body import InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.body import BodyPart, DamageType, HarmCause, InjuryKind, InjuryState
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import PlaceStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.environment.place_traits import bathe, collapse_sinkhole, places_by_region
from aerona.engine.environment.places import apply_kind
from aerona.engine.industry.energy import supply_of
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, mortal, seed_core_world, settlement, surveyed, tuned_rules

RULES = Rules()


async def place_of(session: AsyncSession, world: CoreWorld, kind: PlaceKind, name: str) -> EntityRow:
    place = await entity(session, name, EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(PlaceProfileRow(entity_id=place.id, kind=kind, locked=[]))
    await session.flush()
    return place


def height(kind: PlaceKind) -> int:
    ground = PlaceEnvironmentRow(locked=[])
    apply_kind(RULES, ground, kind)
    return ground.height_advantage


def test_a_plateau_gives_height_a_valley_does_not() -> None:
    assert height(PlaceKind.PLATEAU) > height(PlaceKind.VALLEY)
    assert height(PlaceKind.PLATEAU) >= RULES.places.plateau_defence


async def test_a_waterfall_powers_the_mills_of_its_land(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    town = await settlement(session, "Millrace", world, world.regions[0])
    await place_of(session, world, PlaceKind.WATERFALL, "The Long Fall")
    ctx = await manual_context(session, "test", RULES)
    falls = await places_by_region(session, PlaceKind.WATERFALL)
    assert falls == Counter({world.regions[0].id: 1})
    book = await EconomyBook.load(ctx)
    still, _ = await supply_of(ctx, book, town, Counter())
    driven, _ = await supply_of(ctx, book, town, Counter(), falls=falls)
    assert driven[EnergyKind.WATER] - still[EnergyKind.WATER] == RULES.places.waterfall_power


async def sinkhole_world(session: AsyncSession) -> tuple[CoreWorld, EntityRow, TickContext]:
    world = await seed_core_world(session)
    place = await place_of(session, world, PlaceKind.SINKHOLE, "The Swallow")
    return world, place, await manual_context(session, "test", tuned_rules(places={"sinkhole_collapse_pct": 100}))


async def test_a_sinkhole_can_swallow_what_is_built_on_it(session: AsyncSession) -> None:
    world, place, ctx = await sinkhole_world(session)
    hut = await entity(session, "Edge Hut", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=place.id)
    session.add(StructureProfileRow(structure_entity_id=hut.id, kind=StructureKind.TEMPLE, condition=100))
    await session.flush()
    assert await collapse_sinkhole(ctx, place) == 1
    profile = await session.get(StructureProfileRow, hut.id)
    assert profile is not None and profile.condition == 100 - RULES.places.sinkhole_collapse_harm
    assert "place.collapsed" in set(await session.scalars(select(IncidentRow.kind)))


async def test_a_hot_spring_eases_the_wounds_of_those_who_bathe(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    spring = await place_of(session, world, PlaceKind.HOT_SPRING, "Warm Pool")
    ctx = await manual_context(session, "test", RULES)
    bather = await mortal(session, "Bather", world, spring.id)
    wound = InjuryRow(
        bearer_node_id=bather.id,
        part=BodyPart.LEFT_ARM,
        kind=InjuryKind.CUT,
        damage_type=DamageType.CUT,
        severity=4,
        state=InjuryState.HEALING,
        function_loss=20,
        cause_kind=HarmCause.ACCIDENT,
        epoch=1,
    )
    session.add(wound)
    await session.flush()
    assert await bathe(ctx, spring) == 1 and wound.severity == 4 - RULES.places.hot_spring_heal
