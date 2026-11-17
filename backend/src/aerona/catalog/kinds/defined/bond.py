from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.bond import PseudoLinkKind

PSEUDO_LINK_KIND = total(
    PseudoLinkKind,
    {
        PseudoLinkKind.ROUTE: Defined("Route", checked_by=(), used_by=("catalog.bonds.LINK_GROUP_KINDS",)),
        PseudoLinkKind.IN_WORLD: Defined("In world", checked_by=(), used_by=()),
        PseudoLinkKind.CREATED: Defined("Created", checked_by=(), used_by=("catalog.bonds.LINK_GROUP_KINDS",)),
    },
)
