from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.cosmography import PhenomenonRhythm
from aerona.domain.enums.dominion import CreatureDeed
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule
from aerona.domain.enums.records import ProcessClock as C
from aerona.domain.enums.records import ProcessGroup as G

KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "parley.burial",
        G.DIPLOMACY,
        "{subject} paused the war after {battles:battle|battles} to bury their dead.",
        roles=(RoleSpec(R.SUBJECT, many=True),),
        facts=(FactSpec("war", FactValue.NODE), FactSpec("battles", FactValue.NUMBER, unit=FactUnit.COUNT)),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "army.detachment_cut",
        G.BATTLES,
        "A detachment of {subject} was cut off from its army.",
        roles=(RoleSpec(R.SUBJECT),),
        place=PlaceRule.NONE,
        clock=C.MARCH,
    ),
    IncidentKindSpec(
        "dominion.creature_carry_messages",
        G.GODS,
        "{actor}, beast of {patron}, carried the word of its god{target:? to #}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PATRON), RoleSpec(R.TARGET, required=False)),
        facts=(FactSpec("deed", FactValue.ENUM, enum=CreatureDeed),),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.PHASE,
    ),
    IncidentKindSpec(
        "dominion.creature_teach",
        G.GODS,
        "{actor}, beast of {patron}, taught the folk{target:? of #}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PATRON), RoleSpec(R.TARGET, required=False)),
        facts=(FactSpec("deed", FactValue.ENUM, enum=CreatureDeed),),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.PHASE,
    ),
    IncidentKindSpec(
        "dominion.creature_trade",
        G.GODS,
        "{actor}, beast of {patron}, traded with the folk{target:? of #}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PATRON), RoleSpec(R.TARGET, required=False)),
        facts=(FactSpec("deed", FactValue.ENUM, enum=CreatureDeed),),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.PHASE,
    ),
    IncidentKindSpec(
        "faith.charity",
        G.PEOPLES,
        "{givers:giver|givers} among the followers of {actor} gave away {given:point|points} of their wealth to those in need.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.MEMBER, many=True)),
        facts=(FactSpec("givers", FactValue.NUMBER, FactUnit.PEOPLE), FactSpec("given", FactValue.NUMBER, FactUnit.WEALTH_POINTS)),
        clock=C.MARCH,
    ),
    IncidentKindSpec(
        "faith.pilgrim_zeal",
        G.PEOPLES,
        "{pilgrims:follower|followers} of {authority} left everything for a holy journey.",
        roles=(RoleSpec(R.AUTHORITY), RoleSpec(R.MEMBER, many=True), RoleSpec(R.DESTINATION, required=False)),
        facts=(FactSpec("pilgrims", FactValue.NUMBER, FactUnit.PEOPLE),),
        clock=C.MARCH,
    ),
    IncidentKindSpec(
        "feud.woke",
        G.SINGLE_COMBAT,
        "The feud between {actor} and {opponent} woke after {quiet:epoch|epochs} of quiet.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.OPPONENT)),
        facts=(FactSpec("quiet", FactValue.NUMBER, FactUnit.COUNT),),
        place=PlaceRule.NONE,
        clock=C.PHASE,
    ),
    IncidentKindSpec(
        "mantle.contested",
        G.GODS,
        "{actor} and {opponent} both claimed the mantle of {target}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.OPPONENT), RoleSpec(R.TARGET)),
        place=PlaceRule.NONE,
        clock=C.PHASE,
    ),
    IncidentKindSpec(
        "outer.dead_returned",
        G.GODS,
        "{subject} came back from death by the bargain of {patron} with {actor}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.SUBJECT), RoleSpec(R.PATRON)),
        place=PlaceRule.NONE,
        clock=C.PHASE,
    ),
    IncidentKindSpec(
        "phenomenon.arrived",
        G.NATURE,
        "{subject} came to {place}, as its rhythm brings it: {rhythm}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PLACE)),
        facts=(FactSpec("rhythm", FactValue.ENUM, enum=PhenomenonRhythm),),
        place=PlaceRule.REQUIRED,
        clock=C.PHASE,
    ),
)
