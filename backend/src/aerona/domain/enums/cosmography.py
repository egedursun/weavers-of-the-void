from enum import StrEnum


class GalaxyType(StrEnum):
    SPIRAL = "spiral"
    BARRED_SPIRAL = "barred_spiral"
    GRAND_DESIGN_SPIRAL = "grand_design_spiral"
    FLOCCULENT_SPIRAL = "flocculent_spiral"
    LENTICULAR = "lenticular"
    ELLIPTICAL = "elliptical"
    GIANT_ELLIPTICAL = "giant_elliptical"
    DWARF_ELLIPTICAL = "dwarf_elliptical"
    DWARF_SPHEROIDAL = "dwarf_spheroidal"
    IRREGULAR = "irregular"
    DWARF_IRREGULAR = "dwarf_irregular"
    RING = "ring"
    PECULIAR = "peculiar"
    STARBURST = "starburst"
    ACTIVE = "active"
    QUASAR_HOST = "quasar_host"
    LOW_SURFACE_BRIGHTNESS = "low_surface_brightness"
    ULTRA_DIFFUSE = "ultra_diffuse"
    LIVING = "living"
    DEAD = "dead"
    SHATTERED = "shattered"
    FORGED = "forged"
    DREAMING = "dreaming"
    MIRROR = "mirror"
    CROWNED = "crowned"
    HOLLOW = "hollow"
    EMBER = "ember"
    VEILED = "veiled"


class GalacticNucleus(StrEnum):
    NONE = "none"
    DORMANT = "dormant"
    ACTIVE = "active"
    QUASAR = "quasar"
    DEVOURED = "devoured"


class GalaxyAge(StrEnum):
    FORMING = "forming"
    YOUNG = "young"
    MATURE = "mature"
    OLD = "old"
    DYING = "dying"
    DEAD = "dead"


class GalacticZone(StrEnum):
    CORE = "core"
    BULGE = "bulge"
    BAR = "bar"
    INNER_DISC = "inner_disc"
    ARM = "arm"
    INTERARM = "interarm"
    OUTER_DISC = "outer_disc"
    HALO = "halo"
    RIM = "rim"
    INTERGALACTIC = "intergalactic"


class GalacticStructureKind(StrEnum):
    SPIRAL_ARM = "spiral_arm"
    BAR = "bar"
    BULGE = "bulge"
    CORE = "core"
    HALO = "halo"
    EMISSION_NEBULA = "emission_nebula"
    REFLECTION_NEBULA = "reflection_nebula"
    DARK_NEBULA = "dark_nebula"
    PLANETARY_NEBULA = "planetary_nebula"
    SUPERNOVA_REMNANT = "supernova_remnant"
    STELLAR_NURSERY = "stellar_nursery"
    OPEN_CLUSTER = "open_cluster"
    GLOBULAR_CLUSTER = "globular_cluster"
    STELLAR_STREAM = "stellar_stream"
    DUST_LANE = "dust_lane"
    SUPERBUBBLE = "superbubble"
    STAR_GRAVEYARD = "star_graveyard"
    LEY_SPIRAL = "ley_spiral"
    SEALED_VAULT = "sealed_vault"
    GODS_FORGE = "gods_forge"
    DEAD_LIGHT_DRIFT = "dead_light_drift"
    SINGING_NEBULA = "singing_nebula"
    RIFT_SCAR = "rift_scar"


class GalacticEventKind(StrEnum):
    CORE_OUTBURST = "core_outburst"
    GAMMA_RAY_BURST = "gamma_ray_burst"
    STARBURST = "starburst"
    TIDAL_STRIPPING = "tidal_stripping"
    MERGER_BEGUN = "merger_begun"
    MERGER_COMPLETED = "merger_completed"
    HYPERVELOCITY_STAR = "hypervelocity_star"
    NEBULA_COLLAPSE = "nebula_collapse"
    GALACTIC_DIMMING = "galactic_dimming"
    AWAKENING = "awakening"
    SHROUDING = "shrouding"
    SEVERING = "severing"


class ClusterKind(StrEnum):
    GALAXY_GROUP = "galaxy_group"
    LOCAL_GROUP = "local_group"
    POOR_CLUSTER = "poor_cluster"
    RICH_CLUSTER = "rich_cluster"
    SUPERCLUSTER = "supercluster"
    FILAMENT = "filament"
    WALL = "wall"
    VOID = "void"
    CROWN_CLUSTER = "crown_cluster"
    DROWNED_CLUSTER = "drowned_cluster"
    FORGE_CLUSTER = "forge_cluster"
    DREAM_CLUSTER = "dream_cluster"
    MIRROR_CLUSTER = "mirror_cluster"


class DimensionKind(StrEnum):
    PRIME = "prime"
    PARALLEL = "parallel"
    MIRROR = "mirror"
    POCKET = "pocket"
    BUBBLE_UNIVERSE = "bubble_universe"
    BRANE = "brane"
    HIGHER_DIMENSIONAL = "higher_dimensional"
    ANTIMATTER = "antimatter"
    QUANTUM_BRANCH = "quantum_branch"
    TIME_REVERSED = "time_reversed"
    COMPACTIFIED = "compactified"
    ASTRAL = "astral"
    ETHEREAL = "ethereal"
    DREAM = "dream"
    SHADOW = "shadow"
    SPIRIT = "spirit"
    FEY = "fey"
    ELEMENTAL = "elemental"
    CELESTIAL = "celestial"
    INFERNAL = "infernal"
    ABYSSAL = "abyssal"
    LIMBO = "limbo"
    FAR_REALM = "far_realm"
    CLOCKWORK = "clockwork"
    CHAOS = "chaos"
    UNDERWORLD = "underworld"
    DIVINE_DOMAIN = "divine_domain"
    VOID_BETWEEN = "void_between"


class DimensionElement(StrEnum):
    FIRE = "fire"
    WATER = "water"
    EARTH = "earth"
    AIR = "air"
    VOID = "void"
    LIGHT = "light"
    SHADOW = "shadow"
    ICE = "ice"
    LIGHTNING = "lightning"
    METAL = "metal"
    WOOD = "wood"


class Causality(StrEnum):
    STRICT = "strict"
    LOOSE = "loose"
    BROKEN = "broken"


class DimensionalEventKind(StrEnum):
    INCURSION = "incursion"
    CONVERGENCE = "convergence"
    VEIL_THINNING = "veil_thinning"
    PLANAR_ALIGNMENT = "planar_alignment"
    BLEED = "bleed"
    SCHISM = "schism"
    COLLAPSE = "collapse"
    ECHO = "echo"


class RiftState(StrEnum):
    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"
    SEALED = "sealed"
    COLLAPSED = "collapsed"


OPEN_RIFT_STATES = frozenset({RiftState.OPENING, RiftState.OPEN, RiftState.CLOSING})


class RiftCause(StrEnum):
    RITE_BACKLASH = "rite_backlash"
    LEAK_PEAK = "leak_peak"
    CONVERGENCE = "convergence"
    GOD = "god"
    BEING = "being"
    PHENOMENON = "phenomenon"
    CREATOR = "creator"


class RouteScope(StrEnum):
    SYSTEM = "system"
    STELLAR = "stellar"
    GALACTIC = "galactic"
    INTERGALACTIC = "intergalactic"
    INTERCLUSTER = "intercluster"
    INTERDIMENSIONAL = "interdimensional"


class BeingKind(StrEnum):
    PLANAR_NATIVE = "planar_native"
    DIMENSION_WALKER = "dimension_walker"
    RIFT_SPAWN = "rift_spawn"
    HIGHER_DIMENSIONAL = "higher_dimensional"
    STAR_EATER = "star_eater"
    NEBULA_MIND = "nebula_mind"
    GALACTIC_LEVIATHAN = "galactic_leviathan"
    VOID_SHEPHERD = "void_shepherd"
    ECHO = "echo"
    TIME_WANDERER = "time_wanderer"
    COSMIC_TITAN = "cosmic_titan"
    VEIL_WARDEN = "veil_warden"
    PLANE_SOVEREIGN = "plane_sovereign"
    SWARM_INTELLIGENCE = "swarm_intelligence"
    LIVING_CONSTELLATION = "living_constellation"


class BeingScale(StrEnum):
    WORLD = "world"
    SYSTEM = "system"
    GALAXY = "galaxy"
    CLUSTER = "cluster"
    DIMENSION = "dimension"


class BeingPhase(StrEnum):
    DORMANT = "dormant"
    ROAMING = "roaming"
    MANIFEST = "manifest"
    INCURSION = "incursion"
    BOUND = "bound"
    BANISHED = "banished"


class BeingAgenda(StrEnum):
    FEED = "feed"
    EXPLORE = "explore"
    CONQUER = "conquer"
    GUARD = "guard"
    TRADE = "trade"
    FLEE = "flee"
    SEEK_WORSHIP = "seek_worship"
    UNMAKE = "unmake"
    MEND = "mend"


class PhenomenonKind(StrEnum):
    ETERNAL_STORM = "eternal_storm"
    TIME_SLIP = "time_slip"
    LEAK_WOUND = "leak_wound"
    LEY_NEXUS_FLARE = "ley_nexus_flare"
    GOD_CORPSE_AURA = "god_corpse_aura"
    LIVING_FOG = "living_fog"
    CRYSTAL_BLOOM = "crystal_bloom"
    DEAD_ZONE = "dead_zone"
    MIRROR_LAKE = "mirror_lake"
    GRAVITY_WELL = "gravity_well"
    SINGING_STONES = "singing_stones"
    AURORA_PERMANENT = "aurora_permanent"
    GHOST_ROAD = "ghost_road"
    BLIGHT = "blight"


class PhenomenonCause(StrEnum):
    RITE_BACKLASH = "rite_backlash"
    GOD_DEATH = "god_death"
    LAW_CONFLICT = "law_conflict"
    SKY_EVENT = "sky_event"
    LEAK_PEAK = "leak_peak"
    BATTLEFIELD = "battlefield"
    RIFT = "rift"
    DIVINE = "divine"


class StarAge(StrEnum):
    YOUNG = "young"
    MAIN = "main"
    OLD = "old"
    DYING = "dying"
    DEAD = "dead"
    REBORN = "reborn"


class WorldAge(StrEnum):
    YOUNG = "young"
    MATURE = "mature"
    OLD = "old"
    DYING = "dying"


class OceanCurrent(StrEnum):
    NONE = "none"
    WARM = "warm"
    COLD = "cold"


class ApocalypseVariant(StrEnum):
    RUIN = "ruin"
    WORLD_WAR = "world_war"
    OUTER_DESCENT = "outer_descent"
    TWILIGHT_OF_GODS = "twilight_of_gods"
    DIMENSIONAL_COLLAPSE = "dimensional_collapse"
    GALACTIC_DEATH = "galactic_death"


class OmenReading(StrEnum):
    GOOD = "good"
    EVIL = "evil"
    NEUTRAL = "neutral"
