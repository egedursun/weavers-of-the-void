from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.kin_dynamics import KinStir

KIN_STIR = total(
    KinStir,
    {
        KinStir.FAVOUR: Defined("Favour", checked_by=("tools.son.kin_dynamics.stir",), used_by=()),
        KinStir.RIVALRY: Defined("Rivalry", checked_by=("tools.son.kin_dynamics.stir",), used_by=()),
        KinStir.RECONCILE: Defined("Reconcile", checked_by=("tools.son.kin_dynamics.stir",), used_by=()),
        KinStir.ELDER: Defined("Elder", checked_by=("tools.son.kin_dynamics.stir",), used_by=()),
    },
)
