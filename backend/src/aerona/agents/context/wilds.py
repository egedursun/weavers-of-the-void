from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import spoken
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import BeastProfileRow, HerdRow, SpeciesProductRow, SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.flora import CropPestRow, PlantProfileRow, RegionCropRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.ecology import SpeciesClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.ecology.anatomy import anatomy_lines
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat


def words(value: str) -> str:
    return value.replace("_", " ")


async def crop_lines(session: AsyncSession, region: int | None) -> list[str]:
    if region is None:
        return []
    rows = await session.execute(
        select(EntityRow.name, RegionCropRow.share, PlantProfileRow.cultivation)
        .join(RegionCropRow, RegionCropRow.plant_entity_id == EntityRow.id)
        .outerjoin(PlantProfileRow, PlantProfileRow.species_entity_id == EntityRow.id)
        .where(RegionCropRow.region_entity_id == region, EntityRow.status == EntityStatus.CANON)
        .order_by(RegionCropRow.share.desc(), EntityRow.name)
    )
    return [f"{name} ({share}% of the fields{', ' + spoken(cultivation) if cultivation is not None else ''})" for name, share, cultivation in rows]


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
        wild = [f"{name} ({spoken(diet)}, {abundance} strong)" for name, abundance, diet in rows]
    herds = [
        f"{name} ({head} head, {spoken(stage)}{f'; {trained} trained for {spoken(training)}' if training is not None and trained else ''})"
        for name, head, stage, training, trained in await session.execute(
            select(EntityRow.name, HerdRow.head, HerdRow.stage, HerdRow.training, HerdRow.trained)
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
            beasts.append(f"{beast.name} ({spoken(row.temper)}, terror {stat(beast, 'terror') or 0})")
    return wild, herds, beasts


def flags_of(row: SpeciesProfileRow) -> list[str]:
    return [label for label, held in (("nocturnal", row.nocturnal), ("migratory", row.migratory)) if held]


async def species_nature(session: AsyncSession, species: EntityRow) -> list[str]:
    row = await session.get(SpeciesProfileRow, species.id)
    if row is None:
        return []
    habits = ", ".join(
        [
            spoken(row.species_class),
            f"{spoken(row.biochemistry)} life",
            spoken(row.size_class),
            spoken(row.body_plan),
            spoken(row.diet),
            spoken(row.sociality),
            *flags_of(row),
        ]
    )
    products = ", ".join(
        await session.scalars(select(SpeciesProductRow.product).where(SpeciesProductRow.species_entity_id == species.id).order_by(SpeciesProductRow.product))
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
    lines = [f"nature: {habits}; {spoken(row.stage)}; tameability {row.tameability}, aggression {row.aggression}"]
    if products:
        lines.append(f"yields: {products}")
    if prey:
        lines.append(f"hunts: {', '.join(prey)}")
    if sacred is not None:
        lines.append(f"sacred to {sacred.name}")
    return lines + await plant_lines(session, species, row)


async def plant_lines(session: AsyncSession, species: EntityRow, row: SpeciesProfileRow) -> list[str]:
    plant = await session.get(PlantProfileRow, species.id)
    lines: list[str] = []
    if plant is not None:
        cycle, cultivation = spoken(plant.growth_cycle), spoken(plant.cultivation)
        lines.append(f"grows: {cycle}, needs {plant.growing_seasons} growing seasons and soil of {plant.soil_need}; {cultivation}")
    sown = list(
        await session.scalars(
            select(EntityRow.name)
            .join(RegionCropRow, RegionCropRow.region_entity_id == EntityRow.id)
            .where(RegionCropRow.plant_entity_id == species.id)
            .order_by(EntityRow.name)
        )
    )
    if sown:
        lines.append(f"sown in: {', '.join(sown)}")
    pests = list(
        await session.scalars(
            select(EntityRow.name)
            .join(CropPestRow, CropPestRow.pest_entity_id == EntityRow.id)
            .where(CropPestRow.plant_entity_id == species.id)
            .order_by(EntityRow.name)
        )
    )
    if pests:
        lines.append(f"its pests: {', '.join(pests)}")
    hosts = list(
        await session.scalars(
            select(EntityRow.name)
            .join(CropPestRow, CropPestRow.plant_entity_id == EntityRow.id)
            .where(CropPestRow.pest_entity_id == species.id)
            .order_by(EntityRow.name)
        )
    )
    if hosts or row.species_class is SpeciesClass.VERMIN:
        lines.append(f"a pest of: {', '.join(hosts) or 'stores and fields'}")
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
        f"beast: {spoken(row.size_class)}, {spoken(row.temper)}, endurance {row.endurance}, perception {row.perception}, "
        f"willpower {row.willpower}, intelligence {row.intelligence}, age {row.age} of {row.lifespan}"
    ]
    if hoard or treasures:
        lines.append(f"hoard: {', '.join(part for part in (hoard, ', '.join(treasures)) if part)}")
    return lines


async def nature_lines(session: AsyncSession, entity: EntityRow) -> list[str]:
    if entity.entity_type is EntityType.SPECIES:
        return [*await species_nature(session, entity), *await anatomy_lines(session, entity.id)]
    if entity.entity_type is EntityType.BEAST:
        return [*await beast_nature(session, entity), *await anatomy_lines(session, entity.id)]
    if entity.entity_type is EntityType.REGION:
        crops = await crop_lines(session, entity.id)
        return [f"crops grown here: {', '.join(crops)}"] if crops else []
    return []


async def pet_lines(session: AsyncSession, me: EntityRow) -> list[str]:
    pets = await session.execute(
        select(EntityRow.name, BeastProfileRow.size_class)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .join(BeastProfileRow, BeastProfileRow.beast_entity_id == EntityRow.id)
        .where(BondRow.target_node_id == me.id, BondRow.kind == BondKind.PET_OF, BondRow.state == BondState.ACTIVE, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.name)
    )
    return [f"{name} ({spoken(size)})" for name, size in pets]
