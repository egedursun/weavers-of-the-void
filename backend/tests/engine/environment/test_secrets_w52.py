from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.disease import DiseaseProfileRow, EndemicDiseaseRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.place import PlaceProfileRow, PlaceSecretRow
from aerona.db.tables.region import RegionMemoryRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.disease import ClimateMoisture
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import WaterSource
from aerona.domain.enums.place import DiscoveryMode, PlaceKind, SecretKind, SecretOrigin
from aerona.domain.enums.region import RegionMemoryKind
from aerona.domain.models.entity_stats import DiseaseStats, PlaceStats
from aerona.engine.context import TickContext
from aerona.engine.environment.places import apply_kind
from aerona.engine.environment.secrets import find_chance, reveal, subject_for
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, seed_core_world, surveyed

RULES = Rules()


async def secret_at(session: AsyncSession, world: CoreWorld, ctx: TickContext, kind: SecretKind, place_kind: PlaceKind) -> PlaceSecretRow:
    place = await entity(session, f"Hidden {kind.value}", EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(PlaceProfileRow(entity_id=place.id, kind=place_kind, locked=[]))
    ground = PlaceEnvironmentRow(entity_id=place.id, region_entity_id=world.regions[0].id, soil_fertility=50, derived_fertility=50, locked=[])
    apply_kind(RULES, ground, place_kind)
    session.add(ground)
    secret = PlaceSecretRow(place_entity_id=place.id, kind=kind, strength=40, origin=SecretOrigin.LAND, created_epoch=0)
    session.add(secret)
    await session.flush()
    secret.subject_entity_id = await subject_for(ctx, kind, world.regions[0].id)
    await session.flush()
    return secret


async def found(session: AsyncSession) -> set[str]:
    return set(await session.scalars(select(IncidentRow.kind)))


def test_routes_and_graves_are_easier_to_find_than_their_strength_alone_says() -> None:
    plain = find_chance(RULES, skill=50, mystery=50, strength=40, called=False)
    assert find_chance(RULES, skill=50, mystery=50, strength=40, called=False, kind=SecretKind.HIDDEN_ROUTE) == plain + RULES.secrets.hidden_route_find_pct
    assert find_chance(RULES, skill=50, mystery=50, strength=40, called=False, kind=SecretKind.HIDDEN_GRAVE) == plain + RULES.secrets.hidden_grave_find_pct


async def test_a_sleeping_beast_wakes_hungry_in_its_lair(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    ctx = await manual_context(session, "test", RULES)
    session.add(SpeciesRangeRow(species_entity_id=world.species.id, region_entity_id=world.regions[0].id, abundance=60, locked=[]))
    await session.flush()
    secret = await secret_at(session, world, ctx, SecretKind.SLEEPING_BEAST, PlaceKind.CAVE)
    assert secret.subject_entity_id == world.species.id
    beast = await reveal(ctx, secret, DiscoveryMode.EXPLORER, None, None)
    assert beast is not None and beast.entity_type is EntityType.BEAST
    profile = await session.get(BeastProfileRow, beast.id)
    assert profile is not None and profile.lair_place_id == secret.place_entity_id and profile.temper is BeastTemper.HUNGRY
    assert "beast.woken" in await found(session)


async def test_a_hidden_spring_waters_its_land(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    ctx = await manual_context(session, "test", RULES)
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert land is not None
    land.harvest_pct = 100
    secret = await secret_at(session, world, ctx, SecretKind.HIDDEN_SPRING, PlaceKind.MEADOW)
    dry = await session.get(PlaceEnvironmentRow, secret.place_entity_id)
    assert dry is not None
    dry.water_source = WaterSource.NONE
    await reveal(ctx, secret, DiscoveryMode.EXPLORER, None, land)
    ground = await session.get(PlaceEnvironmentRow, secret.place_entity_id)
    assert ground is not None and ground.water_source is WaterSource.SPRING
    assert land.harvest_pct == 100 + RULES.secrets.hidden_spring_harvest


async def test_a_dormant_disease_settles_into_its_land(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    ctx = await manual_context(session, "test", RULES)
    disease = await entity(session, "Slow Fever", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    session.add(
        DiseaseProfileRow(
            disease_entity_id=disease.id,
            primary_route=Transmission.CONTACT,
            virulence=50,
            lethality=20,
            chronic_rate=10,
            incubation=1,
            affinity_moisture=ClimateMoisture.WET,
            immunity_epochs=2,
            mutation_rate=1,
            stigma=10,
            cure_level=9,
            locked=[],
        )
    )
    await session.flush()
    secret = await secret_at(session, world, ctx, SecretKind.DORMANT_DISEASE, PlaceKind.CAVE)
    woken = await reveal(ctx, secret, DiscoveryMode.EXPLORER, None, None)
    assert isinstance(woken, EntityRow) and woken.id == disease.id
    endemic = await session.get(EndemicDiseaseRow, (world.regions[0].id, disease.id))
    assert endemic is not None and endemic.load == RULES.secrets.dormant_disease_load


async def test_a_false_account_found_out_weakens_the_land_memory_it_told(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    ctx = await manual_context(session, "test", RULES)
    told = RegionMemoryRow(world_id=world.world.id, region_entity_id=world.regions[0].id, kind=RegionMemoryKind.FOUNDING, magnitude=80, epoch=0, source_key="t")
    session.add(told)
    await session.flush()
    secret = await secret_at(session, world, ctx, SecretKind.FALSE_ACCOUNT, PlaceKind.ISTHMUS)
    await reveal(ctx, secret, DiscoveryMode.EXPLORER, None, None)
    assert told.magnitude == 80 - 80 * RULES.secrets.false_account_cut_pct // 100
    assert secret.revealed_epoch is not None
