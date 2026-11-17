from itertools import count

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.lore import ITEM_CLASSES, KNOWLEDGE_ITEMS, REGALIA, WEAPONS
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.demography import InheritanceCustom, MartialStyle
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.domain.models.entity_stats import CultStats, HouseStats, ItemStats, VesselStats
from aerona.engine.context import TickContext
from aerona.engine.lore.arms import GUARDS
from aerona.engine.lore.items import POWERS, WAYFINDERS, Holding, mend_bearer, nearest_foe
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement

C = ItemClass
MADE = count(1)


async def holding(session: AsyncSession, world: CoreWorld, item_class: ItemClass, holder: EntityRow, home: EntityRow | None, *, value: int = 50) -> Holding:
    item = await entity(session, f"The {item_class.value} {next(MADE)}", EntityType.ITEM, ItemStats(), world_id=world.world.id)
    return Holding(item, ItemProfileRow(item_entity_id=item.id, item_class=item_class, value=value, quality=50, locked=[]), holder, home)


async def scene(session: AsyncSession, world: CoreWorld) -> tuple[TickContext, EntityRow, EntityRow]:
    ctx = await manual_context(session, "test")
    town = await settlement(session, "Brookhold", world, world.regions[0])
    keeper = await mortal(session, "Ilsa", world, town.id)
    return ctx, town, keeper


async def test_instruments_bind_a_people_and_mirrors_watch_its_foe(session: AsyncSession, world: CoreWorld) -> None:
    ctx, _, keeper = await scene(session, world)
    culture = PeopleCultureRow(
        people_entity_id=world.people.id,
        cohesion=40,
        literacy=0,
        urbanisation=0,
        martial_style=next(iter(MartialStyle)),
        inheritance=next(iter(InheritanceCustom)),
    )
    session.add(culture)
    await session.flush()
    assert await POWERS[C.INSTRUMENT](ctx, await holding(session, world, C.INSTRUMENT, keeper, world.people)) == "music"
    assert culture.cohesion > 40
    assert await POWERS[C.INSTRUMENT](ctx, await holding(session, world, C.INSTRUMENT, keeper, None)) is None
    foe = await settlement(session, "Rivalhold", world, world.regions[0])
    assert await nearest_foe(ctx, world.people.id) is None
    assert await POWERS[C.MIRROR](ctx, await holding(session, world, C.MIRROR, keeper, world.people)) is None
    await bond(session, world.people.id, foe.id, BondKind.ENEMY)
    assert await nearest_foe(ctx, world.people.id) == foe.id
    assert await POWERS[C.MIRROR](ctx, await holding(session, world, C.MIRROR, keeper, world.people)) == "seen"


async def test_vessels_feed_the_patron_and_keys_and_coin_serve_the_town(session: AsyncSession, world: CoreWorld) -> None:
    ctx, town, keeper = await scene(session, world)
    assert await POWERS[C.VESSEL_OBJECT](ctx, await holding(session, world, C.VESSEL_OBJECT, keeper, town)) is None
    await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
    faith = world.son.faith
    assert await POWERS[C.VESSEL_OBJECT](ctx, await holding(session, world, C.VESSEL_OBJECT, keeper, town)) == "libation"
    assert world.son.faith > faith
    set_stats(town, defense=10, prosperity=10)
    assert await POWERS[C.KEY](ctx, await holding(session, world, C.KEY, keeper, town)) == "gates"
    assert await POWERS[C.KEY](ctx, await holding(session, world, C.KEY, keeper, world.people)) is None
    assert await POWERS[C.CURRENCY](ctx, await holding(session, world, C.CURRENCY, keeper, town)) == "coin"
    assert (stat(town, "defense") or 0) > 10 and (stat(town, "prosperity") or 0) > 10
    assert await POWERS[C.CURRENCY](ctx, await holding(session, world, C.CURRENCY, keeper, None)) is None


async def test_idols_stir_a_cult_jewels_raise_a_house_and_limbs_need_a_stump(session: AsyncSession, world: CoreWorld) -> None:
    ctx, town, keeper = await scene(session, world)
    cult = await entity(session, "The Watchers", EntityType.CULT, CultStats(zeal=20), world_id=world.world.id, location_id=town.id)
    assert await POWERS[C.IDOL](ctx, await holding(session, world, C.IDOL, cult, town)) == "worship"
    assert (stat(cult, "zeal") or 0) > 20
    assert await POWERS[C.IDOL](ctx, await holding(session, world, C.IDOL, keeper, town)) is None
    assert await POWERS[C.JEWEL](ctx, await holding(session, world, C.JEWEL, keeper, town)) is None
    house = await entity(session, "House Varn", EntityType.HOUSE, HouseStats(), world_id=world.world.id)
    profile = HouseProfileRow(house_entity_id=house.id, prestige=20, traits=[], seats=[], locked=[])
    session.add_all([profile, HouseMemberRow(house_entity_id=house.id, mortal_entity_id=keeper.id, joined_epoch=1, by_marriage=False)])
    await session.flush()
    assert await POWERS[C.CROWN](ctx, await holding(session, world, C.CROWN, keeper, town, value=100)) == "prestige"
    assert profile.prestige > 20
    assert await POWERS[C.JEWEL](ctx, await holding(session, world, C.JEWEL, cult, town)) is None
    assert await POWERS[C.PROSTHESIS](ctx, await holding(session, world, C.PROSTHESIS, keeper, town)) is None
    assert await POWERS[C.PROSTHESIS](ctx, await holding(session, world, C.PROSTHESIS, cult, town)) is None
    assert not await mend_bearer(ctx, keeper, 10)


async def test_drugs_devices_communicators_and_parts_each_serve_their_holder(session: AsyncSession, world: CoreWorld) -> None:
    ctx, town, keeper = await scene(session, world)
    assert await POWERS[C.DRUG](ctx, await holding(session, world, C.DRUG, keeper, town)) in {"dose", "dependence"}
    assert await POWERS[C.DRUG](ctx, await holding(session, world, C.DRUG, town, town)) is None
    set_stats(town, prosperity=10)
    assert await POWERS[C.DEVICE](ctx, await holding(session, world, C.DEVICE, keeper, town)) == "device"
    assert (stat(town, "prosperity") or 0) > 10
    assert await POWERS[C.COMMUNICATOR](ctx, await holding(session, world, C.COMMUNICATOR, keeper, None)) is None
    assert await POWERS[C.VEHICLE_PART](ctx, await holding(session, world, C.VEHICLE_PART, keeper, town)) is None
    ship = await entity(session, "The Tern", EntityType.VESSEL, VesselStats(), world_id=world.world.id)
    vessel = VesselProfileRow(entity_id=ship.id, kind=VehicleKind.SHIP, frame=VehicleFrame.MOTORBOAT, captain_entity_id=keeper.id, condition=50, locked=[])
    session.add(vessel)
    await session.flush()
    assert await POWERS[C.VEHICLE_PART](ctx, await holding(session, world, C.VEHICLE_PART, keeper, town)) == "repaired"
    assert vessel.condition > 50


def test_every_class_of_item_does_something_in_the_world() -> None:
    roles = set(WEAPONS) | set(KNOWLEDGE_ITEMS) | set(REGALIA) | set(GUARDS) | set(POWERS) | set(WAYFINDERS) | {C.TOOL, C.STANDARD}
    assert sorted(item.value for item in ItemClass if item not in roles) == []
    assert all(ITEM_CLASSES[item].coverage == 0 or item in GUARDS or item in POWERS for item in ItemClass)
