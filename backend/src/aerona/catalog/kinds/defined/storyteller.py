from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.storyteller import PaletteSubsystem, RecoveryKind, SpontaneousKind

PALETTE_SUBSYSTEM = total(
    PaletteSubsystem,
    {
        PaletteSubsystem.WAR: Defined("War", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE", "engine.storyteller.palette.SPEC_PALETTE")),
        PaletteSubsystem.FAITH: Defined("Faith", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE", "engine.storyteller.palette.SPEC_PALETTE")),
        PaletteSubsystem.ECONOMY: Defined(
            "Economy", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE", "engine.storyteller.palette.SPEC_PALETTE")
        ),
        PaletteSubsystem.ECOLOGY: Defined(
            "Ecology", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE", "engine.storyteller.palette.SPEC_PALETTE")
        ),
        PaletteSubsystem.DISEASE: Defined(
            "Disease", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE", "engine.storyteller.palette.SPEC_PALETTE")
        ),
        PaletteSubsystem.CLIMATE: Defined(
            "Climate", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE", "engine.storyteller.palette.SPEC_PALETTE")
        ),
        PaletteSubsystem.COSMOS: Defined(
            "Cosmos", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE", "engine.storyteller.palette.SPEC_PALETTE")
        ),
        PaletteSubsystem.MADE_MINDS: Defined("Made minds", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
        PaletteSubsystem.NETWORKS: Defined("Networks", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
        PaletteSubsystem.REPLICATORS: Defined("Replicators", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
        PaletteSubsystem.POWERS: Defined("Powers", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
        PaletteSubsystem.SOURCES: Defined("Sources of power", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
        PaletteSubsystem.CONCEALMENT: Defined("Concealment", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
        PaletteSubsystem.LIVING_CRAFT: Defined("Living craft", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
        PaletteSubsystem.GODS: Defined("Gods", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
        PaletteSubsystem.OUTER_BEINGS: Defined("Beings from outside", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
        PaletteSubsystem.HOUSEHOLDS: Defined(
            "Households", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE", "engine.storyteller.palette.SPEC_PALETTE")
        ),
        PaletteSubsystem.MIGRATION: Defined("Migration", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
        PaletteSubsystem.IDEOLOGY: Defined("Ideology", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
        PaletteSubsystem.ART: Defined("Art", checked_by=(), used_by=("engine.storyteller.palette.BASE_PALETTE",)),
    },
)

RECOVERY_KIND = total(
    RecoveryKind,
    {
        RecoveryKind.HARVEST: Defined("Harvest", checked_by=(), used_by=("engine.phases.gatherings.recover", "engine.storyteller.palette.BASE_PALETTE")),
        RecoveryKind.PEACE_ENVOY: Defined(
            "Peace envoy", checked_by=(), used_by=("engine.phases.diplomacy._neighbour_pair", "engine.storyteller.palette.BASE_PALETTE")
        ),
        RecoveryKind.HEALER_BIRTH: Defined("Healer birth", checked_by=(), used_by=("engine.phases.births.notables", "engine.storyteller.palette.BASE_PALETTE")),
    },
)

SPONTANEOUS_KIND = total(
    SpontaneousKind,
    {
        SpontaneousKind.BEAST_AWAKENING: Defined(
            "Beasts awakened", checked_by=(), used_by=("engine.ecology.monsters.emerge_from_deep", "engine.storyteller.palette.BASE_PALETTE")
        ),
        SpontaneousKind.RAID: Defined("Raids", checked_by=(), used_by=("engine.phases.vendettas.lesser_act", "engine.storyteller.palette.BASE_PALETTE")),
        SpontaneousKind.COMET: Defined("Comets", checked_by=(), used_by=("engine.phases.sky.spontaneous_sky_event", "engine.storyteller.palette.BASE_PALETTE")),
        SpontaneousKind.PLAGUE: Defined(
            "Plagues", checked_by=(), used_by=("engine.phases.disasters._region_disasters", "engine.storyteller.palette.BASE_PALETTE")
        ),
        SpontaneousKind.CLAIMANT: Defined("Claimants", checked_by=(), used_by=("engine.polity.offices.regency", "engine.storyteller.palette.BASE_PALETTE")),
    },
)
