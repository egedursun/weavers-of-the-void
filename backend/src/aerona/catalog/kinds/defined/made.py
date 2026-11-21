from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.made import AugmentMake, Authenticity, RelicUse, ReplicatorOutput

AUGMENT_MAKE = total(
    AugmentMake,
    {
        AugmentMake.MADE: Defined(
            "Made",
            checked_by=("engine.augments.install", "engine.made.backfill.prostheses"),
            used_by=(
                "db.tables.made.AugmentRow",
                "engine.made.backfill.prostheses",
                "services.player.minds.AugmentDraft",
                "tools.mortal.minds.InstallAugmentInput",
            ),
        ),
        AugmentMake.RITE_BOUND: Defined("Rite-bound", checked_by=("engine.augments.install",), used_by=()),
        AugmentMake.GROWN: Defined("Grown", checked_by=(), used_by=("engine.living.grown.grow_organ",)),
    },
)

AUTHENTICITY = total(
    Authenticity,
    {
        Authenticity.GENUINE: Defined(
            "Genuine",
            checked_by=("engine.made.trust.tend",),
            used_by=(
                "db.tables.collective.AccountRow",
                "engine.collective.accounts.record",
                "engine.made.trust.find_forgeries",
                "engine.reckoning.measures.testify",
                "tools.mortal.minds.publish",
            ),
        ),
        Authenticity.ALTERED: Defined(
            "Altered",
            checked_by=(),
            used_by=("engine.leader_cults.cults.chronicle", "engine.made.intrusion.land", "engine.made.trust.FALSE", "engine.powers.effects.alter_record"),
        ),
        Authenticity.FORGED: Defined(
            "Forged",
            checked_by=(),
            used_by=("engine.made.intrusion.land", "engine.made.trust.FALSE", "services.player.minds.RecordMark", "tools.mortal.minds.forge_record"),
        ),
        Authenticity.GENERATED: Defined("Generated", checked_by=(), used_by=("engine.made.trust.FALSE",)),
        Authenticity.UNKNOWN: Defined("Unknown", checked_by=("engine.made.trust.find_forgeries",), used_by=("engine.collective.accounts.record",)),
    },
)

RELIC_USE = total(
    RelicUse,
    {
        RelicUse.AS_MADE: Defined(
            "Used as made",
            checked_by=("engine.made.relics.keep_relic",),
            used_by=("db.tables.made.MadeRelicRow", "engine.made.control.mark_relic", "engine.made.relics.mark_collapse"),
        ),
        RelicUse.REPURPOSED: Defined("Studied and repurposed", checked_by=("engine.made.relics.keep_relic",), used_by=("tools.mortal.minds.study_relic",)),
        RelicUse.REVERED: Defined("Revered", checked_by=(), used_by=("engine.made.relics.STANCE_USE",)),
        RelicUse.DISPLAYED: Defined("Displayed", checked_by=(), used_by=("engine.made.relics.STANCE_USE",)),
        RelicUse.FEARED: Defined("Feared", checked_by=(), used_by=("engine.made.relics.STANCE_USE",)),
        RelicUse.IGNORED: Defined("Ignored", checked_by=("engine.made.relics.keep_relic",), used_by=("engine.made.relics.keep_relic",)),
    },
)

REPLICATOR_OUTPUT = total(
    ReplicatorOutput,
    {
        ReplicatorOutput.COPIES: Defined("Copies of itself", checked_by=(), used_by=("db.tables.made.ReplicatorLineRow", "engine.made.abundance.MAKERS")),
        ReplicatorOutput.GOODS: Defined(
            "Goods",
            checked_by=("engine.made.replicators.OUTPUT_GOODS",),
            used_by=("engine.made.abundance.MAKERS", "services.player.minds.LineDraft", "tools.mortal.minds.BuildReplicatorInput"),
        ),
        ReplicatorOutput.STRUCTURES: Defined("Structures", checked_by=("engine.made.replicators.yield_to",), used_by=("engine.made.abundance.MAKERS",)),
        ReplicatorOutput.REPAIR: Defined("Repair", checked_by=("engine.made.replicators.yield_to",), used_by=()),
        ReplicatorOutput.MEDICINE: Defined("Medicine", checked_by=("engine.made.replicators.OUTPUT_GOODS",), used_by=()),
        ReplicatorOutput.TERRAFORMING: Defined(
            "Reshaping land",
            checked_by=("engine.made.backfill.terraformers", "engine.made.replicators.yield_to"),
            used_by=("engine.made.backfill.terraformers",),
        ),
        ReplicatorOutput.DISASSEMBLY: Defined(
            "Disassembly", checked_by=("engine.made.replicators.yield_to", "engine.minds.war_methods.replicator_weapons"), used_by=()
        ),
    },
)
