from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import BeastProfileRow, HerdRow, SpeciesProfileRow, SpeciesRangeRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
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


def flags_of(row: SpeciesProfileRow) -> list[str]:
    return [label for label, held in (("nocturnal", row.nocturnal), ("migratory", row.migratory)) if held]


async def species_nature(session: AsyncSession, species: EntityRow) -> list[str]:
    row = await session.get(SpeciesProfileRow, species.id)
    if row is None:
        return []
    habits = ", ".join([words(row.size_class.value), words(row.body_plan.value), words(row.diet.value), words(row.sociality.value), *flags_of(row)])
    products = ", ".join(
        await session.scalars(select(SpeciesYieldRow.product).where(SpeciesYieldRow.species_entity_id == species.id).order_by(SpeciesYieldRow.product))
    )
    prey = list(
        await session.scalars(
            select(EntityRow.name)
            .join(BondRow, BondRow.target_node_id == EntityRow.id)
            .where(BondRow.source_node_id == species.id, BondRow.kind == BondKind.HUNTS, BondRow.state == BondState.ACTIVE)
            .order_by(EntityRow.name)
        )
    )
    sacred = await session.get(EntityRow, row.sacred_to_node_id) if row.sacred_to_node_id is not None else None
    lines = [f"nature: {habits}; {words(row.stage.value)}; tameability {row.tameability}, aggression {row.aggression}"]
    if products:
        lines.append(f"yields: {products}")
    if prey:
        lines.append(f"hunts: {', '.join(prey)}")
    if sacred is not None:
        lines.append(f"sacred to {sacred.name}")
    return lines


async def beast_nature(session: AsyncSession, beast: EntityRow) -> list[str]:
    row = await session.get(BeastProfileRow, beast.id)
    if row is None:
        return []
    hoard = ", ".join(f"{value} {words(key)}" for key, value in sorted(row.hoard.items()) if value > 0)
    treasures = list(
        await session.scalars(
            select(EntityRow.name)
            .join(BondRow, BondRow.target_node_id == EntityRow.id)
            .where(BondRow.source_node_id == beast.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
            .order_by(EntityRow.name)
        )
    )
    lines = [
        f"beast: {words(row.size_class.value)}, {words(row.temper.value)}, endurance {row.endurance}, perception {row.perception}, "
        f"willpower {row.willpower}, intelligence {row.intelligence}, age {row.age} of {row.lifespan}"
    ]
    if hoard or treasures:
        lines.append(f"hoard: {', '.join(part for part in (hoard, ', '.join(treasures)) if part)}")
    return lines


async def nature_lines(session: AsyncSession, entity: EntityRow) -> list[str]:
    if entity.entity_type is EntityType.SPECIES:
        return await species_nature(session, entity)
    if entity.entity_type is EntityType.BEAST:
        return await beast_nature(session, entity)
    return []
