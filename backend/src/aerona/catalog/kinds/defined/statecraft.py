from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.statecraft import NobleWant, SubjectKind

NOBLE_WANT = total(
    NobleWant,
    {
        NobleWant.DWELLING: Defined("Dwelling", checked_by=(), used_by=()),
        NobleWant.FINE_GOODS: Defined("Fine goods", checked_by=("engine.polity.mandates.satisfied",), used_by=()),
        NobleWant.OFFICE: Defined("Office", checked_by=("engine.polity.mandates.satisfied",), used_by=()),
        NobleWant.HONOUR: Defined("Honour", checked_by=("engine.polity.mandates.satisfied",), used_by=()),
    },
)

SUBJECT_KIND = total(
    SubjectKind,
    {
        SubjectKind.VASSAL: Defined(
            "Vassal",
            checked_by=(),
            used_by=(
                "db.tables.polity.VassalageRow",
                "engine.polity.subjects.LEVY_KINDS",
                "engine.polity.subjects.TRIBUTE_KINDS",
                "engine.polity.subjects.held_kind",
                "tools.mortal.ways_of_rule.FealtyInput",
            ),
        ),
        SubjectKind.TRIBUTARY: Defined("Tributary", checked_by=(), used_by=("engine.polity.subjects.TRIBUTE_KINDS", "engine.polity.subjects.held_kind")),
        SubjectKind.MARCH: Defined("March", checked_by=(), used_by=("engine.polity.subjects.LEVY_KINDS", "engine.polity.subjects.held_kind")),
        SubjectKind.PERSONAL_UNION: Defined("Personal union", checked_by=("engine.polity.subjects.dissolved",), used_by=("engine.polity.titles.join_crowns",)),
        SubjectKind.CLIENT: Defined("Client", checked_by=(), used_by=("engine.polity.subjects.PROTECTED_KINDS", "engine.polity.subjects.kind_for")),
        SubjectKind.COLONY: Defined(
            "Colony",
            checked_by=("engine.polity.formation.subject_government",),
            used_by=("engine.polity.subjects.LEVY_KINDS", "engine.polity.subjects.TRIBUTE_KINDS", "engine.polity.subjects.kind_for"),
        ),
        SubjectKind.PROTECTORATE: Defined(
            "Protectorate", checked_by=(), used_by=("engine.polity.subjects.PROTECTED_KINDS", "engine.polity.subjects.held_kind")
        ),
        SubjectKind.ENCLAVE: Defined(
            "Enclave",
            checked_by=(),
            used_by=("engine.polity.subjects.PROTECTED_KINDS", "engine.polity.subjects.TRIBUTE_KINDS", "engine.polity.subjects.bound_kind"),
        ),
        SubjectKind.MANDATE: Defined(
            "Mandate", checked_by=(), used_by=("engine.polity.subjects.LEVY_KINDS", "engine.polity.subjects.TRIBUTE_KINDS", "engine.polity.subjects.bound_kind")
        ),
        SubjectKind.ASSOCIATED_STATE: Defined(
            "Associated state", checked_by=(), used_by=("engine.polity.subjects.PROTECTED_KINDS", "engine.polity.subjects.bound_kind")
        ),
    },
)
