from sqlalchemy import select

from aerona.catalog.conditions import MAIMS
from aerona.constants.units import PERCENT
from aerona.db.tables.body import BodyCustomRow, MaimedCohortRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import BodyReading, MaimedKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.customs import ensure_customs, people_of
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import blocked
from aerona.engine.phases.remembrance import MemorialForm, memorial
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.numbers import apportion, clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules
from aerona.rules.registry.body import MaimedRules

FESTIVAL_SUBTYPE = "scar festival"
FESTIVAL_FIELD = "scar_festivals"


COHORT_KEY = "maimed"


def kind_weights(rules: MaimedRules, helmet_cover: int) -> dict[MaimedKind, float]:
    weights = {kind: spec.weight(rules) for kind, spec in MAIMS.items()}
    shield = max(0, PERCENT - helmet_cover * rules.helmet_eye_cut_pct / PERCENT) / PERCENT
    return {kind: weight * (shield if MAIMS[kind].eyes else 1) for kind, weight in weights.items()}


async def cohort(ctx: TickContext, community_id: int, kind: MaimedKind) -> MaimedCohortRow:
    row = await ctx.session.get(MaimedCohortRow, (community_id, kind))
    if row is None:
        row = MaimedCohortRow(community_entity_id=community_id, kind=kind, count=0, veterans=0, updated_epoch=ctx.epoch)
        ctx.session.add(row)
    return row


async def helmet_cover(ctx: TickContext, community_id: int) -> int:
    levels = (await known_levels(ctx.session, [community_id])).get(community_id, {})
    return min(ctx.rules.armour.coverage_cap, levels.get(KnowledgeBranch.METALLURGY, 0) * ctx.rules.armour.metallurgy_head_per_level)


async def return_maimed(ctx: TickContext, community: EntityRow, wounded: int) -> int:
    table = ctx.rules.maimed
    if blocked(community.id, COHORT_KEY):
        return 0
    maimed = round_half_up(max(0, wounded) * table.return_pct / PERCENT)
    if maimed <= 0:
        return 0
    weights = kind_weights(table, await helmet_cover(ctx, community.id))
    total = sum(weights.values())
    if total <= 0:
        return 0
    placed = 0
    ordered = sorted(weights.items(), key=lambda item: -item[1])
    for kind, part in apportion(maimed, dict(ordered)).items():
        share = max(0, min(part, maimed - placed))
        if share <= 0:
            continue
        row = await cohort(ctx, community.id, kind)
        row.count += share
        row.veterans += share
        row.updated_epoch = ctx.epoch
        placed += share
        await record(ctx, "body.maimed", roles={IncidentRole.SUBJECT: community.id}, facts={"maim": kind, "count": share})
    ctx.count("maimed_returned", placed)
    return placed


async def cohorts_of(ctx: TickContext, community_id: int) -> list[MaimedCohortRow]:
    rows = await ctx.session.scalars(select(MaimedCohortRow).where(MaimedCohortRow.community_entity_id == community_id))
    return list(rows)


def maimed_share(rules: Rules, community: EntityRow, rows: list[MaimedCohortRow]) -> float:
    population = stat(community, "population") or 0
    if population <= 0:
        return 0.0
    return min(rules.maimed.share_cap_pct / PERCENT, sum(row.count for row in rows) / population)


async def share_of(ctx: TickContext, community: EntityRow) -> float:
    return maimed_share(ctx.rules, community, await cohorts_of(ctx, community.id))


async def custom_for(ctx: TickContext, community: EntityRow) -> BodyCustomRow | None:
    people = await people_of(ctx.session, community)
    return await ensure_customs(ctx.session, ctx.rules, people) if people is not None else None


async def war_appetite(ctx: TickContext, community: EntityRow) -> float:
    custom = await custom_for(ctx, community)
    if custom is not None and custom.reading is BodyReading.MARTIAL_HONOUR:
        return 1.0
    return max(0.0, 1 - await share_of(ctx, community) * ctx.rules.maimed.anti_war_pct / PERCENT)


async def labour_factor(ctx: TickContext, community: EntityRow) -> float:
    rows = await cohorts_of(ctx, community.id)
    whole = sum(row.count for row in rows)
    if whole <= 0:
        return 1.0
    loss = sum(row.count * MAIMS[row.kind].loss(ctx.rules.maimed) for row in rows) / whole
    return max(0.0, 1 - maimed_share(ctx.rules, community, rows) * loss / PERCENT)


async def shooting_factor(ctx: TickContext, community: EntityRow) -> int:
    rows = [row for row in await cohorts_of(ctx, community.id) if row.kind is MaimedKind.LOST_FINGERS]
    return round(maimed_share(ctx.rules, community, rows) * ctx.rules.maimed.lost_fingers_missile_cut)


async def healer_demand(ctx: TickContext, community: EntityRow) -> float:
    return 1 + await share_of(ctx, community) * ctx.rules.maimed.healer_demand_pct / PERCENT


async def _festival(ctx: TickContext, custom: BodyCustomRow, veterans: int) -> None:
    table = ctx.rules.maimed
    if custom.scar_festivals and custom.tradition_entity_id is not None:
        held = await entity(ctx.session, custom.tradition_entity_id)
        if held is not None and held.status is EntityStatus.CANON:
            return
    if custom.reading is not BodyReading.MARTIAL_HONOUR or veterans < table.festival_veterans or FESTIVAL_FIELD in custom.locked:
        return
    people = await entity(ctx.session, custom.people_entity_id)
    if people is None or people.world_id is None:
        return
    name = f"Scar Festival of {people.name}"
    body = f"Each year the veterans of {people.name} show the scars of their wars, and the people honour every mark."
    tradition = await memorial(ctx, MemorialForm.TRADITION, name, FESTIVAL_SUBTYPE, body, location_id=people.location_id, world_id=people.world_id)
    await connect(ctx.session, people.id, tradition.id, BondKind.CELEBRATES, ctx.epoch)
    custom.scar_festivals = True
    custom.tradition_entity_id = tradition.id
    await record(
        ctx,
        "cohort.scar_festival",
        roles={IncidentRole.SUBJECT: people.id, IncidentRole.PRODUCT: tradition.id},
        facts={"veterans": veterans, "reading": custom.reading},
    )


async def tend_cohorts(ctx: TickContext) -> None:
    table = ctx.rules.maimed
    rows = list(await ctx.session.scalars(select(MaimedCohortRow).order_by(MaimedCohortRow.community_entity_id, MaimedCohortRow.kind)))
    grouped: dict[int, list[MaimedCohortRow]] = {}
    for row in rows:
        grouped.setdefault(row.community_entity_id, []).append(row)
    for community_id, group in grouped.items():
        community = await entity(ctx.session, community_id)
        if community is None or community.status is not EntityStatus.CANON or community.entity_type not in {EntityType.SETTLEMENT, EntityType.PEOPLE}:
            continue
        if blocked(community_id, COHORT_KEY):
            continue
        for row in group:
            row.count = round_half_up(row.count * (PERCENT - table.attrition_pct) / PERCENT)
            row.veterans = min(row.count, round_half_up(row.veterans * (PERCENT - table.attrition_pct) / PERCENT))
            row.updated_epoch = ctx.epoch
        share = maimed_share(ctx.rules, community, group)
        custom = await custom_for(ctx, community)
        pension = custom is not None and custom.pension
        drain = share * PERCENT * table.beggar_drain_pct / PERCENT * (table.pension_drain_pct / PERCENT if pension else 1)
        if drain > 0:
            shift_stat(community, "prosperity", -clamp_int(drain, 0, table.drain_cap))
            ctx.count("maimed_drain", round_half_up(drain))
        if custom is not None:
            await _festival(ctx, custom, sum(row.veterans for row in group))
