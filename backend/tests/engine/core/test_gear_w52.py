from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.catch import GEAR, GROUNDS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.ecology import HerdRow, SpeciesUseRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.crafts import CatchGround, Gear
from aerona.domain.enums.ecology import AnimalRole, DomesticationStage
from aerona.domain.enums.environment import ScarKind
from aerona.engine.context import TickContext
from aerona.engine.crafts.catch import regrowth_scale, trap_factors, worked
from aerona.engine.crafts.shores import harm_by_gear
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules

RULES = Rules()


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "crafts", rules=tuned_rules(**rules))


def ground(gear: Gear, *, collapsed: bool = False) -> CatchGroundRow:
    return CatchGroundRow(
        source_entity_id=1, region_entity_id=2, ground=CatchGround.FISHERY, gear=gear, first_stock=100, stock=100, effort=50, collapsed=collapsed, locked=[]
    )


def test_every_gear_belongs_to_a_ground_and_heavy_gear_takes_more_and_regrows_slower() -> None:
    assert set(GEAR) == {gear for spec in GROUNDS.values() for gear in spec.gear}
    assert worked(RULES, ground(Gear.TRAWLS)) > worked(RULES, ground(Gear.LINES))
    assert worked(RULES, ground(Gear.LINES, collapsed=True)) == 0.0
    assert GEAR[Gear.TRAWLS].harms_bed and GEAR[Gear.POISON].sickens and GEAR[Gear.HUNTING_ANIMALS].needs_animals


async def test_depleting_gear_slows_regrowth_and_a_collapse_slows_it_more(session: AsyncSession, world: CoreWorld) -> None:
    for source, gear in ((world.regions[1].id, Gear.LINES), (world.regions[2].id, Gear.TRAWLS)):
        session.add(CatchGroundRow(source_entity_id=source, region_entity_id=source, ground=CatchGround.FISHERY, gear=gear, first_stock=100, locked=[]))
    await session.flush()
    light, heavy = await regrowth_scale(session, RULES, world.regions[1].id), await regrowth_scale(session, RULES, world.regions[2].id)
    assert light == 1 - GEAR[Gear.LINES].depletion(RULES) / 200 and heavy == 1 - GEAR[Gear.TRAWLS].depletion(RULES) / 200 and heavy < light
    row = await session.get(CatchGroundRow, (world.regions[2].id, world.regions[2].id))
    assert row is not None
    row.collapsed = True
    await session.flush()
    assert await regrowth_scale(session, RULES, world.regions[2].id) == heavy * RULES.grounds.collapsed_regrowth_pct / 100


async def test_trawls_scar_the_bed_and_poison_sickens_the_land(session: AsyncSession, world: CoreWorld) -> None:
    await environment_survey(await at(session, 2))
    ctx = await at(session, 3)
    land = await session.get(RegionEnvironmentRow, world.regions[1].id)
    assert land is not None
    eroded, load = land.scars.get(ScarKind.ERODED.value, 0), land.disease_load
    trawl = CatchGroundRow(
        source_entity_id=world.regions[1].id, region_entity_id=land.entity_id, ground=CatchGround.FISHERY, gear=Gear.TRAWLS, first_stock=100, locked=[]
    )
    await harm_by_gear(ctx, trawl)
    assert land.scars.get(ScarKind.ERODED.value, 0) > eroded and land.disease_load == load
    poison = CatchGroundRow(
        source_entity_id=world.regions[1].id, region_entity_id=land.entity_id, ground=CatchGround.FISHERY, gear=Gear.POISON, first_stock=100, locked=[]
    )
    await harm_by_gear(ctx, poison)
    assert land.disease_load == min(100, load + RULES.grounds.poison_sickness_pct)
    lines = CatchGroundRow(
        source_entity_id=world.regions[1].id, region_entity_id=land.entity_id, ground=CatchGround.FISHERY, gear=Gear.LINES, first_stock=100, locked=[]
    )
    before = dict(land.scars), land.disease_load
    await harm_by_gear(ctx, lines)
    assert (dict(land.scars), land.disease_load) == before
    await session.flush()
    kinds = set(await session.scalars(select(IncidentRow.kind)))
    assert {"catch.bed_harmed", "catch.poisoned_catch"} <= kinds


async def test_hunting_animals_catch_only_where_a_town_keeps_them(session: AsyncSession, world: CoreWorld) -> None:
    await environment_survey(await at(session, 2))
    region = world.regions[0].id
    town = await settlement(session, "Houndmere", world, world.regions[0])
    session.add(
        CatchGroundRow(
            source_entity_id=world.species.id,
            region_entity_id=region,
            ground=CatchGround.GAME_HUNT,
            gear=Gear.HUNTING_ANIMALS,
            first_stock=50,
            effort=50,
            locked=[],
        )
    )
    await session.flush()
    assert (await trap_factors(session, RULES))[world.species.id, region] == 0.0
    session.add(SpeciesUseRow(species_entity_id=world.species.id, use=AnimalRole.HUNTING))
    session.add(HerdRow(community_entity_id=town.id, species_entity_id=world.species.id, head=10, stage=DomesticationStage.DOMESTICATED, locked=[]))
    await session.flush()
    row = await session.get(CatchGroundRow, (world.species.id, region))
    assert row is not None
    expected = worked(RULES, row) * (1 + RULES.species_roles.hunting_catch_pct / 100)
    assert (await trap_factors(session, RULES))[world.species.id, region] == expected
