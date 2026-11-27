import math
from types import MappingProxyType

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.dominion import GodImageRow, MiracleRecordRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringGuestRow, GatheringRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import Manifestation
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.gathering import GatheringStatus
from aerona.domain.enums.intervention import Miracle
from aerona.domain.enums.mind import PressureKind
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import domains_of, god_of
from aerona.engine.divine.standing import standing_row
from aerona.engine.dominion.book import DominionBook
from aerona.engine.mind.book import pressures_of
from aerona.engine.mind.ethics import at_war
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import clamp_int, round_half_up

D = Domain
MIRACLE_DOMAINS = MappingProxyType(
    {
        Miracle.HEALING: frozenset({D.LIFE, D.PLANTS, D.LOVE, D.LIGHT, D.SUN}),
        Miracle.BOUNTY: frozenset({D.HARVEST, D.PLANTS, D.EARTH, D.SUN, D.TRADE, D.SEA}),
        Miracle.PEACE: frozenset({D.LOVE, D.LIGHT, D.DREAM, D.KNOWLEDGE, D.MOON, D.SOUND}),
        Miracle.PROTECTION: frozenset({D.WAR, D.STONE, D.EARTH, D.SKY, D.STORM, D.ICE}),
    }
)
WAR_NEED = 60
MIRACLE_KINDS = frozenset(item.value for item in Miracle)


async def community_of(ctx: TickContext, target: EntityRow) -> EntityRow | None:
    if target.entity_type in COMMUNITY_TYPES:
        return target
    place = await ctx.session.get(EntityRow, target.location_id) if target.location_id is not None else None
    return place if place is not None and place.entity_type in COMMUNITY_TYPES else None


async def need_at(ctx: TickContext, target: EntityRow, community: EntityRow | None) -> int:
    pressure = await pressures_of(ctx.session, community.id if community is not None else target.id)
    hunger = pressure.get(PressureKind.HUNGER, 0)
    insecurity = pressure.get(PressureKind.INSECURITY, 0)
    war = WAR_NEED if community is not None and await at_war(ctx.session, [community.id]) else 0
    return clamp_int(max(hunger, insecurity, war), 0, PERCENT)


async def novelty_of(ctx: TickContext, god_id: int, kind: str, region: int | None) -> int:
    table = ctx.rules.miracle_impression
    repeats = await ctx.session.scalar(
        select(func.count())
        .select_from(MiracleRecordRow)
        .where(
            MiracleRecordRow.god_node_id == god_id,
            MiracleRecordRow.kind == kind,
            MiracleRecordRow.region_entity_id == region,
            MiracleRecordRow.epoch >= ctx.epoch - table.repeat_window,
        )
    )
    return clamp_int(PERCENT - int(repeats or 0) * table.repeat_drop_pct, 0, PERCENT)


async def fits(ctx: TickContext, god_id: int, kind: str) -> bool:
    god = await god_of(ctx.session, god_id)
    wanted = MIRACLE_DOMAINS.get(Miracle(kind)) if kind in MIRACLE_KINDS else None
    return god is None or wanted is None or bool(set(domains_of(god)) & wanted)


async def credited(ctx: TickContext, god_id: int, kind: str, region: int | None, legible: bool) -> int:
    book = await DominionBook.load(ctx.session)
    ruler = book.ruler(ctx.rules, region)
    if ruler is None or ruler == god_id or legible:
        return god_id
    if not await fits(ctx, ruler, kind):
        return god_id
    misread = ctx.rng(f"miracle.misread.{god_id}.{'nowhere' if region is None else region}.{kind}.{ctx.epoch}").chance(ctx.rules.miracle_impression.misread_pct)
    return ruler if misread else god_id


def belief_of(ctx: TickContext, *, magnitude: int, witnesses: int, need: int, novelty: int, legibility: int) -> int:
    table = ctx.rules.miracle_impression
    seen = min(max(witnesses, 1), table.witness_cap)
    crowd = 1 + math.log2(seen) * table.witness_log_pct / PERCENT
    urgency = 1 + need * table.need_pct / PERCENT / PERCENT
    value = table.base_belief * magnitude / PERCENT * crowd * urgency * novelty / PERCENT * legibility / PERCENT
    return max(0, round_half_up(value))


async def veiled(ctx: TickContext, god_id: int) -> bool:
    image = await ctx.session.get(GodImageRow, god_id)
    return image is not None and image.manifestation is Manifestation.VEILED


async def offend_ruler(ctx: TickContext, god_id: int, region: int | None, book: DominionBook, share: float) -> None:
    ruler = book.ruler(ctx.rules, region)
    if ruler is None or ruler == god_id or held(ruler, god_id):
        return
    if await ctx.session.get(SonRow, ruler) is None or await ctx.session.get(SonRow, god_id) is None:
        return
    offence = round_half_up(ctx.rules.dominion.rival_miracle_offence * share)
    if offence:
        await SonRepository(ctx.session).change_relation(god_id, ruler, -offence)


async def impress(ctx: TickContext, god_id: int, target: EntityRow, *, kind: str, magnitude: int, witnesses: int) -> MiracleRecordRow:
    table = ctx.rules.miracle_impression
    share = ctx.rules.dominion.veiled_witness_pct / PERCENT if await veiled(ctx, god_id) else 1.0
    witnesses = max(1, round_half_up(witnesses * share))
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(target.id)
    community = await community_of(ctx, target)
    legible = await fits(ctx, god_id, kind)
    legibility = PERCENT if legible else PERCENT // 2
    need = await need_at(ctx, target, community)
    novelty = await novelty_of(ctx, god_id, kind, region)
    book = await DominionBook.load(ctx.session)
    power = book.power_factor(ctx.rules, god_id, region, ctx.rules.dominion.miracle_power_pct)
    belief = round_half_up(
        belief_of(ctx, magnitude=clamp_int(magnitude, 0, PERCENT), witnesses=witnesses, need=need, novelty=novelty, legibility=legibility) * power
    )
    credit = await credited(ctx, god_id, kind, region, legible)
    row = MiracleRecordRow(
        god_node_id=god_id,
        target_entity_id=target.id,
        region_entity_id=region,
        kind=kind,
        epoch=ctx.epoch,
        magnitude=clamp_int(magnitude, 0, PERCENT),
        witnesses=witnesses,
        need=need,
        novelty=novelty,
        legibility=legibility,
        belief=belief,
        credited_node_id=credit,
        locked=[],
    )
    ctx.session.add(row)
    god = await god_of(ctx.session, credit)
    if god is not None and not held(credit) and "faith" not in getattr(god, "locked", []):
        god.faith = god.faith + round_half_up(belief * table.faith_per_belief_pct / PERCENT)
    if community is not None and not held(community.id, credit):
        standing = await standing_row(ctx, community.id, credit)
        if "awe" not in standing.locked:
            standing.awe = clamp_int(standing.awe + round_half_up(belief * table.awe_per_belief_pct / PERCENT * share), 0, PERCENT)
    await offend_ruler(ctx, god_id, region, book, share)
    await ctx.session.flush()
    return row


async def gathered_with(ctx: TickContext, target: EntityRow) -> int:
    held_here = select(GatheringRow.id).where(
        GatheringRow.epoch == ctx.epoch,
        GatheringRow.status.in_([GatheringStatus.HELD, GatheringStatus.DISRUPTED]),
        (GatheringRow.place_entity_id == target.id) | GatheringRow.id.in_(select(GatheringGuestRow.gathering_id).where(GatheringGuestRow.node_id == target.id)),
    )
    statement = (
        select(func.count())
        .select_from(GatheringGuestRow)
        .where(GatheringGuestRow.gathering_id.in_(held_here), GatheringGuestRow.attended.is_(True), GatheringGuestRow.node_id != target.id)
    )
    return int(await ctx.session.scalar(statement) or 0)


async def witness_count(ctx: TickContext, target: EntityRow) -> int:
    crowd = await gathered_with(ctx, target)
    if target.entity_type not in COMMUNITY_TYPES:
        return 1 + crowd
    named = select(func.count()).select_from(EntityRow).where(await present_in(ctx.session, target), EntityRow.status == EntityStatus.CANON)
    cohorts = select(func.coalesce(func.sum(CohortRow.count), 0)).where(CohortRow.community_entity_id == target.id)
    return max(1, int(await ctx.session.scalar(named) or 0) + int(await ctx.session.scalar(cohorts) or 0) + crowd)


async def miracle_factor(ctx: TickContext, god_id: int, target: EntityRow) -> float:
    atlas = await RegionAtlas.load(ctx.session)
    return (await DominionBook.load(ctx.session)).cost_factor(ctx.rules, god_id, atlas.top_region(target.id))
