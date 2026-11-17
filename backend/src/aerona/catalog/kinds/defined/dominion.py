from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.dominion import MagicSiteKind, PrayerTone

MAGIC_SITE_KIND = total(
    MagicSiteKind,
    {
        MagicSiteKind.SOURCE: Defined("Source", checked_by=("engine.arcana.vis.from_sites", "engine.dominion.sites.yield_sites"), used_by=()),
        MagicSiteKind.SCHOOL_SEAT: Defined("School seat", checked_by=("engine.lore.rites.site_factor",), used_by=()),
        MagicSiteKind.WARD: Defined("Ward", checked_by=("engine.lore.rites.site_factor",), used_by=()),
        MagicSiteKind.GATEWAY: Defined("Gateway", checked_by=("engine.dominion.sites.reveal", "engine.dominion.sites.seed_sites"), used_by=()),
        MagicSiteKind.TIDE_POINT: Defined("Tide point", checked_by=(), used_by=()),
        MagicSiteKind.DEPLETION_SCAR: Defined("Depletion scar", checked_by=(), used_by=()),
    },
)

PRAYER_TONE = total(
    PrayerTone,
    {
        PrayerTone.THANKS: Defined("Thanks", checked_by=(), used_by=("engine.dominion.worship.prayer_tone",)),
        PrayerTone.MERCY: Defined("A plea for mercy", checked_by=(), used_by=("engine.dominion.worship.prayer_tone",)),
    },
)
