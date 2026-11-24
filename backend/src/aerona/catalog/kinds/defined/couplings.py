from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.couplings import FieldAgreementKind

FIELD_AGREEMENT_KIND = total(
    FieldAgreementKind,
    {
        FieldAgreementKind.PARLEY: Defined("Parley", checked_by=(), used_by=("engine.couplings.field.parley", "tools.mortal.couplings.parley")),
        FieldAgreementKind.TRUCE: Defined("Truce", checked_by=(), used_by=("engine.couplings.field.parley", "tools.mortal.couplings.parley")),
        FieldAgreementKind.SURRENDER: Defined(
            "Surrender terms",
            checked_by=("engine.couplings.field.lapse", "engine.couplings.field.under_terms"),
            used_by=("engine.couplings.field.offer_terms",),
        ),
        FieldAgreementKind.EXCHANGE: Defined("Exchange of captives and the dead", checked_by=(), used_by=("engine.couplings.field.exchanges",)),
        FieldAgreementKind.SAFE_CONDUCT: Defined("Safe conduct", checked_by=(), used_by=("engine.couplings.field.offer_terms",)),
        FieldAgreementKind.FRATERNISATION: Defined("Fraternisation", checked_by=(), used_by=("engine.couplings.field.fraternise",)),
        FieldAgreementKind.BURIAL_TRUCE: Defined("Burial truce", checked_by=(), used_by=("engine.couplings.field.bury_dead",)),
    },
)
