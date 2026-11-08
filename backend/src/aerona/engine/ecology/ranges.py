from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.ecology import SpeciesHostRow, SpeciesProfileRow, SpeciesRangeRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.ecology import GRAZERS, HUNTERS, SIZE_ORDER, Biochemistry, DomesticationStage, RangeTrend, Sociality
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.ecology.biochemistry import bearable, tolerated
from aerona.engine.ecology.profiles import profile_of
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.faith.book import FaithBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, canon
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

T = CreatureTrait
UNHUNTED = frozenset({T.POISONOUS_FLESH, T.SACRED_ANIMAL})
HOUSED = frozenset({DomesticationStage.DOMESTICATED, DomesticationStage.BREED})


@dataclass
class Wilds:
    atlas: RegionAtlas
    lands: dict[int, RegionEnvironmentRow]
    regions: dict[int, EntityRow]
    population: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    hunters: dict[int, list[EntityRow]] = field(default_factory=lambda: defaultdict(list))
    invasive: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    ranges: dict[int, dict[int, SpeciesRangeRow]] = field(default_factory=lambda: defaultdict(dict))
    profiles: dict[int, SpeciesProfileRow] = field(default_factory=dict)
    traits: dict[int, set[CreatureTrait]] = field(default_factory=dict)
    sick: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))
    sacred: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))
    life: dict[int, tuple[Biochemistry, ...]] = field(default_factory=dict)

    def allowed(self, land: RegionEnvironmentRow | None) -> tuple[Biochemistry, ...] | None:
        return self.life.get(land.world_id) if land is not None and land.world_id is not None else None

    def in_region(self, region_id: int) -> dict[int, SpeciesRangeRow]:
        return {species_id: rows[region_id] for species_id, rows in self.ranges.items() if region_id in rows}


async def load_wilds(ctx: TickContext, species: list[EntityRow], invasive: set[int]) -> Wilds:
    atlas = await RegionAtlas.load(ctx.session)
    lands = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    wilds = Wilds(atlas, lands, {region.id: region for region in await canon(ctx.session, [EntityType.REGION])})
    for community in await canon(ctx.session, SOCIETY_TYPES):
        region = atlas.top_region(community.id)
        if region is not None:
            wilds.population[region] += stat(community, "population") or 0
            wilds.hunters[region].append(community)
    for row in await ctx.session.scalars(select(SpeciesRangeRow)):
        wilds.ranges[row.species_entity_id][row.region_entity_id] = row
    for item in species:
        wilds.profiles[item.id] = await profile_of(ctx, item)
        wilds.traits[item.id] = await traits_of(ctx.session, item.id)
        if item.id in invasive:
            for region in wilds.ranges[item.id]:
                wilds.invasive[region] += 1
    for world_id in sorted({land.world_id for land in lands.values() if land.world_id is not None}):
        wilds.life[world_id] = await tolerated(ctx.session, world_id)
    await sacred_and_sick(ctx, wilds)
    return wilds


async def holy_to_gods(ctx: TickContext, wilds: Wilds) -> None:
    worshipped: dict[int, set[int]] = defaultdict(set)
    for keeper, god in await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    ):
        region = wilds.atlas.top_region(keeper)
        if region is not None:
            worshipped[god].add(region)
    for species_id, profile in wilds.profiles.items():
        if profile.sacred_to_node_id is not None:
            wilds.sacred[species_id] |= worshipped.get(profile.sacred_to_node_id, set())


async def sacred_and_sick(ctx: TickContext, wilds: Wilds) -> None:
    atlas = wilds.atlas
    await holy_to_gods(ctx, wilds)
    for church in (await FaithBook.load(ctx.session)).churches.values():
        held = church.tenets.get(TenetKind.SACRED_SPECIES)
        if held is not None and held.target is not None and held.target.isdigit():
            for member in church.members:
                region = atlas.top_region(member.id)
                if region is not None:
                    wilds.sacred[int(held.target)].add(region)
    totems = await ctx.session.execute(
        select(BondRow.source_node_id, TraditionProfileRow.origin_entity_id)
        .join(TraditionProfileRow, TraditionProfileRow.tradition_entity_id == BondRow.target_node_id)
        .where(BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE, TraditionProfileRow.origin_entity_id.is_not(None))
    )
    for keeper, species_id in totems:
        region = atlas.top_region(keeper)
        if region is not None and species_id is not None:
            wilds.sacred[species_id].add(region)
    hosts = await ctx.session.execute(select(SpeciesHostRow.species_entity_id, SpeciesHostRow.disease_entity_id).where(SpeciesHostRow.immune.is_(False)))
    carriers: dict[int, set[int]] = defaultdict(set)
    for species_id, disease_id in hosts:
        carriers[disease_id].add(species_id)
    for outbreak in await ctx.session.scalars(select(OutbreakRow).where(OutbreakRow.status != OutbreakStatus.ENDED)):
        for species_id in carriers.get(outbreak.disease_entity_id, set()):
            wilds.sick[species_id].add(outbreak.region_entity_id)


def terrain_fit(rules: Rules, profile: SpeciesProfileRow, land: RegionEnvironmentRow, traits: set[CreatureTrait]) -> float:
    table = rules.habitat
    fit = profile.habitat.get(land.dominant_terrain.value, table.terrain_default) / PERCENT
    if traits & {T.AQUATIC, T.AMPHIBIOUS} and land.coast_kind.value != "none":
        fit = max(fit, table.water_fit / PERCENT)
    return fit


def fit_of(
    rules: Rules, profile: SpeciesProfileRow, land: RegionEnvironmentRow | None, traits: set[CreatureTrait], allowed: tuple[Biochemistry, ...] | None = None
) -> float:
    if land is None:
        return rules.habitat.terrain_default / PERCENT
    if allowed is not None and not bearable(profile.biochemistry, allowed):
        return 0.0
    table = rules.habitat
    fit = terrain_fit(rules, profile, land, traits)
    beyond = max(0, profile.temperature_min - table.temperature_slack - land.temperature, land.temperature - profile.temperature_max - table.temperature_slack)
    fit *= max(0.0, 1 - beyond * table.cold_penalty_pct / PERCENT)
    if not profile.altitude_min <= land.elevation_mean <= profile.altitude_max:
        fit *= 1 - table.altitude_penalty_pct / PERCENT
    if land.moisture < profile.water_need:
        fit *= max(0.0, 1 - (profile.water_need - land.moisture) / PERCENT * table.water_pct / PERCENT)
    return max(0.0, min(1.5, fit))


def wildness(land: RegionEnvironmentRow | None, burrowing: bool, rules: Rules) -> int | None:
    if land is None:
        return None
    cleared = land.cleared * (1 - rules.habitat.burrow_pct / PERCENT) if burrowing else land.cleared
    return clamp_int(land.forest_cover + land.wetland - round_half_up(cleared), 0, PERCENT)


def capacity_of(rules: Rules, land: RegionEnvironmentRow | None, region: EntityRow | None, megafauna: bool, wild: int | None) -> int:
    ecology = rules.ecology
    if megafauna:
        return ecology.megafauna_capacity
    fertility = stat(region, "fertility") if region is not None else None
    if fertility is None:
        fertility = land.soil_fertility if land is not None else ecology.initial_base
    extra = 0 if wild is None else (wild - ecology.wildness_pivot) * ecology.capacity_wildness_pct / PERCENT
    return clamp_int(ecology.capacity_base + fertility * ecology.capacity_fertility_pct / PERCENT + extra, 1, PERCENT)


def food_of(rules: Rules, profile: SpeciesProfileRow, land: RegionEnvironmentRow | None, prey: list[int]) -> float:
    table = rules.habitat
    if profile.diet in HUNTERS and profile.diet not in GRAZERS:
        if not prey:
            return 1 - table.prey_pct / PERCENT
        mean = sum(prey) / len(prey)
        return 1 - table.prey_pct / PERCENT + table.prey_pct / PERCENT * min(2.0, mean / max(1, rules.ecology.hunger_threshold * 2))
    if profile.diet in GRAZERS and land is not None:
        forage = (land.forest_cover + land.soil_fertility) / (2 * PERCENT)
        return 1 - table.forage_pct / PERCENT + table.forage_pct / PERCENT * forage * 2
    return 1.0


def growth_rate(rules: Rules, profile: SpeciesProfileRow, land: RegionEnvironmentRow | None, traits: set[CreatureTrait]) -> float:
    table = rules.habitat
    young = profile.litter_size * max(1, profile.breeding_seasons) / max(1, 1 + profile.maturity_years)
    rate = rules.ecology.reversion_pct / PERCENT * (1 + young * table.fecundity_pct / PERCENT)
    if land is not None:
        rate *= 1 - land.seasonality / PERCENT * table.season_pct / PERCENT
    if T.SWARM_BREEDER in traits:
        rate *= 1 + table.swarm_pct / PERCENT
    return rate


def shield(rules: Rules, traits: set[CreatureTrait]) -> float:
    table = rules.habitat
    kept = 1.0
    if T.ARMOURED in traits:
        kept *= 1 - table.armour_pct / PERCENT
    if traits & {T.CAMOUFLAGE, T.MIMIC}:
        kept *= 1 - table.camouflage_pct / PERCENT
    return kept


@dataclass(frozen=True)
class Pressure:
    hunted: float
    loss: float


def numbers_kept(rules: Rules, profile: SpeciesProfileRow | None) -> float:
    if profile is not None and profile.sociality in {Sociality.HERD, Sociality.HIVE}:
        return 1 - rules.habitat.herd_pct / PERCENT
    return 1.0


def predation(rules: Rules, wilds: Wilds, prey_id: int, region: int, hunters_of: dict[int, list[int]]) -> float:
    ecology = rules.ecology
    loss = 0.0
    for hunter_id in hunters_of.get(prey_id, []):
        hunter = wilds.ranges.get(hunter_id, {}).get(region)
        if hunter is None:
            continue
        bite = ecology.predation + hunter.abundance / ecology.predation_divisor
        hunter_profile = wilds.profiles.get(hunter_id)
        if T.PACK_HUNTER in wilds.traits.get(hunter_id, set()) or (hunter_profile is not None and hunter_profile.sociality is Sociality.PACK):
            bite *= 1 + rules.habitat.pack_pct / PERCENT
        loss += bite
    return loss * shield(rules, wilds.traits.get(prey_id, set())) * numbers_kept(rules, wilds.profiles.get(prey_id))


def human_hunting(rules: Rules, wilds: Wilds, species: EntityRow, region: int, *, protected: bool, megafauna: bool) -> float:
    ecology = rules.ecology
    traits = wilds.traits.get(species.id, set())
    if protected or megafauna or traits & UNHUNTED or region in wilds.sacred.get(species.id, set()) or (stat(species, "danger") or 0) >= ecology.hunting_danger:
        return 0.0
    pressure: float = min(ecology.hunting_cap, wilds.population[region] // max(1, ecology.hunting_population))
    if T.REGENERATING in traits:
        pressure *= 1 - rules.habitat.regeneration_pct / PERCENT
    profile = wilds.profiles.get(species.id)
    if profile is not None:
        pressure *= 1 - profile.cunning / PERCENT * rules.habitat.cunning_pct / PERCENT
        if profile.nocturnal or T.ECHOLOCATION in traits:
            pressure *= 1 - rules.habitat.nocturnal_pct / PERCENT
    return pressure * shield(rules, traits)


@dataclass(frozen=True)
class RangeMarks:
    megafauna: set[int]
    protected: set[int]
    invasive: set[int]


def plan(
    ctx: TickContext,
    wilds: Wilds,
    species: EntityRow,
    row: SpeciesRangeRow,
    *,
    hunters_of: dict[int, list[int]],
    prey_of: dict[int, list[int]],
    marks: RangeMarks,
) -> Pressure:
    rules = ctx.rules
    region = row.region_entity_id
    profile = wilds.profiles[species.id]
    traits = wilds.traits.get(species.id, set())
    land = wilds.lands.get(region)
    fit = fit_of(rules, profile, land, traits, wilds.allowed(land))
    if "fit" not in row.locked:
        row.fit = clamp_int(round_half_up(fit * PERCENT), 0, PERCENT * 2)
    prey = [wilds.ranges[item][region].abundance for item in prey_of.get(species.id, []) if region in wilds.ranges.get(item, {})]
    megafauna = species.id in marks.megafauna
    capacity = (
        capacity_of(rules, land, wilds.regions.get(region), megafauna, wildness(land, T.BURROWING in traits, rules)) * fit * food_of(rules, profile, land, prey)
    )
    delta = (capacity - row.abundance) * growth_rate(rules, profile, land, traits)
    delta -= predation(rules, wilds, species.id, region, hunters_of)
    if profile.diet in HUNTERS and prey and sum(prey) / len(prey) < rules.ecology.hunger_threshold:
        delta -= rules.ecology.hunger * profile.metabolism / rules.habitat.metabolism_mean
    hunted = human_hunting(rules, wilds, species, region, protected=species.id in marks.protected, megafauna=megafauna)
    delta -= hunted
    if region in wilds.sick.get(species.id, set()):
        delta -= rules.habitat.disease_loss * (1 - rules.habitat.regeneration_pct / PERCENT if T.REGENERATING in traits else 1)
    if species.id not in marks.invasive:
        delta -= wilds.invasive[region] * rules.ecology.invasive_pressure * (1 - profile.territoriality / PERCENT * rules.habitat.territory_pct / PERCENT)
    swing = ctx.rng(f"range.{species.id}.{region}").die(rules.ecology.noise) - (rules.ecology.noise + 1) / 2
    delta += swing * (1 - rules.habitat.long_lived_pct / PERCENT if T.LONG_LIVED in traits else 1)
    return Pressure(hunted=min(hunted, row.abundance), loss=delta)


def settle(row: SpeciesRangeRow, delta: float, epoch: int) -> None:
    if "abundance" in row.locked:
        return
    before = row.abundance
    row.abundance = clamp_int(round_half_up(before + delta), 0, PERCENT)
    row.trend = RangeTrend.RISING if row.abundance > before else RangeTrend.FALLING if row.abundance < before else RangeTrend.STEADY
    row.updated_epoch = epoch


def size_weights(atlas: RegionAtlas, regions: dict[int, EntityRow]) -> dict[int, float]:
    sizes: dict[int, int] = {}
    by_world: dict[int | None, list[int]] = defaultdict(list)
    for region_id, region in regions.items():
        record = atlas.record(region_id)
        if record is not None and record.size > 0 and not atlas.is_water(region_id):
            sizes[region_id] = record.size
            by_world[region.world_id].append(record.size)
    means = {world: sum(values) / len(values) for world, values in by_world.items() if values}
    return {region_id: size / means[regions[region_id].world_id] for region_id, size in sizes.items()}


def overall(rules: Rules, rows: list[SpeciesRangeRow], weights: dict[int, float]) -> int:
    weight = rules.habitat.range_weight_pct / PERCENT
    total = sum(row.abundance * weights.get(row.region_entity_id, 1.0) * weight for row in rows if row.abundance > 0)
    return clamp_int(round_half_up(total), 0, PERCENT)


async def seed(ctx: TickContext, wilds: Wilds, species: list[EntityRow], initial: dict[int, int]) -> int:
    opened = 0
    for item in species:
        if wilds.profiles[item.id].stage in HOUSED:
            continue
        homes = {wilds.atlas.top_region(item.id)} | {
            bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.LIVES_IN], sources=[item.id]) if bond.target_node_id in wilds.regions
        }
        for region in sorted(home for home in homes if home is not None):
            if region in wilds.ranges[item.id]:
                continue
            row = SpeciesRangeRow(
                species_entity_id=item.id,
                region_entity_id=region,
                abundance=initial.get(item.id, ctx.rules.ecology.initial_base) if not wilds.ranges[item.id] else ctx.rules.habitat.spread_seed,
                trend=RangeTrend.STEADY,
                fit=PERCENT // 2,
                hunted=0,
                since_epoch=ctx.epoch,
                updated_epoch=ctx.epoch,
                locked=[],
            )
            ctx.session.add(row)
            wilds.ranges[item.id][region] = row
            opened += 1
    return opened


async def spread(ctx: TickContext, wilds: Wilds, species: list[EntityRow]) -> int:
    table = ctx.rules.habitat
    opened = 0
    for item in species:
        traits = wilds.traits.get(item.id, set())
        for region, row in sorted(wilds.ranges[item.id].items()):
            if opened >= table.spread_cap or row.abundance < table.spread_threshold:
                continue
            for neighbour in wilds.atlas.neighbour_regions(region):
                if neighbour in wilds.ranges[item.id] or neighbour not in wilds.regions:
                    continue
                if wilds.atlas.is_water(neighbour) and not traits & {T.AQUATIC, T.FLYING}:
                    continue
                if (
                    fit_of(ctx.rules, wilds.profiles[item.id], wilds.lands.get(neighbour), traits, wilds.allowed(wilds.lands.get(neighbour))) * PERCENT
                    < table.spread_fit
                ):
                    continue
                fresh = SpeciesRangeRow(
                    species_entity_id=item.id,
                    region_entity_id=neighbour,
                    abundance=table.spread_seed,
                    trend=RangeTrend.RISING,
                    fit=PERCENT // 2,
                    hunted=0,
                    since_epoch=ctx.epoch,
                    updated_epoch=ctx.epoch,
                    locked=[],
                )
                ctx.session.add(fresh)
                wilds.ranges[item.id][neighbour] = fresh
                opened += 1
                break
    return opened


async def migrate(ctx: TickContext, wilds: Wilds, species: list[EntityRow]) -> int:
    table = ctx.rules.habitat
    moved = 0
    for item in species:
        profile = wilds.profiles[item.id]
        if not profile.migratory:
            continue
        if len(profile.migration_path) < 2 and "migration_path" not in profile.locked:
            home = min(wilds.ranges[item.id], key=lambda region: -wilds.ranges[item.id][region].abundance, default=None)
            options = [region for region in (wilds.atlas.neighbour_regions(home) if home is not None else []) if region in wilds.regions]
            if home is None or not options:
                continue
            best = max(
                options,
                key=lambda region: (
                    fit_of(ctx.rules, profile, wilds.lands.get(region), wilds.traits.get(item.id, set()), wilds.allowed(wilds.lands.get(region))),
                    -region,
                ),
            )
            profile.migration_path = [home, best]
        path = [region for region in profile.migration_path if region in wilds.regions]
        if len(path) < 2:
            continue
        start, end = (path[0], path[1]) if ctx.epoch % 2 == 0 else (path[1], path[0])
        source = wilds.ranges[item.id].get(start)
        if source is None or source.abundance <= 0 or "abundance" in source.locked:
            continue
        target = wilds.ranges[item.id].get(end)
        if target is None:
            target = SpeciesRangeRow(
                species_entity_id=item.id,
                region_entity_id=end,
                abundance=0,
                trend=RangeTrend.RISING,
                fit=PERCENT // 2,
                hunted=0,
                since_epoch=ctx.epoch,
                updated_epoch=ctx.epoch,
                locked=[],
            )
            ctx.session.add(target)
            wilds.ranges[item.id][end] = target
        if "abundance" in target.locked:
            continue
        share = round_half_up(source.abundance * table.migration_pct / PERCENT)
        source.abundance -= share
        target.abundance = clamp_int(target.abundance + share, 0, PERCENT)
        moved += 1
    return moved


async def harvest_hunt(ctx: TickContext, wilds: Wilds, species_id: int, region: int, hunted: float) -> int:
    if hunted <= 0 or not wilds.hunters[region]:
        return 0
    products = list(await ctx.session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.species_entity_id == species_id)))
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    taken = 0
    share = hunted / len(wilds.hunters[region])
    for community in wilds.hunters[region]:
        for item in products:
            amount = round_half_up(share * item.rate)
            if amount > 0 and item.commodity is not None:
                taken += await ledger.add(
                    community.id, item.commodity, amount, GoodsFlow.EXTRACTION, material=item.material, world_material_id=item.world_material_id
                )
    return taken


TERRAIN_WORDS = {
    "hills": "highland",
    "mountains": "highland",
    "high_pass": "highland",
    "desert": "desert",
    "tundra": "frost",
    "ice_sheet": "frost",
    "marsh": "marsh",
    "jungle": "jungle",
    "forest": "forest",
    "steppe": "steppe",
    "island": "island",
    "volcanic": "ash",
}


async def adapt_subspecies(ctx: TickContext, parent: EntityRow, child: EntityRow, region_id: int) -> str:
    source = await profile_of(ctx, parent)
    row = await profile_of(ctx, child)
    land = await ctx.session.get(RegionEnvironmentRow, region_id)
    drift = ctx.rules.habitat.subspecies_drift
    word = "isolated"
    if land is not None:
        word = TERRAIN_WORDS.get(land.dominant_terrain.value, word)
        middle = (source.temperature_min + source.temperature_max) / 2
        shift = drift if land.temperature > middle else -drift
        row.temperature_min, row.temperature_max = source.temperature_min + shift, source.temperature_max + shift
        table = ctx.rules.habitat
        swing = 1 if land.temperature <= table.subspecies_cold else -1 if land.temperature >= table.subspecies_hot else 0
        index = SIZE_ORDER.index(source.size_class) + swing
        row.size_class = SIZE_ORDER[max(0, min(len(SIZE_ORDER) - 1, index))]
        row.habitat = {**source.habitat, land.dominant_terrain.value: PERCENT}
    child.subtype = f"{word} subspecies"
    parent_range = await ctx.session.get(SpeciesRangeRow, (parent.id, region_id))
    if parent_range is not None:
        ctx.session.add(
            SpeciesRangeRow(
                species_entity_id=child.id,
                region_entity_id=region_id,
                abundance=parent_range.abundance,
                trend=RangeTrend.STEADY,
                fit=parent_range.fit,
                hunted=0,
                since_epoch=ctx.epoch,
                updated_epoch=ctx.epoch,
                locked=[],
            )
        )
        await ctx.session.delete(parent_range)
    await ctx.session.flush()
    return word
