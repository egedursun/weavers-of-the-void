from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.crafts import CatchMedium, CatchRight, Notation

CATCH_MEDIUM = total(
    CatchMedium,
    {
        CatchMedium.WATER: Defined("Water", checked_by=(), used_by=("catalog.catch.GROUNDS", "engine.couplings.registers.SEA_GROUNDS")),
        CatchMedium.LAND: Defined(
            "Land",
            checked_by=("tools.mortal.deep.open_catch_ground",),
            used_by=("catalog.catch.GROUNDS", "engine.couplings.registers.HUNT_GROUNDS", "engine.crafts.catch.LAND_GROUNDS"),
        ),
        CatchMedium.SHORE: Defined("Shore", checked_by=(), used_by=("catalog.catch.GROUNDS", "engine.crafts.shores.WORKED_MEDIA")),
        CatchMedium.UNDER_WATER: Defined("Under water", checked_by=(), used_by=("catalog.catch.GROUNDS", "engine.crafts.shores.WORKED_MEDIA")),
        CatchMedium.POND: Defined("Pond", checked_by=(), used_by=("catalog.catch.GROUNDS", "engine.crafts.shores.WORKED_MEDIA")),
    },
)

CATCH_RIGHT = total(
    CatchRight,
    {
        CatchRight.COMMONS: Defined(
            "Common to all",
            checked_by=("engine.couplings.fisheries.closures",),
            used_by=("db.tables.crafts.CatchGroundRow", "engine.crafts.grounds.seed_fisheries", "services.player.crafts.CatchGroundDraft"),
        ),
        CatchRight.OWNED: Defined("Owned", checked_by=("engine.crafts.grounds.poaching",), used_by=("engine.crafts.grounds.seed_fisheries",)),
    },
)

NOTATION = total(
    Notation,
    {
        Notation.ADDITIVE: Defined(
            "Added up",
            checked_by=("engine.crafts.numbers.keep_numbers",),
            used_by=("db.tables.crafts.NumberSystemRow", "engine.crafts.numbers.seed_system", "services.player.crafts.NumberSystemDraft"),
        ),
        Notation.POSITIONAL: Defined(
            "By place",
            checked_by=("agents.context.crafts_lines.people_lines", "engine.crafts.reckoning.notation_boost"),
            used_by=("engine.crafts.numbers.keep_numbers", "engine.crafts.numbers.seed_system"),
        ),
    },
)
