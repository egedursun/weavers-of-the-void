from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.arts import ClubKind, FandomLine, ForgeryKind

CLUB_KIND = total(
    ClubKind,
    {
        ClubKind.TEAM_GAME: Defined("Team game", checked_by=(), used_by=("catalog.life.arts.FIELD_GAMES", "db.tables.arts.ClubRow")),
        ClubKind.RACING: Defined("Racing", checked_by=(), used_by=("catalog.life.arts.FIELD_GAMES",)),
        ClubKind.COMBAT: Defined("Combat", checked_by=(), used_by=("catalog.life.arts.FIELD_GAMES",)),
        ClubKind.ATHLETICS: Defined("Athletics", checked_by=(), used_by=("catalog.life.arts.FIELD_GAMES",)),
    },
)

FANDOM_LINE = total(
    FandomLine,
    {
        FandomLine.NONE: Defined("No line", checked_by=("engine.arts.sport.read_line",), used_by=("db.tables.arts.ClubRow", "engine.arts.sport.read_line")),
        FandomLine.CLASS: Defined("Class", checked_by=(), used_by=("engine.arts.sport.read_line",)),
        FandomLine.DISTRICT: Defined("District", checked_by=(), used_by=("engine.arts.sport.read_line",)),
        FandomLine.FAITH: Defined("Faith", checked_by=(), used_by=("engine.arts.sport.read_line",)),
    },
)

FORGERY_KIND = total(
    ForgeryKind,
    {
        ForgeryKind.ARTWORK: Defined("A work of art", checked_by=("engine.arts.forgery.forge",), used_by=("engine.arts.forgery.kind_for",)),
        ForgeryKind.RELIC: Defined("A relic", checked_by=("engine.arts.forgery.forge",), used_by=("engine.arts.forgery.kind_for",)),
        ForgeryKind.DOCUMENT: Defined("A charter", checked_by=("engine.arts.forgery.forge",), used_by=("engine.arts.forgery.kind_for",)),
        ForgeryKind.BRAND: Defined("A brand", checked_by=(), used_by=("engine.arts.forgery.forge", "engine.arts.forgery.kind_for")),
    },
)
