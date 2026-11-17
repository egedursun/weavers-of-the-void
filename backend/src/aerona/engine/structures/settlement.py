from collections import defaultdict

from aerona.constants.units import PER_MILLE, PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.domain.enums.economy import MaterialFamily
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.integrity import HarmForce
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import BuildMaterial, WaterSupply
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record
from aerona.engine.structures.damage import harm
from aerona.engine.structures.profiles import material_props, profiles_at
from aerona.engine.structures.readers import Working, working

K = StructureKind
WALL_MAX = 5
ROAD_MAX = 5
COUNT_MAX = 20
STONE_FAMILIES = frozenset({MaterialFamily.STONE, MaterialFamily.METAL, MaterialFamily.EXOTIC})


def free(locked: list[str], key: str) -> bool:
    return key not in locked


def strength(items: list[Working]) -> float:
    return sum(item.strength for item in items)


def capacity(items: list[Working]) -> int:
    return round_half_up(sum(item.profile.capacity * item.strength for item in items))


async def walls(ctx: TickContext, infrastructure: SettlementInfrastructureRow, items: list[Working]) -> None:
    if not items:
        return
    best = max(items, key=lambda item: (item.profile.level, item.profile.effect_pct, -item.structure.id))
    locked = infrastructure.locked
    if free(locked, "walls_level") and best.profile.level >= infrastructure.walls_level:
        infrastructure.walls_level = min(WALL_MAX, best.profile.level)
        props = await material_props(ctx.session, best.structure)
        if free(locked, "walls_material"):
            infrastructure.walls_material = BuildMaterial.STONE if props is not None and props.family in STONE_FAMILIES else BuildMaterial.TIMBER
        if free(locked, "walls_condition"):
            infrastructure.walls_condition = clamp_int(best.profile.condition, 0, PERCENT)


def infrastructure_from(infrastructure: SettlementInfrastructureRow, kinds: dict[StructureKind, list[Working]], road_pct: int) -> None:
    locked = infrastructure.locked
    if free(locked, "gates"):
        infrastructure.gates = min(COUNT_MAX, max(infrastructure.gates, len(kinds[K.GATE]) + (1 if kinds[K.WALL] else 0)))
    if free(locked, "towers"):
        infrastructure.towers = min(COUNT_MAX, max(infrastructure.towers, len(kinds[K.TOWER]) + len(kinds[K.WATCHTOWER])))
    if free(locked, "roads") and kinds[K.ROAD]:
        built = max(round_half_up(item.profile.level * item.strength * road_pct / PERCENT) for item in kinds[K.ROAD])
        infrastructure.roads = min(ROAD_MAX, max(infrastructure.roads, built))
    if free(locked, "water") and kinds[K.AQUEDUCT]:
        infrastructure.water = WaterSupply.AQUEDUCT
    if free(locked, "sewers") and kinds[K.SEWER]:
        infrastructure.sewers = True
    if free(locked, "granary_capacity"):
        infrastructure.granary_capacity += capacity(kinds[K.GRANARY])
    if free(locked, "warehouse_capacity"):
        infrastructure.warehouse_capacity += capacity(kinds[K.WAREHOUSE])
    if free(locked, "harbour_capacity"):
        infrastructure.harbour_capacity += capacity(kinds[K.HARBOUR])


def shift(profile: SettlementProfileRow, key: str, delta: float) -> None:
    if free(profile.locked, key) and delta:
        setattr(profile, key, clamp_int(getattr(profile, key) + delta, 0, PERCENT))


def civic_from(ctx: TickContext, entity: EntityRow, profile: SettlementProfileRow, kinds: dict[StructureKind, list[Working]]) -> None:
    table = ctx.rules.structure_functions
    shift(profile, "sanitation", strength(kinds[K.AQUEDUCT]) * table.aqueduct_sanitation + strength(kinds[K.SEWER]) * table.sewer_sanitation)
    shift(
        profile,
        "public_order",
        strength(kinds[K.COURT]) * table.court_order
        + strength(kinds[K.PRISON]) * table.prison_order
        + strength(kinds[K.CITADEL]) * table.citadel_order
        + strength(kinds[K.TOWN_HALL]) * table.town_hall_order,
    )
    people = max(1, stat(entity, "population") or 0)
    cells = sum(item.profile.capacity * item.strength for item in kinds[K.PRISON])
    fullness = min(1.0, cells * PER_MILLE / people / table.prison_cells_per_1000) if kinds[K.PRISON] else 0.0
    shift(
        profile,
        "crime",
        -(strength(kinds[K.COURT]) * table.court_crime_cut + fullness * table.prison_crime_cut + strength(kinds[K.WATCHTOWER]) * table.watchtower_crime_cut),
    )
    shift(
        profile,
        "unrest",
        -(
            strength(kinds[K.ARENA]) * table.arena_unrest_cut
            + strength(kinds[K.THEATRE]) * table.theatre_unrest_cut
            + strength(kinds[K.TAVERN]) * table.tavern_unrest_cut
            + strength(kinds[K.ORPHANAGE]) * table.orphanage_unrest_cut
            + strength(kinds[K.PLAZA]) * table.plaza_unrest_cut
            + strength(kinds[K.TRAINING_GROUND]) * table.training_unrest_cut
        ),
    )
    shift(
        profile,
        "prestige",
        strength(kinds[K.MONUMENT]) * table.monument_prestige
        + strength(kinds[K.TOMB]) * table.tomb_prestige
        + strength(kinds[K.THEATRE]) * table.theatre_prestige
        + strength(kinds[K.WONDER]) * table.wonder_prestige
        + strength(kinds[K.MUSEUM]) * table.museum_prestige,
    )
    garrison = sum(item.profile.capacity * item.strength for item in kinds[K.FORT] + kinds[K.CITADEL] + kinds[K.BARRACKS])
    drilled = sum(item.profile.level * item.strength for item in kinds[K.TRAINING_GROUND]) * table.training_militia
    if free(profile.locked, "militia"):
        profile.militia += round_half_up(garrison * table.garrison_militia_pct / PERCENT + drilled)
    if free(profile.locked, "investment_pool"):
        profile.investment_pool += round_half_up(
            sum(item.profile.level * item.strength for item in kinds[K.BANK]) * table.bank_investment
            + sum(item.profile.level * item.strength for item in kinds[K.GUILDHALL]) * table.guildhall_investment
            + sum(item.profile.level * item.strength for item in kinds[K.MINT]) * table.mint_investment
        )
    if free(profile.locked, "siege_supplies"):
        profile.siege_supplies += round_half_up(sum(item.profile.level * item.strength for item in kinds[K.GRANARY]) * table.granary_siege_days)


async def burn(ctx: TickContext, entity: EntityRow, fires: int) -> int:
    if fires <= 0:
        return 0
    burned = 0
    for profile in await profiles_at(ctx.session, entity.id):
        work = await ctx.session.get(EntityRow, profile.structure_entity_id)
        if work is None or work.status is not EntityStatus.CANON:
            continue
        loss = fires * ctx.rules.upkeep.fire_damage * (PERCENT - profile.fire_resistance) / PERCENT
        if loss <= 0:
            continue
        burned += 1
        await harm(ctx, work, profile, loss, cause="fire", force=HarmForce.FIRE, quiet=True)
    if burned:
        await record(ctx, "structures.burned", roles={IncidentRole.SUBJECT: entity.id}, facts={"fires": fires, "burned": burned}, place=entity.id)
    return burned


async def serve_town(ctx: TickContext, entity: EntityRow, profile: SettlementProfileRow, infrastructure: SettlementInfrastructureRow, *, fires: int = 0) -> int:
    if entity.entity_type is not EntityType.SETTLEMENT:
        return 0
    await burn(ctx, entity, fires)
    found = await working(ctx.session, list(StructureKind), host_id=entity.id)
    kinds: dict[StructureKind, list[Working]] = defaultdict(list)
    for item in found:
        kinds[item.profile.kind].append(item)
    await walls(ctx, infrastructure, kinds[K.WALL])
    infrastructure_from(infrastructure, kinds, ctx.rules.structure_functions.road_level_pct)
    civic_from(ctx, entity, profile, kinds)
    return len(found)
