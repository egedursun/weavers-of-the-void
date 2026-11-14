from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.flora import DEFAULT_YIELDS, PLANT_PRODUCTS
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import BodyRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesUseRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.flora import PlantProfileRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.ecology import (
    GRAZERS,
    GROWN,
    SIZE_ORDER,
    Biochemistry,
    Diet,
    GrowthCycle,
    PlantYield,
    SizeClass,
    Sociality,
    SpeciesClass,
    SpeciesUse,
    YieldProduct,
)
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.nature import Dormancy, PlantDefence, Thermoregulation
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.ecology.biochemistry import tolerated
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import shift_bounded, stat, stat_or

T = CreatureTrait
Z = SizeClass
P = BodyPlan
WATER = frozenset({TerrainKind.COAST, TerrainKind.MARSH, TerrainKind.ISLAND, TerrainKind.RIVER_VALLEY})
LIFESPAN = {Z.TINY: 2, Z.SMALL: 6, Z.MEDIUM: 15, Z.LARGE: 25, Z.HUGE: 60, Z.COLOSSAL: 200}
LITTER = {Z.TINY: 8, Z.SMALL: 5, Z.MEDIUM: 3, Z.LARGE: 1, Z.HUGE: 1, Z.COLOSSAL: 1}
METABOLISM = {Z.TINY: 80, Z.SMALL: 65, Z.MEDIUM: 50, Z.LARGE: 40, Z.HUGE: 30, Z.COLOSSAL: 20}
TRAIT_PLANS = ((T.HIVE_MIND, P.INSECTOID), (T.SHAPESHIFTER, P.AMORPHOUS), (T.FLYING, P.AVIAN), (T.AQUATIC, P.AQUATIC))
PLAN_DIETS = {P.ARBOREAL: Diet.PHOTOSYNTHETIC, P.AMORPHOUS: Diet.FILTER, P.CONSTRUCT: Diet.MINERAL, P.INCORPOREAL: Diet.SOUL}
PLAN_TRAITS = {P.AVIAN: T.FLYING, P.AQUATIC: T.AQUATIC, P.SERPENTINE: T.AMBUSH_PREDATOR, P.INSECTOID: T.ARMOURED}
SOCIAL_TRAITS = {Sociality.PACK: T.PACK_HUNTER, Sociality.HIVE: T.HIVE_MIND}
UNEATEN = frozenset({Diet.MINERAL, Diet.VOID, Diet.PHOTOSYNTHETIC})
SHELLED = frozenset({Z.TINY, Z.SMALL})
GREAT = frozenset({Z.HUGE, Z.COLOSSAL})
DRAUGHT = frozenset({Z.LARGE, Z.HUGE})
KEPT_SIZES = frozenset({Z.SMALL, Z.MEDIUM, Z.LARGE})
SIZE_STEP = 25
FLYERS = frozenset({P.AVIAN})


@dataclass(frozen=True)
class Product:
    product: str
    commodity: CommodityKind
    material: MaterialKind | None
    rate: int


MEAT = Product("meat", CommodityKind.LIVESTOCK, None, 2)
HIDE = Product("hide", CommodityKind.CLOTH, MaterialKind.HIDE, 1)
BONE = Product("bone", CommodityKind.TOOLS, MaterialKind.BONE, 1)
IVORY = Product("ivory", CommodityKind.LUXURIES, MaterialKind.IVORY, 1)
CHITIN = Product("chitin", CommodityKind.ARMOUR, MaterialKind.CHITIN, 1)
VENOM = Product("venom", CommodityKind.MEDICINE, None, 1)
SILK = Product("silk", CommodityKind.CLOTH, MaterialKind.CLOTH, 1)
WOOL = Product("wool", CommodityKind.WOOL, None, 1)
MILK = Product("milk", CommodityKind.MILK, None, 1)
EGGS = Product("eggs", CommodityKind.EGGS, None, 1)
FEATHERS = Product("feathers", CommodityKind.LUXURIES, None, 1)
REAGENTS = Product("magic reagents", CommodityKind.MAGICAL_REAGENTS, None, 1)
DRAGONBONE = Product("dragonbone", CommodityKind.WEAPONS, MaterialKind.DRAGONBONE, 1)
PRODUCTS = {
    YieldProduct.MEAT: MEAT,
    YieldProduct.HIDE: HIDE,
    YieldProduct.BONE: BONE,
    YieldProduct.IVORY: IVORY,
    YieldProduct.CHITIN: CHITIN,
    YieldProduct.VENOM: VENOM,
    YieldProduct.SILK: SILK,
    YieldProduct.WOOL: WOOL,
    YieldProduct.MILK: MILK,
    YieldProduct.FEATHERS: FEATHERS,
    YieldProduct.MAGIC_REAGENTS: REAGENTS,
    YieldProduct.DRAGONBONE: DRAGONBONE,
    YieldProduct.EGGS: EGGS,
}
PLANT_PLANS = {SpeciesClass.PLANT: P.ARBOREAL, SpeciesClass.FUNGUS: P.AMORPHOUS}
PLANT_DIETS = {SpeciesClass.PLANT: Diet.PHOTOSYNTHETIC, SpeciesClass.FUNGUS: Diet.SCAVENGER}
PEST_HUNTERS = frozenset({Diet.CARNIVORE, Diet.OMNIVORE})
LAYERS = frozenset({P.AVIAN, P.SERPENTINE, P.AQUATIC, P.INSECTOID})


COLD_PLANS = frozenset({BodyPlan.SERPENTINE, BodyPlan.INSECTOID, BodyPlan.AQUATIC})
SLEEPERS = frozenset({SizeClass.TINY, SizeClass.SMALL, SizeClass.MEDIUM})


@dataclass(frozen=True)
class SpeciesSpec:
    body_plan: BodyPlan | None = None
    size_class: SizeClass | None = None
    diet: Diet | None = None
    sociality: Sociality | None = None
    nocturnal: bool | None = None
    migratory: bool | None = None
    products: tuple[YieldProduct, ...] = ()
    species_class: SpeciesClass | None = None
    biochemistry: Biochemistry | None = None
    growth_cycle: GrowthCycle | None = None
    plant_yields: tuple[PlantYield, ...] = ()
    dormancy: Dormancy | None = None
    thermoregulation: Thermoregulation | None = None
    plant_defence: PlantDefence | None = None
    defence_potency: int | None = None


@dataclass(frozen=True)
class Nature:
    plan: BodyPlan
    size: SizeClass
    diet: Diet
    sociality: Sociality
    nocturnal: bool
    migratory: bool
    species_class: SpeciesClass = SpeciesClass.ANIMAL
    biochemistry: Biochemistry = Biochemistry.CARBON_WATER


async def parent_profile(session: AsyncSession, species_id: int) -> SpeciesProfileRow | None:
    parents = await session.scalars(
        select(BondRow.target_node_id)
        .where(BondRow.source_node_id == species_id, BondRow.kind == BondKind.DESCENDS_FROM, BondRow.target_node_id != species_id)
        .order_by(BondRow.id)
    )
    for parent in list(parents):
        row = await session.get(SpeciesProfileRow, parent)
        if row is not None:
            return row
    return None


async def plan_of(session: AsyncSession, species_id: int, traits: set[CreatureTrait], megafauna: bool, parent: SpeciesProfileRow | None) -> BodyPlan:
    if parent is not None:
        return parent.body_plan
    body = await session.get(BodyRow, species_id)
    if body is not None:
        return body.plan
    by_trait = next((plan for trait, plan in TRAIT_PLANS if trait in traits), None)
    if by_trait is not None:
        return by_trait
    return P.COLOSSAL if megafauna else P.QUADRUPED


def size_of(species: EntityRow, plan: BodyPlan, megafauna: bool, parent: SpeciesProfileRow | None) -> SizeClass:
    if parent is not None:
        return parent.size_class
    if plan is P.COLOSSAL:
        return Z.COLOSSAL
    if megafauna:
        return Z.HUGE
    strength = stat_or(species, "strength", PERCENT // 2)
    return SIZE_ORDER[clamp_int(strength // SIZE_STEP + 1, 1, 4)]


def diet_of(species: EntityRow, traits: set[CreatureTrait], plan: BodyPlan, parent: SpeciesProfileRow | None) -> Diet:
    if T.SOUL_EATER in traits:
        return Diet.SOUL
    if T.IRON_EATING in traits:
        return Diet.MINERAL
    if parent is not None:
        return parent.diet
    if plan in PLAN_DIETS:
        return PLAN_DIETS[plan]
    return Diet.CARNIVORE if (stat(species, "danger") or 0) >= PERCENT // 2 else Diet.HERBIVORE


def sociality_of(diet: Diet, traits: set[CreatureTrait], parent: SpeciesProfileRow | None) -> Sociality:
    if T.HIVE_MIND in traits:
        return Sociality.HIVE
    if T.PACK_HUNTER in traits:
        return Sociality.PACK
    if parent is not None:
        return parent.sociality
    return Sociality.HERD if diet in GRAZERS else Sociality.SOLITARY


def class_of(spec: SpeciesSpec, traits: set[CreatureTrait], parent: SpeciesProfileRow | None) -> SpeciesClass:
    if spec.species_class is not None:
        return spec.species_class
    if parent is not None:
        return parent.species_class
    if spec.diet is Diet.PHOTOSYNTHETIC or spec.body_plan is P.ARBOREAL:
        return SpeciesClass.PLANT
    if T.CROP_PEST in traits and (spec.size_class is None or spec.size_class in SHELLED):
        return SpeciesClass.VERMIN
    return SpeciesClass.ANIMAL


def biochemistry_of(spec: SpeciesSpec, plan: BodyPlan, diet: Diet, parent: SpeciesProfileRow | None, native: tuple[Biochemistry, ...]) -> Biochemistry:
    if spec.biochemistry is not None:
        return spec.biochemistry
    if parent is not None:
        return parent.biochemistry
    if diet is Diet.VOID:
        return Biochemistry.VOID
    if diet is Diet.SOUL or plan is P.INCORPOREAL:
        return Biochemistry.SPIRIT
    if diet is Diet.MINERAL or plan is P.CONSTRUCT:
        return Biochemistry.SILICON
    return Biochemistry.CARBON_WATER if not native or Biochemistry.CARBON_WATER in native else native[0]


async def nature_of(
    session: AsyncSession, species: EntityRow, traits: set[CreatureTrait], megafauna: bool, spec: SpeciesSpec, *, native: tuple[Biochemistry, ...] = ()
) -> Nature:
    parent = await parent_profile(session, species.id)
    kind = class_of(spec, traits, parent)
    grown = kind in GROWN
    plan = spec.body_plan or (PLANT_PLANS[kind] if grown and parent is None else await plan_of(session, species.id, traits, megafauna, parent))
    size = spec.size_class or size_of(species, plan, megafauna, parent)
    diet = spec.diet or (PLANT_DIETS[kind] if grown and parent is None else diet_of(species, traits, plan, parent))
    sociality = spec.sociality or sociality_of(diet, traits, parent)
    nocturnal = spec.nocturnal if spec.nocturnal is not None else parent.nocturnal if parent is not None else T.ECHOLOCATION in traits
    migratory = spec.migratory if spec.migratory is not None else parent.migratory if parent is not None else False
    return Nature(plan, size, diet, sociality, nocturnal, migratory, kind, biochemistry_of(spec, plan, diet, parent, native))


def yields_of(nature: Nature, traits: set[CreatureTrait], might: int, mighty: int, extra: tuple[YieldProduct, ...]) -> list[Product]:
    size, diet, plan = nature.size, nature.diet, nature.plan
    found = [MEAT] if T.POISONOUS_FLESH not in traits and diet not in UNEATEN else []
    found.append(CHITIN if plan is P.INSECTOID or (T.ARMOURED in traits and size in SHELLED) else HIDE)
    found.append(BONE)
    if size in GREAT:
        found.append(DRAGONBONE if T.FIRE_BREATHING in traits or might >= mighty else IVORY)
    if T.VENOMOUS in traits:
        found.append(VENOM)
    if diet in GRAZERS and size in KEPT_SIZES:
        found.extend((WOOL, MILK))
    if T.FLYING in traits or plan in FLYERS:
        found.append(FEATHERS)
    if plan in LAYERS and size in KEPT_SIZES and diet not in UNEATEN:
        found.append(EGGS)
    if might >= mighty:
        found.append(REAGENTS)
    found.extend(PRODUCTS[item] for item in extra)
    return list({item.product: item for item in found}.values())


def uses_of(nature: Nature, tameability: int, traits: set[CreatureTrait], might: int, mighty: int) -> set[SpeciesUse]:
    size, diet = nature.size, nature.diet
    found: set[SpeciesUse] = set()
    if T.POISONOUS_FLESH not in traits and diet in GRAZERS:
        found |= {SpeciesUse.FOOD, SpeciesUse.SACRIFICE}
    if size in DRAUGHT and diet in GRAZERS:
        found |= {SpeciesUse.MOUNT, SpeciesUse.LABOUR}
    if size in {Z.LARGE, Z.HUGE, Z.COLOSSAL} and diet not in GRAZERS:
        found.add(SpeciesUse.WAR)
    if (T.FLYING in traits or nature.plan in FLYERS) and size in DRAUGHT:
        found.add(SpeciesUse.MOUNT)
    if T.PACK_HUNTER in traits or nature.sociality is Sociality.PACK or (diet is Diet.CARNIVORE and size is Z.MEDIUM):
        found.add(SpeciesUse.GUARD)
    if size in SHELLED and tameability >= PERCENT // 2:
        found.add(SpeciesUse.COMPANION)
    if might >= mighty:
        found.add(SpeciesUse.MAGIC)
    if diet in PEST_HUNTERS and size in SHELLED:
        found.add(SpeciesUse.PEST_CONTROL)
    return found


def plant_uses(might: int, mighty: int) -> set[SpeciesUse]:
    return {SpeciesUse.MAGIC} if might >= mighty else set()


def plant_products(nature: Nature, cycle: GrowthCycle, chosen: tuple[PlantYield, ...]) -> list[Product]:
    wanted = chosen or DEFAULT_YIELDS[(nature.species_class, cycle)]
    return [Product(item.value, PLANT_PRODUCTS[item].commodity, PLANT_PRODUCTS[item].material, PLANT_PRODUCTS[item].rate) for item in dict.fromkeys(wanted)]


def cycle_of(spec: SpeciesSpec, nature: Nature, lifespan: int) -> GrowthCycle:
    if spec.growth_cycle is not None:
        return spec.growth_cycle
    if nature.plan is P.ARBOREAL and nature.size in GREAT | {Z.LARGE}:
        return GrowthCycle.TREE
    return GrowthCycle.PERENNIAL if lifespan > 1 else GrowthCycle.ANNUAL


async def home_land(session: AsyncSession, species: EntityRow) -> RegionEnvironmentRow | None:
    region = (await RegionAtlas.load(session)).top_region(species.id)
    return await session.get(RegionEnvironmentRow, region) if region is not None else None


async def inherited_products(session: AsyncSession, species_id: int) -> tuple[YieldProduct, ...]:
    parent = await parent_profile(session, species_id)
    if parent is None:
        return ()
    names = set(await session.scalars(select(SpeciesYieldRow.product).where(SpeciesYieldRow.species_entity_id == parent.species_entity_id)))
    return tuple(item for item, product in PRODUCTS.items() if product.product in names)


async def profile_of(ctx: TickContext, species: EntityRow, spec: SpeciesSpec | None = None) -> SpeciesProfileRow:
    row = await ctx.session.get(SpeciesProfileRow, species.id)
    if row is not None:
        return row
    table = ctx.rules.species_nature
    chosen = spec or SpeciesSpec()
    traits = await traits_of(ctx.session, species.id)
    megafauna = await has_flag(ctx.session, species.id, EntityFlag.MEGAFAUNA)
    nature = await nature_of(ctx.session, species, traits, megafauna, chosen, native=await tolerated(ctx.session, species.world_id))
    size, diet = nature.size, nature.diet
    land = await home_land(ctx.session, species)
    danger = stat(species, "danger") or 0
    intelligence = stat(species, "intelligence") or 0
    might = stat(species, "might") or 0
    tameability = clamp_int(
        table.tame_base
        - danger * table.tame_danger_pct // PERCENT
        + (intelligence - table.tame_wit_pivot) * table.tame_wit_pct // PERCENT
        + (table.tame_grazer if diet in GRAZERS else 0)
        - (table.tame_megafauna if megafauna else 0),
        0,
        PERCENT,
    )
    lifespan = LIFESPAN[size] * (table.long_lived_factor if T.LONG_LIVED in traits else 1)
    terrain = land.dominant_terrain if land is not None else TerrainKind.PLAIN
    habitat = {terrain.value: PERCENT}
    if traits & {T.AQUATIC, T.AMPHIBIOUS} or nature.plan is P.AQUATIC:
        habitat |= {kind.value: ctx.rules.habitat.water_fit for kind in WATER}
    temperature = land.temperature if land is not None else table.default_temperature
    elevation = land.elevation_mean if land is not None else 0
    seasonal = land is not None and land.seasonality >= ctx.rules.dormancy.seasonal_at and size in SLEEPERS and not nature.migratory
    sleep = Dormancy.NONE
    if seasonal and nature.species_class not in GROWN:
        sleep = Dormancy.HIBERNATION if temperature < ctx.rules.environment.temperate_below else Dormancy.AESTIVATION
    row = SpeciesProfileRow(
        species_entity_id=species.id,
        species_class=nature.species_class,
        biochemistry=nature.biochemistry,
        body_plan=nature.plan,
        size_class=size,
        lifespan_years=max(1, lifespan),
        maturity_years=max(0, lifespan // table.maturity_divisor),
        litter_size=LITTER[size] * (table.swarm_litter_factor if T.SWARM_BREEDER in traits else 1),
        breeding_seasons=2 if size in SHELLED else 1,
        diet=diet,
        metabolism=METABOLISM[size],
        habitat=habitat,
        temperature_min=temperature - table.temperature_band,
        temperature_max=temperature + table.temperature_band,
        water_need=table.aquatic_water_need if T.AQUATIC in traits or nature.plan is P.AQUATIC else PERCENT // 2,
        altitude_min=max(0, elevation - table.altitude_band),
        altitude_max=elevation + table.altitude_band,
        nocturnal=nature.nocturnal,
        migratory=nature.migratory,
        dormancy=chosen.dormancy or sleep,
        thermoregulation=chosen.thermoregulation or (Thermoregulation.ECTOTHERM if nature.plan in COLD_PLANS else Thermoregulation.ENDOTHERM),
        migration_path=[],
        aggression=clamp_int(danger, 0, PERCENT),
        territoriality=clamp_int(danger // 2 + table.territory_base, 0, PERCENT),
        sociality=nature.sociality,
        cunning=clamp_int(intelligence, 0, PERCENT),
        fear_of_people=clamp_int(PERCENT - danger, 0, PERCENT),
        tameability=tameability,
        updated_epoch=ctx.epoch,
        stage_epoch=ctx.epoch,
        pinned_prey=[],
        barred_prey=[],
        locked=[],
    )
    ctx.session.add(row)
    if nature.species_class in GROWN:
        cycle = cycle_of(chosen, nature, row.lifespan_years)
        plant = add_plant_profile(ctx, species.id, cycle)
        if chosen.plant_defence is not None:
            plant.defence = chosen.plant_defence
            plant.defence_potency = chosen.defence_potency if chosen.defence_potency is not None else ctx.rules.plant_defences.default_potency
        products = plant_products(nature, cycle, chosen.plant_yields)
        kept = plant_uses(might, table.mighty)
    else:
        extra = tuple(dict.fromkeys((*chosen.products, *await inherited_products(ctx.session, species.id))))
        products = yields_of(nature, traits, might, table.mighty, extra)
        kept = uses_of(nature, tameability, traits, might, table.mighty)
    for item in products:
        ctx.session.add(SpeciesYieldRow(species_entity_id=species.id, product=item.product, commodity=item.commodity, material=item.material, rate=item.rate))
    for use in kept:
        ctx.session.add(SpeciesUseRow(species_entity_id=species.id, use=use))
    await ctx.session.flush()
    return row


CYCLE_SEASONS = {
    GrowthCycle.ANNUAL: lambda rules: rules.flora.annual_seasons,
    GrowthCycle.PERENNIAL: lambda rules: rules.flora.perennial_seasons,
    GrowthCycle.TREE: lambda rules: rules.flora.tree_seasons,
}


def add_plant_profile(ctx: TickContext, species_id: int, cycle: GrowthCycle) -> PlantProfileRow:
    plant = PlantProfileRow(
        species_entity_id=species_id,
        growth_cycle=cycle,
        growing_seasons=CYCLE_SEASONS[cycle](ctx.rules),
        soil_need=ctx.rules.flora.soil_need,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(plant)
    return plant


def traits_from_nature(profile: SpeciesProfileRow) -> list[CreatureTrait]:
    found = [PLAN_TRAITS[profile.body_plan]] if profile.body_plan in PLAN_TRAITS else []
    if profile.sociality in SOCIAL_TRAITS:
        found.append(SOCIAL_TRAITS[profile.sociality])
    if profile.nocturnal:
        found.append(T.ECHOLOCATION)
    return list(dict.fromkeys(found))


async def assign_traits(ctx: TickContext, species: EntityRow) -> list[CreatureTrait]:
    repository = EntityRepository(ctx.session)
    if await repository.traits(species.id):
        return []
    chosen = traits_from_nature(await profile_of(ctx, species))[: ctx.rules.creatures.traits_from_description_cap]
    for trait in chosen:
        await repository.add_trait(species.id, trait)
    if CreatureTrait.HIVE_MIND in chosen:
        shift_bounded(ctx.rules, species, "intelligence", ctx.rules.creatures.hive_mind_intelligence)
    return chosen


NATURE_FIXUP = "wilds.typed_nature"


async def typed_nature_backfill(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, NATURE_FIXUP) is not None:
        return 0
    changed = 0
    for row in list(await ctx.session.scalars(select(SpeciesProfileRow).order_by(SpeciesProfileRow.species_entity_id))):
        body = await ctx.session.get(BodyRow, row.species_entity_id)
        if body is None or "body_plan" in row.locked or body.plan is row.body_plan:
            continue
        row.body_plan = body.plan
        changed += 1
    ctx.session.add(AppliedFixupRow(key=NATURE_FIXUP, result={"species": changed}))
    await ctx.session.flush()
    return changed
