from enum import StrEnum


class ArtMarketRole(StrEnum):
    COLLECTOR = "collector"
    DEALER = "dealer"
    PATRON = "patron"
    CONNOISSEUR = "connoisseur"
    CURATOR = "curator"
    CRITIC = "critic"
    FORGER = "forger"


class ForgeryKind(StrEnum):
    ARTWORK = "artwork"
    RELIC = "relic"
    DOCUMENT = "document"
    BRAND = "brand"
    COIN = "coin"
    LINEAGE = "lineage"
    SEAL = "seal"


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
    ANIMAL_CONTEST = "animal_contest"
    MIND_GAMES = "mind_games"


class FandomLine(StrEnum):
    NONE = "none"
    CLASS = "class"
    DISTRICT = "district"
    FAITH = "faith"
