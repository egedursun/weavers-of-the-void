from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.body import ConditionKind, InjuryKind
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.records import StepAction

CONDITION_PHRASES: Mapping[ConditionKind, str] = {
    ConditionKind.CHRONIC_ILLNESS: "fell into a lingering illness",
    ConditionKind.PARANOIA: "grew paranoid",
    ConditionKind.VISIONS: "began to see visions",
    ConditionKind.RAGE: "was seized by fits of rage",
    ConditionKind.MELANCHOLY: "sank into melancholy",
    ConditionKind.ADDICTION: "fell into addiction",
    ConditionKind.AGE_BLINDNESS: "went blind with age",
    ConditionKind.AGE_DEAFNESS: "went deaf with age",
    ConditionKind.WITHERED_LIMB: "was left with a withered limb",
    ConditionKind.ENDLESS_HUNGER: "was cursed with an endless hunger",
    ConditionKind.POSSESSION: "was possessed by a spirit",
    ConditionKind.VOID_TAINT: "was tainted by the void",
    ConditionKind.CHOSEN_MARK: "bore the mark of the chosen",
    ConditionKind.DIVINE_BRAND: "bore a god's brand",
    ConditionKind.NIGHTMARES: "began to dream the same nightmare again and again",
    ConditionKind.COMATOSE: "fell into a sleep no one could wake them from",
    ConditionKind.COGNITIVE_DECLINE: "began to lose their memory and their reckoning",
    ConditionKind.MALNUTRITION: "began to waste from a poor diet",
}

ILLNESSES = frozenset({ConditionKind.CHRONIC_ILLNESS, ConditionKind.ENDLESS_HUNGER, ConditionKind.MALNUTRITION})
ONSET_STEPS: Mapping[PackageKind, StepAction] = {
    PackageKind.SNAKE_VENOM: StepAction.FALL_ILL,
    PackageKind.LYCANTHROPY: StepAction.FALL_ILL,
    PackageKind.VAMPIRISM: StepAction.FALL_ILL,
    PackageKind.VOID_TAINT: StepAction.FALL_ILL,
    PackageKind.HUNGER_CURSE: StepAction.FALL_ILL,
    PackageKind.WARPING: StepAction.FALL_ILL,
    PackageKind.POSSESSION: StepAction.POSSESS,
    PackageKind.DIVINE_BLESSING: StepAction.BLESS,
}

END_PHRASES: Mapping[ConditionKind, str] = {
    ConditionKind.CHRONIC_ILLNESS: "recovered from a lingering illness",
    ConditionKind.PARANOIA: "was freed of paranoia",
    ConditionKind.VISIONS: "no longer sees visions",
    ConditionKind.RAGE: "mastered their rage",
    ConditionKind.MELANCHOLY: "came out of melancholy",
    ConditionKind.ADDICTION: "broke free of addiction",
    ConditionKind.POSSESSION: "was freed of the spirit that possessed them",
    ConditionKind.ENDLESS_HUNGER: "was freed of the endless hunger",
    ConditionKind.NIGHTMARES: "slept free of nightmares at last",
    ConditionKind.COMATOSE: "woke at last",
    ConditionKind.COGNITIVE_DECLINE: "came back to their wits",
    ConditionKind.MALNUTRITION: "was nourished back to strength",
}

RESPONSE_WORDS: Mapping[PlagueResponse, str] = {
    PlagueResponse.CLOSE_BORDERS: "closed its borders",
    PlagueResponse.QUARANTINE: "shut its sick away",
    PlagueResponse.BURN_DEAD: "burned its dead",
    PlagueResponse.EXPEL_SICK: "drove out its sick",
    PlagueResponse.PRAYER: "gathered to pray",
    PlagueResponse.SEEK_CURE: "set its learned to seek a cure",
}

INJURY_PHRASES: Mapping[InjuryKind, str] = total(
    InjuryKind,
    {
        InjuryKind.BRUISE: "a bruising blow",
        InjuryKind.CUT: "a cut",
        InjuryKind.DEEP_CUT: "a deep cut",
        InjuryKind.PUNCTURE: "a piercing wound",
        InjuryKind.FRACTURE: "a broken bone",
        InjuryKind.CRUSH: "a crushing blow",
        InjuryKind.BURN: "burns",
        InjuryKind.FROSTBITE: "frostbite",
        InjuryKind.BITE: "a savage bite",
        InjuryKind.VENOM: "venom",
        InjuryKind.SEVERED: "the loss of a part",
        InjuryKind.GOUGED: "a gouging",
        InjuryKind.DESTROYED: "a ruinous wound",
        InjuryKind.CURSE_WITHER: "a withering curse",
        InjuryKind.VOID_TOUCH: "the touch of the void",
        InjuryKind.DIVINE_BRAND: "a divine brand",
        InjuryKind.SICKNESS: "a wasting sickness",
        InjuryKind.GUNSHOT: "a gunshot wound",
        InjuryKind.SHRAPNEL: "shrapnel wounds",
        InjuryKind.CONCUSSION: "a concussion",
        InjuryKind.ELECTRICAL_BURN: "electrical burns",
        InjuryKind.CHEMICAL_BURN: "chemical burns",
        InjuryKind.RADIATION_SICKNESS: "radiation sickness",
        InjuryKind.MIND_SCAR: "harm to the mind",
    },
)
LOSS_LINES: Mapping[InjuryKind, str] = {
    InjuryKind.SEVERED: "{patient} lost their {part}.",
    InjuryKind.GOUGED: "{patient} had their {part} gouged out.",
    InjuryKind.DESTROYED: "The {part} of {patient} was ruined.",
}


def injury_line(kind: InjuryKind) -> str:
    return LOSS_LINES.get(kind) or "{patient} took " + INJURY_PHRASES[kind] + " to the {part}."
