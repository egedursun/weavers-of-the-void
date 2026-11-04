from contextvars import ContextVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.disease import DiseaseProfileRow, OutbreakRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import ClimateAffinity, OutbreakStatus, SpreadPath
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.mortal import HarshnessScale
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.emergence import COLD_BANDS, DRY, WARM_BANDS, WET, new_disease
from aerona.engine.disease.vectors import Spot, crowd_weight, host_factor, sanitation_weight, vector_factor
from aerona.engine.gods.progress import cap_gained_essence
from aerona.engine.primitives.harshness import harshness
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import set_stats, stat

PLAGUE_SON_DOMAINS = frozenset({Domain.PLAGUE})
STRIKING: ContextVar[DiseaseProfileRow | None] = ContextVar("striking_disease", default=None)
FACTOR_FLOOR, FACTOR_CEILING = 0.05, 6.0
SEVERITY_LOCK = "severity"
STATUS_LOCK = "status"
INFECTED_LOCK = "infected"
DEAD_LOCK = "dead"
QUARANTINE_LOCK = "quarantined"
OUTBREAK_LOCKS = (SEVERITY_LOCK, STATUS_LOCK, INFECTED_LOCK, DEAD_LOCK, QUARANTINE_LOCK)


async def disease_for(ctx: TickContext, book: DiseaseBook, region: EntityRow, *, quiet: bool = False) -> EntityRow:
    rng = ctx.rng(f"disease.for.{region.id}")
    nearby = {region.id, *book.atlas.neighbour_regions(region.id)}
    known = sorted(
        {row.disease_entity_id for place in nearby for row in book.endemic.get(place, [])}
        | {item.disease_entity_id for item in book.outbreaks if item.region_entity_id in nearby}
        | {disease_id for disease_id, profile in book.profiles.items() if profile.origin_region_id in nearby}
    )
    known = [disease_id for disease_id in known if disease_id in book.diseases]
    if known and rng.chance(ctx.rules.epidemiology.reuse_disease_chance):
        return book.diseases[rng.pick(known)]
    return await new_disease(ctx, book, region, path=SpreadPath.ORIGIN, host=await host_for(ctx, book, region.id), quiet=quiet)


async def host_for(ctx: TickContext, book: DiseaseBook, region_id: int) -> EntityRow | None:
    bearers = set(await ctx.session.scalars(select(EntityTraitRow.entity_id).where(EntityTraitRow.trait == CreatureTrait.PLAGUE_BEARER)))
    found = sorted(
        ((abundance, species_id) for (species_id, place), abundance in book.ranges.items() if place == region_id and species_id in bearers), reverse=True
    )
    if not found:
        return None
    abundance, species_id = found[0]
    if not ctx.rng(f"disease.host.{region_id}.{len(book.diseases)}").chance(ctx.rules.epidemiology.host_emergence_pct * min(PERCENT, abundance) / PERCENT):
        return None
    return await ctx.session.get(EntityRow, species_id)


def climate_fit(rules_pct: tuple[int, int], profile: DiseaseProfileRow, ground: RegionEnvironmentRow | None) -> float:
    match, mismatch = rules_pct
    if ground is None or profile.climate_affinity is ClimateAffinity.ANY:
        return 1.0
    fits = {
        ClimateAffinity.WARM: ground.temperature_band in WARM_BANDS,
        ClimateAffinity.COLD: ground.temperature_band in COLD_BANDS,
        ClimateAffinity.WET: ground.wetland >= WET,
        ClimateAffinity.DRY: ground.rainfall <= DRY,
    }
    if fits[profile.climate_affinity]:
        return match / PERCENT
    opposed = (profile.climate_affinity is ClimateAffinity.WARM and ground.temperature_band in COLD_BANDS) or (
        profile.climate_affinity is ClimateAffinity.COLD and ground.temperature_band in WARM_BANDS | {TemperatureBand.TEMPERATE}
    )
    return mismatch / PERCENT if opposed else 1.0


def virgin(book: DiseaseBook, community: EntityRow, disease_id: int) -> bool:
    if book.met_before(community.id, disease_id):
        return False
    seen = any(key[1] == disease_id for key in book.immunity) or any(row.disease_entity_id == disease_id for rows in book.endemic.values() for row in rows)
    return seen


def lethality_factor(book: DiseaseBook, disease_id: int, communities: list[EntityRow], knowledge: KnowledgeMap) -> float:
    table = book.rules.epidemiology
    profile = book.profiles.get(disease_id)
    if profile is None:
        return 1.0
    base = profile.lethality / table.neutral_lethality
    weight = 0.0
    total = 0.0
    for community in communities:
        people = max(1, stat(community, "population") or 1)
        factor = 1 - book.immune_share(community.id, disease_id) * table.immunity_strength_pct / PERCENT
        if virgin(book, community, disease_id):
            factor *= table.virgin_soil_pct / PERCENT
        if book.cured(disease_id, community.id) or knowledge.level(community.id, KnowledgeBranch.MEDICINE) >= profile.cure_level:
            factor *= table.cure_lethality_pct / PERCENT
        ward = book.hospital_strength.get(book.atlas.top_region(community.id) or -1, 0.0)
        factor *= 1 - ward * (1 - table.hospital_lethality_pct / PERCENT)
        weight += people * factor
        total += people
    blended = weight / total if total else 1.0
    return max(FACTOR_FLOOR, min(FACTOR_CEILING, base * blended * harshness(book.rules, HarshnessScale.DISEASE_DEATH)))


def spread_factor(
    book: DiseaseBook,
    disease_id: int,
    target: EntityRow,
    ground: RegionEnvironmentRow | None,
    *,
    source_region: int | None,
    path: SpreadPath = SpreadPath.ORIGIN,
    hidden: float = 0.0,
    sealed: bool = False,
) -> float:
    table = book.rules.epidemiology
    profile = book.profiles.get(disease_id)
    if profile is None:
        return 1.0
    immune = book.immune_share(target.id, disease_id)
    if immune >= book.herd_threshold(disease_id):
        return 0.0
    region = book.atlas.top_region(target.id)
    factor = profile.virulence / table.neutral_virulence
    factor *= climate_fit((table.climate_match_pct, table.climate_mismatch_pct), profile, ground)
    factor *= 1 - immune * table.immunity_strength_pct / PERCENT
    load = ground.disease_load if ground is not None else 0
    factor *= 1 + load / PERCENT * table.load_spread_pct / PERCENT
    crowd = min(1.0, (stat(target, "population") or 0) / max(1, table.crowd_population))
    factor *= 1 + crowd * crowd_weight(book, profile)
    factor *= max(0.0, 1 - book.sanitation.get(region or -1, 0) / PERCENT * sanitation_weight(book, profile))
    factor *= vector_factor(book, profile, Spot(target, ground, region, path))
    factor *= host_factor(book, profile, region)
    if sealed or book.quarantined(region) or book.quarantined(source_region):
        held = table.quarantine_spread_pct / PERCENT
        factor *= held + (1 - held) * hidden
    factor *= 1 + hidden * table.incubation_spread_pct / PERCENT
    if target.id in book.inoculated:
        factor *= 1 - book.rules.technique_effects.inoculation_pct / PERCENT
    factor *= book.seasonal.get(region or -1, 1.0)
    return max(0.0, factor)


async def open_outbreak(
    ctx: TickContext,
    book: DiseaseBook,
    disease: EntityRow,
    region_id: int,
    *,
    path: SpreadPath,
    severity: int,
    event: EntityRow | None = None,
    source: OutbreakRow | None = None,
) -> OutbreakRow:
    found = book.active_of(disease.id, region_id)
    if found is not None:
        if SEVERITY_LOCK not in found.locked:
            found.severity = clamp_int(max(found.severity, severity), 0, PERCENT)
        if STATUS_LOCK not in found.locked:
            found.status = OutbreakStatus.ACTIVE
        if event is not None and found.event_entity_id is None:
            found.event_entity_id = event.id
        return found
    row = OutbreakRow(
        disease_entity_id=disease.id,
        region_entity_id=region_id,
        event_entity_id=event.id if event is not None else None,
        source_outbreak_id=source.id if source is not None else None,
        path=path,
        status=OutbreakStatus.ACTIVE,
        severity=clamp_int(severity, 0, PERCENT),
        infected=0,
        dead=0,
        started_epoch=ctx.epoch,
        ended_epoch=None,
        quarantined=book.quarantined(region_id),
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    book.outbreaks.append(row)
    if event is not None:
        await connect(ctx.session, disease.id, event.id, BondKind.CAUSED, ctx.epoch, description="the sickness behind it")
    await feed_gods(ctx, disease)
    ctx.count(f"outbreak.{path.value}")
    return row


def tally(disease: EntityRow, outbreak: OutbreakRow, *, infected: int, dead: int) -> None:
    if INFECTED_LOCK not in outbreak.locked:
        outbreak.infected += max(0, infected)
    if DEAD_LOCK not in outbreak.locked:
        outbreak.dead += max(0, dead)
    set_stats(disease, infected=(stat(disease, "infected") or 0) + max(0, infected), dead=(stat(disease, "dead") or 0) + max(0, dead))


async def feed_gods(ctx: TickContext, disease: EntityRow) -> None:
    table = ctx.rules.epidemiology
    sons = await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id == disease.world_id).order_by(SonRow.id))
    for son in sons:
        gain = 0
        if son.domain_primary in PLAGUE_SON_DOMAINS or son.domain_secondary in PLAGUE_SON_DOMAINS:
            gain += table.essence_per_outbreak
        if son.id == disease.creator_son_id:
            gain += table.creator_essence_per_outbreak
        if gain:
            before = son.essence
            son.essence += gain
            cap_gained_essence(ctx.rules, son, before)


async def disease_god(session: AsyncSession, plague: EntityRow) -> SonRow | None:
    outbreak = await session.scalar(select(OutbreakRow).where(OutbreakRow.event_entity_id == plague.id).order_by(OutbreakRow.id).limit(1))
    if outbreak is None:
        return None
    disease = await session.get(EntityRow, outbreak.disease_entity_id)
    if disease is None or disease.creator_son_id is None:
        return None
    return await session.get(SonRow, disease.creator_son_id)
