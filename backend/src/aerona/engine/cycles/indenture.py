from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.cycles import IndentureRow, ManumissionRow, SlaveMarketRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.cycles import ManumissionPath
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
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


async def record_manumission(ctx: TickContext, community: EntityRow, count: int, path: ManumissionPath) -> ManumissionRow | None:
    if count <= 0:
        return None
    row = ManumissionRow(community_entity_id=community.id, count=count, path=path, epoch=ctx.epoch)
    ctx.session.add(row)
    return row


async def revolts_in(session: AsyncSession, town_ids: list[int], since: int) -> int:
    found = await session.scalar(
        select(func.coalesce(func.sum(ManumissionRow.count), 0)).where(
            ManumissionRow.community_entity_id.in_(town_ids), ManumissionRow.path == ManumissionPath.REVOLT, ManumissionRow.epoch >= since
        )
    )
    return round_half_up(int(found or 0))
