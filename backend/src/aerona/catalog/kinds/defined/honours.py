from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.honours import VeteranGrant

VETERAN_GRANT = total(
    VeteranGrant,
    {
        VeteranGrant.LAND: Defined("Land in a colony", checked_by=(), used_by=("engine.honours.veterans.grant",)),
        VeteranGrant.PENSION: Defined(
            "Pensions",
            checked_by=("engine.honours.veterans.grant", "engine.honours.veterans.pay_pensions"),
            used_by=("engine.honours.veterans.grant", "services.player.honours.VeteranGrantDraft"),
        ),
        VeteranGrant.NONE: Defined("Nothing", checked_by=("engine.honours.veterans.bitter_veterans",), used_by=("engine.honours.veterans.grant",)),
    },
)
