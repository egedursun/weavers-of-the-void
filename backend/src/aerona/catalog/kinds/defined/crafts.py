from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.crafts import CatchMedium, CatchRight, InsuranceCover, Notation, RightAcquired

CATCH_MEDIUM = total(
    CatchMedium,
    {
        CatchMedium.WATER: Defined("Water", checked_by=(), used_by=("catalog.catch.GROUNDS", "engine.couplings.registers.SEA_GROUNDS")),
        CatchMedium.LAND: Defined(
            "Land", checked_by=(), used_by=("catalog.catch.GROUNDS", "engine.couplings.registers.HUNT_GROUNDS", "engine.crafts.catch.LAND_GROUNDS")
        ),
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

INSURANCE_COVER = total(
    InsuranceCover,
    {
        InsuranceCover.CARGO: Defined(
            "Cargo",
            checked_by=("engine.crafts.cover.cargo_holders",),
            used_by=("engine.crafts.insurance.candidates", "engine.economy.routes.mourn_losses", "services.player.crafts.InsurancePolicyDraft"),
        ),
        InsuranceCover.HOUSE: Defined("House", checked_by=(), used_by=("engine.crafts.insurance.candidates", "engine.environment.hazards.strike")),
        InsuranceCover.LIFE: Defined(
            "Life",
            checked_by=("engine.crafts.cover.claim", "tools.mortal.crafts.buy_insurance"),
            used_by=("engine.crafts.insurance.candidates", "engine.lifecycle.mortal_death.die", "tools.mortal.crafts.buy_insurance"),
        ),
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

RIGHT_ACQUIRED = total(
    RightAcquired,
    {
        RightAcquired.CREATED: Defined(
            "Made", checked_by=(), used_by=("db.tables.crafts.IncorporealRightRow", "engine.crafts.rights.claim_names", "engine.crafts.rights.claim_works")
        ),
        RightAcquired.INHERITED: Defined("Inherited", checked_by=(), used_by=("engine.crafts.heirs.pass_rights",)),
        RightAcquired.BOUGHT: Defined("Bought", checked_by=(), used_by=("engine.crafts.rights.collect_licence",)),
        RightAcquired.LICENSED: Defined("Licensed", checked_by=("engine.crafts.rights.licensed_copy",), used_by=("engine.crafts.rights.licensed_copy",)),
        RightAcquired.STOLEN: Defined("Stolen", checked_by=(), used_by=("engine.crafts.rights.infringe",)),
        RightAcquired.GRANTED: Defined("Granted", checked_by=(), used_by=("services.player.crafts.IncorporealRightDraft",)),
    },
)
