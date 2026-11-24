from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.couplings import CarrionRest
from aerona.domain.enums.culture import ArtMode
from aerona.domain.enums.demography import FuneralCustom, Job, NaturalTrait
from aerona.domain.enums.ecology import Diet, SizeClass
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import CreatureTrait

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
    mounted: bool = False
    frontless: bool = False


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
    label: str
    deed: str
    contagion_pct: int
    spirit_pct: int
    restless_shift: int
    mourning_pct: int
    binds_spirits: bool = False
    raises_dead: bool = False
    body_left: bool = True
    counts_as_rite: bool = True
    seals: bool = False
    cultural: bool = True
    carrion: CarrionRest | None = None
    preserves: bool = False
    second_rite: bool = False


KIN: dict[BodyPlan, KinSpec] = {
    BodyPlan.HUMANOID: KinSpec(100, 100, 100, 100, MountFit.RIDES),
    BodyPlan.QUADRUPED: KinSpec(130, 140, 100, 70, MountFit.IS_MOUNT, {J.HERDING: 125, J.FARMING: 110, J.CRAFTING: 75}),
    BodyPlan.AVIAN: KinSpec(90, 80, 100, 50, MountFit.FLIES, {J.TRADE: 120, J.BUILDING: 80, J.MINING: 65}),
    BodyPlan.SERPENTINE: KinSpec(80, 90, 95, 90, MountFit.CANNOT, {J.FISHING: 110, J.CRAFTING: 85}),
    BodyPlan.INSECTOID: KinSpec(70, 60, 90, 50, MountFit.CANNOT, {J.BUILDING: 130, J.MINING: 120, J.SCHOLARSHIP: 80}),
    BodyPlan.AQUATIC: KinSpec(
        100,
        100,
        100,
        170,
        MountFit.CANNOT,
        {J.FISHING: 170, J.FARMING: 55, J.MINING: 60},
    ),
    BodyPlan.AMORPHOUS: KinSpec(60, 70, 70, 80, MountFit.CANNOT, {J.CRAFTING: 115, J.FARMING: 80}),
    BodyPlan.ARBOREAL: KinSpec(90, 90, 100, 80, MountFit.RIDES, {J.CRAFTING: 115, J.BUILDING: 110, J.FARMING: 90}),
    BodyPlan.INCORPOREAL: KinSpec(20, 30, 10, 30, MountFit.FLIES, {J.CLERGY: 150, J.SCHOLARSHIP: 130, J.MINING: 40, J.FARMING: 40, J.BUILDING: 40}),
    BodyPlan.COLOSSAL: KinSpec(120, 130, 110, 40, MountFit.CANNOT, {J.BUILDING: 180, J.MINING: 150, J.CRAFTING: 55}),
    BodyPlan.CONSTRUCT: KinSpec(30, 80, 15, 50, MountFit.CANNOT, {J.MINING: 140, J.BUILDING: 130, J.CRAFTING: 120, J.CLERGY: 50, J.SCHOLARSHIP: 70}),
    BodyPlan.DIVINE_MANIFEST: KinSpec(50, 120, 30, 60, MountFit.FLIES, {J.CLERGY: 200, J.SCHOLARSHIP: 120, J.FARMING: 70}),
    BodyPlan.TENTACLED: KinSpec(85, 95, 100, 160, MountFit.CANNOT, {J.FISHING: 150, J.CRAFTING: 120, J.FARMING: 60}),
    BodyPlan.CENTAUROID: KinSpec(160, 150, 100, 60, MountFit.CANNOT, {J.HERDING: 120, J.TRADE: 115, J.CRAFTING: 90}, mounted=True),
    BodyPlan.RADIAL: KinSpec(55, 75, 90, 140, MountFit.CANNOT, {J.FISHING: 130, J.SCHOLARSHIP: 70}, frontless=True),
    BodyPlan.COLONIAL: KinSpec(80, 110, 120, 110, MountFit.CANNOT, {J.BUILDING: 120, J.FARMING: 110, J.SCHOLARSHIP: 75}),
    BodyPlan.HEXAPOD: KinSpec(110, 100, 130, 100, MountFit.CANNOT, {J.BUILDING: 120, J.MINING: 120, J.HERDING: 80}),
    BodyPlan.ROOTED: KinSpec(40, 60, 80, 40, MountFit.CANNOT, {J.FARMING: 160, J.SCHOLARSHIP: 110, J.TRADE: 40}),
}

SIZES: dict[SizeClass, SizeSpec] = {
    SizeClass.TINY: SizeSpec(40, 40, 45, 60, 130, True),
    SizeClass.SMALL: SizeSpec(70, 70, 75, 85, 115, True),
    SizeClass.MEDIUM: SizeSpec(100, 100, 100, 100, 100, True),
    SizeClass.LARGE: SizeSpec(160, 160, 140, 120, 90, True),
    SizeClass.HUGE: SizeSpec(250, 250, 190, 145, 70, False),
    SizeClass.COLOSSAL: SizeSpec(400, 400, 260, 170, 50, False),
    SizeClass.MICROSCOPIC: SizeSpec(5, 5, 5, 5, 150, False),
}

HEAVY_JOBS = frozenset({J.FARMING, J.MINING, J.BUILDING, J.SOLDIERING})
FINE_JOBS = frozenset({J.CRAFTING, J.SCHOLARSHIP, J.TRADE})

FOOD_SOURCES = frozenset({FoodSource.FIELDS, FoodSource.PASTURE, FoodSource.SEA})

DIETS: Mapping[Diet, DietSpec] = total(
    Diet,
    {
        Diet.OMNIVORE: DietSpec(
            {FoodSource.FIELDS: 100, FoodSource.PASTURE: 100, FoodSource.SEA: 100},
            frozenset({CommodityKind.GRAIN, CommodityKind.BREAD, CommodityKind.LIVESTOCK, CommodityKind.FISH}),
        ),
        Diet.HERBIVORE: DietSpec({FoodSource.FIELDS: 110}, frozenset({CommodityKind.GRAIN, CommodityKind.BREAD, CommodityKind.FODDER})),
        Diet.CARNIVORE: DietSpec({FoodSource.PASTURE: 110, FoodSource.SEA: 100}, frozenset({CommodityKind.LIVESTOCK, CommodityKind.FISH})),
        Diet.PISCIVORE: DietSpec({FoodSource.SEA: 140}, frozenset({CommodityKind.FISH})),
        Diet.FILTER: DietSpec({FoodSource.SEA: 120}, frozenset({CommodityKind.FISH})),
        Diet.SCAVENGER: DietSpec(
            {FoodSource.FIELDS: 70, FoodSource.PASTURE: 70, FoodSource.SEA: 70},
            frozenset({CommodityKind.GRAIN, CommodityKind.FODDER, CommodityKind.LIVESTOCK, CommodityKind.FISH}),
        ),
        Diet.SANGUIVORE: DietSpec({FoodSource.PASTURE: 60}, frozenset({CommodityKind.LIVESTOCK})),
        Diet.MINERAL: DietSpec({FoodSource.STONE: 100}, frozenset({CommodityKind.STONE, CommodityKind.ORE})),
        Diet.SOUL: DietSpec({FoodSource.ESSENCE: 100}, frozenset({CommodityKind.MAGICAL_REAGENTS, CommodityKind.INCENSE})),
        Diet.VOID: DietSpec({FoodSource.ESSENCE: 80}, frozenset({CommodityKind.MAGICAL_REAGENTS})),
        Diet.PHOTOSYNTHETIC: DietSpec({FoodSource.SUN: 100}, frozenset()),
        Diet.PARASITE: DietSpec({FoodSource.PASTURE: 50}, frozenset({CommodityKind.LIVESTOCK})),
        Diet.DECOMPOSER: DietSpec({FoodSource.FIELDS: 60}, frozenset({CommodityKind.DUNG, CommodityKind.FODDER})),
        Diet.CHEMOSYNTHETIC: DietSpec({FoodSource.STONE: 90}, frozenset({CommodityKind.ORE})),
        Diet.INSECTIVORE: DietSpec({FoodSource.FIELDS: 70, FoodSource.PASTURE: 40}, frozenset({CommodityKind.MEAT})),
        Diet.ENERGY: DietSpec({FoodSource.SUN: 80, FoodSource.ESSENCE: 60}, frozenset({CommodityKind.FUEL, CommodityKind.MAGICAL_REAGENTS})),
    },
)

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

CREATURE_DIETS: tuple[tuple[CreatureTrait, Diet], ...] = (
    (CreatureTrait.IRON_EATING, Diet.MINERAL),
    (CreatureTrait.STONESKIN, Diet.MINERAL),
    (CreatureTrait.SOUL_EATER, Diet.SOUL),
    (CreatureTrait.RADIANT, Diet.PHOTOSYNTHETIC),
)

PLAN_DIETS: dict[BodyPlan, Diet] = {
    BodyPlan.CONSTRUCT: Diet.MINERAL,
    BodyPlan.INCORPOREAL: Diet.SOUL,
    BodyPlan.DIVINE_MANIFEST: Diet.SOUL,
    BodyPlan.AQUATIC: Diet.PISCIVORE,
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

F = FuneralCustom
FUNERALS = total(
    FuneralCustom,
    {
        F.BURIAL: FuneralSpec("Burial", "lay their dead in the ground", 100, 100, 0, 100),
        F.CREMATION: FuneralSpec("Cremation", "burn their dead", 70, 70, -10, 90, body_left=False),
        F.SKY_BURIAL: FuneralSpec("Open laying", "leave their dead in the open", 115, 80, 5, 80),
        F.SEA_BURIAL: FuneralSpec("Water burial", "give their dead to the water", 85, 90, 10, 85),
        F.ENTOMBMENT: FuneralSpec("Entombment", "close their dead in tombs", 95, 130, -5, 140),
        F.ANCESTOR_SHRINE: FuneralSpec("Ancestor shrine", "keep the remains of their dead at home shrines", 110, 150, -15, 130),
        F.ENDOCANNIBALISM: FuneralSpec("Funerary eating", "eat of their dead", 160, 60, 15, 110),
        F.REANIMATION: FuneralSpec("Raising", "raise their dead to serve again", 130, 160, 30, 60, raises_dead=True, body_left=False, counts_as_rite=False),
        F.SOUL_BINDING: FuneralSpec("Soul binding", "bind the souls of their dead into vessels", 90, 50, -100, 100, binds_spirits=True, body_left=False),
        F.NAMELESS: FuneralSpec("Nameless rite", "put away their dead without their names", 100, 60, 20, 60, seals=True, cultural=False),
        F.NONE: FuneralSpec("No rite", "hold no rite for their dead", 130, 70, 25, 50, counts_as_rite=False, cultural=False),
        F.MUMMIFICATION: FuneralSpec("Preservation", "preserve the bodies of their dead", 60, 130, -10, 130, carrion=CarrionRest.MUMMIFIED, preserves=True),
        F.SECONDARY_BURIAL: FuneralSpec(
            "Second burial", "lay their dead to rest, then gather the bones in a second rite", 105, 120, -5, 140, carrion=CarrionRest.ROTTING, second_rite=True
        ),
        F.RETURN_TO_SOIL: FuneralSpec("Return to the soil", "give their dead back to the living ground", 90, 85, -5, 90),
        F.MEMORIAL_ONLY: FuneralSpec("Memorial", "honour the lost and unrecovered with a memorial alone", 0, 110, 10, 110, body_left=False),
    },
)

CULTURAL_FUNERALS = frozenset(custom for custom, spec in FUNERALS.items() if spec.cultural)


@dataclass(frozen=True)
class Style:
    ornament: int
    geometry: int
    colour: int
    scale: int
    symmetry: int


STYLE_AXES = ("ornament", "geometry", "colour", "scale", "symmetry")
STYLE_MIDPOINT = 50
STYLE_NEUTRAL = Style(ornament=50, geometry=50, colour=50, scale=50, symmetry=50)
VALUE_STYLE: Mapping[ValueAxis, Style] = MappingProxyType(
    {
        ValueAxis.MARTIAL: Style(ornament=15, geometry=55, colour=20, scale=45, symmetry=65),
        ValueAxis.WEALTH: Style(ornament=90, geometry=50, colour=80, scale=60, symmetry=60),
        ValueAxis.KNOWLEDGE: Style(ornament=50, geometry=90, colour=45, scale=55, symmetry=85),
        ValueAxis.NATURE: Style(ornament=40, geometry=10, colour=55, scale=40, symmetry=30),
        ValueAxis.DEATH: Style(ornament=60, geometry=40, colour=25, scale=50, symmetry=45),
        ValueAxis.PIETY: Style(ornament=60, geometry=65, colour=70, scale=80, symmetry=70),
    }
)
MODE_STYLE: MappingProxyType[ArtMode, Style] = total(
    ArtMode,
    {
        ArtMode.VERBAL: Style(ornament=0, geometry=20, colour=-20, scale=0, symmetry=20),
        ArtMode.MUSICAL: Style(ornament=10, geometry=0, colour=-20, scale=0, symmetry=20),
        ArtMode.MOVEMENT: Style(ornament=10, geometry=-30, colour=10, scale=0, symmetry=-10),
        ArtMode.FLAT_IMAGE: Style(ornament=20, geometry=10, colour=40, scale=0, symmetry=0),
        ArtMode.SOLID_IMAGE: Style(ornament=-10, geometry=0, colour=-20, scale=20, symmetry=10),
        ArtMode.BUILT: Style(ornament=10, geometry=30, colour=0, scale=40, symmetry=30),
        ArtMode.WORN: Style(ornament=30, geometry=0, colour=30, scale=-20, symmetry=0),
        ArtMode.CULINARY: Style(ornament=20, geometry=-10, colour=20, scale=-20, symmetry=0),
        ArtMode.SCENT: Style(ornament=10, geometry=-20, colour=0, scale=-20, symmetry=-10),
        ArtMode.LIGHT: Style(ornament=10, geometry=10, colour=40, scale=30, symmetry=10),
        ArtMode.RECORDED: Style(ornament=0, geometry=20, colour=10, scale=0, symmetry=10),
        ArtMode.INTERACTIVE: Style(ornament=10, geometry=20, colour=20, scale=0, symmetry=-10),
        ArtMode.LANDSCAPE: Style(ornament=0, geometry=-30, colour=20, scale=40, symmetry=-20),
        ArtMode.BODY: Style(ornament=30, geometry=-20, colour=20, scale=-30, symmetry=0),
        ArtMode.RITUAL_PERFORMANCE: Style(ornament=30, geometry=0, colour=10, scale=20, symmetry=20),
        ArtMode.TEXTILE_IMAGE: Style(ornament=40, geometry=20, colour=40, scale=-10, symmetry=20),
        ArtMode.MADE_MIND_ART: Style(ornament=0, geometry=30, colour=10, scale=0, symmetry=0),
        ArtMode.TACTILE: Style(ornament=10, geometry=10, colour=-30, scale=-10, symmetry=10),
        ArtMode.MIND: Style(ornament=-10, geometry=-20, colour=20, scale=10, symmetry=-10),
    },
)
STYLE_VALUES: MappingProxyType[str, ValueAxis] = MappingProxyType(
    {"ornament": ValueAxis.WEALTH, "geometry": ValueAxis.KNOWLEDGE, "colour": ValueAxis.ARTWORK, "scale": ValueAxis.HIERARCHY, "symmetry": ValueAxis.TRADITION}
)
IMAGE_MODES = (ArtMode.FLAT_IMAGE, ArtMode.SOLID_IMAGE, ArtMode.BUILT, ArtMode.TEXTILE_IMAGE, ArtMode.LIGHT)
