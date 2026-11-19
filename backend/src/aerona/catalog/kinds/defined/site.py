from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.site import BattlefieldFeature, ExcavationRisk, RoomContentKind, SiteChallenge, SiteRoomKind

BATTLEFIELD_FEATURE = total(
    BattlefieldFeature,
    {
        BattlefieldFeature.MASS_GRAVE: Defined("Mass grave", checked_by=("engine.sites.digs.tend_battlefields",), used_by=()),
        BattlefieldFeature.SALVAGE_FIELD: Defined("Field of salvage", checked_by=("engine.sites.digs.tend_battlefields",), used_by=()),
        BattlefieldFeature.EARTHWORKS: Defined(
            "Old earthworks", checked_by=("engine.sites.digs.mark_battlefields", "engine.sites.digs.tend_battlefields"), used_by=()
        ),
    },
)

EXCAVATION_RISK = total(
    ExcavationRisk,
    {
        ExcavationRisk.NONE: Defined(
            "No risk", checked_by=("engine.sites.digs.dig_on",), used_by=("db.tables.sites.ExcavationStageRow", "engine.sites.digs.plan_stages")
        ),
        ExcavationRisk.CURSE: Defined("Curse", checked_by=("engine.sites.digs.suffer",), used_by=("engine.sites.digs.RISKS",)),
        ExcavationRisk.SPIRIT: Defined("Spirit", checked_by=("engine.sites.digs.suffer",), used_by=("engine.sites.digs.RISKS",)),
        ExcavationRisk.COLLAPSE: Defined("Collapse", checked_by=("engine.sites.digs.suffer",), used_by=("engine.sites.digs.RISKS",)),
    },
)

ROOM_CONTENT_KIND = total(
    RoomContentKind,
    {
        RoomContentKind.ITEM: Defined("Item", checked_by=("engine.sites.rooms.loot",), used_by=("engine.sites.rooms.furnish",)),
        RoomContentKind.SPIRIT: Defined("Spirit", checked_by=("engine.sites.rooms.loot",), used_by=("engine.sites.rooms.furnish",)),
        RoomContentKind.BEAST: Defined(
            "Beast", checked_by=("engine.sites.rooms.loot", "engine.sites.rooms.walk_room"), used_by=("engine.sites.rooms.furnish",)
        ),
        RoomContentKind.TRAP: Defined(
            "Trap", checked_by=("engine.gatherings.control.add_content", "engine.sites.rooms.loot"), used_by=("engine.sites.rooms.furnish",)
        ),
        RoomContentKind.MIND: Defined("Mind", checked_by=("engine.sites.rooms.FOUND",), used_by=("engine.sites.rooms.furnish",)),
        RoomContentKind.RELIC: Defined("Relic", checked_by=("engine.sites.rooms.FOUND",), used_by=("engine.sites.rooms.furnish",)),
        RoomContentKind.REALM_GATE: Defined("Realm gate", checked_by=("engine.sites.rooms.FOUND",), used_by=("engine.sites.rooms.furnish",)),
    },
)

SITE_CHALLENGE = total(
    SiteChallenge,
    {
        SiteChallenge.NONE: Defined(
            "No challenge",
            checked_by=("engine.sites.rooms.walk_room",),
            used_by=("db.tables.sites.SiteRoomRow", "engine.sites.rooms.furnish", "services.player.gatherings.RoomDraft"),
        ),
        SiteChallenge.TRAP: Defined("Trap", checked_by=("engine.sites.rooms.furnish",), used_by=("engine.sites.rooms.CHALLENGES",)),
        SiteChallenge.GUARDIAN: Defined(
            "Guardian", checked_by=("engine.sites.rooms.walk_room",), used_by=("engine.sites.rooms.CHALLENGES", "engine.sites.rooms.furnish")
        ),
        SiteChallenge.PUZZLE: Defined("Puzzle", checked_by=(), used_by=("engine.sites.rooms.CHALLENGES",)),
        SiteChallenge.HAZARD: Defined("Hazard", checked_by=(), used_by=("engine.sites.rooms.CHALLENGES",)),
    },
)

SITE_ROOM_KIND = total(
    SiteRoomKind,
    {
        SiteRoomKind.GATE: Defined(
            "Gate",
            checked_by=("engine.sites.rooms.furnish",),
            used_by=("catalog.gatherings.ROOM_PLACES", "catalog.gatherings.ROOM_SETTLEMENTS", "catalog.gatherings.ROOM_STRUCTURES"),
        ),
        SiteRoomKind.HALL: Defined(
            "Hall", checked_by=(), used_by=("catalog.gatherings.ROOM_PLACES", "catalog.gatherings.ROOM_SETTLEMENTS", "catalog.gatherings.ROOM_STRUCTURES")
        ),
        SiteRoomKind.STAIR: Defined("Stair", checked_by=(), used_by=("catalog.gatherings.ROOM_PLACES", "catalog.gatherings.ROOM_STRUCTURES")),
        SiteRoomKind.CELL: Defined(
            "Cell", checked_by=(), used_by=("catalog.gatherings.ROOM_PLACES", "catalog.gatherings.ROOM_SETTLEMENTS", "catalog.gatherings.ROOM_STRUCTURES")
        ),
        SiteRoomKind.CHAMBER: Defined("Chamber", checked_by=(), used_by=("catalog.gatherings.ROOM_PLACES", "catalog.gatherings.ROOM_STRUCTURES")),
        SiteRoomKind.VAULT: Defined(
            "Vault",
            checked_by=(),
            used_by=(
                "catalog.gatherings.GUARDED_ROOMS",
                "catalog.gatherings.ITEM_ROOMS",
                "catalog.gatherings.ROOM_PLACES",
                "catalog.gatherings.ROOM_SETTLEMENTS",
                "catalog.gatherings.ROOM_STRUCTURES",
            ),
        ),
        SiteRoomKind.SHRINE: Defined(
            "Shrine",
            checked_by=("engine.sites.rooms.furnish",),
            used_by=("catalog.gatherings.ROOM_PLACES", "catalog.gatherings.ROOM_SETTLEMENTS", "catalog.gatherings.ROOM_STRUCTURES"),
        ),
        SiteRoomKind.LAIR: Defined(
            "Lair", checked_by=("engine.sites.rooms.furnish",), used_by=("catalog.gatherings.GUARDED_ROOMS", "catalog.gatherings.ROOM_PLACES")
        ),
        SiteRoomKind.LIBRARY: Defined(
            "Library",
            checked_by=(),
            used_by=(
                "catalog.gatherings.ITEM_ROOMS",
                "catalog.gatherings.ROOM_PLACES",
                "catalog.gatherings.ROOM_SETTLEMENTS",
                "catalog.gatherings.ROOM_STRUCTURES",
            ),
        ),
        SiteRoomKind.ARMOURY: Defined(
            "Armoury", checked_by=(), used_by=("catalog.gatherings.ITEM_ROOMS", "catalog.gatherings.ROOM_SETTLEMENTS", "catalog.gatherings.ROOM_STRUCTURES")
        ),
        SiteRoomKind.CRYPT: Defined(
            "Crypt",
            checked_by=("engine.sites.rooms.furnish",),
            used_by=(
                "catalog.gatherings.GUARDED_ROOMS",
                "catalog.gatherings.ITEM_ROOMS",
                "catalog.gatherings.ROOM_PLACES",
                "catalog.gatherings.ROOM_SETTLEMENTS",
                "catalog.gatherings.ROOM_STRUCTURES",
            ),
        ),
        SiteRoomKind.LABORATORY: Defined(
            "Laboratory", checked_by=(), used_by=("catalog.gatherings.ROOM_PLACES", "catalog.gatherings.ROOM_SETTLEMENTS", "catalog.gatherings.ROOM_STRUCTURES")
        ),
        SiteRoomKind.HOUSE: Defined("House", checked_by=(), used_by=("catalog.gatherings.ROOM_SETTLEMENTS",)),
        SiteRoomKind.STORE: Defined(
            "Store",
            checked_by=(),
            used_by=(
                "catalog.gatherings.ITEM_ROOMS",
                "catalog.gatherings.ROOM_PLACES",
                "catalog.gatherings.ROOM_SETTLEMENTS",
                "catalog.gatherings.ROOM_STRUCTURES",
            ),
        ),
        SiteRoomKind.HEART: Defined(
            "Heart of the site",
            checked_by=("engine.sites.rooms.furnish",),
            used_by=(
                "catalog.gatherings.GUARDED_ROOMS",
                "catalog.gatherings.ITEM_ROOMS",
                "catalog.gatherings.ROOM_PLACES",
                "catalog.gatherings.ROOM_SETTLEMENTS",
                "catalog.gatherings.ROOM_STRUCTURES",
            ),
        ),
    },
)
