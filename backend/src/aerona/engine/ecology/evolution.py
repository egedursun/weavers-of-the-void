from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.domestication import KEPT_STAGES
from aerona.catalog.evolution import NEUTRAL, PREY_TRAITS, lean, seeded_trait, size_from
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.disease import DiseaseProfileRow, OutbreakRow
from aerona.db.tables.disease_agents import DiseaseAgentRow
from aerona.db.tables.ecology import HerdRow, SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.evolution import LineageMarkRow, SpeciesTraitRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.evolution import EvolvedTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.ecology.history import record_species
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term
from aerona.rules.registry import Rules

E = EvolvedTrait
Evolved = dict[EvolvedTrait, int]
WARMER = -1
MAX_VARIANCE = 50
BASE_VARIANCE = 10

SHIFT_BAND = 25


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


async def seed_traits(
    session: AsyncSession, species: EntityRow, profile: SpeciesProfileRow, region_id: int, epoch: int, *, have: frozenset[EvolvedTrait] = frozenset()
) -> list[SpeciesTraitRow]:
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
                tameability=profile.tameability,
                stage=profile.stage,
                lifespan=profile.lifespan_years,
            ),
            variance=BASE_VARIANCE,
            updated_epoch=epoch,
            locked=[],
        )
        for trait in EvolvedTrait
        if trait not in have
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


async def stricken_kinds(session: AsyncSession) -> set[tuple[int, int]]:
    statement = (
        select(DiseaseAgentRow.reservoir_species_id, OutbreakRow.region_entity_id)
        .join(OutbreakRow, OutbreakRow.disease_entity_id == DiseaseAgentRow.disease_entity_id)
        .where(DiseaseAgentRow.reservoir_species_id.is_not(None), OutbreakRow.status == OutbreakStatus.ACTIVE, OutbreakRow.dead > 0)
    )
    return {(species, region) for species, region in await session.execute(statement) if species is not None}


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
    stricken: set[tuple[int, int]] = field(default_factory=set)
    kept: set[int] = field(default_factory=set)


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
    if (row.species_entity_id, region) in selection.stricken:
        steps[E.DISEASE_RESISTANCE] += table.resistance_gain
    tamed = profile.stage in KEPT_STAGES or row.species_entity_id in selection.kept
    steps[E.DOCILITY] += table.docility_keep_gain if tamed else -table.docility_wild_loss
    preyed = any((hunter, region) in selection.present for hunter in selection.hunted_by.get(row.species_entity_id, set()))
    steps[E.LONGEVITY] += -table.predator_pressure * table.longevity_predation_pct / PERCENT * 2 if preyed else table.predator_pressure / 2
    steps[E.STRENGTH] += table.strength_pressure if tamed else -table.strength_pressure / 2
    steps[E.PARENTAL_CARE] += table.parental_care_pressure if preyed else -table.parental_care_pressure / 2
    steps[E.SOCIAL_LEARNING] += table.social_learning_pressure if row.hunted > 0 else 0
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
    before = averaged(stored)
    selection = Selection(
        stored,
        await hunters_of(ctx.session),
        {(row.species_entity_id, row.region_entity_id) for row in ranges},
        await stricken_kinds(ctx.session),
        set(await ctx.session.scalars(select(HerdRow.species_entity_id).where(HerdRow.head > 0))),
    )
    for row in ranges:
        key = (row.species_entity_id, row.region_entity_id)
        profile = profiles.get(row.species_entity_id)
        if profile is None or held(*key):
            continue
        if len(stored[key]) < len(EvolvedTrait):
            fresh = not stored[key]
            species = await ctx.session.get(EntityRow, row.species_entity_id)
            if species is not None:
                added = await seed_traits(ctx.session, species, profile, row.region_entity_id, ctx.epoch, have=frozenset(stored[key]))
                stored[key] |= {item.trait: item for item in added}
                tally.seeded += 1
            if fresh:
                continue
        land = lands.get(row.region_entity_id)
        steps = pressures(ctx.rules, selection, row, profile, land)
        leak = land.leak / PERCENT if land is not None else 0.0
        rng = ctx.rng(f"traits.{row.species_entity_id}.{row.region_entity_id}")
        for trait, item in sorted(stored[key].items()):
            spread_out(ctx.rules, item, leak)
            if pull(item, steps.get(trait, 0.0), (rng.random() * 2 - 1) * item.variance / 10, ctx.epoch):
                tally.moved += 1
    after = averaged(stored)
    await tell_shifts(ctx, before, after)
    await live_traits(ctx, after, profiles)
    await record_species(ctx, [item for traits in stored.values() for item in traits.values()])


def averaged(stored: dict[tuple[int, int], dict[EvolvedTrait, SpeciesTraitRow]]) -> dict[tuple[int, EvolvedTrait], int]:
    means: dict[tuple[int, EvolvedTrait], list[int]] = defaultdict(list)
    for (species_id, _region_id), traits in stored.items():
        for trait, item in traits.items():
            means[(species_id, trait)].append(item.mean)
    return {key: round_half_up(sum(values) / len(values)) for key, values in means.items()}


async def tell_shifts(ctx: TickContext, before: dict[tuple[int, EvolvedTrait], int], after: dict[tuple[int, EvolvedTrait], int]) -> None:
    for (species_id, trait), mean in sorted(after.items()):
        was = before.get((species_id, trait))
        if was is None or was // SHIFT_BAND == mean // SHIFT_BAND or held(species_id):
            continue
        await record(ctx, "life.trait_shifted", roles={IncidentRole.SUBJECT: species_id}, facts={"trait": trait, "mean": mean, "before": was})


async def live_traits(ctx: TickContext, means: dict[tuple[int, EvolvedTrait], int], profiles: dict[int, SpeciesProfileRow]) -> None:
    table = ctx.rules.trait_evolution
    for species_id, profile in sorted(profiles.items()):
        longevity = means.get((species_id, EvolvedTrait.LONGEVITY))
        if longevity is None or held(species_id) or "lifespan_years" in (profile.locked or []):
            continue
        step = 1 if longevity > NEUTRAL + SHIFT_BAND // 2 else -1 if longevity < NEUTRAL - SHIFT_BAND // 2 else 0
        if step:
            with explaining():
                term("trait_evolution.longevity_mean", longevity, source_node_id=species_id)
                profile.lifespan_years = max(1, profile.lifespan_years + step)
    await raise_young(ctx, means, profiles)
    resistant = {species_id for (species_id, trait), mean in means.items() if trait is EvolvedTrait.DISEASE_RESISTANCE and mean > NEUTRAL}
    if not resistant:
        return
    agents = await ctx.session.scalars(
        select(DiseaseAgentRow).where(DiseaseAgentRow.reservoir_species_id.in_(sorted(resistant))).order_by(DiseaseAgentRow.disease_entity_id)
    )
    for agent in agents:
        disease = await ctx.session.get(DiseaseProfileRow, agent.disease_entity_id)
        if disease is not None and not held(disease.disease_entity_id) and "virulence" not in (disease.locked or []):
            disease.virulence = clamp_int(disease.virulence + table.virulence_answer, 1, PERCENT)


async def raise_young(ctx: TickContext, means: dict[tuple[int, EvolvedTrait], int], profiles: dict[int, SpeciesProfileRow]) -> None:
    high = NEUTRAL + SHIFT_BAND // 2
    for species_id, profile in sorted(profiles.items()):
        if held(species_id):
            continue
        locked = profile.locked or []
        care = means.get((species_id, EvolvedTrait.PARENTAL_CARE), 0)
        if care > high and "litter_size" not in locked and profile.litter_size > 1:
            with explaining():
                term("trait_evolution.parental_care_mean", care, source_node_id=species_id)
                profile.litter_size -= 1
        learning = means.get((species_id, EvolvedTrait.SOCIAL_LEARNING), 0)
        if learning > high and "fear_of_people" not in locked:
            with explaining():
                term("trait_evolution.social_learning_mean", learning, source_node_id=species_id)
                profile.fear_of_people = clamp_int(profile.fear_of_people + 1, 0, PERCENT)
        strength = means.get((species_id, EvolvedTrait.STRENGTH), 0)
        if strength > high and "metabolism" not in locked:
            with explaining():
                term("trait_evolution.strength_mean", strength, source_node_id=species_id)
                profile.metabolism = clamp_int(profile.metabolism + 1, 0, PERCENT)


async def docility_of(session: AsyncSession, species_id: int) -> int:
    found = await session.scalar(
        select(func.avg(SpeciesTraitRow.mean)).where(SpeciesTraitRow.species_entity_id == species_id, SpeciesTraitRow.trait == EvolvedTrait.DOCILITY)
    )
    return NEUTRAL if found is None else round_half_up(float(found))


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
