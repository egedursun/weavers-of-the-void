from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.ecology import AwakeningTrigger
from aerona.domain.enums.entity import EntityType as E
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.records import FactUnit as U
from aerona.domain.enums.records import FactValue, PlaceRule
from aerona.domain.enums.records import ProcessClock as C
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.society import KnowledgeBranch

BEING = frozenset({E.COSMIC_BEING})

KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "being.woke",
        G.COSMOS,
        "{subject} woke from its slumber on {place}, stirred by {trigger}.",
        roles=(RoleSpec(R.SUBJECT, BEING), RoleSpec(R.PLACE)),
        facts=(FactSpec("trigger", FactValue.ENUM, enum=AwakeningTrigger), FactSpec("might", FactValue.NUMBER, U.STRENGTH)),
        place=PlaceRule.NONE,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "being.world_answered",
        G.COSMOS,
        "{subject} answered {battles:battle|battles} fought on it, and every town on {place} lost {loss} prosperity.",
        roles=(RoleSpec(R.SUBJECT, BEING), RoleSpec(R.PLACE)),
        facts=(FactSpec("battles", FactValue.NUMBER, U.COUNT), FactSpec("loss", FactValue.NUMBER, U.PERCENT)),
        place=PlaceRule.NONE,
        clock=C.PHASE,
        terms=True,
    ),
    IncidentKindSpec(
        "being.world_bargained",
        G.COSMOS,
        "{subject} kept its bargain with the {communities:community|communities} on {place} that worship it, giving each {gift} prosperity.",
        roles=(RoleSpec(R.SUBJECT, BEING), RoleSpec(R.PLACE)),
        facts=(FactSpec("communities", FactValue.NUMBER, U.COUNT), FactSpec("gift", FactValue.NUMBER, U.PERCENT)),
        place=PlaceRule.NONE,
        clock=C.PHASE,
        terms=True,
    ),
    IncidentKindSpec(
        "being.lore_shared",
        G.KNOWLEDGE,
        "{target} studied {subject} and rose to level {level} in {branch}.",
        roles=(RoleSpec(R.SUBJECT, BEING), RoleSpec(R.TARGET)),
        facts=(FactSpec("branch", FactValue.ENUM, enum=KnowledgeBranch), FactSpec("level", FactValue.NUMBER, U.KNOWLEDGE)),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.PHASE,
    ),
    IncidentKindSpec(
        "power.bound",
        G.FAITH,
        "The power of {subject}, of strength {strength}, was bound by another's hold and lay quiet.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(FactSpec("strength", FactValue.NUMBER, U.STRENGTH),),
        place=PlaceRule.NONE,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "power.transferred",
        G.FAITH,
        "{actor} took a power from {victim}; it came to {actor} with strength {strength}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.VICTIM)),
        facts=(FactSpec("strength", FactValue.NUMBER, U.STRENGTH),),
        place=PlaceRule.NONE,
        clock=C.INSTANT,
        terms=True,
    ),
    IncidentKindSpec(
        "gifted.conscripted",
        G.LAW,
        "{actor} called {subject}, gifted with a power of strength {strength}, to serve under its law of sources.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.ACTOR)),
        facts=(FactSpec("strength", FactValue.NUMBER, U.STRENGTH),),
        place=PlaceRule.NONE,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "truth.relocated",
        G.KNOWLEDGE,
        "The keepers of {truth} moved {subject} to a new refuge in {destination}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.DESTINATION)),
        facts=(FactSpec("truth", FactValue.NAME),),
        place=PlaceRule.NONE,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "line.crossed_wild",
        G.NATURE,
        "{line} crossed with its wild kin, {subject}, moving their fit by {fit} across {ranges} lands.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(FactSpec("line", FactValue.NAME), FactSpec("fit", FactValue.NUMBER, U.PERCENT), FactSpec("ranges", FactValue.NUMBER, U.COUNT)),
        place=PlaceRule.NONE,
        clock=C.PHASE,
        terms=True,
    ),
    IncidentKindSpec(
        "relic.restored",
        G.MAKING,
        "{subject} was studied and repaired until it worked again for {owner}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.OWNER, required=False)),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.PHASE,
    ),
    IncidentKindSpec(
        "relic.dismantled",
        G.MAKING,
        "{owner} took {subject} apart for its parts, gaining {salvage} coin and what its making taught.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.OWNER, required=False)),
        facts=(FactSpec("salvage", FactValue.NUMBER, U.COIN),),
        place=PlaceRule.NONE,
        clock=C.INSTANT,
    ),
)
