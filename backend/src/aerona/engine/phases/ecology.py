from collections import defaultdict
from dataclasses import dataclass, field

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityFlag, EntityType
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, flags_by_entity, living_entity, remove_flag
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

ABUNDANCE_KEY = "abundance"


@dataclass
class Habitat:
    regions: dict[int, EntityRow]
    atlas: RegionAtlas
    population: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    invasive: dict[int, int] = field(default_factory=lambda: defaultdict(int))

    def region_of(self, species: EntityRow) -> int | None:
        return self.atlas.top_region(species.id)


async def fertility_of(ctx: TickContext, species: EntityRow, habitat: Habitat) -> int:
    location = await living_entity(ctx.session, species.location_id)
    value = stat(location, "fertility") if location is not None else None
    if value is None:
        region = habitat.regions.get(habitat.region_of(species) or 0)
        value = stat(region, "fertility") if region is not None else None
    return value if value is not None else ctx.rules.ecology.initial_base


def initial_abundance(rules: Rules, fertility: int, megafauna: bool) -> int:
    ecology = rules.ecology
    if megafauna:
        return ecology.initial_megafauna
    return clamp_int(ecology.initial_base + fertility * ecology.initial_fertility_pct / 100, 1, 100)


def carrying_capacity(rules: Rules, fertility: int, megafauna: bool) -> int:
    ecology = rules.ecology
    if megafauna:
        return ecology.megafauna_capacity
    return clamp_int(ecology.capacity_base + fertility * ecology.capacity_fertility_pct / 100, 1, 100)


def abundance(species: EntityRow) -> int:
    return stat(species, ABUNDANCE_KEY) or 0


async def load_habitat(ctx: TickContext, species: list[EntityRow], invasive: set[int]) -> Habitat:
    habitat = Habitat({region.id: region for region in await canon(ctx.session, [EntityType.REGION])}, await RegionAtlas.load(ctx.session))
    for community in await canon(ctx.session, SOCIETY_TYPES):
        region = habitat.atlas.top_region(community.id)
        if region is not None:
            habitat.population[region] += stat(community, "population") or 0
    for item in species:
        region = habitat.region_of(item)
        if item.id in invasive and region is not None:
            habitat.invasive[region] += 1
    return habitat


async def seed_abundance(ctx: TickContext, species: list[EntityRow], habitat: Habitat, megafauna: set[int]) -> int:
    seeded = 0
    for item in species:
        if stat(item, ABUNDANCE_KEY) is None:
            set_stats(item, abundance=initial_abundance(ctx.rules, await fertility_of(ctx, item, habitat), item.id in megafauna))
            seeded += 1
    return seeded


async def extinction(ctx: TickContext, species: EntityRow, hunters: list[EntityRow], habitat: Habitat) -> None:
    ecology = ctx.rules.ecology
    predator = max(hunters, key=lambda hunter: (abundance(hunter), -hunter.id), default=None)
    region = habitat.region_of(species)
    hunter_people: EntityRow | None = None
    if predator is None and (stat(species, "danger") or 0) < ecology.hunting_danger and region is not None:
        nearby = [community for community in await canon(ctx.session, SOCIETY_TYPES) if habitat.atlas.top_region(community.id) == region]
        hunter_people = max(nearby, key=lambda community: (stat(community, "population") or 0, -community.id), default=None)
    if predator is not None:
        reason = f"{predator.name} hunted down its last herds"
    elif hunter_people is not None:
        reason = f"the hunters of {hunter_people.name} took its last herds"
    else:
        reason = "the land could carry it no longer"
    set_stats(species, abundance=0)
    await remove_flag(ctx.session, species.id, EntityFlag.ENDANGERED)
    await add_flag(ctx.session, species.id, EntityFlag.EXTINCT, ctx.epoch)
    await retire_in(ctx, species, f"went extinct; {reason}")
    culprit = predator or hunter_people
    if culprit is not None:
        await BondRepository(ctx.session).connect(BondDraft(culprit.id, species.id, BondKind.DESTROYED, ctx.epoch, "wiped out its kind"))
    await note(ctx, f"{species.name} died out: {reason}.", key="ecology.extinct", ids=[species.id, *([culprit.id] if culprit is not None else [])])


@dataclass(frozen=True)
class FoodWeb:
    prey_of: dict[int, list[EntityRow]]
    hunters_of: dict[int, list[EntityRow]]


@dataclass(frozen=True)
class EcologyMarks:
    megafauna: set[int]
    protected: set[int]
    invasive: set[int]
    endangered: set[int]
    rewound: set[int]


async def food_web(ctx: TickContext, species: list[EntityRow]) -> FoodWeb:
    by_id = {item.id: item for item in species}
    prey_of: dict[int, list[EntityRow]] = defaultdict(list)
    hunters_of: dict[int, list[EntityRow]] = defaultdict(list)
    for bond in await active_bonds(ctx.session, [BondKind.HUNTS]):
        hunter, prey = by_id.get(bond.source_node_id), by_id.get(bond.target_node_id)
        if hunter is not None and prey is not None:
            prey_of[hunter.id].append(prey)
            hunters_of[prey.id].append(hunter)
    return FoodWeb(prey_of, hunters_of)


async def planned_abundance(ctx: TickContext, item: EntityRow, web: FoodWeb, habitat: Habitat, marks: EcologyMarks) -> int:
    settings = ctx.rules.ecology
    current = abundance(item)
    is_megafauna = item.id in marks.megafauna
    delta = (carrying_capacity(ctx.rules, await fertility_of(ctx, item, habitat), is_megafauna) - current) * settings.reversion_pct / 100
    for hunter in web.hunters_of[item.id]:
        delta -= settings.predation + abundance(hunter) / settings.predation_divisor
    eaten = web.prey_of[item.id]
    if eaten and sum(abundance(other) for other in eaten) / len(eaten) < settings.hunger_threshold:
        delta -= settings.hunger
    region = habitat.region_of(item)
    if item.id not in marks.protected and not is_megafauna and (stat(item, "danger") or 0) < settings.hunting_danger and region is not None:
        delta -= min(settings.hunting_cap, habitat.population[region] // settings.hunting_population)
    if item.id not in marks.invasive and region is not None:
        delta -= habitat.invasive[region] * settings.invasive_pressure
    delta += ctx.rng(f"abundance.{item.id}").die(settings.noise) - (settings.noise + 1) / 2
    return round_half_up(current + delta)


async def track_endangered(ctx: TickContext, item: EntityRow, marks: EcologyMarks, warnings: int) -> int:
    settings = ctx.rules.ecology
    if abundance(item) < settings.critical and item.id not in marks.endangered:
        await add_flag(ctx.session, item.id, EntityFlag.ENDANGERED, ctx.epoch)
        if warnings < settings.warning_cap:
            await note(ctx, f"The herds of {item.name} grew sparse; it is close to dying out.", key="ecology.endangered", ids=[item.id])
            return warnings + 1
    elif abundance(item) >= settings.critical * 2 and item.id in marks.endangered:
        await remove_flag(ctx.session, item.id, EntityFlag.ENDANGERED)
    return warnings


async def ecology(ctx: TickContext) -> None:
    settings = ctx.rules.ecology
    species = await canon(ctx.session, [EntityType.SPECIES])
    if not species:
        return
    flags = [
        await flags_by_entity(ctx.session, flag)
        for flag in (EntityFlag.MEGAFAUNA, EntityFlag.PROTECTED, EntityFlag.INVASIVE, EntityFlag.ENDANGERED, EntityFlag.TIME_RETURNED)
    ]
    marks = EcologyMarks(*flags)
    habitat = await load_habitat(ctx, species, marks.invasive)
    ctx.count("seeded", await seed_abundance(ctx, species, habitat, marks.megafauna))
    web = await food_web(ctx, species)
    planned = {item.id: await planned_abundance(ctx, item, web, habitat, marks) for item in species}
    extinct = warnings = 0
    for item in species:
        value = settings.last_herd if planned[item.id] <= 0 and item.id in marks.protected else planned[item.id]
        if value <= 0:
            if CreatureTrait.TIME_REWINDER in await EntityRepository(ctx.session).traits(item.id) and item.id not in marks.rewound:
                set_stats(item, abundance=settings.rewind_abundance)
                await add_flag(ctx.session, item.id, EntityFlag.TIME_RETURNED, ctx.epoch)
                await note(
                    ctx, f"{item.name} turned back time in the epoch it would have died out; its herds are seen again.", key="ecology.rewound", ids=[item.id]
                )
                continue
            if extinct < settings.extinction_cap:
                await extinction(ctx, item, web.hunters_of[item.id], habitat)
                extinct += 1
                continue
            value = settings.last_herd
        set_stats(item, abundance=clamp_int(value, 0, 100))
        warnings = await track_endangered(ctx, item, marks, warnings)
    ctx.count("extinct", extinct)
    await ctx.session.flush()


async def set_abundance(ctx: TickContext, species_id: int, value: int) -> EntityRow:
    species = await living_entity(ctx.session, species_id)
    if species is None or species.entity_type is not EntityType.SPECIES:
        raise ValidationFailedError("Only a living species has an abundance.")
    set_stats(species, abundance=clamp_int(value, 0, 100))
    if abundance(species) >= ctx.rules.ecology.critical:
        await remove_flag(ctx.session, species.id, EntityFlag.ENDANGERED)
    await note(ctx, f"The herds of {species.name} now stand at {abundance(species)}.", key="ecology.abundance_set", ids=[species.id])
    return species


PHASES = (Phase("ecology", ecology),)
