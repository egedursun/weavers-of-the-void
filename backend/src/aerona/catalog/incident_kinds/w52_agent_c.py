from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.collective import FormativeKind
from aerona.domain.enums.demography import InheritanceCustom
from aerona.domain.enums.mind import ActKind, EthicalStance
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule
from aerona.domain.enums.records import ProcessClock as C
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import MobilityEvent

KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "ethics.act_judged",
        G.SOCIAL,
        "{actor} committed {act}, which their own people hold {stance}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.VICTIM, required=False)),
        facts=(FactSpec("act", FactValue.ENUM, enum=ActKind), FactSpec("stance", FactValue.ENUM, enum=EthicalStance)),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "renown.gained",
        G.SOCIAL,
        "{subject} won renown for {axis} among {witness}, who now hold it at {value}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.WITNESS)),
        facts=(FactSpec("axis", FactValue.ENUM, enum=ReputationAxis), FactSpec("value", FactValue.NUMBER, FactUnit.PERCENT)),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "inheritance.will_read",
        G.SOCIAL,
        "The will of {predecessor} was read, naming {heirs:heir|heirs}: {heir}.",
        roles=(RoleSpec(R.PREDECESSOR), RoleSpec(R.HEIR, required=False, many=True)),
        facts=(FactSpec("heirs", FactValue.NUMBER, FactUnit.COUNT),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "inheritance.will_contested",
        G.SOCIAL,
        "{accuser}, left out of the will of {predecessor}, contested it; set aside: {set_aside}; found forged: {forged}.",
        roles=(RoleSpec(R.PREDECESSOR), RoleSpec(R.ACCUSER)),
        facts=(FactSpec("set_aside", FactValue.NUMBER, FactUnit.COUNT), FactSpec("forged", FactValue.NUMBER, FactUnit.COUNT)),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "tools.mortal.make_will",
        G.SOCIAL,
        "{actor} made a will naming {heirs:heir|heirs}: {heir}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.HEIR, many=True)),
        facts=(FactSpec("heirs", FactValue.NUMBER, FactUnit.COUNT),),
        place=PlaceRule.NONE,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "life.class_changed",
        G.SOCIAL,
        "{subject} was moved from {from_class} to {to_class}: {event}, having {cause}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PLACE, required=False)),
        facts=(
            FactSpec("event", FactValue.ENUM, enum=MobilityEvent),
            FactSpec("from_class", FactValue.ENUM, enum=SocialClass),
            FactSpec("to_class", FactValue.ENUM, enum=SocialClass),
            FactSpec("cause", FactValue.NAME),
        ),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "generation.formed",
        G.SOCIAL,
        "The generation of {place} born in epoch {born} was marked by {kind}.",
        roles=(RoleSpec(R.PLACE),),
        facts=(FactSpec("kind", FactValue.ENUM, enum=FormativeKind), FactSpec("born", FactValue.NUMBER, FactUnit.NONE)),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "demography.orphans",
        G.SOCIAL,
        "{orphans} children of {place} were left without parents.",
        roles=(RoleSpec(R.PLACE),),
        facts=(FactSpec("orphans", FactValue.NUMBER, FactUnit.PEOPLE),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "demography.displaced",
        G.SOCIAL,
        "{displaced} who had lost their homes came to press on {host}.",
        roles=(RoleSpec(R.HOST),),
        facts=(FactSpec("displaced", FactValue.NUMBER, FactUnit.PEOPLE),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "inheritance.disputed",
        G.SOCIAL,
        "{accuser} disputed the passing of what {predecessor} held to {heir} by {custom}.",
        roles=(RoleSpec(R.PREDECESSOR), RoleSpec(R.HEIR), RoleSpec(R.ACCUSER)),
        facts=(FactSpec("custom", FactValue.ENUM, enum=InheritanceCustom),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
)
