from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.belonging import FugitiveKind, SanctuaryKind

FUGITIVE_KIND = total(
    FugitiveKind,
    {
        FugitiveKind.OUTLAW: Defined("Outlaw", checked_by=(), used_by=("engine.belonging.sanctuary.fugitives", "services.player.belonging.SanctuaryDraft")),
        FugitiveKind.ACCUSED: Defined("Accused", checked_by=(), used_by=("engine.belonging.sanctuary.fugitives",)),
        FugitiveKind.DEFECTOR: Defined("Defector", checked_by=(), used_by=("engine.belonging.sanctuary.asylums",)),
    },
)

SANCTUARY_KIND = total(
    SanctuaryKind,
    {
        SanctuaryKind.TEMPLE: Defined(
            "Temple sanctuary",
            checked_by=("engine.belonging.sanctuary.violate",),
            used_by=("engine.belonging.sanctuary.host_for", "services.player.belonging.SanctuaryDraft"),
        ),
        SanctuaryKind.HOSPITALITY: Defined("Guest right", checked_by=(), used_by=("engine.belonging.sanctuary.host_for",)),
        SanctuaryKind.ASYLUM: Defined("Asylum in a realm", checked_by=(), used_by=("engine.belonging.sanctuary.asylums",)),
    },
)
