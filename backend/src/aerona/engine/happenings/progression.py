from collections import Counter
from collections.abc import Mapping

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.happenings import EventProfileRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.warfare import SiegeRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.happening import EventPhase
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.context import TickContext
from aerona.engine.happenings.effects import aftermath, famine_onset, peak_harm, plague_active, siege_over, siege_peaked, struck_communities
from aerona.engine.happenings.profile import (
    MULTI_SEASON,
    Happening,
    close_profile,
    derive_footprint,
    footprint_of,
    happen,
    open_profile,
    siege_for,
)
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat

PHASE_LINES: Mapping[EventPhase, str] = total(
    EventPhase,
    {
        EventPhase.ONSET: "{name} began.",
        EventPhase.PEAK: "{name} reached its height.",
        EventPhase.AFTERMATH: "{name} passed its height; its aftermath began.",
        EventPhase.MEMORY: "{name} is over and passes into memory.",
    },
)
PHASE_HOLD = "phase"


async def phase_line(ctx: TickContext, event: EntityRow, step: EventPhase) -> None:
    if event.engine_kind is None:
        return
    await ctx.chronicle(
        ChronicleKind.DISASTER if event.engine_kind is not EngineKind.SIEGE else ChronicleKind.WAR,
        PHASE_LINES[step].format(name=event.name),
        template_key=f"event.phase.{event.engine_kind.value}.{step.value}",
        entity_ids=[event.id],
        world_id=event.world_id,
        feed_category=FeedCategory.DISASTER,
        place_entity_id=event.location_id,
        roles={event.id: IncidentRole.SUBJECT},
    )


async def harvest_of(ctx: TickContext, event: EntityRow) -> int:
    harvests = [
        ground.harvest_pct
        for region_id in await footprint_of(ctx.session, event.id)
        if (ground := await ctx.session.get(RegionEnvironmentRow, region_id)) is not None
    ]
    return min(harvests, default=PERCENT)


async def famine_next(ctx: TickContext, event: EntityRow, profile: EventProfileRow) -> EventPhase:
    table = ctx.rules.events
    harvest = await harvest_of(ctx, event)
    if profile.phase is EventPhase.ONSET:
        return EventPhase.PEAK if harvest < table.famine_peak_below_harvest else EventPhase.AFTERMATH
    spent = ctx.epoch - profile.phase_epoch >= table.peak_max_epochs
    return EventPhase.AFTERMATH if harvest >= table.famine_recover_harvest or spent else EventPhase.PEAK


async def plague_next(ctx: TickContext, event: EntityRow, profile: EventProfileRow) -> EventPhase:
    active = await plague_active(ctx, event)
    if profile.phase is EventPhase.ONSET:
        return EventPhase.PEAK if active else EventPhase.AFTERMATH
    spent = ctx.epoch - profile.phase_epoch >= ctx.rules.events.peak_max_epochs
    return EventPhase.AFTERMATH if not active or spent else EventPhase.PEAK


async def siege_next(ctx: TickContext, event: EntityRow, profile: EventProfileRow) -> EventPhase:
    del event
    siege = await ctx.session.get(SiegeRow, profile.siege_id) if profile.siege_id is not None else None
    if siege_over(siege):
        return EventPhase.AFTERMATH
    return EventPhase.PEAK if profile.phase is EventPhase.PEAK or siege_peaked(ctx, siege) else EventPhase.ONSET


PROGRESSIONS = {EngineKind.FAMINE: famine_next, EngineKind.PLAGUE: plague_next, EngineKind.SIEGE: siege_next}


async def next_phase(ctx: TickContext, event: EntityRow, profile: EventProfileRow) -> EventPhase:
    step = PROGRESSIONS.get(event.engine_kind) if event.engine_kind is not None else None
    if profile.phase in {EventPhase.AFTERMATH, EventPhase.MEMORY} or step is None:
        return profile.phase if profile.phase is EventPhase.MEMORY else EventPhase.AFTERMATH
    return await step(ctx, event, profile)


async def turn(ctx: TickContext, event: EntityRow, profile: EventProfileRow, phase: EventPhase, atlas: RegionAtlas) -> None:
    profile.phase = phase
    profile.phase_epoch = ctx.epoch
    if event.engine_kind in MULTI_SEASON:
        await phase_line(ctx, event, phase)
    if phase is EventPhase.AFTERMATH:
        await aftermath(ctx, event, profile, atlas)


async def memorialise(ctx: TickContext, event: EntityRow, atlas: RegionAtlas) -> int:
    weight = clamp_int(stat(event, "severity") or 0, 0, PERCENT) * ctx.rules.events.memory_pct // PERCENT
    if weight <= 0:
        return 0
    kept = 0
    for community in await struck_communities(ctx, event, atlas):
        if held(community.id):
            continue
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=community.id,
            subject_id=event.id,
            kind=MemoryKind.LAMENTED,
            magnitude=-weight,
            epoch=ctx.epoch,
            note="an event kept in memory",
        )
        kept += 1
    return kept


async def advance(ctx: TickContext, atlas: RegionAtlas) -> Counter[str]:
    counts: Counter[str] = Counter()
    profiles = list(await ctx.session.scalars(select(EventProfileRow).where(EventProfileRow.end_epoch.is_(None)).order_by(EventProfileRow.entity_id)))
    for profile in profiles:
        event = await ctx.session.get(EntityRow, profile.entity_id)
        if event is None or event.status is EntityStatus.REJECTED:
            continue
        if ctx.epoch > profile.phase_epoch and PHASE_HOLD not in profile.locked:
            wanted = await next_phase(ctx, event, profile)
            if wanted is not profile.phase:
                await turn(ctx, event, profile, wanted, atlas)
                counts[f"to_{wanted.value}"] += 1
            elif profile.phase is EventPhase.AFTERMATH and ctx.epoch - profile.phase_epoch >= ctx.rules.events.aftermath_epochs:
                profile.phase, profile.phase_epoch = EventPhase.MEMORY, ctx.epoch
                await memorialise(ctx, event, atlas)
                await close_profile(ctx, profile)
                if event.engine_kind in MULTI_SEASON:
                    await phase_line(ctx, event, EventPhase.MEMORY)
                counts["ended"] += 1
        if profile.phase is EventPhase.PEAK and profile.end_epoch is None and event.engine_kind in MULTI_SEASON:
            counts["peak_dead"] += await peak_harm(ctx, event, profile, atlas)
    await ctx.session.flush()
    return counts


async def ongoing_at_backfill(ctx: TickContext, event: EntityRow) -> bool:
    if event.engine_kind is EngineKind.PLAGUE:
        return await plague_active(ctx, event)
    if event.engine_kind is EngineKind.SIEGE:
        siege = await siege_for(ctx.session, event)
        return siege is not None and siege.status is SiegeStatus.ONGOING
    return False


async def ensure_profiles(ctx: TickContext, atlas: RegionAtlas) -> Counter[str]:
    counts: Counter[str] = Counter()
    statement = (
        select(EntityRow)
        .outerjoin(EventProfileRow, EventProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.EVENT, EntityRow.status != EntityStatus.REJECTED, EventProfileRow.entity_id.is_(None))
        .order_by(EntityRow.id)
    )
    for event in list(await ctx.session.scalars(statement)):
        fresh = event.birth_epoch >= ctx.epoch
        profile = await open_profile(ctx, event)
        await derive_footprint(ctx.session, atlas, event, event.birth_epoch)
        if fresh:
            counts["opened"] += 1
            if event.engine_kind is EngineKind.FAMINE:
                counts["famine_onsets"] += await famine_onset(ctx, event, atlas)
            continue
        if await ongoing_at_backfill(ctx, event):
            profile.phase, profile.phase_epoch = EventPhase.PEAK, max(profile.start_epoch, ctx.epoch - 1)
            counts["backfilled_ongoing"] += 1
            continue
        profile.phase = EventPhase.AFTERMATH
        profile.end_epoch = profile.start_epoch
        profile.end_year = profile.start_year
        profile.end_season = profile.start_season
        counts["backfilled"] += 1
    await ctx.session.flush()
    return counts


async def link_profiles(ctx: TickContext) -> int:
    linked = 0
    statement = (
        select(EventProfileRow).where((EventProfileRow.incident_id.is_(None)) | (EventProfileRow.siege_id.is_(None))).order_by(EventProfileRow.entity_id)
    )
    profiles = list(await ctx.session.scalars(statement))
    unlinked = [profile.entity_id for profile in profiles if profile.incident_id is None]
    firsts: dict[int, IncidentRow] = {}
    for node_id, found in await ctx.session.execute(
        select(IncidentParticipantRow.node_id, IncidentRow)
        .join(IncidentRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .join(EntityRow, EntityRow.id == IncidentParticipantRow.node_id)
        .where(IncidentParticipantRow.node_id.in_(unlinked), IncidentRow.epoch >= EntityRow.birth_epoch)
        .order_by(IncidentRow.epoch, IncidentRow.id)
    ):
        firsts.setdefault(node_id, found)
    events = {event.id: event for event in await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_([profile.entity_id for profile in profiles])))}
    for profile in profiles:
        event = events.get(profile.entity_id)
        if event is None:
            continue
        if profile.incident_id is None:
            incident = firsts.get(profile.entity_id)
            if incident is not None:
                profile.incident_id = incident.id
                if incident.year is not None and incident.epoch == profile.start_epoch:
                    profile.start_year = incident.year
                    if profile.end_year is not None and profile.end_year < incident.year:
                        profile.end_year = incident.year
                linked += 1
        if profile.siege_id is None and event.engine_kind is EngineKind.SIEGE:
            siege = await siege_for(ctx.session, event)
            if siege is not None:
                profile.siege_id = siege.id
                linked += 1
    await ctx.session.flush()
    return linked


async def siege_events(ctx: TickContext, atlas: RegionAtlas) -> int:
    covered = set(await ctx.session.scalars(select(EventProfileRow.siege_id).where(EventProfileRow.siege_id.is_not(None))))
    made = 0
    for siege in list(await ctx.session.scalars(select(SiegeRow).where(SiegeRow.status == SiegeStatus.ONGOING).order_by(SiegeRow.id))):
        if siege.id in covered or made >= ctx.rules.events.emergent_cap:
            continue
        town = await ctx.session.get(EntityRow, siege.besieged_entity_id)
        besieger = await ctx.session.get(EntityRow, siege.besieger_entity_id)
        if town is None or town.status is not EntityStatus.CANON:
            continue
        foe = besieger.name if besieger is not None else "an enemy"
        event, profile = await happen(
            ctx,
            Happening(
                EngineKind.SIEGE,
                f"the Siege of {town.name}",
                f"{foe} closed the roads around {town.name} and sat down before its walls.",
                f"{foe} laid siege to {town.name}.",
                town,
                min(PERCENT, 40 + siege.rounds * 10),
                {town.id: IncidentRole.TARGET, **({besieger.id: IncidentRole.ACTOR} if besieger is not None else {})},
                chronicle=ChronicleKind.WAR,
            ),
            atlas,
        )
        profile.siege_id = siege.id
        profile.start_epoch = min(profile.start_epoch, siege.started_epoch)
        profile.phase_epoch = profile.start_epoch
        made += 1
        del event
    return made
