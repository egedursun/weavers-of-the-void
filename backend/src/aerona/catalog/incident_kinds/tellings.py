from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule, ProcessClock, ProcessGroup

CORRECTED = "rumour.corrected"
CONTRADICTED = "information.contradicted"
RETOLD = "event.retold"
RECOUNTED = "event.recounted"
PLANTED = "rumour.planted"
PLANTED_ATROCITY = "rumour.planted_atrocity"

KINDS: tuple[IncidentKindSpec, ...] = (
    *(
        IncidentKindSpec(
            key,
            ProcessGroup.KNOWLEDGE,
            "{subject} is said to have done this: {account}",
            roles=(RoleSpec(IncidentRole.SUBJECT), RoleSpec(IncidentRole.TELLER, required=False)),
            facts=(FactSpec("account", FactValue.NAME),),
            place=PlaceRule.WHEN_KNOWN,
            clock=ProcessClock.INSTANT,
            chronicle_kind=ChronicleKind.KNOWLEDGE,
            told=False,
        )
        for key in (PLANTED, PLANTED_ATROCITY)
    ),
    IncidentKindSpec(
        CORRECTED,
        ProcessGroup.KNOWLEDGE,
        "{subject} set its account of an earlier happening right after {teller} told it more truly; {dropped:changed detail|changed details} fell away.",
        roles=(RoleSpec(IncidentRole.SUBJECT), RoleSpec(IncidentRole.TELLER)),
        facts=(FactSpec("dropped", FactValue.NUMBER, FactUnit.COUNT), FactSpec("fidelity", FactValue.NUMBER, FactUnit.PERCENT)),
        place=PlaceRule.WHEN_KNOWN,
        clock=ProcessClock.INSTANT,
        chronicle_kind=ChronicleKind.KNOWLEDGE,
    ),
    IncidentKindSpec(
        CONTRADICTED,
        ProcessGroup.KNOWLEDGE,
        "{subject} heard {teller} tell {happening} otherwise than it knew it: "
        "{differences:difference|differences} between the accounts, and trust in what is told fell by {trust_lost}.",
        roles=(RoleSpec(IncidentRole.SUBJECT), RoleSpec(IncidentRole.TELLER)),
        facts=(
            FactSpec("happening", FactValue.NAME),
            FactSpec("differences", FactValue.NUMBER, FactUnit.COUNT),
            FactSpec("trust_lost", FactValue.NUMBER, FactUnit.PERCENT),
        ),
        place=PlaceRule.WHEN_KNOWN,
        clock=ProcessClock.INSTANT,
        terms=True,
        chronicle_kind=ChronicleKind.KNOWLEDGE,
    ),
    IncidentKindSpec(
        RETOLD,
        ProcessGroup.GODS,
        "{teller} told {witness} an account of an earlier happening, with {changes:change|changes} to it.",
        roles=(RoleSpec(IncidentRole.TELLER), RoleSpec(IncidentRole.WITNESS, many=True)),
        facts=(FactSpec("changes", FactValue.NUMBER, FactUnit.COUNT),),
        place=PlaceRule.NONE,
        clock=ProcessClock.INSTANT,
        chronicle_kind=ChronicleKind.SPEECH,
    ),
    IncidentKindSpec(
        RECOUNTED,
        ProcessGroup.KNOWLEDGE,
        "{teller} told {witness} what they knew of an earlier happening.",
        roles=(RoleSpec(IncidentRole.TELLER), RoleSpec(IncidentRole.WITNESS, many=True)),
        facts=(FactSpec("fidelity", FactValue.NUMBER, FactUnit.PERCENT),),
        place=PlaceRule.WHEN_KNOWN,
        clock=ProcessClock.INSTANT,
        chronicle_kind=ChronicleKind.SPEECH,
    ),
)
