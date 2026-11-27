from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.affliction import ChangeSign, CharmKind, CureKind, PackageKind
from aerona.domain.enums.agrarian import NutrientKind
from aerona.domain.enums.arcana import RiteEnd
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.constructs import OrderCondition, OrderKind
from aerona.domain.enums.customs import CoopPurpose, EvidenceKind, MemberRight, Membership, Naturalisation
from aerona.domain.enums.demography import FuneralCustom
from aerona.domain.enums.entity import EntityType as E
from aerona.domain.enums.environment import MovementMode, SoilKind, TerrainKind
from aerona.domain.enums.evolution import SuccessionStage
from aerona.domain.enums.faction import FactionActionKind, FactionGoalKind
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.domain.enums.law_depth import CourtLevel
from aerona.domain.enums.mind import ActKind, Emotion, GriefStage, SkillKind
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.mortal import CareerPath
from aerona.domain.enums.mythic import GeasLayer, GeasMode, QuestTrial
from aerona.domain.enums.polity import ClaimBasis, OathKind, OfficeKind
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule
from aerona.domain.enums.records import ProcessClock as C
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.records import StepAction as A
from aerona.domain.enums.regime import ClientRole
from aerona.domain.enums.statecraft import CouncilTask, CourtPosition, MandateKind

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
        "{subject} left{origin:? #} to settle the frontier at {destination}.",
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
        "{subject} tended {dead:body|bodies} by its funeral custom ({custom}), at a cost of {cost} to its common purse.",
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
        "death.funeral_unpaid",
        G.FAITH,
        "{subject} tended {dead:body|bodies} by its funeral custom ({custom}), with nothing spent from its common purse.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.PEOPLE})),),
        facts=(
            FactSpec("custom", FactValue.ENUM, enum=FuneralCustom),
            FactSpec("dead", FactValue.NUMBER, FactUnit.COUNT),
        ),
        steps=frozenset({A.SETTLE}),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "death.second_rite",
        G.FAITH,
        "{subject} held a second rite for {dead:none of its dead|# of its dead|# of its dead}; its cohesion stands at {cohesion}.",
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
        "The fortune of {patient} turned at strength {strength}; its source: {lean}.",
        roles=(RoleSpec(R.PATIENT),),
        facts=(FactSpec("lean", FactValue.ENUM, enum=FortuneSourceKind), FactSpec("strength", FactValue.NUMBER, FactUnit.PERCENT)),
        clock=C.COURSE,
    ),
    IncidentKindSpec(
        "affliction.transformed",
        G.BODY,
        "{patient} changed into a new body ({plan}); its sign: {trigger}.",
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
        "The grief of {subject} for {target} moved to a new stage: {stage}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.TARGET)),
        facts=(FactSpec("stage", FactValue.ENUM, enum=GriefStage),),
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "mind.emotion_felt",
        G.SOCIAL,
        "Moved by {emotion}, {subject} acted{target:? toward #}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.TARGET, required=False)),
        facts=(FactSpec("emotion", FactValue.ENUM, enum=Emotion),),
        clock=C.SEASON,
        legacy=True,
    ),
    IncidentKindSpec(
        "mind.curiosity_studied",
        G.SOCIAL,
        "Moved by curiosity, {subject} studied a skill: {skill}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})),),
        facts=(FactSpec("skill", FactValue.ENUM, enum=SkillKind),),
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "mind.compassion_gift",
        G.SOCIAL,
        "Moved by compassion, {subject} gave {target} {gift:wealth point|wealth points}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.TARGET)),
        facts=(FactSpec("gift", FactValue.NUMBER, FactUnit.WEALTH_POINTS),),
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "mind.contempt_humiliation",
        G.SOCIAL,
        "Moved by contempt, {subject} humiliated {target}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.TARGET)),
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
        "{actor} moved the grief of {subject} to a new stage: {stage}.",
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
        "{actor} lifted an affliction from {patient}; the cure: {cure}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.PATIENT)),
        facts=(FactSpec("cure", FactValue.ENUM, enum=CureKind),),
        steps=frozenset({A.TREAT}),
    ),
    IncidentKindSpec(
        "tools.mortal.choose_path",
        G.SOCIAL,
        "{subject} chose a path in life: {path}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})),),
        facts=(FactSpec("path", FactValue.ENUM, enum=CareerPath),),
    ),
    IncidentKindSpec(
        "tools.mortal.improve_soil",
        G.NATURE,
        "{actor} worked the {soil} soil of {place}; its nutrient ({nutrient}) now stands at {stock}.",
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
        "{actor} moved {member} {regions:region|regions} toward {destination}; way of travel: {mode}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.MEMBER, frozenset({E.ARMY})), RoleSpec(R.DESTINATION)),
        facts=(FactSpec("mode", FactValue.ENUM, enum=MovementMode), FactSpec("regions", FactValue.NUMBER, FactUnit.COUNT)),
        place=PlaceRule.REQUIRED,
        clock=C.MARCH,
    ),
)


STATECRAFT: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "council.task",
        G.LAW,
        "{actor}, {office} of {authority}, took up a task: {task}.",
        roles=(RoleSpec(R.AUTHORITY), RoleSpec(R.ACTOR, frozenset({E.MORTAL}))),
        facts=(FactSpec("office", FactValue.ENUM, enum=OfficeKind), FactSpec("task", FactValue.ENUM, enum=CouncilTask)),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "mandate.issued",
        G.LAW,
        "{authority} issued a mandate ({mandate}){subject:? on #}, to stand until epoch {until}.",
        roles=(RoleSpec(R.AUTHORITY), RoleSpec(R.SUBJECT, required=False), RoleSpec(R.ACTOR, required=False)),
        facts=(FactSpec("mandate", FactValue.ENUM, enum=MandateKind), FactSpec("until", FactValue.NUMBER, FactUnit.COUNT)),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "court.jest",
        G.SOCIAL,
        "{actor} mocked {target} before the court of {authority}, and the mockery was let stand; the seat grew calmer by {calm}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.TARGET), RoleSpec(R.AUTHORITY)),
        facts=(FactSpec("calm", FactValue.NUMBER, FactUnit.PERCENT),),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "court.jest_silenced",
        G.SOCIAL,
        "{actor} mocked {target} before the court of {authority} and was silenced; the seat grew angrier by {calm}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.TARGET), RoleSpec(R.AUTHORITY)),
        facts=(FactSpec("calm", FactValue.NUMBER, FactUnit.PERCENT),),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "court.foretold",
        G.FAITH,
        "{actor} read the signs for the court of {authority}, and the realm's standing moved by {sway}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.AUTHORITY)),
        facts=(FactSpec("sway", FactValue.NUMBER, FactUnit.PERCENT),),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "court.jurisdiction_disputed",
        G.LAW,
        "Courts of two levels, {first} and {second}, claimed the case of {accused} in {authority}, and it went before the high court.",
        roles=(RoleSpec(R.AUTHORITY), RoleSpec(R.ACCUSED)),
        facts=(FactSpec("first", FactValue.ENUM, enum=CourtLevel), FactSpec("second", FactValue.ENUM, enum=CourtLevel)),
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "patronage.bound",
        G.SOCIAL,
        "{member} became the {role} client of {patron}.",
        roles=(RoleSpec(R.PATRON), RoleSpec(R.MEMBER, frozenset({E.MORTAL}))),
        facts=(FactSpec("role", FactValue.ENUM, enum=ClientRole),),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "membership.gained",
        G.LAW,
        "{subject} became a citizen of {authority} by {way}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.AUTHORITY), RoleSpec(R.SPOUSE, required=False)),
        facts=(FactSpec("way", FactValue.ENUM, enum=Naturalisation),),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "claim.made",
        G.LAW,
        "{actor} came to hold a claim of strength {strength} to rule {authority}; its basis: {basis}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.AUTHORITY), RoleSpec(R.PATRON, required=False)),
        facts=(FactSpec("basis", FactValue.ENUM, enum=ClaimBasis), FactSpec("strength", FactValue.NUMBER, FactUnit.PERCENT)),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "succession.designated",
        G.LAW,
        "{actor} named {successor} heir to {authority}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.SUCCESSOR, frozenset({E.MORTAL})), RoleSpec(R.AUTHORITY)),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "oath.broken",
        G.LAW,
        "{actor} broke the {oath} oath before the courts{authority:? of #} in the case{accused:? of #}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.AUTHORITY, required=False), RoleSpec(R.ACCUSED, required=False)),
        facts=(FactSpec("oath", FactValue.ENUM, enum=OathKind),),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "faction.acted",
        G.SOCIAL,
        "{actor} set out to {action}{target:?, aimed at #}, pressing for {goal}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.TARGET, required=False)),
        facts=(FactSpec("action", FactValue.ENUM, enum=FactionActionKind), FactSpec("goal", FactValue.ENUM, enum=FactionGoalKind)),
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "faction.goal_met",
        G.SOCIAL,
        "{actor} won what it pressed for: {goal}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.TARGET, required=False)),
        facts=(FactSpec("goal", FactValue.ENUM, enum=FactionGoalKind),),
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "law.right_changed",
        G.LAW,
        "{authority} changed whether those of {category} standing hold the right of {right}.",
        roles=(RoleSpec(R.AUTHORITY), RoleSpec(R.ACTOR, required=False)),
        facts=(
            FactSpec("category", FactValue.ENUM, enum=Membership),
            FactSpec("right", FactValue.ENUM, enum=MemberRight),
        ),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "tools.mortal.appoint_court",
        G.LAW,
        "{actor} made {target} the {position} of the court of {authority}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.TARGET, frozenset({E.MORTAL})), RoleSpec(R.AUTHORITY)),
        facts=(FactSpec("position", FactValue.ENUM, enum=CourtPosition),),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "tools.mortal.take_client",
        G.SOCIAL,
        "{patron} took {member} as a client ({role}).",
        roles=(RoleSpec(R.PATRON, frozenset({E.MORTAL})), RoleSpec(R.MEMBER, frozenset({E.MORTAL}))),
        facts=(FactSpec("role", FactValue.ENUM, enum=ClientRole),),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "tools.mortal.press_claim",
        G.LAW,
        "{actor} pressed a claim to rule {authority} (basis: {basis}); it now stands at {strength}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.AUTHORITY)),
        facts=(FactSpec("basis", FactValue.ENUM, enum=ClaimBasis), FactSpec("strength", FactValue.NUMBER, FactUnit.PERCENT)),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "tools.mortal.found_coop",
        G.SOCIAL,
        "{actor} led {product} to pool its members' means as a cooperative for {purpose}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.PRODUCT)),
        facts=(FactSpec("purpose", FactValue.ENUM, enum=CoopPurpose),),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "tools.mortal.testify",
        G.LAW,
        "{actor} gave {evidence} evidence in the case{accused:? against #}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.ACCUSED, required=False)),
        facts=(FactSpec("evidence", FactValue.ENUM, enum=EvidenceKind),),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "tools.mortal.set_faction_goal",
        G.SOCIAL,
        "{actor} set their faction to press for {goal}{target:?, aimed at #}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.TARGET, required=False)),
        facts=(FactSpec("goal", FactValue.ENUM, enum=FactionGoalKind),),
        clock=C.INSTANT,
    ),
)


ARCANA: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "rite.ended",
        G.KNOWLEDGE,
        "The working of {subject}{target:? on #} came to its end: {end}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.RITE})), RoleSpec(R.TARGET, required=False)),
        facts=(FactSpec("end", FactValue.ENUM, enum=RiteEnd),),
        clock=C.PHASE,
    ),
    IncidentKindSpec(
        "quest.trial",
        G.FAITH,
        "{actor} met a trial of {trial} on the path of the myth {passed:and failed it|and passed it|and passed it}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})),),
        facts=(FactSpec("trial", FactValue.ENUM, enum=QuestTrial), FactSpec("passed", FactValue.NUMBER, FactUnit.COUNT)),
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "geas.laid",
        G.FAITH,
        "A geas was laid on {subject}{origin:? by #} (source: {layer}): {mode} of {act}.",
        roles=(RoleSpec(R.SUBJECT, frozenset({E.MORTAL})), RoleSpec(R.ORIGIN, required=False)),
        facts=(
            FactSpec("layer", FactValue.ENUM, enum=GeasLayer),
            FactSpec("mode", FactValue.ENUM, enum=GeasMode),
            FactSpec("act", FactValue.ENUM, enum=ActKind),
        ),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "orders.given",
        G.MAKING,
        "{subject} was given an order{authority:? by #}: {order}{target:?, aimed at #}, kept {condition}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.AUTHORITY, required=False), RoleSpec(R.TARGET, required=False)),
        facts=(FactSpec("order", FactValue.ENUM, enum=OrderKind), FactSpec("condition", FactValue.ENUM, enum=OrderCondition)),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "orders.lapsed",
        G.MAKING,
        "An order of {subject} lapsed: {order}, kept {condition}.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(FactSpec("order", FactValue.ENUM, enum=OrderKind), FactSpec("condition", FactValue.ENUM, enum=OrderCondition)),
        clock=C.PHASE,
    ),
    IncidentKindSpec(
        "orders.seized",
        G.MAKING,
        "{owner} spoke the true name of {subject} and it answered to no other.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.OWNER)),
        place=PlaceRule.WHEN_KNOWN,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "worship.bargain",
        G.FAITH,
        "{subject} bargained with {patron} by offering; {answered:no bargain was|# bargain was|# bargains were} answered and "
        "{unanswered:none went|# went|# went} unanswered.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PATRON)),
        facts=(FactSpec("answered", FactValue.NUMBER, FactUnit.COUNT), FactSpec("unanswered", FactValue.NUMBER, FactUnit.COUNT)),
        clock=C.PHASE,
    ),
    IncidentKindSpec(
        "tools.mortal.lay_geas_on_kin",
        G.FAITH,
        "{actor} laid a geas on {target} by the word of kin: {mode} of {act}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})), RoleSpec(R.TARGET, frozenset({E.MORTAL}))),
        facts=(FactSpec("mode", FactValue.ENUM, enum=GeasMode), FactSpec("act", FactValue.ENUM, enum=ActKind)),
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "tools.mortal.swear_geas",
        G.FAITH,
        "{actor} swore a geas upon itself: {mode} of {act}.",
        roles=(RoleSpec(R.ACTOR, frozenset({E.MORTAL})),),
        facts=(FactSpec("mode", FactValue.ENUM, enum=GeasMode), FactSpec("act", FactValue.ENUM, enum=ActKind)),
        clock=C.INSTANT,
    ),
)

KINDS: tuple[IncidentKindSpec, ...] = (*CAREERS, *DEATHS, *PACKAGES, *MINDS, *TOOLS, *LAND, *TRAVEL, *STATECRAFT, *ARCANA)
