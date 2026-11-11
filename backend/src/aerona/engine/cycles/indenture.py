from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.cycles import IndentureRow, ManumissionRow, SlaveMarketRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import ManumissionPath
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.demography.bound import BOUND
from aerona.engine.demography.cohorts import cohorts_of
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

SKILLED_PATHS = frozenset({ManumissionPath.PURCHASE, ManumissionPath.SERVICE})


async def indentured_in(session: AsyncSession, community_id: int) -> int:
    return int(await session.scalar(select(func.coalesce(func.sum(IndentureRow.count), 0)).where(IndentureRow.community_entity_id == community_id)) or 0)


async def bondage_weight(session: AsyncSession, community: EntityRow) -> int:
    rows = list(await session.scalars(select(IndentureRow).where(IndentureRow.community_entity_id == community.id)))
    people = stat_or(community, "population", 0)
    if not rows or people <= 0:
        return 0
    return clamp_int(sum(row.count * row.exploitation for row in rows) / people, 0, PERCENT)


async def indentured_share(session: AsyncSession, community_id: int) -> int:
    community = await session.get(EntityRow, community_id)
    people = stat_or(community, "population", 0) if community is not None else 0
    return clamp_int(await indentured_in(session, community_id) * PERCENT / people, 0, PERCENT) if people else 0


async def captive_price(session: AsyncSession, rules: Rules, community_id: int) -> float:
    realm = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id).limit(1))
    towns = [community_id]
    if realm is not None:
        towns = list(await session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == realm)))
    best = await session.scalar(select(func.max(SlaveMarketRow.price)).where(SlaveMarketRow.settlement_entity_id.in_(towns), SlaveMarketRow.open.is_(True)))
    if best is None:
        return 1.0
    return 1 + max(0, int(best) - rules.slave_markets.base_price) * rules.slave_markets.raid_lift / PERCENT / max(1, rules.slave_markets.base_price)


def freed_class(path: ManumissionPath) -> SocialClass:
    return SocialClass.ARTISAN if path in SKILLED_PATHS else SocialClass.FARMER


async def manumission_path(ctx: TickContext, community: EntityRow, lawful: bool, at_war: bool) -> ManumissionPath:
    table = ctx.rules.manumission
    if not lawful:
        return ManumissionPath.LAW
    if at_war and ctx.rng(f"manumission.service.{community.id}.{ctx.epoch}").chance(table.service_pct):
        return ManumissionPath.SERVICE
    if stat_or(community, "prosperity", 0) >= table.purchase_prosperity:
        return ManumissionPath.PURCHASE
    return ManumissionPath.WILL


async def freed_origin(ctx: TickContext, community: EntityRow) -> EntityRow | None:
    hosts = await people_of(ctx.session, community)
    origins = await ctx.session.scalars(
        select(CaptiveCohortRow.origin_entity_id)
        .where(CaptiveCohortRow.captor_entity_id == community.id, CaptiveCohortRow.origin_entity_id.is_not(None))
        .order_by(CaptiveCohortRow.origin_entity_id)
    )
    for origin_id in origins:
        origin = await ctx.session.get(EntityRow, origin_id) if origin_id is not None and (hosts is None or origin_id != hosts.id) else None
        if origin is not None:
            return origin
    return None


async def settle_freed(ctx: TickContext, community: EntityRow, origin: EntityRow, count: int) -> None:
    profile = await ctx.session.get(SettlementProfileRow, community.id)
    people = stat_or(community, "population", 0)
    if profile is None or people <= 0 or "foreigners" in profile.locked or held(community.id):
        return
    share = round_half_up(count * ctx.rules.manumission.origin_share_pct / people)
    if share <= 0:
        return
    key = str(origin.id)
    profile.foreigners = {**profile.foreigners, key: min(PERCENT, profile.foreigners.get(key, 0) + share)}


async def free_mortals(ctx: TickContext, community: EntityRow, count: int, path: ManumissionPath) -> int:
    remaining = sum(row.count for row in (await cohorts_of(ctx.session, community.id)).values() if row.social_class is BOUND)
    share = count * PERCENT / (count + remaining)
    bound = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            await present_in(ctx.session, community),
            EntityRow.social_class == SocialClass.SERF_OR_SLAVE,
        )
        .order_by(EntityRow.id)
    )
    freed = 0
    for mortal in list(bound):
        if held(mortal.id) or not ctx.rng(f"manumission.mortal.{mortal.id}.{ctx.epoch}").chance(share):
            continue
        mortal.social_class = freed_class(path)
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=mortal.id,
            subject_id=community.id,
            kind=MemoryKind.FREED_US,
            magnitude=ctx.rules.mobility.freed_memory,
            epoch=ctx.epoch,
            note=f"freed by {path.value.replace('_', ' ')}",
            decay_pct=0,
        )
        freed += 1
    return freed


async def record_manumission(ctx: TickContext, community: EntityRow, count: int, path: ManumissionPath) -> ManumissionRow | None:
    if count <= 0:
        return None
    origin = await freed_origin(ctx, community)
    row = ManumissionRow(
        community_entity_id=community.id,
        count=count,
        path=path,
        standing=ctx.rules.manumission.freed_standing,
        origin_entity_id=origin.id if origin is not None else None,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    if origin is not None:
        await settle_freed(ctx, community, origin, count)
    await free_mortals(ctx, community, count, path)
    return row


async def freed_stigma(session: AsyncSession, community: EntityRow) -> int:
    rows = list(await session.scalars(select(ManumissionRow).where(ManumissionRow.community_entity_id == community.id, ManumissionRow.standing < PERCENT)))
    people = stat_or(community, "population", 0)
    if not rows or people <= 0:
        return 0
    return clamp_int(sum(row.count * (PERCENT - row.standing) for row in rows) / people, 0, PERCENT)


async def revolts_in(session: AsyncSession, town_ids: list[int], since: int) -> int:
    found = await session.scalar(
        select(func.coalesce(func.sum(ManumissionRow.count), 0)).where(
            ManumissionRow.community_entity_id.in_(town_ids), ManumissionRow.path == ManumissionPath.REVOLT, ManumissionRow.epoch >= since
        )
    )
    return round_half_up(int(found or 0))
