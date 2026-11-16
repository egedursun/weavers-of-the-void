from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import (
    CentralPlaceRow,
    FamineLoreRow,
    GameReserveRow,
    IntensificationRow,
    KeystoneResourceRow,
    LandRingRow,
    PerennialRow,
    PreparednessRow,
    SoilNutrientRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import LandUseRing, NutrientKind, PreparednessKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import top_region
from aerona.rules.registry import Rules

P = PreparednessKind
BODY = (NutrientKind.FIXED, NutrientKind.MINERAL, NutrientKind.ORGANIC)
SHIELDS: dict[Disaster, frozenset[PreparednessKind]] = {
    Disaster.FLOOD: frozenset({P.LEVEE, P.SEAWALL, P.EVACUATION_ROUTES, P.WARNING_NETWORK}),
    Disaster.STORM: frozenset({P.SEAWALL, P.SHELTERS, P.WARNING_NETWORK}),
    Disaster.EARTHQUAKE: frozenset({P.DRILL, P.SHELTERS, P.EVACUATION_ROUTES}),
    Disaster.VOLCANIC_QUAKE: frozenset({P.DRILL, P.SHELTERS, P.EVACUATION_ROUTES}),
    Disaster.ERUPTION: frozenset({P.DRILL, P.EVACUATION_ROUTES, P.WARNING_NETWORK}),
    Disaster.DROUGHT: frozenset({P.STOCKPILE, P.RESERVES_OF_ENERGY}),
    Disaster.PLAGUE: frozenset({P.QUARANTINE_PLAN}),
}
FIRE_SHIELDS = frozenset({P.FIREBREAK, P.EVACUATION_ROUTES, P.WARD})
SHIELDS = {disaster: kinds | {P.WARD} for disaster, kinds in SHIELDS.items()}


def ring_shares(rules: Rules, ring: LandUseRing) -> tuple[int, int]:
    table = rules.thunen
    return {
        LandUseRing.GARDENS: (table.gardens_farm_pct, table.gardens_graze_pct),
        LandUseRing.FORESTRY: (table.forestry_farm_pct, table.forestry_graze_pct),
        LandUseRing.GRAIN: (table.grain_farm_pct, table.grain_graze_pct),
        LandUseRing.RANCHING: (table.ranching_farm_pct, table.ranching_graze_pct),
        LandUseRing.WILDS: (PERCENT, PERCENT),
    }[ring]


async def rings_of(session: AsyncSession) -> dict[int, LandRingRow]:
    return {row.region_entity_id: row for row in await session.scalars(select(LandRingRow))}


async def gap_of(session: AsyncSession, region_id: int) -> int:
    row = await session.get(LandRingRow, region_id)
    return row.gap if row is not None else 0


async def centrality_of(session: AsyncSession, settlement_id: int) -> int:
    row = await session.get(CentralPlaceRow, settlement_id)
    return row.centrality if row is not None else 0


def counted_people(rules: Rules, people: int, centrality: int) -> int:
    return round_half_up(people * (1 + centrality / PERCENT * rules.central_places.tier_pct / PERCENT))


def readout(rules: Rules, stocks: dict[NutrientKind, int]) -> int:
    body = sum(stocks.get(kind, 0) for kind in BODY) / len(BODY)
    salt = stocks.get(NutrientKind.SALINITY, 0) * rules.nutrients.salinity_weight / PERCENT
    return clamp_int(body * max(0.0, PERCENT - salt) / PERCENT, 0, PERCENT)


async def nutrient_stocks(session: AsyncSession) -> dict[int, dict[NutrientKind, int]]:
    found: dict[int, dict[NutrientKind, int]] = defaultdict(dict)
    for row in await session.scalars(select(SoilNutrientRow)):
        found[row.region_entity_id][row.nutrient] = row.stock
    return found


def nutrient_shift(rules: Rules, stocks: dict[NutrientKind, int] | None, soil_base: int) -> int:
    if not stocks or any(kind not in stocks for kind in BODY):
        return 0
    return readout(rules, stocks) - soil_base


async def intensity_of(session: AsyncSession, entity: EntityRow | None) -> IntensificationRow | None:
    if entity is None:
        return None
    region = entity if entity.entity_type is EntityType.REGION else await top_region(session, entity)
    return await session.get(IntensificationRow, region.id) if region is not None else None


async def farming_boost(session: AsyncSession, entity: EntityRow) -> float:
    row = await intensity_of(session, entity)
    return 1 + (row.research_boost if row is not None else 0) / PERCENT


async def method_lift(session: AsyncSession, rules: Rules, entity: EntityRow) -> float:
    row = await intensity_of(session, entity)
    return 1 + (row.research_boost if row is not None else 0) / PERCENT * rules.boserup.method_pct / PERCENT


def harvest_lift(rules: Rules, row: IntensificationRow | None) -> float:
    return 1 + (row.intensity if row is not None else 0) / PERCENT * rules.boserup.harvest_pct / PERCENT


async def intensities(session: AsyncSession) -> dict[int, IntensificationRow]:
    return {row.region_entity_id: row for row in await session.scalars(select(IntensificationRow))}


@dataclass(frozen=True)
class Cushion:
    storage: int
    foods: bool


async def famine_cushions(session: AsyncSession, atlas: RegionAtlas) -> dict[int, Cushion]:
    lore = {row.people_entity_id: row for row in await session.scalars(select(FamineLoreRow))}
    stockpiled: dict[int, int] = defaultdict(int)
    for row in await session.scalars(select(PreparednessRow).where(PreparednessRow.kind == PreparednessKind.STOCKPILE)):
        region = atlas.top_region(row.settlement_entity_id)
        if region is not None:
            stockpiled[region] = max(stockpiled[region], row.level * row.condition // 5)
    storage: dict[int, int] = defaultdict(int)
    foods: set[int] = set()
    if lore:
        towns = await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON))
        for town in towns:
            region = atlas.top_region(town.id)
            people = await people_of(session, town)
            known = lore.get(people.id) if people is not None else None
            if region is None or known is None:
                continue
            storage[region] = max(storage[region], known.storage)
            if known.famine_foods:
                foods.add(region)
    return {region: Cushion(min(PERCENT, storage[region] + stockpiled[region]), region in foods) for region in set(storage) | set(stockpiled) | foods}


def cushioned(rules: Rules, harvest: int, cushion: Cushion | None) -> tuple[int, bool]:
    table = rules.famine_foods
    if cushion is None or harvest >= table.floor:
        return harvest, False
    share = cushion.storage * table.storage_fill / PERCENT + (table.foods_fill if cushion.foods else 0)
    return round_half_up(harvest + (table.floor - harvest) * min(PERCENT, share) / PERCENT), cushion.foods


async def reserve_marks(session: AsyncSession) -> dict[tuple[int, int | None], tuple[int, int]]:
    return {(row.region_entity_id, row.species_entity_id): (row.strictness, row.poaching) for row in await session.scalars(select(GameReserveRow))}


def reserve_factor(rules: Rules, marks: dict[tuple[int, int | None], tuple[int, int]], species_id: int, region_id: int) -> float:
    mark = marks.get((region_id, species_id)) or marks.get((region_id, None))
    if mark is None:
        return 1.0
    strictness, poaching = mark
    protected = strictness / PERCENT * rules.game_laws.protect_pct / PERCENT
    return 1 - protected + protected * poaching / PERCENT


def shield_cut(rules: Rules, rows: list[PreparednessRow], kinds: frozenset[PreparednessKind]) -> float:
    table = rules.resilience
    cut = 0.0
    for row in rows:
        worth = row.level * row.condition / PERCENT
        if row.kind in kinds:
            cut += worth * table.per_level_pct
        elif row.kind is PreparednessKind.WATCHTOWER:
            cut += worth * table.watch_pct
    return min(table.cap_pct, cut) / PERCENT


STRIKES = frozenset({EngineKind.EARTHQUAKE, EngineKind.FLOOD, EngineKind.DROUGHT, EngineKind.STORM, EngineKind.ERUPTION, EngineKind.FIRE, EngineKind.FAMINE})


async def unready(session: AsyncSession, rules: Rules, atlas: RegionAtlas, town_id: int, epoch: int) -> bool:
    if await session.scalar(select(PreparednessRow.kind).where(PreparednessRow.settlement_entity_id == town_id).limit(1)) is not None:
        return False
    region = atlas.top_region(town_id)
    since = epoch - rules.resilience.memory_epochs
    events = await session.scalars(
        select(EntityRow.id).where(EntityRow.entity_type == EntityType.EVENT, EntityRow.engine_kind.in_(list(STRIKES)), EntityRow.birth_epoch >= since)
    )
    return region is not None and any(atlas.top_region(event_id) == region for event_id in events)


async def keystone_source(session: AsyncSession, controller_id: int) -> int | None:
    found: int | None = await session.scalar(
        select(KeystoneResourceRow.source_region_entity_id)
        .where(KeystoneResourceRow.controller_entity_id == controller_id, KeystoneResourceRow.source_region_entity_id.is_not(None))
        .order_by(KeystoneResourceRow.id)
        .limit(1)
    )
    return found


async def gap_site(session: AsyncSession, rules: Rules, atlas: RegionAtlas, home: int) -> int | None:
    rings = {
        row.region_entity_id: row.gap
        for row in await session.scalars(select(LandRingRow).where(LandRingRow.region_entity_id.in_(atlas.neighbour_regions(home))))
    }
    open_lands = [(gap, -region) for region, gap in rings.items() if gap >= rules.central_places.settle_gap and not atlas.is_water(region)]
    return -max(open_lands)[1] if open_lands else None


async def works_of(session: AsyncSession, settlement_id: int) -> list[PreparednessRow]:
    return list(await session.scalars(select(PreparednessRow).where(PreparednessRow.settlement_entity_id == settlement_id).order_by(PreparednessRow.kind)))


async def shield_of(ctx: TickContext, town: EntityRow, disaster: Disaster | None) -> float:
    rows = await works_of(ctx.session, town.id)
    if not rows:
        return 0.0
    kinds = SHIELDS.get(disaster, frozenset()) if disaster is not None else FIRE_SHIELDS
    cut = shield_cut(ctx.rules, rows, kinds)
    if cut * PERCENT >= ctx.rules.resilience.noted_pct:
        helped = [row for row in rows if row.kind in kinds or row.kind is PreparednessKind.WATCHTOWER]
        for row in helped:
            if "averted" not in row.locked and not held(town.id):
                row.averted += 1
        what = " and ".join(sorted({row.kind.value.replace("_", " ") + "s" for row in helped}))
        harm = disaster.value.replace("_", " ") if disaster is not None else "fire"
        await note(ctx, f"The {what} of {town.name} held: the {harm} did not become a catastrophe.", key="resilience.held", ids=[town.id])
    return cut


async def deposit(ctx: TickContext, region_id: int, nutrient: NutrientKind, amount: int) -> None:
    if held(region_id) or amount <= 0:
        return
    row = await ctx.session.get(SoilNutrientRow, (region_id, nutrient))
    if row is not None and "stock" not in row.locked:
        row.stock = clamp_int(row.stock + amount, 0, PERCENT)


async def fell_plantings(ctx: TickContext, region: EntityRow, share_pct: int) -> int:
    if held(region.id) or share_pct <= 0:
        return 0
    felled = 0
    for row in await ctx.session.scalars(select(PerennialRow).where(PerennialRow.region_entity_id == region.id).order_by(PerennialRow.id)):
        if row.maturity <= 0 or "maturity" in row.locked:
            continue
        row.maturity = clamp_int(row.maturity * (PERCENT - share_pct) / PERCENT, 0, PERCENT)
        if "condition" not in row.locked:
            row.condition = clamp_int(row.condition - share_pct, 0, PERCENT)
        row.felled_epoch = ctx.epoch
        felled += 1
    if felled:
        how = "cut down; it will take generations to grow them again" if share_pct * 2 >= PERCENT else "partly cut down"
        await note(ctx, f"The plantings of {region.name} were {how}.", key="perennials.felled", ids=[region.id])
    return felled
