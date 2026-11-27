from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.affliction import ForgetScope, PackageKind, SleepUntil
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule
from aerona.domain.enums.records import ProcessClock as C
from aerona.domain.enums.records import ProcessGroup as G

KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "language.endangered",
        G.PEOPLES,
        "{subject} came near its end, kept by {speakers:speaker|speakers}.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(FactSpec("speakers", FactValue.NUMBER, FactUnit.PEOPLE),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "petition.answered",
        G.SOCIAL,
        "The crowd of {place} brought its petition to those who rule; answered: {answered}.",
        roles=(RoleSpec(R.PLACE),),
        facts=(FactSpec("answered", FactValue.NUMBER, FactUnit.COUNT), FactSpec("participants", FactValue.NUMBER, FactUnit.PEOPLE)),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "gift.hoarded",
        G.SOCIAL,
        "{actor} kept{instrument:? #} of the circuit {circuit} instead of passing it on.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.INSTRUMENT, required=False)),
        facts=(FactSpec("circuit", FactValue.NAME),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "affliction.aged",
        G.BODY,
        "{patient} was moved {years:year|years} through its life by what it bears.",
        roles=(RoleSpec(R.PATIENT),),
        facts=(FactSpec("years", FactValue.NUMBER, FactUnit.YEARS),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "affliction.forgot",
        G.BODY,
        "{patient} lost {lost:memory|memories} to what it bears: {scope}.",
        roles=(RoleSpec(R.PATIENT),),
        facts=(FactSpec("lost", FactValue.NUMBER, FactUnit.COUNT), FactSpec("scope", FactValue.ENUM, enum=ForgetScope)),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "affliction.slept",
        G.BODY,
        "{patient} fell into a sleep it could not leave, {until}; its household spends {care} tending it.",
        roles=(RoleSpec(R.PATIENT),),
        facts=(FactSpec("care", FactValue.NUMBER, FactUnit.WEALTH_POINTS), FactSpec("until", FactValue.ENUM, enum=SleepUntil)),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "affliction.woke",
        G.BODY,
        "{patient} woke from {package}.",
        roles=(RoleSpec(R.PATIENT),),
        facts=(FactSpec("package", FactValue.ENUM, enum=PackageKind),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "affliction.recognised",
        G.BODY,
        "{actor} read the sign of {package} on {patient}.",
        roles=(RoleSpec(R.PATIENT), RoleSpec(R.ACTOR)),
        facts=(FactSpec("package", FactValue.ENUM, enum=PackageKind),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
)
