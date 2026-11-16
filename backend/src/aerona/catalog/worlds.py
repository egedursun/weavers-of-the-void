from dataclasses import dataclass

from aerona.domain.enums.domain import Domain
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import Atmosphere, Discovery, Gravity, SkyEventKind, WorldType

W = WorldType


@dataclass(frozen=True)
class WorldTypeSpec:
    world_type: WorldType
    label: str
    description: str
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
            (Domain.EARTH, Domain.MEMORY),
        ),
        WorldTypeSpec(
            W.OCEAN,
            "Ocean world",
            "A world that is mostly water, with little land.",
            (Domain.SEA, Domain.STORM),
        ),
        WorldTypeSpec(
            W.SAND,
            "Sand world",
            "A dry world of sand and stone with little water.",
            (Domain.SUN, Domain.SALT),
        ),
        WorldTypeSpec(
            W.ICE,
            "Ice world",
            "A cold world where most of the water is frozen.",
            (Domain.ICE, Domain.SLEEP),
        ),
        WorldTypeSpec(
            W.LAVA,
            "Lava world",
            "A hot world with molten rock at or near its surface.",
            (Domain.FIRE, Domain.ASH),
        ),
        WorldTypeSpec(
            W.CRYSTAL,
            "Crystal world",
            "A world whose ground is largely crystal.",
            (Domain.GLASS, Domain.LIGHT),
        ),
        WorldTypeSpec(
            W.LIVING,
            "Living planet",
            "A world that is itself alive and feels what is done upon it.",
            (Domain.LIFE, Domain.BLOOD),
            living=True,
        ),
        WorldTypeSpec(
            W.DEAD,
            "Realm of the dead",
            "A world where souls go after death.",
            (Domain.DEATH, Domain.BONE),
            realm_of_dead=True,
        ),
        WorldTypeSpec(
            W.DREAM,
            "Dream realm",
            "A world shaped by dreaming rather than by nature.",
            (Domain.DREAM, Domain.SLEEP),
            hidden_route_methods=frozenset({TravelMethod.DREAM_JOURNEY}),
        ),
        WorldTypeSpec(
            W.MIRROR,
            "Mirror world",
            "An inverted twin: what dies in one is born in the other.",
            (Domain.GLASS, Domain.LIES),
            mirror=True,
        ),
        WorldTypeSpec(
            W.GAS,
            "Gas giant",
            "A giant world of gas with no solid surface.",
            (Domain.STORM, Domain.SKY),
            hidden_route_methods=frozenset({TravelMethod.SWALLOWED}),
        ),
        WorldTypeSpec(
            W.RINGED,
            "Ringed world",
            "A world with rings of ice and stone that shade parts of its land.",
            (Domain.STONE, Domain.MOON),
        ),
        WorldTypeSpec(
            W.ASTEROID_BELT,
            "Asteroid belt",
            "Many separate rocks sharing one orbit, with thin air between them.",
            (Domain.STONE, Domain.ROAD),
        ),
        WorldTypeSpec(
            W.TIDALLY_LOCKED,
            "Tidally locked world",
            "One side always faces its star and stays hot; the other always faces away and stays cold.",
            (Domain.SUN, Domain.SHADOW),
        ),
        WorldTypeSpec(
            W.VOID_POCKET,
            "Void pocket",
            "A small piece of land with nothing around it, close to what lies outside the cosmos.",
            (Domain.MADNESS, Domain.BORDER),
        ),
        WorldTypeSpec(
            W.GODS_PALACE,
            "The god's palace",
            "Halls and gardens raised by a god's will rather than by nature.",
            (Domain.LIGHT, Domain.OATH),
            artificial=True,
        ),
        WorldTypeSpec(
            W.GENERATION_SHIP,
            "Generation ship",
            "A vessel the size of a world, carrying its peoples between stars.",
            (Domain.CRAFT, Domain.ROAD),
            artificial=True,
        ),
        WorldTypeSpec(
            W.CORPSE_WORLD,
            "Corpse-world",
            "The body of a dead god, become a world.",
            (Domain.DEATH, Domain.HUNGER),
        ),
        WorldTypeSpec(
            W.FORGE,
            "Forge-world",
            "A world given over to furnaces and foundries, its mountains mined hollow.",
            (Domain.CRAFT, Domain.FIRE),
        ),
        WorldTypeSpec(
            W.SUPER_EARTH,
            "Super-earth",
            "A large rocky world with strong gravity, low mountains, broad seas and thick air.",
            (Domain.EARTH, Domain.STONE),
        ),
        WorldTypeSpec(
            W.ICE_GIANT,
            "Ice giant",
            "A cold giant of water, ammonia and methane ice with strong storms.",
            (Domain.ICE, Domain.STORM),
            hidden_route_methods=frozenset({TravelMethod.SWALLOWED}),
        ),
        WorldTypeSpec(
            W.HOT_GIANT,
            "Hot giant",
            "A gas giant close to its star, very hot on its day side, with winds faster than sound.",
            (Domain.FIRE, Domain.STORM),
            hidden_route_methods=frozenset({TravelMethod.SWALLOWED}),
        ),
        WorldTypeSpec(
            W.IRON,
            "Iron world",
            "A metal core without its rock: iron ground, rust and strong magnetic storms.",
            (Domain.WAR, Domain.EARTH),
        ),
        WorldTypeSpec(
            W.CARBON,
            "Diamond world",
            "A carbon-rich world of graphite, tar and diamond.",
            (Domain.STONE, Domain.TRADE),
        ),
        WorldTypeSpec(
            W.GREENHOUSE,
            "Greenhouse world",
            "A world whose thick air traps heat: acid clouds, great heat and a surface hidden from the sky.",
            (Domain.FIRE, Domain.PLAGUE),
        ),
        WorldTypeSpec(
            W.DWARF_PLANET,
            "Dwarf world",
            "A small, cold body with frost plains, nitrogen ice and almost no air.",
            (Domain.ICE, Domain.BORDER),
        ),
        WorldTypeSpec(
            W.CHTHONIAN,
            "Chthonian world",
            "The bare core of a giant whose air its star boiled away: hot, molten and close to its star.",
            (Domain.FIRE, Domain.DEATH),
        ),
        WorldTypeSpec(
            W.HYCEAN,
            "Steam-ocean world",
            "A hot ocean world under a hydrogen sky, with little land.",
            (Domain.SEA, Domain.LIFE),
        ),
        WorldTypeSpec(
            W.JUNGLE,
            "Jungle world",
            "A world covered in rainforest and swamp from pole to pole.",
            (Domain.PLANTS, Domain.HUNT),
        ),
        WorldTypeSpec(
            W.FUNGAL,
            "Fungal world",
            "A world where fungi grow larger than trees and cover much of the land.",
            (Domain.PLANTS, Domain.PLAGUE),
            hidden_route_methods=frozenset({TravelMethod.DREAM_JOURNEY}),
        ),
        WorldTypeSpec(
            W.SHATTERED,
            "Shattered world",
            "A world broken into separate land masses around a molten core.",
            (Domain.SKY, Domain.STONE),
        ),
        WorldTypeSpec(
            W.HOLLOW,
            "Hollow world",
            "A hollow shell with a small sun at its centre; its peoples live on the inner surface.",
            (Domain.EARTH, Domain.SUN),
        ),
        WorldTypeSpec(
            W.ICE_SHELL,
            "Ice-shell world",
            "A frozen crust over a hidden ocean, broken by geysers, with life near the deep vents.",
            (Domain.ICE, Domain.SEA),
        ),
        WorldTypeSpec(
            W.METHANE,
            "Methane world",
            "A cold world under an orange haze, with lakes and rain of liquid methane.",
            (Domain.STORM, Domain.ICE),
        ),
    )
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
    SkyEventKind.FLARE: "Stellar flare",
    SkyEventKind.AURORA: "Aurora",
    SkyEventKind.TRANSIT: "Transit across the star",
}


HARSH_ATMOSPHERES = frozenset({Atmosphere.NONE, Atmosphere.TOXIC})
