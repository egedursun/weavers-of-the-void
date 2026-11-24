from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.geology import DeepPassageState
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.records import FactValue, PlaceRule
from aerona.domain.enums.records import ProcessGroup as G

KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "route.passage_cut",
        G.EXCHANGE,
        "{subject} was cut below {place}: the passage toward {destination} is {state}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PLACE), RoleSpec(R.DESTINATION)),
        facts=(FactSpec("state", FactValue.ENUM, enum=DeepPassageState),),
        place=PlaceRule.REQUIRED,
    ),
    IncidentKindSpec(
        "route.passage_reopened",
        G.EXCHANGE,
        "The passages of {subject} below {place} opened again, and its trade moved once more.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PLACE)),
        place=PlaceRule.REQUIRED,
    ),
)
