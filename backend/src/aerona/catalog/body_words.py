from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.body import BodyPlan

BODY_WORDS: Mapping[BodyPlan, tuple[str, ...]] = total(
    BodyPlan,
    {
        BodyPlan.HUMANOID: ("folk", "people", "kin", "giant", "dwarf", "elf", "troll", "ogre"),
        BodyPlan.QUADRUPED: ("hound", "wolf", "horse", "boar", "cat", "deer", "bear", "ox", "goat", "beast"),
        BodyPlan.AVIAN: ("bird", "hawk", "eagle", "owl", "raven", "crow", "griffin", "roc", "feather"),
        BodyPlan.SERPENTINE: ("serpent", "snake", "wyrm", "eel", "naga", "worm", "viper", "adder"),
        BodyPlan.INSECTOID: ("insect", "beetle", "ant", "spider", "mantis", "wasp", "bee", "locust", "scorpion"),
        BodyPlan.AQUATIC: ("fish", "whale", "shark", "seal", "fin", "gill"),
        BodyPlan.AMORPHOUS: ("ooze", "slime", "jelly", "blob", "mire", "sludge"),
        BodyPlan.ARBOREAL: ("ape", "monkey", "sloth", "dryad", "treefolk", "canopy", "vine"),
        BodyPlan.INCORPOREAL: ("ghost", "spirit", "wraith", "shade", "phantom", "wisp", "specter"),
        BodyPlan.COLOSSAL: ("colossus", "titan", "leviathan", "behemoth", "mammoth", "mountain"),
        BodyPlan.CONSTRUCT: ("golem", "construct", "automaton", "clockwork", "statue", "effigy"),
        BodyPlan.DIVINE_MANIFEST: (),
        BodyPlan.TENTACLED: ("squid", "octopus", "cuttlefish", "kraken", "tentacle"),
        BodyPlan.CENTAUROID: ("centaur",),
        BodyPlan.RADIAL: ("starfish", "urchin", "radial"),
        BodyPlan.COLONIAL: ("colony", "coral", "siphonophore"),
        BodyPlan.HEXAPOD: ("hexapod", "six-legged"),
        BodyPlan.ROOTED: ("rooted", "sessile"),
    },
)
