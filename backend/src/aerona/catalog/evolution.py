from aerona.constants.units import PERCENT
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import SIZE_ORDER, Diet, SizeClass
from aerona.domain.enums.evolution import EvolvedTrait, KeystoneRole, SuccessionStage, TrophicLevel
from aerona.domain.enums.society import CreatureTrait

S = SuccessionStage
T = CreatureTrait

STAGE_COVER: dict[SuccessionStage, int] = {
    S.BARE: 5,
    S.GRASSLAND: 15,
    S.SHRUBLAND: 35,
    S.YOUNG_FOREST: 60,
    S.OLD_FOREST: 100,
    S.MARSH: 40,
    S.SWAMP_FOREST: 100,
}
DRY_PATH = (S.BARE, S.GRASSLAND, S.SHRUBLAND, S.YOUNG_FOREST, S.OLD_FOREST)
WET_PATH = (S.BARE, S.GRASSLAND, S.MARSH, S.SWAMP_FOREST)
WET_LAND = 40
BARE_SOIL = 10
WOODED = frozenset({S.YOUNG_FOREST, S.OLD_FOREST, S.SWAMP_FOREST})
FIRE_STAGE: dict[SuccessionStage, SuccessionStage] = {
    S.YOUNG_FOREST: S.GRASSLAND,
    S.OLD_FOREST: S.SHRUBLAND,
    S.SWAMP_FOREST: S.MARSH,
}

PRODUCER_DIETS = frozenset({Diet.PHOTOSYNTHETIC, Diet.MINERAL})
PLANT_EATERS = frozenset({Diet.HERBIVORE, Diet.FILTER})
MEAT_EATERS = frozenset({Diet.CARNIVORE, Diet.OMNIVORE, Diet.SCAVENGER})
APEX_SIZES = frozenset({SizeClass.LARGE, SizeClass.HUGE, SizeClass.COLOSSAL})
LITTLE = frozenset({SizeClass.TINY, SizeClass.SMALL})
DAM_SIZES = frozenset({SizeClass.SMALL, SizeClass.MEDIUM})
TROPHIC_ORDER = tuple(TrophicLevel)

NEUTRAL = PERCENT // 2
SEEDED_HIGH = 70
SEEDED_LOW = 30
NICHE_BAND = 20


def climax_stage(forest: int, wetland: int, fertility: int) -> SuccessionStage:
    if wetland >= WET_LAND:
        return S.SWAMP_FOREST if forest >= WET_LAND else S.MARSH
    if forest >= STAGE_COVER[S.YOUNG_FOREST]:
        return S.OLD_FOREST
    if forest >= STAGE_COVER[S.SHRUBLAND]:
        return S.YOUNG_FOREST
    if forest >= STAGE_COVER[S.GRASSLAND]:
        return S.SHRUBLAND
    if forest < STAGE_COVER[S.BARE] and fertility < BARE_SOIL:
        return S.BARE
    return S.GRASSLAND


def next_stage(stage: SuccessionStage, wet: bool) -> SuccessionStage | None:
    path = WET_PATH if wet and stage not in (S.SHRUBLAND, S.YOUNG_FOREST, S.OLD_FOREST) else DRY_PATH
    if stage not in path:
        return None
    index = path.index(stage)
    return path[index + 1] if index + 1 < len(path) else None


def trophic_level(diet: Diet, size: SizeClass) -> TrophicLevel | None:
    if diet in PRODUCER_DIETS:
        return TrophicLevel.PRODUCER
    if diet in PLANT_EATERS:
        return TrophicLevel.HERBIVORE
    if diet is Diet.CARNIVORE and size in APEX_SIZES:
        return TrophicLevel.APEX
    if diet in MEAT_EATERS:
        return TrophicLevel.CARNIVORE
    return None


def keystone_of(plan: BodyPlan, diet: Diet, size: SizeClass, traits: set[CreatureTrait]) -> KeystoneRole | None:
    if diet is Diet.SCAVENGER:
        return KeystoneRole.SCAVENGER
    if size in LITTLE and diet in (Diet.HERBIVORE, Diet.OMNIVORE) and (T.FLYING in traits or plan in (BodyPlan.INSECTOID, BodyPlan.AVIAN)):
        return KeystoneRole.POLLINATOR
    if T.BURROWING in traits and size not in APEX_SIZES:
        return KeystoneRole.SOIL_MAKER
    if diet is Diet.HERBIVORE and size in DAM_SIZES and traits & {T.AMPHIBIOUS, T.AQUATIC}:
        return KeystoneRole.DAM_BUILDER
    return None


def seeded_trait(trait: EvolvedTrait, *, size: SizeClass, traits: set[CreatureTrait], cold_floor: int, intelligence: int, litter: int, fear: int) -> int:
    high = {
        EvolvedTrait.ARMOUR: bool(traits & {T.ARMOURED, T.STONESKIN}),
        EvolvedTrait.VENOM: T.VENOMOUS in traits,
        EvolvedTrait.CAMOUFLAGE: bool(traits & {T.CAMOUFLAGE, T.MIMIC}),
        EvolvedTrait.SPEED: T.FLYING in traits,
    }
    if trait in high:
        return SEEDED_HIGH if high[trait] else SEEDED_LOW
    if trait is EvolvedTrait.SIZE:
        return round(SIZE_ORDER.index(size) * PERCENT / (len(SIZE_ORDER) - 1))
    if trait is EvolvedTrait.COLD_TOLERANCE:
        return max(0, min(PERCENT, NEUTRAL - cold_floor * 2))
    if trait is EvolvedTrait.INTELLIGENCE:
        return max(0, min(PERCENT, intelligence))
    if trait is EvolvedTrait.FECUNDITY:
        return max(0, min(PERCENT, litter * 10))
    return max(0, min(PERCENT, fear))


def lean(value: int | None) -> float:
    return 0.0 if value is None else max(-1.0, min(1.0, (value - NEUTRAL) / NEUTRAL))


def size_band(value: int) -> int:
    return min(PERCENT // NICHE_BAND - 1, value // NICHE_BAND)


def size_from(value: int) -> SizeClass:
    return SIZE_ORDER[max(0, min(len(SIZE_ORDER) - 1, round(value * (len(SIZE_ORDER) - 1) / PERCENT)))]
