from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.affliction import ChangeSign, CharmKind, CureKind, PackageKind
from aerona.domain.enums.agrarian import NutrientKind
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.demography import FuneralCustom
from aerona.domain.enums.entity import EntityType as E
from aerona.domain.enums.environment import MovementMode, SoilKind, TerrainKind
from aerona.domain.enums.evolution import SuccessionStage
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.domain.enums.mind import Emotion, GriefStage
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.mortal import CareerPath
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule
from aerona.domain.enums.records import ProcessClock as C
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.records import StepAction as A

CAREERS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "career.lost_at_sea",
        G.SOCIAL,
        "{subject} went to sea and did not come back.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})),),
        steps=frozenset({A.DIE}),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "career.entered_service",
        G.SOCIAL,
        "{subject} entered the service of {target}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.TARGET)),
        steps=frozenset({A.ENTER}),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "career.settled_frontier",
        G.SOCIAL,
        "{subject} left {origin} to settle the frontier at {destination}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.ORIGIN, required=False), RoleSpec(R.DESTINATION)),
        steps=frozenset({A.DEPART, A.ARRIVE}),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.MARCH,
    ),
)

DEATHS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "death.funeral",
        G.FAITH,
        "{subject} laid {dead:body|bodies} to rest by {custom}, at a cost of {cost}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.PEOPLE})),),
        facts=(
            FactSpec("custom", FactValue.ENUM, enum=FuneralCustom),
            FactSpec("dead", FactValue.NUMBER, FactUnit.COUNT),
            FactSpec("cost", FactValue.NUMBER, FactUnit.COIN),
        ),
        steps=frozenset({A.SETTLE}),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "death.second_rite",
        G.FAITH,
        "{subject} gathered the bones of {dead:none of its dead|# of its dead|# of its dead} in a second rite; its cohesion stands at {cohesion}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.PEOPLE})),),
        facts=(FactSpec("dead", FactValue.NUMBER, FactUnit.COUNT), FactSpec("cohesion", FactValue.NUMBER, FactUnit.PERCENT)),
        steps=frozenset({A.SETTLE}),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.SEASON,
    ),
)

PACKAGES: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "affliction.fortune_turned",
        G.BODY,
        "The fortune of {patient} turned to {lean}, at strength {strength}.",
        roles=(RoleSpec(R.PATIENT),),
        facts=(FactSpec("lean", FactValue.ENUM, enum=FortuneSourceKind), FactSpec("strength", FactValue.NUMBER, FactUnit.PERCENT)),
        clock=C.COURSE,
    ),
    IncidentKindSpec(
        "affliction.transformed",
        G.BODY,
        "{patient} changed into a body that is {plan}, by the sign of {trigger}.",
        roles=(RoleSpec(R.PATIENT),),
        facts=(
            FactSpec("plan", FactValue.ENUM, enum=BodyPlan),
            FactSpec("trigger", FactValue.ENUM, enum=ChangeSign),
            FactSpec("mind_kept", FactValue.NUMBER, FactUnit.COUNT),
        ),
        steps=frozenset({A.FALL_ILL}),
        clock=C.COURSE,
    ),
    IncidentKindSpec(
        "affliction.charmed",
        G.BODY,
        "{patient} was bound to {target} by a charm of {charm}.",
        roles=(RoleSpec(R.PATIENT), RoleSpec(R.TARGET)),
        facts=(FactSpec("charm", FactValue.ENUM, enum=CharmKind),),
        clock=C.COURSE,
    ),
    IncidentKindSpec(
        "affliction.charm_broken",
        G.BODY,
        "The charm of {charm} on {patient} broke.",
        roles=(RoleSpec(R.PATIENT), RoleSpec(R.ACTOR, required=False)),
        facts=(FactSpec("charm", FactValue.ENUM, enum=CharmKind), FactSpec("found", FactValue.NUMBER, FactUnit.COUNT)),
        steps=frozenset({A.RECOVER}),
        clock=C.COURSE,
    ),
    IncidentKindSpec(
        "affliction.charm_renewed",
        G.BODY,
        "{actor} paid {cost} to renew the charm of {charm} on {patient}.",
        roles=(RoleSpec(R.PATIENT), RoleSpec(R.ACTOR)),
        facts=(FactSpec("charm", FactValue.ENUM, enum=CharmKind), FactSpec("cost", FactValue.NUMBER, FactUnit.COIN)),
        steps=frozenset({A.PAY}),
        clock=C.COURSE,
    ),
)

MINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "mind.grief_stage",
        G.SOCIAL,
        "The grief of {subject} for {target} came to {stage}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.TARGET)),
        facts=(FactSpec("stage", FactValue.ENUM, enum=GriefStage),),
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "mind.emotion_felt",
        G.SOCIAL,
        "Moved by {emotion}, {subject} acted toward {target}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.TARGET, required=False)),
        facts=(FactSpec("emotion", FactValue.ENUM, enum=Emotion),),
        clock=C.SEASON,
    ),
)

TOOLS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "tools.son.stir_emotion",
        G.SOCIAL,
        "{actor} stirred {emotion} in {subject}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.SUBJECT)),
        facts=(FactSpec("emotion", FactValue.ENUM, enum=Emotion),),
    ),
    IncidentKindSpec(
        "tools.son.ease_grief",
        G.SOCIAL,
        "{actor} moved the grief of {subject} to {stage}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.SUBJECT)),
        facts=(FactSpec("stage", FactValue.ENUM, enum=GriefStage),),
    ),
    IncidentKindSpec(
        "tools.son.curse_with",
        G.BODY,
        "{actor} cursed {patient} with {package}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PATIENT)),
        facts=(FactSpec("package", FactValue.ENUM, enum=PackageKind),),
    ),
    IncidentKindSpec(
        "tools.son.bless_with",
        G.BODY,
        "{actor} gave {patient} {package}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PATIENT)),
        facts=(FactSpec("package", FactValue.ENUM, enum=PackageKind),),
    ),
    IncidentKindSpec(
        "tools.mortal.bind_with_charm",
        G.SOCIAL,
        "{actor} gave {target} a charm of {charm}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.TARGET)),
        facts=(FactSpec("charm", FactValue.ENUM, enum=CharmKind),),
    ),
    IncidentKindSpec(
        "tools.mortal.lift_affliction",
        G.BODY,
        "{actor} lifted an affliction from {patient} by {cure}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.PATIENT)),
        facts=(FactSpec("cure", FactValue.ENUM, enum=CureKind),),
        steps=frozenset({A.TREAT}),
    ),
    IncidentKindSpec(
        "tools.mortal.choose_path",
        G.SOCIAL,
        "{subject} took up the path of {path}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})),),
        facts=(FactSpec("path", FactValue.ENUM, enum=CareerPath),),
    ),
    IncidentKindSpec(
        "tools.mortal.improve_soil",
        G.NATURE,
        "{actor} worked the {soil} soil of {place}; its {nutrient} now stands at {stock}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.PLACE)),
        facts=(
            FactSpec("soil", FactValue.ENUM, enum=SoilKind),
            FactSpec("nutrient", FactValue.ENUM, enum=NutrientKind),
            FactSpec("stock", FactValue.NUMBER, FactUnit.COUNT),
        ),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
)

LAND: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "terrain.changed",
        G.NATURE,
        "The land of {place} turned from {before} to {after}.",
        roles=(RoleSpec(R.PLACE),),
        facts=(FactSpec("before", FactValue.ENUM, enum=TerrainKind), FactSpec("after", FactValue.ENUM, enum=TerrainKind)),
        place=PlaceRule.REQUIRED,
        clock=C.YEAR,
    ),
    IncidentKindSpec(
        "succession.advanced",
        G.NATURE,
        "The growth of {place} moved from {before} to {stage}.",
        roles=(RoleSpec(R.PLACE),),
        facts=(FactSpec("before", FactValue.ENUM, enum=SuccessionStage), FactSpec("stage", FactValue.ENUM, enum=SuccessionStage)),
        place=PlaceRule.REQUIRED,
        clock=C.YEAR,
    ),
)

TRAVEL: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "travel.mode_used",
        G.MOVEMENT,
        "{actor} moved {member} {regions:region|regions} toward {destination}, going {mode}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.MEMBER, frozenset({E.ARMY})), RoleSpec(R.DESTINATION)),
        facts=(FactSpec("mode", FactValue.ENUM, enum=MovementMode), FactSpec("regions", FactValue.NUMBER, FactUnit.COUNT)),
        place=PlaceRule.REQUIRED,
        clock=C.MARCH,
    ),
)

KINDS: tuple[IncidentKindSpec, ...] = (*CAREERS, *DEATHS, *PACKAGES, *MINDS, *TOOLS, *LAND, *TRAVEL)
