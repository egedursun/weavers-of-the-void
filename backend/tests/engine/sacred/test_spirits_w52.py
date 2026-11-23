from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.region import RegionMemoryRow
from aerona.db.tables.sacred import GeniusLocusRow, SpiritOfficeRow
from aerona.db.tables.sites import ExcavationRow
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.crafts import CatchGround, Gear
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.region import RegionMemoryKind
from aerona.domain.enums.sacred import BureauRank, GeniusLocusKind, PetitionKind, PetitionStatus, SpiritOffence
from aerona.domain.models.entity_stats import PlaceStats, ResourceStats, SpiritStats
from aerona.engine.primitives.stats import stat_or
from aerona.engine.sacred import control
from aerona.engine.sacred.spirits import SpiritTally, backfill_spirits, offence_of
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement
from tests.engine.core.test_sacred_w25 import at, society


async def place(session: AsyncSession, world: CoreWorld, name: str, kind: PlaceKind) -> int:
    found = await entity(session, name, EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(PlaceProfileRow(entity_id=found.id, kind=kind, locked=[]))
    await session.flush()
    return found.id


async def test_great_battlefields_and_ruins_gain_spirits_and_a_dug_ruin_or_an_emptied_ground_offends_them(session: AsyncSession, world: CoreWorld) -> None:
    await settlement(session, "Graveford", world, world.regions[0])
    field = await place(session, world, "Red Meadow", PlaceKind.BATTLEFIELD)
    ruin = await place(session, world, "Fallen Hall", PlaceKind.RUIN)
    session.add(
        RegionMemoryRow(world_id=world.world.id, region_entity_id=world.regions[0].id, kind=RegionMemoryKind.BATTLE, magnitude=80, source_key="w", epoch=1)
    )
    await session.flush()
    ctx = await at(session, 3)
    assert await backfill_spirits(ctx, SpiritTally()) >= 2
    kinds = {row.place_entity_id: row.kind for row in await session.scalars(select(GeniusLocusRow))}
    assert kinds[field] is GeniusLocusKind.BATTLEFIELD and kinds[ruin] is GeniusLocusKind.RUIN
    ruin_spirit = await session.scalar(select(GeniusLocusRow).where(GeniusLocusRow.place_entity_id == ruin))
    ruin_place = await session.get(EntityRow, ruin)
    assert ruin_spirit is not None and ruin_place is not None
    session.add(ExcavationRow(site_entity_id=ruin, started_epoch=3))
    await session.flush()
    assert await offence_of(ctx, ruin_spirit, ruin_place) is SpiritOffence.TABOO
    pond = await entity(session, "Stocked Pond", EntityType.RESOURCE, ResourceStats(abundance=10), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(
        CatchGroundRow(
            source_entity_id=pond.id,
            region_entity_id=world.regions[0].id,
            ground=CatchGround.FISHERY,
            gear=Gear.NETS,
            first_stock=50,
            collapsed=True,
            locked=[],
        )
    )
    await session.flush()
    field_spirit = await session.scalar(select(GeniusLocusRow).where(GeniusLocusRow.place_entity_id == field))
    field_place = await session.get(EntityRow, field)
    assert field_spirit is not None and await offence_of(ctx, field_spirit, field_place) is SpiritOffence.OVERHARVEST


async def test_a_granted_petition_for_vengeance_curses_the_wrongdoer_and_one_for_protection_strengthens_the_town(
    session: AsyncSession, world: CoreWorld
) -> None:
    town = await settlement(session, "Coinbridge", world, world.regions[1])
    session.add(society(town.id, 5000))
    merchant = await mortal(session, "Hollis", world, town.id)
    cheat = await mortal(session, "Vane", world, town.id)
    spring = await entity(session, "Spirit of the Spring", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=town.id)
    session.add(SpiritOfficeRow(spirit_entity_id=spring.id, rank=BureauRank.LOCAL, overseer_node_id=world.son.id, jurisdiction_entity_id=town.id, locked=[]))
    await session.flush()
    ctx = await at(session, 3)
    vengeance = await control.lodge_petition(ctx, merchant.id, spring.id, PetitionKind.VENGEANCE, defendant_id=None, bribe=0, target_id=cheat.id)
    assert vengeance.target_node_id == cheat.id
    await control.judge(ctx, vengeance.id, True, None)
    assert vengeance.status is PetitionStatus.GRANTED
    curse = await session.scalar(select(AfflictionRow).where(AfflictionRow.bearer_node_id == cheat.id))
    assert curse is not None and curse.package is PackageKind.FORTUNE
    guard = await control.lodge_petition(ctx, town.id, spring.id, PetitionKind.PROTECTION, defendant_id=None, bribe=0)
    before = stat_or(town, "defense", 0)
    await control.judge(ctx, guard.id, True, None)
    assert stat_or(town, "defense", 0) == before + ctx.rules.petitions.protection_defence
