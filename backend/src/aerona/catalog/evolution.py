from collections.abc import Callable, Mapping

from aerona.catalog.diets import FLESH_SEEKERS, FORAGERS, PRODUCERS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import SIZE_ORDER, Diet, DomesticationStage, SizeClass
from aerona.domain.enums.evolution import EvolvedTrait, KeystoneRole, SuccessionStage, TrophicLevel
from aerona.domain.enums.society import CreatureTrait
from aerona.rules.registry import Rules

S = SuccessionStage
T = CreatureTrait

STAGE_COVER = total(
    SuccessionStage,
    {
        S.BARE: 5,
        S.PIONEER: 8,
        S.GRASSLAND: 15,
        S.HEATH: 20,
        S.COASTAL_DUNE: 10,
        S.SHRUBLAND: 35,
        S.YOUNG_FOREST: 60,
        S.OLD_FOREST: 100,
        S.OPEN_WATER: 0,
        S.MARSH: 40,
        S.BOG: 45,
        S.SWAMP_FOREST: 100,
    },
)
DRY_PATH = (S.BARE, S.PIONEER, S.GRASSLAND, S.SHRUBLAND, S.YOUNG_FOREST, S.OLD_FOREST)
WET_PATH = (S.OPEN_WATER, S.MARSH, S.BOG, S.SWAMP_FOREST)
ADVANCE: Mapping[SuccessionStage, Callable[[Rules], int]] = total(
    SuccessionStage,
    {
        S.BARE: lambda rules: rules.succession_stages.epochs(rules.succession_stages.bare_advance_years),
        S.PIONEER: lambda rules: rules.succession_stages.epochs(rules.succession_stages.pioneer_advance_years),
        S.GRASSLAND: lambda rules: rules.succession_stages.epochs(rules.succession_stages.grassland_advance_years),
        S.HEATH: lambda rules: rules.succession_stages.epochs(rules.succession_stages.heath_advance_years),
        S.COASTAL_DUNE: lambda rules: rules.succession_stages.epochs(rules.succession_stages.coastal_dune_advance_years),
        S.SHRUBLAND: lambda rules: rules.succession_stages.epochs(rules.succession_stages.shrubland_advance_years),
        S.YOUNG_FOREST: lambda rules: rules.succession_stages.epochs(rules.succession_stages.young_forest_advance_years),
        S.OLD_FOREST: lambda rules: rules.succession_stages.epochs(rules.succession_stages.old_forest_advance_years),
        S.OPEN_WATER: lambda rules: rules.succession_stages.epochs(rules.succession_stages.open_water_advance_years),
        S.MARSH: lambda rules: rules.succession_stages.epochs(rules.succession_stages.marsh_advance_years),
        S.BOG: lambda rules: rules.succession_stages.epochs(rules.succession_stages.bog_advance_years),
        S.SWAMP_FOREST: lambda rules: rules.succession_stages.epochs(rules.succession_stages.swamp_forest_advance_years),
    },
)
POOR_PATH = (S.BARE, S.PIONEER, S.HEATH, S.SHRUBLAND)
DUNE_PATH = (S.BARE, S.PIONEER, S.COASTAL_DUNE, S.GRASSLAND)
WET_LAND = 40
BARE_SOIL = 10
WOODED = frozenset({S.YOUNG_FOREST, S.OLD_FOREST, S.SWAMP_FOREST})
FIRE_STAGE: dict[SuccessionStage, SuccessionStage] = {
    S.YOUNG_FOREST: S.GRASSLAND,
    S.OLD_FOREST: S.SHRUBLAND,
    S.SWAMP_FOREST: S.MARSH,
}

PRODUCER_DIETS = PRODUCERS
PLANT_EATERS = FORAGERS
MEAT_EATERS = FLESH_SEEKERS
PREY_TRAITS = (EvolvedTrait.SPEED, EvolvedTrait.CAMOUFLAGE)
APEX_SIZES = frozenset({SizeClass.LARGE, SizeClass.HUGE, SizeClass.COLOSSAL})
LITTLE = frozenset({SizeClass.TINY, SizeClass.SMALL})
DAM_SIZES = frozenset({SizeClass.SMALL, SizeClass.MEDIUM})
DISPERSER_DIETS = frozenset({Diet.HERBIVORE, Diet.OMNIVORE})
TROPHIC_ORDER = tuple(level for level in TrophicLevel if level not in (TrophicLevel.DECOMPOSER, TrophicLevel.PARASITE))

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


def path_of(stage: SuccessionStage, *, wet: bool, poor: bool = False, dune: bool = False) -> tuple[SuccessionStage, ...]:
    if wet and stage in (*WET_PATH, S.BARE, S.PIONEER, S.GRASSLAND):
        return (S.BARE, S.PIONEER, S.GRASSLAND, *WET_PATH[1:]) if stage not in WET_PATH else WET_PATH
    if dune and stage in DUNE_PATH:
        return DUNE_PATH
    if poor and stage in POOR_PATH:
        return POOR_PATH
    return DRY_PATH


def next_stage(stage: SuccessionStage, wet: bool, *, poor: bool = False, dune: bool = False) -> SuccessionStage | None:
    path = path_of(stage, wet=wet, poor=poor, dune=dune)
    if stage not in path:
        return None
    index = path.index(stage)
    return path[index + 1] if index + 1 < len(path) else None


FIXED_LEVELS: Mapping[Diet, TrophicLevel] = {Diet.DECOMPOSER: TrophicLevel.DECOMPOSER, Diet.PARASITE: TrophicLevel.PARASITE}


def trophic_level(diet: Diet, size: SizeClass) -> TrophicLevel | None:
    if diet in FIXED_LEVELS:
        return FIXED_LEVELS[diet]
    if diet in PRODUCER_DIETS:
        return TrophicLevel.PRODUCER
    if diet in PLANT_EATERS:
        return TrophicLevel.HERBIVORE
    if diet is Diet.CARNIVORE and size in APEX_SIZES:
        return TrophicLevel.APEX
    if diet in MEAT_EATERS:
        return TrophicLevel.CARNIVORE
    return None


KeystoneTest = Callable[[BodyPlan, Diet, SizeClass, set[CreatureTrait]], bool]
KEYSTONE_TESTS: tuple[tuple[KeystoneTest, KeystoneRole], ...] = (
    (lambda _plan, diet, size, _traits: diet in PRODUCER_DIETS and size in LITTLE, KeystoneRole.NUTRIENT_FIXER),
    (lambda _plan, diet, size, traits: diet is Diet.HERBIVORE and size in APEX_SIZES and T.FLYING not in traits, KeystoneRole.GRAZER),
    (lambda _plan, diet, _size, _traits: diet is Diet.SCAVENGER, KeystoneRole.SCAVENGER),
    (
        lambda plan, diet, size, traits: size in LITTLE and diet in DISPERSER_DIETS and (T.FLYING in traits or plan in (BodyPlan.INSECTOID, BodyPlan.AVIAN)),
        KeystoneRole.POLLINATOR,
    ),
    (lambda _plan, _diet, size, traits: T.BURROWING in traits and size not in APEX_SIZES, KeystoneRole.SOIL_MAKER),
    (lambda _plan, diet, size, traits: diet is Diet.HERBIVORE and size in DAM_SIZES and bool(traits & {T.AMPHIBIOUS, T.AQUATIC}), KeystoneRole.DAM_BUILDER),
    (lambda _plan, diet, size, traits: diet is Diet.FILTER and T.AQUATIC in traits and size in LITTLE, KeystoneRole.REEF_BUILDER),
    (lambda _plan, diet, size, _traits: diet is Diet.CARNIVORE and size in APEX_SIZES, KeystoneRole.REGULATOR),
    (lambda plan, diet, _size, traits: diet in DISPERSER_DIETS and (T.FLYING in traits or plan is BodyPlan.AVIAN), KeystoneRole.SEED_DISPERSER),
)


def keystone_of(plan: BodyPlan, diet: Diet, size: SizeClass, traits: set[CreatureTrait]) -> KeystoneRole | None:
    return next((role for test, role in KEYSTONE_TESTS if test(plan, diet, size, traits)), None)


HOT = 30
LIFESPAN_NEUTRAL = 10
STAGE_DOCILITY: Mapping[DomesticationStage, int] = total(
    DomesticationStage,
    {
        DomesticationStage.WILD: 0,
        DomesticationStage.COMMENSAL: 35,
        DomesticationStage.TAMED: 50,
        DomesticationStage.HERDED: 60,
        DomesticationStage.DOMESTICATED: 75,
        DomesticationStage.BREED: 85,
        DomesticationStage.FERAL: 30,
        DomesticationStage.CAPTIVE: 40,
    },
)


def seeded_trait(
    trait: EvolvedTrait,
    *,
    size: SizeClass,
    traits: set[CreatureTrait],
    cold_floor: int,
    intelligence: int,
    litter: int,
    fear: int,
    heat_ceiling: int = HOT,
    water_need: int = NEUTRAL,
    tameability: int = NEUTRAL,
    stage: DomesticationStage = DomesticationStage.WILD,
    lifespan: int = LIFESPAN_NEUTRAL,
) -> int:
    def high(flag: bool) -> int:
        return SEEDED_HIGH if flag else SEEDED_LOW

    def bounded(value: float) -> int:
        return max(0, min(PERCENT, round(value)))

    seeds = total(
        EvolvedTrait,
        {
            EvolvedTrait.SIZE: round(SIZE_ORDER.index(size) * PERCENT / (len(SIZE_ORDER) - 1)),
            EvolvedTrait.SPEED: high(T.FLYING in traits),
            EvolvedTrait.ARMOUR: high(bool(traits & {T.ARMOURED, T.STONESKIN})),
            EvolvedTrait.VENOM: high(T.VENOMOUS in traits),
            EvolvedTrait.CAMOUFLAGE: high(bool(traits & {T.CAMOUFLAGE, T.MIMIC})),
            EvolvedTrait.COLD_TOLERANCE: bounded(NEUTRAL - cold_floor * 2),
            EvolvedTrait.INTELLIGENCE: bounded(intelligence),
            EvolvedTrait.FECUNDITY: bounded(litter * 10),
            EvolvedTrait.WARINESS: bounded(fear),
            EvolvedTrait.HEAT_TOLERANCE: bounded(NEUTRAL + (heat_ceiling - HOT) * 2),
            EvolvedTrait.DROUGHT_TOLERANCE: bounded(PERCENT - water_need),
            EvolvedTrait.KEEN_SENSES: SEEDED_HIGH if traits & {T.ECHOLOCATION, T.SPIRIT_SIGHT, T.MIND_READER} else NEUTRAL,
            EvolvedTrait.DISEASE_RESISTANCE: NEUTRAL,
            EvolvedTrait.DOCILITY: bounded(max(tameability, STAGE_DOCILITY[stage])),
            EvolvedTrait.LONGEVITY: bounded(NEUTRAL * lifespan / LIFESPAN_NEUTRAL),
            EvolvedTrait.STRENGTH: round(SIZE_ORDER.index(size) * PERCENT / (len(SIZE_ORDER) - 1)),
            EvolvedTrait.PARENTAL_CARE: bounded(PERCENT - litter * 10),
            EvolvedTrait.SOCIAL_LEARNING: bounded(intelligence),
        },
    )
    return seeds[trait]


def lean(value: int | None) -> float:
    return 0.0 if value is None else max(-1.0, min(1.0, (value - NEUTRAL) / NEUTRAL))


def size_band(value: int) -> int:
    return min(PERCENT // NICHE_BAND - 1, value // NICHE_BAND)


def size_from(value: int) -> SizeClass:
    return SIZE_ORDER[max(0, min(len(SIZE_ORDER) - 1, round(value * (len(SIZE_ORDER) - 1) / PERCENT)))]
