from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.customs import EvidenceKind, IntoxicantUse, MarkKind, MarkMeaning, MemberRight, NameForm, NamingPattern, ReliefKind, RevivalAim

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
            checked_by=(),
            used_by=(
                "catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES",
                "catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES_2",
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
            "Forbidden", checked_by=("engine.customs.intoxicants.habits",), used_by=("catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES_2",)
        ),
    },
)

MARK_KIND = total(
    MarkKind,
    {
        MarkKind.TATTOO: Defined("Tattoo", checked_by=(), used_by=("services.player.customs.BodyMarkDraft",)),
        MarkKind.SCAR: Defined("Scar", checked_by=(), used_by=()),
        MarkKind.PIERCING: Defined("Piercing", checked_by=(), used_by=()),
        MarkKind.SHAPING: Defined("Shaping", checked_by=(), used_by=()),
        MarkKind.FILED_TEETH: Defined("Filed teeth", checked_by=(), used_by=()),
        MarkKind.COSMETIC: Defined("Cosmetic", checked_by=(), used_by=()),
        MarkKind.JEWELLERY: Defined("Jewellery", checked_by=(), used_by=()),
        MarkKind.BRAND: Defined("Brand", checked_by=("engine.customs.marks.MARKABLE",), used_by=("engine.mortal.justice.sentence",)),
    },
)

MARK_MEANING = total(
    MarkMeaning,
    {
        MarkMeaning.STATUS: Defined(
            "Status",
            checked_by=("catalog.life.customs.EVENT_BONDS",),
            used_by=("catalog.life.customs.READ_MARK_MARK_MEANINGS", "services.player.customs.MarkCustomDraft"),
        ),
        MarkMeaning.CLAN: Defined("Clan", checked_by=("engine.customs.marks.happened",), used_by=("catalog.life.customs.READ_MARK_MARK_MEANINGS_2",)),
        MarkMeaning.DEED: Defined(
            "Deeds",
            checked_by=("catalog.life.customs.EVENT_BONDS",),
            used_by=("catalog.life.customs.READ_MARK_MARK_MEANINGS", "services.player.customs.BodyMarkDraft"),
        ),
        MarkMeaning.AGE_SET: Defined(
            "Age-set",
            checked_by=("engine.customs.age_sets.initiate", "engine.customs.marks.keep_marks"),
            used_by=("catalog.life.customs.READ_MARK_MARK_MEANINGS_2", "engine.customs.age_sets.initiate"),
        ),
        MarkMeaning.MARRIAGE: Defined(
            "Marriage", checked_by=("catalog.life.customs.EVENT_BONDS",), used_by=("catalog.life.customs.READ_MARK_MARK_MEANINGS_2",)
        ),
        MarkMeaning.MOURNING: Defined("Mourning", checked_by=("engine.customs.marks.happened",), used_by=("catalog.life.customs.CALM_MARKED_MARK_MEANINGS",)),
        MarkMeaning.PROTECTION: Defined(
            "Protection", checked_by=("engine.customs.marks.happened",), used_by=("catalog.life.customs.CALM_MARKED_MARK_MEANINGS",)
        ),
        MarkMeaning.CRIME: Defined(
            "Crime", checked_by=("engine.customs.marks.read_mark", "engine.customs.marks.seed_customs"), used_by=("engine.mortal.justice.sentence",)
        ),
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

NAME_FORM = total(
    NameForm,
    {
        NameForm.BIRTH: Defined("Birth name", checked_by=(), used_by=("engine.customs.naming.name_life", "engine.customs.naming.teknonyms")),
        NameForm.SECRET: Defined("Secret name", checked_by=(), used_by=("engine.customs.naming.name_life",)),
        NameForm.DEED: Defined("Deed name", checked_by=(), used_by=("engine.customs.naming.teknonyms",)),
        NameForm.INITIATION: Defined("Initiation name", checked_by=(), used_by=("engine.customs.naming.initiate_name",)),
        NameForm.MARRIAGE: Defined("Marriage name", checked_by=(), used_by=("engine.customs.naming.name_life",)),
        NameForm.VOW: Defined("Vow name", checked_by=(), used_by=("engine.customs.naming.name_life",)),
        NameForm.ASCENSION: Defined("Ascension name", checked_by=("engine.customs.naming.name_life",), used_by=("engine.customs.naming.name_life",)),
    },
)

NAMING_PATTERN = total(
    NamingPattern,
    {
        NamingPattern.GIVEN: Defined("A given name", checked_by=(), used_by=("db.tables.customs.NamingCustomRow", "services.player.customs.NamingCustomDraft")),
        NamingPattern.PARENT: Defined("Named for a parent", checked_by=("engine.customs.naming.birth_name",), used_by=()),
        NamingPattern.CLAN: Defined("Named for the clan", checked_by=("engine.customs.naming.birth_name",), used_by=()),
        NamingPattern.TEKNONYM: Defined("Named for a child", checked_by=("engine.customs.naming.name_life",), used_by=()),
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

REVIVAL_AIM = total(
    RevivalAim,
    {
        RevivalAim.RESTORE: Defined(
            "Restore the old ways",
            checked_by=("engine.customs.revival.open_revival",),
            used_by=("catalog.life.tools.AIMS", "engine.customs.revival.aim_for", "services.player.customs.RevivalDraft"),
        ),
        RevivalAim.SYNTHESISE: Defined(
            "Join old and new",
            checked_by=("engine.customs.revival.open_revival", "engine.customs.revival.pull_values"),
            used_by=("engine.customs.revival.aim_for",),
        ),
        RevivalAim.ADOPT: Defined(
            "Adopt the pressed ways",
            checked_by=("engine.customs.revival.open_revival", "engine.customs.revival.pull_values"),
            used_by=("catalog.life.tools.AIMS", "engine.customs.revival.aim_for"),
        ),
    },
)
