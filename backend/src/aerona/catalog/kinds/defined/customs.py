from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.customs import EvidenceKind, IntoxicantUse, MemberRight, ReliefKind

EVIDENCE_KIND = total(
    EvidenceKind,
    {
        EvidenceKind.WITNESS: Defined("A witness", checked_by=(), used_by=("catalog.crimes.CRIMES", "engine.customs.civics.gather_evidence")),
        EvidenceKind.TRACE: Defined(
            "A trace", checked_by=(), used_by=("catalog.crimes.CRIMES", "engine.customs.civics.gather_evidence", "services.player.customs.EvidenceDraft")
        ),
        EvidenceKind.DOCUMENT: Defined(
            "A document", checked_by=(), used_by=("catalog.crimes.CRIMES", "engine.customs.civics.gather_evidence", "engine.media.press.recorded_evidence")
        ),
        EvidenceKind.CONFESSION: Defined("A confession", checked_by=(), used_by=("catalog.crimes.CRIMES", "engine.customs.civics.read_and_confess")),
        EvidenceKind.DIVINATION: Defined("A divination", checked_by=(), used_by=("catalog.crimes.CRIMES", "engine.customs.civics.read_and_confess")),
        EvidenceKind.MAGIC: Defined(
            "Magic", checked_by=("engine.crafts.sympathy.links_as_evidence",), used_by=("catalog.crimes.CRIMES", "engine.crafts.sympathy.links_as_evidence")
        ),
    },
)

INTOXICANT_USE = total(
    IntoxicantUse,
    {
        IntoxicantUse.DAILY: Defined(
            "Daily",
            checked_by=("engine.customs.intoxicants.habits",),
            used_by=(
                "catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES",
                "catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES_2",
                "engine.customs.intoxicants.adopt_new",
                "engine.customs.intoxicants.seed_customs",
            ),
        ),
        IntoxicantUse.FEAST: Defined(
            "At feasts",
            checked_by=("engine.customs.intoxicants.keep_intoxication",),
            used_by=(
                "catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES",
                "db.tables.customs.IntoxicantCustomRow",
                "engine.customs.intoxicants.seed_customs",
                "services.player.customs.IntoxicantCustomDraft",
            ),
        ),
        IntoxicantUse.RITE: Defined(
            "In rites", checked_by=("engine.customs.intoxicants.keep_intoxication",), used_by=("engine.customs.intoxicants.seed_customs",)
        ),
        IntoxicantUse.MOURNING: Defined("In mourning", checked_by=("engine.customs.intoxicants.keep_intoxication",), used_by=()),
        IntoxicantUse.FORBIDDEN: Defined(
            "Forbidden",
            checked_by=("engine.customs.intoxicants.forbids", "engine.customs.intoxicants.habits", "engine.customs.intoxicants.keep_intoxication"),
            used_by=("catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES_2",),
        ),
        IntoxicantUse.MEDICINE: Defined(
            "As medicine",
            checked_by=("engine.customs.intoxicants.keep_intoxication",),
            used_by=("catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES_2", "engine.customs.intoxicants.adopt_new"),
        ),
        IntoxicantUse.HOSPITALITY: Defined("Offered to guests", checked_by=("engine.customs.intoxicants.keep_intoxication",), used_by=()),
    },
)

MEMBER_RIGHT = total(
    MemberRight,
    {
        MemberRight.OFFICE: Defined("Office", checked_by=(), used_by=("engine.polity.offices.appoint", "services.player.customs.RightGrant")),
        MemberRight.MARRIAGE: Defined("Marriage", checked_by=(), used_by=("catalog.life.customs.RIGHTS", "engine.customs.rights.unwed_by_law")),
        MemberRight.ARMS: Defined("Arms", checked_by=(), used_by=("catalog.life.customs.RIGHTS", "engine.customs.rights.unarmed")),
        MemberRight.COURTS: Defined("The courts", checked_by=(), used_by=("catalog.life.customs.RIGHTS", "engine.polity.trials.by_judge")),
    },
)

RELIEF_KIND = total(
    ReliefKind,
    {
        ReliefKind.GRANARY: Defined("Granary distribution", checked_by=(), used_by=()),
        ReliefKind.ALMS: Defined("Alms", checked_by=(), used_by=("services.player.customs.PoorReliefDraft",)),
        ReliefKind.WORKHOUSE: Defined("Workhouses", checked_by=(), used_by=()),
        ReliefKind.PARISH: Defined("Parish relief", checked_by=(), used_by=()),
    },
)
