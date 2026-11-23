from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import WORLD_TYPE_TRAITS, having
from aerona.catalog.nature_kinds50 import PRESERVATIONS
from aerona.constants.units import PERCENT
from aerona.core.total import partial
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import LegendProfileRow
from aerona.db.tables.discovery import TheoryAdherentRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.lifecycle_ends import LifecycleStateRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.disease import OutbreakStatus, SpreadPath
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind, TemperatureBand
from aerona.domain.enums.fossil import FossilReading, FossilSource, Preservation
from aerona.domain.enums.life_traits import WorldTypeTrait
from aerona.domain.enums.lifecycle_end import LifecycleState
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.mind.book import values_for
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import has_stat, scale_stat, shift_stat
from aerona.engine.recording.record import record

COLD_WORLDS = having(WORLD_TYPE_TRAITS, WorldTypeTrait.COLD_WORLDS)
DIGGINGS = (StructureKind.MINE, StructureKind.QUARRY)
UPHEAVALS = (EngineKind.EARTHQUAKE, EngineKind.FLOOD)
FINDERS = (EntityType.SETTLEMENT, EntityType.PEOPLE)
READINGS = (
    (ValueAxis.SUPERSTITION, FossilReading.LEGEND),
    (ValueAxis.PIETY, FossilReading.RELIC),
    (ValueAxis.KNOWLEDGE, FossilReading.DEEP_TIME),
    (ValueAxis.WEALTH, FossilReading.MATERIAL),
    (ValueAxis.MERCY, FossilReading.MEDICINE),
)


ASHEN = frozenset({ScarKind.BURNED.value, ScarKind.CRATER.value})


@dataclass
class FossilTally:
    laid: int = 0
    found: int = 0
    read: int = 0
    rereleased: int = 0


@dataclass(frozen=True)
class Remains:
    entity: EntityRow
    source: FossilSource


async def flagged(session: AsyncSession, flag: EntityFlag) -> set[int]:
    return set(await session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == flag)))


async def remains(ctx: TickContext) -> list[Remains]:
    session = ctx.session
    laid = set(await session.scalars(select(FossilBedRow.source_entity_id).where(FossilBedRow.source_entity_id.is_not(None))))
    extinct = await flagged(session, EntityFlag.EXTINCT)
    mighty = await flagged(session, EntityFlag.MEGAFAUNA)
    earlier = await flagged(session, EntityFlag.PREVIOUS_CREATION)
    found: list[Remains] = []
    for entity in await session.scalars(select(EntityRow).where(EntityRow.id.in_(list(extinct | earlier))).order_by(EntityRow.id)):
        if entity.id in laid:
            continue
        if entity.id in earlier:
            found.append(Remains(entity, FossilSource.PREVIOUS_CREATION))
        elif entity.entity_type is EntityType.SPECIES:
            found.append(Remains(entity, FossilSource.MEGAFAUNA if entity.id in mighty else FossilSource.EXTINCT_SPECIES))
    for beast in await session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.BEAST, EntityRow.status == EntityStatus.DEAD).order_by(EntityRow.id)
    ):
        if beast.id not in laid:
            found.append(Remains(beast, FossilSource.BEAST))
    born = {world_id: epoch for world_id, epoch in await session.execute(select(WorldRow.id, WorldRow.created_epoch))}
    for people in await session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.DEAD).order_by(EntityRow.id)
    ):
        age = ctx.epoch - born.get(people.world_id or 0, ctx.epoch)
        if people.id not in laid and people.world_id in born and age >= ctx.rules.fossils.old_world_epochs:
            found.append(Remains(people, FossilSource.EXTINCT_PEOPLE))
    for corpse in await session.scalars(
        select(EntityRow).where(EntityRow.engine_kind == EngineKind.DEAD_GOD, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    ):
        if corpse.id not in laid:
            found.append(Remains(corpse, FossilSource.GOD))
    return found


async def resting_place(ctx: TickContext, atlas: RegionAtlas, entity: EntityRow) -> int | None:
    if entity.entity_type is EntityType.SPECIES:
        region = await ctx.session.scalar(
            select(SpeciesRangeRow.region_entity_id)
            .where(SpeciesRangeRow.species_entity_id == entity.id)
            .order_by(SpeciesRangeRow.abundance.desc(), SpeciesRangeRow.region_entity_id)
            .limit(1)
        )
        if region is not None:
            return int(region)
    return atlas.top_region(entity.location_id) or atlas.top_region(entity.id)


async def sealed_disease(ctx: TickContext, region_id: int) -> int | None:
    eradicated = select(LifecycleStateRow.holder_entity_id).where(LifecycleStateRow.state == LifecycleState.ERADICATED)
    found = await ctx.session.scalar(
        select(OutbreakRow.disease_entity_id)
        .where(OutbreakRow.region_entity_id == region_id, OutbreakRow.disease_entity_id.in_(eradicated))
        .order_by(OutbreakRow.disease_entity_id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def is_frozen(ctx: TickContext, region_id: int, world_id: int | None) -> bool:
    world = await ctx.session.get(WorldRow, world_id) if world_id is not None else None
    land = await ctx.session.get(RegionEnvironmentRow, region_id)
    return (world is not None and world.world_type in COLD_WORLDS) or (land is not None and land.temperature_band is TemperatureBand.FROZEN)


async def preservation_of(ctx: TickContext, region_id: int, frozen: bool) -> Preservation:
    table = ctx.rules.fossils
    land = await ctx.session.get(RegionEnvironmentRow, region_id)
    if frozen:
        return Preservation.ICE
    if land is not None and (land.scars or {}).keys() & ASHEN:
        return Preservation.ASH
    if land is not None and land.wetland >= table.bog_wetland:
        return Preservation.BOG
    if land is not None and land.rainfall < table.dry_rainfall:
        return Preservation.DRY
    return Preservation.ROCK


def depth_of(ctx: TickContext, bed: FossilBedRow) -> int:
    return clamp_int(bed.layer + (ctx.epoch - bed.laid_epoch) * ctx.rules.fossils.layer_per_epoch, 0, PERCENT)


async def lay_beds(ctx: TickContext, atlas: RegionAtlas, tally: FossilTally) -> None:
    table = ctx.rules.fossils
    for item in await remains(ctx):
        region = await resting_place(ctx, atlas, item.entity)
        if region is None or held(region):
            continue
        frozen = await is_frozen(ctx, region, item.entity.world_id)
        richness = (
            table.dead_god_richness
            if item.source is FossilSource.GOD
            else table.richness
            if item.source in {FossilSource.EXTINCT_SPECIES, FossilSource.EXTINCT_PEOPLE}
            else table.megafauna_richness
        )
        ctx.session.add(
            FossilBedRow(
                region_entity_id=region,
                world_id=item.entity.world_id,
                source=item.source,
                source_entity_id=item.entity.id,
                richness=richness,
                frozen=frozen,
                preservation=await preservation_of(ctx, region, frozen),
                disease_entity_id=await sealed_disease(ctx, region) if frozen else None,
                laid_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.laid += 1
    await ctx.session.flush()


async def disturbed(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> float:
    table = ctx.rules.fossils
    chance = float(table.find_pct)
    hosts = await ctx.session.scalars(select(StructureProfileRow.host_entity_id).where(StructureProfileRow.kind.in_(DIGGINGS)))
    if any(atlas.top_region(host) == region_id for host in hosts if host is not None):
        chance += table.mine_pct
    shaken = await ctx.session.scalar(
        select(func.count())
        .select_from(EntityRow)
        .where(EntityRow.location_id == region_id, EntityRow.engine_kind.in_(UPHEAVALS), EntityRow.birth_epoch == ctx.epoch)
    )
    if shaken:
        chance += table.erosion_pct
    return chance


async def finder_in(ctx: TickContext, region_id: int) -> EntityRow | None:
    for kind in FINDERS:
        found = await ctx.session.scalar(
            select(EntityRow)
            .where(EntityRow.location_id == region_id, EntityRow.entity_type == kind, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
            .limit(1)
        )
        if found is not None and not held(found.id):
            return found
    return None


async def reading_of(ctx: TickContext, finder: EntityRow) -> FossilReading:
    values = await values_for(ctx.session, finder.id)
    strongest = max(READINGS, key=lambda item: (values.get(item[0], 0), -READINGS.index(item)))
    return strongest[1] if values.get(strongest[0], 0) >= ctx.rules.fossils.reading_from else FossilReading.UNREAD


async def tell_legend(ctx: TickContext, bed: FossilBedRow, finder: EntityRow) -> None:
    for legend in await ctx.session.scalars(select(LegendProfileRow)):
        if finder.id in legend.tellers and "credence" not in legend.locked:
            legend.credence = clamp_int(legend.credence + ctx.rules.fossils.legend_credence, 0, PERCENT)


async def revere(ctx: TickContext, bed: FossilBedRow, finder: EntityRow) -> None:
    for cult in await ctx.session.scalars(
        select(EntityRow).where(
            EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.in_([bed.region_entity_id, finder.id])
        )
    ):
        if not held(cult.id):
            scale_stat(ctx.rules, cult, "followers", 1 + ctx.rules.fossils.relic_followers_pct / PERCENT, default=0)


async def overturn(ctx: TickContext, bed: FossilBedRow, finder: EntityRow) -> None:
    for row in await ctx.session.scalars(select(TheoryAdherentRow).where(TheoryAdherentRow.adherent_entity_id == finder.id)):
        if "strength" not in row.locked:
            row.strength = clamp_int(row.strength + ctx.rules.fossils.deep_time_strength, 0, PERCENT)


async def work_remains(ctx: TickContext, bed: FossilBedRow, finder: EntityRow) -> None:
    units = round_half_up(bed.richness / 10 * ctx.rules.fossils.material_yield)
    material = MaterialKind.DIVINE_TISSUE if bed.source is FossilSource.GOD else MaterialKind.CALCIFIED_TISSUE
    await goods_of(ctx.session, ctx.epoch).add(finder.id, CommodityKind.ORE, units, GoodsFlow.EXTRACTION, material=material)


async def grind_remains(ctx: TickContext, bed: FossilBedRow, finder: EntityRow) -> None:
    table = ctx.rules.fossils
    await goods_of(ctx.session, ctx.epoch).add(
        finder.id, CommodityKind.MEDICINE, round_half_up(bed.richness / 10 * table.medicine_demand), GoodsFlow.EXTRACTION
    )
    if table.medicine_effect and has_stat(finder, "hp"):
        shift_stat(finder, "hp", table.medicine_effect, 0)


READ_EFFECTS: Mapping[FossilReading, Callable[[TickContext, FossilBedRow, EntityRow], Awaitable[None]]] = partial(
    FossilReading,
    {
        FossilReading.LEGEND: tell_legend,
        FossilReading.RELIC: revere,
        FossilReading.DEEP_TIME: overturn,
        FossilReading.MATERIAL: work_remains,
        FossilReading.MEDICINE: grind_remains,
    },
    without=(FossilReading.UNREAD,),
)


async def told(ctx: TickContext, bed: FossilBedRow, finder: EntityRow) -> None:
    if bed.reading in READ_EFFECTS:
        await READ_EFFECTS[bed.reading](ctx, bed, finder)
    if bed.source is FossilSource.GOD:
        ground = await ctx.session.get(RegionEnvironmentRow, bed.region_entity_id)
        if ground is not None and "sacredness" not in ground.locked and not held(ground.entity_id):
            ground.sacredness = clamp_int(ground.sacredness + ctx.rules.fossils.dead_god_draw, 0, PERCENT)


async def reveal(ctx: TickContext, bed: FossilBedRow, finder: EntityRow | None, tally: FossilTally) -> None:
    table = ctx.rules.fossils
    bed.found_epoch = ctx.epoch
    bed.finder_entity_id = finder.id if finder is not None else None
    if "layer" not in bed.locked:
        bed.layer = depth_of(ctx, bed)
    tally.found += 1
    luxuries = 0
    if finder is not None:
        if "reading" not in bed.locked:
            bed.reading = await reading_of(ctx, finder)
        tally.read += int(bed.reading is not FossilReading.UNREAD)
        await told(ctx, bed, finder)
        units = round_half_up(bed.richness / 10 * table.luxury_per_10)
        luxuries = max(0, units)
        if units > 0:
            await goods_of(ctx.session, ctx.epoch).add(finder.id, CommodityKind.LUXURIES, units, GoodsFlow.EXTRACTION)
            await record(
                ctx,
                "land.fossil_traded",
                roles={IncidentRole.PLACE: bed.region_entity_id, IncidentRole.ACTOR: finder.id},
                facts={"units": units},
                place=bed.region_entity_id,
            )
        fuel_kind = PRESERVATIONS[bed.preservation].fuel
        fuel = round_half_up(bed.richness / 10 * table.fuel_per_10) if fuel_kind is not None else 0
        if fuel > 0 and fuel_kind is not None:
            await goods_of(ctx.session, ctx.epoch).add(finder.id, fuel_kind, fuel, GoodsFlow.EXTRACTION)
    if bed.frozen and bed.disease_entity_id is not None:
        ctx.session.add(
            OutbreakRow(
                disease_entity_id=bed.disease_entity_id,
                region_entity_id=bed.region_entity_id,
                path=SpreadPath.ORIGIN,
                status=OutbreakStatus.ACTIVE,
                severity=bed.richness,
                started_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.rereleased += 1
    await record(
        ctx,
        f"fossil.{bed.reading.value}",
        roles={
            IncidentRole.PLACE: bed.region_entity_id,
            IncidentRole.ACTOR: finder.id if finder is not None else None,
            IncidentRole.SUBJECT: bed.source_entity_id,
        },
        facts={"source": bed.source, "reading": bed.reading, "richness": bed.richness, "luxuries": luxuries},
        place=bed.region_entity_id,
        world_id=bed.world_id,
    )
    await ctx.session.flush()


async def find_beds(ctx: TickContext, atlas: RegionAtlas, tally: FossilTally) -> None:
    for bed in list(await ctx.session.scalars(select(FossilBedRow).where(FossilBedRow.found_epoch.is_(None)).order_by(FossilBedRow.id))):
        if "found_epoch" in bed.locked or held(bed.region_entity_id):
            continue
        shallow = 1 - depth_of(ctx, bed) * ctx.rules.fossils.layer_find_cut_pct / PERCENT / PERCENT
        if ctx.rng(f"fossil.find.{bed.id}.{ctx.epoch}").chance(await disturbed(ctx, atlas, bed.region_entity_id) * shallow):
            await reveal(ctx, bed, await finder_in(ctx, bed.region_entity_id), tally)


async def keep_fossils(ctx: TickContext, tally: FossilTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    await lay_beds(ctx, atlas, tally)
    await find_beds(ctx, atlas, tally)
    await ctx.session.flush()
