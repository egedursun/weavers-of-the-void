from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.body import BodyCustomRow, MaimedCohortRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import BodyReading, MaimedKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.customs import ensure_customs, people_of
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.phases.remembrance import MemorialForm, memorial
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.rules.registry import Rules
from aerona.rules.registry.body import MaimedRules

EYE_KINDS = frozenset({MaimedKind.ONE_EYED, MaimedKind.BLIND})
FESTIVAL_SUBTYPE = "scar festival"
FESTIVAL_FIELD = "scar_festivals"


def kind_weights(rules: MaimedRules, helmet_cover: int) -> dict[MaimedKind, float]:
    weights = {
        MaimedKind.ONE_ARMED: rules.one_armed,
        MaimedKind.ONE_LEGGED: rules.one_legged,
        MaimedKind.ONE_EYED: rules.one_eyed,
        MaimedKind.BLIND: rules.blind,
        MaimedKind.DEAF: rules.deaf,
        MaimedKind.MUTE: rules.mute,
        MaimedKind.LAME: rules.lame,
        MaimedKind.SCARRED: rules.scarred,
        MaimedKind.BROKEN_MINDED: rules.broken_minded,
    }
    shield = max(0, PERCENT - helmet_cover * rules.helmet_eye_cut_pct / PERCENT) / PERCENT
    return {kind: weight * (shield if kind in EYE_KINDS else 1) for kind, weight in weights.items()}


async def cohort(ctx: TickContext, community_id: int, kind: MaimedKind) -> MaimedCohortRow:
    row = await ctx.session.get(MaimedCohortRow, (community_id, kind))
    if row is None:
        row = MaimedCohortRow(community_entity_id=community_id, kind=kind, count=0, veterans=0, updated_epoch=ctx.epoch)
        ctx.session.add(row)
    return row


async def helmet_cover(ctx: TickContext, community_id: int) -> int:
    levels = (await known_levels(ctx.session, [community_id])).get(community_id, {})
    return min(ctx.rules.armour.coverage_cap, levels.get(KnowledgeBranch.METALLURGY, 0) * ctx.rules.armour.metallurgy_head_per_level)


async def return_maimed(ctx: TickContext, community: EntityRow, lost: int) -> int:
    table = ctx.rules.maimed
    maimed = round_half_up(max(0, lost) * table.return_pct / PERCENT)
    if maimed <= 0:
        return 0
    weights = kind_weights(table, await helmet_cover(ctx, community.id))
    total = sum(weights.values())
    if total <= 0:
        return 0
    placed = 0
    ordered = sorted(weights.items(), key=lambda item: -item[1])
    for index, (kind, weight) in enumerate(ordered):
        share = maimed - placed if index == len(ordered) - 1 else round_half_up(maimed * weight / total)
        share = max(0, min(share, maimed - placed))
        if share <= 0:
            continue
        row = await cohort(ctx, community.id, kind)
        row.count += share
        row.veterans += share
        row.updated_epoch = ctx.epoch
        placed += share
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
    return max(0.0, 1 - await share_of(ctx, community) * ctx.rules.maimed.labour_loss_pct / PERCENT)


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
    await note(ctx, f"The maimed veterans of {people.name} became a festival: {tradition.name}.", key="cohort.scar_festival", ids=[people.id, tradition.id])


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
