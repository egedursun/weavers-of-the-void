from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.divine import BargainGain, BargainPrice, CouncilSeat, DivineCost, LawException, SonPunishment, WoundCause

BARGAIN_GAIN = total(
    BargainGain,
    {
        BargainGain.ESSENCE: Defined(
            "Essence",
            checked_by=(),
            used_by=(
                "db.tables.foreign_gods.OuterBargainRow",
                "engine.cosmos.actions.BargainTerms",
                "services.player.pantheon.OuterBargainOrder",
                "tools.son.cosmos.OuterBargainInput",
            ),
        ),
        BargainGain.POWER: Defined("A power", checked_by=("engine.divine.outer.take_gain",), used_by=()),
        BargainGain.MIGHT: Defined("Might", checked_by=("engine.divine.outer.take_gain",), used_by=()),
    },
)

BARGAIN_PRICE = total(
    BargainPrice,
    {
        BargainPrice.WORLD_SANITY: Defined(
            "A world's sanity",
            checked_by=(),
            used_by=(
                "db.tables.foreign_gods.OuterBargainRow",
                "engine.cosmos.actions.BargainTerms",
                "services.player.pantheon.OuterBargainOrder",
                "tools.son.cosmos.OuterBargainInput",
            ),
        ),
        BargainPrice.DOMAIN: Defined(
            "One of its domains", checked_by=("engine.cosmos.actions.bargain_with_outer", "engine.divine.outer.pay_price"), used_by=()
        ),
        BargainPrice.TRUE_NAME: Defined("Its true name", checked_by=("engine.divine.outer.pay_price",), used_by=()),
    },
)

COUNCIL_SEAT = total(
    CouncilSeat,
    {
        CouncilSeat.BY_RIGHT: Defined(
            "Sits by right",
            checked_by=("engine.divine.council_order.enact_expel", "engine.divine.council_order.foreign_members"),
            used_by=("db.tables.council_order.DivineSeatRow", "engine.divine.council_order.exclusion", "engine.divine.council_order.seat_gods"),
        ),
        CouncilSeat.INVITED: Defined("Invited", checked_by=(), used_by=("engine.divine.council_order.enact_admit", "services.player.council_order.SeatSet")),
        CouncilSeat.BY_PACT: Defined("Sits by a pact", checked_by=(), used_by=("engine.divine.council_order.seat_gods",)),
        CouncilSeat.RECOGNISED: Defined("Recognised by the gods", checked_by=(), used_by=("engine.divine.council_order.enact_recognise",)),
    },
)

DIVINE_COST = total(
    DivineCost,
    {
        DivineCost.ESSENCE: Defined(
            "Essence",
            checked_by=("engine.divine.grammar.pay",),
            used_by=(
                "db.tables.divine_powers.DivinePowerRow",
                "engine.divine.grammar.grant_by_worship",
                "engine.divine.grammar.preset_row",
                "services.player.divine_powers.DivinePowerCreate",
            ),
        ),
        DivineCost.ATTENTION: Defined("Attention", checked_by=("engine.divine.grammar.pay",), used_by=()),
        DivineCost.STANDING: Defined("Standing", checked_by=("engine.divine.grammar.pay",), used_by=()),
        DivineCost.DOMAIN: Defined("Strength of its domain", checked_by=("engine.divine.grammar.pay",), used_by=()),
        DivineCost.SACRIFICE: Defined("A sacrifice by the faithful", checked_by=("engine.divine.grammar.pay",), used_by=()),
    },
)

LAW_EXCEPTION = total(
    LawException,
    {
        LawException.NONE: Defined(
            "No exception",
            checked_by=("engine.divine.laws.exempt",),
            used_by=("db.tables.divine.NaturalLawProfileRow", "engine.divine.law_grammar.set_grammar", "engine.divine.laws.drafted_profile"),
        ),
        LawException.CREATOR_CHOSEN: Defined("Except the Creator's chosen", checked_by=("engine.divine.laws.exempt",), used_by=()),
        LawException.AUTHOR_WORSHIPPERS: Defined("Except the author's faithful", checked_by=("engine.divine.laws.exempt",), used_by=()),
        LawException.HEROES: Defined("Except heroes", checked_by=("engine.divine.laws.exempt",), used_by=()),
        LawException.AVATARS: Defined("Except avatars of the gods", checked_by=("engine.divine.laws.exempt",), used_by=()),
    },
)

SON_PUNISHMENT = total(
    SonPunishment,
    {
        SonPunishment.CHAIN: Defined(
            "Chain",
            checked_by=("engine.divine.decrees.council_chained", "engine.divine.rulings.enforce_rulings"),
            used_by=("agents.council.apply_decision", "engine.divine.rulings.engine_motion"),
        ),
        SonPunishment.EXILE: Defined("Exile", checked_by=("engine.divine.rulings.enact_punishment", "engine.divine.rulings.enforce_rulings"), used_by=()),
        SonPunishment.STRIP_POWER: Defined("Strip a power", checked_by=("engine.divine.rulings.enact_punishment",), used_by=()),
        SonPunishment.STRIP_DIVINITY: Defined("Strip of divinity", checked_by=("engine.divine.rulings.enact_punishment",), used_by=()),
    },
)

WOUND_CAUSE = total(
    WoundCause,
    {
        WoundCause.DUEL: Defined("a duel of the gods", checked_by=(), used_by=("engine.cosmos.duels.son_duel",)),
        WoundCause.GOD_WAR: Defined("a war of gods", checked_by=(), used_by=("engine.cosmos.foreign_gods.resolve_god_war",)),
        WoundCause.CREATOR: Defined("the Creator", checked_by=("engine.divine.wounds.death_cause",), used_by=("engine.divine.control.wound_god",)),
        WoundCause.AVATAR_SLAIN: Defined("the death of its mortal form", checked_by=(), used_by=("engine.divine.wounds.avatar_slain",)),
        WoundCause.OUTER_BARGAIN: Defined(
            "a bargain with an outer being",
            checked_by=("engine.divine.wounds.death_cause", "engine.transform.gods.bargained"),
            used_by=("engine.divine.outer.pay_price",),
        ),
    },
)
