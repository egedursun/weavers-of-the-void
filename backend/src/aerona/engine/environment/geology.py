from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import WORLD_TYPE_TRAITS, having
from aerona.catalog.nature_kinds50 import SEDIMENTS
from aerona.catalog.rocks import ROCKS, WORLD_CRUSTS
from aerona.catalog.terrain import terrain_has
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import RegionGeologyRow, RegionStratumRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.tables.water import SedimentFlowRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, SoilKind, TerrainKind, TerrainTrait
from aerona.domain.enums.geology import RockKind, UndergroundStratum
from aerona.domain.enums.life_traits import WorldTypeTrait
from aerona.domain.enums.world import WorldType
from aerona.engine.context import TickContext
from aerona.engine.environment.columns import POROUS
from aerona.rules.registry import Rules

R = RockKind
U = UndergroundStratum
SOLUBLE = 50
SEDIMENT_THICKNESS = 5
MOLTEN_WORLDS = having(WORLD_TYPE_TRAITS, WorldTypeTrait.VOLCANIC_WORLDS)
CRYSTAL_WORLDS = frozenset({WorldType.CRYSTAL})


@dataclass(frozen=True)
class Layer:
    rock: RockKind
    thickness: int


@dataclass(frozen=True)
class Underlay:
    stratum: UndergroundStratum
    volume: int = 0
    pressure: int = 0


def sediments(ground: RegionEnvironmentRow) -> list[Layer]:
    terrain = ground.dominant_terrain
    found: list[Layer] = []
    if terrain_has(terrain, TerrainTrait.ARID):
        found += [Layer(R.HALITE, 8 if terrain is TerrainKind.EVAPORITE_FLAT else 4), Layer(R.SAND, 10)]
    if terrain_has(terrain, TerrainTrait.WET) or ground.soil in (SoilKind.PEAT, SoilKind.GLEY):
        found.append(Layer(R.CLAY, 8))
    if ground.base_forest >= POROUS or ground.base_wetland >= POROUS:
        found.append(Layer(R.COAL, 6))
    if ground.coast_kind is not CoastKind.NONE or ground.soil is SoilKind.CALCAREOUS:
        found.append(Layer(R.CHALK, 10))
    found += [Layer(R.SANDSTONE, 12), Layer(R.SHALE, 10), Layer(R.LIMESTONE, 30 if terrain is TerrainKind.KARST else 12)]
    return found


def hard_rock(ground: RegionEnvironmentRow, physics: WorldPhysicsRow | None, world_type: WorldType) -> list[Layer]:
    found: list[Layer] = []
    volcanism = physics.volcanism if physics is not None else 0
    tectonics = physics.tectonics if physics is not None else 0
    if ground.dominant_terrain is TerrainKind.VOLCANIC or volcanism >= PERCENT // 2 or world_type in MOLTEN_WORLDS:
        found += [Layer(R.TUFF, 10), Layer(R.BASALT, 20), Layer(R.OBSIDIAN, 5)]
    if terrain_has(ground.dominant_terrain, TerrainTrait.ROUGH) or terrain_has(ground.dominant_terrain, TerrainTrait.HIGH):
        found.append(Layer(R.SLATE, 10))
        if tectonics >= PERCENT // 2:
            found += [Layer(R.MARBLE, 10), Layer(R.QUARTZITE, 10), Layer(R.GNEISS, 15)]
    found.append(Layer(R.CRYSTAL_BEDROCK if world_type in CRYSTAL_WORLDS else R.GRANITE, 25))
    return found


def column_for(ground: RegionEnvironmentRow, physics: WorldPhysicsRow | None, world_type: WorldType, rng: SeededRandom) -> list[Layer]:
    crust = WORLD_CRUSTS.get(world_type)
    top = [Layer(R.SOIL, 3 + rng.below(4))] if crust is not R.LIVING_TISSUE else []
    shell = [Layer(crust, 40)] if crust is not None else []
    return [*top, *shell, *sediments(ground), *hard_rock(ground, physics, world_type)]


def veins_for(rules: Rules, column: list[Layer], minerals: dict[str, int]) -> list[dict[str, int]]:
    laid: list[dict[str, int]] = [{} for _ in column]
    for material, richness in sorted(minerals.items()):
        index = next((i for i, layer in enumerate(column) if any(vein.value == material for vein in ROCKS[layer.rock].veins)), None)
        if index is not None:
            laid[index][material] = richness or rules.rocks.vein_richness
    return laid


def strata_for(rules: Rules, column: list[Layer], physics: WorldPhysicsRow | None, world_type: WorldType, *, underworld: bool, rough: bool) -> list[Underlay]:
    table = rules.underground
    rocks = [layer.rock for layer in column]
    found: list[Underlay] = []
    hydro = physics.hydrosphere if physics is not None else 0
    if hydro > 0 and any(ROCKS[rock].porosity(rules) >= POROUS for rock in rocks):
        found.append(Underlay(U.AQUIFER))
    beds = sum(1 for index, rock in enumerate(rocks) if ROCKS[rock].organic and any(ROCKS[above].seals for above in rocks[:index]))
    if beds:
        found.append(Underlay(U.RESERVOIR, min(1000, beds * table.reservoir_volume_per_bed), table.reservoir_pressure))
    volcanism = physics.volcanism if physics is not None else 0
    if R.WATER_ICE in rocks and volcanism >= table.under_ocean_heat_min:
        found.append(Underlay(U.UNDER_OCEAN))
    if any(ROCKS[rock].solubility(rules) >= SOLUBLE for rock in rocks):
        found.append(Underlay(U.CAVERN_UPPER))
        if rough:
            found.append(Underlay(U.CAVERN_MIDDLE))
            if physics is not None and physics.tectonics >= PERCENT * 3 // 5:
                found.append(Underlay(U.CAVERN_DEEP))
    if volcanism >= PERCENT // 2 or world_type in MOLTEN_WORLDS:
        found.append(Underlay(U.MAGMA_SEA))
    if world_type is WorldType.HOLLOW:
        found.append(Underlay(U.HOLLOW_INTERIOR))
    if underworld:
        found.append(Underlay(U.DEEP_UNDERWORLD))
    return found


async def shafts_of(session: AsyncSession, world_id: int) -> int:
    shafts = (
        select(func.count())
        .select_from(RegionStratumRow)
        .join(RegionEnvironmentRow, RegionEnvironmentRow.entity_id == RegionStratumRow.region_entity_id)
        .where(RegionEnvironmentRow.world_id == world_id, RegionStratumRow.stratum == U.HOLLOW_INTERIOR)
    )
    return await session.scalar(shafts) or 0


async def lay_region(session: AsyncSession, rules: Rules, ground: RegionEnvironmentRow, world: WorldRow | None, rng: SeededRandom) -> int:
    physics = await session.get(WorldPhysicsRow, ground.world_id)
    world_type = world.world_type if world is not None else WorldType.ORDINARY
    laid_down = await session.scalars(select(SedimentFlowRow.kind).where(SedimentFlowRow.sink_region_id == ground.entity_id).distinct())
    column = column_for(ground, physics, world_type, rng)
    sediment_rocks = [Layer(SEDIMENTS[kind].rock, SEDIMENT_THICKNESS) for kind in sorted(laid_down)]
    column = [*column[:1], *sediment_rocks, *column[1:]]
    veins = veins_for(rules, column, ground.mineral_layers or {})
    for order, (layer, vein) in enumerate(zip(column, veins, strict=True)):
        session.add(
            RegionGeologyRow(
                region_entity_id=ground.entity_id, depth_order=order, rock=layer.rock, thickness=max(1, min(PERCENT, layer.thickness)), veins=vein, locked=[]
            )
        )
    underworld = await session.scalar(
        select(EntityRow.id).where(EntityRow.world_id == ground.world_id, EntityRow.is_underworld.is_(True), EntityRow.status == EntityStatus.CANON).limit(1)
    )
    rough = terrain_has(ground.dominant_terrain, TerrainTrait.ROUGH)
    for under in strata_for(rules, column, physics, world_type, underworld=underworld is not None, rough=rough):
        if under.stratum is U.HOLLOW_INTERIOR and await shafts_of(session, ground.world_id) >= rules.underground.hollow_shaft_count:
            continue
        session.add(RegionStratumRow(region_entity_id=ground.entity_id, stratum=under.stratum, volume=under.volume, pressure=under.pressure, locked=[]))
    return len(column)


async def lay_columns(ctx: TickContext) -> int:
    session = ctx.session
    laid = set(await session.scalars(select(RegionGeologyRow.region_entity_id).distinct()))
    worlds = {row.id: row for row in await session.scalars(select(WorldRow))}
    regions = set(await session.scalars(select(EntityRow.id).where(EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)))
    made = 0
    for ground in list(await session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id))):
        if ground.entity_id in laid or ground.entity_id not in regions or held(ground.entity_id) or ground.dominant_terrain is TerrainKind.CLOUD_DECK:
            continue
        await lay_region(session, ctx.rules, ground, worlds.get(ground.world_id), ctx.environment.rng(f"geology.{ground.entity_id}"))
        made += 1
    await session.flush()
    return made
