from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.dominion import MagicSiteKind

MAGIC_SITE_KIND = total(
    MagicSiteKind,
    {
        MagicSiteKind.SOURCE: Defined("Source", checked_by=("engine.arcana.vis.from_sites", "engine.dominion.sites.yield_sites"), used_by=()),
        MagicSiteKind.SCHOOL_SEAT: Defined("School seat", checked_by=("engine.lore.rites.site_factor",), used_by=()),
        MagicSiteKind.WARD: Defined("Ward", checked_by=("engine.lore.rites.site_factor",), used_by=()),
        MagicSiteKind.GATEWAY: Defined("Gateway", checked_by=("engine.dominion.sites.reveal", "engine.dominion.sites.seed_sites"), used_by=()),
        MagicSiteKind.TIDE_POINT: Defined("Tide point", checked_by=(), used_by=()),
        MagicSiteKind.DEPLETION_SCAR: Defined("Depletion scar", checked_by=(), used_by=()),
        MagicSiteKind.CONFLUENCE: Defined("Confluence", checked_by=("engine.dominion.sites.meet_and_fail",), used_by=()),
        MagicSiteKind.NULL_ZONE: Defined("Null zone", checked_by=("engine.dominion.sites.in_null_zone",), used_by=()),
    },
)
