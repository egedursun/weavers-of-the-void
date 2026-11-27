from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.agrarian import CommonsKind, NutrientKind
from aerona.domain.enums.crafts import CatchGround
from aerona.domain.enums.ecology import BeastTemper, DomesticationStage
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.nature import FermentKind
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule
from aerona.domain.enums.records import ProcessClock as C
from aerona.domain.enums.records import ProcessGroup as G

KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "tools.son.tend_soil_stock",
        G.GODS,
        "{actor} tended the {stock} in the soil of {place}, which now stands at {level}.{reason:? #}",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PLACE)),
        facts=(
            FactSpec("stock", FactValue.ENUM, enum=NutrientKind),
            FactSpec("level", FactValue.NUMBER, FactUnit.PERCENT),
            FactSpec("reason", FactValue.NAME, required=False),
        ),
        place=PlaceRule.REQUIRED,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "beast.fled",
        G.NATURE,
        "{subject} left its land, {temper}.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(FactSpec("temper", FactValue.ENUM, enum=BeastTemper),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "beast.migrated",
        G.NATURE,
        "{subject} set out on its seasonal path, {temper}.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(FactSpec("temper", FactValue.ENUM, enum=BeastTemper),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "ferment.culture_lost",
        G.NATURE,
        "The {culture} kept by {subject} spoiled and was lost.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(FactSpec("culture", FactValue.ENUM, enum=FermentKind),),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "species.escaped",
        G.NATURE,
        "{subject}, once {stage}, escaped its keepers and ran wild.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(FactSpec("stage", FactValue.ENUM, enum=DomesticationStage),),
        place=PlaceRule.NONE,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "catch.depleted",
        G.NATURE,
        "The {ground} of {subject} in {place} was worked below what it can bear, {left} left.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PLACE)),
        facts=(FactSpec("ground", FactValue.ENUM, enum=CatchGround), FactSpec("left", FactValue.NUMBER, FactUnit.PERCENT)),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "commons.overused",
        G.NATURE,
        "The common {common} of {subject} was used beyond what it bears and wore down to {condition}.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(
            FactSpec("common", FactValue.ENUM, enum=CommonsKind),
            FactSpec("use", FactValue.NUMBER, FactUnit.PERCENT),
            FactSpec("condition", FactValue.NUMBER, FactUnit.PERCENT),
        ),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
    IncidentKindSpec(
        "world.core_cooled",
        G.NATURE,
        "The inner heat of {subject} ran low and its fires quietened, volcanism falling to {volcanism}.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(FactSpec("volcanism", FactValue.NUMBER, FactUnit.PERCENT), FactSpec("heat", FactValue.NUMBER, FactUnit.PERCENT)),
        place=PlaceRule.NONE,
        clock=C.LIFE,
    ),
    IncidentKindSpec(
        "seal.failed",
        G.NATURE,
        "The made mind{actor:? #} no longer kept the seal over the deep beneath {subject}, and the seal failed.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.ACTOR, required=False)),
        place=PlaceRule.REQUIRED,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "quake.struck",
        G.NATURE,
        "The fault beneath {place} gave way and the ground shook.",
        roles=(RoleSpec(R.PLACE),),
        facts=(FactSpec("stress", FactValue.NUMBER, FactUnit.PERCENT), FactSpec("severity", FactValue.NUMBER, FactUnit.PERCENT)),
        place=PlaceRule.REQUIRED,
        clock=C.INSTANT,
    ),
    IncidentKindSpec(
        "rocks.pumice_rafts",
        G.NATURE,
        "Rafts of pumice from {place} drifted to {shores:shore|shores}, where the stone was gathered.",
        roles=(RoleSpec(R.PLACE),),
        facts=(FactSpec("shores", FactValue.NUMBER, FactUnit.COUNT),),
        place=PlaceRule.REQUIRED,
        clock=C.SEASON,
    ),
)
