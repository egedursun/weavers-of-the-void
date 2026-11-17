from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.world import GenesisTemplate, SonDistribution, StarType

GENESIS_TEMPLATE = total(
    GenesisTemplate,
    {
        GenesisTemplate.DARK_FANTASY: Defined("Dark fantasy", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.MYTHIC_AGE: Defined("Mythic age", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.COSMIC_HORROR: Defined("Cosmic horror", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.FAIRY_TALE: Defined("Fairy tale", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.STAR_MYTH: Defined("Star myth", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.DESERT_WORLD: Defined("Desert world", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.PRIMORDIAL_DAWN: Defined("Primordial dawn", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.COURT_INTRIGUE: Defined("Court intrigue", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.DROWNED_WORLD: Defined("Drowned world", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.LONG_WINTER: Defined("Long winter", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.AFTER_THE_FALL: Defined("After the fall", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.SKY_ISLANDS: Defined("Sky islands", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.AGE_OF_ENGINES: Defined("Age of engines", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.MANY_SUNS: Defined("Many suns", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.LAYERED_REALMS: Defined("Layered realms", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.LIVING_WORLD: Defined("Living world", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.DREAMING_WORLD: Defined("Dreaming world", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.GENERATION_SHIP: Defined("Generation ship", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.WITHOUT_MAGIC: Defined("Without magic", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.ELECTRIC_AGE: Defined("Electric age", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.INFORMATION_AGE: Defined("Information age", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.ADVANCED_AGE: Defined("Advanced age", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.MADE_MINDS: Defined("Made minds", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.AFTER_ABUNDANCE: Defined("After abundance", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.GUNPOWDER_AGE: Defined("Gunpowder age", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.INTERSTELLAR_AGE: Defined("Interstellar age", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
        GenesisTemplate.BEYOND_AGE: Defined("Beyond age", checked_by=(), used_by=("catalog.genesis.TEMPLATES",)),
    },
)

SON_DISTRIBUTION = total(
    SonDistribution,
    {
        SonDistribution.AUTO: Defined(
            "Auto", checked_by=("epoch.phases.distribution.distribute_sons", "tools.son.availability.world_state"), used_by=("db.tables.cosmos.CosmosRow",)
        ),
        SonDistribution.MANUAL: Defined("Manual", checked_by=("services.player.assignments.auto_distribute",), used_by=()),
    },
)

STAR_TYPE = total(
    StarType,
    {
        StarType.YELLOW_DWARF: Defined(
            "Yellow dwarf",
            checked_by=(),
            used_by=(
                "catalog.stars.STAR_TYPES",
                "engine.cosmos.birth._new_star",
                "engine.cosmos.galaxies.BIRTH_TYPES",
                "engine.cosmos.star_types.STAR_TYPE_MECHANICS",
                "services.player.cosmic.HangStar",
                "tools.son.cosmos.hang",
            ),
        ),
        StarType.RED_GIANT: Defined(
            "Red giant",
            checked_by=(),
            used_by=(
                "catalog.stars.STAR_TYPES",
                "engine.cosmos.star_types.STAR_TYPE_MECHANICS",
                "engine.cosmos.stellar.GIANTS",
                "engine.cosmos.stellar.giant_for",
                "engine.cosmos.world_ends.GIANTS",
            ),
        ),
        StarType.BLUE_GIANT: Defined("Blue giant", checked_by=(), used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS")),
        StarType.BINARY: Defined("Binary", checked_by=(), used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS")),
        StarType.WHITE_DWARF: Defined(
            "White dwarf",
            checked_by=(),
            used_by=(
                "catalog.stars.STAR_TYPES",
                "engine.cosmos.star_types.STAR_TYPE_MECHANICS",
                "engine.cosmos.stellar.REMNANTS",
                "engine.cosmos.stellar.remnant_for",
            ),
        ),
        StarType.DEAD_STAR: Defined(
            "Dead star",
            checked_by=(),
            used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS", "engine.cosmos.stars.extinguish_star"),
        ),
        StarType.BLACK_SUN: Defined(
            "Black sun",
            checked_by=("engine.cosmos.star_types.rekindle_cost",),
            used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS", "engine.cosmos.stars.black_sun"),
        ),
        StarType.BROKEN_STAR: Defined(
            "Broken star",
            checked_by=("engine.cosmos.star_types.rekindle_cost",),
            used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS"),
        ),
        StarType.PULSAR: Defined(
            "Pulsar", checked_by=(), used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS", "engine.cosmos.stellar.REMNANTS")
        ),
        StarType.STAR_REMNANT: Defined(
            "Star remnant",
            checked_by=("engine.cosmos.star_types.rekindle_cost",),
            used_by=("catalog.stars.STAR_TYPES", "catalog.stars.StarTypeSpec", "engine.cosmos.star_types.STAR_TYPE_MECHANICS"),
        ),
        StarType.REBORN_STAR: Defined(
            "Reborn star",
            checked_by=(),
            used_by=(
                "catalog.stars.STAR_TYPES",
                "engine.cosmos.star_types.STAR_TYPE_MECHANICS",
                "engine.cosmos.stars.rekindle_star",
                "engine.gods.metrics._reborn",
            ),
        ),
        StarType.BLUE_STAR: Defined(
            "Blue star",
            checked_by=(),
            used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.galaxies.BIRTH_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS"),
        ),
        StarType.BLUE_WHITE_STAR: Defined(
            "Blue white star",
            checked_by=(),
            used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.galaxies.BIRTH_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS"),
        ),
        StarType.WHITE_STAR: Defined(
            "White star",
            checked_by=(),
            used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.galaxies.BIRTH_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS"),
        ),
        StarType.YELLOW_WHITE_STAR: Defined(
            "Yellow white star", checked_by=(), used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS")
        ),
        StarType.ORANGE_DWARF: Defined(
            "Orange dwarf",
            checked_by=(),
            used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.galaxies.BIRTH_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS"),
        ),
        StarType.RED_DWARF: Defined(
            "Red dwarf",
            checked_by=(),
            used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.galaxies.BIRTH_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS"),
        ),
        StarType.BROWN_DWARF: Defined(
            "Brown dwarf",
            checked_by=(),
            used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.galaxies.BIRTH_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS"),
        ),
        StarType.YELLOW_GIANT: Defined(
            "Yellow giant",
            checked_by=(),
            used_by=(
                "catalog.stars.STAR_TYPES",
                "engine.cosmos.star_types.STAR_TYPE_MECHANICS",
                "engine.cosmos.stellar.GIANTS",
                "engine.cosmos.world_ends.GIANTS",
            ),
        ),
        StarType.RED_SUPERGIANT: Defined(
            "Red supergiant",
            checked_by=(),
            used_by=(
                "catalog.stars.STAR_TYPES",
                "engine.cosmos.star_types.STAR_TYPE_MECHANICS",
                "engine.cosmos.stellar.GIANTS",
                "engine.cosmos.stellar.giant_for",
                "engine.cosmos.world_ends.GIANTS",
            ),
        ),
        StarType.BLUE_SUPERGIANT: Defined(
            "Blue supergiant",
            checked_by=(),
            used_by=(
                "catalog.stars.STAR_TYPES",
                "engine.cosmos.star_types.STAR_TYPE_MECHANICS",
                "engine.cosmos.stellar.GIANTS",
                "engine.cosmos.world_ends.GIANTS",
            ),
        ),
        StarType.HYPERGIANT: Defined(
            "Hypergiant",
            checked_by=(),
            used_by=(
                "catalog.stars.STAR_TYPES",
                "engine.cosmos.star_types.STAR_TYPE_MECHANICS",
                "engine.cosmos.stellar.GIANTS",
                "engine.cosmos.world_ends.GIANTS",
            ),
        ),
        StarType.WOLF_RAYET: Defined("Wolf rayet", checked_by=(), used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS")),
        StarType.PROTOSTAR: Defined(
            "Protostar",
            checked_by=(),
            used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.galaxies.BIRTH_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS"),
        ),
        StarType.CARBON_STAR: Defined("Carbon star", checked_by=(), used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS")),
        StarType.NEUTRON_STAR: Defined(
            "Neutron star",
            checked_by=(),
            used_by=(
                "catalog.stars.STAR_TYPES",
                "engine.cosmos.star_types.STAR_TYPE_MECHANICS",
                "engine.cosmos.stellar.REMNANTS",
                "engine.cosmos.stellar.remnant_for",
            ),
        ),
        StarType.MAGNETAR: Defined(
            "Magnetar", checked_by=(), used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS", "engine.cosmos.stellar.REMNANTS")
        ),
        StarType.BLACK_HOLE: Defined(
            "Black hole",
            checked_by=(
                "engine.cosmos.features.devour",
                "engine.cosmos.features.ensure_wells",
                "engine.cosmos.features.slingshot",
                "engine.cosmos.star_types.rekindle_cost",
            ),
            used_by=(
                "catalog.stars.STAR_TYPES",
                "engine.cosmos.star_types.STAR_TYPE_MECHANICS",
                "engine.cosmos.stellar.REMNANTS",
                "engine.cosmos.stellar.remnant_for",
            ),
        ),
        StarType.VARIABLE_STAR: Defined("Variable star", checked_by=(), used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS")),
        StarType.TRINARY: Defined("Trinary", checked_by=(), used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS")),
        StarType.CHAINED_STAR: Defined("Chained star", checked_by=(), used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS")),
        StarType.WATCHING_STAR: Defined("Watching star", checked_by=(), used_by=("catalog.stars.STAR_TYPES", "engine.cosmos.star_types.STAR_TYPE_MECHANICS")),
    },
)
