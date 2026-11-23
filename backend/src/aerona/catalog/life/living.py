from aerona.core.total import total
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.living import CultivationMethod, Fertility, HostPlacement, LivingCraftStance, Metabolism
from aerona.domain.enums.mind import SkillKind

FEED_OF = {Metabolism.FEEDING: CommodityKind.FODDER, Metabolism.CHEMICAL: CommodityKind.ORE, Metabolism.HEAT: CommodityKind.FUEL}


DEPTH = total(
    HostPlacement, {HostPlacement.SKIN: 1, HostPlacement.BLOOD: 2, HostPlacement.GUT: 2, HostPlacement.ORGAN: 3, HostPlacement.NERVE: 4, HostPlacement.MIND: 5}
)


CRAFTS = total(
    CultivationMethod,
    {
        CultivationMethod.SELECTIVE_BREEDING: ((SkillKind.BEAST_HANDLING, SkillKind.FORAGING), None),
        CultivationMethod.CULTIVATION: ((SkillKind.FORAGING, SkillKind.BEAST_HANDLING), None),
        CultivationMethod.SHAPING: ((SkillKind.MEDICINE, SkillKind.SPELLCRAFT, SkillKind.SURGERY), None),
        CultivationMethod.ENGINEERING: ((SkillKind.SCIENCE, SkillKind.MEDICINE), Technique.GENETIC_ENGINEERING),
        CultivationMethod.SYNTHESIS: ((SkillKind.SCIENCE,), Technique.GENETIC_ENGINEERING),
        CultivationMethod.BINDING: ((SkillKind.SPELLCRAFT, SkillKind.MEDICINE), None),
        CultivationMethod.CLONING: ((SkillKind.SCIENCE, SkillKind.MEDICINE, SkillKind.SPELLCRAFT), Technique.GENETIC_ENGINEERING),
        CultivationMethod.MERGING: ((SkillKind.SCIENCE, SkillKind.SPELLCRAFT, SkillKind.MEDICINE), Technique.GENETIC_ENGINEERING),
        CultivationMethod.INDUCTION: ((SkillKind.SPELLCRAFT, SkillKind.SCIENCE, SkillKind.FORAGING), None),
        CultivationMethod.HYBRIDISING: ((SkillKind.BEAST_HANDLING, SkillKind.FORAGING), None),
        CultivationMethod.WILD_RELEASE: ((SkillKind.FORAGING, SkillKind.BEAST_HANDLING), None),
    },
)


STANCE_SIGN = {
    LivingCraftStance.ABOMINATION: -1,
    LivingCraftStance.PERMITTED: 0,
    LivingCraftStance.SACRED_DUTY: 1,
    LivingCraftStance.SILENT: 0,
    LivingCraftStance.REGULATED: 0,
}

SEED_DUES_FERTILITYS = (Fertility.STERILE, Fertility.NEEDS_MAKER)
BREED_FERTILITYS = frozenset({Fertility.STERILE, Fertility.NEEDS_MAKER})
