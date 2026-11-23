from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.arts import FandomLine

FANDOM_LINE = total(
    FandomLine,
    {
        FandomLine.NONE: Defined("No line", checked_by=("engine.arts.sport.read_line",), used_by=("db.tables.arts.ClubRow", "engine.arts.sport.read_line")),
        FandomLine.CLASS: Defined("Class", checked_by=(), used_by=("engine.arts.sport.read_line",)),
        FandomLine.DISTRICT: Defined("District", checked_by=(), used_by=("engine.arts.sport.read_line",)),
        FandomLine.FAITH: Defined("Faith", checked_by=(), used_by=("engine.arts.sport.read_line",)),
    },
)
