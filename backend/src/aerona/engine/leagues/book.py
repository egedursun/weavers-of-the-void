from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leagues import LeagueMemberRow, PolityLeagueRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.leagues import BOUND_STANDINGS, VOTING_STANDINGS, LeagueAim, LeagueStanding


@dataclass
class LeagueTally:
    founded: int = 0
    joined: int = 0
    left: int = 0
    expelled: int = 0
    sanctions: int = 0
    rulings: int = 0
    decisions: int = 0
    defied: int = 0
    dissolved: int = 0
    federated: int = 0
    calls: int = 0
    adopted: int = 0


def aims_of(profile: PolityLeagueRow) -> frozenset[LeagueAim]:
    known = {aim.value: aim for aim in LeagueAim}
    return frozenset(known[value] for value in profile.aims or [] if value in known)


async def members_of(session: AsyncSession, league_id: int, standings: frozenset[LeagueStanding] = BOUND_STANDINGS) -> list[LeagueMemberRow]:
    query = select(LeagueMemberRow).where(LeagueMemberRow.league_entity_id == league_id, LeagueMemberRow.standing.in_(sorted(standings)))
    return list(await session.scalars(query.order_by(LeagueMemberRow.id)))


async def voters_of(session: AsyncSession, league_id: int) -> list[LeagueMemberRow]:
    return await members_of(session, league_id, VOTING_STANDINGS)


async def membership(session: AsyncSession, league_id: int, polity_id: int) -> LeagueMemberRow | None:
    query = select(LeagueMemberRow).where(LeagueMemberRow.league_entity_id == league_id, LeagueMemberRow.polity_entity_id == polity_id)
    return await session.scalar(query.limit(1))


async def core_of(session: AsyncSession, polity_id: int) -> int | None:
    profile = await session.get(PolityProfileRow, polity_id)
    return profile.core_entity_id if profile is not None else None


async def living_polity(session: AsyncSession, polity_id: int | None) -> EntityRow | None:
    entity = await session.get(EntityRow, polity_id) if polity_id is not None else None
    if entity is None or entity.entity_type is not EntityType.POLITY or entity.status is not EntityStatus.CANON:
        return None
    return entity


async def unions_of(session: AsyncSession) -> tuple[dict[int, set[int]], dict[int, int]]:
    unions: dict[int, set[int]] = {}
    tariffs: dict[int, int] = {}
    for profile in await session.scalars(select(PolityLeagueRow).order_by(PolityLeagueRow.league_entity_id)):
        if LeagueAim.CUSTOMS_UNION not in aims_of(profile):
            continue
        tariffs[profile.league_entity_id] = profile.common_tariff_pct
        for member in await members_of(session, profile.league_entity_id):
            unions.setdefault(member.polity_entity_id, set()).add(profile.league_entity_id)
    return unions, tariffs
