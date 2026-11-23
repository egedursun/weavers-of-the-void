from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.biology import BIOLOGY_VARIANTS
from aerona.constants.units import PERCENT
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.variants import variants_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term

TEN = 10
DRY = 25
PARCHED = frozenset({TemperatureBand.HOT, TemperatureBand.SEARING})


@dataclass
class VariantTally:
    budded: int = 0
    wilted: int = 0
    starved: int = 0
    partners: int = 0
    partners_lost: int = 0


async def lands_of(ctx: TickContext, atlas: RegionAtlas, people_id: int) -> list[int]:
    return sorted({region for town in await towns_of_people(ctx.session, people_id) if (region := atlas.top_region(town)) is not None})


def resize(ctx: TickContext, people: EntityRow, share: float, key: str) -> int:
    floor, cap = headcount_bounds(ctx.rules, people)
    before = stat_or(people, "population", 0)
    after = clamp_int(round_half_up(before * (1 + share)), floor, cap)
    if after != before:
        with explaining():
            term(key, after - before, source_node_id=people.id)
            set_stats(people, population=after)
    return after - before


async def bud(ctx: TickContext, people: EntityRow, tally: VariantTally) -> None:
    grown = resize(ctx, people, ctx.rules.biology.colonial_bud_rate / PERCENT, "biology.colonial_bud_rate")
    if grown > 0:
        tally.budded += 1
        await record(ctx, "people.budded", roles={IncidentRole.SUBJECT: people.id}, facts={"grown": grown})


async def wilt(ctx: TickContext, people: EntityRow, lands: list[int], tally: VariantTally) -> None:
    grounds = list(await ctx.session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.entity_id.in_(lands))))
    parched = [ground for ground in grounds if ground.temperature_band in PARCHED and ground.rainfall <= DRY]
    if not grounds or not parched:
        return
    harm = (ctx.rules.biology.fungal_fire_harm_pct - PERCENT) / PERCENT * len(parched) / len(grounds) / TEN
    if harm > 0 and resize(ctx, people, -harm, "biology.fungal_fire_harm_pct") < 0:
        tally.wilted += 1


async def feed_on_sources(ctx: TickContext, people: EntityRow, lands: list[int], tally: VariantTally) -> None:
    strength = await ctx.session.scalar(select(func.max(RegionEnvironmentRow.magic_density)).where(RegionEnvironmentRow.entity_id.in_(lands))) or 0
    need = ctx.rules.biology.energy_source_need
    if strength >= need:
        return
    if resize(ctx, people, -(need - strength) / PERCENT / TEN, "biology.energy_source_need") < 0:
        tally.starved += 1


async def partner_in(ctx: TickContext, people: EntityRow, lands: list[int]) -> int | None:
    found = await ctx.session.scalar(
        select(SpeciesRangeRow.species_entity_id)
        .where(SpeciesRangeRow.region_entity_id.in_(lands), SpeciesRangeRow.abundance > 0, SpeciesRangeRow.species_entity_id != people.id)
        .group_by(SpeciesRangeRow.species_entity_id)
        .order_by(func.sum(SpeciesRangeRow.abundance).desc(), SpeciesRangeRow.species_entity_id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def live_with_partner(ctx: TickContext, people: EntityRow, row: BiologyRow, lands: list[int], tally: VariantTally) -> None:
    table = ctx.rules.biology
    partner = await ctx.session.get(EntityRow, row.partner_species_id) if row.partner_species_id is not None else None
    if partner is not None and partner.status is not EntityStatus.CANON:
        lost = resize(ctx, people, -table.symbiotic_partner_need / PERCENT, "biology.symbiotic_partner_need")
        await record(ctx, "people.partner_lost", roles={IncidentRole.SUBJECT: people.id, IncidentRole.TARGET: partner.id}, facts={"lost": -lost})
        tally.partners_lost += 1
        if "partner_species_id" not in row.locked:
            row.partner_species_id = None
        return
    if partner is None:
        if "partner_species_id" not in row.locked:
            row.partner_species_id = await partner_in(ctx, people, lands)
            tally.partners += row.partner_species_id is not None
        return
    abundance = (
        await ctx.session.scalar(
            select(func.max(SpeciesRangeRow.abundance)).where(SpeciesRangeRow.species_entity_id == partner.id, SpeciesRangeRow.region_entity_id.in_(lands))
        )
        or 0
    )
    if abundance < table.symbiotic_partner_need:
        resize(ctx, people, -(table.symbiotic_partner_need - abundance) / PERCENT / TEN, "biology.symbiotic_partner_need")


async def keep_variant_ways(ctx: TickContext) -> VariantTally:
    tally = VariantTally()
    atlas = await RegionAtlas.load(ctx.session)
    rows = await ctx.session.execute(
        select(BiologyRow, EntityRow)
        .join(EntityRow, EntityRow.id == BiologyRow.holder_entity_id)
        .where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON)
        .order_by(BiologyRow.holder_entity_id)
    )
    for row, people in list(rows):
        if held(people.id):
            continue
        specs = [BIOLOGY_VARIANTS[variant] for variant in variants_of(row.variants)]
        if not any(spec.buds or spec.burns or spec.needs_source or spec.needs_partner for spec in specs):
            continue
        lands = await lands_of(ctx, atlas, people.id)
        if any(spec.buds for spec in specs):
            await bud(ctx, people, tally)
        if any(spec.burns for spec in specs):
            await wilt(ctx, people, lands, tally)
        if any(spec.needs_source for spec in specs):
            await feed_on_sources(ctx, people, lands, tally)
        if any(spec.needs_partner for spec in specs):
            await live_with_partner(ctx, people, row, lands, tally)
    await ctx.session.flush()
    return tally
