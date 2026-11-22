import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.diets import GRAZERS, HUNTERS
from aerona.catalog.domestication import HOUSED_STAGES, SOCIALITIES
from aerona.catalog.senses import TRACKING
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.ecology import HerdRow, SpeciesHostRow, SpeciesProductRow, SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.gardens import GardenRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.ecology import SIZE_ORDER, Biochemistry, HerdTraining, RangeTrend, Sociality
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.evolution import EvolvedTrait
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.agrarian.book import reserve_factor, reserve_marks
from aerona.engine.body.variants import ORDINARY, BiologyView, biology_views
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.creature_groups.groups import hunt_factor
from aerona.engine.ecology.biochemistry import bearable, tolerated
from aerona.engine.ecology.evolution import alert, cold_reach, drought_reach, escape, evolved_traits, fecund, heat_reach, wary
from aerona.engine.ecology.profiles import profile_of
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.faith.book import FaithBook
from aerona.engine.folk_knowledge.factor import folk_factor
from aerona.engine.loops.delay import delay_of, lagged
from aerona.engine.museums.reading import refuges
from aerona.engine.nature.islands import spared_kinds
from aerona.engine.nature.seasons import activity, asleep, chilled, season_bands
from aerona.engine.nature.senses import sense_score
from aerona.engine.nature.sleepers import awake_now
from aerona.engine.nature.symbiosis import SymbiosisBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.physics import flight_capacity_pct
from aerona.engine.primitives.queries import active_bonds, canon
from aerona.engine.primitives.stats import stat
from aerona.engine.protected_nature.book import hunting_marks, spared_species
from aerona.rules.registry import Rules

T = CreatureTrait
UNHUNTED = frozenset({T.POISONOUS_FLESH, T.SACRED_ANIMAL})
HOUSED = HOUSED_STAGES


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
    hunt_bonus: dict[int, float] = field(default_factory=dict)
    lift: dict[int, float] = field(default_factory=dict)
    evolved: dict[tuple[int, int], dict[EvolvedTrait, int]] = field(default_factory=dict)
    reserves: dict[tuple[int, int | None], tuple[int, int]] = field(default_factory=dict)
    symbiosis: SymbiosisBook = field(default_factory=SymbiosisBook)
    bands: dict[int, TemperatureBand] = field(default_factory=dict)
    spared: frozenset[tuple[int, int]] = frozenset()
    protected_kinds: dict[int, float] = field(default_factory=dict)
    tracking: dict[int, float] = field(default_factory=dict)
    epoch: int = 0
    presence: dict[int, dict[int, int]] = field(default_factory=dict)
    natures: dict[int, BiologyView] = field(default_factory=dict)
    refuges: set[tuple[int, int]] = field(default_factory=set)
    refuge_floor: int = 0

    def present(self, region_id: int) -> dict[int, int]:
        if region_id not in self.presence:
            self.presence[region_id] = {species_id: row.abundance for species_id, row in self.in_region(region_id).items()}
        return self.presence[region_id]

    def allowed(self, land: RegionEnvironmentRow | None) -> tuple[Biochemistry, ...] | None:
        return self.life.get(land.world_id) if land is not None and land.world_id is not None else None

    def in_region(self, region_id: int) -> dict[int, SpeciesRangeRow]:
        return {species_id: rows[region_id] for species_id, rows in self.ranges.items() if region_id in rows}


async def load_wilds(ctx: TickContext, species: list[EntityRow], invasive: set[int]) -> Wilds:
    atlas = await RegionAtlas.load(ctx.session)
    lands = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    wilds = Wilds(atlas, lands, {region.id: region for region in await canon(ctx.session, [EntityType.REGION])})
    wilds.reserves = await reserve_marks(ctx.session)
    for key, mark in (await hunting_marks(ctx.session, ctx.rules)).items():
        wilds.reserves[key] = max(wilds.reserves.get(key, mark), mark)
    wilds.protected_kinds = await spared_species(ctx.session, ctx.rules)
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
        wilds.lift[world_id] = flight_capacity_pct(ctx.rules, await ctx.session.get(WorldRow, world_id)) / PERCENT
    trained: dict[int, int] = {}
    for community_id, head in await ctx.session.execute(select(HerdRow.community_entity_id, HerdRow.trained).where(HerdRow.training == HerdTraining.HUNTING)):
        trained[community_id] = trained.get(community_id, 0) + head
    table = ctx.rules.husbandry
    wilds.hunt_bonus = {key: 1 + table.hunt_pct / PERCENT * min(1.0, value / table.trained_full_head) for key, value in trained.items()}
    wilds.evolved = await evolved_traits(ctx.session)
    wilds.symbiosis = await SymbiosisBook.load(ctx.session)
    wilds.bands = await season_bands(ctx.session, ctx.rules, ctx.epoch)
    wilds.spared = await spared_kinds(ctx.session, ctx.rules.island_rule.revered_value)
    wilds.epoch = ctx.epoch
    wilds.natures = await biology_views(ctx.session)
    towns = set(await ctx.session.scalars(select(GardenRow.settlement_entity_id)))
    wilds.refuges = await refuges(ctx.session, {town: atlas.top_region(town) for town in towns})
    wilds.refuge_floor = ctx.rules.gardens.refuge_floor
    for region, communities in wilds.hunters.items():
        keen = [await sense_score(ctx.session, community.id, TRACKING) for community in communities]
        wilds.tracking[region] = 1 + sum(keen) / len(keen) * ctx.rules.senses.tracking_pct / PERCENT if keen else 1.0
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
    rules: Rules,
    profile: SpeciesProfileRow,
    land: RegionEnvironmentRow | None,
    traits: set[CreatureTrait],
    allowed: tuple[Biochemistry, ...] | None = None,
    *,
    cold: float = 0.0,
    heat: float = 0.0,
    dry: float = 0.0,
) -> float:
    if land is None:
        return rules.habitat.terrain_default / PERCENT
    if allowed is not None and not bearable(profile.biochemistry, allowed):
        return 0.0
    table = rules.habitat
    fit = terrain_fit(rules, profile, land, traits)
    beyond = max(
        0,
        profile.temperature_min - table.temperature_slack - cold - land.temperature,
        land.temperature - profile.temperature_max - table.temperature_slack - heat,
    )
    fit *= max(0.0, 1 - beyond * table.cold_penalty_pct / PERCENT)
    if not profile.altitude_min <= land.elevation_mean <= profile.altitude_max:
        fit *= 1 - table.altitude_penalty_pct / PERCENT
    if land.moisture + dry < profile.water_need:
        fit *= max(0.0, 1 - (profile.water_need - land.moisture - dry) / PERCENT * table.water_pct / PERCENT)
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
    if profile is not None and SOCIALITIES[profile.sociality].keeps_numbers:
        return 1 - rules.habitat.herd_pct / PERCENT
    return 1.0


def predation(rules: Rules, wilds: Wilds, prey_id: int, region: int, hunters_of: dict[int, list[int]]) -> float:
    ecology = rules.ecology
    loss = 0.0
    for hunter_id in hunters_of.get(prey_id, []):
        hunter = wilds.ranges.get(hunter_id, {}).get(region)
        if hunter is None:
            continue
        hunter_profile = wilds.profiles.get(hunter_id)
        bite = (ecology.predation + hunter.abundance / ecology.predation_divisor) * (
            activity(rules, hunter_profile.thermoregulation, wilds.bands.get(region)) if hunter_profile is not None else 1.0
        )
        if T.PACK_HUNTER in wilds.traits.get(hunter_id, set()) or (hunter_profile is not None and hunter_profile.sociality is Sociality.PACK):
            bite *= 1 + rules.habitat.pack_pct / PERCENT
        loss += bite
    return loss * shield(rules, wilds.traits.get(prey_id, set())) * numbers_kept(rules, wilds.profiles.get(prey_id))


def human_hunting(rules: Rules, wilds: Wilds, species: EntityRow, region: int, *, protected: bool, megafauna: bool, people: int) -> float:
    ecology = rules.ecology
    traits = wilds.traits.get(species.id, set())
    spared = protected or (species.id, region) in wilds.spared or region in wilds.sacred.get(species.id, set())
    if spared or megafauna or traits & UNHUNTED or (stat(species, "danger") or 0) >= ecology.hunting_danger:
        return 0.0
    pressure: float = min(ecology.hunting_cap, math.log2(1 + people / max(1, ecology.hunting_population))) * wilds.tracking.get(region, 1.0)
    pressure *= reserve_factor(rules, wilds.reserves, species.id, region)
    pressure *= 1 - wilds.protected_kinds.get(species.id, 0.0)
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
    traps: Mapping[tuple[int, int], float] = field(default_factory=dict)
    prey_seen: Mapping[tuple[int, int], float] = field(default_factory=dict)
    people_seen: Mapping[int, int] = field(default_factory=dict)


async def seen_by_hunters(
    ctx: TickContext, wilds: Wilds, species: list[EntityRow], prey_of: dict[int, list[int]]
) -> tuple[dict[tuple[int, int], float], dict[int, int]]:
    prey_seen: dict[tuple[int, int], float] = {}
    people_seen: dict[int, int] = {}
    if delay_of(ctx, BalanceLoop.PREDATOR_PREY) > 0:
        for item in species:
            for region in wilds.ranges[item.id]:
                now = sum(wilds.ranges[prey][region].abundance for prey in prey_of.get(item.id, []) if region in wilds.ranges.get(prey, {}))
                if now:
                    prey_seen[(item.id, region)] = await lagged(ctx, BalanceLoop.PREDATOR_PREY, region, float(now), subject=item.id) / now
    if delay_of(ctx, BalanceLoop.KEYSTONE_HUNTING) > 0:
        for region in sorted({region for item in species for region in wilds.ranges[item.id]}):
            people_seen[region] = await lagged(ctx, BalanceLoop.KEYSTONE_HUNTING, region, wilds.population[region])
    return prey_seen, people_seen


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
    evolved = wilds.evolved.get((species.id, region), {})
    fit = fit_of(
        rules, profile, land, traits, wilds.allowed(land), cold=cold_reach(rules, evolved), heat=heat_reach(rules, evolved), dry=drought_reach(rules, evolved)
    )
    if "fit" not in row.locked:
        row.fit = clamp_int(round_half_up(fit * PERCENT), 0, PERCENT * 2)
    felt = marks.prey_seen.get((species.id, region), 1.0)
    prey = [round_half_up(wilds.ranges[item][region].abundance * felt) for item in prey_of.get(species.id, []) if region in wilds.ranges.get(item, {})]
    megafauna = species.id in marks.megafauna
    capacity = (
        capacity_of(rules, land, wilds.regions.get(region), megafauna, wildness(land, T.BURROWING in traits, rules)) * fit * food_of(rules, profile, land, prey)
    )
    if T.FLYING in traits and land is not None:
        capacity *= wilds.lift.get(land.world_id, 1.0)
    present = wilds.present(region)
    band = wilds.bands.get(region)
    capacity *= wilds.symbiosis.room(rules, species.id, present) / (
        rules.thermoregulation.endotherm_cold_food_pct / PERCENT if chilled(profile.thermoregulation, band) else 1
    )
    nature = wilds.natures.get(species.id, ORDINARY)
    delta = (
        (capacity - row.abundance)
        * growth_rate(rules, profile, land, traits)
        * fecund(rules, evolved)
        * activity(rules, profile.thermoregulation, band)
        * nature.factor("fertility_pct")
    )
    delta -= wilds.symbiosis.drain(rules, species.id, present)
    delta -= predation(rules, wilds, species.id, region, hunters_of) * escape(rules, evolved) * alert(rules, evolved)
    if profile.diet in HUNTERS and prey and sum(prey) / len(prey) < rules.ecology.hunger_threshold:
        delta -= rules.ecology.hunger * profile.metabolism / rules.habitat.metabolism_mean * nature.factor("food_need_pct") * nature.factor("death_pct")
    hunted = (
        human_hunting(
            rules,
            wilds,
            species,
            region,
            protected=species.id in marks.protected,
            megafauna=megafauna,
            people=marks.people_seen.get(region, wilds.population[region]),
        )
        * wary(rules, evolved)
        * marks.traps.get((species.id, region), 1.0)
        * wilds.symbiosis.shield(rules, species.id, present)
    )
    if asleep(profile.dormancy, band) and not awake_now(profile, wilds.epoch):
        hunted = 0.0
    delta -= hunted
    if region in wilds.sick.get(species.id, set()):
        delta -= rules.habitat.disease_loss * (1 - rules.habitat.regeneration_pct / PERCENT if T.REGENERATING in traits else 1) * nature.factor("disease_pct")
    if species.id not in marks.invasive:
        delta -= wilds.invasive[region] * rules.ecology.invasive_pressure * (1 - profile.territoriality / PERCENT * rules.habitat.territory_pct / PERCENT)
    swing = ctx.rng(f"range.{species.id}.{region}").die(rules.ecology.noise) - (rules.ecology.noise + 1) / 2
    delta += swing * (1 - rules.habitat.long_lived_pct / PERCENT if T.LONG_LIVED in traits else 1)
    if (species.id, region) in wilds.refuges and row.abundance + delta < wilds.refuge_floor:
        delta = wilds.refuge_floor - row.abundance
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
        kind_opened = 0
        for region, row in ctx.rng(f"habitat.spread.{item.id}").shuffled(sorted(wilds.ranges[item.id].items())):
            if kind_opened >= table.spread_cap or row.abundance < table.spread_threshold:
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
                kind_opened += 1
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
    products = list(await ctx.session.scalars(select(SpeciesProductRow).where(SpeciesProductRow.species_entity_id == species_id)))
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    taken = 0
    share = hunted / len(wilds.hunters[region]) * await hunt_factor(ctx.session, ctx.rules, species_id, region)
    for community in wilds.hunters[region]:
        luck = await ctx.hook_factor(community.id, DomainHook.HUNT_YIELD)
        luck *= await folk_factor(ctx.session, ctx.rules, community, FolkDomain.ANIMALS)
        for item in products:
            amount = round_half_up(share * item.rate * wilds.hunt_bonus.get(community.id, 1.0) * luck)
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
