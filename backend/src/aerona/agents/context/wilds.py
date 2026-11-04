from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ecology import BeastProfileRow, HerdRow, SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat


def words(value: str) -> str:
    return value.replace("_", " ")


async def wild_lines(session: AsyncSession, home: EntityRow, region: int | None) -> tuple[list[str], list[str], list[str]]:
    wild: list[str] = []
    if region is not None:
        rows = await session.execute(
            select(EntityRow.name, SpeciesRangeRow.abundance, SpeciesProfileRow.diet)
            .join(SpeciesRangeRow, SpeciesRangeRow.species_entity_id == EntityRow.id)
            .join(SpeciesProfileRow, SpeciesProfileRow.species_entity_id == EntityRow.id)
            .where(SpeciesRangeRow.region_entity_id == region, EntityRow.status == EntityStatus.CANON, SpeciesRangeRow.abundance > 0)
            .order_by(SpeciesRangeRow.abundance.desc())
        )
        wild = [f"{name} ({words(diet.value)}, {abundance} strong)" for name, abundance, diet in rows]
    herds = [
        f"{name} ({head} head, {words(stage.value)})"
        for name, head, stage in await session.execute(
            select(EntityRow.name, HerdRow.head, HerdRow.stage)
            .join(EntityRow, EntityRow.id == HerdRow.species_entity_id)
            .where(HerdRow.community_entity_id == home.id)
        )
    ]
    atlas = await RegionAtlas.load(session)
    beasts = []
    for beast, row in await session.execute(
        select(EntityRow, BeastProfileRow).join(BeastProfileRow, BeastProfileRow.beast_entity_id == EntityRow.id).where(EntityRow.status == EntityStatus.CANON)
    ):
        lair = row.lair_place_id or beast.location_id
        if lair is not None and region is not None and atlas.top_region(lair) == region:
            beasts.append(f"{beast.name} ({words(row.temper.value)}, terror {stat(beast, 'terror') or 0})")
    return wild, herds, beasts
