from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.entity import EntityType as E
from aerona.domain.enums.military import DuelContext, DuelEnd
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.polity import OathKind
from aerona.domain.enums.records import FactValue, PlaceRule
from aerona.domain.enums.records import ProcessClock as C
from aerona.domain.enums.records import ProcessGroup as G

KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "captive.paroled",
        G.SOCIAL,
        "{actor} freed {subject} on parole, an oath of {oath_kind} sworn before going home to {origin}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.ORIGIN)),
        facts=(FactSpec("oath_kind", FactValue.ENUM, enum=OathKind),),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "captive.married_in",
        G.SOCIAL,
        "{subject}, once a captive of {actor}, stayed with {spouse} and joined the people of the captors for good.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.SPOUSE, frozenset({E.MORTAL})), RoleSpec(R.ORIGIN, required=False)),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "duel.fought",
        G.SINGLE_COMBAT,
        "{actor} and {opponent} fought a duel of {context} that ended in {end}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.OPPONENT, frozenset({E.MORTAL}))),
        facts=(FactSpec("context", FactValue.ENUM, enum=DuelContext), FactSpec("end", FactValue.ENUM, enum=DuelEnd)),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "tools.mortal.challenge_to_duel",
        G.SINGLE_COMBAT,
        "{actor} challenged {opponent} to a duel of {context}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.OPPONENT, frozenset({E.MORTAL}))),
        facts=(FactSpec("context", FactValue.ENUM, enum=DuelContext), FactSpec("end", FactValue.ENUM, enum=DuelEnd, required=False)),
        place=PlaceRule.NONE,
        clock=C.INSTANT,
    ),
)
