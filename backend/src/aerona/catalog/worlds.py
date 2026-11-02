from dataclasses import dataclass

from aerona.domain.enums.domain import Domain
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import Atmosphere, Discovery, Gravity, HorrorEventKind, SkyEventKind, StarType, WorldType

W = WorldType


@dataclass(frozen=True)
class WorldTypeSpec:
    world_type: WorldType
    label: str
    description: str
    biomes: tuple[str, ...]
    domains: tuple[Domain, Domain]
    realm_of_dead: bool = False
    living: bool = False
    mirror: bool = False
    hidden_route_methods: frozenset[TravelMethod] = frozenset()
    artificial: bool = False


WORLD_TYPES: dict[WorldType, WorldTypeSpec] = {
    spec.world_type: spec
    for spec in (
        WorldTypeSpec(
            W.ORDINARY,
            "Ordinary world",
            "Seas, plains, forests and mountains in their ordinary places.",
            ("shallow sea", "deep sea", "beach", "steppe", "meadow", "forest", "barren hills", "wooded hills", "rocky mountains", "snowy peaks"),
            (Domain.EARTH, Domain.MEMORY),
        ),
        WorldTypeSpec(
            W.OCEAN,
            "Ocean world",
            "Endless water with scattered islands.",
            (
                "coral shallows",
                "abyssal sea",
                "white beach",
                "salt cliff",
                "kelp island",
                "mangrove",
                "rocky island",
                "misty island",
                "volcanic summit",
                "icy peak",
            ),
            (Domain.SEA, Domain.STORM),
        ),
        WorldTypeSpec(
            W.SAND,
            "Sand world",
            "Dunes and dried seas under a merciless sun.",
            ("salt lake", "dried sea", "sand sea", "dune", "glass desert", "oasis", "red cliffs", "canyon", "wind pillars", "sand peak"),
            (Domain.SUN, Domain.SALT),
        ),
        WorldTypeSpec(
            W.ICE,
            "Ice world",
            "Floes, tundra and blue glaciers.",
            ("ice floe", "black water", "snow shore", "ice field", "tundra", "needle forest", "glacier", "blue ice", "ice mountain", "storm peak"),
            (Domain.ICE, Domain.SLEEP),
        ),
        WorldTypeSpec(
            W.LAVA,
            "Lava world",
            "Magma oceans, obsidian shores and ash plains.",
            ("lava lake", "magma ocean", "obsidian shore", "ash plain", "basalt plain", "sulphur marsh", "coal hills", "smoke valley", "volcano", "ember peak"),
            (Domain.FIRE, Domain.ASH),
        ),
        WorldTypeSpec(
            W.CRYSTAL,
            "Crystal world",
            "Prisms, ringing hills and lakes of light.",
            (
                "light lake",
                "prism depth",
                "glass shore",
                "quartz plain",
                "echo meadow",
                "crystal forest",
                "ringing hills",
                "rainbow valley",
                "echoing mountains",
                "pure peak",
            ),
            (Domain.GLASS, Domain.LIGHT),
        ),
        WorldTypeSpec(
            W.LIVING,
            "Living planet",
            "A world of flesh and bone that feels what walks on it.",
            ("fluid lake", "blood sea", "membrane shore", "skin plain", "hair meadow", "flesh forest", "bone hills", "vein valley", "tooth ridges", "eye peak"),
            (Domain.LIFE, Domain.BLOOD),
            living=True,
        ),
        WorldTypeSpec(
            W.DEAD,
            "Realm of the dead",
            "Where souls descend; rivers of oblivion and pale meadows.",
            (
                "water of oblivion",
                "black river",
                "ash shore",
                "bone plain",
                "pale meadow",
                "mist valley",
                "grave hills",
                "echo forest",
                "silent mountains",
                "dead peak",
            ),
            (Domain.DEATH, Domain.BONE),
            realm_of_dead=True,
        ),
        WorldTypeSpec(
            W.DREAM,
            "Dream realm",
            "Floating islands and inverted valleys of sleep.",
            (
                "dream water",
                "sleep depth",
                "cotton shore",
                "floating island",
                "violet meadow",
                "whisper forest",
                "slanted hills",
                "inverted valley",
                "cloud mountain",
                "star peak",
            ),
            (Domain.DREAM, Domain.SLEEP),
            hidden_route_methods=frozenset({TravelMethod.DREAM_JOURNEY}),
        ),
        WorldTypeSpec(
            W.MIRROR,
            "Mirror world",
            "An inverted twin: what dies in one is born in the other.",
            (
                "inverted water",
                "silver depth",
                "glass shore",
                "reflecting plain",
                "inverted meadow",
                "mirror forest",
                "echo hills",
                "broken valley",
                "silver mountains",
                "inverted peak",
            ),
            (Domain.GLASS, Domain.LIES),
            mirror=True,
        ),
        WorldTypeSpec(
            W.GAS,
            "Gas giant",
            "Cloud bands, floating forests and an eye of storms.",
            (
                "low cloud",
                "pressure abyss",
                "cloud shore",
                "wind island",
                "storm band",
                "floating forest",
                "cloud hill",
                "lightning valley",
                "vortex",
                "eye storm",
            ),
            (Domain.STORM, Domain.SKY),
            hidden_route_methods=frozenset({TravelMethod.SWALLOWED}),
        ),
        WorldTypeSpec(
            W.RINGED,
            "Ringed world",
            "A world crowned by rings of ice and stone that shadow its lands.",
            (
                "ring shadow sea",
                "deep sea",
                "shard beach",
                "shadow steppe",
                "ring meadow",
                "dusk forest",
                "debris hills",
                "crater wood",
                "ring-lit mountains",
                "shard peaks",
            ),
            (Domain.STONE, Domain.MOON),
        ),
        WorldTypeSpec(
            W.ASTEROID_BELT,
            "Asteroid belt",
            "Countless drifting rocks bound by thin air and old tethers.",
            ("void gap", "dust drift", "tether rock", "hollow rock", "moss rock", "fungus rock", "iron rock", "crater field", "spire rock", "shattered peak"),
            (Domain.STONE, Domain.ROAD),
        ),
        WorldTypeSpec(
            W.TIDALLY_LOCKED,
            "Tidally locked world",
            "One face burns in endless day, the other freezes in endless night.",
            (
                "night sea",
                "frozen deep",
                "twilight shore",
                "dusk steppe",
                "twilight meadow",
                "ember forest",
                "day desert",
                "scorched hills",
                "sun cliffs",
                "night peaks",
            ),
            (Domain.SUN, Domain.SHADOW),
        ),
        WorldTypeSpec(
            W.VOID_POCKET,
            "Void pocket",
            "A bubble of land adrift in nothing, close to what lies outside.",
            (
                "nothing",
                "edge of nothing",
                "pale rim",
                "grey plain",
                "silent meadow",
                "hollow forest",
                "drifting hills",
                "folded valley",
                "void spires",
                "the last peak",
            ),
            (Domain.MADNESS, Domain.BORDER),
        ),
        WorldTypeSpec(
            W.GODS_PALACE,
            "The god's palace",
            "Halls and gardens raised by a god's will rather than by nature.",
            (
                "reflecting pool",
                "golden deep",
                "marble shore",
                "court plain",
                "garden",
                "pillar forest",
                "terrace hills",
                "throne valley",
                "tower range",
                "throne peak",
            ),
            (Domain.LIGHT, Domain.OATH),
            artificial=True,
        ),
        WorldTypeSpec(
            W.GENERATION_SHIP,
            "Generation ship",
            "A vessel the size of a world, carrying its peoples between stars.",
            (
                "water tank",
                "coolant deep",
                "dock",
                "deck plain",
                "garden deck",
                "orchard deck",
                "engine hills",
                "corridor valley",
                "hull ridge",
                "bridge tower",
            ),
            (Domain.CRAFT, Domain.ROAD),
            artificial=True,
        ),
        WorldTypeSpec(
            W.CORPSE_WORLD,
            "Corpse-world",
            "The body of a dead god, its lands grown over bone and old blood.",
            ("blood lake", "marrow sea", "skin shore", "rib plain", "hair meadow", "sinew forest", "spine hills", "wound valley", "skull ridge", "crown peak"),
            (Domain.DEATH, Domain.HUNGER),
        ),
    )
}

STAR_TYPE_LABELS: dict[StarType, str] = {
    StarType.YELLOW_DWARF: "Yellow dwarf",
    StarType.RED_GIANT: "Red giant",
    StarType.BLUE_GIANT: "Blue giant",
    StarType.BINARY: "Binary star",
    StarType.WHITE_DWARF: "White dwarf",
    StarType.DEAD_STAR: "Dead star",
    StarType.BLACK_SUN: "Black sun",
    StarType.BROKEN_STAR: "Broken star",
    StarType.PULSAR: "Pulsar",
    StarType.STAR_REMNANT: "Star remnant",
    StarType.REBORN_STAR: "Reborn star",
}

GRAVITY_LABELS: dict[Gravity, str] = {Gravity.LOW: "Low", Gravity.NORMAL: "Normal", Gravity.HIGH: "High"}

ATMOSPHERE_LABELS: dict[Atmosphere, str] = {
    Atmosphere.NONE: "None",
    Atmosphere.THIN: "Thin",
    Atmosphere.NORMAL: "Normal",
    Atmosphere.DENSE: "Dense",
    Atmosphere.TOXIC: "Toxic",
}

DISCOVERY_LABELS: dict[Discovery, str] = {
    Discovery.KNOWN: "Known",
    Discovery.LEGEND: "Legend",
    Discovery.UNKNOWN: "Unknown",
    Discovery.FORGOTTEN: "Forgotten",
}

SKY_EVENT_LABELS: dict[SkyEventKind, str] = {
    SkyEventKind.ECLIPSE: "Eclipse",
    SkyEventKind.COMET: "Comet",
    SkyEventKind.ALIGNMENT: "Planetary alignment",
    SkyEventKind.SUPERNOVA: "Supernova",
    SkyEventKind.BLACK_SUN: "Birth of a black sun",
    SkyEventKind.VOID_STORM: "Void storm",
}

HORROR_EVENT_LABELS: dict[HorrorEventKind, str] = {
    HorrorEventKind.STARS_ALIGN: "The stars align",
    HorrorEventKind.EYE_IN_THE_SKY: "An eye in the sky",
    HorrorEventKind.WAVE_OF_SILENCE: "A wave of silence",
    HorrorEventKind.REVERSE_RAIN: "Rain falling upward",
    HorrorEventKind.VISIT_OF_THE_VOID: "Visit of the Void",
}

HARSH_ATMOSPHERES = frozenset({Atmosphere.NONE, Atmosphere.TOXIC})
