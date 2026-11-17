from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.statecraft import CrisisDemand, ResolutionKind

DEMAND_TEXT: Mapping[CrisisDemand, str] = total(
    CrisisDemand,
    {
        CrisisDemand.CEDE_REGION: "cede a land",
        CrisisDemand.RELEASE_VASSAL: "release a vassal",
        CrisisDemand.CONVERT: "take up its faith",
        CrisisDemand.PAY: "pay what it owes",
    },
)

RESOLUTION_TEXT: Mapping[ResolutionKind, str] = total(
    ResolutionKind,
    {
        ResolutionKind.ROUTE_SECURITY: "guard the routes between its worlds",
        ResolutionKind.EMBARGO: "embargo a realm",
        ResolutionKind.VOID_BAN: "ban rites of the void",
        ResolutionKind.SANCTION: "sanction the world of a god",
    },
)
