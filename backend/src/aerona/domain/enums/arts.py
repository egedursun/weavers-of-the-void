from enum import StrEnum


class ArtMarketRole(StrEnum):
    COLLECTOR = "collector"
    DEALER = "dealer"
    PATRON = "patron"
    CONNOISSEUR = "connoisseur"


class ForgeryKind(StrEnum):
    ARTWORK = "artwork"
    RELIC = "relic"
    DOCUMENT = "document"
    BRAND = "brand"


class ForgeryStatus(StrEnum):
    HIDDEN = "hidden"
    EXPOSED = "exposed"


class CanonPath(StrEnum):
    RENOWN = "renown"
    INSTITUTION = "institution"
    COPYING = "copying"
    TEACHING = "teaching"
    MOVEMENT = "movement"


class ClubKind(StrEnum):
    TEAM_GAME = "team_game"
    RACING = "racing"
    COMBAT = "combat"
    ATHLETICS = "athletics"


class FandomLine(StrEnum):
    NONE = "none"
    CLASS = "class"
    DISTRICT = "district"
    FAITH = "faith"
