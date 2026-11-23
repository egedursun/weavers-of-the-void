from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.faith import RebirthPath
from aerona.domain.enums.folkways import AccusationOutcome, LuckReach, LuckSign
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule
from aerona.domain.enums.records import ProcessClock as C
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.sacred import (
    DivinationKind,
    DivinationQuestion,
    GeniusLocusKind,
    OmenVerdict,
    PetitionKind,
    SacramentKind,
    SpiritOffence,
    TheodicyCause,
    VisionKind,
)

KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "mystic.vision",
        G.FAITH,
        "{subject} knew the divine as {vision}; answered by a god: {answered}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.ORIGIN, required=False)),
        facts=(FactSpec("vision", FactValue.ENUM, enum=VisionKind), FactSpec("answered", FactValue.NUMBER, FactUnit.COUNT)),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "faith.crisis",
        G.FAITH,
        "The faithful of {subject} in {place} asked why their god was silent through {cause}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PLACE)),
        facts=(FactSpec("cause", FactValue.ENUM, enum=TheodicyCause), FactSpec("suffering", FactValue.NUMBER, FactUnit.PERCENT)),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "sacrament.given",
        G.FAITH,
        "{officiant} gave {patient} the rite of {rite} in the faith of {subject}.",
        roles=(RoleSpec(R.PATIENT), RoleSpec(R.SUBJECT), RoleSpec(R.OFFICIANT, required=False)),
        facts=(FactSpec("rite", FactValue.ENUM, enum=SacramentKind),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "soul.reborn",
        G.FAITH,
        "The soul of {predecessor} was born again by the path of {path} as {product}.",
        roles=(RoleSpec(R.PREDECESSOR), RoleSpec(R.PRODUCT), RoleSpec(R.PLACE, required=False)),
        facts=(FactSpec("path", FactValue.ENUM, enum=RebirthPath),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "spirit.appeared",
        G.FAITH,
        "A spirit of the {spirit} came to dwell in {place}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PLACE)),
        facts=(FactSpec("spirit", FactValue.ENUM, enum=GeniusLocusKind),),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "spirit.offended",
        G.FAITH,
        "The spirit {subject} was offended by {offence}; its contentment stands at {contentment}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PLACE, required=False)),
        facts=(FactSpec("offence", FactValue.ENUM, enum=SpiritOffence), FactSpec("contentment", FactValue.NUMBER, FactUnit.PERCENT)),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "petition.filed",
        G.FAITH,
        "{actor} petitioned the spirit {subject} for {petition}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.SUBJECT), RoleSpec(R.TARGET, required=False)),
        facts=(FactSpec("petition", FactValue.ENUM, enum=PetitionKind),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "luck.read",
        G.FAITH,
        "The folk of {place} read luck in {sign:an} touching {reach}; held lucky: {lucky}.",
        roles=(RoleSpec(R.PLACE), RoleSpec(R.SUBJECT, required=False)),
        facts=(
            FactSpec("sign", FactValue.ENUM, enum=LuckSign),
            FactSpec("reach", FactValue.ENUM, enum=LuckReach),
            FactSpec("lucky", FactValue.NUMBER, FactUnit.COUNT),
        ),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "hunt.accusation",
        G.LAW,
        "The accusation against {accused} in {place} ended: {outcome}.",
        roles=(RoleSpec(R.ACCUSED), RoleSpec(R.PLACE)),
        facts=(FactSpec("outcome", FactValue.ENUM, enum=AccusationOutcome),),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "omen.read",
        G.FAITH,
        "The diviners of {subject} read {method} on {question}, and read it {verdict}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.ACTOR, required=False)),
        facts=(
            FactSpec("method", FactValue.ENUM, enum=DivinationKind),
            FactSpec("question", FactValue.ENUM, enum=DivinationQuestion),
            FactSpec("verdict", FactValue.ENUM, enum=OmenVerdict),
        ),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
)
