from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.flora import PlantProduct, plant_product_of
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.ecology import SpeciesHostRow, SpeciesProfileRow, SpeciesRangeRow, SpeciesUseRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.flora import CropPestRow, PlantProfileRow, RegionCropRow
from aerona.db.tables.mind import SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.ecology import GROWN, SOWN, Biochemistry, Cultivation, Diet, SpeciesClass, SpeciesUse
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherEffect
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.ecology.biochemistry import bearable, tolerated
from aerona.engine.ecology.profiles import PEST_HUNTERS, SHELLED, Nature, SpeciesSpec, add_plant_profile, cycle_of, plant_products, profile_of
from aerona.engine.environment.weather import Weather
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

PEST_TRAITS = frozenset({CreatureTrait.CROP_PEST})
SHELLED_SIZES = SHELLED
HERD_GOODS = {"milk": CommodityKind.MILK, "wool": CommodityKind.WOOL, "eggs": CommodityKind.EGGS}


@dataclass(frozen=True)
class CropField:
    plant_id: int
    share: int
    products: tuple[tuple[PlantProduct, int], ...]


@dataclass(frozen=True)
class CropYear:
    degrees: int = 0
    moisture: int = 0


AVERAGE_YEAR = CropYear()


def crop_year(rules: Rules, weather: Weather) -> CropYear:
    table = rules.flora
    heat = weather.effect(WeatherEffect.HEAT) - weather.effect(WeatherEffect.COLD)
    return CropYear(round(heat * table.weather_degrees / PERCENT), round(weather.effect(WeatherEffect.WET) * table.weather_moisture_pct / PERCENT))


def crop_fit(
    rules: Rules,
    profile: SpeciesProfileRow,
    plant: PlantProfileRow,
    land: RegionEnvironmentRow,
    *,
    seasons: int | None,
    allowed: tuple[Biochemistry, ...],
    year: CropYear = AVERAGE_YEAR,
) -> float:
    if not bearable(profile.biochemistry, allowed):
        return 0.0
    table = rules.flora
    warmth = land.temperature + year.degrees
    moisture = min(PERCENT, land.moisture + year.moisture)
    over = max(0, warmth - profile.temperature_max - table.temperature_slack, profile.temperature_min - warmth - table.temperature_slack)
    heat = max(0.0, 1 - over * table.temperature_penalty_pct / PERCENT)
    water = max(0.0, 1 - abs(moisture - profile.water_need) / PERCENT * table.water_penalty_pct / PERCENT)
    lack = max(0, plant.soil_need - land.soil_fertility)
    soil = max(0.0, 1 - lack / max(1, plant.soil_need) * table.soil_penalty_pct / PERCENT)
    short = max(0, plant.growing_seasons - seasons) if seasons is not None else 0
    season = max(0.0, 1 - short * table.season_penalty_pct / PERCENT)
    return heat * water * soil * season


@dataclass
class CropBook:
    rules: Rules
    lands: dict[int, RegionEnvironmentRow]
    crops: dict[int, list[RegionCropRow]] = field(default_factory=lambda: defaultdict(list))
    profiles: dict[int, SpeciesProfileRow] = field(default_factory=dict)
    plants: dict[int, PlantProfileRow] = field(default_factory=dict)
    yields: dict[int, list[SpeciesYieldRow]] = field(default_factory=lambda: defaultdict(list))
    seasons: dict[int, int] = field(default_factory=dict)
    life: dict[int, tuple[Biochemistry, ...]] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules, lands: dict[int, RegionEnvironmentRow] | None = None) -> "CropBook":
        if lands is None:
            lands = {row.entity_id: row for row in await session.scalars(select(RegionEnvironmentRow))}
        book = cls(rules, lands)
        for row in await session.scalars(select(RegionCropRow).order_by(RegionCropRow.region_entity_id, RegionCropRow.plant_entity_id)):
            book.crops[row.region_entity_id].append(row)
        book.plants = {row.species_entity_id: row for row in await session.scalars(select(PlantProfileRow))}
        book.profiles = {
            row.species_entity_id: row
            for row in await session.scalars(select(SpeciesProfileRow).where(SpeciesProfileRow.species_entity_id.in_(list(book.plants))))
        }
        for item in await session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.species_entity_id.in_(list(book.plants)))):
            book.yields[item.species_entity_id].append(item)
        floor = rules.flora.growing_season_floor
        for season in await session.scalars(select(WorldSeasonRow)):
            book.seasons[season.world_id] = book.seasons.get(season.world_id, 0) + (1 if season.growth >= floor else 0)
        worlds = {land.world_id for land in lands.values() if land.world_id is not None}
        for world_id in sorted(worlds):
            book.life[world_id] = await tolerated(session, world_id)
        return book

    def fit(self, plant_id: int, region_id: int, year: CropYear = AVERAGE_YEAR) -> float:
        land, profile, plant = self.lands.get(region_id), self.profiles.get(plant_id), self.plants.get(plant_id)
        if land is None or profile is None or plant is None:
            return 0.0
        world = land.world_id
        return crop_fit(
            self.rules,
            profile,
            plant,
            land,
            seasons=self.seasons.get(world) if world is not None else None,
            allowed=self.life.get(world, tuple(Biochemistry)) if world is not None else tuple(Biochemistry),
            year=year,
        )

    def factor(self, region_id: int, year: CropYear = AVERAGE_YEAR) -> float:
        rows = [row for row in self.crops.get(region_id, []) if row.share > 0]
        total = sum(row.share for row in rows)
        if total <= 0:
            return 1.0
        weighted = sum(row.share * self.fit(row.plant_entity_id, region_id, year) for row in rows) / total
        return 1 - self.rules.flora.crop_weight_pct / PERCENT * (1 - weighted)

    def fields(self, region_id: int) -> list[CropField]:
        found: list[CropField] = []
        for row in self.crops.get(region_id, []):
            products = tuple(
                (matched, item.rate)
                for item in self.yields.get(row.plant_entity_id, [])
                if (matched := plant_product_of(item.product, item.commodity)) is not None
            )
            if row.share > 0 and products:
                found.append(CropField(row.plant_entity_id, row.share, products))
        return found


def split_fields(rules: Rules, fields: float, crops: list[CropField]) -> dict[CommodityKind, float]:
    total = sum(crop.share for crop in crops)
    found: dict[CommodityKind, float] = defaultdict(float)
    if total <= 0:
        return found
    table = rules.flora
    for crop in crops:
        land = fields * crop.share / total
        food = [(product, rate) for product, rate in crop.products if product.food]
        weight = sum(rate for _, rate in food)
        for product, rate in food:
            found[product.commodity] += land * rate / weight
        side = table.side_yield_pct if food else table.sole_yield_pct
        for product, rate in crop.products:
            if not product.food:
                found[product.commodity] += land * rate * side / PERCENT
    return found


async def agriculture_level(session: AsyncSession, holder_ids: list[int]) -> int:
    if not holder_ids:
        return 0
    found = await session.scalar(
        select(HolderLevelRow.level)
        .where(HolderLevelRow.holder_entity_id.in_(holder_ids), HolderLevelRow.branch == KnowledgeBranch.AGRICULTURE)
        .order_by(HolderLevelRow.level.desc())
        .limit(1)
    )
    return int(found or 0)


async def farmers_in(session: AsyncSession, atlas: RegionAtlas, region_id: int) -> list[EntityRow]:
    found: list[EntityRow] = []
    for community_id in atlas.communities_in(region_id):
        community = await session.get(EntityRow, community_id)
        if community is not None and community.status is EntityStatus.CANON and (stat(community, "population") or 0) > 0:
            found.append(community)
    return found


def add_crop(ctx: TickContext, book: CropBook, region_id: int, plant_id: int) -> RegionCropRow:
    row = RegionCropRow(region_entity_id=region_id, plant_entity_id=plant_id, share=ctx.rules.flora.new_crop_share, since_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    book.crops[region_id].append(row)
    return row


async def gather_wild(ctx: TickContext, book: CropBook, atlas: RegionAtlas) -> dict[str, int]:
    table = ctx.rules.flora
    counts = {"plants_gathered": 0, "plants_sown": 0}
    growing: dict[int, list[int]] = defaultdict(list)
    for species_id, region_id in await ctx.session.execute(
        select(SpeciesRangeRow.species_entity_id, SpeciesRangeRow.region_entity_id)
        .where(SpeciesRangeRow.species_entity_id.in_(list(book.plants)), SpeciesRangeRow.abundance > 0)
        .order_by(SpeciesRangeRow.species_entity_id, SpeciesRangeRow.region_entity_id)
    ):
        growing[species_id].append(region_id)
    for plant_id, regions in sorted(growing.items()):
        plant = book.plants[plant_id]
        if held(plant_id) or "cultivation" in plant.locked or plant.cultivation in SOWN:
            continue
        farmed = [region for region in regions if await farmers_in(ctx.session, atlas, region)]
        if not farmed:
            continue
        rng = ctx.rng(f"flora.gather.{plant_id}.{ctx.epoch}")
        if plant.cultivation is Cultivation.WILD and rng.chance(table.gather_pct):
            plant.cultivation, plant.since_epoch = Cultivation.GATHERED, ctx.epoch
            counts["plants_gathered"] += 1
            continue
        if plant.cultivation is not Cultivation.GATHERED or not rng.chance(table.cultivate_pct):
            continue
        for region in farmed:
            farmers = await farmers_in(ctx.session, atlas, region)
            if await agriculture_level(ctx.session, [item.id for item in farmers]) < table.cultivate_level or held(region):
                continue
            plant.cultivation, plant.since_epoch = Cultivation.CULTIVATED, ctx.epoch
            if all(row.plant_entity_id != plant_id for row in book.crops.get(region, [])):
                add_crop(ctx, book, region, plant_id)
            counts["plants_sown"] += 1
            species = await ctx.session.get(EntityRow, plant_id)
            if species is not None:
                await note(ctx, f"The farmers of {farmers[0].name} began to sow {species.name}.", key="flora.sown", ids=[farmers[0].id, plant_id])
            break
    return counts


def rebalance(rules: Rules, book: CropBook, region_id: int) -> int:
    rows = book.crops.get(region_id, [])
    free = [row for row in rows if "share" not in row.locked]
    if not free:
        return 0
    fits = {row.plant_entity_id: book.fit(row.plant_entity_id, region_id) for row in free}
    room = PERCENT - sum(row.share for row in rows if "share" in row.locked)
    weight = sum(fits.values())
    changed = 0
    for row in free:
        target = room * fits[row.plant_entity_id] / weight if weight > 0 else room / len(free)
        moved = clamp_int(row.share + (target - row.share) * rules.flora.share_drift / PERCENT, 0, PERCENT)
        changed += int(moved != row.share)
        row.share = moved
    scale = sum(row.share for row in free)
    if scale > 0 and room >= 0:
        for row in free:
            row.share = clamp_int(row.share * room / scale, 0, PERCENT)
    return changed


async def sow(ctx: TickContext, book: CropBook, atlas: RegionAtlas) -> dict[str, int]:
    table = ctx.rules.flora
    counts = {"crop_shares_moved": 0, "crops_dropped": 0, "crops_spread": 0}
    for region_id in sorted(book.crops):
        if held(region_id):
            continue
        for row in list(book.crops[region_id]):
            if row.share < table.min_share and "share" not in row.locked and len(book.crops[region_id]) > 1:
                book.crops[region_id].remove(row)
                await ctx.session.delete(row)
                counts["crops_dropped"] += 1
        counts["crop_shares_moved"] += rebalance(ctx.rules, book, region_id)
    spread = 0
    for region_id in sorted(book.crops):
        for row in list(book.crops[region_id]):
            if spread >= table.spread_cap:
                break
            for neighbour in atlas.neighbour_regions(region_id):
                sown = book.crops.get(neighbour, [])
                if held(neighbour) or len(sown) >= table.crop_cap or any(item.plant_entity_id == row.plant_entity_id for item in sown):
                    continue
                if book.fit(row.plant_entity_id, neighbour) * PERCENT < table.spread_fit or not await farmers_in(ctx.session, atlas, neighbour):
                    continue
                if ctx.rng(f"flora.spread.{row.plant_entity_id}.{neighbour}.{ctx.epoch}").chance(table.spread_pct):
                    add_crop(ctx, book, neighbour, row.plant_entity_id)
                    rebalance(ctx.rules, book, neighbour)
                    spread += 1
                    break
    counts["crops_spread"] = spread
    return counts


async def master_farmer(session: AsyncSession, community_ids: list[int]) -> int:
    mortals = select(EntityRow.id).where(
        EntityRow.location_id.in_(community_ids), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    found = await session.scalar(
        select(SkillRow.level).where(SkillRow.holder_node_id.in_(mortals), SkillRow.skill == SkillKind.FORAGING).order_by(SkillRow.level.desc()).limit(1)
    )
    return int(found or 0)


async def breed_cultivar(ctx: TickContext, book: CropBook, row: RegionCropRow, keeper: EntityRow) -> EntityRow | None:
    table = ctx.rules.flora
    parent = await ctx.session.get(EntityRow, row.plant_entity_id)
    profile, plant = book.profiles.get(row.plant_entity_id), book.plants.get(row.plant_entity_id)
    if parent is None or profile is None or plant is None:
        return None
    child = await create_record(
        ctx,
        RecordSpec(
            name=f"{keeper.name} {parent.name}",
            entity_type=EntityType.SPECIES,
            stats=parent.stats,
            body=f"A cultivar bred from {parent.name} by the farmers of {keeper.name}.",
            power=parent.power_level,
            world_id=keeper.world_id,
            location_id=row.region_entity_id,
            subtype="cultivar",
            engine_kind=EngineKind.DOMESTICATED,
        ),
    )
    await connect(ctx.session, child.id, parent.id, BondKind.DESCENDS_FROM, ctx.epoch, description="bred by farmers")
    products = tuple(
        dict.fromkeys(matched.product for item in book.yields.get(parent.id, []) if (matched := plant_product_of(item.product, item.commodity)) is not None)
    )
    spec = SpeciesSpec(
        body_plan=profile.body_plan,
        size_class=profile.size_class,
        diet=profile.diet,
        species_class=profile.species_class,
        biochemistry=profile.biochemistry,
        growth_cycle=plant.growth_cycle,
        plant_yields=products,
    )
    fresh = await profile_of(ctx, child, spec)
    fresh.temperature_min = profile.temperature_min - table.cultivar_hardiness
    fresh.temperature_max = profile.temperature_max + table.cultivar_hardiness
    fresh.water_need = profile.water_need
    bred = await ctx.session.get(PlantProfileRow, child.id)
    if bred is not None:
        bred.cultivation, bred.cultivar_of_id = Cultivation.CULTIVAR, parent.id
        bred.soil_need = clamp_int(plant.soil_need - table.cultivar_soil, 0, PERCENT)
        bred.growing_seasons = plant.growing_seasons
        book.plants[child.id] = bred
    rates = {item.product: item.rate for item in book.yields.get(parent.id, [])}
    for item in await ctx.session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.species_entity_id == child.id)):
        item.rate = max(rates.get(item.product, item.rate) + 1, round_half_up(rates.get(item.product, item.rate) * (1 + table.cultivar_yield_pct / PERCENT)))
        book.yields[child.id].append(item)
    book.profiles[child.id] = fresh
    replacement = RegionCropRow(region_entity_id=row.region_entity_id, plant_entity_id=child.id, share=row.share, since_epoch=ctx.epoch, locked=[])
    book.crops[row.region_entity_id].remove(row)
    await ctx.session.delete(row)
    ctx.session.add(replacement)
    book.crops[row.region_entity_id].append(replacement)
    return child


async def breed_cultivars(ctx: TickContext, book: CropBook, atlas: RegionAtlas) -> int:
    table = ctx.rules.flora
    bred = 0
    for region_id in sorted(book.crops):
        if held(region_id):
            continue
        for row in list(book.crops[region_id]):
            plant = book.plants.get(row.plant_entity_id)
            if (
                bred >= table.cultivar_cap
                or plant is None
                or plant.cultivation is not Cultivation.CULTIVATED
                or ctx.epoch - row.since_epoch < table.cultivar_epochs
            ):
                continue
            farmers = await farmers_in(ctx.session, atlas, region_id)
            if not farmers or await master_farmer(ctx.session, [item.id for item in farmers]) < table.cultivar_skill:
                continue
            if not ctx.rng(f"flora.cultivar.{row.plant_entity_id}.{region_id}.{ctx.epoch}").chance(table.cultivar_pct):
                continue
            child = await breed_cultivar(ctx, book, row, farmers[0])
            if child is not None:
                bred += 1
                await note(ctx, f"The farmers of {farmers[0].name} bred a new cultivar, {child.name}.", key="flora.cultivar", ids=[farmers[0].id, child.id])
    return bred


async def pest_ids(session: AsyncSession) -> set[int]:
    traited = set(await session.scalars(select(EntityTraitRow.entity_id).where(EntityTraitRow.trait.in_(list(PEST_TRAITS)))))
    vermin = set(await session.scalars(select(SpeciesProfileRow.species_entity_id).where(SpeciesProfileRow.species_class == SpeciesClass.VERMIN)))
    return traited | vermin


async def link_pests(ctx: TickContext, book: CropBook) -> int:
    pests = await pest_ids(ctx.session)
    linked = {(plant, pest) for plant, pest in await ctx.session.execute(select(CropPestRow.plant_entity_id, CropPestRow.pest_entity_id))}
    added = 0
    for pest_id, region_id in await ctx.session.execute(
        select(SpeciesRangeRow.species_entity_id, SpeciesRangeRow.region_entity_id)
        .where(SpeciesRangeRow.species_entity_id.in_(list(pests)), SpeciesRangeRow.abundance > 0)
        .order_by(SpeciesRangeRow.species_entity_id, SpeciesRangeRow.region_entity_id)
    ):
        crops = sorted(book.crops.get(region_id, []), key=lambda row: (-row.share, row.plant_entity_id))
        if not crops or held(pest_id) or held(crops[0].plant_entity_id) or any((row.plant_entity_id, pest_id) in linked for row in crops):
            continue
        if ctx.rng(f"flora.pest.{pest_id}.{region_id}.{ctx.epoch}").chance(ctx.rules.flora.pest_link_pct):
            ctx.session.add(CropPestRow(plant_entity_id=crops[0].plant_entity_id, pest_entity_id=pest_id, since_epoch=ctx.epoch, locked=[]))
            linked.add((crops[0].plant_entity_id, pest_id))
            added += 1
    return added


async def host_share(session: AsyncSession, pest_id: int, region_crops: list[RegionCropRow]) -> float | None:
    hosts = set(await session.scalars(select(CropPestRow.plant_entity_id).where(CropPestRow.pest_entity_id == pest_id)))
    if not hosts:
        return None
    return sum(row.share for row in region_crops if row.plant_entity_id in hosts) / PERCENT


async def blight(ctx: TickContext, book: CropBook) -> int:
    raging = defaultdict(set)
    for disease_id, region_id in await ctx.session.execute(
        select(OutbreakRow.disease_entity_id, OutbreakRow.region_entity_id).where(OutbreakRow.status == OutbreakStatus.ACTIVE)
    ):
        raging[region_id].add(disease_id)
    hosts = defaultdict(set)
    for species_id, disease_id in await ctx.session.execute(
        select(SpeciesHostRow.species_entity_id, SpeciesHostRow.disease_entity_id).where(
            SpeciesHostRow.immune.is_(False), SpeciesHostRow.species_entity_id.in_(list(book.plants))
        )
    ):
        hosts[species_id].add(disease_id)
    struck = 0
    for region_id, rows in sorted(book.crops.items()):
        land = book.lands.get(region_id)
        if land is None or held(region_id) or "harvest_pct" in land.locked:
            continue
        loss = sum(row.share for row in rows if hosts.get(row.plant_entity_id, set()) & raging.get(region_id, set())) / PERCENT
        if loss > 0:
            land.harvest_pct = clamp_int(land.harvest_pct - round_half_up(ctx.rules.flora.blight_loss * loss), 0, PERCENT * 2)
            struck += 1
    return struck


async def plant_backfill(ctx: TickContext) -> int:
    added = 0
    plants = set(await ctx.session.scalars(select(PlantProfileRow.species_entity_id)))
    for profile in list(await ctx.session.scalars(select(SpeciesProfileRow).where(SpeciesProfileRow.species_class.in_(list(GROWN))))):
        if profile.species_entity_id in plants or held(profile.species_entity_id):
            continue
        nature = Nature(
            profile.body_plan,
            profile.size_class,
            profile.diet,
            profile.sociality,
            profile.nocturnal,
            profile.migratory,
            profile.species_class,
            profile.biochemistry,
        )
        add_plant_profile(ctx, profile.species_entity_id, cycle_of(SpeciesSpec(), nature, profile.lifespan_years))
        added += 1
    await ctx.session.flush()
    return added


FLORA_FIXUP = "flora.typed_flora"
VOID_PLANS = frozenset({BodyPlan.INCORPOREAL})
STONE_PLANS = frozenset({BodyPlan.CONSTRUCT})


def first_biochemistry(profile: SpeciesProfileRow) -> Biochemistry | None:
    if profile.diet is Diet.VOID:
        return Biochemistry.VOID
    if profile.diet is Diet.SOUL or profile.body_plan in VOID_PLANS:
        return Biochemistry.SPIRIT
    if profile.diet is Diet.MINERAL or profile.body_plan in STONE_PLANS:
        return Biochemistry.SILICON
    return None


async def reclass_plant(ctx: TickContext, profile: SpeciesProfileRow) -> None:
    profile.species_class = SpeciesClass.PLANT
    for item in list(await ctx.session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.species_entity_id == profile.species_entity_id))):
        if plant_product_of(item.product, item.commodity) is None:
            await ctx.session.delete(item)
    nature = Nature(
        profile.body_plan,
        profile.size_class,
        profile.diet,
        profile.sociality,
        profile.nocturnal,
        profile.migratory,
        profile.species_class,
        profile.biochemistry,
    )
    cycle = cycle_of(SpeciesSpec(), nature, profile.lifespan_years)
    for product in plant_products(nature, cycle, ()):
        if await ctx.session.get(SpeciesYieldRow, (profile.species_entity_id, product.product)) is None:
            ctx.session.add(
                SpeciesYieldRow(
                    species_entity_id=profile.species_entity_id,
                    product=product.product,
                    commodity=product.commodity,
                    material=product.material,
                    rate=product.rate,
                )
            )
    for use in list(await ctx.session.scalars(select(SpeciesUseRow).where(SpeciesUseRow.species_entity_id == profile.species_entity_id))):
        if use.use is not SpeciesUse.MAGIC:
            await ctx.session.delete(use)


async def flora_backfill(ctx: TickContext) -> dict[str, int]:
    counts = {"plants": 0, "vermin": 0, "biochemistry": 0, "herd_goods": 0, "pest_hunters": 0}
    if await ctx.session.get(AppliedFixupRow, FLORA_FIXUP) is not None:
        return counts
    small = set(await ctx.session.scalars(select(EntityTraitRow.entity_id).where(EntityTraitRow.trait == CreatureTrait.CROP_PEST)))
    for profile in list(await ctx.session.scalars(select(SpeciesProfileRow).order_by(SpeciesProfileRow.species_entity_id))):
        if held(profile.species_entity_id):
            continue
        locked = set(profile.locked)
        if "species_class" not in locked and profile.species_class is SpeciesClass.ANIMAL:
            if profile.diet is Diet.PHOTOSYNTHETIC or profile.body_plan is BodyPlan.ARBOREAL:
                await reclass_plant(ctx, profile)
                counts["plants"] += 1
            elif profile.species_entity_id in small and profile.size_class in SHELLED_SIZES:
                profile.species_class = SpeciesClass.VERMIN
                counts["vermin"] += 1
        chosen = first_biochemistry(profile)
        if "biochemistry" not in locked and chosen is not None and profile.biochemistry is Biochemistry.CARBON_WATER:
            profile.biochemistry = chosen
            counts["biochemistry"] += 1
        hunter = profile.species_class not in GROWN and profile.diet in PEST_HUNTERS and profile.size_class in SHELLED_SIZES
        if hunter and await ctx.session.get(SpeciesUseRow, (profile.species_entity_id, SpeciesUse.PEST_CONTROL)) is None:
            ctx.session.add(SpeciesUseRow(species_entity_id=profile.species_entity_id, use=SpeciesUse.PEST_CONTROL))
            counts["pest_hunters"] += 1
    for item in list(await ctx.session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.product.in_(list(HERD_GOODS))))):
        kind = HERD_GOODS[item.product]
        if item.commodity is not kind and not held(item.species_entity_id):
            item.commodity, item.material = kind, None
            counts["herd_goods"] += 1
    ctx.session.add(AppliedFixupRow(key=FLORA_FIXUP, result=counts))
    await ctx.session.flush()
    return counts
