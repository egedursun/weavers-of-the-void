from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityFlag, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction, StepLocus
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.crafts.catch import trap_factors
from aerona.engine.ecology.domestication import domestic_head
from aerona.engine.ecology.extinction import cascade
from aerona.engine.ecology.foodweb import appetites
from aerona.engine.ecology.hosts import acquire_immunity
from aerona.engine.ecology.pests import plague_of_pests
from aerona.engine.ecology.ranges import (
    RangeMarks,
    Wilds,
    harvest_hunt,
    load_wilds,
    migrate,
    overall,
    plan,
    seed,
    seen_by_hunters,
    settle,
    size_weights,
    spread,
)
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, flags_by_entity, living_entity, remove_flag
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.recording.record import FactInput, StepDraft, record
from aerona.rules.registry import Rules

ABUNDANCE_KEY = "abundance"
HERD_UNIT = 10


@dataclass
class Habitat:
    regions: dict[int, EntityRow]
    atlas: RegionAtlas
    wilds: dict[int, int] = field(default_factory=dict)
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


def wildness_of(forest_cover: int, cleared: int, wetland: int) -> int:
    return clamp_int(forest_cover + wetland - cleared, 0, 100)


def abundance(species: EntityRow) -> int:
    return stat(species, ABUNDANCE_KEY) or 0


async def load_habitat(ctx: TickContext, species: list[EntityRow], invasive: set[int]) -> Habitat:
    grounds = await ctx.session.execute(
        select(RegionEnvironmentRow.entity_id, RegionEnvironmentRow.forest_cover, RegionEnvironmentRow.cleared, RegionEnvironmentRow.wetland)
    )
    wilds = {region_id: wildness_of(forest, cleared, wetland) for region_id, forest, cleared, wetland in grounds}
    habitat = Habitat({region.id: region for region in await canon(ctx.session, [EntityType.REGION])}, await RegionAtlas.load(ctx.session), wilds)
    for community in await canon(ctx.session, SOCIETY_TYPES):
        region = habitat.atlas.top_region(community.id)
        if region is not None:
            habitat.population[region] += stat(community, "population") or 0
    for item in species:
        region = habitat.region_of(item)
        if item.id in invasive and region is not None:
            habitat.invasive[region] += 1
    return habitat


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
        key = "ecology.extinct"
    elif hunter_people is not None:
        reason = f"the hunters of {hunter_people.name} took its last herds"
        key = "ecology.extinct_hunted"
    else:
        reason = "the land could carry it no longer"
        key = "ecology.extinct_starved"
    last = abundance(species)
    set_stats(species, abundance=0)
    for row in await ctx.session.scalars(
        select(SpeciesRangeRow).where(SpeciesRangeRow.species_entity_id == species.id).order_by(SpeciesRangeRow.region_entity_id)
    ):
        if "abundance" not in row.locked:
            row.abundance = 0
    await remove_flag(ctx.session, species.id, EntityFlag.ENDANGERED)
    await add_flag(ctx.session, species.id, EntityFlag.EXTINCT, ctx.epoch)
    await retire_in(ctx, species, f"went extinct; {reason}")
    culprit = predator or hunter_people
    if culprit is not None:
        await BondRepository(ctx.session).connect(BondDraft(culprit.id, species.id, BondKind.DESTROYED, ctx.epoch, "wiped out its kind"))
    facts: dict[str, FactInput] = {"abundance": last}
    if key == "ecology.extinct_hunted":
        facts["danger"] = stat(species, "danger") or 0
    await record(
        ctx,
        key,
        roles={IncidentRole.SUBJECT: species.id, IncidentRole.ACTOR: culprit.id if culprit is not None else None, IncidentRole.PLACE: region},
        facts=facts,
        place=region,
        steps=(
            StepDraft(
                StepAction.DIE_OUT,
                actor=culprit.id if culprit is not None else None,
                target=species.id,
                locus_kind=StepLocus.REGION if region is not None else StepLocus.NONE,
                locus_node=region,
                amount=last,
                unit=FactUnit.PERCENT,
            ),
        ),
    )


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


async def track_endangered(ctx: TickContext, item: EntityRow, marks: EcologyMarks, warnings: int) -> int:
    settings = ctx.rules.ecology
    if abundance(item) < settings.critical and item.id not in marks.endangered:
        await add_flag(ctx.session, item.id, EntityFlag.ENDANGERED, ctx.epoch)
        if warnings < settings.warning_cap:
            await record(
                ctx,
                "ecology.endangered",
                roles={IncidentRole.SUBJECT: item.id},
                facts={"abundance": abundance(item), "critical": settings.critical},
            )
            return warnings + 1
    elif abundance(item) >= settings.critical * 2 and item.id in marks.endangered:
        await remove_flag(ctx.session, item.id, EntityFlag.ENDANGERED)
    return warnings


async def wild_numbers(ctx: TickContext, species: list[EntityRow], marks: EcologyMarks) -> tuple[Wilds, int]:
    wilds = await load_wilds(ctx, species, marks.invasive)
    habitat = await load_habitat(ctx, species, marks.invasive)
    initial = {
        item.id: stat_or(item, ABUNDANCE_KEY, initial_abundance(ctx.rules, await fertility_of(ctx, item, habitat), item.id in marks.megafauna))
        for item in species
    }
    ctx.count("ranges_seeded", await seed(ctx, wilds, species, initial))
    web = await food_web(ctx, species)
    prey_of = {key: [item.id for item in rows] for key, rows in web.prey_of.items()}
    hunters_of = {key: [item.id for item in rows] for key, rows in web.hunters_of.items()}
    prey_seen, people_seen = await seen_by_hunters(ctx, wilds, species, prey_of)
    range_marks = RangeMarks(marks.megafauna, marks.protected, marks.invasive, await trap_factors(ctx.session, ctx.rules), prey_seen, people_seen)
    planned = [
        (row, plan(ctx, wilds, item, row, hunters_of=hunters_of, prey_of=prey_of, marks=range_marks))
        for item in species
        for row in list(wilds.ranges[item.id].values())
    ]
    hunted = 0
    for row, pressure in planned:
        settle(row, pressure.loss, ctx.epoch)
        row.hunted = round_half_up(pressure.hunted)
        hunted += await harvest_hunt(ctx, wilds, row.species_entity_id, row.region_entity_id, pressure.hunted)
    ctx.count("hunted_goods", hunted)
    for item in species:
        rows = wilds.ranges[item.id]
        for region in [region for region, row in rows.items() if row.abundance <= 0 and len(rows) > 1]:
            await ctx.session.delete(rows.pop(region))
            ctx.count("ranges_lost")
    ctx.count("ranges_spread", await spread(ctx, wilds, species))
    ctx.count("migrations", await migrate(ctx, wilds, species))
    for key, value in (await plague_of_pests(ctx, wilds)).items():
        ctx.count(key, value)
    return wilds, hunted


@reads(
    "people.population",
    "place.fertility",
    "region.fertility",
    "settlement.population",
    "species.abundance",
    "species.danger",
    "species.intelligence",
    "species.might",
    "species.strength",
    "spirit.unrest",
    "table.augment_effects",
    "table.augments",
    "table.bonds",
    "table.catch_grounds",
    "table.creator",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.entity_traits",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.game_reserves",
    "table.gardens",
    "table.herds",
    "table.nodes",
    "table.outbreaks",
    "table.region_environment",
    "table.reverences",
    "table.sense_profiles",
    "table.sons",
    "table.species_hosts",
    "table.species_products",
    "table.species_profiles",
    "table.species_ranges",
    "table.species_relations",
    "table.species_traits",
    "table.stars",
    "table.tradition_profiles",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes(
    "species.abundance",
    "spirit.unrest",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_stocks",
    "table.entities",
    "table.entity_flags",
    "table.incident_participants",
    "table.incidents",
    "table.species_hosts",
    "table.species_products",
    "table.species_profiles",
    "table.species_ranges",
    "table.species_uses",
)
async def ecology(ctx: TickContext) -> None:
    settings = ctx.rules.ecology
    species = unheld(await canon(ctx.session, [EntityType.SPECIES]))
    if not species:
        return
    flags = [
        await flags_by_entity(ctx.session, flag)
        for flag in (EntityFlag.MEGAFAUNA, EntityFlag.PROTECTED, EntityFlag.INVASIVE, EntityFlag.ENDANGERED, EntityFlag.TIME_RETURNED)
    ]
    marks = EcologyMarks(*flags)
    wilds, _ = await wild_numbers(ctx, species, marks)
    weights = size_weights(wilds.atlas, wilds.regions)
    ctx.count("immunities", await acquire_immunity(ctx, wilds))
    ctx.count("hungry_hunters", sum(1 for value in (await appetites(ctx, species, adjust=True)).values() if value > 1))
    web = await food_web(ctx, species)
    habitat = await load_habitat(ctx, species, marks.invasive)
    extinct = warnings = 0
    for item in species:
        rows = list(wilds.ranges[item.id].values())
        head = await domestic_head(ctx, item.id)
        if not rows and head is None:
            ctx.count("unplaced")
            continue
        value = overall(ctx.rules, rows, weights) if head is None else clamp_int(head // HERD_UNIT, 1 if head > 0 else 0, 100)
        if value <= 0 and item.id in marks.protected:
            value = settings.last_herd
        if value <= 0:
            if CreatureTrait.TIME_REWINDER in await EntityRepository(ctx.session).traits(item.id) and item.id not in marks.rewound:
                for row in rows:
                    row.abundance = settings.rewind_abundance
                set_stats(item, abundance=settings.rewind_abundance)
                await add_flag(ctx.session, item.id, EntityFlag.TIME_RETURNED, ctx.epoch)
                await record(ctx, "ecology.rewound", roles={IncidentRole.SUBJECT: item.id}, facts={"abundance": settings.rewind_abundance})
                continue
            await extinction(ctx, item, web.hunters_of[item.id], habitat)
            ctx.count("cascade", await cascade(ctx, item))
            extinct += 1
            continue
        set_stats(item, abundance=clamp_int(value, 0, 100))
        warnings = await track_endangered(ctx, item, marks, warnings)
    ctx.count("extinct", extinct)
    await ctx.session.flush()


async def set_abundance(ctx: TickContext, species_id: int, value: int) -> EntityRow:
    species = await living_entity(ctx.session, species_id)
    if species is None or species.entity_type is not EntityType.SPECIES:
        raise ValidationFailedError("Only a living species has an abundance.")
    set_stats(species, abundance=clamp_int(value, 0, 100))
    rows = list(await ctx.session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.species_entity_id == species.id)))
    for row in rows:
        row.abundance = clamp_int(value, 0, 100)
    if abundance(species) >= ctx.rules.ecology.critical:
        await remove_flag(ctx.session, species.id, EntityFlag.ENDANGERED)
    await record(ctx, "ecology.abundance_set", roles={IncidentRole.SUBJECT: species.id}, facts={"abundance": abundance(species)})
    return species


PHASES = (Phase("ecology", ecology),)
