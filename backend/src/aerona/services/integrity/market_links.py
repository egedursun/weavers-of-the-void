from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.market_kinds import ANIMAL_CLUBS, CLUBS, WAYS
from aerona.db.tables.arts import ClubRow, MatchRow
from aerona.db.tables.crafts import IncorporealRightRow
from aerona.db.tables.ecology import HerdRow, SpeciesUseRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.domain.enums.crafts import RightAcquired, RightKind
from aerona.domain.enums.ecology import AnimalRole


def unbound(row: IncorporealRightRow) -> bool:
    way = WAYS[row.acquired]
    if way.needs_contest and row.contest_id is None:
        return True
    if way.needs_union and row.marriage_id is None:
        return True
    if row.kind is RightKind.TECHNIQUE and row.technique is None:
        return True
    return row.kind is RightKind.RECIPE and row.dish_id is None


async def unbound_rights(session: AsyncSession) -> list[int]:
    return [row.id for row in await session.scalars(select(IncorporealRightRow).order_by(IncorporealRightRow.id)) if unbound(row)]


async def bind_right(session: AsyncSession, key: int) -> None:
    row = await session.get(IncorporealRightRow, key)
    if row is None:
        return
    if (row.kind is RightKind.TECHNIQUE and row.technique is None) or (row.kind is RightKind.RECIPE and row.dish_id is None):
        await session.delete(row)
        return
    if "acquired" not in row.locked:
        row.acquired = RightAcquired.GRANTED


async def beastless_clubs(session: AsyncSession) -> list[int]:
    sport = select(SpeciesUseRow.species_entity_id).where(SpeciesUseRow.use == AnimalRole.SPORT)
    keeping = set(await session.scalars(select(HerdRow.community_entity_id).where(HerdRow.species_entity_id.in_(sport), HerdRow.head > 0)))
    found = await session.execute(
        select(ClubRow.faction_entity_id, FactionProfileRow.home_entity_id)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == ClubRow.faction_entity_id)
        .where(ClubRow.kind.in_(list(ANIMAL_CLUBS)))
        .order_by(ClubRow.faction_entity_id)
    )
    return [club for club, home in found.all() if home not in keeping]


async def unbeast_club(session: AsyncSession, key: int) -> None:
    row = await session.get(ClubRow, key)
    if row is not None and "kind" not in row.locked:
        row.kind = next(kind for kind, spec in CLUBS.items() if not spec.keeps_animals)


async def loose_fixings(session: AsyncSession) -> list[int]:
    loose = [
        row.faction_entity_id
        for row in await session.scalars(select(ClubRow).where(ClubRow.fixed_by_entity_id.is_not(None)).order_by(ClubRow.faction_entity_id))
        if row.fixed_winner_entity_id is None
    ]
    unnamed = await session.scalars(select(MatchRow.id).where(MatchRow.fixing_exposed.is_(True), MatchRow.fixed_by_entity_id.is_(None)).order_by(MatchRow.id))
    return [*loose, *(-match for match in unnamed)]


async def settle_fixing(session: AsyncSession, key: int) -> None:
    if key < 0:
        match = await session.get(MatchRow, -key)
        if match is not None and "fixing_exposed" not in match.locked:
            match.fixing_exposed = False
        return
    row = await session.get(ClubRow, key)
    if row is not None and "fixed_by_entity_id" not in row.locked:
        row.fixed_by_entity_id, row.fixed_winner_entity_id = None, None
