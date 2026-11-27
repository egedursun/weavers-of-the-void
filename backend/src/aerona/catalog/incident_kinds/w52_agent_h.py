from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.crafts import Notation
from aerona.domain.enums.discovery import AnomalyKind, TheoryDomain
from aerona.domain.enums.entity import EntityType as E
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.operations import ExpeditionGround, ResolveKind
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule, StepAction
from aerona.domain.enums.records import ProcessClock as C
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.site import BattlefieldFeature, ExcavationRisk, ExcavationStage, SiteChallenge, SiteRoomKind

KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "numeracy.notation_adopted",
        G.KNOWLEDGE,
        "{subject} took up {notation} notation in place of {before}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.PEOPLE})),),
        facts=(
            FactSpec("notation", FactValue.ENUM, enum=Notation),
            FactSpec("before", FactValue.ENUM, enum=Notation),
            FactSpec("rank", FactValue.NUMBER, FactUnit.COUNT, required=False),
        ),
        steps=frozenset({StepAction.LEARN}),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "expedition.resolve",
        G.MOVEMENT,
        "Under strain on the way{destination:? to #}, {member} turned {resolve}.",
        roles=(RoleSpec(R.MEMBER, frozenset({E.MORTAL})), RoleSpec(R.DESTINATION, required=False)),
        facts=(
            FactSpec("resolve", FactValue.ENUM, enum=ResolveKind),
            FactSpec("stress", FactValue.NUMBER, FactUnit.NONE, required=False),
            FactSpec("virtue", FactValue.NUMBER, FactUnit.COUNT, required=False),
        ),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.MARCH,
    ),
    IncidentKindSpec(
        "expedition.discovery",
        G.MOVEMENT,
        "On a leg into the {ground}{destination:? of #}, {actor} made a discovery.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.DESTINATION, required=False)),
        facts=(
            FactSpec("ground", FactValue.ENUM, enum=ExpeditionGround),
            FactSpec("leg", FactValue.NUMBER, FactUnit.COUNT, required=False),
            FactSpec("charted", FactValue.NUMBER, FactUnit.KNOWLEDGE, required=False),
        ),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.MARCH,
    ),
    IncidentKindSpec(
        "site.challenge",
        G.MOVEMENT,
        "{actor} met the {challenge} of the {room} at {place}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.PLACE)),
        facts=(
            FactSpec("challenge", FactValue.ENUM, enum=SiteChallenge),
            FactSpec("room", FactValue.ENUM, enum=SiteRoomKind),
            FactSpec("passed", FactValue.NUMBER, FactUnit.COUNT, required=False),
        ),
        place=PlaceRule.REQUIRED,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "dig.risk",
        G.KNOWLEDGE,
        "The dig of {actor} at {place} met {risk} in its {stage}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.PLACE), RoleSpec(R.PATRON, required=False)),
        facts=(FactSpec("risk", FactValue.ENUM, enum=ExcavationRisk), FactSpec("stage", FactValue.ENUM, enum=ExcavationStage)),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "battlefield.ordnance",
        G.BATTLES,
        "Arms left on the field at {place} killed {dead:person|people} of {victim}.",
        roles=(RoleSpec(R.VICTIM), RoleSpec(R.PLACE)),
        facts=(
            FactSpec("feature", FactValue.ENUM, enum=BattlefieldFeature, required=False),
            FactSpec("dead", FactValue.NUMBER, FactUnit.PEOPLE),
            FactSpec("strength", FactValue.NUMBER, FactUnit.STRENGTH, required=False),
        ),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "theory.challenged",
        G.KNOWLEDGE,
        "{subject} was challenged in {witness}: {anomaly}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.THEORY})), RoleSpec(R.WITNESS), RoleSpec(R.PLACE, required=False)),
        facts=(
            FactSpec("anomaly", FactValue.ENUM, enum=AnomalyKind),
            FactSpec("domain", FactValue.ENUM, enum=TheoryDomain, required=False),
            FactSpec("weight", FactValue.NUMBER, FactUnit.COUNT, required=False),
        ),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.SEASON,
    ),
)
