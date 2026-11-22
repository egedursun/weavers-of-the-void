from aerona.core.total import partial
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.culture import ItemClass, Technique
from aerona.domain.enums.site import ExcavationFind, ExcavationRisk, SiteChallenge, SiteRoomKind

RISKS = (ExcavationRisk.CURSE, ExcavationRisk.SPIRIT, ExcavationRisk.COLLAPSE)


FINDS = (ExcavationFind.ARTIFACT, ExcavationFind.BOOK, ExcavationFind.TECHNIQUE, ExcavationFind.REGALIA, ExcavationFind.ROUTE_MAP)


CURSES = (PackageKind.HUNGER_CURSE, PackageKind.POSSESSION, PackageKind.VOID_TAINT)


FIND_CLASSES = partial(
    ExcavationFind,
    {
        ExcavationFind.ARTIFACT: ItemClass.IDOL,
        ExcavationFind.BOOK: ItemClass.BOOK,
        ExcavationFind.TECHNIQUE: ItemClass.TOOL,
        ExcavationFind.REGALIA: ItemClass.CROWN,
        ExcavationFind.ROUTE_MAP: ItemClass.MAP,
    },
    without={ExcavationFind.NOTHING, ExcavationFind.WAKING},
)


LOST_TECHNIQUES = (Technique.ARCH, Technique.CARTOGRAPHY, Technique.WARDING, Technique.ALCHEMY, Technique.ASTRONOMY_INSTRUMENTS, Technique.WRITTEN_LAW)


CHALLENGES = (SiteChallenge.TRAP, SiteChallenge.GUARDIAN, SiteChallenge.PUZZLE, SiteChallenge.HAZARD)

FURNISH_SITE_ROOM_KINDS = (SiteRoomKind.LAIR, SiteRoomKind.HEART)
FURNISH_SITE_ROOM_KINDS_2 = (SiteRoomKind.CRYPT, SiteRoomKind.SHRINE, SiteRoomKind.HEART)
