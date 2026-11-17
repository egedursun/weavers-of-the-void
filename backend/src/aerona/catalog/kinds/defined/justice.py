from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.justice import Deposition

DEPOSITION = total(
    Deposition,
    {
        Deposition.ACCUSES: Defined(
            "Accuses",
            checked_by=(
                "engine.customs.civics.gather_evidence",
                "engine.polity.trials.accuse_case",
                "engine.polity.trials.by_combat",
                "engine.polity.trials.testimony_weight",
                "engine.polity.trials.try_case",
            ),
            used_by=("engine.polity.trials.accuse_case", "engine.polity.trials.frame_case", "engine.polity.trials.testimony_of"),
        ),
        Deposition.SHIELDS: Defined(
            "Shields",
            checked_by=("engine.polity.trials.tamper", "engine.polity.trials.testimony_weight", "engine.polity.trials.try_case"),
            used_by=("engine.polity.trials.tamper", "engine.polity.trials.testimony_of"),
        ),
        Deposition.SILENT: Defined("Silent", checked_by=(), used_by=("engine.polity.trials.accuse_case", "engine.polity.trials.testimony_of")),
    },
)
