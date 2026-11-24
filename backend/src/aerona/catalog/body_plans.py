from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.body import BodyBuild, BodyPlan, HeightClass
from aerona.domain.enums.cosmography import BeingKind
from aerona.domain.enums.divine import OuterHunger
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.society import CreatureTrait


@dataclass(frozen=True)
class PlanSpec:
    plan: BodyPlan
    label: str
    height: HeightClass
    build: BodyBuild


PLANS: dict[BodyPlan, PlanSpec] = {
    spec.plan: spec
    for spec in (
        PlanSpec(
            BodyPlan.HUMANOID,
            "two legs, two arms, a head",
            HeightClass.AVERAGE,
            BodyBuild.AVERAGE,
        ),
        PlanSpec(
            BodyPlan.QUADRUPED,
            "four legs and a head",
            HeightClass.AVERAGE,
            BodyBuild.AVERAGE,
        ),
        PlanSpec(
            BodyPlan.AVIAN,
            "wings, two legs and a beak",
            HeightClass.SHORT,
            BodyBuild.SLIGHT,
        ),
        PlanSpec(
            BodyPlan.SERPENTINE,
            "a long limbless body",
            HeightClass.SHORT,
            BodyBuild.AVERAGE,
        ),
        PlanSpec(
            BodyPlan.INSECTOID,
            "six legs, a shell and feelers",
            HeightClass.SHORT,
            BodyBuild.SLIGHT,
        ),
        PlanSpec(
            BodyPlan.AQUATIC,
            "fins, gills and a tail",
            HeightClass.AVERAGE,
            BodyBuild.HEAVY,
        ),
        PlanSpec(BodyPlan.AMORPHOUS, "a shapeless mass", HeightClass.SHORT, BodyBuild.HEAVY),
        PlanSpec(
            BodyPlan.ARBOREAL,
            "long arms for climbing and a gripping tail",
            HeightClass.AVERAGE,
            BodyBuild.SLIGHT,
        ),
        PlanSpec(
            BodyPlan.INCORPOREAL,
            "no flesh, a form without a body",
            HeightClass.AVERAGE,
            BodyBuild.SLIGHT,
        ),
        PlanSpec(
            BodyPlan.COLOSSAL,
            "a body far larger than a dwelling",
            HeightClass.GIANT,
            BodyBuild.GIANT,
        ),
        PlanSpec(
            BodyPlan.CONSTRUCT,
            "a body that was made rather than born",
            HeightClass.TALL,
            BodyBuild.HEAVY,
        ),
        PlanSpec(BodyPlan.DIVINE_MANIFEST, "a god's manifest form", HeightClass.TALL, BodyBuild.AVERAGE),
        PlanSpec(BodyPlan.TENTACLED, "many soft arms round a head and a beak", HeightClass.AVERAGE, BodyBuild.AVERAGE),
        PlanSpec(BodyPlan.CENTAUROID, "an upright body with arms set on four legs", HeightClass.TALL, BodyBuild.HEAVY),
        PlanSpec(BodyPlan.RADIAL, "arms set round a centre, with no front and no head", HeightClass.SHORT, BodyBuild.SLIGHT),
        PlanSpec(BodyPlan.COLONIAL, "one body made of many living members", HeightClass.AVERAGE, BodyBuild.AVERAGE),
        PlanSpec(BodyPlan.HEXAPOD, "a body set on six limbs", HeightClass.AVERAGE, BodyBuild.HEAVY),
        PlanSpec(BodyPlan.ROOTED, "a body held in the ground by roots", HeightClass.TALL, BodyBuild.HEAVY),
    )
}

HEIGHT_RANK: dict[HeightClass, int] = {HeightClass.SHORT: 0, HeightClass.AVERAGE: 1, HeightClass.TALL: 2, HeightClass.GIANT: 4}
BUILD_RANK: dict[BodyBuild, int] = {BodyBuild.SLIGHT: 0, BodyBuild.AVERAGE: 1, BodyBuild.HEAVY: 2, BodyBuild.GIANT: 4}
WHOLE_PLANS = frozenset({BodyPlan.SERPENTINE, BodyPlan.AMORPHOUS, BodyPlan.INCORPOREAL})


BEING_PLANS: MappingProxyType[BeingKind, BodyPlan] = total(
    BeingKind,
    {
        BeingKind.PLANAR_NATIVE: BodyPlan.HUMANOID,
        BeingKind.DIMENSION_TRAVELLER: BodyPlan.HUMANOID,
        BeingKind.RIFT_BORN: BodyPlan.INSECTOID,
        BeingKind.HIGHER_DIMENSIONAL: BodyPlan.DIVINE_MANIFEST,
        BeingKind.STAR_FEEDER: BodyPlan.COLOSSAL,
        BeingKind.CLOUD_MIND: BodyPlan.AMORPHOUS,
        BeingKind.GALAXY_SCALE_BEING: BodyPlan.SERPENTINE,
        BeingKind.VOID_KEEPER: BodyPlan.COLOSSAL,
        BeingKind.MIRRORED_DOUBLE: BodyPlan.INCORPOREAL,
        BeingKind.TIME_TRAVELLER: BodyPlan.INCORPOREAL,
        BeingKind.SYSTEM_SCALE_BEING: BodyPlan.COLOSSAL,
        BeingKind.BOUNDARY_KEEPER: BodyPlan.INCORPOREAL,
        BeingKind.DIMENSION_RULER: BodyPlan.DIVINE_MANIFEST,
        BeingKind.SWARM_INTELLIGENCE: BodyPlan.AMORPHOUS,
        BeingKind.STAR_PATTERN_MIND: BodyPlan.INCORPOREAL,
        BeingKind.LIVING_WORLD: BodyPlan.COLOSSAL,
        BeingKind.ANCIENT_MADE_MIND: BodyPlan.CONSTRUCT,
    },
)
HUNGER_PLANS: MappingProxyType[OuterHunger, BodyPlan] = total(
    OuterHunger,
    {
        OuterHunger.SOULS: BodyPlan.AMORPHOUS,
        OuterHunger.KNOWLEDGE: BodyPlan.INCORPOREAL,
        OuterHunger.LIGHT: BodyPlan.COLOSSAL,
        OuterHunger.NAMES: BodyPlan.INCORPOREAL,
        OuterHunger.MEMORIES: BodyPlan.AMORPHOUS,
        OuterHunger.DREAMS: BodyPlan.INCORPOREAL,
        OuterHunger.TIME: BodyPlan.AMORPHOUS,
    },
)

PLAN_DIETS = {
    BodyPlan.ARBOREAL: Diet.PHOTOSYNTHETIC,
    BodyPlan.AMORPHOUS: Diet.FILTER,
    BodyPlan.CONSTRUCT: Diet.MINERAL,
    BodyPlan.INCORPOREAL: Diet.SOUL,
}
PLAN_TRAITS = {
    BodyPlan.AVIAN: CreatureTrait.FLYING,
    BodyPlan.AQUATIC: CreatureTrait.AQUATIC,
    BodyPlan.SERPENTINE: CreatureTrait.AMBUSH_PREDATOR,
    BodyPlan.INSECTOID: CreatureTrait.ARMOURED,
}
LAYERS = frozenset({BodyPlan.AVIAN, BodyPlan.SERPENTINE, BodyPlan.AQUATIC, BodyPlan.INSECTOID})
COLD_PLANS = frozenset({BodyPlan.SERPENTINE, BodyPlan.INSECTOID, BodyPlan.AQUATIC, BodyPlan.TENTACLED, BodyPlan.RADIAL})
BUDDING_PLANS = frozenset({BodyPlan.AMORPHOUS, BodyPlan.CONSTRUCT, BodyPlan.COLONIAL})
PLAN_TEXT = {
    BodyPlan.HUMANOID: "stands and grips like the peoples and is wounded as they are",
    BodyPlan.QUADRUPED: "runs on four legs and yields what its body gives",
    BodyPlan.AVIAN: "flies, sheds feathers and can carry a rider through the sky",
    BodyPlan.SERPENTINE: "lies in ambush",
    BodyPlan.INSECTOID: "wears chitin and armour",
    BodyPlan.AQUATIC: "lives in the waters and thirsts for them",
    BodyPlan.AMORPHOUS: "sifts its food from the waters",
    BodyPlan.ARBOREAL: "lives on light like a tree",
    BodyPlan.INCORPOREAL: "feeds on souls",
    BodyPlan.COLOSSAL: "stands colossal",
    BodyPlan.CONSTRUCT: "eats stone and ore",
    BodyPlan.DIVINE_MANIFEST: "is a god's own shape",
    BodyPlan.TENTACLED: "grips and moves with many soft arms and loses them one by one, not all at once",
    BodyPlan.CENTAUROID: "moves as a rider moves and fights with both hands",
    BodyPlan.RADIAL: "has no front and cannot be taken from the flank",
    BodyPlan.COLONIAL: "loses members to harm and grows them back, dying only when too few remain",
    BodyPlan.HEXAPOD: "stands steady on six limbs, carries great loads and climbs well",
    BodyPlan.ROOTED: "stays where it grows, drawing water and food through its roots, and moves only slowly",
}
MINED_PLANS = (BodyPlan.COLOSSAL, BodyPlan.INSECTOID)
FALLBACK_PLANS = frozenset({BodyPlan.QUADRUPED, BodyPlan.AQUATIC})
ATHERMIC_PLANS = frozenset({BodyPlan.CONSTRUCT})
CHANGEABLE_PLANS = tuple(plan for plan in BodyPlan if plan not in (BodyPlan.INCORPOREAL, BodyPlan.DIVINE_MANIFEST))
