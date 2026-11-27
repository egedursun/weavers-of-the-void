from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.models.entity_stats import FactionStats, PeopleStats, StructureStats
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.life import band_pressure, collect_taxes, keep_order, prestige
from tests.engine.core.factories import CoreWorld, entity, settlement


async def test_a_town_s_poverty_and_taxes_follow_its_people_s_prosperity_not_its_emptied_purse(session: AsyncSession, world: CoreWorld) -> None:
    town_row = await settlement(session, "Emptypurse", world, world.regions[0], prosperity=70)
    session.add(SettlementProfileRow(settlement_entity_id=town_row.id, size_tier=SizeTier.TOWN, public_order=50, crime=0, tax_rate=20, locked=[]))
    await session.flush()
    ctx = await manual_context(session, "poverty")
    found: list[tuple[int, int, int]] = []
    for purse in (0, 100):
        set_stats(town_row, wealth=purse, prosperity=70)
        town = await town_of(ctx, town_row, await KnowledgeMap.load(session))
        town.profile.public_order, town.profile.crime, town.profile.treasury = 50, 0, 0
        await keep_order(ctx, town, justice=0.5, bands=[], hierarchy=0, pressure=0.0)
        found.append((town.profile.crime, town.profile.public_order, await collect_taxes(ctx, town)))
    assert found[0] == found[1]
    crime, order, taxes = found[0]
    assert crime < 40 and order > 0 and taxes > 0


async def test_a_band_preys_hardest_on_its_own_land_and_only_in_part_on_its_neighbours(session: AsyncSession, world: CoreWorld) -> None:
    town_row = await settlement(session, "Crossmarch", world, world.regions[0])
    near = await entity(session, "Ford Robbers", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=world.regions[0].id)
    far = await entity(session, "Hill Robbers", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=world.regions[1].id)
    session.add(SettlementProfileRow(settlement_entity_id=town_row.id, size_tier=SizeTier.TOWN, locked=[]))
    await session.flush()
    ctx = await manual_context(session, "bands")
    town = await town_of(ctx, town_row, await KnowledgeMap.load(session))
    atlas = await RegionAtlas.load(session)
    pressure = band_pressure(ctx.rules, atlas, town, [near, far])
    assert pressure == 1 + ctx.rules.crime.neighbour_band_pct / 100 and pressure < 2


async def test_a_town_taxes_a_whole_epoch_of_years_and_the_people_that_draw_on_it(session: AsyncSession, world: CoreWorld) -> None:
    town_row = await settlement(session, "Tollridge", world, world.regions[0], population=4000, prosperity=50)
    session.add(
        SettlementProfileRow(settlement_entity_id=town_row.id, size_tier=SizeTier.TOWN, public_order=100, crime=0, tax_rate=20, admin_capacity=100, locked=[])
    )
    await session.flush()
    ctx = await manual_context(session, "tolls")
    town = await town_of(ctx, town_row, await KnowledgeMap.load(session))
    town.profile.public_order, town.profile.admin_capacity = 100, 100
    alone = await collect_taxes(ctx, town)
    table = ctx.rules.taxation
    one_year = 4000 / 100 * table.per_capita_output * 0.5 * 0.2
    assert alone >= one_year * table.per_epoch(1) * 0.5
    throng = await entity(session, "Hill Throng", EntityType.PEOPLE, PeopleStats(population=12000), world_id=world.world.id, location_id=world.regions[0].id)
    await BondRepository(session).connect(BondDraft(town_row.id, throng.id, BondKind.DESCENDS_FROM, 1))
    await session.flush()
    assert await collect_taxes(ctx, town) > alone * 3


async def test_a_ruin_lends_a_town_none_of_the_splendor_it_had_when_it_stood(session: AsyncSession, world: CoreWorld) -> None:
    town_row = await settlement(session, "Brokenspire", world, world.regions[0])
    session.add(SettlementProfileRow(settlement_entity_id=town_row.id, size_tier=SizeTier.TOWN, public_order=50, crime=0, tax_rate=20, locked=[]))
    hall = await entity(session, "Fallen Hall", EntityType.STRUCTURE, StructureStats(splendor=90), world_id=world.world.id, location_id=town_row.id)
    session.add(
        StructureProfileRow(
            structure_entity_id=hall.id, kind=next(iter(StructureKind)), construction_state=ConstructionState.COMPLETE, condition=100, locked=[]
        )
    )
    await session.flush()
    ctx = await manual_context(session, "prestige")
    town = await town_of(ctx, town_row, await KnowledgeMap.load(session))
    await prestige(ctx, town)
    standing = town.profile.prestige
    profile = await session.get(StructureProfileRow, hall.id)
    assert profile is not None
    profile.construction_state, profile.condition = ConstructionState.RUINED, 0
    await session.flush()
    await prestige(ctx, town)
    assert town.profile.prestige < standing
