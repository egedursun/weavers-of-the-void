from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.impacts import IMPACT_BODIES
from aerona.catalog.law_exceptions import LAW_EXCEPTIONS
from aerona.catalog.life.cosmos import SOURCED_CAUSES
from aerona.catalog.life_traits import WORLD_TYPE_TRAITS, having
from aerona.catalog.physics_life import LIFE_PLACES, air_fits, first_fitting_air
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mass_weapons import WarRemnantRow
from aerona.db.tables.physics import ImpactEventRow, WorldLifeRow, WorldPhysicsRow
from aerona.db.tables.world_ends import WorldEndRow
from aerona.domain.enums.divine import LawException
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.life_traits import WorldTypeTrait
from aerona.domain.enums.physics import ImpactOutcome, LifeEnvironment
from aerona.engine.cosmos.orbits import GAS_WORLDS, gravity_band
from aerona.rules.registry import Rules

KIND_TYPES = frozenset({EntityType.SPECIES, EntityType.PEOPLE})
BROKEN_WORLDS = having(WORLD_TYPE_TRAITS, WorldTypeTrait.BROKEN_WORLDS)


async def kindless_exemptions(session: AsyncSession) -> list[int]:
    named = [exception for exception, spec in LAW_EXCEPTIONS.items() if spec.names_kind]
    rows = await session.scalars(select(NaturalLawProfileRow).where(NaturalLawProfileRow.exception.in_(named)).order_by(NaturalLawProfileRow.law_entity_id))
    found = []
    for row in rows:
        kind = await session.get(EntityRow, row.exempt_kind_entity_id) if row.exempt_kind_entity_id is not None else None
        if kind is None or kind.entity_type not in KIND_TYPES:
            found.append(row.law_entity_id)
    return found


async def spare_no_one(session: AsyncSession, key: int) -> None:
    row = await session.get(NaturalLawProfileRow, key)
    if row is not None:
        row.exception, row.exempt_kind_entity_id = LawException.NONE, None


async def unfit_breaths(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(PeopleBiologyRow).order_by(PeopleBiologyRow.people_entity_id))
    return [row.people_entity_id for row in rows if not air_fits(row.air, row.biochemistry)]


async def breathe_by_chemistry(session: AsyncSession, key: int) -> None:
    row = await session.get(PeopleBiologyRow, key)
    if row is not None and not air_fits(row.air, row.biochemistry):
        row.air = first_fitting_air(row.biochemistry)


def place_fits(place: str, world: WorldRow) -> bool:
    if place not in set(LifeEnvironment):
        return False
    wanted = LIFE_PLACES[LifeEnvironment(place)].gas_world
    return wanted is None or wanted is (world.world_type in GAS_WORLDS)


async def misplaced_life(session: AsyncSession) -> list[int]:
    found = []
    for row in await session.scalars(select(WorldLifeRow).order_by(WorldLifeRow.world_id)):
        world = await session.get(WorldRow, row.world_id)
        if world is not None and not all(place_fits(place, world) for place in row.environments):
            found.append(row.world_id)
    return found


async def keep_fitting_places(session: AsyncSession, key: int) -> None:
    row = await session.get(WorldLifeRow, key)
    world = await session.get(WorldRow, key)
    if row is not None and world is not None:
        row.environments = [place for place in row.environments if place_fits(place, world)]


async def sourceless_falls(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(ImpactEventRow).where(ImpactEventRow.outcome == ImpactOutcome.PENDING).order_by(ImpactEventRow.id))
    found = []
    for row in rows:
        spec = IMPACT_BODIES[row.body]
        moon = await session.get(WorldRow, row.fragment_world_id) if row.fragment_world_id is not None else None
        wreck = await session.get(WarRemnantRow, row.wreck_remnant_id) if row.wreck_remnant_id is not None else None
        ringless = spec.from_ring and (moon is None or moon.parent_world_id != row.world_id or moon.world_type not in BROKEN_WORLDS)
        hulless = spec.made and (wreck is None or wreck.orbit_world_id != row.world_id)
        if ringless or hulless:
            found.append(row.id)
    return found


async def let_it_pass(session: AsyncSession, key: int) -> None:
    row = await session.get(ImpactEventRow, key)
    if row is not None and row.outcome is ImpactOutcome.PENDING:
        row.outcome = ImpactOutcome.MISSED


async def stray_end_sources(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(WorldEndRow).where(WorldEndRow.source_node_id.is_not(None)).order_by(WorldEndRow.world_id))
    return [row.world_id for row in rows if row.cause not in SOURCED_CAUSES]


async def drop_end_source(session: AsyncSession, key: int) -> None:
    row = await session.get(WorldEndRow, key)
    if row is not None and row.cause not in SOURCED_CAUSES:
        row.source_node_id = None


async def misbanded_worlds(session: AsyncSession) -> list[int]:
    rules = Rules()
    found = []
    for physics in await session.scalars(select(WorldPhysicsRow).order_by(WorldPhysicsRow.world_id)):
        world = await session.get(WorldRow, physics.world_id)
        if world is not None and "gravity" not in world.locked and world.gravity is not gravity_band(rules, physics.gravity_g):
            found.append(world.id)
    return found


async def band_by_mass(session: AsyncSession, key: int) -> None:
    world = await session.get(WorldRow, key)
    physics = await session.get(WorldPhysicsRow, key)
    if world is not None and physics is not None and "gravity" not in world.locked:
        world.gravity = gravity_band(Rules(), physics.gravity_g)
