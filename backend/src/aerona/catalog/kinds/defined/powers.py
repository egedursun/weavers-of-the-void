from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.powers import PowerDeviceEffect, PowerVisibility, RestrictionKind, SourceRelation, SourceRenewal

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

POWER_VISIBILITY = total(
    PowerVisibility,
    {
        PowerVisibility.OVERT: Defined(
            "Plain to see",
            checked_by=(
                "engine.powers.phase.live_with",
                "engine.powers.society.go_quiet",
                "engine.powers.society.keep_apart",
                "engine.powers.systems.unsettle",
                "engine.powers.use.use",
            ),
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

RESTRICTION_KIND = total(
    RestrictionKind,
    {
        RestrictionKind.ONLY_IN_PLACE: Defined("Only in one place", checked_by=(), used_by=("engine.powers.use.out_of_place",)),
        RestrictionKind.ONLY_AT_TIME: Defined("Only at one time", checked_by=(), used_by=("engine.powers.use.out_of_time",)),
        RestrictionKind.ONLY_AGAINST: Defined("Only against one foe", checked_by=(), used_by=("engine.powers.use.wrong_target",)),
        RestrictionKind.SPOKEN_VOW: Defined(
            "Bound to a spoken vow", checked_by=(), used_by=("catalog.life.powers.BROKEN_VOWS_RESTRICTION_KINDS", "engine.powers.use.kept")
        ),
        RestrictionKind.PRICE_EACH_USE: Defined("A price for each use", checked_by=(), used_by=("engine.powers.use.unpaid",)),
        RestrictionKind.NEVER_ON_SELF: Defined("Never on oneself", checked_by=(), used_by=("engine.powers.use.on_self",)),
        RestrictionKind.FORBIDDEN_ACT: Defined(
            "Lost by a forbidden act", checked_by=(), used_by=("catalog.life.powers.BROKEN_VOWS_RESTRICTION_KINDS", "engine.powers.use.kept")
        ),
        RestrictionKind.MUST_BE_SEEN: Defined("Must be seen", checked_by=(), used_by=("engine.powers.use.unseen",)),
        RestrictionKind.MUST_BE_UNSEEN: Defined("Must be unseen", checked_by=(), used_by=("engine.powers.use.seen",)),
        RestrictionKind.MUST_TOUCH: Defined("Must touch", checked_by=(), used_by=("engine.powers.use.out_of_reach",)),
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
        SourceRenewal.REST: Defined("Rest", checked_by=("catalog.life.powers.RENEWAL_KINDS",), used_by=("engine.powers.backfill.BUILT_IN",)),
        SourceRenewal.TIME: Defined(
            "Time",
            checked_by=("catalog.life.powers.RENEWAL_KINDS",),
            used_by=(
                "db.tables.powers.PowerSourceRow",
                "engine.powers.backfill.BUILT_IN",
                "services.player.powers.SourceCreate",
                "tools.son.powers.ShapeSourceInput",
            ),
        ),
        SourceRenewal.SEASON: Defined("The seasons", checked_by=("catalog.life.powers.RENEWAL_KINDS",), used_by=()),
        SourceRenewal.SKY_CYCLE: Defined("The sky's cycle", checked_by=("catalog.life.powers.RENEWAL_KINDS",), used_by=()),
        SourceRenewal.WORSHIP: Defined("Worship", checked_by=("catalog.life.powers.RENEWAL_KINDS",), used_by=("engine.powers.backfill.BUILT_IN",)),
        SourceRenewal.FEEDING: Defined("Feeding", checked_by=("catalog.life.powers.RENEWAL_KINDS",), used_by=()),
        SourceRenewal.TAKING: Defined("Taking from others", checked_by=("catalog.life.powers.RENEWAL_KINDS",), used_by=("engine.powers.backfill.BUILT_IN",)),
        SourceRenewal.VOWS_KEPT: Defined("Vows kept", checked_by=("catalog.life.powers.RENEWAL_KINDS",), used_by=()),
        SourceRenewal.RETURN_TO_PLACE: Defined("Return to the place", checked_by=("catalog.life.powers.RENEWAL_KINDS",), used_by=()),
        SourceRenewal.NONE: Defined("Never; it runs out", checked_by=(), used_by=("engine.powers.backfill.BUILT_IN",)),
    },
)
