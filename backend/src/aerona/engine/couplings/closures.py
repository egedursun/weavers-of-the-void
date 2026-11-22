from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.laws import defaults_for
from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import LawProfileRow, OfficeRow, PolityMemberRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import LawKind, OfficeKind
from aerona.rules.registry import Rules


async def holders_of(session: AsyncSession, ground: CatchGroundRow) -> list[int]:
    holders: list[int] = []
    if ground.owner_node_id is not None:
        holders.append(ground.owner_node_id)
    towns = await session.scalars(
        select(EntityRow.id)
        .where(EntityRow.location_id == ground.region_entity_id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    holders.extend(towns)
    realms = await session.scalars(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id.in_(holders)))
    return list(dict.fromkeys([*holders, *realms]))


CLOSURE_CUTS: dict[LawKind, str] = {
    LawKind.CLOSED_SEASON: "season_cut_pct",
    LawKind.PROTECTED_WATERS: "protected_cut_pct",
    LawKind.CATCH_QUOTA: "quota_cut_pct",
    LawKind.GEAR_BAN: "gear_cut_pct",
}


async def closures_on(session: AsyncSession, ground: CatchGroundRow) -> list[tuple[LawProfileRow, int]]:
    holders = await holders_of(session, ground)
    if not holders:
        return []
    statement = (
        select(LawProfileRow, EntityRow.location_id)
        .join(EntityRow, EntityRow.id == LawProfileRow.law_entity_id)
        .where(LawProfileRow.kind.in_(tuple(CLOSURE_CUTS)), EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_(holders))
    )
    return [(profile, holder) for profile, holder in await session.execute(statement) if holder is not None]


async def wardened(session: AsyncSession, holder_id: int) -> bool:
    realm = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == holder_id).limit(1))
    found = await session.scalar(
        select(OfficeRow.id)
        .where(OfficeRow.polity_entity_id.in_([holder_id, *([realm] if realm is not None else [])]), OfficeRow.kind == OfficeKind.WARDEN)
        .limit(1)
    )
    return found is not None


def bans_gear(profile: LawProfileRow, ground: CatchGroundRow) -> bool:
    if profile.kind is not LawKind.GEAR_BAN:
        return True
    return str(profile.params.get("gear", defaults_for(LawKind.GEAR_BAN)["gear"])) == ground.gear.value


async def closure_factor(session: AsyncSession, rules: Rules, ground: CatchGroundRow) -> float:
    table = rules.closures
    factor = 1.0
    for profile, holder in await closures_on(session, ground):
        rule_name = CLOSURE_CUTS.get(profile.kind)
        if rule_name is None or not bans_gear(profile, ground):
            continue
        cut: int = getattr(table, rule_name)
        evasion = table.wardened_poaching_pct if await wardened(session, holder) else table.poaching_pct
        kept = cut * profile.enforcement / PERCENT * (PERCENT - evasion) / PERCENT
        factor *= max(0.0, 1 - kept / PERCENT)
    return factor
