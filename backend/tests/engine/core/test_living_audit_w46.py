from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.agrarian import PerennialRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.living import LivingLineRow, LivingProfileRow, SymbiontRow
from aerona.db.tables.made import SalvageSiteRow
from aerona.db.tables.networks import NetworkOutageRow, NetworkProfileRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.powers import MagicSystemRow
from aerona.domain.enums.agrarian import PerennialKind
from aerona.domain.enums.ecology import DomesticationStage, Temperament
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.living import CultivationMethod, Fertility, GrowthStage, HostPlacement, HostRelation, Metabolism
from aerona.domain.enums.networks import NetworkCarrier, OutageCause
from aerona.domain.enums.place import PlaceKind
from aerona.domain.models.entity_stats import NetworkStats, PeopleStats, PlaceStats, SpeciesStats
from aerona.engine.economy.purse import coin_of, give_coin
from aerona.engine.living.backfill import keep_kinds_alive, legacy_backfill
from aerona.engine.living.kin import remove_symbiont
from aerona.engine.living.production import heal_living_links, seed_dues
from aerona.engine.living.profiles import keep_profiles
from aerona.engine.made.backfill import keep_made_kinds
from aerona.engine.made.backfill import legacy_backfill as made_backfill
from aerona.engine.powers.backfill import systems
from aerona.engine.primitives.stats import stat_or
from aerona.services.integrity.living_links import mend_living_links
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement
from tests.engine.core.test_minds_w44 import at


async def test_a_grower_of_a_sterile_line_pays_its_owner_each_epoch(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    owner = await mortal(session, "Ila Venn", world, town.id)
    grower = await mortal(session, "Oren Vale", world, town.id)
    line = LivingLineRow(name="the seedless grain", method=CultivationMethod.ENGINEERING, fertility=Fertility.STERILE, owner_node_id=owner.id, locked=[])
    session.add(line)
    await session.flush()
    session.add(
        PerennialRow(region_entity_id=world.regions[0].id, kind=PerennialKind.ORCHARD, line_id=line.id, owner_node_id=grower.id, planted_epoch=1, locked=[])
    )
    await session.flush()
    ctx = await at(session, 2)
    await give_coin(session, ctx.rules, grower, 50)
    before = await coin_of(session, ctx.rules, owner)
    assert await seed_dues(ctx) == 1
    assert await coin_of(session, ctx.rules, owner) > before


async def test_a_cut_in_a_grown_link_heals_by_itself(session: AsyncSession, world: CoreWorld) -> None:
    link = await entity(session, "the root way", EntityType.NETWORK, NetworkStats(reach=3), world_id=world.world.id)
    session.add(NetworkProfileRow(network_entity_id=link.id, carrier=NetworkCarrier.GROWN_LINK))
    outage = NetworkOutageRow(network_entity_id=link.id, cause=OutageCause.STORM, epoch=1, epochs=4, severity=50)
    session.add(outage)
    await session.flush()
    assert await heal_living_links(await at(session, 2)) == 1
    assert outage.epochs == 3


async def test_a_people_bonded_to_its_partner_suffers_when_the_partner_is_taken(session: AsyncSession, world: CoreWorld) -> None:
    folk = await entity(session, "the bonded folk", EntityType.PEOPLE, PeopleStats(population=400, prosperity=60, craft=60), world_id=world.world.id)
    row = SymbiontRow(host_node_id=folk.id, placement=HostPlacement.SKIN, relation=HostRelation.MUTUAL, strength=40, since_epoch=1, locked=[])
    session.add(row)
    await session.flush()
    await remove_symbiont(await at(session, 2), row)
    assert stat_or(folk, "prosperity", 0) == 50 and stat_or(folk, "craft", 0) == 50


async def test_a_neglected_living_thing_turns_from_its_handler(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    captain = await mortal(session, "Ila Venn", world, town.id)
    ship = await mortal(session, "the grown hull", world, town.id)
    session.add(
        LivingProfileRow(
            thing_node_id=ship.id,
            metabolism=Metabolism.LIGHT,
            growth_stage=GrowthStage.GROWN,
            temperament=Temperament.FIERCE,
            bonded_to_node_id=captain.id,
            bond=5,
            health=100,
            age_seasons=10,
            locked=[],
        )
    )
    await session.flush()
    await keep_profiles(await at(session, 2))
    row = await session.get(LivingProfileRow, ship.id)
    assert row is not None and row.bonded_to_node_id is None


async def test_integrity_marks_the_lifeless_dead_feeds_the_unfed_and_drops_symbionts_without_a_body(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greenmere", world, world.regions[0])
    being = await mortal(session, "Ila Venn", world, town.id)
    session.add(LivingProfileRow(thing_node_id=being.id, metabolism=Metabolism.FEEDING, growth_stage=GrowthStage.GROWN, health=0, locked=[]))
    session.add(SymbiontRow(host_node_id=town.id, placement=HostPlacement.SKIN, relation=HostRelation.MUTUAL, strength=30, since_epoch=1, locked=[]))
    await session.flush()
    ctx = await at(session, 2)
    assert await mend_living_links(session, ctx.rules, 2) >= 3
    row = await session.get(LivingProfileRow, being.id)
    await session.refresh(row)
    assert row is not None and row.growth_stage is GrowthStage.DEAD and row.feed_commodity is CommodityKind.FODDER
    assert await session.scalar(select(SymbiontRow.id).where(SymbiontRow.host_node_id == town.id)) is None


async def test_a_species_bred_after_the_backfill_still_gains_a_line_and_only_once(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    await legacy_backfill(ctx)
    beast = await entity(session, "Marsh striders", EntityType.SPECIES, SpeciesStats(), world_id=world.world.id, location_id=world.regions[0].id)
    kind = SpeciesProfileRow(species_entity_id=beast.id, stage=DomesticationStage.WILD)
    session.add(kind)
    await session.flush()
    kind.stage = DomesticationStage.DOMESTICATED
    await session.flush()
    later = await at(session, 3)
    assert await keep_kinds_alive(later) >= 1
    assert await keep_kinds_alive(later) == 0
    lines = await session.scalar(select(func.count()).select_from(LivingLineRow).where(LivingLineRow.species_entity_id == kind.species_entity_id))
    assert lines == 1


async def test_a_ruin_that_appears_after_the_backfill_still_becomes_a_salvage_site(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    await made_backfill(ctx)
    wreck = await entity(session, "the fallen span", EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(PlaceProfileRow(entity_id=wreck.id, kind=PlaceKind.MEGASTRUCTURE_RUIN))
    await session.flush()
    assert await keep_made_kinds(ctx) >= 1
    assert await keep_made_kinds(ctx) == 0
    assert await session.get(SalvageSiteRow, wreck.id) is not None


async def test_a_world_without_a_system_of_power_gains_one_whenever_it_lacks_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    await systems(ctx)
    for row in list(await session.scalars(select(MagicSystemRow).where(MagicSystemRow.scope_node_id == world.world.id))):
        await session.delete(row)
    await session.flush()
    assert await systems(ctx) == 1
    assert await systems(ctx) == 0
