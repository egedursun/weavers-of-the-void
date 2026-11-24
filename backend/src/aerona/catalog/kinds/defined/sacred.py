from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.sacred import BureauRank, SacramentProtection, SignInfluence, TheodicyResolution

BUREAU_RANK = total(
    BureauRank,
    {
        BureauRank.HEARTH: Defined("Hearth", checked_by=(), used_by=("catalog.sacred.SPIRIT_RANKS",)),
        BureauRank.LOCAL: Defined(
            "Local", checked_by=(), used_by=("catalog.sacred.SPIRIT_RANKS", "db.tables.sacred.SpiritOfficeRow", "services.player.sacred.OfficeDraft")
        ),
        BureauRank.CITY: Defined("Town", checked_by=(), used_by=("catalog.sacred.SPIRIT_RANKS",)),
        BureauRank.PROVINCE: Defined("Province", checked_by=(), used_by=("catalog.sacred.SPIRIT_RANKS",)),
        BureauRank.MINISTRY: Defined("Ministry", checked_by=(), used_by=()),
    },
)

SACRAMENT_PROTECTION = total(
    SacramentProtection,
    {
        SacramentProtection.ROUTING: Defined(
            "The soul's way after death", checked_by=(), used_by=("catalog.sacred.SACRAMENT_GUARDS", "engine.sacred.guards.rite_chance")
        ),
        SacramentProtection.POSSESSION: Defined("Possession", checked_by=(), used_by=("catalog.sacred.SACRAMENT_GUARDS", "engine.sacred.guards.warded_hosts")),
        SacramentProtection.UNREST: Defined("Unrest at death", checked_by=(), used_by=("catalog.sacred.SACRAMENT_GUARDS", "engine.sacred.guards.unrest_shift")),
        SacramentProtection.CURSE: Defined("Curses", checked_by=(), used_by=("catalog.sacred.SACRAMENT_GUARDS", "engine.sacred.guards.curse_ward")),
        SacramentProtection.FORTUNE: Defined("Fortune", checked_by=(), used_by=("catalog.sacred.SACRAMENT_GUARDS", "engine.sacred.bureau.avenge")),
    },
)

SIGN_INFLUENCE = total(
    SignInfluence,
    {
        SignInfluence.REAL: Defined("Truly rules", checked_by=("engine.sacred.astrology.sign_birth",), used_by=("engine.sacred.astrology.sign_birth",)),
        SignInfluence.BELIEVED: Defined("Believed only", checked_by=(), used_by=("db.tables.sacred.BirthSignRow", "engine.sacred.astrology.sign_birth")),
    },
)

THEODICY_RESOLUTION = total(
    TheodicyResolution,
    {
        TheodicyResolution.PENDING: Defined(
            "Unresolved",
            checked_by=(
                "agents.context.sacred_lines.son_sacred_lines",
                "agents.context.sacred_lines.town_lines",
                "engine.sacred.control.answer_crisis",
                "engine.sacred.mysteries.keep_theodicy",
                "engine.sacred.mysteries.test_doctrines",
            ),
            used_by=("db.tables.sacred.TheodicyCrisisRow",),
        ),
        TheodicyResolution.ANSWERED: Defined(
            "Answered by the god", checked_by=(), used_by=("engine.sacred.control.answer_crisis", "engine.sacred.mysteries.resolve_crisis")
        ),
        TheodicyResolution.ARGUED: Defined("Settled by argument", checked_by=(), used_by=("engine.sacred.mysteries.seek_another_way",)),
        TheodicyResolution.NEW_DOCTRINE: Defined("A new doctrine", checked_by=(), used_by=("engine.sacred.mysteries.seek_another_way",)),
        TheodicyResolution.CONVERSION: Defined("Turned away", checked_by=(), used_by=("engine.sacred.mysteries.seek_another_way",)),
        TheodicyResolution.SECULAR_DRIFT: Defined("Drifted from faith", checked_by=(), used_by=("engine.sacred.mysteries.seek_another_way",)),
    },
)
