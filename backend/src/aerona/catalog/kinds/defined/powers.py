from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.powers import PowerDeviceEffect, PowerOrigin, PowerVisibility, SourceLocus, SourceRelation, SourceRenewal

POWER_DEVICE_EFFECT = total(
    PowerDeviceEffect,
    {
        PowerDeviceEffect.AMPLIFY: Defined("Strengthens powers", checked_by=(), used_by=("engine.powers.use.device_factor",)),
        PowerDeviceEffect.DAMPEN: Defined("Dampens powers", checked_by=(), used_by=("engine.powers.use.dampened", "engine.powers.use.dampeners")),
        PowerDeviceEffect.AWAKEN: Defined("Wakes latent powers", checked_by=("engine.powers.phase.awaken",), used_by=()),
        PowerDeviceEffect.STABILISE: Defined("Steadies control", checked_by=(), used_by=("engine.powers.use.device_factor",)),
        PowerDeviceEffect.EXTEND_RANGE: Defined("Extends reach", checked_by=("engine.powers.use.distance",), used_by=()),
        PowerDeviceEffect.SHIELD: Defined("Shields from powers", checked_by=(), used_by=("engine.powers.use.dampened",)),
        PowerDeviceEffect.DETECT: Defined("Finds the gifted", checked_by=("engine.powers.society.keep_registries",), used_by=()),
    },
)

POWER_ORIGIN = total(
    PowerOrigin,
    {
        PowerOrigin.BORN: Defined(
            "Born with it",
            checked_by=(),
            used_by=(
                "db.tables.powers.PowerRow",
                "engine.powers.backfill.gifted",
                "engine.powers.kinds.GIFTED_ORIGINS",
                "engine.powers.kinds.bloodline",
                "engine.powers.society.BORN_ORIGINS",
                "services.player.powers.PowerCreate",
            ),
        ),
        PowerOrigin.AWAKENED: Defined("Woken by a trigger", checked_by=(), used_by=("engine.powers.kinds.GIFTED_ORIGINS",)),
        PowerOrigin.EXPOSURE: Defined(
            "By exposure", checked_by=(), used_by=("engine.powers.kinds.GIFTED_ORIGINS", "engine.powers.phase.exposed", "engine.powers.society.heirs")
        ),
        PowerOrigin.GRANTED: Defined(
            "Granted", checked_by=(), used_by=("engine.powers.control.grant_power", "engine.powers.kinds.granted", "tools.son.powers.grant_power")
        ),
        PowerOrigin.BONDED: Defined("By a bond", checked_by=(), used_by=("engine.divine.outer_agency.strike_bargain", "engine.powers.kinds.bonded")),
        PowerOrigin.DISCIPLINE: Defined("By discipline", checked_by=("engine.powers.phase.train",), used_by=("engine.powers.kinds.trained",)),
        PowerOrigin.MADE: Defined("By a made part", checked_by=("engine.powers.phase.fade", "engine.powers.society.at_death"), used_by=()),
        PowerOrigin.GROWN: Defined(
            "By a grown part", checked_by=("engine.powers.phase.fade", "engine.powers.society.at_death"), used_by=("engine.living.control.born_gift",)
        ),
        PowerOrigin.BLOODLINE: Defined(
            "By its line",
            checked_by=("engine.powers.society.heirs",),
            used_by=(
                "engine.powers.kinds.GIFTED_ORIGINS",
                "engine.powers.kinds.bloodline",
                "engine.powers.society.BORN_ORIGINS",
                "engine.powers.society.heirs",
            ),
        ),
        PowerOrigin.HELD: Defined("While holding a thing", checked_by=("engine.powers.phase.fade", "engine.powers.society.at_death"), used_by=()),
    },
)

POWER_VISIBILITY = total(
    PowerVisibility,
    {
        PowerVisibility.OVERT: Defined(
            "Plain to see",
            checked_by=("engine.powers.phase.live_with", "engine.powers.society.go_quiet", "engine.powers.society.keep_apart", "engine.powers.use.use"),
            used_by=("engine.powers.backfill.BUILT_IN",),
        ),
        PowerVisibility.SUBTLE: Defined(
            "Subtle",
            checked_by=(),
            used_by=(
                "db.tables.powers.MagicSystemRow",
                "db.tables.powers.PowerRow",
                "db.tables.powers.PowerSourceRow",
                "engine.living.control.born_gift",
                "engine.powers.backfill.BUILT_IN",
                "engine.powers.backfill.gifted",
                "engine.powers.backfill.systems",
                "engine.powers.phase.exposed",
                "engine.powers.society.go_quiet",
                "services.player.powers.PowerCreate",
                "services.player.powers.SourceCreate",
                "tools.son.powers.ShapeSourceInput",
                "tools.son.powers.grant_power",
            ),
        ),
        PowerVisibility.HIDDEN: Defined("Hidden", checked_by=("engine.powers.use.use",), used_by=("engine.powers.backfill.BUILT_IN",)),
    },
)

SOURCE_LOCUS = total(
    SourceLocus,
    {
        SourceLocus.SELF: Defined("The self", checked_by=(), used_by=("engine.powers.backfill.BUILT_IN",)),
        SourceLocus.OTHERS: Defined("Other beings", checked_by=(), used_by=("engine.powers.backfill.BUILT_IN",)),
        SourceLocus.PLACE: Defined(
            "The place", checked_by=(), used_by=("engine.powers.backfill.BUILT_IN", "engine.powers.sources.LAND_LOCI", "services.player.powers.SourceCreate")
        ),
        SourceLocus.SKY: Defined("The sky and its cycles", checked_by=("engine.cosmos.omens.body_returns",), used_by=("engine.powers.sources.LAND_LOCI",)),
        SourceLocus.SURROUNDINGS: Defined("The surroundings", checked_by=(), used_by=("engine.powers.sources.LAND_LOCI",)),
        SourceLocus.MADE_THINGS: Defined("Made things", checked_by=("engine.powers.kinds.locus_factor",), used_by=()),
        SourceLocus.PATRON: Defined("A patron", checked_by=(), used_by=("engine.powers.backfill.BUILT_IN",)),
        SourceLocus.BOND: Defined("An oath or pact", checked_by=("engine.powers.kinds.locus_factor",), used_by=()),
        SourceLocus.STORY: Defined("Belief, renown or story", checked_by=("engine.powers.kinds.locus_factor",), used_by=()),
        SourceLocus.VOID: Defined("The void", checked_by=(), used_by=("engine.powers.backfill.BUILT_IN",)),
        SourceLocus.SUBSTANCE: Defined("A consumed substance", checked_by=(), used_by=("engine.powers.backfill.BUILT_IN",)),
        SourceLocus.LIFE: Defined("Life nearby", checked_by=(), used_by=("engine.powers.sources.LAND_LOCI",)),
        SourceLocus.DEATH: Defined("The dead nearby", checked_by=(), used_by=("engine.powers.sources.LAND_LOCI",)),
        SourceLocus.DREAM: Defined("Dreams", checked_by=("engine.powers.kinds.locus_factor",), used_by=()),
        SourceLocus.EMOTION: Defined("Feeling", checked_by=("engine.powers.kinds.locus_factor",), used_by=()),
    },
)

SOURCE_RELATION = total(
    SourceRelation,
    {
        SourceRelation.SUPPRESSES: Defined("Suppresses", checked_by=("engine.powers.sources.interaction_factor",), used_by=()),
        SourceRelation.AMPLIFIES: Defined("Amplifies", checked_by=("engine.powers.sources.interaction_factor",), used_by=()),
        SourceRelation.CONVERTS_INTO: Defined("Turns into", checked_by=("engine.powers.sources.interaction_factor",), used_by=()),
        SourceRelation.CONFLICTS: Defined("Conflicts with", checked_by=("engine.powers.sources.interaction_factor",), used_by=()),
    },
)

SOURCE_RENEWAL = total(
    SourceRenewal,
    {
        SourceRenewal.REST: Defined("Rest", checked_by=("engine.powers.sources.RENEWAL_KINDS",), used_by=("engine.powers.backfill.BUILT_IN",)),
        SourceRenewal.TIME: Defined(
            "Time",
            checked_by=("engine.powers.sources.RENEWAL_KINDS",),
            used_by=(
                "db.tables.powers.PowerSourceRow",
                "engine.powers.backfill.BUILT_IN",
                "services.player.powers.SourceCreate",
                "tools.son.powers.ShapeSourceInput",
            ),
        ),
        SourceRenewal.SEASON: Defined("The seasons", checked_by=("engine.powers.sources.RENEWAL_KINDS",), used_by=()),
        SourceRenewal.SKY_CYCLE: Defined("The sky's cycle", checked_by=("engine.powers.sources.RENEWAL_KINDS",), used_by=()),
        SourceRenewal.WORSHIP: Defined("Worship", checked_by=("engine.powers.sources.RENEWAL_KINDS",), used_by=("engine.powers.backfill.BUILT_IN",)),
        SourceRenewal.FEEDING: Defined("Feeding", checked_by=("engine.powers.sources.RENEWAL_KINDS",), used_by=()),
        SourceRenewal.TAKING: Defined("Taking from others", checked_by=("engine.powers.sources.RENEWAL_KINDS",), used_by=("engine.powers.backfill.BUILT_IN",)),
        SourceRenewal.VOWS_KEPT: Defined("Vows kept", checked_by=("engine.powers.sources.RENEWAL_KINDS",), used_by=()),
        SourceRenewal.RETURN_TO_PLACE: Defined("Return to the place", checked_by=("engine.powers.sources.RENEWAL_KINDS",), used_by=()),
        SourceRenewal.NONE: Defined("Never; it runs out", checked_by=(), used_by=("engine.powers.backfill.BUILT_IN",)),
    },
)
