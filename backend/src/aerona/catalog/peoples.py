from dataclasses import dataclass, field
from enum import StrEnum

from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.culture import ArtMedium
from aerona.domain.enums.demography import Aesthetic, FolkDiet, FuneralCustom, Job, NaturalTrait
from aerona.domain.enums.ecology import Diet, SizeClass
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import TemperatureBand, TerrainKind
from aerona.domain.enums.faith import FuneralRite
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import CreatureTrait

T = TerrainKind
J = Job


class MountFit(StrEnum):
    RIDES = "rides"
    IS_MOUNT = "is_mount"
    FLIES = "flies"
    CANNOT = "cannot"


class FoodSource(StrEnum):
    FIELDS = "fields"
    PASTURE = "pasture"
    SEA = "sea"
    STONE = "stone"
    ESSENCE = "essence"
    SUN = "sun"


@dataclass(frozen=True)
class KinSpec:
    food_pct: int
    space_pct: int
    disease_pct: int
    naval_pct: int
    mount: MountFit
    labour: dict[Job, int] = field(default_factory=dict)
    terrain: dict[TerrainKind, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SizeSpec:
    food_pct: int
    space_pct: int
    strength_pct: int
    heavy_labour_pct: int
    fine_labour_pct: int
    rides: bool


@dataclass(frozen=True)
class DietSpec:
    sources: dict[FoodSource, int]
    edible: frozenset[CommodityKind]


@dataclass(frozen=True)
class FuneralSpec:
    contagion_pct: int
    spirit_pct: int
    restless_shift: int
    mourning_pct: int
    binds_spirits: bool = False
    raises_dead: bool = False


KIN: dict[BodyPlan, KinSpec] = {
    BodyPlan.HUMANOID: KinSpec(100, 100, 100, 100, MountFit.RIDES),
    BodyPlan.QUADRUPED: KinSpec(
        130, 140, 100, 70, MountFit.IS_MOUNT, {J.HERDING: 125, J.FARMING: 110, J.CRAFTING: 75}, {T.PLAIN: 115, T.STEPPE: 120, T.FOREST: 90, T.MOUNTAINS: 80}
    ),
    BodyPlan.AVIAN: KinSpec(
        90, 80, 100, 50, MountFit.FLIES, {J.TRADE: 120, J.BUILDING: 80, J.MINING: 65}, {T.MOUNTAINS: 125, T.HILLS: 115, T.HIGH_PASS: 125, T.CANYON: 120}
    ),
    BodyPlan.SERPENTINE: KinSpec(
        80, 90, 95, 90, MountFit.CANNOT, {J.FISHING: 110, J.CRAFTING: 85}, {T.MARSH: 125, T.JUNGLE: 120, T.DESERT: 110, T.MOUNTAINS: 80}
    ),
    BodyPlan.INSECTOID: KinSpec(
        70, 60, 90, 50, MountFit.CANNOT, {J.BUILDING: 130, J.MINING: 120, J.SCHOLARSHIP: 80}, {T.FOREST: 110, T.DESERT: 115, T.UNDERGROUND: 120}
    ),
    BodyPlan.AQUATIC: KinSpec(
        100,
        100,
        100,
        170,
        MountFit.CANNOT,
        {J.FISHING: 170, J.FARMING: 55, J.MINING: 60},
        {T.MARSH: 130, T.COAST: 130, T.SEA: 150, T.DESERT: 55, T.MOUNTAINS: 70},
    ),
    BodyPlan.AMORPHOUS: KinSpec(60, 70, 70, 80, MountFit.CANNOT, {J.CRAFTING: 115, J.FARMING: 80}, {T.UNDERGROUND: 125, T.MARSH: 115, T.PLAIN: 90}),
    BodyPlan.ARBOREAL: KinSpec(
        90, 90, 100, 80, MountFit.RIDES, {J.CRAFTING: 115, J.BUILDING: 110, J.FARMING: 90}, {T.FOREST: 130, T.JUNGLE: 130, T.PLAIN: 85, T.DESERT: 70}
    ),
    BodyPlan.INCORPOREAL: KinSpec(
        20, 30, 10, 30, MountFit.FLIES, {J.CLERGY: 150, J.SCHOLARSHIP: 130, J.MINING: 40, J.FARMING: 40, J.BUILDING: 40}, {T.RUIN_FIELD: 130, T.VOID_SHORE: 120}
    ),
    BodyPlan.COLOSSAL: KinSpec(120, 130, 110, 40, MountFit.CANNOT, {J.BUILDING: 180, J.MINING: 150, J.CRAFTING: 55}, {T.FOREST: 80, T.MARSH: 70, T.PLAIN: 115}),
    BodyPlan.CONSTRUCT: KinSpec(
        30, 80, 15, 50, MountFit.CANNOT, {J.MINING: 140, J.BUILDING: 130, J.CRAFTING: 120, J.CLERGY: 50, J.SCHOLARSHIP: 70}, {T.UNDERGROUND: 110, T.MARSH: 80}
    ),
    BodyPlan.DIVINE_MANIFEST: KinSpec(
        50, 120, 30, 60, MountFit.FLIES, {J.CLERGY: 200, J.SCHOLARSHIP: 120, J.FARMING: 70}, {T.CRYSTAL_FIELD: 125, T.MOUNTAINS: 110}
    ),
}

SIZES: dict[SizeClass, SizeSpec] = {
    SizeClass.TINY: SizeSpec(40, 40, 45, 60, 130, True),
    SizeClass.SMALL: SizeSpec(70, 70, 75, 85, 115, True),
    SizeClass.MEDIUM: SizeSpec(100, 100, 100, 100, 100, True),
    SizeClass.LARGE: SizeSpec(160, 160, 140, 120, 90, True),
    SizeClass.HUGE: SizeSpec(250, 250, 190, 145, 70, False),
    SizeClass.COLOSSAL: SizeSpec(400, 400, 260, 170, 50, False),
}

HEAVY_JOBS = frozenset({J.FARMING, J.MINING, J.BUILDING, J.SOLDIERING})
FINE_JOBS = frozenset({J.CRAFTING, J.SCHOLARSHIP, J.TRADE})

FOOD_SOURCES = frozenset({FoodSource.FIELDS, FoodSource.PASTURE, FoodSource.SEA})

DIETS: dict[FolkDiet, DietSpec] = {
    FolkDiet.OMNIVORE: DietSpec(
        {FoodSource.FIELDS: 100, FoodSource.PASTURE: 100, FoodSource.SEA: 100},
        frozenset({CommodityKind.GRAIN, CommodityKind.BREAD, CommodityKind.LIVESTOCK, CommodityKind.FISH}),
    ),
    FolkDiet.HERBIVORE: DietSpec({FoodSource.FIELDS: 110}, frozenset({CommodityKind.GRAIN, CommodityKind.BREAD, CommodityKind.FODDER})),
    FolkDiet.CARNIVORE: DietSpec({FoodSource.PASTURE: 110, FoodSource.SEA: 100}, frozenset({CommodityKind.LIVESTOCK, CommodityKind.FISH})),
    FolkDiet.PISCIVORE: DietSpec({FoodSource.SEA: 140}, frozenset({CommodityKind.FISH})),
    FolkDiet.SCAVENGER: DietSpec(
        {FoodSource.FIELDS: 70, FoodSource.PASTURE: 70, FoodSource.SEA: 70},
        frozenset({CommodityKind.GRAIN, CommodityKind.FODDER, CommodityKind.LIVESTOCK, CommodityKind.FISH}),
    ),
    FolkDiet.SANGUIVORE: DietSpec({FoodSource.PASTURE: 60}, frozenset({CommodityKind.LIVESTOCK})),
    FolkDiet.LITHOVORE: DietSpec({FoodSource.STONE: 100}, frozenset({CommodityKind.STONE, CommodityKind.ORE})),
    FolkDiet.ESSENCE_FEEDER: DietSpec({FoodSource.ESSENCE: 100}, frozenset({CommodityKind.MAGICAL_REAGENTS, CommodityKind.INCENSE})),
    FolkDiet.PHOTOTROPH: DietSpec({FoodSource.SUN: 100}, frozenset()),
}

SUN_BY_BAND: dict[TemperatureBand, int] = {
    TemperatureBand.FROZEN: 30,
    TemperatureBand.COLD: 60,
    TemperatureBand.TEMPERATE: 100,
    TemperatureBand.WARM: 120,
    TemperatureBand.HOT: 130,
    TemperatureBand.SEARING: 110,
}

STAPLE_BY_SOURCE: dict[FoodSource, CommodityKind] = {
    FoodSource.FIELDS: CommodityKind.GRAIN,
    FoodSource.PASTURE: CommodityKind.LIVESTOCK,
    FoodSource.SEA: CommodityKind.FISH,
    FoodSource.STONE: CommodityKind.STONE,
    FoodSource.ESSENCE: CommodityKind.MAGICAL_REAGENTS,
    FoodSource.SUN: CommodityKind.FODDER,
}

ECOLOGY_DIETS: dict[Diet, FolkDiet] = {
    Diet.HERBIVORE: FolkDiet.HERBIVORE,
    Diet.CARNIVORE: FolkDiet.CARNIVORE,
    Diet.OMNIVORE: FolkDiet.OMNIVORE,
    Diet.SCAVENGER: FolkDiet.SCAVENGER,
    Diet.FILTER: FolkDiet.PISCIVORE,
    Diet.PHOTOSYNTHETIC: FolkDiet.PHOTOTROPH,
    Diet.MINERAL: FolkDiet.LITHOVORE,
    Diet.SOUL: FolkDiet.ESSENCE_FEEDER,
    Diet.VOID: FolkDiet.ESSENCE_FEEDER,
}

CREATURE_DIETS: tuple[tuple[CreatureTrait, FolkDiet], ...] = (
    (CreatureTrait.IRON_EATING, FolkDiet.LITHOVORE),
    (CreatureTrait.STONESKIN, FolkDiet.LITHOVORE),
    (CreatureTrait.SOUL_EATER, FolkDiet.ESSENCE_FEEDER),
    (CreatureTrait.RADIANT, FolkDiet.PHOTOTROPH),
)

PLAN_DIETS: dict[BodyPlan, FolkDiet] = {
    BodyPlan.CONSTRUCT: FolkDiet.LITHOVORE,
    BodyPlan.INCORPOREAL: FolkDiet.ESSENCE_FEEDER,
    BodyPlan.DIVINE_MANIFEST: FolkDiet.ESSENCE_FEEDER,
    BodyPlan.AQUATIC: FolkDiet.PISCIVORE,
}

CREATURE_NATURES: dict[CreatureTrait, NaturalTrait] = {
    CreatureTrait.FLYING: NaturalTrait.WINGED,
    CreatureTrait.AMPHIBIOUS: NaturalTrait.AMPHIBIOUS,
    CreatureTrait.AQUATIC: NaturalTrait.AMPHIBIOUS,
    CreatureTrait.ARMOURED: NaturalTrait.THICK_HIDE,
    CreatureTrait.STONESKIN: NaturalTrait.THICK_HIDE,
    CreatureTrait.ECHOLOCATION: NaturalTrait.DARK_SIGHT,
    CreatureTrait.SPIRIT_SIGHT: NaturalTrait.DARK_SIGHT,
    CreatureTrait.AMBUSH_PREDATOR: NaturalTrait.KEEN_SENSES,
    CreatureTrait.PACK_HUNTER: NaturalTrait.KEEN_SENSES,
    CreatureTrait.CAMOUFLAGE: NaturalTrait.KEEN_SENSES,
    CreatureTrait.VENOMOUS: NaturalTrait.VENOMOUS,
    CreatureTrait.POISONOUS_FLESH: NaturalTrait.VENOMOUS,
    CreatureTrait.REGENERATING: NaturalTrait.REGENERATING,
    CreatureTrait.BURROWING: NaturalTrait.BURROWING,
    CreatureTrait.HIVE_MIND: NaturalTrait.HIVE_MINDED,
    CreatureTrait.SWARM_BREEDER: NaturalTrait.HIVE_MINDED,
}

PLAN_NATURES: dict[BodyPlan, tuple[NaturalTrait, ...]] = {
    BodyPlan.SERPENTINE: (NaturalTrait.COLD_BLOODED,),
    BodyPlan.INSECTOID: (NaturalTrait.COLD_BLOODED, NaturalTrait.HIVE_MINDED),
    BodyPlan.AVIAN: (NaturalTrait.WINGED,),
    BodyPlan.AQUATIC: (NaturalTrait.AMPHIBIOUS,),
    BodyPlan.CONSTRUCT: (NaturalTrait.THICK_HIDE,),
    BodyPlan.INCORPOREAL: (NaturalTrait.DARK_SIGHT,),
}

CREATURE_PLANS: tuple[tuple[CreatureTrait, BodyPlan], ...] = (
    (CreatureTrait.HIVE_MIND, BodyPlan.INSECTOID),
    (CreatureTrait.SHAPESHIFTER, BodyPlan.AMORPHOUS),
    (CreatureTrait.FLYING, BodyPlan.AVIAN),
    (CreatureTrait.AQUATIC, BodyPlan.AQUATIC),
)

FUNERALS: dict[FuneralCustom, FuneralSpec] = {
    FuneralCustom.BURIAL: FuneralSpec(100, 100, 0, 100),
    FuneralCustom.CREMATION: FuneralSpec(70, 70, -10, 90),
    FuneralCustom.SKY_BURIAL: FuneralSpec(115, 80, 5, 80),
    FuneralCustom.SEA_BURIAL: FuneralSpec(85, 90, 10, 85),
    FuneralCustom.ENTOMBMENT: FuneralSpec(95, 130, -5, 140),
    FuneralCustom.ANCESTOR_SHRINE: FuneralSpec(110, 150, -15, 130),
    FuneralCustom.ENDOCANNIBALISM: FuneralSpec(160, 60, 15, 110),
    FuneralCustom.REANIMATION: FuneralSpec(130, 160, 30, 60, raises_dead=True),
    FuneralCustom.SOUL_BINDING: FuneralSpec(90, 50, -100, 100, binds_spirits=True),
}

FUNERAL_NAMES: dict[FuneralCustom, str] = {
    FuneralCustom.BURIAL: "The Burial Rite of {people}",
    FuneralCustom.CREMATION: "The Pyres of {people}",
    FuneralCustom.SKY_BURIAL: "The Sky Burial of {people}",
    FuneralCustom.SEA_BURIAL: "The Sea Farewell of {people}",
    FuneralCustom.ENTOMBMENT: "The Tombs of {people}",
    FuneralCustom.ANCESTOR_SHRINE: "The Ancestor Shrines of {people}",
    FuneralCustom.ENDOCANNIBALISM: "The Last Feast of {people}",
    FuneralCustom.REANIMATION: "The Raising of the Dead of {people}",
    FuneralCustom.SOUL_BINDING: "The Soul Binding of {people}",
}

FUNERAL_DEEDS: dict[FuneralCustom, str] = {
    FuneralCustom.BURIAL: "lay their dead in the earth",
    FuneralCustom.CREMATION: "burn their dead on pyres",
    FuneralCustom.SKY_BURIAL: "lay their dead open to the sky",
    FuneralCustom.SEA_BURIAL: "give their dead to the waters",
    FuneralCustom.ENTOMBMENT: "seal their dead in tombs",
    FuneralCustom.ANCESTOR_SHRINE: "keep the bones of their dead at home shrines",
    FuneralCustom.ENDOCANNIBALISM: "eat of their dead to keep them close",
    FuneralCustom.REANIMATION: "raise their dead to serve again",
    FuneralCustom.SOUL_BINDING: "bind the souls of their dead into vessels",
}

AESTHETIC_MEDIA: dict[Aesthetic, frozenset[ArtMedium]] = {
    Aesthetic.AUSTERE: frozenset({ArtMedium.CARVING, ArtMedium.SONG, ArtMedium.EPIC_POEM}),
    Aesthetic.ORNATE: frozenset({ArtMedium.TAPESTRY, ArtMedium.MOSAIC, ArtMedium.ARCHITECTURE_ORNAMENT}),
    Aesthetic.GEOMETRIC: frozenset({ArtMedium.MOSAIC, ArtMedium.BOOK, ArtMedium.ARCHITECTURE_ORNAMENT}),
    Aesthetic.NATURAL: frozenset({ArtMedium.CARVING, ArtMedium.DANCE, ArtMedium.MUSIC}),
    Aesthetic.MACABRE: frozenset({ArtMedium.FRESCO, ArtMedium.STATUE, ArtMedium.PLAY}),
    Aesthetic.CELESTIAL: frozenset({ArtMedium.FRESCO, ArtMedium.MUSIC, ArtMedium.STATUE}),
}

AESTHETIC_SHUNS: dict[Aesthetic, frozenset[ArtMedium]] = {
    Aesthetic.AUSTERE: frozenset({ArtMedium.TAPESTRY, ArtMedium.ARCHITECTURE_ORNAMENT, ArtMedium.MOSAIC}),
    Aesthetic.ORNATE: frozenset({ArtMedium.CARVING}),
    Aesthetic.GEOMETRIC: frozenset({ArtMedium.DANCE, ArtMedium.STATUE}),
    Aesthetic.NATURAL: frozenset({ArtMedium.ARCHITECTURE_ORNAMENT, ArtMedium.MOSAIC}),
    Aesthetic.MACABRE: frozenset({ArtMedium.DANCE, ArtMedium.TAPESTRY}),
    Aesthetic.CELESTIAL: frozenset({ArtMedium.PLAY, ArtMedium.CARVING}),
}

AESTHETIC_AXES: dict[Aesthetic, ValueAxis] = {
    Aesthetic.AUSTERE: ValueAxis.TRADITION,
    Aesthetic.ORNATE: ValueAxis.WEALTH,
    Aesthetic.GEOMETRIC: ValueAxis.KNOWLEDGE,
    Aesthetic.NATURAL: ValueAxis.NATURE,
    Aesthetic.MACABRE: ValueAxis.DEATH,
    Aesthetic.CELESTIAL: ValueAxis.PIETY,
}

AESTHETIC_IMAGES: dict[Aesthetic, ArtMedium] = {
    Aesthetic.AUSTERE: ArtMedium.CARVING,
    Aesthetic.ORNATE: ArtMedium.MOSAIC,
    Aesthetic.GEOMETRIC: ArtMedium.ARCHITECTURE_ORNAMENT,
    Aesthetic.NATURAL: ArtMedium.CARVING,
    Aesthetic.MACABRE: ArtMedium.STATUE,
    Aesthetic.CELESTIAL: ArtMedium.FRESCO,
}

IMAGE_NAMES: dict[ArtMedium, str] = {
    ArtMedium.CARVING: "The Carving of {ruler}",
    ArtMedium.MOSAIC: "The Mosaic of {ruler}",
    ArtMedium.ARCHITECTURE_ORNAMENT: "The Ornamented Gate of {ruler}",
    ArtMedium.STATUE: "The Statue of {ruler}",
    ArtMedium.FRESCO: "The Fresco of {ruler}",
}

FAITH_RITES: dict[FuneralCustom, FuneralRite] = {
    FuneralCustom.BURIAL: FuneralRite.BURIAL,
    FuneralCustom.CREMATION: FuneralRite.BURNING,
    FuneralCustom.SKY_BURIAL: FuneralRite.EXPOSURE,
    FuneralCustom.SEA_BURIAL: FuneralRite.EXPOSURE,
    FuneralCustom.ENTOMBMENT: FuneralRite.BURIAL,
    FuneralCustom.ANCESTOR_SHRINE: FuneralRite.BURIAL,
    FuneralCustom.ENDOCANNIBALISM: FuneralRite.EXPOSURE,
    FuneralCustom.REANIMATION: FuneralRite.NONE,
    FuneralCustom.SOUL_BINDING: FuneralRite.BURNING,
}
