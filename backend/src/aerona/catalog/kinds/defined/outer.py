from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.outer import OuterSealKind

OUTER_SEAL_KIND = total(
    OuterSealKind,
    {
        OuterSealKind.SEAL: Defined("Sealed", checked_by=(), used_by=("db.tables.outer_agency.OuterSealRow", "services.player.outer_agency.SealSet")),
        OuterSealKind.BANISH: Defined(
            "Banished",
            checked_by=("engine.divine.outer_agency.press_seals", "engine.divine.outer_agency.seal_being", "services.player.outer_agency.seal_set"),
            used_by=(),
        ),
    },
)
