from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.crafts import AssistiveAid, CatchGround, CatchRight, InsuranceCover, Notation, RightAcquired, RightKind

ASSISTIVE_AID = total(
    AssistiveAid,
    {
        AssistiveAid.SPECTACLES: Defined(
            "Spectacles", checked_by=(), used_by=("engine.body.state.has_reader", "engine.crafts.aids.FROM_CONDITION", "engine.crafts.aids.GROUND_LENS")
        ),
        AssistiveAid.MAGNIFIER: Defined(
            "Magnifier", checked_by=(), used_by=("engine.body.state.reading_of", "engine.crafts.aids.FROM_SKILL", "engine.crafts.aids.GROUND_LENS")
        ),
        AssistiveAid.TELESCOPE: Defined(
            "Telescope",
            checked_by=("engine.crafts.aids.gaze",),
            used_by=("engine.crafts.aids.FROM_SKILL", "engine.crafts.aids.GROUND_LENS", "engine.environment.long_seasons.forecast"),
        ),
        AssistiveAid.HEARING_HORN: Defined("Hearing horn", checked_by=(), used_by=("engine.body.state.reading_of", "engine.crafts.aids.FROM_CONDITION")),
        AssistiveAid.CANE: Defined("Cane", checked_by=(), used_by=("engine.body.state.reading_of", "engine.crafts.aids.FROM_CONDITION")),
    },
)

CATCH_GROUND = total(
    CatchGround,
    {
        CatchGround.FISHERY: Defined(
            "Fishery",
            checked_by=(),
            used_by=("engine.couplings.registers.SEA_GROUNDS", "engine.crafts.grounds.seed_fisheries", "services.player.crafts.CatchGroundDraft"),
        ),
        CatchGround.TRAPPING: Defined(
            "Trapping",
            checked_by=(),
            used_by=("engine.couplings.registers.HUNT_GROUNDS", "engine.crafts.catch.LAND_GROUNDS", "engine.crafts.grounds.seed_land"),
        ),
        CatchGround.FOWLING: Defined(
            "Fowling", checked_by=(), used_by=("engine.couplings.registers.HUNT_GROUNDS", "engine.crafts.catch.LAND_GROUNDS", "engine.crafts.grounds.seed_land")
        ),
        CatchGround.MARINE_HUNT: Defined(
            "Hunt of great sea beasts",
            checked_by=("engine.crafts.grounds.hunt_risk",),
            used_by=("engine.couplings.registers.SEA_GROUNDS", "engine.crafts.grounds.seed_fisheries"),
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

RIGHT_KIND = total(
    RightKind,
    {
        RightKind.SONG: Defined("Song", checked_by=(), used_by=("catalog.art_modes.ART_MODES", "services.player.crafts.IncorporealRightDraft")),
        RightKind.DANCE: Defined("Dance", checked_by=(), used_by=("catalog.art_modes.ART_MODES",)),
        RightKind.STORY: Defined("Story", checked_by=(), used_by=("catalog.art_modes.ART_MODES",)),
        RightKind.RITE: Defined("Rite", checked_by=(), used_by=("engine.crafts.rights.claim_works",)),
        RightKind.DESIGN: Defined("Design", checked_by=(), used_by=("catalog.art_modes.ART_MODES", "engine.crafts.rights.COPIED")),
        RightKind.NAME: Defined("Name", checked_by=(), used_by=("engine.crafts.rights.claim_names",)),
        RightKind.TITLE: Defined("Title", checked_by=(), used_by=("engine.crafts.rights.claim_names",)),
        RightKind.TRADEMARK: Defined("Mark of a maker", checked_by=(), used_by=("engine.crafts.rights.COPIED",)),
        RightKind.MARKET_PRIVILEGE: Defined("Market privilege", checked_by=(), used_by=("engine.crafts.rights.COPIED",)),
    },
)
