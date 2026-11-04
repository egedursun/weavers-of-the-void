from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesUseRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.ecology import GRAZERS, SIZE_ORDER, Diet, SizeClass, Sociality, SpeciesUse
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import stat

T = CreatureTrait
Z = SizeClass
SIZE_WORDS = (
    (("titan", "leviathan", "kraken", "world-serpent", "colossal"), Z.COLOSSAL),
    (("elephant", "mammoth", "dragon", "whale", "giant", "troll", "behemoth", "wyrm"), Z.HUGE),
    (("bear", "horse", "elk", "bison", "cattle", "ox", "lion", "tiger", "camel", "moose", "aurochs", "boar"), Z.LARGE),
    (("rat", "fox", "cat", "bird", "rabbit", "hare", "owl", "hawk", "bat", "lizard", "goat", "sheep"), Z.SMALL),
    (("insect", "ant", "mouse", "bee", "beetle", "locust", "flea", "spider", "moth", "worm"), Z.TINY),
)
DIET_WORDS = (
    (("void", "starless", "between worlds"), Diet.VOID),
    (("stone-eat", "crystal", "ore-eat", "rock-eat", "iron-eat"), Diet.MINERAL),
    (("plant", "tree", "fungus", "moss", "flower", "vine"), Diet.PHOTOSYNTHETIC),
    (("plankton", "filter", "jelly", "sponge"), Diet.FILTER),
    (("carrion", "vulture", "scaveng", "bone-pick"), Diet.SCAVENGER),
    (("wolf", "lion", "tiger", "hunt", "predator", "fang", "claw", "shark", "hawk", "dragon"), Diet.CARNIVORE),
    (("bear", "boar", "rat", "crow", "pig"), Diet.OMNIVORE),
    (("graze", "grass", "herd", "deer", "horse", "cattle", "sheep", "goat", "bison"), Diet.HERBIVORE),
)
PLAN_WORDS = (
    (("serpent", "snake", "wyrm", "eel"), "serpentine"),
    (("bird", "wing", "hawk", "owl", "eagle", "crow"), "avian"),
    (("fish", "shark", "whale", "eel"), "piscine"),
    (("insect", "spider", "beetle", "ant", "locust", "crab"), "arthropod"),
    (("tree", "plant", "fungus", "vine", "moss"), "plant"),
    (("jelly", "slime", "ooze"), "amorphous"),
)
WATER = frozenset({TerrainKind.COAST, TerrainKind.MARSH, TerrainKind.ISLAND, TerrainKind.RIVER_VALLEY})
LIFESPAN = {Z.TINY: 2, Z.SMALL: 6, Z.MEDIUM: 15, Z.LARGE: 25, Z.HUGE: 60, Z.COLOSSAL: 200}
LITTER = {Z.TINY: 8, Z.SMALL: 5, Z.MEDIUM: 3, Z.LARGE: 1, Z.HUGE: 1, Z.COLOSSAL: 1}
METABOLISM = {Z.TINY: 80, Z.SMALL: 65, Z.MEDIUM: 50, Z.LARGE: 40, Z.HUGE: 30, Z.COLOSSAL: 20}
BAND = 15
ALTITUDE = 1500


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
WOOL = Product("wool", CommodityKind.CLOTH, MaterialKind.CLOTH, 1)
MILK = Product("milk", CommodityKind.LIVESTOCK, None, 1)
FEATHERS = Product("feathers", CommodityKind.LUXURIES, None, 1)
REAGENTS = Product("magic reagents", CommodityKind.MAGICAL_REAGENTS, None, 1)
DRAGONBONE = Product("dragonbone", CommodityKind.WEAPONS, MaterialKind.DRAGONBONE, 1)
MIGHTY = 60


def first_match[V](text: str, table: tuple[tuple[tuple[str, ...], V], ...]) -> V | None:
    return next((value for words, value in table if any(word in text for word in words)), None)


def size_of(text: str, species: EntityRow, megafauna: bool) -> SizeClass:
    found = first_match(text, SIZE_WORDS)
    if found is not None:
        return found
    if megafauna:
        return Z.HUGE
    strength = stat(species, "strength") or PERCENT // 2
    return SIZE_ORDER[clamp_int(strength // 25 + 1, 1, 4)]


def diet_of(text: str, species: EntityRow, traits: set[CreatureTrait]) -> Diet:
    if T.SOUL_EATER in traits:
        return Diet.SOUL
    if T.IRON_EATING in traits:
        return Diet.MINERAL
    found = first_match(text, DIET_WORDS)
    if found is not None:
        return found
    return Diet.CARNIVORE if (stat(species, "danger") or 0) >= PERCENT // 2 else Diet.HERBIVORE


def sociality_of(text: str, diet: Diet, traits: set[CreatureTrait]) -> Sociality:
    if T.HIVE_MIND in traits:
        return Sociality.HIVE
    if T.PACK_HUNTER in traits or "pack" in text or "wolf" in text:
        return Sociality.PACK
    return Sociality.HERD if diet in GRAZERS else Sociality.SOLITARY


def yields_of(size: SizeClass, diet: Diet, traits: set[CreatureTrait], text: str, might: int) -> list[Product]:
    found = [MEAT] if T.POISONOUS_FLESH not in traits and diet not in {Diet.MINERAL, Diet.VOID, Diet.PHOTOSYNTHETIC} else []
    found.append(CHITIN if "arthropod" in text or (T.ARMOURED in traits and size in {Z.TINY, Z.SMALL}) else HIDE)
    found.append(BONE)
    if size in {Z.HUGE, Z.COLOSSAL}:
        found.append(DRAGONBONE if T.FIRE_BREATHING in traits or "dragon" in text else IVORY)
    if T.VENOMOUS in traits:
        found.append(VENOM)
    if "silk" in text or "spider" in text or "moth" in text:
        found.append(SILK)
    if diet in GRAZERS and size in {Z.SMALL, Z.MEDIUM, Z.LARGE}:
        found.extend((WOOL, MILK))
    if T.FLYING in traits:
        found.append(FEATHERS)
    if might >= MIGHTY:
        found.append(REAGENTS)
    return list({item.product: item for item in found}.values())


def uses_of(size: SizeClass, diet: Diet, tameability: int, traits: set[CreatureTrait], might: int) -> set[SpeciesUse]:
    found: set[SpeciesUse] = set()
    if T.POISONOUS_FLESH not in traits and diet in GRAZERS:
        found |= {SpeciesUse.FOOD, SpeciesUse.SACRIFICE}
    if size in {Z.LARGE, Z.HUGE} and diet in GRAZERS:
        found |= {SpeciesUse.MOUNT, SpeciesUse.LABOUR}
    if size in {Z.LARGE, Z.HUGE, Z.COLOSSAL} and diet not in GRAZERS:
        found.add(SpeciesUse.WAR)
    if T.FLYING in traits and size in {Z.LARGE, Z.HUGE}:
        found.add(SpeciesUse.MOUNT)
    if T.PACK_HUNTER in traits or (diet is Diet.CARNIVORE and size is Z.MEDIUM):
        found.add(SpeciesUse.GUARD)
    if size in {Z.TINY, Z.SMALL} and tameability >= PERCENT // 2:
        found.add(SpeciesUse.COMPANION)
    if might >= MIGHTY:
        found.add(SpeciesUse.MAGIC)
    return found


async def home_land(session: AsyncSession, species: EntityRow) -> RegionEnvironmentRow | None:
    region = (await RegionAtlas.load(session)).top_region(species.id)
    return await session.get(RegionEnvironmentRow, region) if region is not None else None


async def profile_of(ctx: TickContext, species: EntityRow) -> SpeciesProfileRow:
    row = await ctx.session.get(SpeciesProfileRow, species.id)
    if row is not None:
        return row
    text = f"{species.name} {species.subtype or ''} {species.description or ''}".lower()
    traits = await traits_of(ctx.session, species.id)
    megafauna = await has_flag(ctx.session, species.id, EntityFlag.MEGAFAUNA)
    size = size_of(text, species, megafauna)
    diet = diet_of(text, species, traits)
    land = await home_land(ctx.session, species)
    danger = stat(species, "danger") or 0
    intelligence = stat(species, "intelligence") or 0
    might = stat(species, "might") or 0
    tameability = clamp_int(60 - danger // 2 + (intelligence - 30) // 3 + (15 if diet in GRAZERS else 0) - (20 if megafauna else 0), 0, PERCENT)
    lifespan = LIFESPAN[size] * (3 if T.LONG_LIVED in traits else 1)
    terrain = land.dominant_terrain if land is not None else TerrainKind.PLAIN
    habitat = {terrain.value: PERCENT}
    if traits & {T.AQUATIC, T.AMPHIBIOUS}:
        habitat |= {kind.value: ctx.rules.habitat.water_fit for kind in WATER}
    temperature = land.temperature if land is not None else 15
    elevation = land.elevation_mean if land is not None else 0
    row = SpeciesProfileRow(
        species_entity_id=species.id,
        body_plan=first_match(text, PLAN_WORDS) or "quadruped",
        size_class=size,
        lifespan_years=max(1, lifespan),
        maturity_years=max(0, lifespan // 6),
        litter_size=LITTER[size] * (3 if T.SWARM_BREEDER in traits else 1),
        breeding_seasons=2 if size in {Z.TINY, Z.SMALL} else 1,
        diet=diet,
        metabolism=METABOLISM[size],
        habitat=habitat,
        temperature_min=temperature - BAND,
        temperature_max=temperature + BAND,
        water_need=90 if T.AQUATIC in traits else PERCENT // 2,
        altitude_min=max(0, elevation - ALTITUDE),
        altitude_max=elevation + ALTITUDE,
        nocturnal=T.ECHOLOCATION in traits or any(word in text for word in ("night", "nocturnal", "owl", "bat", "moon")),
        migratory=any(word in text for word in ("migrat", "flock", "wander", "seasonal")),
        migration_path=[],
        aggression=clamp_int(danger, 0, PERCENT),
        territoriality=clamp_int(danger // 2 + 20, 0, PERCENT),
        sociality=sociality_of(text, diet, traits),
        cunning=clamp_int(intelligence, 0, PERCENT),
        fear_of_people=clamp_int(PERCENT - danger, 0, PERCENT),
        tameability=tameability,
        updated_epoch=ctx.epoch,
        stage_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    for item in yields_of(size, diet, traits, f"{text} {row.body_plan}", might):
        ctx.session.add(SpeciesYieldRow(species_entity_id=species.id, product=item.product, commodity=item.commodity, material=item.material, rate=item.rate))
    for use in uses_of(size, diet, tameability, traits, might):
        ctx.session.add(SpeciesUseRow(species_entity_id=species.id, use=use))
    await ctx.session.flush()
    return row


async def uses(session: AsyncSession, species_id: int) -> set[SpeciesUse]:
    return set(await session.scalars(select(SpeciesUseRow.use).where(SpeciesUseRow.species_entity_id == species_id)))


async def yields(session: AsyncSession, species_id: int) -> list[SpeciesYieldRow]:
    return list(await session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.species_entity_id == species_id).order_by(SpeciesYieldRow.product)))
