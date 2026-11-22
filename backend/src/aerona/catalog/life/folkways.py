from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.folkways import AccusationOutcome, LuckSign, MishapAttribution, MishapKind, MishapResponse
from aerona.domain.enums.mind import SkillKind, ValueAxis
from aerona.domain.enums.mortal import PunishmentKind
from aerona.domain.enums.society import KnowledgeBranch

COUNTERS = (SkillKind.STRATEGY, SkillKind.TACTICS)


EXPLAINERS: Mapping[MishapKind, KnowledgeBranch | None] = total(
    MishapKind,
    {
        MishapKind.ILLNESS: KnowledgeBranch.MEDICINE,
        MishapKind.CROP_FAILURE: KnowledgeBranch.AGRICULTURE,
        MishapKind.CHILD_DEATH: KnowledgeBranch.MEDICINE,
        MishapKind.LIVESTOCK_DEATH: KnowledgeBranch.AGRICULTURE,
        MishapKind.ACCIDENT: None,
        MishapKind.BAD_LUCK: None,
        MishapKind.FALL: None,
        MishapKind.CRUSH: None,
        MishapKind.CUT: None,
        MishapKind.BURN: None,
        MishapKind.SCALD: None,
        MishapKind.DROWNING: None,
        MishapKind.BEAST: None,
        MishapKind.TOOL: None,
        MishapKind.MACHINE: None,
        MishapKind.VEHICLE: None,
        MishapKind.COLLAPSE: None,
        MishapKind.HOUSE_FIRE: None,
        MishapKind.POISONING: KnowledgeBranch.MEDICINE,
        MishapKind.CHOKING: None,
        MishapKind.EXPOSURE: None,
        MishapKind.LIGHTNING: KnowledgeBranch.ASTRONOMY,
        MishapKind.SPORT: None,
        MishapKind.BRAWL: None,
        MishapKind.LOST_WAY: None,
        MishapKind.STORES_SPOILED: KnowledgeBranch.AGRICULTURE,
        MishapKind.GOODS_LOST: None,
        MishapKind.PURSE_LOST: None,
        MishapKind.THEFT_SUFFERED: None,
        MishapKind.TOOL_BROKEN: None,
        MishapKind.NEAR_MISS: None,
    },
)


LEANINGS: Mapping[MishapAttribution, tuple[ValueAxis, ...]] = {
    MishapAttribution.CHANCE: (ValueAxis.KNOWLEDGE, ValueAxis.TRUTH),
    MishapAttribution.KNOWN_CAUSE: (ValueAxis.KNOWLEDGE,),
    MishapAttribution.WITCHCRAFT: (ValueAxis.SUPERSTITION,),
    MishapAttribution.CURSE: (ValueAxis.SUPERSTITION,),
    MishapAttribution.GOD: (ValueAxis.PIETY,),
    MishapAttribution.SPIRIT: (ValueAxis.NATURE,),
    MishapAttribution.ANCESTOR: (ValueAxis.DEATH, ValueAxis.FAMILY),
    MishapAttribution.OMEN: (ValueAxis.SUPERSTITION, ValueAxis.TRADITION),
    MishapAttribution.FATE: (ValueAxis.TRADITION,),
    MishapAttribution.ENEMY_SCHEME: (ValueAxis.LOYALTY,),
    MishapAttribution.IMPURITY: (ValueAxis.PURITY,),
    MishapAttribution.BROKEN_OATH: (ValueAxis.HONOUR, ValueAxis.LAW),
    MishapAttribution.MADE_MIND: (ValueAxis.TRADITION, ValueAxis.PURITY),
    MishapAttribution.HIDDEN_PEOPLE: (ValueAxis.SUPERSTITION, ValueAxis.NATURE),
}


RESPONSES: Mapping[MishapAttribution, MishapResponse] = {
    MishapAttribution.CHANCE: MishapResponse.NOTHING,
    MishapAttribution.KNOWN_CAUSE: MishapResponse.SAFETY_CUSTOM,
    MishapAttribution.WITCHCRAFT: MishapResponse.ACCUSATION,
    MishapAttribution.CURSE: MishapResponse.CHARM,
    MishapAttribution.GOD: MishapResponse.OFFERING,
    MishapAttribution.SPIRIT: MishapResponse.RITE,
    MishapAttribution.ANCESTOR: MishapResponse.RITE,
    MishapAttribution.OMEN: MishapResponse.RITE,
    MishapAttribution.FATE: MishapResponse.NOTHING,
    MishapAttribution.ENEMY_SCHEME: MishapResponse.NOTHING,
    MishapAttribution.IMPURITY: MishapResponse.PURIFICATION,
    MishapAttribution.BROKEN_OATH: MishapResponse.NOTHING,
    MishapAttribution.MADE_MIND: MishapResponse.ACCUSATION,
    MishapAttribution.HIDDEN_PEOPLE: MishapResponse.OFFERING,
}


SIGN_WORDS: Mapping[LuckSign, str] = {
    LuckSign.DAY: "day",
    LuckSign.NUMBER: "number",
    LuckSign.SIGN: "sign",
    LuckSign.GESTURE: "gesture",
    LuckSign.PLACE: "place",
    LuckSign.ACT: "act",
    LuckSign.PERSON: "kind of person",
}


PENALTY_OUTCOMES = {PunishmentKind.DEATH: AccusationOutcome.KILLED, PunishmentKind.EXILE: AccusationOutcome.EXILED}

WEIGHTS_FOR_MISHAP_ATTRIBUTIONS = (MishapAttribution.OMEN, MishapAttribution.FATE)
ANSWER_MISHAP_RESPONSES = (MishapResponse.RITE, MishapResponse.OFFERING)
