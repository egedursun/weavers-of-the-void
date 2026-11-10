from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import partial
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.physics import WorldLifeRow, WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.ecology import Biochemistry
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.physics import AirNeed, LifeComplexity, LifeEnvironment
from aerona.domain.enums.world import WorldType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.orbits import GAS_WORLDS, LIFELESS_WORLDS
from aerona.engine.ecology.biochemistry import bearable, tolerated
from aerona.engine.notes import note
from aerona.rules.registry import Rules

COMPLEXITY_ORDER: tuple[LifeComplexity, ...] = tuple(LifeComplexity)
BARREN_WORLDS = frozenset({*LIFELESS_WORLDS, WorldType.VOID_POCKET, WorldType.ASTEROID_BELT, WorldType.SHATTERED})
HARSH_WORLDS = frozenset({WorldType.LAVA, WorldType.FORGE, WorldType.ICE, WorldType.ICE_SHELL, WorldType.METHANE, WorldType.GREENHOUSE, WorldType.DWARF_PLANET})
BURIED_WORLDS = frozenset({WorldType.ICE_SHELL, WorldType.HOLLOW, WorldType.CHTHONIAN, WorldType.FUNGAL})
AIR_GAS = partial(AirNeed, {AirNeed.OXYGEN: "oxygen", AirNeed.CARBON_DIOXIDE: "carbon_dioxide", AirNeed.METHANE: "methane"}, without={AirNeed.NONE})
GRAVITY_SPAN = (0.5, 1.6)
HOMELAND_FIXUP = "homeland_body"


def rank(complexity: LifeComplexity) -> int:
    return COMPLEXITY_ORDER.index(complexity)


def environments_of(world: WorldRow, physics: WorldPhysicsRow | None) -> list[str]:
    found: list[LifeEnvironment] = []
    sea = physics.hydrosphere if physics is not None else round(world.terrain_sea * PERCENT)
    if sea > 0 and world.world_type not in GAS_WORLDS:
        found.append(LifeEnvironment.MARINE)
    if sea < PERCENT and world.world_type not in GAS_WORLDS:
        found.append(LifeEnvironment.TERRESTRIAL)
    if world.world_type in GAS_WORLDS or (physics is not None and physics.pressure > 0):
        found.append(LifeEnvironment.AERIAL)
    if world.world_type in BURIED_WORLDS:
        found.append(LifeEnvironment.SUBTERRANEAN)
    return [item.value for item in found]


async def living_kinds(session: AsyncSession, world_id: int, kind: EntityType) -> int:
    statement = (
        select(func.count()).select_from(EntityRow).where(EntityRow.world_id == world_id, EntityRow.entity_type == kind, EntityRow.status == EntityStatus.CANON)
    )
    return int(await session.scalar(statement) or 0)


async def inferred_life(session: AsyncSession, world: WorldRow, physics: WorldPhysicsRow | None) -> WorldLifeRow:
    if await living_kinds(session, world.id, EntityType.PEOPLE):
        complexity = LifeComplexity.SAPIENT
    elif await living_kinds(session, world.id, EntityType.SPECIES):
        complexity = LifeComplexity.COMPLEX
    elif world.world_type in BARREN_WORLDS:
        complexity = LifeComplexity.NONE
    elif world.world_type in HARSH_WORLDS:
        complexity = LifeComplexity.MICROBIAL
    elif physics is None or physics.habitable:
        complexity = LifeComplexity.COMPLEX
    else:
        complexity = LifeComplexity.SIMPLE
    return WorldLifeRow(world_id=world.id, complexity=complexity, environments=environments_of(world, physics), locked=[])


async def life_of(session: AsyncSession, world: WorldRow) -> WorldLifeRow:
    row = await session.get(WorldLifeRow, world.id)
    if row is None:
        row = await inferred_life(session, world, await session.get(WorldPhysicsRow, world.id))
        session.add(row)
        await session.flush()
    return row


async def may_arise(session: AsyncSession, rules: Rules, world: WorldRow, *, people: bool) -> bool:
    life = await life_of(session, world)
    needed = rules.life_classes.people_complexity if people else rules.life_classes.species_complexity
    return rank(life.complexity) >= needed


def breathes(rules: Rules, biology: PeopleBiologyRow, physics: WorldPhysicsRow) -> bool:
    gas = AIR_GAS.get(biology.air)
    if gas is None:
        return True
    return physics.pressure >= rules.orbits.no_air_hundredths / PERCENT and getattr(physics, gas) >= rules.life_classes.breathable_oxygen


def bears_gravity(biology: PeopleBiologyRow, physics: WorldPhysicsRow) -> bool:
    return biology.gravity_low <= physics.gravity_g <= biology.gravity_high


def world_fit(rules: Rules, biology: PeopleBiologyRow | None, physics: WorldPhysicsRow | None, allowed: tuple[Biochemistry, ...]) -> int:
    if biology is None or physics is None:
        return PERCENT
    table = rules.life_classes
    fit = float(PERCENT)
    if allowed and not bearable(biology.biochemistry, allowed):
        fit *= table.mismatch_pct / PERCENT
    if not breathes(rules, biology, physics):
        fit *= table.air_pct / PERCENT
    if not bears_gravity(biology, physics):
        fit *= table.gravity_pct / PERCENT
    return round(fit)


async def habitability(session: AsyncSession, rules: Rules, biology: PeopleBiologyRow | None, world_id: int | None) -> int:
    if biology is None or world_id is None:
        return PERCENT
    physics = await session.get(WorldPhysicsRow, world_id)
    return world_fit(rules, biology, physics, await tolerated(session, world_id))


def habitable_growth(rules: Rules, fit: int) -> float:
    return max(0.0, 1 - (PERCENT - fit) / PERCENT * rules.life_classes.growth_pct / PERCENT)


def disease_load(rules: Rules, fit: int) -> float:
    return (PERCENT - fit) / 10 * rules.life_classes.disease_per_point / PERCENT


async def raise_life(session: AsyncSession, world: WorldRow, complexity: LifeComplexity) -> bool:
    life = await life_of(session, world)
    if "complexity" in life.locked or rank(life.complexity) >= rank(complexity):
        return False
    life.complexity = complexity
    return True


async def quicken(ctx: TickContext, worlds: dict[int, WorldRow], physics: dict[int, WorldPhysicsRow]) -> int:
    table = ctx.rules.life_classes
    grown = 0
    for world_id, row in sorted(physics.items()):
        world = worlds.get(world_id)
        if world is None or held(world_id) or not row.habitable or world.biosphere_health < table.rise_health or world.world_type in BARREN_WORLDS:
            continue
        life = await life_of(ctx.session, world)
        if "complexity" in life.locked or rank(life.complexity) >= rank(LifeComplexity.COMPLEX):
            continue
        if ctx.rng(f"life_rise.{world_id}.{ctx.epoch}").chance(table.rise_chance):
            life.complexity = COMPLEXITY_ORDER[rank(life.complexity) + 1]
            await note(ctx, f"The life of {world.name} grew more complex.", key="world.life_grew", world_id=world_id, kind=ChronicleKind.WORLD)
            grown += 1
    return grown


def breath_of_world(rules: Rules, physics: WorldPhysicsRow) -> AirNeed:
    if physics.pressure < rules.orbits.no_air_hundredths / PERCENT:
        return AirNeed.NONE
    shares = {need: getattr(physics, gas) for need, gas in AIR_GAS.items() if getattr(physics, gas) >= rules.life_classes.breathable_oxygen}
    return max(sorted(shares), key=lambda need: shares[need]) if shares else AirNeed.NONE


async def fit_to_homeland(session: AsyncSession, rules: Rules, biology: PeopleBiologyRow, world_id: int | None) -> bool:
    physics = await session.get(WorldPhysicsRow, world_id) if world_id is not None else None
    if physics is None:
        return False
    allowed = await tolerated(session, physics.world_id)
    chemistry = Biochemistry.CARBON_WATER if not allowed or Biochemistry.CARBON_WATER in allowed else allowed[0]
    low, high = GRAVITY_SPAN
    for key, value in (
        ("biochemistry", chemistry),
        ("air", breath_of_world(rules, physics)),
        ("gravity_low", round(physics.gravity_g * low, 2)),
        ("gravity_high", round(physics.gravity_g * high, 2)),
    ):
        if key not in biology.locked:
            setattr(biology, key, value)
    return True


async def fit_peoples(session: AsyncSession, rules: Rules) -> int:
    done = set(await session.scalars(select(AppliedFixupRow.key).where(AppliedFixupRow.key.like(f"{HOMELAND_FIXUP}.%"))))
    fitted = 0
    for biology in list(await session.scalars(select(PeopleBiologyRow).order_by(PeopleBiologyRow.people_entity_id))):
        key = f"{HOMELAND_FIXUP}.{biology.people_entity_id}"
        people = await session.get(EntityRow, biology.people_entity_id)
        if key in done or people is None or held(people.id):
            continue
        if await fit_to_homeland(session, rules, biology, people.world_id):
            session.add(AppliedFixupRow(key=key, result={"world_id": people.world_id}))
            fitted += 1
    await session.flush()
    return fitted
