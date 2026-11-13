from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.body import BodyBuild, BodyPlan, HeightClass
from aerona.domain.enums.cosmography import BeingKind
from aerona.domain.enums.divine import OuterHunger


@dataclass(frozen=True)
class PlanSpec:
    plan: BodyPlan
    label: str
    words: tuple[str, ...]
    height: HeightClass
    build: BodyBuild


PLANS: dict[BodyPlan, PlanSpec] = {
    spec.plan: spec
    for spec in (
        PlanSpec(
            BodyPlan.HUMANOID,
            "two legs, two arms, a head",
            ("folk", "people", "kin", "giant", "dwarf", "elf", "troll", "ogre"),
            HeightClass.AVERAGE,
            BodyBuild.AVERAGE,
        ),
        PlanSpec(
            BodyPlan.QUADRUPED,
            "four legs and a head",
            ("hound", "wolf", "horse", "boar", "cat", "deer", "bear", "ox", "goat", "beast"),
            HeightClass.AVERAGE,
            BodyBuild.AVERAGE,
        ),
        PlanSpec(
            BodyPlan.AVIAN,
            "wings, two legs and a beak",
            ("bird", "hawk", "eagle", "owl", "raven", "crow", "griffin", "roc", "feather"),
            HeightClass.SHORT,
            BodyBuild.SLIGHT,
        ),
        PlanSpec(
            BodyPlan.SERPENTINE,
            "a long limbless body",
            ("serpent", "snake", "wyrm", "eel", "naga", "worm", "viper", "adder"),
            HeightClass.SHORT,
            BodyBuild.AVERAGE,
        ),
        PlanSpec(
            BodyPlan.INSECTOID,
            "six legs, a shell and feelers",
            ("insect", "beetle", "ant", "spider", "mantis", "wasp", "bee", "locust", "scorpion"),
            HeightClass.SHORT,
            BodyBuild.SLIGHT,
        ),
        PlanSpec(
            BodyPlan.AQUATIC,
            "fins, gills and a tail",
            ("fish", "whale", "shark", "squid", "cuttlefish", "kraken", "seal", "fin", "gill"),
            HeightClass.AVERAGE,
            BodyBuild.HEAVY,
        ),
        PlanSpec(BodyPlan.AMORPHOUS, "a shapeless mass", ("ooze", "slime", "jelly", "blob", "mire", "sludge"), HeightClass.SHORT, BodyBuild.HEAVY),
        PlanSpec(
            BodyPlan.ARBOREAL,
            "long arms for climbing and a gripping tail",
            ("ape", "monkey", "sloth", "dryad", "treefolk", "canopy", "vine"),
            HeightClass.AVERAGE,
            BodyBuild.SLIGHT,
        ),
        PlanSpec(
            BodyPlan.INCORPOREAL,
            "no flesh, only a shape of light or shadow",
            ("ghost", "spirit", "wraith", "shade", "phantom", "wisp", "specter"),
            HeightClass.AVERAGE,
            BodyBuild.SLIGHT,
        ),
        PlanSpec(
            BodyPlan.COLOSSAL,
            "a body the size of a hill",
            ("colossus", "titan", "leviathan", "behemoth", "mammoth", "mountain"),
            HeightClass.GIANT,
            BodyBuild.GIANT,
        ),
        PlanSpec(
            BodyPlan.CONSTRUCT,
            "a made body of stone, metal or wood",
            ("golem", "construct", "automaton", "clockwork", "statue", "effigy"),
            HeightClass.TALL,
            BodyBuild.HEAVY,
        ),
        PlanSpec(BodyPlan.DIVINE_MANIFEST, "a god's manifest form", (), HeightClass.TALL, BodyBuild.AVERAGE),
    )
}

HEIGHT_RANK: dict[HeightClass, int] = {HeightClass.SHORT: 0, HeightClass.AVERAGE: 1, HeightClass.TALL: 2, HeightClass.GIANT: 4}
BUILD_RANK: dict[BodyBuild, int] = {BodyBuild.SLIGHT: 0, BodyBuild.AVERAGE: 1, BodyBuild.HEAVY: 2, BodyBuild.GIANT: 4}
WHOLE_PLANS = frozenset({BodyPlan.SERPENTINE, BodyPlan.AMORPHOUS, BodyPlan.INCORPOREAL})


BEING_PLANS: MappingProxyType[BeingKind, BodyPlan] = total(
    BeingKind,
    {
        BeingKind.PLANAR_NATIVE: BodyPlan.HUMANOID,
        BeingKind.DIMENSION_WALKER: BodyPlan.HUMANOID,
        BeingKind.RIFT_SPAWN: BodyPlan.INSECTOID,
        BeingKind.HIGHER_DIMENSIONAL: BodyPlan.DIVINE_MANIFEST,
        BeingKind.STAR_EATER: BodyPlan.COLOSSAL,
        BeingKind.NEBULA_MIND: BodyPlan.AMORPHOUS,
        BeingKind.GALACTIC_LEVIATHAN: BodyPlan.SERPENTINE,
        BeingKind.VOID_SHEPHERD: BodyPlan.COLOSSAL,
        BeingKind.ECHO: BodyPlan.INCORPOREAL,
        BeingKind.TIME_WANDERER: BodyPlan.INCORPOREAL,
        BeingKind.COSMIC_TITAN: BodyPlan.COLOSSAL,
        BeingKind.VEIL_WARDEN: BodyPlan.INCORPOREAL,
        BeingKind.PLANE_SOVEREIGN: BodyPlan.DIVINE_MANIFEST,
        BeingKind.SWARM_INTELLIGENCE: BodyPlan.AMORPHOUS,
        BeingKind.LIVING_CONSTELLATION: BodyPlan.INCORPOREAL,
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
    },
)
