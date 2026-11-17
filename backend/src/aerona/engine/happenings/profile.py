from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.happenings import EventCasualtyRow, EventFootprintRow, EventProfileRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
from aerona.domain.enums.entity import LOCATION_TYPES, SOCIETY_TYPES, EngineKind, EntityType
from aerona.domain.enums.happening import EventPhase
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import SiegeStatus
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import CohortKey, cohorts_of, combat_weights, place, pyramid, sex_spec, sexes, weights_for
from aerona.engine.environment.seasons import DRY, WET
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import apportion, clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.records import RecordSpec, create_record

MULTI_SEASON = frozenset({EngineKind.FAMINE, EngineKind.PLAGUE, EngineKind.SIEGE})
KIND_RAIN: Mapping[EngineKind, int] = {
    EngineKind.FLOOD: WET,
    EngineKind.STORM: WET,
    EngineKind.PLAGUE: WET,
    EngineKind.DROUGHT: DRY,
    EngineKind.FIRE: DRY,
    EngineKind.FAMINE: DRY,
    EngineKind.FESTIVAL_OF_NOTE: DRY,
    EngineKind.WEDDING: DRY,
    EngineKind.SIEGE: DRY,
    EngineKind.BATTLE: DRY,
}
KIND_FLOW: Mapping[EngineKind, FlowCategory] = {
    EngineKind.PLAGUE: FlowCategory.PLAGUE,
    EngineKind.FAMINE: FlowCategory.FAMINE,
    EngineKind.DROUGHT: FlowCategory.FAMINE,
    EngineKind.SIEGE: FlowCategory.FAMINE,
    EngineKind.BATTLE: FlowCategory.CASUALTY,
    EngineKind.MASSACRE: FlowCategory.CASUALTY,
    EngineKind.SACK: FlowCategory.CASUALTY,
    EngineKind.RIOT: FlowCategory.CASUALTY,
}
FALLBACK_CLASS = SocialClass.FARMER


def flow_of(kind: EngineKind | None) -> FlowCategory:
    return KIND_FLOW.get(kind, FlowCategory.DISASTER) if kind is not None else FlowCategory.DISASTER


def year_at(ctx: TickContext, epoch: int, stream: str) -> int:
    years = ctx.rules.time.years_per_epoch
    return epoch_start_year(max(1, epoch), years) + ctx.rng(stream).die(years) - 1


async def seasons_of(session: AsyncSession, world_id: int | None) -> list[WorldSeasonRow]:
    if world_id is None:
        return []
    return list(await session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id).order_by(WorldSeasonRow.position)))


def rain_sign(season: WorldSeasonRow) -> int:
    return WET if season.rain_shift > 0 else DRY if season.rain_shift < 0 else 0


async def season_for(ctx: TickContext, world_id: int | None, kind: EngineKind | None, stream: str) -> int | None:
    seasons = await seasons_of(ctx.session, world_id)
    if not seasons:
        return None
    wanted = KIND_RAIN.get(kind) if kind is not None else None
    match = ctx.rules.events.season_match_weight
    weights = [float(match) if wanted is not None and rain_sign(season) == wanted else 1.0 for season in seasons]
    return ctx.rng(stream).weighted(seasons, weights).position


async def region_of(session: AsyncSession, atlas: RegionAtlas, entity_id: int | None) -> int | None:
    if entity_id is None:
        return None
    found = atlas.top_region(entity_id)
    if found is not None:
        return found
    row = await session.get(EntityRow, entity_id)
    return row.id if row is not None and row.entity_type is EntityType.REGION else None


async def add_footprint(session: AsyncSession, event_id: int, region_id: int | None, epoch: int) -> bool:
    if region_id is None or await session.get(EventFootprintRow, (event_id, region_id)) is not None:
        return False
    session.add(EventFootprintRow(event_entity_id=event_id, region_entity_id=region_id, joined_epoch=max(0, epoch)))
    await session.flush()
    return True


async def footprint_of(session: AsyncSession, event_id: int) -> list[int]:
    rows = await session.scalars(
        select(EventFootprintRow.region_entity_id).where(EventFootprintRow.event_entity_id == event_id).order_by(EventFootprintRow.region_entity_id)
    )
    return list(rows)


async def derive_footprint(session: AsyncSession, atlas: RegionAtlas, event: EntityRow, epoch: int) -> int:
    regions = {await region_of(session, atlas, event.location_id)}
    for bond in await active_bonds(session, [BondKind.CAUSED], sources=[event.id]):
        regions.add(await region_of(session, atlas, bond.target_node_id))
    added = 0
    for region_id in sorted(region for region in regions if region is not None):
        added += int(await add_footprint(session, event.id, region_id, epoch))
    return added


def cohort_split(rows: Mapping[CohortKey, CohortRow], category: FlowCategory, amount: int, combat: Mapping[Sex, float]) -> dict[CohortKey, int]:
    if amount <= 0:
        return {}
    copies = {
        key: CohortRow(
            community_entity_id=row.community_entity_id,
            age_band=row.age_band,
            sex=row.sex,
            social_class=row.social_class,
            condition=row.condition,
            count=row.count,
            generation_epoch=row.generation_epoch,
        )
        for key, row in rows.items()
    }
    if sum(row.count for row in copies.values()) <= 0:
        return {}
    before = {key: row.count for key, row in copies.items()}
    place(copies, weights_for(copies, category, combat=combat), amount, add=False)
    return {key: before[key] - row.count for key, row in copies.items() if before[key] > row.count}


def even_split(amount: int, ages: Mapping[AgeBand, float], kinds: Mapping[Sex, float]) -> dict[CohortKey, int]:
    shares = {(age, sex, FALLBACK_CLASS, CohortCondition.NONE): age_share * sex_share for age, age_share in ages.items() for sex, sex_share in kinds.items()}
    total = sum(shares.values()) or 1.0
    ordered = sorted(shares.items(), key=lambda item: (-item[1], item[0][0].value, item[0][1].value))
    return {key: part for key, part in apportion(amount, {key: share / total for key, share in ordered}).items() if part > 0}


async def record_casualties(ctx: TickContext, event_id: int, community: EntityRow, dead: int, *, category: FlowCategory, phase: EventPhase) -> int:
    if dead <= 0 or community.entity_type not in SOCIETY_TYPES:
        return 0
    rows = await cohorts_of(ctx.session, community.id)
    combat = await combat_weights(ctx.session, community)
    split = cohort_split(rows, category, dead, combat) or even_split(dead, pyramid(ctx.rules), sexes(ctx.rules, await sex_spec(ctx.session, community)))
    counted = {
        (row.event_entity_id, row.community_entity_id, row.age_band, row.sex, row.social_class, row.phase): row
        for row in await ctx.session.scalars(
            select(EventCasualtyRow).where(
                EventCasualtyRow.event_entity_id == event_id, EventCasualtyRow.community_entity_id == community.id, EventCasualtyRow.phase == phase
            )
        )
    }
    for (age, sex, social_class, _), count in sorted(split.items(), key=lambda item: tuple(part.value for part in item[0])):
        key = (event_id, community.id, age, sex, social_class, phase)
        row = counted.get(key)
        if row is None:
            counted[key] = EventCasualtyRow(
                event_entity_id=event_id, community_entity_id=community.id, age_band=age, sex=sex, social_class=social_class, phase=phase, count=count
            )
            ctx.session.add(counted[key])
        else:
            row.count += count
    await ctx.session.flush()
    return dead


async def casualties_of(session: AsyncSession, event_id: int) -> list[EventCasualtyRow]:
    statement = select(EventCasualtyRow).where(EventCasualtyRow.event_entity_id == event_id)
    return list(await session.scalars(statement.order_by(EventCasualtyRow.community_entity_id, EventCasualtyRow.age_band, EventCasualtyRow.sex)))


async def toll_of(session: AsyncSession, event_id: int) -> int:
    return sum(row.count for row in await casualties_of(session, event_id))


async def first_incident(session: AsyncSession, event: EntityRow) -> IncidentRow | None:
    statement = (
        select(IncidentRow)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentParticipantRow.node_id == event.id, IncidentRow.epoch >= event.birth_epoch)
        .order_by(IncidentRow.epoch, IncidentRow.id)
        .limit(1)
    )
    found: IncidentRow | None = await session.scalar(statement)
    return found


async def siege_for(session: AsyncSession, event: EntityRow) -> SiegeRow | None:
    if event.engine_kind is not EngineKind.SIEGE or event.location_id is None:
        return None
    statement = (
        select(SiegeRow)
        .where(SiegeRow.besieged_entity_id == event.location_id, SiegeRow.started_epoch <= event.birth_epoch)
        .order_by((SiegeRow.status == SiegeStatus.ONGOING).desc(), SiegeRow.started_epoch.desc(), SiegeRow.id.desc())
        .limit(1)
    )
    found: SiegeRow | None = await session.scalar(statement)
    return found


async def open_profile(ctx: TickContext, event: EntityRow, *, incident_id: int | None = None, phase: EventPhase = EventPhase.ONSET) -> EventProfileRow:
    found = await ctx.session.get(EventProfileRow, event.id)
    if found is not None:
        return found
    start = max(0, event.birth_epoch)
    incident = await ctx.session.get(IncidentRow, incident_id) if incident_id is not None else await first_incident(ctx.session, event)
    year = incident.year if incident is not None and incident.year is not None else year_at(ctx, start, f"event_year.{event.id}")
    siege = await siege_for(ctx.session, event)
    row = EventProfileRow(
        entity_id=event.id,
        world_id=event.world_id,
        start_epoch=start,
        start_year=max(0, year),
        start_season=await season_for(ctx, event.world_id, event.engine_kind, f"event_season.{event.id}"),
        end_epoch=None,
        end_year=None,
        end_season=None,
        phase=phase,
        phase_epoch=start,
        incident_id=incident.id if incident is not None else None,
        siege_id=siege.id if siege is not None else None,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def close_profile(ctx: TickContext, profile: EventProfileRow) -> None:
    profile.phase = EventPhase.AFTERMATH
    profile.end_epoch = max(profile.start_epoch, ctx.epoch)
    end_year = year_at(ctx, profile.end_epoch, f"event_end.{profile.entity_id}") if profile.end_epoch > profile.start_epoch else profile.start_year
    profile.end_year = max(profile.start_year or 0, end_year or 0)
    profile.end_season = await season_for(ctx, profile.world_id, None, f"event_end_season.{profile.entity_id}")


@dataclass(frozen=True)
class Happening:
    kind: EngineKind
    name: str
    body: str
    text: str
    where: EntityRow
    severity: int
    participants: Mapping[int, IncidentRole] = field(default_factory=dict)
    regions: Sequence[int] = ()
    feed: FeedCategory = FeedCategory.WORLD
    chronicle: ChronicleKind = ChronicleKind.WORLD


async def happen(
    ctx: TickContext, happening: Happening, atlas: RegionAtlas | None = None, *, incident_id: int | None = None
) -> tuple[EntityRow, EventProfileRow]:
    atlas = atlas or await RegionAtlas.load(ctx.session)
    where = happening.where
    event = await create_record(
        ctx,
        RecordSpec(
            name=happening.name[:1].upper() + happening.name[1:],
            entity_type=EntityType.EVENT,
            stats=EventStats(severity=clamp_int(happening.severity, 0, PERCENT)),
            body=happening.body,
            power=ctx.rules.events.event_power,
            world_id=where.world_id,
            location_id=where.id if where.entity_type in LOCATION_TYPES else where.location_id,
            subtype=happening.kind.value.replace("_", " "),
            engine_kind=happening.kind,
        ),
    )
    roles = {event.id: IncidentRole.SUBJECT, **happening.participants}
    if happening.text:
        written = await ctx.chronicle(
            happening.chronicle,
            happening.text,
            template_key=f"event.{happening.kind.value}",
            entity_ids=list(roles),
            world_id=where.world_id,
            feed_category=happening.feed,
            place_entity_id=where.id if where.entity_type in LOCATION_TYPES else None,
            magnitude=clamp_int(happening.severity, 0, PERCENT),
            roles=roles,
        )
        incident_id = written.incident_id
    elif incident_id is not None and await ctx.session.get(IncidentRow, incident_id) is not None:
        ctx.session.add(IncidentParticipantRow(incident_id=incident_id, node_id=event.id, role=IncidentRole.SUBJECT, position=0))
    profile = await open_profile(ctx, event, incident_id=incident_id)
    for region_id in {await region_of(ctx.session, atlas, where.id), *happening.regions}:
        await add_footprint(ctx.session, event.id, region_id, ctx.epoch)
    return event, profile
