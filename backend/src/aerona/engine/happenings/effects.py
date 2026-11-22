from sqlalchemy import select

from aerona.catalog.life.happenings import STARVING
from aerona.constants.units import PERCENT
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.happenings import EventCasualtyRow, EventProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import SOCIETY_TYPES, EngineKind, EntityStatus
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.happening import EventPhase
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.context import TickContext
from aerona.engine.environment.book import add_scar, region_environment
from aerona.engine.environment.geomorph import erupted
from aerona.engine.happenings.profile import flow_of, footprint_of, record_casualties
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import headcount_bounds, set_stats, shift_stat, stat, stat_or
from aerona.engine.services.community_relations import change_relation


def severity_scale(ctx: TickContext, event: EntityRow) -> float:
    return (stat_or(event, "severity", ctx.rules.events.severity_neutral)) / max(1, ctx.rules.events.severity_neutral)


async def struck_communities(ctx: TickContext, event: EntityRow, atlas: RegionAtlas) -> list[EntityRow]:
    found: list[EntityRow] = []
    for region_id in await footprint_of(ctx.session, event.id):
        for community_id in sorted(atlas.communities_in(region_id)):
            community = await ctx.session.get(EntityRow, community_id)
            if community is not None and community.status is EntityStatus.CANON and community.entity_type in SOCIETY_TYPES and community not in found:
                found.append(community)
    return found


async def kill_share(ctx: TickContext, event: EntityRow, community: EntityRow, pct: float, *, category: FlowCategory, phase: EventPhase) -> int:
    population = stat(community, "population")
    if not population or pct <= 0:
        return 0
    floor, _ = headcount_bounds(ctx.rules, community)
    dead = min(max(0, population - floor), round_half_up(population * pct / PERCENT))
    if dead <= 0:
        return 0
    await record_casualties(ctx, event.id, community, dead, category=category, phase=phase)
    with flowing(category):
        set_stats(community, population=population - dead)
    return dead


async def calm(ctx: TickContext, settlement_id: int, relief: int) -> None:
    profile = await ctx.session.get(SettlementProfileRow, settlement_id)
    if profile is not None and "unrest" not in profile.locked:
        profile.unrest = max(0, min(PERCENT, profile.unrest - relief))


async def scar(ctx: TickContext, entity_id: int | None, kind: ScarKind, depth: int) -> None:
    if entity_id is None or depth <= 0:
        return
    ground = await region_environment(ctx.session, entity_id)
    if ground is not None:
        add_scar(ground, kind, depth)


async def plague_active(ctx: TickContext, event: EntityRow) -> bool:
    statement = select(OutbreakRow.id).where(OutbreakRow.event_entity_id == event.id, OutbreakRow.status != OutbreakStatus.ENDED).limit(1)
    return await ctx.session.scalar(statement) is not None


async def adult_loss_pct(ctx: TickContext, event: EntityRow, community: EntityRow) -> float:
    statement = select(EventCasualtyRow.count).where(
        EventCasualtyRow.event_entity_id == event.id, EventCasualtyRow.community_entity_id == community.id, EventCasualtyRow.age_band == AgeBand.ADULT
    )
    adults = sum(await ctx.session.scalars(statement))
    population = stat(community, "population") or 0
    return adults / max(1, population + adults) * PERCENT


async def famine_onset(ctx: TickContext, event: EntityRow, atlas: RegionAtlas) -> int:
    hit = 0
    for community in await struck_communities(ctx, event, atlas):
        if shift_stat(community, "prosperity", -ctx.rules.events.famine_onset_prosperity) is not None:
            hit += 1
    return hit


async def peak_harm(ctx: TickContext, event: EntityRow, profile: EventProfileRow, atlas: RegionAtlas) -> int:
    table = ctx.rules.events
    scale = severity_scale(ctx, event)
    category = flow_of(event.engine_kind)
    if event.engine_kind is EngineKind.SIEGE:
        siege = await ctx.session.get(SiegeRow, profile.siege_id) if profile.siege_id is not None else None
        town = await ctx.session.get(EntityRow, siege.besieged_entity_id if siege is not None else event.location_id or -1)
        hunger = STARVING.get(siege.starvation, 0.0) if siege is not None else 0.0
        if town is None or town.status is not EntityStatus.CANON or not hunger:
            return 0
        return await kill_share(ctx, event, town, table.siege_peak_starvation_pct * hunger * scale, category=category, phase=EventPhase.PEAK)
    pct = table.famine_peak_death_pct if event.engine_kind is EngineKind.FAMINE else table.plague_peak_death_pct
    dead = 0
    for community in await struck_communities(ctx, event, atlas):
        dead += await kill_share(ctx, event, community, pct * scale, category=category, phase=EventPhase.PEAK)
    return dead


async def aftermath(ctx: TickContext, event: EntityRow, profile: EventProfileRow, atlas: RegionAtlas) -> int:
    table = ctx.rules.events
    if event.engine_kind is EngineKind.FAMINE:
        for region_id in await footprint_of(ctx.session, event.id):
            await scar(ctx, region_id, ScarKind.PLAGUE_GROUND, table.famine_aftermath_disease)
        return 1
    if event.engine_kind is EngineKind.PLAGUE:
        touched = 0
        for community in await struck_communities(ctx, event, atlas):
            gain = min(table.plague_aftermath_prosperity_cap, await adult_loss_pct(ctx, event, community) * table.plague_aftermath_prosperity_pct / PERCENT)
            if gain > 0 and shift_stat(community, "prosperity", gain) is not None:
                touched += 1
        return touched
    if event.engine_kind is EngineKind.SIEGE:
        siege = await ctx.session.get(SiegeRow, profile.siege_id) if profile.siege_id is not None else None
        town = await ctx.session.get(EntityRow, siege.besieged_entity_id if siege is not None else event.location_id or -1)
        if town is None:
            return 0
        shift_stat(town, "prosperity", -table.siege_aftermath_prosperity)
        await scar(ctx, town.id, ScarKind.PLAGUE_GROUND, table.siege_aftermath_disease)
        return 1
    return 0


def siege_over(siege: SiegeRow | None) -> bool:
    return siege is None or siege.status is not SiegeStatus.ONGOING


def siege_peaked(ctx: TickContext, siege: SiegeRow | None) -> bool:
    return siege is not None and (siege.rounds >= ctx.rules.events.siege_peak_rounds or siege.starvation in STARVING)


async def world_piety(ctx: TickContext, world_id: int | None, gain: int) -> int:
    if world_id is None:
        return 0
    statement = select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(SOCIETY_TYPES)))
    touched = 0
    for community in list(await ctx.session.scalars(statement.order_by(EntityRow.id))):
        if stat(community, "piety") is not None and shift_stat(community, "piety", gain) is not None:
            touched += 1
    return touched


async def onset(ctx: TickContext, event: EntityRow, where: EntityRow, atlas: RegionAtlas, partner: EntityRow | None = None) -> None:
    table = ctx.rules.events
    kind = event.engine_kind
    if kind is EngineKind.FESTIVAL_OF_NOTE:
        shift_stat(where, "prosperity", table.festival_prosperity)
        await calm(ctx, where.id, table.festival_unrest_relief)
    elif kind is EngineKind.CORONATION:
        shift_stat(where, "prosperity", table.coronation_prosperity)
    elif kind is EngineKind.WEDDING and partner is not None and partner.id != where.id:
        await change_relation(ctx, where.id, partner.id, table.wedding_feast_relation, MemoryKind.GOODWILL, note="wedding feast", event_id=event.id)
    elif kind is EngineKind.MASSACRE:
        await scar(ctx, where.id, ScarKind.HAUNTED, table.massacre_haunt_depth)
    elif kind is EngineKind.SACK:
        await scar(ctx, where.id, ScarKind.BURNED, table.sack_burn_depth)
    elif kind is EngineKind.FIRE:
        await scar(ctx, where.id, ScarKind.BURNED, table.fire_burn_depth)
    elif kind is EngineKind.RIOT:
        await kill_share(ctx, event, where, table.riot_death_pct, category=FlowCategory.CASUALTY, phase=EventPhase.ONSET)
        shift_stat(where, "prosperity", -table.riot_prosperity)
        await calm(ctx, where.id, table.riot_unrest_vent)
    elif kind is EngineKind.SCHISM_COUNCIL:
        if partner is not None:
            shift_stat(partner, "zeal", table.schism_council_zeal)
        shift_stat(where, "influence", -table.schism_council_influence)
    elif kind is EngineKind.ECLIPSE_WATCH:
        await world_piety(ctx, event.world_id, table.eclipse_piety)
    elif kind is EngineKind.FAMINE:
        await famine_onset(ctx, event, atlas)
    elif kind is EngineKind.ERUPTION:
        await erupted(ctx, where, stat_or(event, "severity", table.severity_neutral))
