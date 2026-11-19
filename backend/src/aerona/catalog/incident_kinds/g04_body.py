from enum import StrEnum
from typing import Any

from aerona.catalog.incident_kinds.body_lines import CONDITION_PHRASES, END_PHRASES, ILLNESSES, ONSET_STEPS, RESPONSE_WORDS, injury_line
from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.catalog.kinds.life_stages import LIFE_STAGES
from aerona.domain.enums.affliction import CureKind, PackageKind, Transmission
from aerona.domain.enums.body import BodyPart, BodyReading, ConditionKind, DamageType, HarmCause, InjuryKind, MaimedKind, MedicineTier
from aerona.domain.enums.chronicle import ChronicleKind as K
from aerona.domain.enums.chronicle import FeedCategory as F
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.demography import Sex
from aerona.domain.enums.disease import DiseaseVector, SpreadPath
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.faith import SpiritAlignment
from aerona.domain.enums.gathering import CollectionKind as C
from aerona.domain.enums.genetics import Locus
from aerona.domain.enums.industry import MethodKind
from aerona.domain.enums.living import CultivationMethod, HostPlacement, HostRelation, LineTrait
from aerona.domain.enums.made import AugmentKind, AugmentMake, AugmentSlot
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import CommanderTrait
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.mortal import CrimeKind, DeathCause, LifeStage, StressBreak
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.records import FactUnit as U
from aerona.domain.enums.records import FactValue, PlaceRule, ProcessClock
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.records import StepAction as A
from aerona.domain.enums.society import NaturalLaw, SocialClass

BIRTH_STEPS = frozenset({A.GO_INTO_LABOUR, A.GIVE_BIRTH, A.NAME_CHILD})
LOST_BIRTH_STEPS = frozenset({A.GO_INTO_LABOUR, A.LOSE_CHILD, A.DIE})


def role(kind: R, *, required: bool = True, many: bool = False) -> RoleSpec:
    return RoleSpec(kind, required=required, many=many)


def node(key: str, *, required: bool = True) -> FactSpec:
    return FactSpec(key, FactValue.NODE, required=required)


def number(key: str, unit: U, *, required: bool = True) -> FactSpec:
    return FactSpec(key, FactValue.NUMBER, unit, required=required)


def chosen(key: str, enum: type[StrEnum], *, required: bool = True) -> FactSpec:
    return FactSpec(key, FactValue.ENUM, enum=enum, required=required)


def named(key: str, *, required: bool = True) -> FactSpec:
    return FactSpec(key, FactValue.NAME, required=required)


def kind(key: str, template: str, *, roles: tuple[RoleSpec, ...] = (), facts: tuple[FactSpec, ...] = (), **extra: Any) -> IncidentKindSpec:
    return IncidentKindSpec(key, G.BODY, template, roles=roles, facts=facts, **extra)


BIRTH_FACTS = (
    number("stillbirth_chance", U.PERCENT, required=False),
    number("death_risk", U.PERCENT, required=False),
    number("hunger", U.PERCENT, required=False),
    chosen("medicine", MedicineTier, required=False),
    number("bearer_died", U.COUNT, required=False),
)
STRESS_FACTS = (chosen("break", StressBreak), number("stress", U.PERCENT))
LIVING_LINE = named("line")


def stress_break(key: str, template: str, roles: tuple[RoleSpec, ...] = (), facts: tuple[FactSpec, ...] = ()) -> IncidentKindSpec:
    return kind(f"stress.{key}", template, roles=(role(R.SUBJECT), *roles), facts=(*STRESS_FACTS, *facts))


def disease_origin(key: str, template: str, *, host: bool) -> IncidentKindSpec:
    roles = (role(R.SUBJECT), role(R.PLACE), role(R.ORIGIN, required=host), role(R.PATRON, required=False))
    facts = (chosen("vector", DiseaseVector), chosen("path", SpreadPath), number("lethality", U.PERCENT))
    return kind(key, template, roles=roles, facts=facts, place=PlaceRule.REQUIRED, collection=C.PLAGUE, feed=F.DISASTER, chronicle_kind=K.DISASTER)


def injury_kind(injury: InjuryKind) -> IncidentKindSpec:
    facts = (
        chosen("part", BodyPart),
        chosen("injury", InjuryKind),
        number("severity", U.SEVERITY),
        chosen("damage_type", DamageType),
        chosen("cause", HarmCause),
        number("digits_lost", U.COUNT),
    )
    return kind(f"injury.{injury.value}", injury_line(injury), roles=(role(R.PATIENT), role(R.ACTOR, required=False)), facts=facts, clock=ProcessClock.INSTANT)


CONDITION_STEPS = {"gained": A.FALL_ILL, "ended": A.RECOVER}


def condition_kind(verb: str, condition: ConditionKind, phrase: str) -> IncidentKindSpec:
    facts = (chosen("condition", ConditionKind), number("severity", U.SEVERITY))
    steps = frozenset({CONDITION_STEPS[verb]}) if condition in ILLNESSES else frozenset()
    return kind(
        f"condition.{verb}.{condition.value}", "{patient} " + phrase + ".", roles=(role(R.PATIENT),), facts=facts, clock=ProcessClock.COURSE, steps=steps
    )


def affliction_steps(package: PackageKind) -> frozenset[A]:
    return frozenset({ONSET_STEPS[package]}) if package in ONSET_STEPS else frozenset()


def life_kind(stage: LifeStage, reached: str) -> IncidentKindSpec:
    facts = (chosen("stage", LifeStage), number("age", U.YEARS), number("health", U.PERCENT))
    return kind(f"life.{stage.value}", "{subject} came into " + reached + ".", roles=(role(R.SUBJECT),), facts=facts, clock=ProcessClock.LIFE)


def tool(key: str, template: str, roles: tuple[RoleSpec, ...], facts: tuple[FactSpec, ...] = ()) -> IncidentKindSpec:
    return kind(f"tools.mortal.{key}", template, roles=roles, facts=facts)


KINDS: tuple[IncidentKindSpec, ...] = (
    *(
        kind(
            f"affliction.{package.value}",
            "{patient} now bears {package}.",
            roles=(role(R.PATIENT), role(R.ACTOR, required=False)),
            facts=(chosen("package", PackageKind), chosen("transmission", Transmission)),
            clock=ProcessClock.COURSE,
            steps=affliction_steps(package),
        )
        for package in PackageKind
    ),
    kind(
        "affliction.cured",
        "{patient} is freed of {package}.",
        roles=(role(R.PATIENT),),
        facts=(chosen("package", PackageKind), number("stage", U.COUNT)),
        steps=frozenset({A.RECOVER}),
    ),
    kind(
        "affliction.cured_by",
        "{patient} is freed of {package} by {cure}.",
        roles=(role(R.PATIENT),),
        facts=(chosen("package", PackageKind), number("stage", U.COUNT), chosen("cure", CureKind)),
        steps=frozenset({A.TREAT, A.RECOVER}),
    ),
    kind(
        "augment.installed",
        "{patient} took an augment: {kind}.",
        roles=(role(R.PATIENT), role(R.HEALER, required=False)),
        facts=(
            chosen("slot", AugmentSlot),
            chosen("kind", AugmentKind),
            chosen("make", AugmentMake),
            number("quality", U.PERCENT),
            number("integration", U.PERCENT),
            chosen("part", BodyPart, required=False),
        ),
        steps=frozenset({A.OPERATE}),
    ),
    kind(
        "augment.removed",
        "An augment, {kind}, was taken out of {patient}.",
        roles=(role(R.PATIENT),),
        facts=(chosen("slot", AugmentSlot), chosen("kind", AugmentKind), chosen("make", AugmentMake)),
    ),
    kind(
        "augment.rejected",
        "The body of {patient} rejected an augment: {kind}.",
        roles=(role(R.PATIENT),),
        facts=(chosen("slot", AugmentSlot), chosen("kind", AugmentKind), number("integration", U.PERCENT), number("strain", U.PERCENT)),
    ),
    kind(
        "births.child",
        "{child} was born to {parent}.",
        roles=(role(R.CHILD), role(R.PARENT, many=True), role(R.HEALER, required=False)),
        facts=(chosen("sex", Sex), number("twin", U.COUNT), number("lifespan", U.YEARS), *BIRTH_FACTS),
        steps=BIRTH_STEPS,
        clock=ProcessClock.INSTANT,
        feed=F.LIFE,
        chronicle_kind=K.BIRTH,
    ),
    kind(
        "births.stillborn",
        "The child of {parent} was stillborn.",
        roles=(role(R.PARENT, many=True), role(R.PATIENT), role(R.HEALER, required=False)),
        facts=BIRTH_FACTS,
        steps=LOST_BIRTH_STEPS,
        clock=ProcessClock.INSTANT,
        feed=F.LIFE,
        chronicle_kind=K.BIRTH,
    ),
    kind(
        "births.twins",
        "{parent} were given {children:child|children} at one birth: {child}.",
        roles=(role(R.PARENT, many=True), role(R.CHILD, many=True), role(R.HEALER, required=False)),
        facts=(number("children", U.COUNT), *BIRTH_FACTS),
        feed=F.LIFE,
        chronicle_kind=K.BIRTH,
    ),
    kind(
        "births.notable",
        "{subject} of {origin} came forward as {role:an}.",
        roles=(role(R.SUBJECT), role(R.ORIGIN)),
        facts=(chosen("social_class", SocialClass), chosen("role", MortalRole)),
    ),
    kind("births.ruler", "{successor} came to lead {subject}.", roles=(role(R.SUCCESSOR), role(R.SUBJECT)), facts=(chosen("role", MortalRole),)),
    kind(
        "births.village_ruin",
        "{actor} grew crowded; {migrants:settler|settlers} settled the ruin of {destination} and rebuilt it.",
        roles=(role(R.ACTOR), role(R.DESTINATION)),
        facts=(number("migrants", U.PEOPLE),),
        collection=C.FOUNDING,
    ),
    kind(
        "births.village",
        "{actor} grew crowded; {migrants:settler|settlers} founded {product} in {place}.",
        roles=(role(R.ACTOR), role(R.PRODUCT), role(R.PLACE)),
        facts=(number("migrants", U.PEOPLE), number("settlements_before", U.COUNT)),
        place=PlaceRule.REQUIRED,
        collection=C.FOUNDING,
    ),
    kind(
        "births.ethnogenesis",
        "Descended from {predecessor}, {origin} became a people of its own: {product}.",
        roles=(role(R.PRODUCT), role(R.ORIGIN), role(R.PREDECESSOR)),
        facts=(number("population", U.PEOPLE),),
    ),
    kind(
        "births.sapience",
        "A branch of the {origin} learned to speak and became a people: {product}.",
        roles=(role(R.PRODUCT), role(R.ORIGIN)),
        facts=(number("population", U.PEOPLE),),
    ),
    kind(
        "body.reader_taken",
        "Blinded, {teacher} took {learner} as a reader.",
        roles=(role(R.TEACHER), role(R.LEARNER)),
        facts=(number("intellect", U.STRENGTH),),
    ),
    kind(
        "body.ruler_set_aside",
        "{predecessor} was set aside, for the law asks for a ruler whole in body; {successor} came to rule.",
        roles=(role(R.PREDECESSOR), role(R.SUCCESSOR), role(R.AUTHORITY, required=False)),
        facts=(number("injuries", U.COUNT),),
    ),
    kind("body.maimed_cult", "{member}, maimed, found a welcome in {host}.", roles=(role(R.MEMBER), role(R.HOST)), facts=(number("chance", U.PERCENT),)),
    kind(
        "breeding.begun",
        "A long design, {plan_name}, began to steer the marriages of {subject}.",
        roles=(role(R.SUBJECT), role(R.AUTHORITY)),
        facts=(named("plan_name"), chosen("locus", Locus, required=False), number("target_share", U.PERCENT)),
    ),
    kind(
        "breeding.love",
        "{subject} married for love, against the long design of {opponent}.",
        roles=(role(R.SUBJECT), role(R.OPPONENT)),
        facts=(number("love_matches", U.COUNT),),
    ),
    kind(
        "cohort.scar_festival",
        "The maimed veterans of {subject} became a festival: {product}.",
        roles=(role(R.SUBJECT), role(R.PRODUCT)),
        facts=(number("veterans", U.PEOPLE), chosen("reading", BodyReading)),
    ),
    *(condition_kind("gained", condition, phrase) for condition, phrase in CONDITION_PHRASES.items()),
    *(condition_kind("ended", condition, phrase) for condition, phrase in END_PHRASES.items()),
    kind(
        "disease.army_carried",
        "The soldiers of {actor} came home and brought {instrument} with them to {destination}.",
        roles=(role(R.ACTOR), role(R.DESTINATION), role(R.INSTRUMENT)),
        facts=(number("chance", U.PERCENT), number("severity", U.PERCENT)),
        collection=C.PLAGUE,
        feed=F.DISASTER,
        chronicle_kind=K.DISASTER,
    ),
    kind(
        "disease.carrier_found",
        "Physicians found that {subject} carries {instrument} unseen.",
        roles=(role(R.SUBJECT), role(R.INSTRUMENT)),
        facts=(number("skill", U.KNOWLEDGE),),
        collection=C.PLAGUE,
    ),
    kind(
        "disease.carrier_seeded",
        "{subject} came to {destination}, and {instrument} came too.",
        roles=(role(R.SUBJECT), role(R.INSTRUMENT), role(R.DESTINATION)),
        facts=(number("severity", U.PERCENT), number("seeded", U.COUNT)),
        collection=C.PLAGUE,
        feed=F.DISASTER,
    ),
    kind(
        "disease.cure_found",
        "The learned of {actor} found a cure for {target}.",
        roles=(role(R.ACTOR), role(R.BENEFICIARY), role(R.TARGET)),
        facts=(number("points", U.COUNT), number("specimens", U.COUNT), number("prestige", U.STANDING)),
    ),
    kind(
        "disease.cure_sold",
        "{buyer} bought the cure for {target} that {seller} holds.",
        roles=(role(R.BUYER), role(R.SELLER), role(R.TARGET)),
        facts=(number("price", U.COIN),),
    ),
    disease_origin("disease.emerged", "A new sickness rose in {place}: {subject}, borne by {vector}.", host=False),
    disease_origin("disease.emerged_host", "A new sickness rose in {place}: {subject}, borne by {vector} and carried by {origin}.", host=True),
    disease_origin("disease.loosed", "A new sickness was loosed on {place}: {subject}, borne by {vector}.", host=False),
    disease_origin("disease.loosed_host", "A new sickness was loosed on {place}: {subject}, borne by {vector} and carried by {origin}.", host=True),
    kind(
        "disease.endemic",
        "{subject} never quite left {place}; it became a sickness of the land.",
        roles=(role(R.SUBJECT), role(R.PLACE)),
        facts=(number("load", U.PERCENT),),
        place=PlaceRule.REQUIRED,
        feed=F.DISASTER,
        chronicle_kind=K.DISASTER,
    ),
    kind(
        "disease.expelled",
        "{actor} sent {expelled:sick person|sick people} away to {destination} for fear of {instrument}.",
        roles=(role(R.ACTOR), role(R.DESTINATION), role(R.INSTRUMENT)),
        facts=(number("expelled", U.PEOPLE), number("stigma_reach", U.PERCENT)),
    ),
    kind("disease.hospital", "{actor} began to build {product}.", roles=(role(R.ACTOR), role(R.PRODUCT)), facts=(number("mercy", U.STANDING),)),
    kind(
        "disease.immune_escape",
        "{predecessor} changed past the immunity of {place}; {product} spreads where the old sickness could not.",
        roles=(role(R.PREDECESSOR), role(R.PRODUCT), role(R.PLACE)),
        facts=(number("immune_share", U.PERCENT),),
        collection=C.PLAGUE,
    ),
    *(
        kind(
            f"disease.plague_response.{response.value}",
            "Against {target}, {actor} " + words + ".",
            roles=(role(R.ACTOR), role(R.TARGET)),
            facts=(chosen("response", PlagueResponse),),
            collection=C.PLAGUE,
        )
        for response, words in RESPONSE_WORDS.items()
    ),
    kind(
        "disease.quarantine_riot",
        "The folk of {actor} rose against the quarantine.",
        roles=(role(R.ACTOR), role(R.INSTRUMENT)),
        facts=(number("unrest", U.PERCENT),),
        collection=C.RIOT,
    ),
    kind(
        "disease.spillover",
        "{subject} passed from {origin} to the folk of {destination}.",
        roles=(role(R.SUBJECT), role(R.ORIGIN), role(R.DESTINATION)),
        facts=(number("chance", U.PERCENT), number("abundance", U.PERCENT)),
        collection=C.PLAGUE,
    ),
    kind(
        "disease.strain",
        "In {place}, {predecessor} changed: {product} struck even those who had survived the old sickness.",
        roles=(role(R.PRODUCT), role(R.PREDECESSOR), role(R.PLACE)),
        facts=(number("severity", U.PERCENT), number("infected", U.PEOPLE)),
        collection=C.PLAGUE,
        feed=F.DISASTER,
        chronicle_kind=K.DISASTER,
    ),
    kind(
        "disease.tradition",
        "The survivors of {instrument} in {subject} began to keep {product}.",
        roles=(role(R.PRODUCT), role(R.SUBJECT), role(R.INSTRUMENT)),
        facts=(number("dead", U.PEOPLE),),
    ),
    kind(
        "genetics.resemblance",
        "Its kin came to know {subject} by sight; a mark of {locus} ran in the blood.",
        roles=(role(R.SUBJECT),),
        facts=(chosen("locus", Locus), number("share", U.PERCENT)),
    ),
    kind(
        "genetics.order_recruits",
        "{actor} tested the children of the town and took {learner}, gifted in {school}.",
        roles=(role(R.ACTOR), role(R.LEARNER)),
        facts=(chosen("school", MagicSchool),),
    ),
    kind(
        "healing.amputated",
        "{patient} lost a festering {part} to surgery and lived.",
        roles=(role(R.PATIENT), role(R.HEALER, required=False)),
        facts=(chosen("part", BodyPart), number("infected_epochs", U.COUNT), chosen("medicine", MedicineTier)),
        steps=frozenset({A.AMPUTATE}),
    ),
    kind(
        "healing.reattached",
        "The lost {part} of {patient} was made whole again by {healer}.",
        roles=(role(R.PATIENT), role(R.HEALER)),
        facts=(chosen("part", BodyPart), number("residual_loss", U.PERCENT)),
        steps=frozenset({A.OPERATE}),
    ),
    kind(
        "healing.tended",
        "The wounds of {patient} were tended.",
        roles=(role(R.PATIENT), role(R.HEALER, required=False)),
        facts=(number("wounds", U.COUNT), chosen("medicine", MedicineTier)),
        steps=frozenset({A.EXAMINE, A.SUTURE, A.SET_BONE, A.TREAT, A.EASE, A.WORSEN, A.RECOVER}),
    ),
    kind(
        "healing.prosthesis",
        "{patient} was fitted with {part:an} of {material}.",
        roles=(role(R.PATIENT), role(R.MAKER, required=False), role(R.PRODUCT, required=False)),
        facts=(chosen("part", BodyPart), chosen("material", MaterialKind), number("quality", U.PERCENT), number("restored", U.PERCENT)),
        steps=frozenset({A.FIT_PROSTHESIS}),
    ),
    kind(
        "healing.prosthesis_made",
        "{patient} was fitted with {part:an} of {material} made by {maker}.",
        roles=(role(R.PATIENT), role(R.MAKER), role(R.PRODUCT, required=False)),
        facts=(chosen("part", BodyPart), chosen("material", MaterialKind), number("quality", U.PERCENT), number("restored", U.PERCENT)),
        steps=frozenset({A.FIT_PROSTHESIS}),
    ),
    *(injury_kind(injury) for injury in InjuryKind),
    *(life_kind(stage, spec.reached) for stage, spec in LIFE_STAGES.items() if spec.reached is not None),
    kind(
        "life.native_people",
        "A people appeared of its own accord in {world}: {product}.",
        roles=(role(R.PRODUCT), role(R.PLACE)),
        facts=(node("world"), number("power", U.STRENGTH)),
        place=PlaceRule.REQUIRED,
    ),
    kind(
        "life.native_species",
        "The first species appeared in {world}: {product}.",
        roles=(role(R.PRODUCT), role(R.PLACE)),
        facts=(node("world"), number("danger", U.PERCENT)),
        place=PlaceRule.REQUIRED,
    ),
    kind(
        "living.blight",
        "A blight struck the plantings of {place}, where nothing else was grown.",
        roles=(role(R.PLACE),),
        facts=(number("harm", U.PERCENT), number("plantings", U.COUNT), named("line", required=False)),
        place=PlaceRule.REQUIRED,
    ),
    kind(
        "living.clone_people",
        "The clones of {origin} became a people: {product}.",
        roles=(role(R.PRODUCT), role(R.ORIGIN), role(R.MEMBER, many=True)),
        facts=(number("clones", U.COUNT),),
    ),
    kind(
        "living.cloned",
        "A clone of {origin} was grown: {product}.",
        roles=(role(R.ORIGIN), role(R.PRODUCT), role(R.MAKER, required=False)),
        facts=(number("generation", U.COUNT),),
    ),
    kind(
        "living.contained",
        "{line} was hunted down and held in again, out of {lands:land|lands}.",
        roles=(role(R.SUBJECT, required=False),),
        facts=(LIVING_LINE, number("lands", U.COUNT)),
    ),
    kind("living.cure_cultured", "{maker} cultured a cure for {target}.", roles=(role(R.MAKER), role(R.TARGET)), facts=(named("line", required=False),)),
    kind(
        "living.died",
        "{subject} died and went back to the land.",
        roles=(role(R.SUBJECT),),
        facts=(number("age_seasons", U.SEASONS), number("lifespan", U.YEARS)),
        steps=frozenset({A.DIE}),
    ),
    kind(
        "living.disease_designed",
        "{maker} made a disease by design: {product}.",
        roles=(role(R.MAKER), role(R.PRODUCT), role(R.TARGET, required=False)),
        facts=(number("lethality", U.PERCENT), number("virulence", U.PERCENT)),
    ),
    kind(
        "living.disease_loosed",
        "{subject} got loose among the ones who made it.",
        roles=(role(R.SUBJECT), role(R.VICTIM)),
        facts=(number("severity", U.PERCENT),),
        collection=C.PLAGUE,
    ),
    kind(
        "living.drifted",
        "{line} drifted into a line of its own: {new_line}.",
        roles=(role(R.SUBJECT, required=False),),
        facts=(LIVING_LINE, named("new_line")),
    ),
    kind("living.escaped", "{line} got loose into the wild in {place}.", roles=(role(R.PLACE),), facts=(LIVING_LINE,), place=PlaceRule.REQUIRED),
    kind(
        "living.licensed",
        "{buyer} took a licence to grow {line} from {seller}.",
        roles=(role(R.BUYER), role(R.SELLER)),
        facts=(LIVING_LINE, number("fee", U.COIN)),
    ),
    kind(
        "living.line_blessed",
        "{patron} blessed the line {line}.",
        roles=(role(R.PATRON), role(R.SUBJECT, required=False)),
        facts=(LIVING_LINE, number("stability", U.PERCENT)),
        steps=frozenset({A.BLESS}),
    ),
    kind(
        "living.line_cursed",
        "{patron} cursed the line {line}.",
        roles=(role(R.PATRON), role(R.SUBJECT, required=False)),
        facts=(LIVING_LINE, number("stability", U.PERCENT)),
    ),
    kind(
        "living.line_made",
        "{maker} made a living line: {line}.",
        roles=(role(R.MAKER), role(R.SUBJECT, required=False)),
        facts=(LIVING_LINE, chosen("method", CultivationMethod), number("traits", U.COUNT)),
    ),
    kind(
        "living.mutated",
        "A new trait arose in the line {line}: {trait}.",
        roles=(role(R.SUBJECT, required=False),),
        facts=(LIVING_LINE, chosen("trait", LineTrait), number("strength", U.STRENGTH)),
    ),
    kind(
        "living.organ_grown",
        "{patient} was given a part grown for its body.",
        roles=(role(R.PATIENT), role(R.MAKER, required=False)),
        facts=(number("integration", U.PERCENT),),
    ),
    kind("living.partner_lost", "{subject} lost the partner that lived with them.", roles=(role(R.SUBJECT),), facts=(number("loss", U.PERCENT),)),
    kind("living.profile_made", "{subject} came alive.", roles=(role(R.SUBJECT),), facts=(number("lifespan", U.YEARS), number("gift", U.STRENGTH))),
    kind(
        "living.refused",
        "{subject} would not obey a handler it no longer trusts.",
        roles=(role(R.SUBJECT),),
        facts=(number("literalness", U.PERCENT),),
    ),
    kind("living.released", "{line} was let loose into the wild.", roles=(role(R.SUBJECT),), facts=(LIVING_LINE, number("escaped", U.COUNT))),
    kind(
        "living.rising",
        "{actor} rose with others who sought a higher standing under {authority}.",
        roles=(role(R.ACTOR), role(R.AUTHORITY)),
        facts=(chosen("law", LawKind), number("wanted", U.COUNT), number("step", U.COUNT)),
    ),
    kind("living.sample_lost", "An unkept bank of life, {subject}, lost a sample.", roles=(role(R.SUBJECT),), facts=(number("lost", U.COUNT),)),
    kind(
        "living.sapience",
        "{origin} rose to thought by design and became a people: {product}.",
        roles=(role(R.PRODUCT), role(R.ORIGIN), role(R.MAKER, required=False)),
        facts=(LIVING_LINE,),
    ),
    kind(
        "living.sapience_shaped",
        "The line {line} was shaped toward thought.",
        roles=(role(R.SUBJECT, required=False),),
        facts=(LIVING_LINE, number("strength", U.STRENGTH)),
    ),
    kind(
        "living.spread",
        "What lived in {origin} spread to {destination}.",
        roles=(role(R.ORIGIN), role(R.DESTINATION)),
        facts=(number("strength", U.STRENGTH), chosen("relation", HostRelation)),
    ),
    kind(
        "living.turned",
        "{subject} turned from its handler and answers to no one now.",
        roles=(role(R.SUBJECT), role(R.OWNER, required=False)),
        facts=(number("bond", U.PERCENT),),
    ),
    kind(
        "living.works_lapsed",
        "The living works of {subject} sickened; {old_method} gave way to {new_method}.",
        roles=(role(R.SUBJECT),),
        facts=(chosen("old_method", MethodKind), chosen("new_method", MethodKind)),
    ),
    *(
        kind(
            f"mortal.death.{ending}",
            template,
            roles=(role(R.VICTIM), role(R.HEIR, required=False), role(R.ACTOR, required=ending == "slain")),
            facts=(chosen("manner", DeathCause), number("age", U.YEARS), number("year", U.YEARS)),
            steps=frozenset({A.DIE}),
            clock=ProcessClock.INSTANT,
            feed=F.LIFE,
            chronicle_kind=K.DEATH,
        )
        for ending, template in (
            ("natural", "{victim} died at the age of {age}."),
            ("cause", "{victim} died; the cause was {manner}."),
            ("slain", "{victim} was killed by {actor}; the cause was {manner}."),
        )
    ),
    kind(
        "mortal.death_prestige",
        "The manner of the death of {subject} raised their house.",
        roles=(role(R.SUBJECT),),
        facts=(chosen("manner", DeathCause), number("prestige", U.STANDING)),
    ),
    kind(
        "mortal.death_shame",
        "The manner of the death of {subject} shamed their house.",
        roles=(role(R.SUBJECT),),
        facts=(chosen("manner", DeathCause), number("prestige", U.STANDING)),
    ),
    kind(
        "mortal.inheritance",
        "{items:item|items} of {predecessor} passed to {heir}.",
        roles=(role(R.PREDECESSOR), role(R.INSTRUMENT, many=True), role(R.HEIR, many=True)),
        facts=(number("items", U.COUNT),),
    ),
    kind(
        "mortal.inheritance_lost",
        "{items:item|items} of {predecessor} lay without an owner.",
        roles=(role(R.PREDECESSOR), role(R.INSTRUMENT, many=True)),
        facts=(number("items", U.COUNT),),
    ),
    kind(
        "mortal.mourning",
        "{actor} began a mourning tradition for {subject}: {product}.",
        roles=(role(R.ACTOR), role(R.SUBJECT), role(R.PRODUCT)),
        facts=(number("spread", U.PERCENT),),
        collection=C.FUNERAL,
    ),
    kind(
        "mortal.spirit",
        "The spirit of {predecessor} rose among the ancestors.",
        roles=(role(R.PREDECESSOR), role(R.PRODUCT)),
        facts=(chosen("alignment", SpiritAlignment), number("unrest", U.PERCENT)),
    ),
    kind(
        "mortal.spirit_restless",
        "The spirit of {predecessor} found no rest; it wanders as a restless spirit.",
        roles=(role(R.PREDECESSOR), role(R.PRODUCT)),
        facts=(chosen("alignment", SpiritAlignment), number("unrest", U.PERCENT)),
    ),
    kind(
        "mortal.word",
        '{subject}: "{word}"',
        roles=(role(R.SUBJECT), role(R.PRODUCT, required=False, many=True)),
        facts=(named("word"),),
        chronicle_kind=K.SPEECH,
    ),
    kind(
        "mortals.ghost",
        "{subject} died, but the law of the world called them back as a ghost.",
        roles=(role(R.SUBJECT),),
        facts=(number("age", U.YEARS), chosen("law", NaturalLaw), number("year", U.YEARS)),
        steps=frozenset({A.AGE, A.DIE, A.RETURN_TO_LIFE}),
    ),
    kind(
        "necromancy.tower",
        "{actor} raised a tower to work the rites of death: {product}.",
        roles=(role(R.ACTOR), role(R.PRODUCT)),
        facts=(number("power", U.STRENGTH),),
    ),
    kind(
        "necromancy.host",
        "{actor} raised {product} from their graves.",
        roles=(role(R.ACTOR), role(R.PRODUCT)),
        facts=(number("power", U.STRENGTH), number("size", U.COUNT)),
    ),
    kind(
        "necromancy.siege",
        "{actor}, led by {leader}, laid siege to {target}.",
        roles=(role(R.ACTOR), role(R.LEADER), role(R.TARGET)),
        facts=(number("power", U.STRENGTH),),
        place=PlaceRule.REQUIRED,
        collection=C.SIEGE,
    ),
    kind(
        "reproduction.changed",
        "{subject} came of the age when their people change, and changed sex.",
        roles=(role(R.SUBJECT),),
        facts=(number("age", U.YEARS), chosen("sex", Sex), number("change_age", U.YEARS)),
    ),
    kind("reproduction.budded", "{parent} budded and {child} grew from them.", roles=(role(R.PARENT), role(R.CHILD)), facts=(number("chance", U.PERCENT),)),
    kind(
        "stress.crisis",
        "{subject} entered a crisis: its people are poor, its elites too many and its treasury strained.",
        roles=(role(R.SUBJECT),),
        facts=(
            number("immiseration", U.PERCENT),
            number("elite_overproduction", U.PERCENT),
            number("fiscal_distress", U.PERCENT),
            number("psi", U.PERCENT),
            number("aspirants", U.COUNT),
            number("positions", U.COUNT),
        ),
        terms=True,
    ),
    kind(
        "stress.counter_elites",
        "{leader}, shut out of every office of {opponent}, gathered other disappointed aspirants into {product}.",
        roles=(role(R.LEADER), role(R.PRODUCT), role(R.OPPONENT)),
        facts=(number("overproduction", U.PERCENT),),
    ),
    kind(
        "stress.elites_fell",
        "In the strife of crisis {fallen:noble|nobles} of {subject} fell from their station.",
        roles=(role(R.SUBJECT),),
        facts=(number("fallen", U.PEOPLE), number("psi", U.PERCENT)),
    ),
    stress_break("deserted", "{subject} broke under the strain and deserted.", facts=(chosen("crime", CrimeKind),)),
    stress_break("flight", "{subject} broke under the strain and fled to {destination}.", (role(R.ORIGIN, required=False), role(R.DESTINATION))),
    stress_break("flight_wilds", "{subject} broke under the strain and fled into the wilds.", (role(R.ORIGIN, required=False),)),
    stress_break("rage", "{subject} broke under the strain and raged at the world."),
    stress_break("rage_at", "{subject} broke under the strain and fell upon {target} in a rage.", (role(R.TARGET),), (number("harm", U.HP),)),
    stress_break("despair", "{subject} sank into despair.", facts=(chosen("condition", ConditionKind),)),
    stress_break(
        "zeal",
        "{subject} broke under the strain and gave themself wholly to their faith.",
        (role(R.HOST, required=False),),
        (number("loyalty_god", U.PERCENT),),
    ),
    stress_break("vice", "{subject} broke under the strain and fell into vice.", facts=(chosen("package", PackageKind),)),
    stress_break("revelation", "{subject} broke under the strain, and in the breaking saw visions.", facts=(chosen("condition", ConditionKind),)),
    stress_break("revelation_seer", "{subject} broke under the strain, saw visions and became a seer.", facts=(chosen("role", MortalRole),)),
    tool(
        "answer_sickness",
        "{actor} set the answer of {subject} to {target}: {response}.",
        (role(R.ACTOR), role(R.SUBJECT), role(R.TARGET)),
        (chosen("response", PlagueResponse),),
    ),
    tool("cloned", "{maker} grew a clone of {origin}.", (role(R.MAKER), role(R.ORIGIN), role(R.PRODUCT))),
    tool(
        "disease_designed",
        "{maker} made a disease by design: {product}.",
        (role(R.MAKER), role(R.PRODUCT), role(R.TARGET, required=False)),
        (number("lethality", U.PERCENT), number("virulence", U.PERCENT)),
    ),
    tool("drill_trait", "{leader} took up a way of command: {trait}.", (role(R.LEADER),), (chosen("trait", CommanderTrait),)),
    tool("grown", "{maker} grew {product}.", (role(R.MAKER), role(R.PRODUCT)), (chosen("made", EntityType),)),
    tool(
        "install_augment",
        "{actor} took an augment: {augment}.",
        (role(R.ACTOR),),
        (chosen("augment", AugmentKind), chosen("make", AugmentMake), number("integration", U.PERCENT)),
    ),
    tool(
        "organ_grown",
        "{maker} grew a part for the body of {patient}.",
        (role(R.MAKER), role(R.PATIENT)),
        (chosen("slot", AugmentSlot), chosen("augment", AugmentKind)),
    ),
    tool("remove_augment", "{actor} had an augment taken out: {augment}.", (role(R.ACTOR),), (chosen("augment", AugmentKind),)),
    tool(
        "sample_banked",
        "{actor} put a sample of {subject} into {destination}.",
        (role(R.ACTOR), role(R.SUBJECT), role(R.DESTINATION)),
        (number("quality", U.PERCENT),),
    ),
    tool("seek_cure", "{actor} worked at a cure for {target} at {host}.", (role(R.ACTOR), role(R.HOST), role(R.TARGET)), (number("points", U.COUNT),)),
    tool(
        "symbiont_hosted",
        "{actor} took the line {line} to live within.",
        (role(R.ACTOR),),
        (LIVING_LINE, chosen("placement", HostPlacement), chosen("relation", HostRelation)),
    ),
    tool("symbiont_removed", "{actor} had what lived within taken out.", (role(R.ACTOR),), (chosen("relation", HostRelation),)),
    tool(
        "tend_maimed",
        "{healer} brought one with {maimed} back to work in {place}.",
        (role(R.HEALER), role(R.PLACE)),
        (chosen("maimed", MaimedKind), number("left", U.COUNT)),
    ),
)
