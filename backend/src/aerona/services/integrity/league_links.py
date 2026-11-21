from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leagues import LeagueDecisionRow, LeagueMemberRow, PolityLeagueRow
from aerona.db.tables.monetary import MonetaryAuthorityRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.leagues import LeagueAim, LeagueOrgan
from aerona.engine.leagues.book import aims_of, members_of
from aerona.engine.monetary.authorities import authority_of, currency_for


async def non_polity_members(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for member in await session.scalars(select(LeagueMemberRow).order_by(LeagueMemberRow.id)):
        entity = await session.get(EntityRow, member.polity_entity_id)
        if entity is None or entity.entity_type is not EntityType.POLITY:
            found.append(member.id)
    return found


async def strike_member(session: AsyncSession, key: int) -> None:
    member = await session.get(LeagueMemberRow, key)
    if member is not None:
        await session.delete(member)


async def unbacked_unions(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for profile in await session.scalars(select(PolityLeagueRow).order_by(PolityLeagueRow.league_entity_id)):
        if LeagueAim.CURRENCY_UNION not in aims_of(profile):
            continue
        authority = await session.get(MonetaryAuthorityRow, profile.authority_id) if profile.authority_id is not None else None
        if authority is None:
            found.append(profile.league_entity_id)
    return found


async def back_union(session: AsyncSession, key: int) -> None:
    profile = await session.get(PolityLeagueRow, key)
    if profile is None:
        return
    for member in await members_of(session, key):
        authority = await authority_of(session, await currency_for(session, member.polity_entity_id))
        if authority is not None:
            profile.authority_id = authority.id
            return
    profile.aims = [aim for aim in profile.aims or [] if aim != LeagueAim.CURRENCY_UNION.value]


async def organless_decisions(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for decision in await session.scalars(select(LeagueDecisionRow).order_by(LeagueDecisionRow.id)):
        profile = await session.get(PolityLeagueRow, decision.league_entity_id)
        if profile is not None and decision.organ.value not in (profile.organs or []):
            found.append(decision.id)
    return found


async def give_organ(session: AsyncSession, key: int) -> None:
    decision = await session.get(LeagueDecisionRow, key)
    profile = await session.get(PolityLeagueRow, decision.league_entity_id) if decision is not None else None
    if decision is None or profile is None:
        return
    if LeagueOrgan.ASSEMBLY.value in (profile.organs or []):
        decision.organ = LeagueOrgan.ASSEMBLY
    else:
        profile.organs = sorted({*(profile.organs or []), decision.organ.value})
