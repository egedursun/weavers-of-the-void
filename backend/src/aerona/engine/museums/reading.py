from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.museums import MADE_PIECES, NATURAL_PIECES
from aerona.constants.units import PERCENT
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.museums import MuseumCollectionRow, MuseumPieceRow
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.museum import PieceKind
from aerona.rules.registry import Rules


async def pieces_held(session: AsyncSession, keeper_ids: list[int], kinds: tuple[PieceKind, ...]) -> int:
    if not keeper_ids:
        return 0
    found = await session.scalar(
        select(func.count())
        .select_from(MuseumPieceRow)
        .join(MuseumCollectionRow, MuseumCollectionRow.id == MuseumPieceRow.collection_id)
        .where(MuseumCollectionRow.keeper_entity_id.in_(keeper_ids), MuseumPieceRow.kind.in_(list(kinds)))
    )
    return int(found or 0)


async def collection_factor(session: AsyncSession, rules: Rules, community_id: int, *, natural: bool) -> float:
    table = rules.museums
    pieces = await pieces_held(session, [community_id], NATURAL_PIECES if natural else MADE_PIECES)
    return 1 + min(pieces, table.research_cap) * table.research_pct / PERCENT


async def grandeur(session: AsyncSession, rules: Rules, keeper_ids: list[int]) -> int:
    if not keeper_ids:
        return 0
    hoards = await session.scalar(select(func.max(MuseumCollectionRow.prestige)).where(MuseumCollectionRow.keeper_entity_id.in_(keeper_ids)))
    grounds = await session.scalar(select(func.max(GardenRow.condition)).where(GardenRow.settlement_entity_id.in_(keeper_ids)))
    return max(int(hoards or 0), int(grounds or 0) * rules.gardens.prestige_pct // PERCENT)


async def gardens_kept(session: AsyncSession, rules: Rules, town_ids: list[int]) -> int:
    if not town_ids:
        return 0
    found = await session.scalar(
        select(func.count()).select_from(GardenRow).where(GardenRow.settlement_entity_id.in_(town_ids), GardenRow.condition >= rules.gardens.condition)
    )
    return int(found or 0)


async def physic_share(session: AsyncSession, rules: Rules, town_id: int | None) -> float:
    if town_id is None:
        return 0.0
    found = await session.scalar(select(func.max(GardenRow.condition)).where(GardenRow.settlement_entity_id == town_id, GardenRow.kind == GardenKind.PHYSIC))
    return int(found or 0) / PERCENT * rules.gardens.physic_heal_pct / PERCENT


async def refuges(session: AsyncSession, region_of: dict[int, int | None]) -> set[tuple[int, int]]:
    found: set[tuple[int, int]] = set()
    for town_id, species in await session.execute(select(GardenRow.settlement_entity_id, GardenRow.species).where(GardenRow.condition > 0)):
        region = region_of.get(town_id)
        if region is not None:
            found.update((int(kind), region) for kind in species)
    return found
