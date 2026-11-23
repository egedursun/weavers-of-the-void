from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.ecology import Diet, DomesticationStage, Sociality
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.ecology.domestication import taming_ease
from aerona.engine.ecology.living_ways import keep_living_ways
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules


async def kind(session: AsyncSession, world: CoreWorld, name: str, region: EntityRow, abundance: int, **profile: object) -> EntityRow:
    species = await entity(session, name, EntityType.SPECIES, SpeciesStats(hp=30, intelligence=10), world_id=world.world.id, location_id=region.id)
    session.add(SpeciesProfileRow(species_entity_id=species.id, **profile))
    session.add(SpeciesRangeRow(species_entity_id=species.id, region_entity_id=region.id, abundance=abundance, fit=100, since_epoch=0, locked=[]))
    await session.flush()
    return species


async def range_of(session: AsyncSession, species: EntityRow, region: EntityRow) -> SpeciesRangeRow:
    row = await session.get(SpeciesRangeRow, (species.id, region.id))
    assert row is not None
    return row


async def test_a_parasite_drains_its_hosts_and_thins_where_hosts_are_few(session: AsyncSession, world: CoreWorld) -> None:
    rich, poor = world.regions[0], world.regions[1]
    host = await kind(session, world, "Host Grazer", rich, 80, diet=Diet.HERBIVORE)
    await kind(session, world, "Host Tick", rich, 100, diet=Diet.PARASITE)
    lonely = await kind(session, world, "Lone Tick", poor, 60, diet=Diet.PARASITE)
    ctx = await manual_context(session, "ecology")
    tally = await keep_living_ways(ctx, set())
    assert (await range_of(session, host, rich)).abundance < 80
    assert (await range_of(session, lonely, poor)).abundance < 60
    assert tally.drained >= 1 and tally.thinned >= 1


async def test_a_small_colony_collapses_and_its_fall_tells_how_few_were_left(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    nesting = await kind(session, world, "Cliff Nester", region, 10, sociality=Sociality.COLONY)
    ctx = await manual_context(session, "ecology")
    await keep_living_ways(ctx, set())
    assert (await range_of(session, nesting, region)).abundance == 0
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "ecology.colony_collapsed")) is not None


async def test_a_waste_eater_settles_beside_a_town_and_a_kept_kind_without_keepers_runs_feral(session: AsyncSession, world: CoreWorld) -> None:
    town_land, empty_land = world.regions[0], world.regions[1]
    await settlement(session, "Midden Town", world, town_land)
    scavenger = await kind(session, world, "Midden Picker", town_land, 50, diet=Diet.SCAVENGER)
    herd = await kind(session, world, "Lost Herd", empty_land, 50, stage=DomesticationStage.DOMESTICATED)
    ground = await session.get(RegionEnvironmentRow, empty_land.id)
    ctx = await manual_context(session, "ecology", tuned_rules(domestication_depth={"commensal_chance_pct": 100, "feral_chance_pct": 100}))
    tally = await keep_living_ways(ctx, set())
    first = await session.get(SpeciesProfileRow, scavenger.id)
    second = await session.get(SpeciesProfileRow, herd.id)
    assert first is not None and first.stage is DomesticationStage.COMMENSAL
    assert second is not None and second.stage is DomesticationStage.FERAL
    assert tally.commensal == 1 and tally.feral == 1
    assert ground is None or ground.scars.get("overgrazed", 0) > 0


def test_a_kind_living_beside_people_or_gone_feral_is_tamed_faster() -> None:
    rules = Rules()
    assert taming_ease(rules, DomesticationStage.WILD) == 1.0
    assert taming_ease(rules, DomesticationStage.COMMENSAL) > 1.0
    assert taming_ease(rules, DomesticationStage.FERAL) > taming_ease(rules, DomesticationStage.WILD)
