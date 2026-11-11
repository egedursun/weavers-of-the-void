from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.cycles import PolityStressRow, StressReadingRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import CyclePhase
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import polities, put, realm_towns
from aerona.engine.notes import note
from aerona.engine.primitives.capacity import CapacityModel
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

LOWER = (SocialClass.FARMER, SocialClass.ARTISAN, SocialClass.SERF_OR_SLAVE, SocialClass.OUTCAST)
URBAN = frozenset({SizeTier.TOWN, SizeTier.CITY, SizeTier.METROPOLIS})


@dataclass
class StressTally:
    read: int = 0
    crises: int = 0
    counter_elites: int = 0


@dataclass(frozen=True)
class Reading:
    pressure: int
    immiseration: int
    elite_overproduction: int
    fiscal_distress: int
    aspirants: int
    positions: int


def psi(immiseration: int, elites: int, fiscal: int) -> int:
    return clamp_int(round_half_up((immiseration * elites * fiscal) ** (1 / 3)), 0, PERCENT)


def phase_of(rules: Rules, previous: CyclePhase, pressure: int, index: int) -> CyclePhase:
    table = rules.structural_demography
    if index >= table.crisis_at:
        return CyclePhase.CRISIS
    if previous in {CyclePhase.CRISIS, CyclePhase.DEPRESSION} and pressure < table.recovery_pressure:
        return CyclePhase.DEPRESSION
    if pressure >= table.stagflation_pressure:
        return CyclePhase.STAGFLATION
    return CyclePhase.GROWTH


def share(society: CommunitySocietyRow, social_class: SocialClass) -> float:
    return float(getattr(society, f"share_{social_class.value}")) / PERCENT


def satisfaction(society: CommunitySocietyRow, social_class: SocialClass) -> int:
    return int(getattr(society, f"satisfaction_{social_class.value}"))


async def youth_share(ctx: TickContext, town_ids: list[int]) -> float:
    if not town_ids:
        return 0.0
    rows = await ctx.session.execute(
        select(CohortRow.age_band, func.sum(CohortRow.count)).where(CohortRow.community_entity_id.in_(town_ids)).group_by(CohortRow.age_band)
    )
    counts = {band: int(total or 0) for band, total in rows.all()}
    whole = sum(counts.values())
    return counts.get(AgeBand.CHILD, 0) * PERCENT / whole if whole else 0.0


def realm_capacity(model: CapacityModel, towns: list[EntityRow]) -> float:
    loads = model.build_loads(towns)
    return float(sum(model.capacity(loads[model.region_key(town)], town, model.effective_fertility(town)) for town in towns))


async def read_realm(ctx: TickContext, model: CapacityModel, polity: EntityRow, profile: PolityProfileRow) -> Reading:
    table = ctx.rules.structural_demography
    towns = await realm_towns(ctx.session, polity.id)
    capacity = realm_capacity(model, towns)
    population = sum(stat_or(town, "population", 0) for town in towns)
    occupancy = population * PERCENT / max(1.0, capacity)
    span = max(1, table.pressure_full_pct - table.pressure_floor_pct)
    pressure = clamp_int((occupancy - table.pressure_floor_pct) * PERCENT / span, 0, PERCENT)
    misery_total = 0.0
    lower_people = 0.0
    aspirants = 0.0
    urban = 0
    for town in towns:
        people = stat_or(town, "population", 0)
        society = await ctx.session.get(CommunitySocietyRow, town.id)
        settled = await ctx.session.get(SettlementProfileRow, town.id)
        if settled is not None and settled.size_tier in URBAN:
            urban += people
        if society is None:
            continue
        for social_class in LOWER:
            count = people * share(society, social_class)
            lower_people += count
            misery_total += count * max(0, table.content_at - satisfaction(society, social_class)) * PERCENT / table.content_at
        aspirants += people * (
            share(society, SocialClass.NOBLE)
            + share(society, SocialClass.MERCHANT) * table.merchant_elite_pct / PERCENT
            + share(society, SocialClass.SCRIBE) * table.scribe_elite_pct / PERCENT
        )
    misery = misery_total / lower_people if lower_people else 0.0
    youth = await youth_share(ctx, [town.id for town in towns])
    youth_factor = 1 + (youth - table.youth_norm_pct) * table.youth_weight / PERCENT / PERCENT
    urban_factor = 1 + max(0.0, urban * PERCENT / max(1, population) - table.urban_norm_pct) * table.urban_weight / PERCENT / PERCENT
    immiseration = clamp_int(misery * youth_factor * urban_factor, 0, PERCENT)
    offices = int(await ctx.session.scalar(select(func.count()).select_from(OfficeRow).where(OfficeRow.polity_entity_id == polity.id)) or 0)
    titles = int(
        await ctx.session.scalar(
            select(func.count()).select_from(TitleProfileRow).where(TitleProfileRow.polity_entity_id == polity.id, TitleProfileRow.destroyed_epoch.is_(None))
        )
        or 0
    )
    positions = offices * table.positions_per_office + titles * table.positions_per_title + len(towns) * table.positions_per_town
    ratio = aspirants / max(1, positions)
    elites = clamp_int((ratio - 1) * table.overproduction_scale, 0, PERCENT)
    owed = profile.debt * PERCENT / max(1, profile.treasury + profile.debt)
    fiscal = clamp_int(
        owed * table.debt_weight / PERCENT
        + profile.corruption * table.corruption_weight / PERCENT
        + profile.war_weariness * table.weariness_weight / PERCENT
        + (table.empty_treasury if profile.treasury <= 0 else 0),
        0,
        PERCENT,
    )
    return Reading(pressure, immiseration, elites, fiscal, round_half_up(aspirants), positions)


async def stress_row(ctx: TickContext, polity_id: int) -> PolityStressRow:
    row = await ctx.session.get(PolityStressRow, polity_id)
    if row is None:
        row = PolityStressRow(polity_entity_id=polity_id, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


async def record(ctx: TickContext, row: PolityStressRow) -> None:
    reading = await ctx.session.get(StressReadingRow, (row.polity_entity_id, ctx.epoch))
    if reading is None:
        reading = StressReadingRow(polity_entity_id=row.polity_entity_id, epoch=ctx.epoch)
        ctx.session.add(reading)
    reading.pressure, reading.immiseration, reading.elite_overproduction = row.pressure, row.immiseration, row.elite_overproduction
    reading.fiscal_distress, reading.psi, reading.phase = row.fiscal_distress, row.psi, row.phase


async def aspirant_leader(ctx: TickContext, polity_id: int) -> EntityRow | None:
    holders = select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == polity_id, OfficeRow.holder_entity_id.is_not(None))
    towns = [town.id for town in await realm_towns(ctx.session, polity_id)]
    if not towns:
        return None
    return await ctx.session.scalar(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            await present_among(ctx.session, towns),
            EntityRow.social_class == SocialClass.NOBLE,
            EntityRow.id.not_in(holders),
        )
        .order_by(EntityRow.importance.desc(), EntityRow.id)
        .limit(1)
    )


async def read_stress(ctx: TickContext, tally: StressTally) -> list[tuple[EntityRow, PolityProfileRow, PolityStressRow]]:
    model = await CapacityModel.load(ctx.session, ctx.rules)
    found: list[tuple[EntityRow, PolityProfileRow, PolityStressRow]] = []
    for polity, profile in await polities(ctx.session):
        if held(polity.id):
            continue
        reading = await read_realm(ctx, model, polity, profile)
        row = await stress_row(ctx, polity.id)
        before = row.phase
        put(row, "pressure", reading.pressure)
        put(row, "immiseration", reading.immiseration)
        put(row, "elite_overproduction", reading.elite_overproduction)
        put(row, "fiscal_distress", reading.fiscal_distress)
        put(row, "aspirants", reading.aspirants, high=10**9)
        put(row, "positions", reading.positions, high=10**9)
        put(row, "psi", psi(row.immiseration, row.elite_overproduction, row.fiscal_distress))
        if "phase" not in row.locked:
            row.phase = phase_of(ctx.rules, before, row.pressure, row.psi)
        row.updated_epoch = ctx.epoch
        await record(ctx, row)
        tally.read += 1
        if row.phase is CyclePhase.CRISIS and before is not CyclePhase.CRISIS:
            tally.crises += 1
            await note(
                ctx,
                f"{polity.name} entered a crisis: its people are poor, its elites too many and its treasury strained.",
                key="stress.crisis",
                ids=[polity.id],
            )
        found.append((polity, profile, row))
    return found
