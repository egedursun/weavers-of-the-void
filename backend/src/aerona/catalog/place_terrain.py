from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.environment import PlaceCover, TerrainKind, WaterSource
from aerona.domain.enums.place import PlaceHeight, PlaceKind, SacredClass, SecretKind
from aerona.rules.registry import Rules

K = PlaceKind
S = SecretKind
C = PlaceCover
W = WaterSource
T = TerrainKind
H = PlaceHeight
R = SacredClass


@dataclass(frozen=True)
class PlaceKindSpec:
    label: str
    terrain: TerrainKind | None
    cover: PlaceCover
    water: WaterSource
    height: PlaceHeight
    chokepoint: bool
    sacred: SacredClass
    secrets: tuple[SecretKind, ...]
    deep: bool


PLACE_KINDS = total(
    PlaceKind,
    {
        K.MOUNTAIN: PlaceKindSpec("Mountain", T.MOUNTAINS, C.LIGHT, W.SPRING, H.HIGH, False, R.PROFANE, (S.HIDDEN_RESOURCE, S.UNDERWORLD_ENTRANCE), True),
        K.PEAK: PlaceKindSpec("Peak", T.MOUNTAINS, C.OPEN, W.NONE, H.HIGH, False, R.NOTABLE, (S.LOST_RITE, S.BURIED_RELIC), False),
        K.PASS: PlaceKindSpec("Pass", T.HIGH_PASS, C.LIGHT, W.NONE, H.HIGH, True, R.PROFANE, (S.BURIED_RELIC,), False),
        K.FOREST: PlaceKindSpec("Forest", T.FOREST, C.HEAVY, W.SPRING, H.FLAT, False, R.PROFANE, (S.SEALED_SPIRIT, S.LOST_RITE, S.HIDDEN_PEOPLE), False),
        K.GROVE: PlaceKindSpec("Grove", T.FOREST, C.HEAVY, W.SPRING, H.FLAT, False, R.NOTABLE, (S.LOST_RITE, S.SEALED_SPIRIT), False),
        K.RIVER: PlaceKindSpec("River", T.RIVER_VALLEY, C.OPEN, W.RIVER, H.FLAT, True, R.PROFANE, (S.HIDDEN_RESOURCE,), False),
        K.FORD: PlaceKindSpec("Ford", T.RIVER_VALLEY, C.OPEN, W.RIVER, H.FLAT, True, R.PROFANE, (S.BURIED_RELIC,), False),
        K.LAKE: PlaceKindSpec("Lake", None, C.OPEN, W.LAKE, H.FLAT, False, R.PROFANE, (S.SEALED_SPIRIT, S.BURIED_RELIC), False),
        K.SPRING: PlaceKindSpec("Spring", None, C.LIGHT, W.SPRING, H.FLAT, False, R.NOTABLE, (S.LOST_RITE, S.SEALED_SPIRIT), False),
        K.CAVE: PlaceKindSpec(
            "Cave", T.UNDERGROUND, C.HEAVY, W.SPRING, H.LOW, True, R.PROFANE, (S.HIDDEN_RESOURCE, S.SEALED_SPIRIT, S.UNDERWORLD_ENTRANCE), True
        ),
        K.CAVERN_SYSTEM: PlaceKindSpec(
            "Cavern system",
            T.UNDERGROUND,
            C.HEAVY,
            W.SPRING,
            H.LOW,
            True,
            R.PROFANE,
            (S.UNDERWORLD_ENTRANCE, S.SEALED_SPIRIT, S.HIDDEN_RESOURCE, S.HIDDEN_PEOPLE, S.SEALED_REALM),
            True,
        ),
        K.RUIN: PlaceKindSpec(
            "Ruin", T.RUIN_FIELD, C.HEAVY, W.WELL, H.LOW, False, R.PROFANE, (S.BURIED_RELIC, S.LOST_KNOWLEDGE, S.LOST_RITE, S.DORMANT_MIND), True
        ),
        K.ISLAND: PlaceKindSpec("Island", T.ISLAND, C.LIGHT, W.SEA, H.LOW, False, R.PROFANE, (S.BURIED_RELIC, S.HIDDEN_RESOURCE, S.HIDDEN_PEOPLE), False),
        K.SWAMP: PlaceKindSpec("Swamp", T.MARSH, C.LIGHT, W.LAKE, H.FLAT, False, R.PROFANE, (S.SEALED_SPIRIT, S.BURIED_RELIC), False),
        K.WELL: PlaceKindSpec("Well", None, C.OPEN, W.WELL, H.FLAT, False, R.NOTABLE, (S.LOST_RITE, S.SEALED_SPIRIT), True),
        K.VALLEY: PlaceKindSpec("Valley", T.RIVER_VALLEY, C.LIGHT, W.RIVER, H.FLAT, False, R.PROFANE, (S.HIDDEN_RESOURCE, S.HIDDEN_PEOPLE), False),
        K.CLIFF: PlaceKindSpec("Cliff", T.CANYON, C.LIGHT, W.NONE, H.HIGH, True, R.PROFANE, (S.HIDDEN_RESOURCE, S.BURIED_RELIC), True),
        K.VOLCANO: PlaceKindSpec(
            "Volcano", T.VOLCANIC, C.OPEN, W.NONE, H.HIGH, False, R.NOTABLE, (S.HIDDEN_RESOURCE, S.UNDERWORLD_ENTRANCE, S.SEALED_SPIRIT), True
        ),
        K.CRATER: PlaceKindSpec("Crater", None, C.OPEN, W.NONE, H.LOW, False, R.NOTABLE, (S.HIDDEN_RESOURCE, S.LOST_KNOWLEDGE, S.DORMANT_MIND), True),
        K.BATTLEFIELD: PlaceKindSpec("Battlefield", None, C.OPEN, W.NONE, H.FLAT, False, R.NOTABLE, (S.BURIED_RELIC, S.SEALED_SPIRIT), False),
        K.BURIAL_GROUND: PlaceKindSpec("Burial ground", None, C.LIGHT, W.NONE, H.LOW, False, R.HOLY, (S.BURIED_RELIC, S.SEALED_SPIRIT, S.LOST_KNOWLEDGE), True),
        K.LAIR: PlaceKindSpec("Lair", None, C.HEAVY, W.NONE, H.LOW, True, R.PROFANE, (S.BURIED_RELIC, S.HIDDEN_RESOURCE), True),
        K.NEXUS: PlaceKindSpec("Ley nexus", None, C.OPEN, W.NONE, H.FLAT, False, R.HOLY, (S.LOST_RITE, S.LOST_KNOWLEDGE, S.SEALED_REALM), False),
        K.SHRINE_SITE: PlaceKindSpec("Shrine site", None, C.LIGHT, W.SPRING, H.LOW, False, R.HOLY, (S.LOST_RITE, S.BURIED_RELIC), False),
        K.GOD_CORPSE: PlaceKindSpec(
            "God corpse", None, C.LIGHT, W.NONE, H.HIGH, False, R.HOLY, (S.SEALED_SPIRIT, S.LOST_KNOWLEDGE, S.BURIED_RELIC, S.SEALED_REALM), True
        ),
        K.MINE_SITE: PlaceKindSpec(
            "Mine site", T.UNDERGROUND, C.LIGHT, W.NONE, H.LOW, False, R.PROFANE, (S.HIDDEN_RESOURCE, S.SEALED_SPIRIT, S.UNDERWORLD_ENTRANCE), True
        ),
        K.HARBOUR_SITE: PlaceKindSpec("Harbour site", T.COAST, C.OPEN, W.SEA, H.FLAT, False, R.PROFANE, (S.BURIED_RELIC,), False),
        K.CROSSROADS: PlaceKindSpec("Crossroads", None, C.OPEN, W.WELL, H.FLAT, True, R.PROFANE, (S.BURIED_RELIC, S.LOST_KNOWLEDGE), False),
        K.WRECK_SITE: PlaceKindSpec(
            "Wreck site", None, C.LIGHT, W.SEA, H.LOW, False, R.NOTABLE, (S.BURIED_RELIC, S.HIDDEN_RESOURCE, S.LOST_KNOWLEDGE, S.DORMANT_MIND), True
        ),
        K.MEGASTRUCTURE_RUIN: PlaceKindSpec(
            "Megastructure ruin",
            T.RUIN_FIELD,
            C.HEAVY,
            W.NONE,
            H.HIGH,
            False,
            R.NOTABLE,
            (S.LOST_KNOWLEDGE, S.HIDDEN_RESOURCE, S.BURIED_RELIC, S.DORMANT_MIND, S.SEALED_REALM),
            True,
        ),
        K.ANOMALY: PlaceKindSpec(
            "Anomaly", None, C.OPEN, W.NONE, H.FLAT, False, R.NOTABLE, (S.LOST_KNOWLEDGE, S.SEALED_SPIRIT, S.DORMANT_MIND, S.SEALED_REALM), True
        ),
        K.DEBRIS_FIELD: PlaceKindSpec(
            "Debris field", T.VOID_SHORE, C.LIGHT, W.NONE, H.FLAT, True, R.PROFANE, (S.HIDDEN_RESOURCE, S.BURIED_RELIC, S.DORMANT_MIND), False
        ),
        K.REEF: PlaceKindSpec("Reef", T.SEA, C.LIGHT, W.SEA, H.LOW, True, R.PROFANE, (S.HIDDEN_RESOURCE, S.BURIED_RELIC), False),
        K.GLACIER: PlaceKindSpec("Glacier", T.ICE_SHEET, C.OPEN, W.LAKE, H.HIGH, False, R.PROFANE, (S.BURIED_RELIC, S.SEALED_SPIRIT), True),
        K.DUNES: PlaceKindSpec("Dunes", T.DESERT, C.OPEN, W.NONE, H.LOW, False, R.PROFANE, (S.BURIED_RELIC, S.HIDDEN_RESOURCE), False),
        K.CANYON: PlaceKindSpec(
            "Canyon", T.CANYON, C.LIGHT, W.RIVER, H.LOW, True, R.PROFANE, (S.HIDDEN_RESOURCE, S.UNDERWORLD_ENTRANCE, S.HIDDEN_PEOPLE), True
        ),
        K.OASIS: PlaceKindSpec("Oasis", T.DESERT, C.LIGHT, W.SPRING, H.FLAT, False, R.NOTABLE, (S.LOST_RITE, S.HIDDEN_RESOURCE, S.HIDDEN_PEOPLE), False),
        K.GEYSER: PlaceKindSpec("Geyser", T.VOLCANIC, C.OPEN, W.SPRING, H.FLAT, False, R.NOTABLE, (S.HIDDEN_RESOURCE, S.UNDERWORLD_ENTRANCE), True),
    },
)

TERRAIN_KINDS: dict[TerrainKind, PlaceKind] = {
    T.PLAIN: K.VALLEY,
    T.STEPPE: K.CROSSROADS,
    T.FOREST: K.FOREST,
    T.JUNGLE: K.FOREST,
    T.MARSH: K.SWAMP,
    T.HILLS: K.MOUNTAIN,
    T.MOUNTAINS: K.MOUNTAIN,
    T.HIGH_PASS: K.PASS,
    T.DESERT: K.CRATER,
    T.TUNDRA: K.VALLEY,
    T.ICE_SHEET: K.MOUNTAIN,
    T.VOLCANIC: K.VOLCANO,
    T.COAST: K.HARBOUR_SITE,
    T.ISLAND: K.ISLAND,
    T.RIVER_VALLEY: K.RIVER,
    T.CANYON: K.CLIFF,
    T.UNDERGROUND: K.CAVE,
    T.CRYSTAL_FIELD: K.CRATER,
    T.FLESH: K.SWAMP,
    T.VOID_SHORE: K.CLIFF,
    T.RUIN_FIELD: K.RUIN,
    T.URBAN: K.CROSSROADS,
    T.SEA: K.ISLAND,
}
DEFAULT_KIND = PlaceKind.VALLEY
BATTLEFIELD_FROM = frozenset({PlaceKind.VALLEY, PlaceKind.CROSSROADS})
WRECK_FROM = frozenset({PlaceKind.ISLAND, PlaceKind.REEF, PlaceKind.HARBOUR_SITE, PlaceKind.CLIFF, PlaceKind.LAKE, PlaceKind.RIVER, PlaceKind.FORD})
DEBRIS_FROM = frozenset({PlaceKind.CRATER, PlaceKind.VALLEY, PlaceKind.PEAK, PlaceKind.ANOMALY})
MEGA_RUIN_FROM = frozenset({PlaceKind.RUIN, PlaceKind.CRATER, PlaceKind.VALLEY, PlaceKind.CROSSROADS})
DEEPENS = {PlaceKind.CAVE: PlaceKind.CAVERN_SYSTEM, PlaceKind.MINE_SITE: PlaceKind.CAVERN_SYSTEM}

TERRAIN_NATURES: dict[TerrainKind, tuple[str, ...]] = {
    T.MOUNTAINS: ("pass", "cave", "chasm"),
    T.HILLS: ("hill", "upland", "cave"),
    T.CANYON: ("chasm", "pass"),
    T.MARSH: ("marsh", "lake"),
    T.FOREST: ("forest", "misty grove"),
    T.JUNGLE: ("forest", "marsh"),
    T.RIVER_VALLEY: ("river", "valley"),
    T.COAST: ("cove",),
    T.DESERT: ("dune", "oasis"),
    T.STEPPE: ("plain",),
    T.PLAIN: ("plain", "river"),
}


def height_of(rules: Rules, height: PlaceHeight) -> int:
    if height is PlaceHeight.HIGH:
        return rules.environment.place_height_high
    if height is PlaceHeight.LOW:
        return rules.environment.place_height_low
    return 0


def kind_spec(kind: PlaceKind) -> PlaceKindSpec:
    return PLACE_KINDS[kind]
