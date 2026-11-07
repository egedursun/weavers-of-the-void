from types import MappingProxyType

from aerona.catalog.genetics import LOCI, LOOKS_LOCI
from aerona.catalog.mind import SKILLS
from aerona.domain.enums.culture import ArtMedium, CalendarSlot
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import PreferenceKind, SkillFamily, ValueAxis

P = PreferenceKind
V = ValueAxis

PREFERENCE_LABELS: MappingProxyType[PreferenceKind, str] = MappingProxyType(
    {
        P.MATERIAL: "Material",
        P.FOOD: "Food",
        P.DRINK: "Drink",
        P.CREATURE: "Creature",
        P.PLANT: "Plant",
        P.COLOUR: "Colour",
        P.SHAPE: "Shape",
        P.ART_FORM: "Art form",
        P.ARTWORK_SUBJECT: "Subject of art",
        P.SEASON: "Time of year",
        P.WEATHER: "Weather",
        P.TERRAIN: "Land",
        P.ACTIVITY: "Pastime",
        P.CRAFT: "Craft",
        P.DEITY_ASPECT: "Aspect of the divine",
        P.LOOKS: "Looks",
    }
)

FOODS = (CommodityKind.GRAIN, CommodityKind.LIVESTOCK, CommodityKind.FISH, CommodityKind.BREAD)
DRINKS = MappingProxyType({"water": None, "ale": CommodityKind.GRAIN, "milk": CommodityKind.LIVESTOCK, "wine": CommodityKind.LUXURIES})
COLOURS = ("red", "orange", "yellow", "green", "blue", "violet", "white", "black", "grey", "brown", "gold", "silver")
SHAPES = ("circle", "square", "triangle", "spiral", "star", "cross", "wave", "knot", "crescent", "lattice")
ACTIVITIES = ("feasting", "singing", "dancing", "storytelling", "hunting", "games", "contests", "prayer", "travel", "gardening", "crafting", "study")
SUBJECTS = (
    EntityType.MORTAL,
    EntityType.PEOPLE,
    EntityType.PLACE,
    EntityType.EVENT,
    EntityType.SPECIES,
    EntityType.CELESTIAL,
    EntityType.LEGEND,
    EntityType.SPIRIT,
)
LOOKS_TARGETS = tuple(f"{locus.value}:{allele}" for locus in LOOKS_LOCI for allele in LOCI[locus].keys)
CRAFTS = tuple(skill for skill, spec in SKILLS.items() if spec.family is SkillFamily.CRAFT)

STATIC_TARGETS: MappingProxyType[PreferenceKind, tuple[str, ...]] = MappingProxyType(
    {
        P.MATERIAL: tuple(material.value for material in MaterialKind),
        P.FOOD: tuple(food.value for food in FOODS),
        P.DRINK: tuple(DRINKS),
        P.COLOUR: COLOURS,
        P.SHAPE: SHAPES,
        P.ART_FORM: tuple(medium.value for medium in ArtMedium),
        P.ARTWORK_SUBJECT: tuple(kind.value for kind in SUBJECTS),
        P.SEASON: tuple(slot.value for slot in CalendarSlot),
        P.WEATHER: tuple(weather.value for weather in WeatherKind),
        P.TERRAIN: tuple(terrain.value for terrain in TerrainKind),
        P.ACTIVITY: ACTIVITIES,
        P.CRAFT: tuple(craft.value for craft in CRAFTS),
        P.DEITY_ASPECT: tuple(domain.value for domain in Domain),
        P.LOOKS: LOOKS_TARGETS,
    }
)
SPECIES_KINDS = frozenset({P.CREATURE, P.PLANT})

ACTIVITY_VALUES: MappingProxyType[str, MappingProxyType[ValueAxis, int]] = MappingProxyType(
    {
        "feasting": MappingProxyType({V.LEISURE: 1, V.FRIENDSHIP: 1}),
        "singing": MappingProxyType({V.ARTWORK: 1}),
        "dancing": MappingProxyType({V.ARTWORK: 1, V.LEISURE: 1}),
        "storytelling": MappingProxyType({V.TRADITION: 1, V.ARTWORK: 1}),
        "hunting": MappingProxyType({V.NATURE: 1, V.MARTIAL: 1}),
        "games": MappingProxyType({V.COMPETITION: 1, V.LEISURE: 1}),
        "contests": MappingProxyType({V.COMPETITION: 1, V.HONOUR: 1}),
        "prayer": MappingProxyType({V.PIETY: 1}),
        "travel": MappingProxyType({V.XENOPHILIA: 1}),
        "gardening": MappingProxyType({V.NATURE: 1, V.PERSEVERANCE: 1}),
        "crafting": MappingProxyType({V.CRAFTSMANSHIP: 1}),
        "study": MappingProxyType({V.KNOWLEDGE: 1}),
    }
)


def target_label(kind: PreferenceKind, target: str) -> str:
    return target.replace("_", " ")
