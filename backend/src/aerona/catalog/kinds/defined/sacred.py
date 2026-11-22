from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.sacred import (
    BureauRank,
    DivinationQuestion,
    PetitionKind,
    SacramentProtection,
    SignInfluence,
    SpiritOffence,
    TheodicyResolution,
    VisionKind,
)

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

DIVINATION_QUESTION = total(
    DivinationQuestion,
    {
        DivinationQuestion.BATTLE: Defined(
            "Battle",
            checked_by=(),
            used_by=("catalog.life.sacred.TRUE_OMEN_DIVINATION_QUESTIONS", "engine.sacred.foresight.question_for", "engine.sacred.omens.battle_omen"),
        ),
        DivinationQuestion.WAR: Defined(
            "War",
            checked_by=(),
            used_by=("catalog.life.sacred.TRUE_OMEN_DIVINATION_QUESTIONS", "engine.sacred.foresight.question_for", "engine.sacred.omens.war_forbidden"),
        ),
        DivinationQuestion.WEDDING: Defined(
            "Wedding", checked_by=("engine.sacred.foresight.heed", "engine.sacred.foresight.true_omen"), used_by=("engine.sacred.foresight.question_for",)
        ),
        DivinationQuestion.CORONATION: Defined(
            "Accession", checked_by=("engine.sacred.foresight.heed", "engine.sacred.foresight.true_omen"), used_by=("engine.sacred.foresight.question_for",)
        ),
        DivinationQuestion.HARVEST: Defined(
            "Harvest", checked_by=("engine.sacred.foresight.heed",), used_by=("engine.sacred.foresight.question_for", "services.player.sacred.ReadingDraft")
        ),
    },
)

PETITION_KIND = total(
    PetitionKind,
    {
        PetitionKind.HEALING: Defined(
            "Healing", checked_by=("engine.sacred.bureau.answer",), used_by=("catalog.life.sacred.COMMON_NEEDS", "services.player.sacred.PetitionDraft")
        ),
        PetitionKind.HARVEST: Defined("A good harvest", checked_by=("engine.sacred.bureau.answer",), used_by=("engine.sacred.bureau.need_of",)),
        PetitionKind.FERTILITY: Defined("Children", checked_by=("engine.sacred.bureau.answer",), used_by=("catalog.life.sacred.COMMON_NEEDS",)),
        PetitionKind.SAFE_PASSAGE: Defined("Safe passage", checked_by=("engine.sacred.bureau.answer",), used_by=("catalog.life.sacred.COMMON_NEEDS",)),
        PetitionKind.PROSPERITY: Defined("Prosperity", checked_by=("engine.sacred.bureau.answer",), used_by=("catalog.life.sacred.COMMON_NEEDS",)),
        PetitionKind.SUIT: Defined(
            "A suit against a spirit",
            checked_by=(
                "engine.sacred.bureau.answer",
                "engine.sacred.bureau.file_petition",
                "engine.sacred.control.lodge_petition",
                "tools.mortal.sacred.petition_spirit",
            ),
            used_by=("engine.sacred.bureau.need_of",),
        ),
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
    },
)

SIGN_INFLUENCE = total(
    SignInfluence,
    {
        SignInfluence.REAL: Defined("Truly rules", checked_by=("engine.sacred.astrology.sign_birth",), used_by=("engine.sacred.astrology.sign_birth",)),
        SignInfluence.BELIEVED: Defined("Believed only", checked_by=(), used_by=("db.tables.sacred.BirthSignRow", "engine.sacred.astrology.sign_birth")),
    },
)

SPIRIT_OFFENCE = total(
    SpiritOffence,
    {
        SpiritOffence.POLLUTION: Defined("Pollution", checked_by=(), used_by=("engine.sacred.spirits.land_offence",)),
        SpiritOffence.CLEARING: Defined("Clearing of the woods", checked_by=(), used_by=("engine.sacred.spirits.land_offence",)),
        SpiritOffence.UNPAID: Defined("Offerings left unpaid", checked_by=(), used_by=("engine.sacred.spirits.offence_of",)),
        SpiritOffence.TABOO: Defined("A broken taboo", checked_by=(), used_by=("engine.sacred.spirits.offence_of",)),
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

VISION_KIND = total(
    VisionKind,
    {
        VisionKind.VISION: Defined("Vision", checked_by=(), used_by=()),
        VisionKind.UNION: Defined("Union", checked_by=(), used_by=()),
        VisionKind.VOICE: Defined("A voice", checked_by=(), used_by=()),
        VisionKind.TRANCE: Defined("Trance", checked_by=(), used_by=()),
    },
)
