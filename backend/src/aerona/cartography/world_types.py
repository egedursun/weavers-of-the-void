from dataclasses import dataclass
from enum import StrEnum

from aerona.domain.enums.world import WorldType


class TerrainShape(StrEnum):
    STANDARD = "standard"
    RING_BANDS = "ring_bands"
    FRAGMENTS = "fragments"
    TERMINATOR = "terminator"
    FLOATING_ISLAND = "floating_island"
    TERRACES = "terraces"
    HULL = "hull"
    RIDGES = "ridges"


@dataclass(frozen=True)
class WorldTypeProfile:
    world_type: WorldType
    name: str
    shape: TerrainShape
    biomes: tuple[str, str, str, str, str, str, str, str, str, str]
    palette: tuple[str, str, str, str, str, str, str, str, str, str]


WORLD_TYPE_PROFILES: dict[WorldType, WorldTypeProfile] = {
    WorldType.ORDINARY: WorldTypeProfile(
        WorldType.ORDINARY,
        "Ordinary world",
        TerrainShape.STANDARD,
        ("shallow sea", "deep sea", "beach", "steppe", "meadow", "forest", "barren hills", "wooded hills", "rocky mountains", "snowy peaks"),
        ("#3b6a86", "#1e3a52", "#d8c79a", "#b9ad74", "#8fae6a", "#4f7d4a", "#9a8a66", "#5d7a52", "#8b8478", "#eef1f2"),
    ),
    WorldType.OCEAN: WorldTypeProfile(
        WorldType.OCEAN,
        "Ocean world",
        TerrainShape.STANDARD,
        (
            "coral shallows",
            "abyssal sea",
            "white beach",
            "salt cliffs",
            "moss island",
            "mangrove",
            "rocky island",
            "misty island",
            "volcanic summit",
            "icy peak",
        ),
        ("#3a9bb0", "#0f2c4a", "#ece2c2", "#a9a28a", "#6fa585", "#3f7a5e", "#8a8576", "#6b8a7a", "#5b4a44", "#e8eef2"),
    ),
    WorldType.SAND: WorldTypeProfile(
        WorldType.SAND,
        "Sand world",
        TerrainShape.STANDARD,
        ("salt lake", "dried-up sea", "sand sea", "dune", "glass desert", "oasis", "red crags", "canyon", "wind pillars", "sand peak"),
        ("#d8d2c0", "#b8a888", "#e8c88a", "#dfb26c", "#c9b49a", "#7c9a5a", "#b5643c", "#9a5434", "#8a6a52", "#f0dcb4"),
    ),
    WorldType.ICE: WorldTypeProfile(
        WorldType.ICE,
        "Ice world",
        TerrainShape.STANDARD,
        ("ice floes", "black water", "snow shore", "ice field", "tundra", "needle forest", "glacier", "blue ice", "ice mountain", "storm peak"),
        ("#9cc2d6", "#1b2f45", "#e6eef2", "#d4e2ea", "#a9b8a4", "#4c6a62", "#bcd3e0", "#8fb3cc", "#c8d6e0", "#ffffff"),
    ),
    WorldType.LAVA: WorldTypeProfile(
        WorldType.LAVA,
        "Lava world",
        TerrainShape.STANDARD,
        (
            "lava lake",
            "magma ocean",
            "obsidian shore",
            "ash plain",
            "basalt plain",
            "sulphur marsh",
            "coal hills",
            "smoke valley",
            "volcano",
            "ember peak",
        ),
        ("#e8622c", "#7a1a0c", "#2a2226", "#5a5050", "#3c3434", "#9a9a3c", "#463a36", "#5c4c46", "#2c2020", "#ff9a3c"),
    ),
    WorldType.CRYSTAL: WorldTypeProfile(
        WorldType.CRYSTAL,
        "Crystal world",
        TerrainShape.STANDARD,
        (
            "light lake",
            "prism depths",
            "glass shore",
            "quartz plain",
            "echo meadow",
            "crystal forest",
            "chiming hills",
            "rainbow valley",
            "echoing mountains",
            "pure peak",
        ),
        ("#8fd6e6", "#2c3f7a", "#e8e4f4", "#c8c4dc", "#a8d4c8", "#7aa8c4", "#b4a4d8", "#d4a8c8", "#9c8cc4", "#ffffff"),
    ),
    WorldType.LIVING: WorldTypeProfile(
        WorldType.LIVING,
        "Living planet",
        TerrainShape.STANDARD,
        (
            "fluid lake",
            "blood sea",
            "membrane shore",
            "skin plain",
            "hair meadow",
            "flesh forest",
            "bone hills",
            "vein valley",
            "tooth ridges",
            "eye peak",
        ),
        ("#b04a5a", "#4a1020", "#d8a8a0", "#c48a7c", "#a87a6a", "#8a3c44", "#e0d4c0", "#9a4a5a", "#f0e8dc", "#e8c8b8"),
    ),
    WorldType.DEAD: WorldTypeProfile(
        WorldType.DEAD,
        "Realm of the dead",
        TerrainShape.STANDARD,
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
        ("#4a5a6a", "#141a22", "#8a8a86", "#c8c0b0", "#7a8478", "#5a6670", "#6a6460", "#4a5450", "#3c3a3a", "#d8d4cc"),
    ),
    WorldType.DREAM: WorldTypeProfile(
        WorldType.DREAM,
        "Dream realm",
        TerrainShape.STANDARD,
        (
            "dream water",
            "sleep depths",
            "cotton shore",
            "floating island",
            "violet meadow",
            "whisper forest",
            "slanted hills",
            "inverted valley",
            "cloud mountain",
            "star peak",
        ),
        ("#8a9ae6", "#2a2a6a", "#f0d8e8", "#d4c4f0", "#c4a8e0", "#8a7ac8", "#e0b4d4", "#b4a0dc", "#e8e4ff", "#fff4c8"),
    ),
    WorldType.MIRROR: WorldTypeProfile(
        WorldType.MIRROR,
        "Mirror world",
        TerrainShape.STANDARD,
        (
            "inverted water",
            "silver depths",
            "glass shore",
            "reflecting plain",
            "inverted meadow",
            "mirror forest",
            "echo hills",
            "broken valley",
            "silver mountains",
            "inverted peak",
        ),
        ("#c4d0dc", "#5a6a80", "#e8eef4", "#b8c4d4", "#a8b8c8", "#8496ac", "#d4dce6", "#9aaabc", "#74849a", "#ffffff"),
    ),
    WorldType.GAS: WorldTypeProfile(
        WorldType.GAS,
        "Gas giant",
        TerrainShape.STANDARD,
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
            "eye-storm",
        ),
        ("#d8b48a", "#7a4a2a", "#f0e0c4", "#e4c8a0", "#c8a87a", "#9a7a5a", "#f4e4cc", "#b48a6a", "#e89a5a", "#ffffff"),
    ),
    WorldType.RINGED: WorldTypeProfile(
        WorldType.RINGED,
        "Ringed world",
        TerrainShape.RING_BANDS,
        (
            "ringlit shallows",
            "shadowed deep",
            "pale shore",
            "dust steppe",
            "ringlight meadow",
            "banded forest",
            "shard hills",
            "shadow hills",
            "ring-rock mountains",
            "halo peak",
        ),
        ("#5a86a6", "#1c2c4a", "#d8d0b4", "#b4a884", "#94b07c", "#567c5c", "#a09a86", "#64745e", "#8a8890", "#f2eee4"),
    ),
    WorldType.ASTEROID_BELT: WorldTypeProfile(
        WorldType.ASTEROID_BELT,
        "Asteroid belt",
        TerrainShape.FRAGMENTS,
        (
            "dust drift",
            "open void",
            "regolith rim",
            "rubble field",
            "ice-crust field",
            "lichen hollow",
            "boulder hills",
            "crater hills",
            "shattered crags",
            "core spire",
        ),
        ("#2c2f3e", "#07080e", "#8c8478", "#6e665c", "#a4b0bc", "#5c7a5c", "#7a7064", "#5e5a56", "#4a4644", "#c8b89a"),
    ),
    WorldType.TIDALLY_LOCKED: WorldTypeProfile(
        WorldType.TIDALLY_LOCKED,
        "Tidally locked world",
        TerrainShape.TERMINATOR,
        (
            "twilight shallows",
            "frozen dark sea",
            "glare shore",
            "scorched plain",
            "twilight meadow",
            "dusk forest",
            "sunburnt hills",
            "shadow hills",
            "night glacier",
            "dawn peak",
        ),
        ("#4a6a8a", "#0e1a2c", "#f0d8a4", "#c47a44", "#8a9a6a", "#3c5a50", "#a4643c", "#4c5a6a", "#c4d4e4", "#ffe4b4"),
    ),
    WorldType.VOID_POCKET: WorldTypeProfile(
        WorldType.VOID_POCKET,
        "Void pocket",
        TerrainShape.FLOATING_ISLAND,
        (
            "void mist",
            "the nothing",
            "fraying edge",
            "grey plain",
            "pale meadow",
            "hollow forest",
            "drifting hills",
            "echo hills",
            "still mountains",
            "last peak",
        ),
        ("#2a2438", "#050408", "#6a6478", "#8a8690", "#7c8a84", "#4a5458", "#74707c", "#5a5a66", "#4a4652", "#d4d0dc"),
    ),
    WorldType.GODS_PALACE: WorldTypeProfile(
        WorldType.GODS_PALACE,
        "The god's palace",
        TerrainShape.TERRACES,
        (
            "reflecting pool",
            "abyssal cistern",
            "marble stair",
            "court of stone",
            "garden terrace",
            "sacred grove",
            "colonnade hills",
            "hanging gardens",
            "throne heights",
            "crown spire",
        ),
        ("#6ab4d0", "#1a3a5c", "#f4ecdc", "#d8ccb4", "#9cc48a", "#4f8a5a", "#e4dcc8", "#7aa86c", "#c8b48a", "#f5e27a"),
    ),
    WorldType.GENERATION_SHIP: WorldTypeProfile(
        WorldType.GENERATION_SHIP,
        "Generation ship",
        TerrainShape.HULL,
        (
            "coolant pool",
            "hull breach",
            "deck edge",
            "cargo plain",
            "hydroponic field",
            "grown forest",
            "machine ridges",
            "garden ridges",
            "bulkhead heights",
            "bridge tower",
        ),
        ("#3c8a9c", "#0a0e16", "#8a9098", "#6c7078", "#7cb46a", "#3f7a4e", "#5c6470", "#5a8a5e", "#9aa2ac", "#e4e8ec"),
    ),
    WorldType.CORPSE_WORLD: WorldTypeProfile(
        WorldType.CORPSE_WORLD,
        "Corpse-world",
        TerrainShape.RIDGES,
        (
            "ichor pool",
            "black blood sea",
            "skin shore",
            "rotting plain",
            "marrow meadow",
            "vein forest",
            "rib hills",
            "sinew valley",
            "spine ridges",
            "skull peak",
        ),
        ("#6a7a3c", "#200a10", "#c8aa94", "#8a6a54", "#b49a7c", "#6a2c34", "#e4dccc", "#8a4a4a", "#d4ccbc", "#f0ece0"),
    ),
}


def world_type_profile(world_type: WorldType) -> WorldTypeProfile:
    return WORLD_TYPE_PROFILES[world_type]
