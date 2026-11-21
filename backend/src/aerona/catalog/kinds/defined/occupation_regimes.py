from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.occupation_regimes import CollaborationKind

COLLABORATION_KIND = total(
    CollaborationKind,
    {
        CollaborationKind.ADMINISTRATION: Defined(
            "Administration", checked_by=("engine.occupation_regime.collaborators.join",), used_by=("db.tables.occupation_regimes.CollaborationRow",)
        ),
        CollaborationKind.POLICE: Defined(
            "Police", checked_by=(), used_by=("engine.occupation_regime.effects.INTELLIGENCE", "engine.occupation_regime.measures.ENFORCERS")
        ),
        CollaborationKind.INFORMING: Defined("Informing", checked_by=(), used_by=("engine.occupation_regime.effects.INTELLIGENCE",)),
        CollaborationKind.TRADE: Defined("Trade", checked_by=(), used_by=()),
        CollaborationKind.MILITIA: Defined("Militia", checked_by=(), used_by=("engine.occupation_regime.measures.ENFORCERS",)),
        CollaborationKind.PROPAGANDA: Defined("Propaganda", checked_by=(), used_by=()),
    },
)
