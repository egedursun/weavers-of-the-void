from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.evolution import NEUTRAL, lean, seeded_trait, size_from
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import LineageMarkRow, SpeciesTraitRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.evolution import EvolvedTrait
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.ecology.history import record_species
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

E = EvolvedTrait
Evolved = dict[EvolvedTrait, int]
PREY_TRAITS = (E.SPEED, E.CAMOUFLAGE)
WARMER = -1
MAX_VARIANCE = 50
BASE_VARIANCE = 10


@dataclass
class EvolutionTally:
    seeded: int = 0
    moved: int = 0


async def evolved_traits(session: AsyncSession) -> dict[tuple[int, int], Evolved]:
    found: dict[tuple[int, int], Evolved] = defaultdict(dict)
    for row in await session.scalars(select(SpeciesTraitRow)):
        found[(row.species_entity_id, row.region_entity_id)][row.trait] = row.mean
    return found


def escape(rules: Rules, evolved: Evolved) -> float:
    hidden = sum(lean(evolved.get(trait)) for trait in PREY_TRAITS) / len(PREY_TRAITS)
    return 1 - max(0.0, hidden) * rules.trait_evolution.escape_pct / PERCENT


def wary(rules: Rules, evolved: Evolved) -> float:
    return 1 - max(0.0, lean(evolved.get(E.WARINESS))) * rules.trait_evolution.wariness_pct / PERCENT


def fecund(rules: Rules, evolved: Evolved) -> float:
    return 1 + lean(evolved.get(E.FECUNDITY)) * rules.trait_evolution.fecundity_pct / PERCENT


def cold_reach(rules: Rules, evolved: Evolved) -> float:
    return max(0.0, lean(evolved.get(E.COLD_TOLERANCE))) * rules.trait_evolution.cold_reach


def heat_reach(rules: Rules, evolved: Evolved) -> float:
    return max(0.0, lean(evolved.get(E.HEAT_TOLERANCE))) * rules.trait_evolution.heat_reach


def drought_reach(rules: Rules, evolved: Evolved) -> float:
    return max(0.0, lean(evolved.get(E.DROUGHT_TOLERANCE))) * rules.trait_evolution.drought_reach


def alert(rules: Rules, evolved: Evolved) -> float:
    return 1 - max(0.0, lean(evolved.get(E.KEEN_SENSES))) * rules.trait_evolution.senses_pct / PERCENT


async def seed_traits(session: AsyncSession, species: EntityRow, profile: SpeciesProfileRow, region_id: int, epoch: int) -> list[SpeciesTraitRow]:
    marks = await traits_of(session, species.id)
    rows = [
        SpeciesTraitRow(
            species_entity_id=species.id,
            region_entity_id=region_id,
            trait=trait,
            mean=seeded_trait(
                trait,
                size=profile.size_class,
                traits=marks,
                cold_floor=profile.temperature_min,
                intelligence=stat_or(species, "intelligence", NEUTRAL),
                litter=profile.litter_size,
                fear=profile.fear_of_people,
                heat_ceiling=profile.temperature_max,
                water_need=profile.water_need,
            ),
            variance=BASE_VARIANCE,
            updated_epoch=epoch,
            locked=[],
        )
        for trait in EvolvedTrait
    ]
    session.add_all(rows)
    return rows


def pull(row: SpeciesTraitRow, step: float, noise: float, epoch: int) -> bool:
    if "mean" in row.locked:
        return False
    before = row.mean
    row.mean = clamp_int(round_half_up(row.mean + step + noise), 0, PERCENT)
    row.updated_epoch = epoch
    return row.mean != before


async def hunters_of(session: AsyncSession) -> dict[int, set[int]]:
    found: dict[int, set[int]] = defaultdict(set)
    for hunter, prey in await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.HUNTS, BondRow.state == BondState.ACTIVE)
    ):
        found[prey].add(hunter)
    return found


def climate_push(profile: SpeciesProfileRow, land: RegionEnvironmentRow | None) -> int:
    if land is None:
        return 0
    if land.temperature < profile.temperature_min:
        return 1
    if land.temperature > profile.temperature_max:
        return -1
    return 0


@dataclass
class Selection:
    stored: dict[tuple[int, int], dict[EvolvedTrait, SpeciesTraitRow]]
    hunted_by: dict[int, set[int]]
    present: set[tuple[int, int]]


def pressures(
    rules: Rules, selection: Selection, row: SpeciesRangeRow, profile: SpeciesProfileRow, land: RegionEnvironmentRow | None
) -> dict[EvolvedTrait, float]:
    table = rules.trait_evolution
    region = row.region_entity_id
    steps: dict[EvolvedTrait, float] = defaultdict(float)
    if any((hunter, region) in selection.present for hunter in selection.hunted_by.get(row.species_entity_id, set())):
        for trait in PREY_TRAITS:
            steps[trait] += table.predator_pressure
        steps[E.KEEN_SENSES] += table.predator_pressure
    prey_speeds = [
        selection.stored[(prey, region)][E.SPEED].mean
        for prey, hunters in selection.hunted_by.items()
        if row.species_entity_id in hunters and E.SPEED in selection.stored.get((prey, region), {})
    ]
    own = selection.stored[(row.species_entity_id, region)].get(E.SPEED)
    if prey_speeds and own is not None:
        steps[E.SPEED] += table.arms_race if sum(prey_speeds) / len(prey_speeds) > own.mean else -table.arms_race
    push = climate_push(profile, land)
    steps[E.COLD_TOLERANCE] += push * table.climate_pressure
    steps[E.HEAT_TOLERANCE] += table.climate_pressure if push == WARMER else 0
    if land is not None and land.moisture < profile.water_need:
        steps[E.DROUGHT_TOLERANCE] += table.drought_pressure
    if row.hunted > 0:
        steps[E.WARINESS] += table.hunting_pressure
        steps[E.SIZE] -= table.hunting_pressure
    spared = 1 - table.protection_relax_pct / PERCENT if profile.sacred_to_node_id is not None else 1.0
    return {trait: step * spared for trait, step in steps.items()}


def spread_out(rules: Rules, item: SpeciesTraitRow, leak: float) -> None:
    if "variance" in item.locked:
        return
    if leak > 0:
        item.variance = clamp_int(round_half_up(item.variance + leak * rules.trait_evolution.leak_variance), 0, MAX_VARIANCE)
    elif item.variance > BASE_VARIANCE:
        item.variance -= 1


async def evolve_traits(ctx: TickContext, tally: EvolutionTally) -> None:
    profiles = {row.species_entity_id: row for row in await ctx.session.scalars(select(SpeciesProfileRow))}
    lands = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    stored: dict[tuple[int, int], dict[EvolvedTrait, SpeciesTraitRow]] = defaultdict(dict)
    for item in await ctx.session.scalars(select(SpeciesTraitRow)):
        stored[(item.species_entity_id, item.region_entity_id)][item.trait] = item
    ranges = list(
        await ctx.session.scalars(
            select(SpeciesRangeRow).where(SpeciesRangeRow.abundance > 0).order_by(SpeciesRangeRow.species_entity_id, SpeciesRangeRow.region_entity_id)
        )
    )
    selection = Selection(stored, await hunters_of(ctx.session), {(row.species_entity_id, row.region_entity_id) for row in ranges})
    for row in ranges:
        key = (row.species_entity_id, row.region_entity_id)
        profile = profiles.get(row.species_entity_id)
        if profile is None or held(*key):
            continue
        if not stored[key]:
            species = await ctx.session.get(EntityRow, row.species_entity_id)
            if species is not None:
                stored[key] = {item.trait: item for item in await seed_traits(ctx.session, species, profile, row.region_entity_id, ctx.epoch)}
                tally.seeded += 1
            continue
        land = lands.get(row.region_entity_id)
        steps = pressures(ctx.rules, selection, row, profile, land)
        leak = land.leak / PERCENT if land is not None else 0.0
        rng = ctx.rng(f"traits.{row.species_entity_id}.{row.region_entity_id}")
        for trait, item in sorted(stored[key].items()):
            spread_out(ctx.rules, item, leak)
            if pull(item, steps.get(trait, 0.0), (rng.random() * 2 - 1) * item.variance / 10, ctx.epoch):
                tally.moved += 1
    await record_species(ctx, [item for traits in stored.values() for item in traits.values()])


def distance(first: Evolved, second: Evolved) -> int:
    shared = set(first) & set(second)
    if not shared:
        return 0
    return round_half_up(sum(abs(first[trait] - second[trait]) for trait in shared) / len(shared))


async def apart(session: AsyncSession, rules: Rules, species_id: int, region_id: int) -> bool:
    rows = list(await session.scalars(select(SpeciesTraitRow).where(SpeciesTraitRow.species_entity_id == species_id)))
    here: Evolved = {row.trait: row.mean for row in rows if row.region_entity_id == region_id}
    elsewhere: dict[EvolvedTrait, list[int]] = defaultdict(list)
    for row in rows:
        if row.region_entity_id != region_id:
            elsewhere[row.trait].append(row.mean)
    rest = {trait: round_half_up(sum(values) / len(values)) for trait, values in elsewhere.items()}
    return bool(here) and bool(rest) and distance(here, rest) >= rules.trait_evolution.speciation_distance


async def settle_size(session: AsyncSession, species_id: int, region_id: int) -> None:
    size = await session.get(SpeciesTraitRow, (species_id, region_id, E.SIZE))
    profile = await session.get(SpeciesProfileRow, species_id)
    if size is not None and profile is not None and "size_class" not in profile.locked:
        profile.size_class = size_from(size.mean)


async def inherit_traits(session: AsyncSession, parent_id: int, child_id: int, region_id: int, epoch: int) -> int:
    rows = list(
        await session.scalars(select(SpeciesTraitRow).where(SpeciesTraitRow.species_entity_id == parent_id, SpeciesTraitRow.region_entity_id == region_id))
    )
    for row in rows:
        await session.merge(
            SpeciesTraitRow(
                species_entity_id=child_id,
                region_entity_id=region_id,
                trait=row.trait,
                mean=row.mean,
                variance=row.variance,
                updated_epoch=epoch,
                locked=[],
            )
        )
    await inherit_marks(session, parent_id, child_id, epoch)
    return len(rows)


async def inherit_marks(session: AsyncSession, parent_id: int, child_id: int, epoch: int) -> int:
    marks = list(await session.scalars(select(LineageMarkRow).where(LineageMarkRow.species_entity_id == parent_id)))
    for mark in marks:
        await session.merge(
            LineageMarkRow(
                species_entity_id=child_id,
                package=mark.package,
                blessing=mark.blessing,
                source_node_id=mark.source_node_id,
                epoch=epoch,
                locked=[],
            )
        )
    return len(marks)
