from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.cycles import ChallengeKind, ChallengeResponse, DescentGroup, GiftOccasion, KinTermSystem, LegacyKind, ManumissionPath

CHALLENGE_KIND = total(
    ChallengeKind,
    {
        ChallengeKind.DISASTER: Defined(
            "Disaster", checked_by=("engine.cycles.challenge.kind_of",), used_by=("engine.cycles.challenge.FLOW_KINDS", "services.player.cycles.ChallengeDraft")
        ),
        ChallengeKind.CLIMATE: Defined("A turn of the climate", checked_by=(), used_by=("engine.cycles.challenge.kind_of",)),
        ChallengeKind.INVASION: Defined("Invasion", checked_by=(), used_by=("engine.cycles.challenge.FLOW_KINDS",)),
        ChallengeKind.PLAGUE: Defined("Plague", checked_by=(), used_by=("engine.cycles.challenge.FLOW_KINDS",)),
        ChallengeKind.FAMINE: Defined("Famine", checked_by=(), used_by=("engine.cycles.challenge.FLOW_KINDS",)),
        ChallengeKind.COLLAPSE: Defined("Collapse", checked_by=("engine.cycles.challenge_signals.SIGNALS",), used_by=()),
        ChallengeKind.SECESSION: Defined("Secession", checked_by=("engine.cycles.challenge_signals.SIGNALS",), used_by=()),
        ChallengeKind.TECHNOLOGICAL_SHOCK: Defined("Technological shock", checked_by=("engine.cycles.challenge_signals.SIGNALS",), used_by=()),
        ChallengeKind.SOURCE_DEPLETION: Defined("Source depletion", checked_by=("engine.cycles.challenge_signals.SIGNALS",), used_by=()),
        ChallengeKind.RUNAWAY: Defined("Runaway", checked_by=("engine.cycles.challenge_signals.SIGNALS",), used_by=()),
        ChallengeKind.REVELATION: Defined("Revelation", checked_by=("engine.cycles.challenge_signals.SIGNALS",), used_by=()),
        ChallengeKind.MIGRATION_WAVE: Defined("Migration wave", checked_by=("engine.cycles.challenge_signals.SIGNALS",), used_by=()),
    },
)

CHALLENGE_RESPONSE = total(
    ChallengeResponse,
    {
        ChallengeResponse.STAGNATION: Defined("Stagnation", checked_by=(), used_by=("engine.cycles.challenge.response_to",)),
        ChallengeResponse.RESPONSE: Defined(
            "A creative answer",
            checked_by=("engine.cycles.challenge.answer", "engine.cycles.challenge.meet_challenges"),
            used_by=("db.tables.cycles.ChallengeRow", "engine.cycles.challenge.response_to"),
        ),
        ChallengeResponse.COLLAPSE: Defined(
            "Collapse",
            checked_by=("engine.cycles.challenge.answer", "engine.cycles.challenge.meet_challenges"),
            used_by=("engine.cycles.challenge.response_to",),
        ),
    },
)

DESCENT_GROUP = total(
    DescentGroup,
    {
        DescentGroup.LINEAGE: Defined(
            "Lineages",
            checked_by=("engine.cycles.lineage.line_of", "engine.kin.seed.GROUP_FORMS"),
            used_by=("db.tables.cycles.KinshipSystemRow", "engine.cycles.seeding.group_for", "services.player.cycles.KinshipDraft"),
        ),
        DescentGroup.CLAN: Defined(
            "Clans", checked_by=("engine.cycles.seeding.match_for", "engine.kin.seed.GROUP_FORMS"), used_by=("engine.cycles.seeding.group_for",)
        ),
        DescentGroup.MOIETY: Defined(
            "Two halves",
            checked_by=("engine.cycles.lineage.kin_bars", "engine.cycles.seeding.match_for", "engine.kin.seed.GROUP_FORMS"),
            used_by=("engine.cycles.seeding.group_for",),
        ),
        DescentGroup.HOUSE: Defined(
            "Houses", checked_by=("engine.cycles.lineage.line_of",), used_by=("engine.cycles.lineage.line_of", "engine.cycles.seeding.group_for")
        ),
    },
)

GIFT_OCCASION = total(
    GiftOccasion,
    {
        GiftOccasion.COURTESY: Defined(
            "Courtesy",
            checked_by=(),
            used_by=("db.tables.cycles.GiftRow", "engine.cycles.gifts.divine_gift", "services.player.cycles.GiftDraft", "tools.mortal.cycles.bestow_gift"),
        ),
        GiftOccasion.FEAST: Defined(
            "A rank-claiming feast",
            checked_by=(),
            used_by=("engine.cycles.gifts.COMPETITIVE", "engine.cycles.gifts.potlatch", "engine.cycles.gifts.return_gift"),
        ),
        GiftOccasion.CIRCUIT: Defined("A ceremonial circuit", checked_by=(), used_by=("engine.cycles.gifts.pass_circuit",)),
        GiftOccasion.OFFERING: Defined("An offering", checked_by=("tools.son.cycles.answer_offerings",), used_by=("tools.mortal.cycles.make_offering",)),
        GiftOccasion.MARRIAGE: Defined("A marriage gift", checked_by=(), used_by=("engine.cycles.gifts.marriage_payments", "engine.cycles.gifts.pay_union")),
        GiftOccasion.RETURN: Defined("A return gift", checked_by=(), used_by=("engine.cycles.gifts.return_gift",)),
        GiftOccasion.ALLIANCE: Defined("Between allies", checked_by=(), used_by=("engine.cycles.gifts.courtesy",)),
        GiftOccasion.RELIEF: Defined("Aid in a stricken hour", checked_by=(), used_by=("engine.agrarian.resilience.aid_from",)),
    },
)

KIN_TERM_SYSTEM = total(
    KinTermSystem,
    {
        KinTermSystem.GENERATIONAL: Defined(
            "One term for each generation", checked_by=("engine.cycles.lineage.kin_bars",), used_by=("engine.cycles.seeding.cousins_for",)
        ),
        KinTermSystem.LINEAL: Defined(
            "Direct kin apart from side kin",
            checked_by=(),
            used_by=("db.tables.cycles.KinshipSystemRow", "engine.cycles.seeding.cousins_for", "services.player.cycles.KinshipDraft"),
        ),
        KinTermSystem.BIFURCATE_MERGING: Defined(
            "A parent's like sibling is called parent",
            checked_by=(),
            used_by=("engine.cycles.lineage.PARALLEL_AS_SIBLINGS", "engine.cycles.seeding.cousins_for"),
        ),
        KinTermSystem.BIFURCATE_COLLATERAL: Defined("Each side has its own terms", checked_by=(), used_by=("engine.cycles.seeding.cousins_for",)),
        KinTermSystem.CROSS_PARALLEL: Defined(
            "Parallel cousins are siblings, cross cousins apart",
            checked_by=("engine.kin.seed.duties_for",),
            used_by=("engine.cycles.lineage.PARALLEL_AS_SIBLINGS", "engine.cycles.seeding.cousins_for"),
        ),
        KinTermSystem.DESCRIPTIVE: Defined("Each kinsperson has a term of their own", checked_by=(), used_by=("engine.cycles.seeding.cousins_for",)),
    },
)

LEGACY_KIND = total(
    LegacyKind,
    {
        LegacyKind.MARTIAL_STYLE: Defined("Way of war", checked_by=("engine.cycles.legacy.CULTURE_ENUMS", "engine.cycles.legacy.CULTURE_FIELDS"), used_by=()),
        LegacyKind.AESTHETIC: Defined(
            "Style", checked_by=("api.routers.cycles.legacy_label", "engine.cycles.legacy.apply_legacy", "engine.cycles.legacy.legacy_key"), used_by=()
        ),
        LegacyKind.FUNERAL_RITE: Defined("Funeral rite", checked_by=("engine.cycles.legacy.CULTURE_ENUMS", "engine.cycles.legacy.CULTURE_FIELDS"), used_by=()),
        LegacyKind.BELIEF: Defined(
            "Belief", checked_by=("engine.cycles.legacy.apply_legacy", "engine.cycles.legacy.legacy_key"), used_by=("api.routers.cycles.NAMED_LEGACIES",)
        ),
        LegacyKind.VALUE: Defined("Value", checked_by=("api.routers.cycles.legacy_label",), used_by=()),
        LegacyKind.INNOVATION: Defined(
            "Innovation", checked_by=("api.routers.cycles.legacy_label", "engine.cycles.legacy.apply_legacy", "engine.cycles.legacy.legacy_key"), used_by=()
        ),
        LegacyKind.ART_FORM: Defined(
            "Art form", checked_by=("engine.cycles.legacy.apply_legacy", "engine.cycles.legacy.legacy_key"), used_by=("api.routers.cycles.NAMED_LEGACIES",)
        ),
        LegacyKind.TECHNIQUE: Defined("Technique", checked_by=(), used_by=()),
        LegacyKind.LAW: Defined("Law", checked_by=(), used_by=()),
        LegacyKind.INSTITUTION: Defined("Institution", checked_by=(), used_by=()),
        LegacyKind.LANGUAGE: Defined("Language", checked_by=(), used_by=()),
    },
)

MANUMISSION_PATH = total(
    ManumissionPath,
    {
        ManumissionPath.PURCHASE: Defined(
            "Bought their freedom",
            checked_by=("engine.cycles.indenture.bought_freedom",),
            used_by=("engine.cycles.indenture.SKILLED_PATHS", "engine.cycles.indenture.manumission_path"),
        ),
        ManumissionPath.WILL: Defined(
            "By a master's will", checked_by=(), used_by=("engine.cycles.indenture.manumission_path", "engine.demography.society_control.manumit")
        ),
        ManumissionPath.SERVICE: Defined(
            "Freed for service", checked_by=(), used_by=("engine.cycles.indenture.SKILLED_PATHS", "engine.cycles.indenture.manumission_path")
        ),
        ManumissionPath.LAW: Defined("By law", checked_by=(), used_by=("engine.cycles.indenture.manumission_path", "services.player.cycles.FreeDraft")),
        ManumissionPath.REVOLT: Defined("By revolt", checked_by=("engine.cycles.indenture.revolts_in",), used_by=("engine.cycles.bondage.slave_risings",)),
    },
)
