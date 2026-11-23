from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.site import RoomContentKind

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
        RoomContentKind.MIND: Defined("Mind", checked_by=(), used_by=("engine.sites.rooms.furnish", "engine.sites.rooms.wake_mind")),
        RoomContentKind.RELIC: Defined("Relic", checked_by=(), used_by=("engine.sites.rooms.claim_relic", "engine.sites.rooms.furnish")),
        RoomContentKind.REALM_GATE: Defined("Realm gate", checked_by=(), used_by=("engine.sites.rooms.find_gate", "engine.sites.rooms.furnish")),
        RoomContentKind.RECORDS: Defined("Records", checked_by=("engine.sites.rooms.loot",), used_by=("engine.sites.rooms.seal_and_shelve",)),
    },
)
