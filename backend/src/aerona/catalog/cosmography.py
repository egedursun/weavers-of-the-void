from dataclasses import dataclass
from types import MappingProxyType

from aerona.domain.enums.cosmography import (
    ApocalypseVariant,
    BeingAgenda,
    BeingKind,
    BeingPhase,
    BeingScale,
    Causality,
    ClusterKind,
    DimensionalEventKind,
    DimensionElement,
    DimensionKind,
    GalacticEventKind,
    GalacticNucleus,
    GalacticStructureKind,
    GalacticZone,
    GalaxyAge,
    GalaxyType,
    OmenReading,
    PhenomenonCause,
    PhenomenonKind,
    RiftCause,
    RiftState,
    RouteScope,
    StarAge,
    WorldAge,
)
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import NaturalLaw


@dataclass(frozen=True)
class KindSpec:
    label: str
    description: str


GALAXY_TYPES: MappingProxyType[GalaxyType, KindSpec] = MappingProxyType(
    {
        GalaxyType.SPIRAL: KindSpec("Spiral galaxy", "A flat disc of stars wound into arms around a bright bulge."),
        GalaxyType.BARRED_SPIRAL: KindSpec("Barred spiral galaxy", "A spiral whose arms start from the ends of a straight bar of stars through its centre."),
        GalaxyType.GRAND_DESIGN_SPIRAL: KindSpec("Grand-design spiral", "A spiral with two long, clear arms that sweep the whole disc."),
        GalaxyType.FLOCCULENT_SPIRAL: KindSpec("Flocculent spiral", "A spiral of many short, broken arm pieces."),
        GalaxyType.LENTICULAR: KindSpec("Lenticular galaxy", "A disc without arms, its gas spent; few new stars are born."),
        GalaxyType.ELLIPTICAL: KindSpec("Elliptical galaxy", "A round or oval swarm of old stars with little gas left."),
        GalaxyType.GIANT_ELLIPTICAL: KindSpec("Giant elliptical galaxy", "A vast old swarm at the heart of a cluster, grown by swallowing others."),
        GalaxyType.DWARF_ELLIPTICAL: KindSpec("Dwarf elliptical galaxy", "A small oval swarm of old stars."),
        GalaxyType.DWARF_SPHEROIDAL: KindSpec("Dwarf spheroidal galaxy", "A faint, loose ball of old stars, often a satellite of a larger galaxy."),
        GalaxyType.IRREGULAR: KindSpec("Irregular galaxy", "A galaxy with no settled shape, rich in gas and new stars."),
        GalaxyType.DWARF_IRREGULAR: KindSpec("Dwarf irregular galaxy", "A small shapeless galaxy, young and poor in metals."),
        GalaxyType.RING: KindSpec("Ring galaxy", "A ring of young stars around an empty middle, left by a collision."),
        GalaxyType.PECULIAR: KindSpec("Peculiar galaxy", "A galaxy bent out of shape by another passing through or into it."),
        GalaxyType.STARBURST: KindSpec("Starburst galaxy", "A galaxy bearing new stars far faster than it can last."),
        GalaxyType.ACTIVE: KindSpec("Active galaxy", "A galaxy whose central black hole is feeding and shines brighter than its stars."),
        GalaxyType.QUASAR_HOST: KindSpec("Quasar host", "A galaxy around a quasar, the brightest kind of feeding black hole."),
        GalaxyType.LOW_SURFACE_BRIGHTNESS: KindSpec("Low surface brightness galaxy", "A wide, dim disc with few stars spread thin."),
        GalaxyType.ULTRA_DIFFUSE: KindSpec("Ultra-diffuse galaxy", "A galaxy as wide as a great spiral with a hundredth of its stars."),
        GalaxyType.LIVING: KindSpec("Living galaxy", "A galaxy that is one living thing; its stars answer one will."),
        GalaxyType.DEAD: KindSpec("Dead galaxy", "A galaxy whose stars have nearly all gone out."),
        GalaxyType.SHATTERED: KindSpec("Shattered galaxy", "A galaxy broken into drifting pieces."),
        GalaxyType.FORGED: KindSpec("Forged galaxy", "A galaxy built on purpose by a god or a maker."),
        GalaxyType.DREAMING: KindSpec("Dreaming galaxy", "A galaxy that half exists in dream; its stars come and go."),
        GalaxyType.MIRROR: KindSpec("Mirror galaxy", "A galaxy that repeats another, reversed."),
        GalaxyType.CROWNED: KindSpec("Crowned galaxy", "A galaxy ruled whole by one power."),
        GalaxyType.HOLLOW: KindSpec("Hollow galaxy", "A galaxy with an empty heart where its core should be."),
        GalaxyType.EMBER: KindSpec("Ember galaxy", "A galaxy in its last red glow."),
        GalaxyType.VEILED: KindSpec("Veiled galaxy", "A galaxy hidden from those outside it."),
    }
)


CLUSTER_KINDS: MappingProxyType[ClusterKind, KindSpec] = MappingProxyType(
    {
        ClusterKind.GALAXY_GROUP: KindSpec("Galaxy group", "A few dozen galaxies held together by their pull."),
        ClusterKind.LOCAL_GROUP: KindSpec("Local group", "The small group a home galaxy belongs to."),
        ClusterKind.POOR_CLUSTER: KindSpec("Poor cluster", "A cluster of some hundred galaxies."),
        ClusterKind.RICH_CLUSTER: KindSpec("Rich cluster", "A cluster of a thousand galaxies in a hot sea of gas."),
        ClusterKind.SUPERCLUSTER: KindSpec("Supercluster", "A great gathering of groups and clusters."),
        ClusterKind.FILAMENT: KindSpec("Filament", "A long chain of galaxies joining clusters."),
        ClusterKind.WALL: KindSpec("Wall", "A wide sheet of galaxies at the edge of the voids."),
        ClusterKind.VOID: KindSpec("Void", "A vast emptiness with few galaxies."),
        ClusterKind.CROWN_CLUSTER: KindSpec("Crown cluster", "A cluster ruled by one power."),
        ClusterKind.DROWNED_CLUSTER: KindSpec("Drowned cluster", "A cluster half lost into another dimension."),
        ClusterKind.FORGE_CLUSTER: KindSpec("Forge cluster", "A cluster built by gods."),
        ClusterKind.DREAM_CLUSTER: KindSpec("Dream cluster", "A cluster that half exists in dream."),
        ClusterKind.MIRROR_CLUSTER: KindSpec("Mirror cluster", "A cluster that repeats another, reversed."),
    }
)


DIMENSION_KINDS: MappingProxyType[DimensionKind, KindSpec] = MappingProxyType(
    {
        DimensionKind.PRIME: KindSpec("Prime dimension", "The common layer of existence where the cosmos began."),
        DimensionKind.PARALLEL: KindSpec("Parallel dimension", "A sibling of another dimension with its own history."),
        DimensionKind.MIRROR: KindSpec("Mirror dimension", "A dimension that repeats another, reversed."),
        DimensionKind.POCKET: KindSpec("Pocket dimension", "A small dimension inside another."),
        DimensionKind.BUBBLE_UNIVERSE: KindSpec("Bubble universe", "A whole universe in a bubble of its own."),
        DimensionKind.BRANE: KindSpec("Brane", "A layer of space lying beside another along a hidden direction."),
        DimensionKind.HIGHER_DIMENSIONAL: KindSpec("Higher-dimensional space", "A space with more directions than the prime."),
        DimensionKind.ANTIMATTER: KindSpec("Antimatter dimension", "A dimension of matter that unmakes the prime's on touch."),
        DimensionKind.QUANTUM_BRANCH: KindSpec("Quantum branch", "A branch where another outcome happened."),
        DimensionKind.TIME_REVERSED: KindSpec("Time-reversed dimension", "A dimension where time runs the other way."),
        DimensionKind.COMPACTIFIED: KindSpec("Compactified dimension", "A dimension folded very small."),
        DimensionKind.ASTRAL: KindSpec("Astral plane", "A plane of thought and travel between the others."),
        DimensionKind.ETHEREAL: KindSpec("Ethereal plane", "A plane lying close over the prime, seen as through a mist."),
        DimensionKind.DREAM: KindSpec("Dream dimension", "A dimension made of dreams."),
        DimensionKind.SHADOW: KindSpec("Shadow dimension", "A darker copy lying under the prime."),
        DimensionKind.SPIRIT: KindSpec("Spirit realm", "The realm where spirits dwell."),
        DimensionKind.FEY: KindSpec("Fey realm", "A realm of old powers where time runs strangely."),
        DimensionKind.ELEMENTAL: KindSpec("Elemental plane", "A plane of one element."),
        DimensionKind.CELESTIAL: KindSpec("Celestial realm", "A realm of order and reward."),
        DimensionKind.INFERNAL: KindSpec("Infernal realm", "A realm of law and punishment."),
        DimensionKind.ABYSSAL: KindSpec("Abyssal realm", "A realm of endless ruin."),
        DimensionKind.LIMBO: KindSpec("Limbo", "A grey in-between where little happens."),
        DimensionKind.FAR_REALM: KindSpec("Far realm", "A realm beyond sense, outside the order of the others."),
        DimensionKind.CLOCKWORK: KindSpec("Clockwork plane", "A plane of perfect order."),
        DimensionKind.CHAOS: KindSpec("Plane of chaos", "A plane that never holds a shape."),
        DimensionKind.UNDERWORLD: KindSpec("Underworld", "A realm of the dead."),
        DimensionKind.DIVINE_DOMAIN: KindSpec("Divine domain", "A plane that belongs to one god."),
        DimensionKind.VOID_BETWEEN: KindSpec("Void between", "The empty dark between the dimensions."),
    }
)


STRUCTURE_KINDS: MappingProxyType[GalacticStructureKind, KindSpec] = MappingProxyType(
    {
        GalacticStructureKind.SPIRAL_ARM: KindSpec("Spiral arm", "One of the arms of a spiral, where most stars are born."),
        GalacticStructureKind.BAR: KindSpec("Bar", "The straight band of stars through a barred galaxy's centre."),
        GalacticStructureKind.BULGE: KindSpec("Bulge", "The swollen crowd of old stars around the centre."),
        GalacticStructureKind.CORE: KindSpec("Galactic core", "The centre of the galaxy, around its black hole."),
        GalacticStructureKind.HALO: KindSpec("Halo", "The thin ball of old stars around the disc."),
        GalacticStructureKind.EMISSION_NEBULA: KindSpec("Emission nebula", "A glowing cloud of gas lit by the young stars inside it."),
        GalacticStructureKind.REFLECTION_NEBULA: KindSpec("Reflection nebula", "A dust cloud shining with the light of nearby stars."),
        GalacticStructureKind.DARK_NEBULA: KindSpec("Dark nebula", "A cloud of dust thick enough to hide the stars behind and inside it."),
        GalacticStructureKind.PLANETARY_NEBULA: KindSpec("Planetary nebula", "The shell a dying star has thrown off."),
        GalacticStructureKind.SUPERNOVA_REMNANT: KindSpec("Supernova remnant", "The spreading wreck of an exploded star, rich in new metals."),
        GalacticStructureKind.STELLAR_NURSERY: KindSpec("Stellar nursery", "A dense cloud where new stars are being born."),
        GalacticStructureKind.OPEN_CLUSTER: KindSpec("Open cluster", "A loose family of stars born together."),
        GalacticStructureKind.GLOBULAR_CLUSTER: KindSpec("Globular cluster", "A tight ancient ball of old, metal-poor stars."),
        GalacticStructureKind.STELLAR_STREAM: KindSpec("Stellar stream", "A trail of stars torn from a smaller galaxy."),
        GalacticStructureKind.DUST_LANE: KindSpec("Dust lane", "A band of dust across the disc that dims what lies in it."),
        GalacticStructureKind.SUPERBUBBLE: KindSpec("Superbubble", "A great hollow blown out by many supernovae."),
        GalacticStructureKind.STAR_GRAVEYARD: KindSpec("Star graveyard", "A place where dead stars gather."),
        GalacticStructureKind.LEY_SPIRAL: KindSpec("Ley spiral", "A lane of magic running along the galaxy."),
        GalacticStructureKind.SEALED_VAULT: KindSpec("Sealed vault", "A region of space shut away on purpose."),
        GalacticStructureKind.GODS_FORGE: KindSpec("Gods' forge", "A place where gods make stars and worlds."),
        GalacticStructureKind.DEAD_LIGHT_DRIFT: KindSpec("Drift of dead light", "A drift of light from stars long gone."),
        GalacticStructureKind.SINGING_NEBULA: KindSpec("Singing nebula", "A cloud that carries a sound across space."),
        GalacticStructureKind.RIFT_SCAR: KindSpec("Rift scar", "The healed tear where a dimension once broke through."),
    }
)


GALACTIC_ZONES: MappingProxyType[GalacticZone, KindSpec] = MappingProxyType(
    {
        GalacticZone.CORE: KindSpec("Core zone", "The crowded, hard-lit centre of the galaxy."),
        GalacticZone.BULGE: KindSpec("Bulge zone", "The swollen crowd of old stars around the core."),
        GalacticZone.BAR: KindSpec("Bar zone", "The band of stars through the centre of a barred galaxy."),
        GalacticZone.INNER_DISC: KindSpec("Inner disc", "The busy inner part of the disc."),
        GalacticZone.ARM: KindSpec("Arm", "Inside a spiral arm, among young stars."),
        GalacticZone.INTERARM: KindSpec("Between the arms", "The quieter space between the arms."),
        GalacticZone.OUTER_DISC: KindSpec("Outer disc", "The calm outer part of the disc."),
        GalacticZone.HALO: KindSpec("Halo zone", "The thin ball of old stars above and below the disc."),
        GalacticZone.RIM: KindSpec("Rim", "The far edge of the galaxy."),
        GalacticZone.INTERGALACTIC: KindSpec("Intergalactic space", "Out between the galaxies, belonging to none."),
    }
)


PHENOMENON_KINDS: MappingProxyType[PhenomenonKind, KindSpec] = MappingProxyType(
    {
        PhenomenonKind.ETERNAL_STORM: KindSpec("Eternal storm", "A storm that never ends."),
        PhenomenonKind.TIME_SLIP: KindSpec("Time slip", "A place where time skips and stalls."),
        PhenomenonKind.LEAK_WOUND: KindSpec("Leak wound", "A raw opening where the outside leaks in."),
        PhenomenonKind.LEY_NEXUS_FLARE: KindSpec("Ley nexus flare", "A blaze of magic where ley lines cross."),
        PhenomenonKind.GOD_CORPSE_AURA: KindSpec("God-corpse aura", "The lingering power around the body of a dead god."),
        PhenomenonKind.LIVING_FOG: KindSpec("Living fog", "A fog that moves by its own will."),
        PhenomenonKind.CRYSTAL_BLOOM: KindSpec("Crystal bloom", "Crystal growing out of the ground like a plant."),
        PhenomenonKind.DEAD_ZONE: KindSpec("Dead zone", "Ground where nothing grows."),
        PhenomenonKind.MIRROR_LAKE: KindSpec("Mirror lake", "Water that shows another place."),
        PhenomenonKind.GRAVITY_WELL: KindSpec("Gravity well", "A place where weight itself is wrong."),
        PhenomenonKind.SINGING_STONES: KindSpec("Singing stones", "Stones that sound on their own."),
        PhenomenonKind.AURORA_PERMANENT: KindSpec("Lasting aurora", "Lights that never leave the sky."),
        PhenomenonKind.GHOST_ROAD: KindSpec("Ghost road", "A road the dead still walk."),
        PhenomenonKind.BLIGHT: KindSpec("Blight", "A spreading rot of the land."),
    }
)


BEING_KINDS: MappingProxyType[BeingKind, KindSpec] = MappingProxyType(
    {
        BeingKind.PLANAR_NATIVE: KindSpec("Planar native", "A being born in another dimension."),
        BeingKind.DIMENSION_WALKER: KindSpec("Dimension walker", "A being that walks between dimensions."),
        BeingKind.RIFT_SPAWN: KindSpec("Rift spawn", "A being born where a rift opened."),
        BeingKind.HIGHER_DIMENSIONAL: KindSpec("Higher-dimensional entity", "A being with more directions than the prime has."),
        BeingKind.STAR_EATER: KindSpec("Star eater", "A being that feeds on the light of stars."),
        BeingKind.NEBULA_MIND: KindSpec("Nebula mind", "A mind spread through a cloud between the stars."),
        BeingKind.GALACTIC_LEVIATHAN: KindSpec("Galactic leviathan", "A being that swims between the stars of a galaxy."),
        BeingKind.VOID_SHEPHERD: KindSpec("Void shepherd", "A being that keeps watch over the dark between galaxies."),
        BeingKind.ECHO: KindSpec("Echo", "A double of a mortal from a mirror dimension."),
        BeingKind.TIME_WANDERER: KindSpec("Time wanderer", "A being loose in time."),
        BeingKind.COSMIC_TITAN: KindSpec("Cosmic titan", "A being as large as a star system."),
        BeingKind.VEIL_WARDEN: KindSpec("Veil warden", "A being that guards the boundaries between dimensions."),
        BeingKind.PLANE_SOVEREIGN: KindSpec("Plane sovereign", "A being that rules a whole dimension."),
        BeingKind.SWARM_INTELLIGENCE: KindSpec("Swarm intelligence", "One mind made of countless small bodies."),
        BeingKind.LIVING_CONSTELLATION: KindSpec("Living constellation", "A figure of stars that is alive."),
    }
)

NUCLEUS_LABELS: MappingProxyType[GalacticNucleus, str] = MappingProxyType(
    {
        GalacticNucleus.NONE: "No nucleus",
        GalacticNucleus.DORMANT: "Dormant nucleus",
        GalacticNucleus.ACTIVE: "Active nucleus",
        GalacticNucleus.QUASAR: "Quasar",
        GalacticNucleus.DEVOURED: "Devoured nucleus",
    }
)
GALAXY_AGE_LABELS: MappingProxyType[GalaxyAge, str] = MappingProxyType(
    {
        GalaxyAge.FORMING: "Forming",
        GalaxyAge.YOUNG: "Young",
        GalaxyAge.MATURE: "Mature",
        GalaxyAge.OLD: "Old",
        GalaxyAge.DYING: "Dying",
        GalaxyAge.DEAD: "Dead",
    }
)
GALAXY_AGE_ORDER: tuple[GalaxyAge, ...] = tuple(GalaxyAge)
STAR_AGE_LABELS: MappingProxyType[StarAge, str] = MappingProxyType(
    {
        StarAge.YOUNG: "Young",
        StarAge.MAIN: "Main life",
        StarAge.OLD: "Old",
        StarAge.DYING: "Dying",
        StarAge.DEAD: "Dead",
        StarAge.REBORN: "Reborn",
    }
)
WORLD_AGE_LABELS: MappingProxyType[WorldAge, str] = MappingProxyType(
    {WorldAge.YOUNG: "Young", WorldAge.MATURE: "Mature", WorldAge.OLD: "Old", WorldAge.DYING: "Dying"}
)
CAUSALITY_LABELS: MappingProxyType[Causality, str] = MappingProxyType(
    {Causality.STRICT: "Strict causality", Causality.LOOSE: "Loose causality", Causality.BROKEN: "Broken causality"}
)
ELEMENT_LABELS: MappingProxyType[DimensionElement, str] = MappingProxyType(
    {element: element.value.replace("_", " ").capitalize() for element in DimensionElement}
)
GALACTIC_EVENT_LABELS: MappingProxyType[GalacticEventKind, KindSpec] = MappingProxyType(
    {
        GalacticEventKind.CORE_OUTBURST: KindSpec("Core outburst", "The central black hole flares; the core and bulge are flooded with radiation."),
        GalacticEventKind.GAMMA_RAY_BURST: KindSpec("Gamma-ray burst", "A dying star sends out a beam that strips life from the worlds in its reach."),
        GalacticEventKind.STARBURST: KindSpec("Starburst", "The galaxy bears new stars far faster than usual."),
        GalacticEventKind.TIDAL_STRIPPING: KindSpec("Tidal stripping", "A passing pull tears stars into a stream."),
        GalacticEventKind.MERGER_BEGUN: KindSpec("Merger begun", "Two galaxies have begun to fall into each other."),
        GalacticEventKind.MERGER_COMPLETED: KindSpec("Merger completed", "One galaxy has swallowed another."),
        GalacticEventKind.HYPERVELOCITY_STAR: KindSpec("Hypervelocity star", "A star is flung out of the galaxy."),
        GalacticEventKind.NEBULA_COLLAPSE: KindSpec("Nebula collapse", "A cloud collapses and a new nursery is born."),
        GalacticEventKind.GALACTIC_DIMMING: KindSpec("Galactic dimming", "Every star of the galaxy loses some light."),
        GalacticEventKind.AWAKENING: KindSpec("Awakening", "A living galaxy stirs and its stars brighten."),
        GalacticEventKind.SHROUDING: KindSpec("Shrouding", "A veiled galaxy hides itself from those outside."),
        GalacticEventKind.SEVERING: KindSpec("Severing", "A shattered galaxy splits into two."),
    }
)
DIMENSIONAL_EVENT_LABELS: MappingProxyType[DimensionalEventKind, KindSpec] = MappingProxyType(
    {
        DimensionalEventKind.INCURSION: KindSpec("Incursion", "Beings of a dimension cross into a world."),
        DimensionalEventKind.CONVERGENCE: KindSpec("Convergence", "Two dimensions overlap: their veils open and their laws and beings cross."),
        DimensionalEventKind.VEIL_THINNING: KindSpec("Veil thinning", "A dimension's boundary grows thin."),
        DimensionalEventKind.PLANAR_ALIGNMENT: KindSpec("Planar alignment", "Every veil thins at once."),
        DimensionalEventKind.BLEED: KindSpec("Bleed", "A dimension's nature seeps into a world."),
        DimensionalEventKind.SCHISM: KindSpec("Schism", "A branch dimension splits off."),
        DimensionalEventKind.COLLAPSE: KindSpec("Collapse", "A pocket or bubble dimension falls in on itself."),
        DimensionalEventKind.ECHO: KindSpec("Echo", "A double of a mortal appears from a mirror dimension."),
    }
)
RIFT_STATE_LABELS: MappingProxyType[RiftState, str] = MappingProxyType(
    {RiftState.OPENING: "Opening", RiftState.OPEN: "Open", RiftState.CLOSING: "Closing", RiftState.SEALED: "Sealed", RiftState.COLLAPSED: "Collapsed"}
)
RIFT_CAUSE_LABELS: MappingProxyType[RiftCause, str] = MappingProxyType(
    {
        RiftCause.RITE_BACKLASH: "Rite backlash",
        RiftCause.LEAK_PEAK: "Leak peak",
        RiftCause.CONVERGENCE: "Convergence",
        RiftCause.GOD: "A god's act",
        RiftCause.BEING: "A cosmic being",
        RiftCause.PHENOMENON: "A phenomenon",
        RiftCause.CREATOR: "The Creator",
    }
)
SCOPE_LABELS: MappingProxyType[RouteScope, str] = MappingProxyType(
    {
        RouteScope.SYSTEM: "Within one system",
        RouteScope.STELLAR: "Between stars",
        RouteScope.GALACTIC: "To a near galaxy",
        RouteScope.INTERGALACTIC: "Between galaxies",
        RouteScope.INTERCLUSTER: "Between clusters",
        RouteScope.INTERDIMENSIONAL: "Between dimensions",
    }
)
SCOPE_ORDER: tuple[RouteScope, ...] = tuple(RouteScope)
BEING_SCALE_LABELS: MappingProxyType[BeingScale, str] = MappingProxyType(
    {
        BeingScale.WORLD: "World",
        BeingScale.SYSTEM: "Star system",
        BeingScale.GALAXY: "Galaxy",
        BeingScale.CLUSTER: "Cluster",
        BeingScale.DIMENSION: "Dimension",
    }
)
BEING_PHASE_LABELS: MappingProxyType[BeingPhase, str] = MappingProxyType(
    {
        BeingPhase.DORMANT: "Dormant",
        BeingPhase.ROAMING: "Roaming",
        BeingPhase.MANIFEST: "Manifest",
        BeingPhase.INCURSION: "In incursion",
        BeingPhase.BOUND: "Bound",
        BeingPhase.BANISHED: "Banished",
    }
)
BEING_AGENDA_LABELS: MappingProxyType[BeingAgenda, str] = MappingProxyType(
    {
        BeingAgenda.FEED: "Feed",
        BeingAgenda.EXPLORE: "Explore",
        BeingAgenda.CONQUER: "Conquer",
        BeingAgenda.GUARD: "Guard",
        BeingAgenda.TRADE: "Trade",
        BeingAgenda.FLEE: "Flee",
        BeingAgenda.SEEK_WORSHIP: "Seek worship",
        BeingAgenda.UNMAKE: "Unmake",
        BeingAgenda.MEND: "Mend",
    }
)
PHENOMENON_CAUSE_LABELS: MappingProxyType[PhenomenonCause, str] = MappingProxyType(
    {
        PhenomenonCause.RITE_BACKLASH: "Rite backlash",
        PhenomenonCause.GOD_DEATH: "A god's death",
        PhenomenonCause.LAW_CONFLICT: "Clashing natural laws",
        PhenomenonCause.SKY_EVENT: "A sky event",
        PhenomenonCause.LEAK_PEAK: "A leak peak",
        PhenomenonCause.BATTLEFIELD: "A great battlefield",
        PhenomenonCause.RIFT: "A rift",
        PhenomenonCause.DIVINE: "A divine act",
    }
)
OMEN_LABELS: MappingProxyType[OmenReading, str] = MappingProxyType(
    {OmenReading.GOOD: "Good omen", OmenReading.EVIL: "Evil omen", OmenReading.NEUTRAL: "No omen"}
)
APOCALYPSE_LABELS: MappingProxyType[ApocalypseVariant, KindSpec] = MappingProxyType(
    {
        ApocalypseVariant.RUIN: KindSpec("Ruin", "The leakiest world is shaken by disasters."),
        ApocalypseVariant.WORLD_WAR: KindSpec("World war", "The end becomes the Calling: a war of every people."),
        ApocalypseVariant.OUTER_DESCENT: KindSpec("Outer descent", "Outer beings descend on the leakiest world."),
        ApocalypseVariant.TWILIGHT_OF_GODS: KindSpec("Twilight of the gods", "The sons fade twice as fast."),
        ApocalypseVariant.DIMENSIONAL_COLLAPSE: KindSpec("Dimensional collapse", "Every veil gives way and the dimensions run together."),
        ApocalypseVariant.GALACTIC_DEATH: KindSpec("Galactic death", "The stars of the dimmest galaxy go dark."),
    }
)

BEING_SCALES: MappingProxyType[BeingKind, BeingScale] = MappingProxyType(
    {
        BeingKind.PLANAR_NATIVE: BeingScale.WORLD,
        BeingKind.DIMENSION_WALKER: BeingScale.DIMENSION,
        BeingKind.RIFT_SPAWN: BeingScale.WORLD,
        BeingKind.HIGHER_DIMENSIONAL: BeingScale.DIMENSION,
        BeingKind.STAR_EATER: BeingScale.GALAXY,
        BeingKind.NEBULA_MIND: BeingScale.GALAXY,
        BeingKind.GALACTIC_LEVIATHAN: BeingScale.GALAXY,
        BeingKind.VOID_SHEPHERD: BeingScale.CLUSTER,
        BeingKind.ECHO: BeingScale.WORLD,
        BeingKind.TIME_WANDERER: BeingScale.DIMENSION,
        BeingKind.COSMIC_TITAN: BeingScale.CLUSTER,
        BeingKind.VEIL_WARDEN: BeingScale.DIMENSION,
        BeingKind.PLANE_SOVEREIGN: BeingScale.DIMENSION,
        BeingKind.SWARM_INTELLIGENCE: BeingScale.GALAXY,
        BeingKind.LIVING_CONSTELLATION: BeingScale.GALAXY,
    }
)
BEING_AGENDAS: MappingProxyType[BeingKind, BeingAgenda] = MappingProxyType(
    {
        BeingKind.PLANAR_NATIVE: BeingAgenda.EXPLORE,
        BeingKind.DIMENSION_WALKER: BeingAgenda.EXPLORE,
        BeingKind.RIFT_SPAWN: BeingAgenda.CONQUER,
        BeingKind.HIGHER_DIMENSIONAL: BeingAgenda.EXPLORE,
        BeingKind.STAR_EATER: BeingAgenda.FEED,
        BeingKind.NEBULA_MIND: BeingAgenda.FEED,
        BeingKind.GALACTIC_LEVIATHAN: BeingAgenda.EXPLORE,
        BeingKind.VOID_SHEPHERD: BeingAgenda.GUARD,
        BeingKind.ECHO: BeingAgenda.SEEK_WORSHIP,
        BeingKind.TIME_WANDERER: BeingAgenda.EXPLORE,
        BeingKind.COSMIC_TITAN: BeingAgenda.CONQUER,
        BeingKind.VEIL_WARDEN: BeingAgenda.GUARD,
        BeingKind.PLANE_SOVEREIGN: BeingAgenda.CONQUER,
        BeingKind.SWARM_INTELLIGENCE: BeingAgenda.FEED,
        BeingKind.LIVING_CONSTELLATION: BeingAgenda.MEND,
    }
)
DIMENSION_LAWS: MappingProxyType[DimensionKind, tuple[NaturalLaw, ...]] = MappingProxyType(
    {
        DimensionKind.UNDERWORLD: (NaturalLaw.THE_DEAD_SPEAK,),
        DimensionKind.DREAM: (NaturalLaw.DREAMS_ARE_REAL,),
        DimensionKind.SHADOW: (NaturalLaw.ETERNAL_NIGHT,),
        DimensionKind.INFERNAL: (NaturalLaw.MAGIC_REQUIRES_BLOOD,),
        DimensionKind.CLOCKWORK: (NaturalLaw.OATHS_BIND,),
        DimensionKind.TIME_REVERSED: (NaturalLaw.SEASONS_REVERSED,),
        DimensionKind.HIGHER_DIMENSIONAL: (NaturalLaw.GRAVITY_SHIFT,),
        DimensionKind.FEY: (NaturalLaw.GIFT_FLOWERING, NaturalLaw.NO_IRON),
        DimensionKind.SPIRIT: (NaturalLaw.THE_DEAD_SPEAK,),
        DimensionKind.LIMBO: (NaturalLaw.GIFT_WITHERING,),
    }
)
DIMENSION_MINERALS: MappingProxyType[DimensionKind, MaterialKind] = MappingProxyType(
    {
        DimensionKind.FAR_REALM: MaterialKind.VOID_GLASS,
        DimensionKind.VOID_BETWEEN: MaterialKind.VOID_GLASS,
        DimensionKind.ABYSSAL: MaterialKind.VOID_GLASS,
        DimensionKind.CELESTIAL: MaterialKind.GOLD,
        DimensionKind.ELEMENTAL: MaterialKind.CRYSTAL,
        DimensionKind.ASTRAL: MaterialKind.CRYSTAL,
        DimensionKind.FEY: MaterialKind.AMBER,
    }
)
STRUCTURE_MINERALS: MappingProxyType[GalacticStructureKind, MaterialKind] = MappingProxyType(
    {
        GalacticStructureKind.SUPERNOVA_REMNANT: MaterialKind.STAR_METAL,
        GalacticStructureKind.STAR_GRAVEYARD: MaterialKind.STAR_METAL,
        GalacticStructureKind.GODS_FORGE: MaterialKind.STAR_METAL,
        GalacticStructureKind.RIFT_SCAR: MaterialKind.VOID_GLASS,
        GalacticStructureKind.CORE: MaterialKind.GOLD,
        GalacticStructureKind.PLANETARY_NEBULA: MaterialKind.GEMS,
    }
)
PHENOMENON_WEATHER: MappingProxyType[PhenomenonKind, WeatherKind] = MappingProxyType(
    {
        PhenomenonKind.ETERNAL_STORM: WeatherKind.STORM,
        PhenomenonKind.LIVING_FOG: WeatherKind.FOG,
        PhenomenonKind.AURORA_PERMANENT: WeatherKind.AURORA,
        PhenomenonKind.LEY_NEXUS_FLARE: WeatherKind.MAGIC_STORM,
        PhenomenonKind.LEAK_WOUND: WeatherKind.VOID_RAIN,
        PhenomenonKind.DEAD_ZONE: WeatherKind.DROUGHT_WIND,
    }
)
PHENOMENON_REAGENTS: MappingProxyType[PhenomenonKind, MaterialKind] = MappingProxyType(
    {PhenomenonKind.CRYSTAL_BLOOM: MaterialKind.CRYSTAL, PhenomenonKind.GOD_CORPSE_AURA: MaterialKind.GEMS, PhenomenonKind.LEAK_WOUND: MaterialKind.VOID_GLASS}
)
RIFT_PHENOMENA = frozenset({PhenomenonKind.LEAK_WOUND, PhenomenonKind.MIRROR_LAKE})
MIRROR_DIMENSIONS = frozenset({DimensionKind.MIRROR, DimensionKind.PARALLEL, DimensionKind.QUANTUM_BRANCH})
FRAGILE_DIMENSIONS = frozenset({DimensionKind.POCKET, DimensionKind.BUBBLE_UNIVERSE, DimensionKind.COMPACTIFIED})
BARRED_GALAXIES = frozenset({GalaxyType.BARRED_SPIRAL, GalaxyType.FORGED})
SPIRAL_GALAXIES = frozenset(
    {
        GalaxyType.SPIRAL,
        GalaxyType.BARRED_SPIRAL,
        GalaxyType.GRAND_DESIGN_SPIRAL,
        GalaxyType.FLOCCULENT_SPIRAL,
        GalaxyType.ACTIVE,
        GalaxyType.LOW_SURFACE_BRIGHTNESS,
        GalaxyType.LIVING,
        GalaxyType.FORGED,
        GalaxyType.DREAMING,
        GalaxyType.MIRROR,
        GalaxyType.CROWNED,
        GalaxyType.VEILED,
        GalaxyType.EMBER,
    }
)
NUCLEUS_OF: MappingProxyType[GalaxyType, GalacticNucleus] = MappingProxyType(
    {
        GalaxyType.ACTIVE: GalacticNucleus.ACTIVE,
        GalaxyType.QUASAR_HOST: GalacticNucleus.QUASAR,
        GalaxyType.DWARF_SPHEROIDAL: GalacticNucleus.NONE,
        GalaxyType.DWARF_IRREGULAR: GalacticNucleus.NONE,
        GalaxyType.ULTRA_DIFFUSE: GalacticNucleus.NONE,
        GalaxyType.HOLLOW: GalacticNucleus.DEVOURED,
    }
)
